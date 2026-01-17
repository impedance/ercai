from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from schemas import NextStep


@dataclass
class FakeUsage:
    prompt_tokens: int = 1
    completion_tokens: int = 1


class FakeLLM:
    def __init__(
        self,
        steps: List[NextStep],
        metas: Optional[List[Dict[str, Any]]] = None,
        model_name: str = "fake-llm",
    ) -> None:
        self._steps = steps
        self._metas = metas or []
        self.message_history: List[List[str]] = []
        self.call_count = 0
        self.model = model_name

    def query(self, messages: List[Dict[str, Any]], response_format: Any) -> Any:
        self.message_history.append([message.get("content", "") for message in messages])
        idx = min(self.call_count, len(self._steps) - 1)
        step = self._steps[idx]
        base_meta = {
            "latency_ms": 5,
            "json_valid_first_try": True,
            "recovered_by": "initial",
            "prompt_tokens_total": 1,
            "completion_tokens_total": 1,
            "schema_fallback": False,
        }
        override = self._metas[idx] if idx < len(self._metas) else {}
        meta = {**base_meta, **override}
        usage = FakeUsage()
        self.call_count += 1
        return step, usage, meta


class FakeStoreResponse:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self._payload = payload or {}

    def model_dump(self) -> Dict[str, Any]:
        return self._payload


class FakeAPI:
    def __init__(self, store_client: Any) -> None:
        self._store_client = store_client
        self.logged_calls: List[Dict[str, Any]] = []

    def get_store_client(self, task: Any) -> Any:
        return self._store_client

    def log_llm(self, **kwargs: Any) -> None:
        self.logged_calls.append(kwargs)
