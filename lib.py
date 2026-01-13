import os
import time
import json
import re
import logging
from typing import List, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# AICODE-NOTE: NAV/LLM OpenRouter/OpenAI wrapper that forces schema-aligned JSON responses ref: lib.py

load_dotenv()
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class MyLLM:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("MODEL", "openai/gpt-4o-mini")
        self.temperature = float(os.getenv("TEMPERATURE", "0"))
        max_tokens = os.getenv("MAX_TOKENS")
        self.max_tokens = int(max_tokens) if max_tokens else None
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

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
