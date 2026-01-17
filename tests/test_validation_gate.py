import logging

from agent import run_agent
from erc3 import TaskInfo, store
from schemas import NextStep, Req_ComputeWithPython, ReportTaskCompletion

from tests.fake_llm import FakeAPI, FakeLLM, FakeStoreResponse


class CheckoutStoreClient:
    """Minimal store client that always allows checkout."""

    def dispatch(self, request):
        if isinstance(request, store.Req_CheckoutBasket):
            return FakeStoreResponse({"status": "checked_out"})
        return FakeStoreResponse({})


def _next_step(function, state="validation step", plan=None):
    return NextStep(
        current_state=state,
        plan=plan or ["execute validation"],
        task_completed=False,
        function=function,
    )


def test_validation_guard_blocks_completion_until_py_validation():
    """
    Plan step: the validation tracker must insist on a `mode="validation"` python check before
    allowing ReportTaskCompletion to pass.
    """
    steps = [
        _next_step(store.Req_CheckoutBasket(), state="checkout completed"),
        _next_step(
            ReportTaskCompletion(
                tool="report_completion", completed_steps=["checkout"], code="completed"
            ),
            state="first completion attempt",
        ),
        _next_step(
            Req_ComputeWithPython(
                tool="compute_with_python",
                code="1+1",
                description="validation check",
                mode="validation",
                intent="sum check",
            ),
            state="validation guard satisfied",
        ),
        _next_step(
            ReportTaskCompletion(
                tool="report_completion", completed_steps=["validated"], code="completed"
            ),
            state="second completion attempt",
        ),
    ]
    llm = FakeLLM(steps)
    task = TaskInfo(task_id="validation-guard", task_text="Place an order.")
    summary = run_agent(
        llm,
        FakeAPI(CheckoutStoreClient()),
        task,
        logging.getLogger("test_validation_guard"),
    )

    assert any(
        "Please run `Req_ComputeWithPython` again with `mode=\"validation\"`"
        in msg
        for call in llm.message_history
        for msg in call
    )
    assert isinstance(summary, dict)
    assert summary.get("validation_successful", 0) >= 1
