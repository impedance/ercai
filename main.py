import os
import textwrap
from erc3 import ERC3
from lib import MyLLM
from agent import run_agent
from dotenv import load_dotenv

# AICODE-NOTE: NAV/MAIN orchestrates ERC3 sessions, task loops, and checkpoints ref: main.py

load_dotenv()

def main():
    # 1. Initialize ERC3 with the token from .env
    token = os.getenv("ERC3_API_KEY")
    # AICODE-CONTRACT: CONTRACT/ENV_KEYS ERC3_API_KEY and OPENROUTER_API_KEY must exist before running [2025-01-01]
    if not token:
        print("Error: ERC3_API_KEY not found in .env")
        return

    core = ERC3(key=token)
    llm = MyLLM()

    # 2. Start session for the DEMO benchmark
    print("Starting session for DEMO benchmark...")
    session = core.start_session(
        benchmark="demo",
        workspace="my",
        name="klyon-3",
        architecture="SGR with OpenRouter",
        flags=["compete_accuracy"]
    )


    print(f"Session ID: {session.session_id}")

    # 3. Get tasks
    status = core.session_status(session.session_id)
    print(f"Total tasks: {len(status.tasks)}")

    # 4. Run agent for each task
    for task in status.tasks:
        print("\n" + "="*50)
        print(f"TASK: {task.task_id} ({task.spec_id})")
        print(f"TEXT: {task.task_text}")
        
        # Mark task as started on the platform
        core.start_task(task)
        
        try:
            run_agent(llm, core, task)
        except Exception as e:
            print(f"Agent failed with error: {e}")
        
        # Complete task on the platform
        result = core.complete_task(task)
        if result.eval:
            print(f"SCORE: {result.eval.score}")
            print(f"LOGS: {result.eval.logs}")

    # 5. Submit session
    core.submit_session(session.session_id)
    print("\nSession submitted!")

if __name__ == "__main__":
    main()
