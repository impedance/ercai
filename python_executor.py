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
    "print": print,
    "bool": bool,
    "any": any,
    "all": all,
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
    Evaluate a sandboxed single-line statement safely.

    The expression is parsed to ensure it is a single statement, then executed with tightly
    controlled builtins, a bounded timeout, and an output-length cap to avoid runaway results.
    The `mode`/`intent` flags describe whether the execution is for analysis or a validation
    guard, which the caller can use to enforce shorter outputs or clearer logging.
    """
    stripped_code = code.strip()
    if not stripped_code:
        return {
            "result": None,
            "error": "PythonError: Code must contain a single, non-empty statement.",
        }
    if "\n" in stripped_code:
        return {
            "result": None,
            "error": "PythonError: Only single-line statements are allowed.",
        }

    try:
        tree = ast.parse(stripped_code, mode="exec")
        if len(tree.body) != 1:
            return {
                "result": None,
                "error": "PythonError: Only one single-line statement is permitted.",
            }
        statement = tree.body[0]
        globals_map = {"__builtins__": SAFE_BUILTINS}
        if isinstance(statement, ast.Expr):
            compiled = compile(ast.Expression(statement.value), "<agent_code>", "eval")

            def execute_callable() -> Any:
                return eval(compiled, globals_map, context)
        else:
            compiled = compile(tree, "<agent_code>", "exec")

            def execute_callable() -> Any:
                exec(compiled, globals_map, context)
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(execute_callable)
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
