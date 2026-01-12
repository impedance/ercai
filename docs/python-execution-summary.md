# Python Execution for Agent - Quick Summary

**Date**: 2026-01-12
**Full ADR**: [ADR-0002](decisions/ADR-0002-python-execution-for-algorithmic-tasks.md)

## Why Are We Doing This?

### The Problem
Agent failed task `spec2` in demo benchmark:
```
Task: "Return secret backwards"
Secret: "NcS9euQa" (8 chars)
Agent returned: "aQueu9ScN" (9 chars) ❌ Extra 'u'
Expected: "aQue9ScN" (8 chars) ✓
```

The agent correctly identified every character position, but made a **transcription error** when assembling the final string. This is not a bug - it's a fundamental limitation of how LLMs work.

### Why LLMs Fail at This

LLMs don't "execute" code - they **simulate** step-by-step reasoning by predicting tokens:
- String reversal requires precise character manipulation
- LLMs generate text probabilistically, introducing errors
- No internal verification for deterministic correctness

**What LLMs are bad at:**
- String operations (reverse, slice, regex)
- Precise arithmetic (especially floats, large numbers)
- Algorithmic tasks (sorting, parsing, pattern matching)

**What LLMs are good at:**
- Understanding natural language
- Writing code
- Planning sequences of actions

### Strategic Risk

ERC3 benchmark will **intentionally escalate complexity** to break agents:
- "Extract every 3rd character after splitting by comma and reversing each segment"
- Complex mathematical transformations
- Multi-step data structure manipulations

We can't predict all patterns → can't pre-build specialized tools for each.

## The Solution: Let Agent Write & Execute Python

Instead of asking LLM to "think through" string reversal, let it **write Python code** and execute it:

```python
# Before (LLM reasoning) ❌
"Thinking: Position 7='a', Position 6='Q', ... Result 'aQueu9ScN'"

# After (Python execution) ✅
Code: "'NcS9euQa'[::-1]"
Result: "aQue9ScN"  # Deterministic, no errors
```

## Why This Wins

### ✅ Compared to "Add More Specialized Tools"
- **Infinite flexibility**: Handles ANY algorithmic pattern
- **No maintenance**: Don't need new tool for each task type
- **Future-proof**: Scales with benchmark complexity

### ✅ Compared to "Better Prompting"
- **Solves root cause**: Python doesn't make transcription errors
- **Reliable**: Deterministic execution vs probabilistic generation
- **Verifiable**: Code is testable and debuggable

### ✅ Industry Standard
- OpenAI Code Interpreter (GPT-4)
- Anthropic Claude Artifacts
- Production agents (Devin, Cursor, Replit)

## What Gets Added

### New Tool: `Req_ComputeWithPython`

```python
class Req_ComputeWithPython(BaseModel):
    code: str  # Python expression to execute
    description: str  # What it does (for logs)

# Agent usage
Req_ComputeWithPython(
    code="'NcS9euQa'[::-1]",
    description="Reverse secret string"
)
# Returns: "aQue9ScN"
```

### Secure Execution Engine

- **Only expressions** (`eval`), not statements (`exec`) → no loops, no file I/O
- **Whitelisted builtins**: `len()`, `str()`, `sorted()`, math operators
- **No imports**, no network, no file access
- **AST validation** before execution

### Updated Agent Workflow

```
Task: "Return secret backwards"

Step 1: Req_GetSecret
  ↓ Result: "NcS9euQa"

Step 2: Req_ComputeWithPython
  ↓ code: "'NcS9euQa'[::-1]"
  ↓ Result: "aQue9ScN"

Step 3: Req_ProvideAnswer
  ↓ answer: "aQue9ScN"

Step 4: ReportTaskCompletion
  ✓ SCORE: 1.0
```

## Implementation Size

- `schemas.py`: +10 lines (new tool schema)
- `agent.py`: +30 lines (execution engine + integration)
- System prompt: +40 lines (usage guidelines + examples)
- Tests: +50 lines (unit + integration)

**Total**: ~130 lines, massive capability unlock

## Security Guarantees

| What's Blocked | How |
|----------------|-----|
| File access | No `open()`, `os`, `pathlib` |
| Network | No `requests`, `urllib`, `socket` |
| Process execution | No `os.system()`, `subprocess` |
| Infinite loops | Expression-only (no `while`, `for`) |
| Imports | `__import__` blocked, no `import` in expressions |

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LLM generates bad syntax | AST validation + clear errors + retry |
| Security escape | Sandboxing (see table above) |
| Agent overuses Python | Prompt with clear guidelines when to use |
| Context management | Persistent `python_context` dict |

## Success Criteria

- [ ] Task `spec2` score: 0.0 → 1.0 ✓
- [ ] No regressions on other demo tasks
- [ ] Security: No sandbox escapes in testing
- [ ] Code quality: LLM generates valid Python >90% of time

## Natural Division of Labor

| Responsibility | Owner | Why |
|----------------|-------|-----|
| Understand task | LLM | Language comprehension |
| Plan approach | LLM | Orchestration & reasoning |
| **Write code** | **LLM** | **Trained on billions of lines** |
| **Execute code** | **Python** | **Deterministic, no errors** |
| Interpret result | LLM | Contextual understanding |

## Next Steps

See [ADR-0002](decisions/ADR-0002-python-execution-for-algorithmic-tasks.md) for:
- Complete implementation code
- Detailed security analysis
- Full system prompt with examples
- Testing strategy
- Rollback plan

---

**TL;DR**: LLMs are bad at executing algorithms but great at writing code. Let agent write Python for precise operations instead of "thinking through" them. This is how all production agents work (GPT-4, Claude, Devin).
