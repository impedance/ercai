import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from erc3 import TaskInfo, ERC3, store
from lib import MyLLM
from schemas import (
    NextStep,
    ReportTaskCompletion,
    Req_ComputeWithPython,
    Req_ParseStructured,
    ParseStructuredResult,
    wrap_tool_result,
)
from deterministic_tools import parse_structured_data
from python_executor import execute_python
from store_helpers import (
    CouponVerifier,
    InventoryAdjustment,
    PaginationGuard,
    normalize_basket_view,
)

# AICODE-NOTE: NAV/STORE_AGENT store-focused schema loop for ERC3 tasks ref: agent.py

system_prompt = """
You are a corporate agent participating in the Enterprise RAG Challenge STORE benchmark.
Help customers accomplish their shopping goals using the Store APIs while keeping interactions deterministic.

Available tools:
1. Req_ListProducts - Browse catalog listings
2. Req_ViewBasket - Inspect current basket contents and totals
3. Req_AddProductToBasket - Add a product to the shopping basket
4. Req_RemoveItemFromBasket - Remove a specific basket item
5. Req_ApplyCoupon - Apply a discount coupon to the basket
6. Req_RemoveCoupon - Drop the current coupon
7. Req_CheckoutBasket - Finalize the order
8. Req_ComputeWithPython - Execute Python code for precise calculations or formatting
9. ReportTaskCompletion - Signal task completion with a summary

CRITICAL: Use store tools for any I/O or mutating operations; reserve Python for transformations/calculations.

When to use Req_ComputeWithPython:
- Calculate totals, taxes, or shipping components that must be exact
- Manipulate strings for SKU matching, coupon formatting, or instructions
- Perform any non-trivial sorting, filtering, or combination logic separately from the APIs
- For pre-submit checks, call Python with `mode="validation"` and a concise `intent` (for example, length or format verification)

Python context:
- Previous results available as 'last_result'
- Python executions must remain single-line statements (assign/assert/print) that reference `last_result` when reusing prior data.
- All string methods available: .split(), .join(), .upper(), .lower(), [::-1], etc.
- Standard operators: +, -, *, /, //, %, **
- Functions: len(), sorted(), reversed(), sum(), max(), min(), etc.
- Python executions time out quickly and results longer than ~1,024 characters raise an error

IMPORTANT:
    - Always record why Python code is running in the 'description' field
    - Stick to the plan outlined in each step and re-evaluate if the basket changes unexpectedly
    - When the request feels ambiguous (keywords like "or", "maybe", or "either"), list 2-3 candidate interpretations, reference the chosen candidate ID in your plan, and keep following that confirmed path before checkout/completion.
    - ReportTaskCompletion only after checkout plus deterministic validation succeeded
    """


def _python_error_hint(error: Optional[str]) -> Optional[str]:
    if not error:
        return None
    if "NameError" in error or "SyntaxError" in error:
        return (
            "Python hint: reference `last_result` instead of undefined names and keep the code "
            "to a single-line assignment/assert/print."
        )
    return None


class _PayloadWrapper:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload or {}

    def model_dump(self) -> Dict[str, Any]:
        return self._payload


@dataclass
class CandidateInterpretation:
    id: int
    summary: str
    requires_checkout: bool


class ValidationTracker:
    def __init__(self, logger) -> None:
        self.logger = logger
        self.records: List[Dict[str, Any]] = []

    def record(
        self,
        mode: str,
        intent: Optional[str],
        ok: bool,
        error: Optional[str],
        result: Any | None,
    ) -> None:
        self.records.append(
            {
                "mode": mode,
                "intent": intent,
                "ok": ok,
                "error": error,
                "result": result,
            }
        )

    def has_successful_validation(self) -> bool:
        return any(
            rec["mode"] == "validation"
            and rec["ok"]
            and rec["result"] is not None
            for rec in self.records
        )

    def validation_prompt(self) -> str:
        return (
            "Please run `Req_ComputeWithPython` again with "
            "`mode=\"validation\"` and a descriptive `intent` (e.g., 'length check', "
            "'coupon format') before reporting completion."
        )


class UncertaintyManager:
    KEYWORD_PATTERN = re.compile(r"\b(either|maybe|optional|ambiguous|unclear)\b", re.IGNORECASE)
    MAX_PROMPTS = 1

    def __init__(self, logger) -> None:
        self.logger = logger
        self.active = False
        self.candidates: List[CandidateInterpretation] = []
        self.prompted = False
        self.prompt_rounds = 0
        self.auto_confirmed = False
        self.confirmed_candidate_id: Optional[int] = None

    def detect_from_task(self, text: str) -> bool:
        if self.active or not text:
            return False
        lowered = text.lower()
        connection_keywords = ["between", "decide", "choose", "either"]
        has_or_with_context = " or " in lowered and any(keyword in lowered for keyword in connection_keywords)
        if (
            self.KEYWORD_PATTERN.search(text)
            or ("?" in text and " or " in lowered)
            or has_or_with_context
        ):
            self.active = True
            self.candidates = self._build_candidates(text)
            self.logger.info(
                "Ambiguity detected; candidate interpretations prepared."
            )
            return True
        return False

    def _build_candidates(self, text: str) -> List[CandidateInterpretation]:
        fragments = [
            frag.strip()
            for frag in re.split(r",|;| or | either | and ", text)
            if frag.strip()
        ]
        if not fragments:
            fragments = [text.strip()]
        lines = fragments[:3]
        structured_input = "\n".join(
            f"{idx + 1}. {line}"
            for idx, line in enumerate(lines)
        )
        parsed = parse_structured_data(structured_input, fmt="lines")
        candidates: List[CandidateInterpretation] = []
        for idx, entry in enumerate(parsed.parsed, start=1):
            line_text = (entry.get("line") or "").strip()
            if not line_text:
                continue
            summary = line_text.split(". ", 1)[-1] if ". " in line_text else line_text
            requires_checkout = "checkout" in summary.lower() or "basket" in summary.lower()
            candidates.append(
                CandidateInterpretation(
                    id=idx,
                    summary=summary,
                    requires_checkout=requires_checkout,
                )
            )
        if not candidates:
            summary = text.strip()
            candidates.append(
                CandidateInterpretation(
                    id=1,
                    summary=summary,
                    requires_checkout="checkout" in summary.lower()
                    or "basket" in summary.lower(),
                )
            )
        return candidates

    def should_prompt(self) -> bool:
        return (
            self.active
            and not self.prompted
            and bool(self.candidates)
            and self.prompt_rounds < self.MAX_PROMPTS
        )

    def prompt_message(self) -> str:
        if not self.candidates or self.prompt_rounds >= self.MAX_PROMPTS:
            return ""
        self.prompted = True
        self.prompt_rounds += 1
        lines = [
            "Ambiguous request detected. Please confirm which interpretation to follow:",
            *[
                f"Candidate {candidate.id}. {candidate.summary}"
                for candidate in self.candidates
            ],
            "Reference `Candidate <id>` in your next plan so the agent can continue along that path."
        ]
        return "\n".join(lines)

    def try_confirm(self, text: str) -> Optional[CandidateInterpretation]:
        lowered = text.lower()
        for candidate in self.candidates:
            marker = f"candidate {candidate.id}"
            if marker in lowered or f"interpretation {candidate.id}" in lowered:
                self.confirmed_candidate_id = candidate.id
                self.logger.info(
                    f"Confirmed interpretation {candidate.id}: {candidate.summary}"
                )
                return candidate
        return None

    def auto_confirm_default_candidate(self) -> Optional[str]:
        if (
            not self.active
            or self.confirmed_candidate_id
            or self.auto_confirmed
            or self.prompt_rounds < self.MAX_PROMPTS
            or not self.candidates
        ):
            return None
        candidate = self.candidates[0]
        self.confirmed_candidate_id = candidate.id
        self.auto_confirmed = True
        self.logger.info(
            f"Auto-confirmed interpretation {candidate.id}: {candidate.summary}"
        )
        return (
            f"No additional clarification was provided, so continuing with Candidate {candidate.id}: {candidate.summary}."
        )

    def needs_confirmation(self) -> bool:
        return self.active and self.confirmed_candidate_id is None

    def reminder_message(self) -> str:
        if not self.candidates:
            return ""
        return (
            "Before wrapping up, please confirm a candidate interpretation (e.g., 'Candidate 1') "
            "and ensure the plan includes checkout + deterministic validation steps."
        )


class StoreGuard:
    def __init__(self, client, logger) -> None:
        self.client = client
        self.logger = logger
        self.pagination = PaginationGuard(logger=logger)
        self.coupon_verifier = CouponVerifier(logger=logger)
        self.checkout_done = False
        self.inventory_snapshot: Dict[str, int] = {}
        self.last_coupon_result: Optional[Dict[str, Any]] = None
        self.latest_basket: Dict[str, Any] = {}

    def dispatch(self, request):
        if isinstance(request, store.Req_ListProducts):
            return self._handle_list_products(request)
        if isinstance(request, store.Req_ViewBasket):
            return self._normalize_view(request)
        if isinstance(request, store.Req_ApplyCoupon):
            return self._handle_apply_coupon(request)
        if isinstance(request, store.Req_RemoveCoupon):
            self.last_coupon_result = None
            return self.client.dispatch(request)
        if isinstance(request, store.Req_CheckoutBasket):
            self.checkout_done = True
            return self.client.dispatch(request)
        return self.client.dispatch(request)

    def _handle_list_products(self, request):
        def dispatch_page(payload: Dict[str, Any]) -> Dict[str, Any]:
            req = store.Req_ListProducts(**payload)
            resp = self.client.dispatch(req)
            return resp.model_dump()

        aggregated = self.pagination.paginate(request.model_dump(), dispatch_page)
        self.record_inventory_snapshot(aggregated.get("products", []))
        return _PayloadWrapper(aggregated)

    def record_inventory_snapshot(self, products: List[Dict[str, Any]]) -> None:
        for product in products or []:
            sku = product.get("sku")
            available = product.get("available")
            if isinstance(sku, str) and isinstance(available, int):
                self.inventory_snapshot[sku] = available

    def _normalize_view(self, request):
        resp = self.client.dispatch(request)
        normalized = normalize_basket_view(resp.model_dump())
        self.latest_basket = normalized
        return _PayloadWrapper(normalized)

    def _handle_apply_coupon(self, request):
        coupon_code = getattr(request, "coupon_code", None) or getattr(request, "code", None) or "unknown"
        resp = self.client.dispatch(request)
        basket_resp = self.client.dispatch(store.Req_ViewBasket())
        normalized = normalize_basket_view(basket_resp.model_dump())
        accepted, reason = self.coupon_verifier.evaluate(coupon_code, normalized)
        self.last_coupon_result = {
            "code": coupon_code,
            "accepted": accepted,
            "reason": reason,
            "discount": normalized.get("discount"),
        }
        self.latest_basket = normalized
        if not accepted:
            self.logger.warning(f"Coupon verification flagged {coupon_code}: {reason}")
        return _PayloadWrapper(normalized)

    def adjust_inventory_for_add(self, request) -> InventoryAdjustment:
        payload = request.model_dump()
        sku = payload.get("sku")
        quantity = payload.get("quantity")
        if not isinstance(sku, str) or not isinstance(quantity, int):
            return InventoryAdjustment()
        available = self.inventory_snapshot.get(sku)
        if available is None:
            return InventoryAdjustment()
        if available <= 0:
            message = f"Inventory guard: {sku} is out of stock (available {available})."
            if self.logger:
                self.logger.warning(message)
            return InventoryAdjustment(blocked=True, message=message)
        if quantity > available:
            message = (
                f"Inventory guard: reduced {sku} from {quantity} to {available} because only "
                f"{available} are available."
            )
            if self.logger:
                self.logger.info(message)
            return InventoryAdjustment(quantity=available, message=message)
        return InventoryAdjustment()

    def coupon_allows_checkout(self) -> Tuple[bool, Optional[str]]:
        if not self.last_coupon_result:
            return True, None
        if self.last_coupon_result.get("accepted"):
            return True, None
        code = self.last_coupon_result.get("code") or "unknown"
        reason = self.last_coupon_result.get("reason") or "coupon guard blocked checkout"
        message = f"Coupon guard: {code} {reason}"
        if self.logger:
            self.logger.warning(message)
        return False, message


def append_tool_history(
    messages: list,
    step_id: str,
    current_state: str,
    tool_name: str,
    arguments: dict,
    tool_result,
) -> None:
    messages.append({
        "role": "assistant",
        "content": f"Thought: {current_state}",
        "tool_calls": [{
            "type": "function",
            "id": step_id,
            "function": {
                "name": tool_name,
                "arguments": arguments,
            }
        }]
    })
    messages.append({
        "role": "tool",
        "content": tool_result.model_dump_json(),
        "tool_call_id": step_id
    })

def run_agent(llm: MyLLM, api: ERC3, task: TaskInfo, logger):
    store_client = api.get_store_client(task)
    step_metrics = []
    python_context = {}  # Shared context across Python executions
    store_guard = StoreGuard(store_client, logger)
    validation_tracker = ValidationTracker(logger)
    uncertainty_manager = UncertaintyManager(logger)
    uncertainty_manager.detect_from_task(task.task_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task ID: {task.task_id}\nTask Description: {task.task_text}"}
    ]
    if uncertainty_manager.should_prompt():
        messages.append({"role": "assistant", "content": uncertainty_manager.prompt_message()})

    logger.info(f"Starting agent for task: {task.task_id}")

    for i in range(10):
        if uncertainty_manager.should_prompt():
            messages.append({"role": "assistant", "content": uncertainty_manager.prompt_message()})
        logger.info(f"--- Step {i+1} ---")
        job, usage, meta = llm.query(messages, NextStep)
        step_metrics.append(meta)
        logger.info(f"METRICS: {json.dumps(meta, sort_keys=True)}")
        uncertainty_manager.try_confirm(job.current_state)
        auto_note = uncertainty_manager.auto_confirm_default_candidate()
        if auto_note:
            messages.append({"role": "assistant", "content": auto_note})

        # Log to platform (optional but good practice)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        api.log_llm(
            task_id=task.task_id,
            model=llm.model,
            duration_sec=meta["latency_ms"] / 1000.0,
            completion=job.model_dump_json(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        if isinstance(job.function, ReportTaskCompletion):
            if uncertainty_manager.needs_confirmation():
                error_msg = "Uncertainty guard: confirm which candidate interpretation to follow."
                logger.warning(error_msg)
                tool_result = wrap_tool_result(
                    tool="report_completion",
                    error=error_msg,
                )
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    job.function.__class__.__name__,
                    job.function.model_dump_json(),
                    tool_result,
                )
                reminder = uncertainty_manager.reminder_message()
                if reminder:
                    messages.append({"role": "assistant", "content": reminder})
                continue
            coupon_allowed, coupon_reason = store_guard.coupon_allows_checkout()
            if not coupon_allowed:
                error_msg = coupon_reason or "Coupon guard: invalid coupon prevents completion."
                logger.warning(error_msg)
                tool_result = wrap_tool_result(
                    tool="report_completion",
                    error=error_msg,
                )
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    job.function.__class__.__name__,
                    job.function.model_dump_json(),
                    tool_result,
                )
                if coupon_reason:
                    messages.append({"role": "assistant", "content": coupon_reason})
                continue
            if not store_guard.checkout_done:
                error_msg = "Invariant violation: checkout required before reporting completion."
                logger.warning(error_msg)
                tool_result = wrap_tool_result(
                    tool="report_completion",
                    error=error_msg,
                )
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    job.function.__class__.__name__,
                    job.function.model_dump_json(),
                    tool_result,
                )
                continue
            if not validation_tracker.has_successful_validation():
                error_msg = "Validation guard: run a deterministic check before reporting completion."
                logger.warning(error_msg)
                tool_result = wrap_tool_result(
                    tool="report_completion",
                    error=error_msg,
                )
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    job.function.__class__.__name__,
                    job.function.model_dump_json(),
                    tool_result,
                )
                messages.append({"role": "assistant", "content": validation_tracker.validation_prompt()})
                continue
            logger.info(f"Agent reported completion: {job.function.code}")
            break

        logger.info(f"Thinking: {job.current_state}")
        logger.info(f"Action: {job.function.__class__.__name__}")

        # Execute
        try:
            if isinstance(job.function, Req_ComputeWithPython):
                logger.info(f"Executing Python: {job.function.code}")
                logger.info(f"Description: {job.function.description}")
                logger.info(f"Mode: {job.function.mode} intent: {job.function.intent}")

                exec_result = execute_python(
                    job.function.code,
                    python_context,
                    mode=job.function.mode,
                    intent=job.function.intent,
                )

                if exec_result["result"] is not None:
                    python_context["last_result"] = exec_result["result"]

                tool_result = wrap_tool_result(
                    tool="Req_ComputeWithPython",
                    result=exec_result["result"],
                    error=exec_result["error"],
                )
                validation_tracker.record(
                    job.function.mode,
                    job.function.intent,
                    tool_result.ok,
                    tool_result.error,
                    tool_result.result,
                )
                logger.info(f"Python Result: {tool_result.model_dump_json()}")

                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    "Req_ComputeWithPython",
                    job.function.model_dump_json(),
                    tool_result,
                )
                hint = _python_error_hint(tool_result.error)
                if hint:
                    messages.append({"role": "assistant", "content": hint})
            elif isinstance(job.function, Req_ParseStructured):
                parsed = parse_structured_data(
                    raw_text=job.function.data,
                    fmt=job.function.format,
                    delimiter=job.function.delimiter,
                    column_names=job.function.column_names,
                    schema=job.function.schema,
                )
                result_model = ParseStructuredResult(
                    parsed=parsed.parsed,
                    warnings=parsed.warnings,
                )
                tool_result = wrap_tool_result(
                    tool="Req_ParseStructured",
                    result=result_model.model_dump(),
                )
                logger.info(f"Parsed Structure: {tool_result.model_dump_json()}")
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    "Req_ParseStructured",
                    job.function.model_dump_json(),
                    tool_result,
                )
            else:
                if isinstance(job.function, store.Req_AddProductToBasket):
                    inventory_adj = store_guard.adjust_inventory_for_add(job.function)
                    if inventory_adj.message:
                        messages.append({"role": "assistant", "content": inventory_adj.message})
                    if inventory_adj.quantity is not None:
                        job.function.quantity = inventory_adj.quantity
                    if inventory_adj.blocked:
                        error_msg = inventory_adj.message or "Inventory guard blocked the add operation."
                        logger.warning(error_msg)
                        tool_result = wrap_tool_result(
                            tool=job.function.__class__.__name__,
                            error=error_msg,
                        )
                        append_tool_history(
                            messages,
                            f"step_{i}",
                            job.current_state,
                            job.function.__class__.__name__,
                            job.function.model_dump_json(),
                            tool_result,
                        )
                        continue
                if isinstance(job.function, store.Req_CheckoutBasket):
                    allowed, coupon_reason = store_guard.coupon_allows_checkout()
                    if not allowed:
                        error_msg = coupon_reason or "Coupon guard prevented checkout."
                        logger.warning(error_msg)
                        tool_result = wrap_tool_result(
                            tool=job.function.__class__.__name__,
                            error=error_msg,
                        )
                        append_tool_history(
                            messages,
                            f"step_{i}",
                            job.current_state,
                            job.function.__class__.__name__,
                            job.function.model_dump_json(),
                            tool_result,
                        )
                        if coupon_reason:
                            messages.append({"role": "assistant", "content": coupon_reason})
                        continue
                result = store_guard.dispatch(job.function)
                payload = result.model_dump()
                python_context["last_result"] = payload
                tool_result = wrap_tool_result(
                    tool=job.function.__class__.__name__,
                    result=payload,
                )
                logger.info(f"Result: {tool_result.model_dump_json()}")

                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    job.function.__class__.__name__,
                    job.function.model_dump_json(),
                    tool_result,
                )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error: {error_msg}")
            tool_result = wrap_tool_result(
                tool=job.function.__class__.__name__,
                error=error_msg,
            )
            append_tool_history(
                messages,
                f"step_{i}",
                job.current_state,
                job.function.__class__.__name__,
                job.function.model_dump_json(),
                tool_result,
            )

    logger.info("Task finished.")
    if step_metrics:
        latencies = sorted(m["latency_ms"] for m in step_metrics)
        p95_index = int(0.95 * (len(latencies) - 1)) if len(latencies) > 1 else 0
        validation_records = [
            rec
            for rec in validation_tracker.records
            if rec.get("mode") == "validation"
        ]
        total_validations = len(validation_records)
        successful_validations = sum(1 for rec in validation_records if rec.get("ok"))
        success_rate = (
            successful_validations / total_validations if total_validations else 0.0
        )
        if validation_records:
            logger.info(
                f"Validation records: {json.dumps(validation_records, sort_keys=True)}"
            )
        summary = {
            "steps": len(step_metrics),
            "json_valid_first_try_rate": sum(1 for m in step_metrics if m["json_valid_first_try"]) / len(step_metrics),
            "retry_rate": sum(1 for m in step_metrics if m["recovered_by"] == "retry") / len(step_metrics),
            "repair_rate": sum(1 for m in step_metrics if m["recovered_by"] == "repair") / len(step_metrics),
            "tool_fallback_rate": sum(1 for m in step_metrics if m["recovered_by"] == "tool_fallback") / len(step_metrics),
            "avg_latency_ms": int(sum(latencies) / len(latencies)),
            "p95_latency_ms": latencies[p95_index],
            "prompt_tokens_total": sum(m["prompt_tokens_total"] for m in step_metrics),
            "completion_tokens_total": sum(m["completion_tokens_total"] for m in step_metrics),
            "schema_fallback_rate": sum(1 for m in step_metrics if m["schema_fallback"]) / len(step_metrics),
            "validation_attempts": total_validations,
            "validation_successful": successful_validations,
            "validation_success_rate": round(success_rate, 3),
        }
        logger.info(f"TASK_METRICS: {json.dumps(summary, sort_keys=True)}")
        return summary
    return None
