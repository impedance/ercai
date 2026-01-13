from typing import List, Union, Literal, Annotated
from pydantic import BaseModel, Field
from annotated_types import MaxLen, MinLen
from erc3 import demo, store

class ReportTaskCompletion(BaseModel):
    tool: Literal["report_completion"]
    completed_steps: List[str]
    code: Literal["completed", "failed"]

class Req_ComputeWithPython(BaseModel):
    """Execute Python code for precise algorithmic operations"""
    tool: Literal["compute_with_python"]
    code: str = Field(..., description="Python expression to evaluate")
    description: str = Field(..., description="Human-readable explanation of what this code does")

# AICODE-NOTE: NAV/STORE_SCHEMAS NextStep now routes to store tools + python ref: schemas.py
class NextStep(BaseModel):
    current_state: str
    plan: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(..., description="Your plan to reach the goal")
    task_completed: bool
    function: Union[
        ReportTaskCompletion,
        demo.Req_GetSecret,
        demo.Req_ProvideAnswer,
        store.Req_ListProducts,
        store.Req_ViewBasket,
        store.Req_ApplyCoupon,
        store.Req_RemoveCoupon,
        store.Req_AddProductToBasket,
        store.Req_RemoveItemFromBasket,
        store.Req_CheckoutBasket,
        Req_ComputeWithPython
    ] = Field(..., description="The next tool to call")
