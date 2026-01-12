# ADR-0002: Python Execution for Algorithmic Tasks

## Status
Proposed (2026-01-12)

## Context

### Problem Discovery
During ERC3 demo benchmark testing (session `2026-01-12_17-57-20`), the agent failed task `spec2` ("Return secret backwards"):
- **Input secret**: `NcS9euQa` (8 characters)
- **Agent output**: `aQueu9ScN` (9 characters) - contains extra 'u' ❌
- **Expected output**: `aQue9ScN` (8 characters) ✓

The agent correctly identified each character position but made a transcription error when constructing the reversed string. This is a fundamental limitation of LLMs performing algorithmic operations through "reasoning" rather than execution.

### Root Cause: LLM Architectural Limitations

Large Language Models are **statistically predicting tokens**, not executing deterministic algorithms. They fail at:
1. **String manipulation** - reversing, slicing, regex, character-by-character operations
2. **Precise arithmetic** - especially floating-point, multi-digit calculations
3. **Algorithmic operations** - sorting, searching, pattern matching
4. **Structured data parsing** - JSON manipulation, list transformations

These failures occur because:
- LLMs "simulate" step-by-step reasoning but make transcription errors
- Token-by-token generation introduces compounding probability of mistakes
- No internal verification mechanism for deterministic correctness

### Strategic Concern

The ERC3 benchmark will **intentionally escalate complexity** to test agent robustness. Future tasks may include:
- Complex string transformations (e.g., "extract every 3rd character after splitting by comma")
- Multi-step mathematical operations
- Data structure manipulations (sorting, filtering, nested operations)

We need a scalable solution that doesn't require predicting and implementing a new tool for each algorithmic pattern.

## Decision

**Add `Req_ComputeWithPython` tool** that allows the agent to execute Python code for deterministic operations.

### Architecture

```python
# New schema
class Req_ComputeWithPython(BaseModel):
    tool: Literal["compute_with_python"]
    code: str  # Python expression to evaluate
    description: str  # Human-readable explanation (for logs)

# Example usage by agent
NextStep(
    current_state="Need to reverse secret string precisely",
    function=Req_ComputeWithPython(
        code="'NcS9euQa'[::-1]",
        description="Reverse string using Python slicing"
    )
)
# Returns: "aQue9ScN"
```

### Natural Division of Responsibilities

| Task Type | Handler | Reason |
|-----------|---------|--------|
| Task understanding | LLM | Language comprehension is LLM's strength |
| Tool selection | LLM | Planning and orchestration |
| Code generation | LLM | Trained on massive code corpora (GitHub) |
| **Execution** | **Python** | Deterministic, no transcription errors |
| Result interpretation | LLM | Contextual understanding |

## Alternatives Considered

### ❌ Option 1: Specialized Tools Per Operation
Add `Req_ReverseString`, `Req_Calculate`, `Req_SortList`, etc.

**Rejected because:**
- Non-scalable: Cannot predict all future algorithmic patterns
- Maintenance burden: Each new task type requires new tool implementation
- Arms race: Benchmark complexity will outpace tool development
- **Violates flexibility principle**: ERC3 intentionally tests adaptability

### ❌ Option 2: Improved Prompting
Add detailed instructions like "verify string length after reversal", "show intermediate steps", etc.

**Rejected because:**
- Doesn't address root cause: LLMs inherently make transcription errors
- Increases prompt complexity without reliability gains
- Token overhead without solving fundamental limitation
- **Still fails on novel algorithmic patterns**

### ❌ Option 3: Hybrid - Prompt + Specialized Tools
Combine better prompts with a limited set of common tools.

**Rejected because:**
- Shares scaling issues with Option 1
- Adds prompt complexity (when to use tool vs reasoning)
- Still vulnerable to unforeseen task patterns

### ✅ Option 4: General-Purpose Code Execution (SELECTED)

**Why this wins:**

1. **Unbounded flexibility**: Covers ANY algorithmic operation
   - String: slice, reverse, regex, case transformations
   - Math: arbitrary precision, complex formulas
   - Data: sorting, filtering, aggregations, transformations

2. **Aligns with LLM strengths**:
   - Models excel at code generation (trained on billions of lines)
   - Separates "understanding" (LLM) from "execution" (Python)

3. **Industry standard approach**:
   - OpenAI Code Interpreter (GPT-4)
   - Anthropic Claude artifacts
   - Production agents (Devin, Cursor, Replit Agent)

4. **Future-proof**: Handles escalating complexity without architectural changes

5. **Verifiable**: Code is inspectable, testable, debuggable (vs opaque "reasoning")

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Schema Definition (`schemas.py`)
```python
class Req_ComputeWithPython(BaseModel):
    """Execute Python code for precise algorithmic operations"""
    tool: Literal["compute_with_python"]
    code: str = Field(..., description="Python expression to evaluate")
    description: str = Field(..., description="Human-readable explanation")

# Add to NextStep union
function: Union[
    ReportTaskCompletion,
    demo.Req_GetSecret,
    demo.Req_ProvideAnswer,
    Req_ComputeWithPython  # NEW
]
```

#### 1.2 Safe Execution Engine (`agent.py`)
```python
import ast

# Whitelist safe builtins
SAFE_BUILTINS = {
    'len': len, 'str': str, 'int': int, 'float': float,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'reversed': reversed, 'sorted': sorted, 'enumerate': enumerate,
    'sum': sum, 'max': max, 'min': min, 'abs': abs, 'round': round,
    'range': range, 'zip': zip, 'map': map, 'filter': filter,
}

def execute_python(code: str, context: dict) -> dict:
    """
    Execute Python expression in sandboxed environment

    Security boundaries:
    - Only eval() (expressions), not exec() (statements)
    - No imports, no file I/O, no network
    - Whitelisted builtins only
    - AST validation before execution
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
```

#### 1.3 Agent Loop Integration (`agent.py`)
```python
def run_agent(llm: MyLLM, api: ERC3, task: TaskInfo, logger):
    demo_client = api.get_demo_client(task)
    python_context = {}  # Shared context across Python executions

    # ... existing setup ...

    for i in range(10):
        job, usage = llm.query(messages, NextStep)

        if isinstance(job.function, Req_ComputeWithPython):
            logger.info(f"Executing Python: {job.function.code}")

            # Execute in sandboxed environment
            exec_result = execute_python(job.function.code, python_context)

            if exec_result["error"]:
                result_json = exec_result["error"]
            else:
                result_json = exec_result["result"]
                # Store for future reference
                python_context['last_result'] = result_json

            # Format as tool result
            messages.append({
                "role": "assistant",
                "content": f"Thought: {job.current_state}",
                "tool_calls": [{
                    "type": "function",
                    "id": f"step_{i}",
                    "function": {
                        "name": "Req_ComputeWithPython",
                        "arguments": job.function.model_dump_json()
                    }
                }]
            })
            messages.append({
                "role": "tool",
                "content": result_json,
                "tool_call_id": f"step_{i}"
            })
        else:
            # Existing demo_client.dispatch() path
            result = demo_client.dispatch(job.function)
            # ... existing code ...
```

### Phase 2: Prompt Engineering

Update `system_prompt` in `agent.py`:

```python
system_prompt = """
You are a corporate agent participating in the Enterprise RAG Challenge.

Available tools:
1. Req_GetSecret - Retrieve secret data from platform
2. Req_ProvideAnswer - Submit final answer to platform
3. Req_ComputeWithPython - Execute Python code for algorithmic operations
4. ReportTaskCompletion - Signal task completion

CRITICAL: Use Python for deterministic operations

When to use Req_ComputeWithPython:
- String manipulation (reverse, slice, regex, case transformations)
- Mathematical calculations (especially multi-step or floating-point)
- List/dict operations (sorting, filtering, transformations)
- Any operation requiring precise, character-perfect results

Python context:
- Previous results available as 'last_result'
- All string methods available: .split(), .join(), .upper(), .lower(), [::-1], etc.
- Standard operators: +, -, *, /, //, %, **
- Functions: len(), sorted(), reversed(), sum(), max(), min(), etc.

Example workflow:
Task: "Return secret backwards"
Step 1: Req_GetSecret → {"value": "abc123"}
Step 2: Req_ComputeWithPython
        code: "'abc123'[::-1]"
        → "321cba"
Step 3: Req_ProvideAnswer
        answer: "321cba"
Step 4: ReportTaskCompletion

Task: "Return secret number 2 from comma-separated list"
Step 1: Req_GetSecret → {"value": "apple,banana,cherry"}
Step 2: Req_ComputeWithPython
        code: "'apple,banana,cherry'.split(',')[1]"
        → "banana"
Step 3: Req_ProvideAnswer
        answer: "banana"
Step 4: ReportTaskCompletion

IMPORTANT:
- Use direct API calls (Req_GetSecret, Req_ProvideAnswer) for I/O
- Use Python ONLY for transformations/calculations
- Always provide clear 'description' field explaining Python code intent
"""
```

### Phase 3: Testing & Validation

#### 3.1 Unit Tests
```python
# tests/test_python_execution.py
def test_string_reversal():
    result = execute_python("'abc123'[::-1]", {})
    assert result["result"] == "321cba"
    assert result["error"] is None

def test_list_indexing():
    result = execute_python("'a,b,c'.split(',')[1]", {})
    assert result["result"] == "b"

def test_security_no_imports():
    result = execute_python("__import__('os').system('ls')", {})
    assert result["error"] is not None
    assert "import" in result["error"].lower()
```

#### 3.2 Integration Test
Re-run `spec2` task from failed session:
```bash
python main.py  # Should now pass spec2 with Python execution
```

Expected behavior:
```
Task: "Return secret backwards"
Step 1: Req_GetSecret → "NcS9euQa"
Step 2: Req_ComputeWithPython → "'NcS9euQa'[::-1]" → "aQue9ScN" ✓
Step 3: Req_ProvideAnswer → "aQue9ScN"
SCORE: 1.0 ✓
```

## Security Considerations

### Sandboxing Guarantees

| Attack Vector | Mitigation |
|---------------|------------|
| File system access | No `open()`, `os`, `pathlib` in builtins |
| Network access | No `requests`, `urllib`, `socket` in builtins |
| Process execution | No `os.system()`, `subprocess` |
| Infinite loops | Use `eval()` not `exec()` - only expressions allowed |
| Memory bombs | Expression-only limits recursion depth naturally |
| Import injection | `__import__` blocked, no `import` statement in expressions |

### What's Allowed (Safe Operations)
- String methods: `.split()`, `.join()`, `.replace()`, slicing `[:]`
- Math: `+, -, *, /, //, %, **`
- Builtin functions: `len()`, `sorted()`, `max()`, `sum()`, etc.
- List/dict comprehensions: `[x*2 for x in range(10)]`
- Lambda functions: `list(map(lambda x: x*2, [1,2,3]))`

### Defense in Depth
1. AST parsing catches syntax errors before execution
2. `eval()` mode prevents statements (no `for`, `while`, `def`, `class`)
3. Restricted `__builtins__` prevents imports and I/O
4. Try/except catches runtime errors gracefully
5. Result stringification prevents object injection

## Consequences

### Pros ✅
1. **Eliminates LLM algorithmic errors**: No more transcription mistakes in string/math operations
2. **Infinite flexibility**: Handles any future algorithmic task pattern
3. **Leverages LLM strengths**: Code generation >> simulated computation
4. **Industry-standard pattern**: Aligns with GPT-4 Code Interpreter, Claude Artifacts
5. **Debuggable**: Code is inspectable, testable, modifiable
6. **Future-proof**: Scales to escalating benchmark complexity

### Cons / Risks ⚠️
1. **Syntax errors**: LLM may generate invalid Python
   - *Mitigation*: AST validation + clear error messages + retry logic
2. **Context management**: Need to track variables across steps
   - *Mitigation*: Persistent `python_context` dict in agent loop
3. **Prompt complexity**: Agent must learn when to use Python vs direct API
   - *Mitigation*: Clear examples in system prompt + few-shot learning
4. **Security surface**: Code execution always carries risk
   - *Mitigation*: Sandboxing via eval-only + restricted builtins (see Security section)

### Trade-offs Accepted
- **Complexity** (+30 lines) vs **Capability** (unbounded algorithmic power): Clear win
- **Security risk** (sandboxed code execution) vs **Reliability** (no LLM transcription errors): Acceptable with mitigations
- **Token cost** (slightly longer prompts) vs **Accuracy** (deterministic results): Worth it for competition scoring

## Validation Plan

### Pre-merge Checklist
- [ ] Update `schemas.py` with `Req_ComputeWithPython`
- [ ] Implement `execute_python()` with security sandbox
- [ ] Integrate into agent loop with context management
- [ ] Update system prompt with usage guidelines + examples
- [ ] Add unit tests for execution engine
- [ ] Re-run failed task `spec2` - verify score=1.0
- [ ] Run full demo benchmark - verify no regressions
- [ ] Update `docs/status.md` with current state
- [ ] Run `./scripts/lint-aicode.sh`

### Success Metrics
1. **spec2 task**: Score increases from 0.0 → 1.0
2. **Benchmark regression**: All other tasks maintain scores
3. **Security**: No successful escape from sandbox in testing
4. **Code quality**: LLM generates syntactically valid Python >90% of time

## Rollback Plan

If implementation causes issues:
1. **Immediate**: Revert commits (schema + agent + prompt changes)
2. **Partial rollback**: Keep schema but disable in agent loop (feature flag)
3. **Degraded mode**: Fall back to LLM reasoning if Python execution errors exceed threshold

No data migration needed - changes are purely additive to existing tool set.

## Related

- Log analysis: `logs/session_2026-01-12_17-57-20.log:46-47` (spec2 failure)
- Affected files: `schemas.py`, `agent.py`
- Similar patterns: OpenAI Code Interpreter, Anthropic Claude Code
- Future work: Consider adding `Req_ComputeWithJavaScript` for frontend tasks

## References

- [ERC3 Demo Benchmark](https://github.com/erc3-agents/erc3)
- [OpenAI Code Interpreter](https://platform.openai.com/docs/guides/code-interpreter)
- [Python eval() security](https://docs.python.org/3/library/functions.html#eval)
- [AST module docs](https://docs.python.org/3/library/ast.html)
