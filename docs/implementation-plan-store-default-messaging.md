# Implementation Plan: Store Default Messaging

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Review `docs/implementation-plan-adaptive-agent-architecture.md` to keep the STORE-first framing consistent.

## Goal
- Remove leftover “DEMO→STORE” transition language (and missing plan links) so the repository presents STORE as the baseline benchmark everywhere in docs/prompts/navigation.

## Non-goals
- Changing the agent code, tools, or runtime metadata (store is already the default in `main.py`).
- Rewriting long-form status history—just refresh current focus/entry bullets.

## Contracts / Risks to Preserve
- Maintain the required anchors and doc references (status focus/entry, context invariants).
- Keep README as the navigation index per the AGENTS instructions.
- Running `rg -n "AICODE-"` before editing and `./scripts/lint-aicode.sh` after changes.

## Entry points / Affected files
- `docs/context.md` (mission/stack description should continue to emphasize STORE as the baseline benchmark).
- `docs/status.md` (living focus/next steps mention a STORE transition plan).
- `CLAUDE.md` (navigation notes and architecture overview still describe the older demo flow).
- `README.md` (search pointers and explanations should reflect STORE tooling where appropriate).
- `docs/implementation-plan-adaptive-agent-architecture.md` (ensure the plan’s framing matches the new wording).
- `docs/plan-store-default-implementation.md` (log of the concrete work being tracked).

## Step-by-step plan
1. Identify every doc reference that talks about “demo benchmark”, “demo tools”, or a “STORE transition plan” and note what needs rephrasing (notably `CLAUDE.md` and the implementation plan docs).
2. Replace those phrases with STORE-first language (e.g., “STORE benchmark”, “store client”, “adaptive architecture plan”), refresh the plan docs, and link this work via `docs/plan-store-default-implementation.md`.
3. Double-check anchors (`rg -n "AICODE-"`) to ensure no new violations were introduced.
4. Run `./scripts/lint-aicode.sh` to validate the anchor rules.

## Validation plan
- `./scripts/lint-aicode.sh`
- Manual spot-check (open the updated docs to ensure STORE-first language is clear)

## Rollback plan
- Restore the modified docs from git if STORE messaging causes confusion or the lint script fails.
