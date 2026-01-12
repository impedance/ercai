from erc3 import demo, TaskInfo, ERC3
from lib import MyLLM
from schemas import NextStep, ReportTaskCompletion

# AICODE-NOTE: NAV/AGENT schema-guided reasoning loop for ERC3 tasks ref: agent.py

system_prompt = """

You are a corporate agent participating in the Enterprise RAG Challenge.
Your goal is to solve the task provided by the user.

- Use Req_GetSecret to get the secret string.
- Read the task description carefully and follow it EXACTLY.
- If the task says "Return secret", return it unchanged without any transformation.
- If the task says "Return secret backwards":
  * Take each character from the END to the START
  * Example: "abc" becomes "cba", "hello" becomes "olleh"
  * Preserve case: "aBc" becomes "cBa"
  * IMPORTANT: In your current_state, show the reversal step-by-step to verify correctness
  * Example: Secret "abc" → Position 2='c', Position 1='b', Position 0='a' → Result "cba"
- Use Req_ProvideAnswer to submit the final result.
- Once the task is solved, pick ReportTaskCompletion.
"""

def run_agent(llm: MyLLM, api: ERC3, task: TaskInfo, logger):
    demo_client = api.get_demo_client(task)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task ID: {task.task_id}\nTask Description: {task.task_text}"}
    ]

    logger.info(f"Starting agent for task: {task.task_id}")

    for i in range(10):
        logger.info(f"--- Step {i+1} ---")
        job, usage = llm.query(messages, NextStep)

        # Log to platform (optional but good practice)
        api.log_llm(
            task_id=task.task_id,
            model=llm.model,
            duration_sec=0.5, # Dummy duration
            completion=job.model_dump_json(),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )

        if isinstance(job.function, ReportTaskCompletion):
            logger.info(f"Agent reported completion: {job.function.code}")
            break

        logger.info(f"Thinking: {job.current_state}")
        logger.info(f"Action: {job.function.__class__.__name__}")

        # Execute
        try:
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
