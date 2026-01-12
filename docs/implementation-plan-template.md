# Implementation Plan Template

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Review any relevant ADR in `docs/decisions/` for existing tradeoffs.

## Goal
<!-- Describe the desired outcome for this change -->

## Non-goals
- <!-- List what this change does not attempt to solve -->

## Contracts / Risks to Preserve
- <!-- Mention critical invariants, environment requirements, or monitoring expectations -->

## Entry points / Affected files
- <!-- Enumerate top-level files or modules that need attention -->

## Step-by-step plan
1. <!-- e.g., gather requirements or inspect data -->
2. <!-- implement code changes -->
3. <!-- update docs or anchors -->
4. <!-- run lints/tests -->

## Validation plan
- `./scripts/lint-aicode.sh`
- `# Add the most relevant tests or commands for this stack here` (fill in once known)

## Rollback plan
- <!-- e.g., revert feature flag, re-enable previous version, notify stakeholders -->
