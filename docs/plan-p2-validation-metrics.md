# Implementation Plan: P2 Validation Metrics

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md` (per repo bootstrap checklist).
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Re-read `docs/implementation-plan-adaptive-agent-architecture.md` to keep P2 context aligned with the broader architecture.

## Goal
Collect validation successes in `ValidationTracker.records`, surface them in the final task summary/metrics, and remove the placeholder "no inference statistics" messaging so downstream tooling can see how often deterministic checks pass.

## Non-goals
- Rework the validation guard logic or buyer workflow beyond capturing metrics.
- Introduce new telemetry infrastructure outside the agent's logging and summary payload.

## Contracts / Risks to Preserve
- `CONTRACT/REQUIRED_KEYS` still applies for `ERC3_API_KEY` and `OPENROUTER_API_KEY`. (see `docs/context.md`)
- All `Req_ComputeWithPython` usages must remain schema-aligned and sandbox-safe (per `aicode-system.md` anchors).
- Avoid making `agent` summary-dependent invariants brittle (keep `store_guard` coupon/inventory checks untouched).

## Entry points / Affected files
- `agent.py` (record validation events, include them in `step_metrics` summary, update logs at completion).
- `docs/status.md` (if the live status needs a note that validation metrics now appear in summaries or clarifies expectations).
- `tests/test_agent_helpers.py` (ensure validation tracker behavior remains consistent after metric exposure).

## Step-by-step plan
1. Inspect the existing `step_metrics` summary generation in `agent.py` (near final logging) to decide where to add validation stats.
2. Extend `agent.py` so that `validation_tracker.records` (filtered for successful validation entries) contribute to `summary` and logging, and ensure the metrics include counts/rates relevant to success vs. failure.
3. Update `docs/status.md` (if needed) to note that validation guards now appear in the task metrics/summary for easier monitoring.
4. Run `./scripts/lint-aicode.sh` and `.venv/bin/python -m pytest tests/test_agent_helpers.py` to validate the change.

## Validation plan
- `./scripts/lint-aicode.sh`
- `./.venv/bin/python -m pytest tests/test_agent_helpers.py`

## Rollback plan
- Revert the summary/metrics changes to keep `agent.py` reporting as before.
- Remove any new log statements referencing `validation_tracker.records` if they cause noise or schema issues.
