import ast
import concurrent.futures
from typing import Any, Dict, Optional

SAFE_BUILTINS: Dict[str, Any] = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "reversed": reversed,
    "sorted": sorted,
    "enumerate": enumerate,
    "sum": sum,
    "max": max,
    "min": min,
    "abs": abs,
    "round": round,
    "range": range,
    "zip": zip,
    "map": map,
    "filter": filter,
}

# Execution constraints
PYTHON_EXECUTION_TIMEOUT = 0.2
MAX_OUTPUT_LENGTH = 1024
VALIDATION_MAX_OUTPUT_LENGTH = 256


def execute_python(
    code: str,
    context: Dict[str, Any],
    mode: str = "analysis",
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate a sandboxed expression safely.

    The expression is parsed to ensure it is valid `eval` syntax, then executed with tightly
    controlled builtins, a bounded timeout, and an output-length cap to avoid runaway results.
    The `mode`/`intent` flags describe whether the execution is for analysis or a validation
    guard, which the caller can use to enforce shorter outputs or clearer logging.
    """
    try:
        tree = ast.parse(code, mode="eval")
        compiled = compile(tree, "<agent_code>", "eval")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(eval, compiled, {"__builtins__": SAFE_BUILTINS}, context)
            raw_result = future.result(timeout=PYTHON_EXECUTION_TIMEOUT)

        string_result = str(raw_result)
        limit = MAX_OUTPUT_LENGTH
        if mode == "validation":
            limit = min(MAX_OUTPUT_LENGTH, VALIDATION_MAX_OUTPUT_LENGTH)
        if len(string_result) > limit:
            error = (
                f"OutputTooLong: result length {len(string_result)} exceeds limit {limit} "
                f"for mode={mode} intent={intent or 'none'}"
            )
            return {"result": None, "error": error}

        return {"result": string_result, "error": None}
    except concurrent.futures.TimeoutError:
        return {
            "result": None,
            "error": f"PythonError: Timeout after {PYTHON_EXECUTION_TIMEOUT:.2f}s",
        }
    except Exception as exc:
        return {"result": None, "error": f"PythonError: {type(exc).__name__}: {exc}"}
