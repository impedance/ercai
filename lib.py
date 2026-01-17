import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, List, Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

# AICODE-NOTE: NAV/LLM OpenRouter/OpenAI wrapper that forces schema-aligned JSON responses ref: lib.py

load_dotenv()
logger = logging.getLogger(__name__)
CEREBRAS_RATE_LIMITS_FILE = Path(__file__).resolve().parent / "docs" / "cerebras-rate-limits.json"

T = TypeVar("T", bound=BaseModel)


class RateLimiter:
    """Throttles requests across sliding windows (minute/hour/day) for the LLM client."""

    def __init__(self, *, minute: int | None = None, hour: int | None = None, day: int | None = None, delay_seconds: float | None = None):
        self._windows: list[tuple[str, int, float]] = []
        if minute:
            self._windows.append(("minute", minute, 60.0))
        if hour:
            self._windows.append(("hour", hour, 3600.0))
        if day:
            self._windows.append(("day", day, 86400.0))
        self._queues = [deque() for _ in self._windows]
        self._lock = threading.Lock()
        self._delay_seconds = delay_seconds if delay_seconds and delay_seconds > 0 else None
        self._last_request: float | None = None

    def acquire(self):
        if not self._windows and not self._delay_seconds:
            return

        while True:
            now = time.monotonic()
            wait_time = 0.0
            window_wait = 0.0
            delay_wait = 0.0
            with self._lock:
                for queue, (_, limit, window) in zip(self._queues, self._windows):
                    cutoff = now - window
                    while queue and queue[0] <= cutoff:
                        queue.popleft()
                    if len(queue) >= limit:
                        earliest = queue[0]
                        window_wait = max(window_wait, earliest + window - now)
                if self._delay_seconds is not None and self._last_request is not None:
                    next_allowed = self._last_request + self._delay_seconds
                    if next_allowed > now:
                        delay_wait = next_allowed - now
                wait_time = max(window_wait, delay_wait)
                if wait_time <= 0:
                    for queue in self._queues:
                        queue.append(now)
                    self._last_request = now
                    return
            if wait_time > 0:
                reasons = []
                if window_wait > 0:
                    reasons.append("quota windows")
                if delay_wait > 0:
                    reasons.append("inter-request delay")
                reason_description = " and ".join(reasons) if reasons else "rate limits"
                logger.info(
                    "Waiting %.2fs to respect LLM quota (%s).",
                    wait_time,
                    reason_description,
                )
                time.sleep(wait_time)


def _coerce_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _coerce_positive_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_positive_int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    parsed = _coerce_positive_int(raw)
    if parsed is None:
        logger.warning("Ignoring invalid %s=%r; must be a positive integer.", name, raw)
        return default
    return parsed


def _parse_positive_float_env(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    parsed = _coerce_positive_float(raw)
    if parsed is None:
        logger.warning("Ignoring invalid %s=%r; must be a positive number.", name, raw)
        return default
    return parsed


def _load_cerebras_model_limits(model: str) -> dict[str, float | int | None]:
    if not model:
        return {}
    try:
        with open(CEREBRAS_RATE_LIMITS_FILE, encoding="utf-8") as limits_file:
            data = json.load(limits_file)
    except FileNotFoundError:
        logger.debug(
            "Cerebras rate limit registry %s is missing, defaulting to overrides only.", CEREBRAS_RATE_LIMITS_FILE
        )
        return {}
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse Cerebras rate limit registry %s: %s", CEREBRAS_RATE_LIMITS_FILE, exc
        )
        return {}
    defaults = data.get("defaults", {})
    normalized_defaults = {
        "minute": _coerce_positive_int(defaults.get("requests_per_minute")),
        "hour": _coerce_positive_int(defaults.get("requests_per_hour")),
        "day": _coerce_positive_int(defaults.get("requests_per_day")),
        "delay_seconds": _coerce_positive_float(defaults.get("delay_seconds")),
    }
    models = data.get("models", {})
    entry = models.get(model, {})
    if not entry:
        logger.info(
            "Cerebras rate limit registry %s has no entry for model %s; using defaults.", CEREBRAS_RATE_LIMITS_FILE, model
        )
    return {
        "minute": _coerce_positive_int(entry.get("requests_per_minute")) or normalized_defaults["minute"],
        "hour": _coerce_positive_int(entry.get("requests_per_hour")) or normalized_defaults["hour"],
        "day": _coerce_positive_int(entry.get("requests_per_day")) or normalized_defaults["day"],
        "delay_seconds": _coerce_positive_float(entry.get("delay_seconds")) or normalized_defaults["delay_seconds"],
    }

class MyLLM:
    def __init__(self):
        cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        if cerebras_api_key:
            self.provider = "cerebras"
            self.api_key = cerebras_api_key
            self.base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
            self.model = os.getenv("CEREBRAS_MODEL", "zai-glm-4.7")
            reason = "Cerebras API key detected; using Cerebras provider."
        else:
            self.provider = "openrouter"
            self.api_key = openrouter_api_key
            self.base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
            self.model = os.getenv("MODEL", "openai/gpt-4o-mini")
            reason = "Cerebras API key missing; falling back to OpenRouter provider."

        key_configured = bool(self.api_key)
        logger.info(
            "LLM provider selected: %s (model=%s, base_url=%s, key_configured=%s). %s",
            self.provider,
            self.model,
            self.base_url,
            key_configured,
            reason,
        )

        if not self.api_key:
            logger.warning(
                "LLM provider %s has no API key configured; requests may fail.", self.provider
            )

        self.temperature = float(os.getenv("TEMPERATURE", "0"))
        max_tokens = os.getenv("MAX_TOKENS")
        self.max_tokens = int(max_tokens) if max_tokens else None
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        model_limits: dict[str, float | int | None] = {}
        if self.provider == "cerebras":
            model_limits = _load_cerebras_model_limits(self.model)
        minute_limit = _parse_positive_int_env("LLM_REQUESTS_PER_MINUTE", model_limits.get("minute"))
        hour_limit = _parse_positive_int_env("LLM_REQUESTS_PER_HOUR", model_limits.get("hour"))
        day_limit = _parse_positive_int_env("LLM_REQUESTS_PER_DAY", model_limits.get("day"))
        delay_seconds = _parse_positive_float_env("LLM_REQUEST_DELAY", model_limits.get("delay_seconds"))
        if self.provider == "cerebras":
            logger.info(
                "Cerebras rate limiter configured for %s: minute=%s, hour=%s, day=%s, delay=%s.",
                self.model,
                minute_limit,
                hour_limit,
                day_limit,
                delay_seconds,
            )
        self.rate_limiter = RateLimiter(
            minute=minute_limit,
            hour=hour_limit,
            day=day_limit,
            delay_seconds=delay_seconds,
        )

    def check_schema_capability(self, response_format: Type[T], logger: logging.Logger) -> bool:
        messages = [
            {
                "role": "system",
                "content": "You are running a schema compliance check. Reply with JSON only.",
            },
            {
                "role": "user",
                "content": (
                    "Return a minimal valid JSON object for the schema. "
                    "If the schema includes a completion tool, use it."
                ),
            },
        ]
        try:
            parsed, _, meta = self.query(messages, response_format)
            if not meta.get("json_valid_first_try", True):
                logger.warning(
                    "Model schema check required recovery; tool calls may be unstable."
                )
            return isinstance(parsed, response_format)
        except Exception as exc:
            logger.warning(f"Model schema capability check failed: {exc}")
            return False

    def _create_completion(self, messages: List, response_format: dict):
        self.rate_limiter.acquire()
        kwargs = {
            "model": self.model,
            "messages": messages,
            "response_format": response_format,
            "temperature": self.temperature,
            "extra_headers": {
                "HTTP-Referer": "https://erc.timetoact-group.at",
                "X-Title": "Antigravity ERC Agent",
            },
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        return self.client.chat.completions.create(**kwargs)

    def _extract_json_object(self, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _repair_json(self, schema_json: dict, bad_content: str):
        repair_messages = [
            {
                "role": "system",
                "content": "You repair invalid JSON. Return ONLY valid JSON matching the provided schema.",
            },
            {
                "role": "user",
                "content": (
                    "Schema:\n"
                    f"{json.dumps(schema_json)}\n\n"
                    "Bad output:\n"
                    f"{bad_content}\n\n"
                    "Return only corrected JSON."
                ),
            },
        ]
        repair_resp = self._create_completion(
            messages=repair_messages,
            response_format={"type": "json_object"},
        )
        return (repair_resp.choices[0].message.content or ""), repair_resp.usage

    @staticmethod
    def _is_plan_length_error(exc: ValidationError) -> bool:
        for issue in exc.errors():
            loc = issue.get("loc", ())
            if loc and loc[0] == "plan" and issue.get("type") == "value_error.list.max_items":
                return True
        return False

    def query(self, messages: List, response_format: Type[T]) -> T:
        started = time.time()
        parse_attempts = {
            "initial_schema": 0,
            "retry_schema": 0,
            "repair": 0,
            "tool_fallback": 0,
        }
        total_prompt_tokens = 0
        total_completion_tokens = 0
        valid_first_try = True
        recovered_by = "initial"
        extracted_json = False
        response_format_mode = "json_schema"
        schema_fallback = False

        def _accumulate_usage(usage):
            nonlocal total_prompt_tokens, total_completion_tokens
            if usage:
                total_prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
                total_completion_tokens += getattr(usage, "completion_tokens", 0) or 0

        # Add a hint to messages to be strictly JSON
        schema_json = response_format.model_json_schema()
        json_hint = f"\n\nCRITICAL: Return ONLY valid JSON matching this schema: {json.dumps(schema_json)}. No conversational filler, no markdown backticks, no other text."

        # Always append a user message with the JSON schema hint
        messages_with_hint = messages.copy()
        messages_with_hint.insert(0, {
            "role": "system",
            "content": "Return ONLY valid JSON. No markdown, no prose, no extra keys.",
        })
        messages_with_hint.append({
            "role": "user",
            "content": json_hint
        })

        schema_response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_format.__name__,
                "schema": schema_json,
                "strict": True,
            },
        }

        def _retry_plan_length_hint():
            reminder_messages = messages_with_hint.copy()
            reminder_messages.append({
                "role": "user",
                "content": "plan<=5",
            })
            retry_response_format = schema_response_format
            if schema_fallback:
                retry_response_format = {"type": "json_object"}
            retry_resp = self._create_completion(
                messages=reminder_messages,
                response_format=retry_response_format,
            )
            _accumulate_usage(retry_resp.usage)
            retry_content = retry_resp.choices[0].message.content or ""
            extracted_retry = self._extract_json_object(retry_content)
            json_extracted_after_retry = extracted_json or bool(extracted_retry)
            if extracted_retry:
                retry_content = extracted_retry
            parse_attempts["retry_schema"] += 1
            parsed_retry = response_format.model_validate_json(retry_content)
            recovered_by_retry = "retry"
            meta_retry = {
                "model": self.model,
                "latency_ms": int((time.time() - started) * 1000),
                "prompt_tokens_total": total_prompt_tokens,
                "completion_tokens_total": total_completion_tokens,
                "json_valid_first_try": valid_first_try,
                "recovered_by": recovered_by_retry,
                "parse_attempts": parse_attempts,
                "response_format": response_format_mode,
                "json_extracted": json_extracted_after_retry,
                "schema_fallback": schema_fallback,
            }
            return parsed_retry, retry_resp.usage, meta_retry
        try:
            resp = self._create_completion(
                messages=messages_with_hint,
                response_format=schema_response_format,
            )
        except Exception as exc:
            logger.info(f"DEBUG: json_schema response_format failed, fallback to json_object: {exc}")
            response_format_mode = "json_object"
            schema_fallback = True
            resp = self._create_completion(
                messages=messages_with_hint,
                response_format={"type": "json_object"},
            )
        _accumulate_usage(resp.usage)
        
        content = resp.choices[0].message.content or ""
        # AICODE-TRAP: TRAP/JSON_EXTRACTION heuristics can misinterpret braces when the model adds extra text [2025-01-01]
        # Extract the first complete JSON object to avoid brace heuristics.
        extracted = self._extract_json_object(content)
        if extracted:
            content = extracted
            extracted_json = True
            
        try:
            parse_attempts["initial_schema"] += 1
            parsed = response_format.model_validate_json(content)
        except Exception as e:
            valid_first_try = False
            if isinstance(e, ValidationError) and self._is_plan_length_error(e):
                logger.info("DEBUG: Plan exceeded allowed length; retrying with plan<=5 reminder.")
                try:
                    return _retry_plan_length_hint()
                except Exception as retry_exc:  # pragma: no cover - best effort
                    logger.info(
                        "DEBUG: Plan-length reminder retry failed, falling back to other recovery: %s",
                        retry_exc,
                    )
            logger.info("DEBUG: Schema validation failed, trying repair and tool extraction...")
            try:
                parse_attempts["retry_schema"] += 1
                retry_messages = messages_with_hint.copy()
                retry_messages.append({
                    "role": "user",
                    "content": "Your last response was invalid JSON. Return ONLY valid JSON for the schema.",
                })
                retry_response_format = schema_response_format
                if schema_fallback:
                    retry_response_format = {"type": "json_object"}
                retry_resp = self._create_completion(
                    messages=retry_messages,
                    response_format=retry_response_format,
                )
                _accumulate_usage(retry_resp.usage)
                retry_content = retry_resp.choices[0].message.content or ""
                extracted_retry = self._extract_json_object(retry_content)
                if extracted_retry:
                    retry_content = extracted_retry
                parsed = response_format.model_validate_json(retry_content)
                recovered_by = "retry"
                if parse_attempts["retry_schema"]:
                    logger.info(f"DEBUG: JSON recovered on retry {parse_attempts}")
                meta = {
                    "model": self.model,
                    "latency_ms": int((time.time() - started) * 1000),
                    "prompt_tokens_total": total_prompt_tokens,
                    "completion_tokens_total": total_completion_tokens,
                    "json_valid_first_try": valid_first_try,
                    "recovered_by": recovered_by,
                    "parse_attempts": parse_attempts,
                    "response_format": response_format_mode,
                    "json_extracted": extracted_json,
                    "schema_fallback": schema_fallback,
                }
                return parsed, resp.usage, meta
            except Exception:
                pass
            try:
                parse_attempts["repair"] += 1
                repaired, repair_usage = self._repair_json(schema_json, content)
                _accumulate_usage(repair_usage)
                parsed = response_format.model_validate_json(repaired)
                recovered_by = "repair"
                logger.info(f"DEBUG: JSON recovered via repair {parse_attempts}")
                meta = {
                    "model": self.model,
                    "latency_ms": int((time.time() - started) * 1000),
                    "prompt_tokens_total": total_prompt_tokens,
                    "completion_tokens_total": total_completion_tokens,
                    "json_valid_first_try": valid_first_try,
                    "recovered_by": recovered_by,
                    "parse_attempts": parse_attempts,
                    "response_format": response_format_mode,
                    "json_extracted": extracted_json,
                    "schema_fallback": schema_fallback,
                }
                return parsed, resp.usage, meta
            except Exception:
                pass
            # Fallback: Maybe it returned the tool directly?
            try:
                parse_attempts["tool_fallback"] += 1
                data = json.loads(content)
                from schemas import NextStep, ReportTaskCompletion

                if data.get("tool") == "report_completion":
                    obj = ReportTaskCompletion(**data)
                    parsed = NextStep(
                        current_state="Auto-extracted from direct return",
                        plan=["Directly returning tool"],
                        task_completed=True,
                        function=obj
                    )
                    recovered_by = "tool_fallback"
                else:
                    raise e
            except Exception:
                logger.info(f"DEBUG: Failed to parse JSON {parse_attempts}: {content}")
                raise e
        meta = {
            "model": self.model,
            "latency_ms": int((time.time() - started) * 1000),
            "prompt_tokens_total": total_prompt_tokens,
            "completion_tokens_total": total_completion_tokens,
            "json_valid_first_try": valid_first_try,
            "recovered_by": recovered_by,
            "parse_attempts": parse_attempts,
            "response_format": response_format_mode,
            "json_extracted": extracted_json,
            "schema_fallback": schema_fallback,
        }
        return parsed, resp.usage, meta
