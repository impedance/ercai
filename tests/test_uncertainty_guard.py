import logging

from agent import UncertaintyManager, run_agent
from erc3 import TaskInfo, store
from schemas import NextStep, ReportTaskCompletion

from tests.fake_llm import FakeAPI, FakeLLM, FakeStoreResponse


class ReadOnlyStoreClient:
    """Minimal store client used to exercise the uncertainty guard flow."""

    def dispatch(self, request):
        if isinstance(request, store.Req_ViewBasket):
            return FakeStoreResponse({"items": []})
        return FakeStoreResponse({})


def _next_step(function, state="ambiguous step", plan=None):
    return NextStep(
        current_state=state,
        plan=plan or ["handle ambiguity"],
        task_completed=False,
        function=function,
    )


def test_uncertainty_guard_prompts_before_completion():
    """
    Plan step: an ambiguous task should trigger the uncertainty reminder before ReportTaskCompletion
    can proceed.
    """
    steps = [
        _next_step(
            ReportTaskCompletion(
                tool="report_completion", completed_steps=["step"], code="completed"
            )
        ),
        _next_step(
            store.Req_ViewBasket(),
            state="Candidate 1 selected",
        ),
        _next_step(
            ReportTaskCompletion(
                tool="report_completion", completed_steps=["step"], code="completed"
            ),
        ),
    ]
    llm = FakeLLM(steps)
    task = TaskInfo(task_id="uncertainty", task_text="Decide between apples or bananas.")
    original_max = UncertaintyManager.MAX_PROMPTS
    UncertaintyManager.MAX_PROMPTS = 2
    try:
        run_agent(llm, FakeAPI(ReadOnlyStoreClient()), task, logging.getLogger("test_uncertainty_guard"))
    finally:
        UncertaintyManager.MAX_PROMPTS = original_max

    assert any("Ambiguous request detected" in msg for msg in llm.message_history[0])
    assert any(
        "Before wrapping up, please confirm a candidate interpretation" in msg
        for call in llm.message_history
        for msg in call
    )
