# ADR-0003: Deterministic uncertainty and validation workflow for STORE tasks

## Status
Proposed (2026-01-15)

## Context
STORE benchmark requests often surface ambiguity ("add a product or checkout?") and have previously completed with marginal validation (agents reported completion without verifying length, format, or checkout). Those gaps exacerbate erratic scoring and make debugging labor-intensive because tool results are not framed as deterministic checkpoints.

We already have deterministic compute (`Req_ComputeWithPython`) with sandboxed execution (see ADR-0002) and STORE guard helpers (pagination, coupon verification, basket normalization). The missing piece is a policy that:
- forces the LLM to pick and confirm one of several candidate interpretations when the request is vague,
- runs explicit pre-submit validation steps using deterministic Python code tagged with intents,
- only allows `ReportTaskCompletion` once the STORE checkout invariant and a validation proof exist.

## Decision
We introduce three linked guardrails:

1. **Validation tracking** – `Req_ComputeWithPython` now exposes `mode`/`intent` so the agent can tell analytics vs. validation executions. The loop records every validation result, rejects completion if there is no successful validation, and prompts the LLM to rerun the deterministic check synchronized with a descriptive intent (length, format, coupon).
2. **Uncertainty workflow** – ambiguous descriptions automatically produce 2–3 structured, deterministic candidate interpretations (parsed via `deterministic_tools`). The system asks the LLM to confirm one candidate by ID before doing irreversible mutations, and completion is disallowed until that candidate is confirmed plus checkout has happened.
3. **Prompt & guard updates** – the system prompt explicitly calls out the validation workflow, instructs the agent to refer to candidate IDs, and reinforces that deterministic python validations must precede `ReportTaskCompletion`.

These changes keep the STORE invariant (checkout + structured validation) discoverable in code (agent guard, `store_helpers`) and documentation (`docs/status.md`, this ADR). They also ensure deterministic parse helpers and python guardrails stay central to the workflow instead of ad-hoc prompts.

## Consequences
- ✅ Enforces reproducible parity checks (size, format) before completion so corrections can be replicated.
- ✅ Provides structured traceability for ambiguous requests (candidate IDs + parse logs) to help rerun/triage tasks.
- ⚠️ Introduces more prompts/responses (candidate confirmation, validation reminder) which might increase step counts but improves reliability.
- ⚠️ Adds a small coordination cost: all python validations now require a descriptive `intent`, and new guard logic demands careful logging.

## Implementation
1. Update `python_executor.py` to surface `mode`/`intent` limits and enforce shorter validation outputs.
2. Extend `agent.py` with `ValidationTracker` and `UncertaintyManager`, integrate the guard logic, and refresh the system prompt to describe the workflow.
3. Expand tests (`tests/test_agent_helpers.py`, `tests/test_python_execution.py`, `tests/test_deterministic_tools.py`, `tests/test_store_helpers.py`) plus logs.
4. Document the new focus in `docs/status.md` (current focus + next steps) and link back to this ADR.

## Related
- `docs/implementation-plan-adaptive-agent-architecture.md`
- `docs/plan-complete-adaptive-agent.md`
