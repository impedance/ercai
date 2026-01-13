# Implementation Plan: Completing the Adaptive Agent Architecture

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, and `docs/status.md`.
- Run `rg -n "AICODE-"` before touching anchors.
- Review `docs/implementation-plan-adaptive-agent-architecture.md` plus `docs/decisions/ADR-0002-python-execution-for-algorithmic-tasks.md` for the existing roadmap, guardrails, and tradeoffs.

## Goal
Finish the outstanding adaptive-agent roadmap: extend deterministic compute/validation semantics, add the uncertainty workflow, weave in STORE guardrail messaging, expand tests, and document the new invariants so the agent can be safely run.

## Non-goals
- Rework README structure beyond the existing index map.
- Touch anything inside `repo-erc3-agents/`.
- Introduce new LLM providers or routing mechanisms.

## Contracts / Risks to Preserve
- `ERC3_API_KEY` and `OPENROUTER_API_KEY` key validation (see `docs/context.md` anchoring `AICODE-CONTRACT: CONTRACT/REQUIRED_KEYS`).
- All tool flows must respect the `NextStep` schema (`schemas.py` anchors `AICODE-NOTE: NAV/MAIN`, `AICODE-NOTE: NAV/AGENT`, `AICODE-NOTE: NAV/LLM`).
- Python compute must stay sandboxed (refer to `python_executor.py` and the `AICODE-TRAP: TRAP/JSON_EXTRACTION` guidance in `lib.py`).
- STORE invariants (pagination, basket normalization, coupon validation, checkout guard) from `docs/implementation-plan...` and `store_helpers.py`.

## Entry points / Affected files
- `agent.py` – uncertainty workflow, validation tracking, tool dispatch, prompt tweaks, checkout guard.
- `python_executor.py` – surface `mode`/`intent`, validation limits, and context-friendly metadata.
- `deterministic_tools.py` – structured parsing helpers that back the new uncertainty logic.
- `store_helpers.py` – guard utilities that support the validation path (pagination caps, coupon checks, normalized views).
- `schemas.py` – `Req_ComputeWithPython` schema already includes `mode`/`intent`, ensure any doc/usage reflects it.
- `lib.py` – schema enforcement and hints that drive the prompt/policy updates.
- `tests/test_python_execution.py`, `tests/test_deterministic_tools.py`, `tests/test_store_helpers.py`, `tests/test_agent_helpers.py` – validate compute, parse, validation intent, and uncertainty helpers.
- `docs/status.md` – living focus and next steps.
- `docs/decisions/ADR-0003-uncertainty-and-validation-workflow.md` – capture the new tool protocol.

## Step-by-step plan
1. Review the existing deterministic compute story (schemas → `python_executor.py` → `agent.py`) and design how `mode`/`intent` drive validation before reporting completion; sketch the uncertainty workflow (candidate interpretations + deterministic guard checks).
2. Implement code changes: add validation tracking + uncertainty candidate handling in `agent.py`, pass `mode`/`intent` into `execute_python`, tighten `python_executor.py` output limits, and refresh the system prompt to call out validation/uncertainty behavior.
3. Expand tests (python executor, parse helper, store helpers, agent helpers) and create the new ADR summarizing the protocol/uncertainty workflow; update `docs/status.md` to reflect focus and link the ADR.
4. Run `./scripts/lint-aicode.sh` and `python -m pytest tests/test_agent_helpers.py tests/test_python_execution.py tests/test_deterministic_tools.py tests/test_store_helpers.py`.

## Validation plan
- `./scripts/lint-aicode.sh`
- `python -m pytest tests/test_agent_helpers.py tests/test_python_execution.py tests/test_deterministic_tools.py tests/test_store_helpers.py`

## Rollback plan
- Temporarily disable the validation guard in `agent.py` (skip the `validation_tracker` check) to revert to prior behavior.
- Revert the `python_executor` changes if validation limits block legitimate outputs.
- Remove the new ADR and revert `docs/status.md` if the new roadmap messaging causes confusion.
