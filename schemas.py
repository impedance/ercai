from typing import List, Union, Literal, Annotated
from pydantic import BaseModel, Field
from annotated_types import MaxLen, MinLen
from erc3 import demo

class ReportTaskCompletion(BaseModel):
    tool: Literal["report_completion"]
    completed_steps: List[str]
    code: Literal["completed", "failed"]

class NextStep(BaseModel):
    current_state: str
    plan: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(..., description="Your plan to reach the goal")
    task_completed: bool
    function: Union[
        ReportTaskCompletion,
        demo.Req_GetSecret,
        demo.Req_ProvideAnswer
    ] = Field(..., description="The next tool to call")
