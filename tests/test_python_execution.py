"""
Unit tests for the Python execution helper in python_executor.py
"""

import os
import sys
import time

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from python_executor import (
    MAX_OUTPUT_LENGTH,
    PYTHON_EXECUTION_TIMEOUT,
    execute_python,
)


def test_string_reversal():
    result = execute_python("'abc123'[::-1]", {})
    assert result["result"] == "321cba"
    assert result["error"] is None


def test_list_indexing():
    result = execute_python("'a,b,c'.split(',')[1]", {})
    assert result["result"] == "b"
    assert result["error"] is None


def test_mathematical_operations():
    result = execute_python("(10 + 5) * 2", {})
    assert result["result"] == "30"
    assert result["error"] is None


def test_string_methods():
    result = execute_python("'Hello World'.upper()", {})
    assert result["result"] == "HELLO WORLD"
    assert result["error"] is None


def test_context_persistence():
    context = {}
    result1 = execute_python("'test'", context)
    context["last_result"] = result1["result"]
    result2 = execute_python("last_result + '_suffix'", context)
    assert result2["result"] == "test_suffix"
    assert result2["error"] is None


def test_security_no_imports():
    result = execute_python("__import__('os').system('echo oops')", {})
    assert result["error"] is not None
    assert "NameError" in result["error"]


def test_security_no_file_access():
    result = execute_python("open('/etc/passwd', 'r')", {})
    assert result["error"] is not None
    assert "NameError" in result["error"]


def test_invalid_syntax():
    result = execute_python("'abc'[", {})
    assert result["error"] is not None
    assert "SyntaxError" in result["error"]


def test_safe_builtins():
    result = execute_python("len('hello')", {})
    assert result["result"] == "5"
    assert result["error"] is None

    result = execute_python("max([1, 5, 3])", {})
    assert result["result"] == "5"
    assert result["error"] is None

    result = execute_python("sorted([3, 1, 2])", {})
    assert result["result"] == "[1, 2, 3]"
    assert result["error"] is None


def test_output_length_limit():
    long_expr = f"'x' * ({MAX_OUTPUT_LENGTH} + 10)"
    result = execute_python(long_expr, {})
    assert result["error"] and "OutputTooLong" in result["error"]
    assert result["result"] is None


class SlowObject:
    def run(self):
        time.sleep(PYTHON_EXECUTION_TIMEOUT * 2)
        return "done"


def test_timeout_enforced():
    context = {"slow": SlowObject()}
    result = execute_python("slow.run()", context)
    assert result["error"] and "Timeout" in result["error"]
    assert result["result"] is None


def test_spec2_scenario():
    secret = "NcS9euQa"
    result = execute_python(f"'{secret}'[::-1]", {})
    expected = "aQue9ScN"
    assert result["result"] == expected
    assert result["error"] is None
    assert len(result["result"]) == len(secret)


def run_all_tests():
    tests = [
        test_string_reversal,
        test_list_indexing,
        test_mathematical_operations,
        test_string_methods,
        test_context_persistence,
        test_security_no_imports,
        test_security_no_file_access,
        test_invalid_syntax,
        test_safe_builtins,
        test_output_length_limit,
        test_timeout_enforced,
        test_spec2_scenario,
    ]
    for test in tests:
        test()


if __name__ == "__main__":
    print("Running Python execution engine tests...\n")
    run_all_tests()
    print("\n✅ All tests passed!")
