import os
import time
import json
import re
from typing import List, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# AICODE-NOTE: NAV/LLM OpenRouter/OpenAI wrapper that forces schema-aligned JSON responses ref: lib.py

load_dotenv()

T = TypeVar("T", bound=BaseModel)

class MyLLM:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("MODEL", "openai/gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def query(self, messages: List, response_format: Type[T]) -> T:
        started = time.time()

        # Add a hint to messages to be strictly JSON
        schema_json = response_format.model_json_schema()
        json_hint = f"\n\nCRITICAL: Return ONLY valid JSON matching this schema: {json.dumps(schema_json)}. No conversational filler, no markdown backticks, no other text."

        # Always append a user message with the JSON schema hint
        messages_with_hint = messages.copy()
        messages_with_hint.append({
            "role": "user",
            "content": json_hint
        })

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages_with_hint,
            response_format={"type": "json_object"}, # Some providers support this
            extra_headers={
                "HTTP-Referer": "https://erc.timetoact-group.at",
                "X-Title": "Antigravity ERC Agent",
            }
        )
        
        content = resp.choices[0].message.content
        # AICODE-TRAP: TRAP/JSON_EXTRACTION heuristics can misinterpret braces when the model adds extra text [2025-01-01]
        # Basic cleanup in case model adds artifacts
        
        # Look for the first { and the last }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
            
        try:
            parsed = response_format.model_validate_json(content)
        except Exception as e:
            # Fallback: Maybe it returned the tool directly?
            print(f"DEBUG: Schema validation failed, trying tool extraction...")
            try:
                data = json.loads(content)
                from schemas import NextStep, ReportTaskCompletion
                from erc3 import demo
                
                # If it looks like ReportTaskCompletion or a tool, wrap it in NextStep
                if "tool" in data or "tool_code" in data or "answer" in data:
                    if data.get("tool") == "report_completion":
                        obj = ReportTaskCompletion(**data)
                    elif "secret" in content.lower() or "getsecret" in content.lower():
                        obj = demo.Req_GetSecret()
                    elif "answer" in data:
                        obj = demo.Req_ProvideAnswer(**data)
                    else:
                        raise e
                    
                    parsed = NextStep(
                        current_state="Auto-extracted from direct return",
                        plan=["Directly returning tool"],
                        task_completed=getattr(obj, "tool", "") == "report_completion",
                        function=obj
                    )
                else:
                    raise e
            except Exception:
                print(f"DEBUG: Failed to parse JSON: {content}")
                raise e
        return parsed, resp.usage





