"""
Unit tests for Python execution engine in agent.py
"""

import ast
from typing import Dict

# Duplicate the execute_python function here for testing without dependencies
SAFE_BUILTINS = {
    'len': len, 'str': str, 'int': int, 'float': float,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'reversed': reversed, 'sorted': sorted, 'enumerate': enumerate,
    'sum': sum, 'max': max, 'min': min, 'abs': abs, 'round': round,
    'range': range, 'zip': zip, 'map': map, 'filter': filter,
}

def execute_python(code: str, context: Dict) -> Dict:
    """
    Execute Python expression in sandboxed environment
    """
    try:
        # Parse to validate syntax
        tree = ast.parse(code, mode='eval')

        # Compile and execute with restricted globals
        compiled = compile(tree, '<agent_code>', 'eval')
        result = eval(compiled, {'__builtins__': SAFE_BUILTINS}, context)

        return {"result": str(result), "error": None}
    except Exception as e:
        return {"result": None, "error": f"PythonError: {type(e).__name__}: {str(e)}"}

def test_string_reversal():
    """Test basic string reversal using Python slicing"""
    result = execute_python("'abc123'[::-1]", {})
    assert result["result"] == "321cba"
    assert result["error"] is None
    print("✓ test_string_reversal passed")

def test_list_indexing():
    """Test string splitting and list indexing"""
    result = execute_python("'a,b,c'.split(',')[1]", {})
    assert result["result"] == "b"
    assert result["error"] is None
    print("✓ test_list_indexing passed")

def test_mathematical_operations():
    """Test basic mathematical operations"""
    result = execute_python("(10 + 5) * 2", {})
    assert result["result"] == "30"
    assert result["error"] is None
    print("✓ test_mathematical_operations passed")

def test_string_methods():
    """Test string methods like upper, lower"""
    result = execute_python("'Hello World'.upper()", {})
    assert result["result"] == "HELLO WORLD"
    assert result["error"] is None
    print("✓ test_string_methods passed")

def test_context_persistence():
    """Test that context is preserved across executions"""
    context = {}
    result1 = execute_python("'test'", context)
    context['last_result'] = result1["result"]
    result2 = execute_python("last_result + '_suffix'", context)
    assert result2["result"] == "test_suffix"
    assert result2["error"] is None
    print("✓ test_context_persistence passed")

def test_security_no_imports():
    """Test that imports are blocked"""
    result = execute_python("__import__('os').system('ls')", {})
    assert result["error"] is not None
    assert "NameError" in result["error"]
    print("✓ test_security_no_imports passed")

def test_security_no_file_access():
    """Test that file operations are blocked"""
    result = execute_python("open('/etc/passwd', 'r')", {})
    assert result["error"] is not None
    assert "NameError" in result["error"]
    print("✓ test_security_no_file_access passed")

def test_invalid_syntax():
    """Test that syntax errors are caught"""
    result = execute_python("'abc'[", {})
    assert result["error"] is not None
    assert "SyntaxError" in result["error"]
    print("✓ test_invalid_syntax passed")

def test_safe_builtins():
    """Test that safe builtins are available"""
    result = execute_python("len('hello')", {})
    assert result["result"] == "5"
    assert result["error"] is None

    result = execute_python("max([1, 5, 3])", {})
    assert result["result"] == "5"
    assert result["error"] is None

    result = execute_python("sorted([3, 1, 2])", {})
    assert result["result"] == "[1, 2, 3]"
    assert result["error"] is None
    print("✓ test_safe_builtins passed")

def test_spec2_scenario():
    """Test the actual spec2 scenario that was failing"""
    secret = "NcS9euQa"
    result = execute_python(f"'{secret}'[::-1]", {})
    expected = "aQue9ScN"
    assert result["result"] == expected
    assert result["error"] is None
    assert len(result["result"]) == len(secret)
    print("✓ test_spec2_scenario passed")

if __name__ == "__main__":
    print("Running Python execution engine tests...\n")
    test_string_reversal()
    test_list_indexing()
    test_mathematical_operations()
    test_string_methods()
    test_context_persistence()
    test_security_no_imports()
    test_security_no_file_access()
    test_invalid_syntax()
    test_safe_builtins()
    test_spec2_scenario()
    print("\n✅ All tests passed!")
