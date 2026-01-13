from typing import Any, List, Union, Literal, Annotated, Optional
from pydantic import BaseModel, Field
from annotated_types import MaxLen, MinLen
from erc3 import store

class ReportTaskCompletion(BaseModel):
    tool: Literal["report_completion"]
    completed_steps: List[str]
    code: Literal["completed", "failed"]

class Req_ComputeWithPython(BaseModel):
    """Execute Python code for precise algorithmic operations"""
    tool: Literal["compute_with_python"]
    code: str = Field(..., description="Python expression to evaluate")
    description: str = Field(..., description="Human-readable explanation of what this code does")
    mode: Literal["analysis", "validation"] = Field(
        "analysis",
        description="Intended use of the computation to differentiate validation checks from planning steps",
    )
    intent: Optional[str] = Field(
        None,
        description="Optional tag describing the validation intent (e.g., 'length check', 'format enforcement').",
    )

# AICODE-NOTE: NAV/TOOL_RESULT Standard envelope for tool outputs ref: schemas.py
class ToolResultEnvelope(BaseModel):
    tool: str
    ok: bool = Field(..., description="Whether the tool call succeeded")
    result: Any | None = Field(
        None,
        description="Tool-specific payload (dict for STORE, string for deterministic helpers)",
    )
    error: str | None = Field(None, description="Error text when the call failed")

    class Config:
        extra = "forbid"


def wrap_tool_result(tool: str, result: Any | None = None, error: str | None = None) -> ToolResultEnvelope:
    """
    Normalize tool outputs so downstream logic sees a consistent envelope.
    """
    payload = result if error is None else None
    return ToolResultEnvelope(tool=tool, ok=error is None, result=payload, error=error)


def unwrap_tool_result(envelope: ToolResultEnvelope) -> Any | None:
    """Retrieve the original payload and let callers inspect success/failure."""
    return envelope.result

# AICODE-NOTE: NAV/STORE_SCHEMAS NextStep now routes to store tools + python ref: schemas.py
class ParseStructuredResult(BaseModel):
    parsed: List[Any]
    warnings: List[str] = Field(default_factory=list)


class Req_ParseStructured(BaseModel):
    tool: Literal["parse_structured"]
    data: str = Field(..., description="Raw text that needs to be parsed")
    format: Literal["json", "csv", "lines"] = Field(
        "json",
        description="Expected format of the input data",
    )
    delimiter: Optional[str] = Field(
        None,
        description="Delimiter used for csv/lines formats; newline is the default for lines",
    )
    column_names: Optional[List[str]] = Field(
        None,
        description="Column headers to apply for csv parsing when the payload lacks one",
    )
    schema: Optional[List[str]] = Field(
        None,
        description="Required keys that must appear on each parsed object",
    )


class NextStep(BaseModel):
    current_state: str
    plan: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(..., description="Your plan to reach the goal")
    task_completed: bool
    function: Union[
        ReportTaskCompletion,
        store.Req_ListProducts,
        store.Req_ViewBasket,
        store.Req_ApplyCoupon,
        store.Req_RemoveCoupon,
        store.Req_AddProductToBasket,
        store.Req_RemoveItemFromBasket,
        store.Req_CheckoutBasket,
        Req_ComputeWithPython,
        Req_ParseStructured,
    ] = Field(..., description="The next tool to call")
