import json
from typing import Any, Dict

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
from store_helpers import CouponVerifier, PaginationGuard, normalize_basket_view

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

Python context:
- Previous results available as 'last_result'
- All string methods available: .split(), .join(), .upper(), .lower(), [::-1], etc.
- Standard operators: +, -, *, /, //, %, **
- Functions: len(), sorted(), reversed(), sum(), max(), min(), etc.
- Python executions time out quickly and results longer than ~1,024 characters raise an error

IMPORTANT:
    - Always record why Python code is running in the 'description' field
    - Stick to the plan outlined in each step and re-evaluate if the basket changes unexpectedly
    - Return to ReportTaskCompletion as soon as the task is satisfied
"""


class _PayloadWrapper:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload or {}

    def model_dump(self) -> Dict[str, Any]:
        return self._payload


class StoreGuard:
    def __init__(self, client, logger) -> None:
        self.client = client
        self.logger = logger
        self.pagination = PaginationGuard(logger=logger)
        self.coupon_verifier = CouponVerifier(logger=logger)
        self.checkout_done = False

    def dispatch(self, request):
        if isinstance(request, store.Req_ListProducts):
            return self._handle_list_products(request)
        if isinstance(request, store.Req_ViewBasket):
            return self._normalize_view(request)
        if isinstance(request, store.Req_ApplyCoupon):
            return self._handle_apply_coupon(request)
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
        return _PayloadWrapper(aggregated)

    def _normalize_view(self, request):
        resp = self.client.dispatch(request)
        normalized = normalize_basket_view(resp.model_dump())
        return _PayloadWrapper(normalized)

    def _handle_apply_coupon(self, request):
        coupon_code = getattr(request, "coupon_code", None) or getattr(request, "code", None) or "unknown"
        resp = self.client.dispatch(request)
        basket_resp = self.client.dispatch(store.Req_ViewBasket())
        normalized = normalize_basket_view(basket_resp.model_dump())
        accepted, reason = self.coupon_verifier.evaluate(coupon_code, normalized)
        if not accepted:
            self.logger.warning(f"Coupon verification flagged {coupon_code}: {reason}")
        return _PayloadWrapper(normalized)


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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task ID: {task.task_id}\nTask Description: {task.task_text}"}
    ]

    logger.info(f"Starting agent for task: {task.task_id}")

        for i in range(10):
            logger.info(f"--- Step {i+1} ---")
            job, usage, meta = llm.query(messages, NextStep)
            step_metrics.append(meta)
            logger.info(f"METRICS: {json.dumps(meta, sort_keys=True)}")

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
            logger.info(f"Agent reported completion: {job.function.code}")
            break

        logger.info(f"Thinking: {job.current_state}")
        logger.info(f"Action: {job.function.__class__.__name__}")

        # Execute
        try:
            if isinstance(job.function, Req_ComputeWithPython):
                logger.info(f"Executing Python: {job.function.code}")
                logger.info(f"Description: {job.function.description}")

                # Execute in sandboxed environment
                exec_result = execute_python(job.function.code, python_context)

                if exec_result["result"] is not None:
                    python_context['last_result'] = exec_result["result"]

                tool_result = wrap_tool_result(
                    tool="Req_ComputeWithPython",
                    result=exec_result["result"],
                    error=exec_result["error"],
                )
                logger.info(f"Python Result: {tool_result.model_dump_json()}")

                # Add to history
                append_tool_history(
                    messages,
                    f"step_{i}",
                    job.current_state,
                    "Req_ComputeWithPython",
                    job.function.model_dump_json(),
                    tool_result,
                )
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
                result = store_guard.dispatch(job.function)
                payload = result.model_dump()
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
        }
        logger.info(f"TASK_METRICS: {json.dumps(summary, sort_keys=True)}")
        return summary
    return None
