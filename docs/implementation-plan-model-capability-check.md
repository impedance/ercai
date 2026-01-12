# Implementation Plan: Model Capability Check (Tool/Schema Compliance)

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Review `lib.py` (`MyLLM.query`) and `agent.py` (`run_agent`) to see current schema/tool flow.

## Goal
Add a startup capability check that verifies the configured model can return schema-aligned JSON for `NextStep`, and warn early if it cannot.

## Non-goals
- No changes to model selection or routing logic.
- No new tools beyond this check.
- No persistent telemetry or external monitoring.

## Contracts / Risks to Preserve
- Schema-aligned JSON is required before dispatching tools (`NextStep` invariant).
- Avoid altering core request behavior in `MyLLM.query`.
- Keep the check lightweight (one request, short prompt).

## Entry points / Affected files
- `main.py` (call capability check at startup)
- `lib.py` (helper method on `MyLLM`)
- `agent.py` (optional: reuse minimal prompt text if needed)

## Step-by-step plan
1. Add `MyLLM.check_schema_capability(response_format, logger)` that:
   - Sends a short prompt asking for a minimal valid JSON response.
   - Catches parse errors and returns `True/False`.
2. Call this check in `main.py` after `MyLLM()` initialization:
   - If it fails, log a warning about tool/schema compliance risk.
3. Keep the check opt-in or always-on (decide and document in code).

## Validation plan
- Run `python main.py` and confirm:
  - success logs when model complies
  - warning logs when intentionally misconfigured model is used

## Rollback plan
- Remove the call in `main.py` and the helper in `lib.py` (no side effects).
