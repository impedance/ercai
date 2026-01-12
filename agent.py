import json
import ast
from typing import Dict
from erc3 import demo, TaskInfo, ERC3
from lib import MyLLM
from schemas import NextStep, ReportTaskCompletion, Req_ComputeWithPython

# AICODE-NOTE: NAV/AGENT schema-guided reasoning loop for ERC3 tasks ref: agent.py

# Whitelist safe builtins for Python execution
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

system_prompt = """

You are a corporate agent participating in the Enterprise RAG Challenge.
Your goal is to solve the task provided by the user.

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
        description: "Reverse string using Python slicing"
        → "321cba"
Step 3: Req_ProvideAnswer
        answer: "321cba"
Step 4: ReportTaskCompletion

Task: "Return secret number 2 from comma-separated list"
Step 1: Req_GetSecret → {"value": "apple,banana,cherry"}
Step 2: Req_ComputeWithPython
        code: "'apple,banana,cherry'.split(',')[1]"
        description: "Split by comma and get second element"
        → "banana"
Step 3: Req_ProvideAnswer
        answer: "banana"
Step 4: ReportTaskCompletion

IMPORTANT:
- Use direct API calls (Req_GetSecret, Req_ProvideAnswer) for I/O
- Use Python ONLY for transformations/calculations
- Always provide clear 'description' field explaining Python code intent
- Read the task description carefully and follow it EXACTLY
"""

def run_agent(llm: MyLLM, api: ERC3, task: TaskInfo, logger):
    demo_client = api.get_demo_client(task)
    step_metrics = []
    python_context = {}  # Shared context across Python executions

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task ID: {task.task_id}\nTask Description: {task.task_text}"}
    ]

    logger.info(f"Starting agent for task: {task.task_id}")

    for i in range(10):
        logger.info(f"--- Step {i+1} ---")
        job, usage, meta = llm.query(messages, NextStep)
        step_metrics.append(meta)
        logger.info(f"METRICS: {json.dumps(meta, sort_keys=True)}")

        # Log to platform (optional but good practice)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        api.log_llm(
            task_id=task.task_id,
            model=llm.model,
            duration_sec=meta["latency_ms"] / 1000.0,
            completion=job.model_dump_json(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        if isinstance(job.function, ReportTaskCompletion):
            logger.info(f"Agent reported completion: {job.function.code}")
            break

        logger.info(f"Thinking: {job.current_state}")
        logger.info(f"Action: {job.function.__class__.__name__}")

        # Execute
        try:
            if isinstance(job.function, Req_ComputeWithPython):
                logger.info(f"Executing Python: {job.function.code}")
                logger.info(f"Description: {job.function.description}")

                # Execute in sandboxed environment
                exec_result = execute_python(job.function.code, python_context)

                if exec_result["error"]:
                    result_json = exec_result["error"]
                else:
                    result_json = exec_result["result"]
                    # Store for future reference
                    python_context['last_result'] = result_json

                logger.info(f"Python Result: {result_json}")

                # Add to history
                messages.append({
                    "role": "assistant",
                    "content": f"Thought: {job.current_state}",
                    "tool_calls": [{
                        "type": "function",
                        "id": f"step_{i}",
                        "function": {
                            "name": "Req_ComputeWithPython",
                            "arguments": job.function.model_dump_json(),
                        }
                    }]
                })
                messages.append({"role": "tool", "content": result_json, "tool_call_id": f"step_{i}"})
            else:
                result = demo_client.dispatch(job.function)
                result_json = result.model_dump_json()
                logger.info(f"Result: {result_json}")

                # Add to history
                messages.append({
                    "role": "assistant",
                    "content": f"Thought: {job.current_state}",
                    "tool_calls": [{
                        "type": "function",
                        "id": f"step_{i}",
                        "function": {
                            "name": job.function.__class__.__name__,
                            "arguments": job.function.model_dump_json(),
                        }
                    }]
                })
                messages.append({"role": "tool", "content": result_json, "tool_call_id": f"step_{i}"})
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error: {error_msg}")
            messages.append({"role": "tool", "content": f"Error: {error_msg}", "tool_call_id": f"step_{i}"})

    logger.info("Task finished.")
    if step_metrics:
        latencies = sorted(m["latency_ms"] for m in step_metrics)
        p95_index = int(0.95 * (len(latencies) - 1)) if len(latencies) > 1 else 0
        summary = {
            "steps": len(step_metrics),
            "json_valid_first_try_rate": sum(1 for m in step_metrics if m["json_valid_first_try"]) / len(step_metrics),
            "retry_rate": sum(1 for m in step_metrics if m["recovered_by"] == "retry") / len(step_metrics),
            "repair_rate": sum(1 for m in step_metrics if m["recovered_by"] == "repair") / len(step_metrics),
            "tool_fallback_rate": sum(1 for m in step_metrics if m["recovered_by"] == "tool_fallback") / len(step_metrics),
            "avg_latency_ms": int(sum(latencies) / len(latencies)),
            "p95_latency_ms": latencies[p95_index],
            "prompt_tokens_total": sum(m["prompt_tokens_total"] for m in step_metrics),
            "completion_tokens_total": sum(m["completion_tokens_total"] for m in step_metrics),
            "schema_fallback_rate": sum(1 for m in step_metrics if m["schema_fallback"]) / len(step_metrics),
        }
        logger.info(f"TASK_METRICS: {json.dumps(summary, sort_keys=True)}")
        return summary
    return None
