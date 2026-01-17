import logging

from agent import run_agent
from erc3 import TaskInfo, store
from schemas import NextStep

from tests.fake_llm import FakeAPI, FakeLLM, FakeStoreResponse


class BurnoutStoreClient:
    """Fake store client that fails checkout once and tracks add attempts."""

    def __init__(self) -> None:
        self.inventory = {"widget": 2}
        self.add_calls = []
        self.checkout_attempts = 0
        self.fail_first_checkout = True

    def dispatch(self, request):
        if isinstance(request, store.Req_ListProducts):
            products = [
                {"sku": "widget", "available": self.inventory["widget"]}
            ]
            return FakeStoreResponse({"products": products, "next_offset": -1})
        if isinstance(request, store.Req_ViewBasket):
            return FakeStoreResponse({"items": []})
        if isinstance(request, store.Req_AddProductToBasket):
            payload = request.model_dump()
            self.add_calls.append(payload)
            return FakeStoreResponse({"line_count": 1, "item_count": payload["quantity"]})
        if isinstance(request, store.Req_CheckoutBasket):
            self.checkout_attempts += 1
            if self.fail_first_checkout and self.checkout_attempts == 1:
                raise RuntimeError("inventory shortfall")
            return FakeStoreResponse({"status": "checked_out"})
        return FakeStoreResponse({})


def _next_step(function, state="task", plan=None):
    return NextStep(
        current_state=state,
        plan=plan or ["execute step"],
        task_completed=False,
        function=function,
    )


def test_checkout_retry_retries_after_inventory_shortfall():
    """
    Plan step: inventory guard should lower add quantity and the agent retries checkout after
    a transient inventory shortfall.
    """
    client = BurnoutStoreClient()
    steps = [
        _next_step(store.Req_ListProducts()),
        _next_step(store.Req_AddProductToBasket(sku="widget", quantity=5)),
        _next_step(store.Req_CheckoutBasket()),
        _next_step(store.Req_CheckoutBasket()),
        _next_step(store.Req_ViewBasket()),
    ]
    llm = FakeLLM(steps)
    task = TaskInfo(task_id="checkout-retry", task_text="Purchase the widget.")
    summary = run_agent(llm, FakeAPI(client), task, logging.getLogger("test_checkout_retry"))

    assert client.add_calls, "Add product should be attempted"
    assert client.add_calls[-1]["quantity"] == 2
    assert client.checkout_attempts >= 2
    assert isinstance(summary, dict)
