import json
import sys
from pathlib import Path


PREFIXES = ("SESSION_METRICS:", "TASK_METRICS:", "METRICS:")


def _load_metrics_from_file(path: Path):
    session_metrics = []
    task_metrics = []
    step_metrics = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith("SESSION_METRICS:"):
                payload = line.split("SESSION_METRICS:", 1)[1].strip()
                try:
                    session_metrics.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
            elif line.startswith("TASK_METRICS:"):
                payload = line.split("TASK_METRICS:", 1)[1].strip()
                try:
                    task_metrics.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
            elif line.startswith("METRICS:"):
                payload = line.split("METRICS:", 1)[1].strip()
                try:
                    step_metrics.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
    return session_metrics, task_metrics, step_metrics


def _summarize_from_tasks(task_metrics):
    if not task_metrics:
        return None
    steps = sum(m.get("steps", 0) for m in task_metrics)
    summary = {
        "tasks": len(task_metrics),
        "steps": steps,
        "json_valid_first_try_rate": 0.0,
        "retry_rate": 0.0,
        "repair_rate": 0.0,
        "tool_fallback_rate": 0.0,
        "avg_latency_ms": 0,
        "p95_latency_ms": 0,
        "prompt_tokens_total": sum(m.get("prompt_tokens_total", 0) for m in task_metrics),
        "completion_tokens_total": sum(m.get("completion_tokens_total", 0) for m in task_metrics),
        "schema_fallback_rate": 0.0,
    }
    if steps:
        summary["json_valid_first_try_rate"] = sum(m.get("json_valid_first_try_rate", 0) * m.get("steps", 0) for m in task_metrics) / steps
        summary["retry_rate"] = sum(m.get("retry_rate", 0) * m.get("steps", 0) for m in task_metrics) / steps
        summary["repair_rate"] = sum(m.get("repair_rate", 0) * m.get("steps", 0) for m in task_metrics) / steps
        summary["tool_fallback_rate"] = sum(m.get("tool_fallback_rate", 0) * m.get("steps", 0) for m in task_metrics) / steps
        summary["schema_fallback_rate"] = sum(m.get("schema_fallback_rate", 0) * m.get("steps", 0) for m in task_metrics) / steps
    latencies = [m.get("avg_latency_ms", 0) for m in task_metrics if "avg_latency_ms" in m]
    if latencies:
        latencies_sorted = sorted(latencies)
        p95_index = int(0.95 * (len(latencies_sorted) - 1)) if len(latencies_sorted) > 1 else 0
        summary["avg_latency_ms"] = int(sum(latencies_sorted) / len(latencies_sorted))
        summary["p95_latency_ms"] = latencies_sorted[p95_index]
    return summary


def _summarize_from_steps(step_metrics):
    if not step_metrics:
        return None
    steps = len(step_metrics)
    latencies = [m.get("latency_ms", 0) for m in step_metrics]
    latencies_sorted = sorted(latencies)
    p95_index = int(0.95 * (len(latencies_sorted) - 1)) if len(latencies_sorted) > 1 else 0
    summary = {
        "tasks": 0,
        "steps": steps,
        "json_valid_first_try_rate": sum(1 for m in step_metrics if m.get("json_valid_first_try")) / steps,
        "retry_rate": sum(1 for m in step_metrics if m.get("recovered_by") == "retry") / steps,
        "repair_rate": sum(1 for m in step_metrics if m.get("recovered_by") == "repair") / steps,
        "tool_fallback_rate": sum(1 for m in step_metrics if m.get("recovered_by") == "tool_fallback") / steps,
        "avg_latency_ms": int(sum(latencies_sorted) / len(latencies_sorted)),
        "p95_latency_ms": latencies_sorted[p95_index],
        "prompt_tokens_total": sum(m.get("prompt_tokens_total", 0) for m in step_metrics),
        "completion_tokens_total": sum(m.get("completion_tokens_total", 0) for m in step_metrics),
        "schema_fallback_rate": sum(1 for m in step_metrics if m.get("schema_fallback")) / steps,
    }
    return summary


def _format_rate(value):
    return f"{value:.2%}"


def _render_table(rows):
    headers = [
        "file",
        "tasks",
        "steps",
        "json_ok",
        "retry",
        "repair",
        "tool_fb",
        "avg_ms",
        "p95_ms",
        "prompt_tok",
        "completion_tok",
        "schema_fb",
    ]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for key, val in row.items():
            widths[key] = max(widths.get(key, 0), len(str(val)))
    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(str(row[h]).ljust(widths[h]) for h in headers))


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/metrics_report.py logs/session_*.log")
        sys.exit(1)
    rows = []
    for arg in sys.argv[1:]:
        for path in sorted(Path().glob(arg)) if "*" in arg else [Path(arg)]:
            if not path.exists():
                continue
            session_metrics, task_metrics, step_metrics = _load_metrics_from_file(path)
            if session_metrics:
                summary = session_metrics[-1]
            else:
                summary = _summarize_from_tasks(task_metrics) or _summarize_from_steps(step_metrics)
            if not summary:
                continue
            rows.append({
                "file": path.name,
                "tasks": summary.get("tasks", 0),
                "steps": summary.get("steps", 0),
                "json_ok": _format_rate(summary.get("json_valid_first_try_rate", 0)),
                "retry": _format_rate(summary.get("retry_rate", 0)),
                "repair": _format_rate(summary.get("repair_rate", 0)),
                "tool_fb": _format_rate(summary.get("tool_fallback_rate", 0)),
                "avg_ms": summary.get("avg_latency_ms", 0),
                "p95_ms": summary.get("p95_latency_ms", 0),
                "prompt_tok": summary.get("prompt_tokens_total", 0),
                "completion_tok": summary.get("completion_tokens_total", 0),
                "schema_fb": _format_rate(summary.get("schema_fallback_rate", 0)),
            })
    if not rows:
        print("No metrics found.")
        sys.exit(0)
    _render_table(rows)


if __name__ == "__main__":
    main()
