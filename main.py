import os
import json
import logging
from datetime import datetime
from pathlib import Path
from erc3 import ERC3
from lib import MyLLM
from agent import run_agent
from schemas import NextStep
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
    if not llm.check_schema_capability(NextStep, logger):
        logger.warning(
            "Model may not support schema-aligned tool calls; expect failures on tool usage."
        )

    # 2. Start session for the STORE benchmark
    logger.info("Starting session for STORE benchmark...")
    session = core.start_session(
        benchmark="store",
        workspace="my",
        name="klyon-3-store",
        architecture="SGR with OpenRouter (STORE)",
        flags=["compete_accuracy"]
    )

    logger.info(f"Session ID: {session.session_id}")

    # 3. Get tasks
    status = core.session_status(session.session_id)
    logger.info(f"Total tasks: {len(status.tasks)}")

    # 4. Run agent for each task
    session_summaries = []
    for task in status.tasks:
        logger.info("\n" + "="*50)
        logger.info(f"TASK: {task.task_id} ({task.spec_id})")
        logger.info(f"TEXT: {task.task_text}")

        # Mark task as started on the platform
        core.start_task(task)

        try:
            summary = run_agent(llm, core, task, logger)
            if summary:
                summary["task_id"] = task.task_id
                summary["spec_id"] = task.spec_id
                session_summaries.append(summary)
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
    if session_summaries:
        all_latencies = []
        steps_total = 0
        summary_out = {
            "tasks": len(session_summaries),
            "steps": 0,
            "json_valid_first_try_rate": 0.0,
            "retry_rate": 0.0,
            "repair_rate": 0.0,
            "tool_fallback_rate": 0.0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "schema_fallback_rate": 0.0,
        }
        for s in session_summaries:
            steps_total += s["steps"]
            summary_out["prompt_tokens_total"] += s["prompt_tokens_total"]
            summary_out["completion_tokens_total"] += s["completion_tokens_total"]
            summary_out["json_valid_first_try_rate"] += s["json_valid_first_try_rate"] * s["steps"]
            summary_out["retry_rate"] += s["retry_rate"] * s["steps"]
            summary_out["repair_rate"] += s["repair_rate"] * s["steps"]
            summary_out["tool_fallback_rate"] += s["tool_fallback_rate"] * s["steps"]
            summary_out["schema_fallback_rate"] += s["schema_fallback_rate"] * s["steps"]
            all_latencies.append(s["avg_latency_ms"])
        summary_out["steps"] = steps_total
        if steps_total:
            summary_out["json_valid_first_try_rate"] /= steps_total
            summary_out["retry_rate"] /= steps_total
            summary_out["repair_rate"] /= steps_total
            summary_out["tool_fallback_rate"] /= steps_total
            summary_out["schema_fallback_rate"] /= steps_total
        if all_latencies:
            all_latencies_sorted = sorted(all_latencies)
            p95_index = int(0.95 * (len(all_latencies_sorted) - 1)) if len(all_latencies_sorted) > 1 else 0
            summary_out["avg_latency_ms"] = int(sum(all_latencies_sorted) / len(all_latencies_sorted))
            summary_out["p95_latency_ms"] = all_latencies_sorted[p95_index]
        logger.info(f"SESSION_METRICS: {json.dumps(summary_out, sort_keys=True)}")

if __name__ == "__main__":
    main()
