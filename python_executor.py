import ast
import concurrent.futures
from typing import Any, Dict

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


def execute_python(code: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a sandboxed expression safely.

    The expression is parsed to ensure it is valid `eval` syntax, then executed with tightly
    controlled builtins, a bounded timeout, and an output-length cap to avoid runaway results.
    """
    try:
        tree = ast.parse(code, mode="eval")
        compiled = compile(tree, "<agent_code>", "eval")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(eval, compiled, {"__builtins__": SAFE_BUILTINS}, context)
            raw_result = future.result(timeout=PYTHON_EXECUTION_TIMEOUT)

        string_result = str(raw_result)
        if len(string_result) > MAX_OUTPUT_LENGTH:
            error = (
                f"OutputTooLong: result length {len(string_result)} exceeds "
                f"max {MAX_OUTPUT_LENGTH}"
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
