# Implementation Plan: Store Baseline Messaging

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` before editing to confirm no anchors change unintentionally.
- Refer to `docs/implementation-plan-store-default-messaging.md` and `docs/implementation-plan-adaptive-agent-architecture.md` for the requested framing.

## Goal
- Emphasize the STORE benchmark as the baseline everywhere (code, prompts, docs) by removing leftover demo references, aligning schema/fallback logic, and updating navigation notes accordingly.

## Non-goals
- Adding new runtime tools beyond the existing store + Python compute surfaces.
- Touching samples under `repo-erc3-agents/` or rewriting historical ADR summaries.

## Contracts / Risks to Preserve
- Maintain `AICODE-*` anchor discipline and preserve `CONTRACT/REQUIRED_KEYS`.
- Keep Python compute logic untouched while ensuring no regression in store tool usage.
- Do not break the existing store session init (`benchmark="store"`) or the schema union.

## Entry points / Affected files
- `schemas.py` (drop demo tools from `NextStep` and keep store + Python only).
- `lib.py` (remove `demo` fallback heuristics and keep `ReportTaskCompletion` wrap).
- `CLAUDE.md` (refresh narrative to describe the STORE benchmark + store tools).
- `docs/implementation-plan-store-default-messaging.md` (tune wording to show STORE baseline and this work).
- `docs/implementation-plan-adaptive-agent-architecture.md` (remove outdated demo transition language).
- `README.md` / `docs/status.md` (spot-check anchors and ensure doc navigation references remain accurate).
- `docs/plan-store-default-implementation.md` (this file documents the plan itself).

## Step-by-step plan
1. Capture this plan in `docs/plan-store-default-implementation.md` (done).
2. Update `schemas.py` to import only `store`, keep `Req_ComputeWithPython`, and ensure `NextStep` has no demo tools.
3. Simplify `lib.py` JSON fallback so it only reconstructs `ReportTaskCompletion` (no demo heuristics).
4. Refresh `CLAUDE.md` and the implementation plan docs so the narrative consistently mentions STORE + store tools and links to this plan.
5. Review anchors with `rg -n "AICODE-"` and run `./scripts/lint-aicode.sh` to validate.

## Validation plan
- `rg -n "AICODE-"`
- `./scripts/lint-aicode.sh`

## Rollback plan
- Revert the modified files via Git if any change destabilizes the anchor checks or tool schema.
