import os
import logging
from datetime import datetime
from pathlib import Path
from erc3 import ERC3
from lib import MyLLM
from agent import run_agent
from dotenv import load_dotenv

# AICODE-NOTE: NAV/MAIN orchestrates ERC3 sessions, task loops, and checkpoints ref: main.py

load_dotenv()

def setup_logging():
    """Setup logging to both file and console"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"session_{timestamp}.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Log file: {log_file}")
    logger.info("="*50)
    return logger

def main():
    # Setup logging first
    logger = setup_logging()

    # 1. Initialize ERC3 with the token from .env
    token = os.getenv("ERC3_API_KEY")
    # AICODE-CONTRACT: CONTRACT/ENV_KEYS ERC3_API_KEY and OPENROUTER_API_KEY must exist before running [2025-01-01]
    if not token:
        logger.error("Error: ERC3_API_KEY not found in .env")
        return

    core = ERC3(key=token)
    llm = MyLLM()

    # 2. Start session for the DEMO benchmark
    logger.info("Starting session for DEMO benchmark...")
    session = core.start_session(
        benchmark="demo",
        workspace="my",
        name="klyon-3",
        architecture="SGR with OpenRouter",
        flags=["compete_accuracy"]
    )

    logger.info(f"Session ID: {session.session_id}")

    # 3. Get tasks
    status = core.session_status(session.session_id)
    logger.info(f"Total tasks: {len(status.tasks)}")

    # 4. Run agent for each task
    for task in status.tasks:
        logger.info("\n" + "="*50)
        logger.info(f"TASK: {task.task_id} ({task.spec_id})")
        logger.info(f"TEXT: {task.task_text}")

        # Mark task as started on the platform
        core.start_task(task)

        try:
            run_agent(llm, core, task, logger)
        except Exception as e:
            logger.error(f"Agent failed with error: {e}")

        # Complete task on the platform
        result = core.complete_task(task)
        if result.eval:
            logger.info(f"SCORE: {result.eval.score}")
            logger.info(f"LOGS: {result.eval.logs}")

    # 5. Submit session
    core.submit_session(session.session_id)
    logger.info("\nSession submitted!")

if __name__ == "__main__":
    main()
