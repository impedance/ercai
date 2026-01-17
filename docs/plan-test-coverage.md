# Test Coverage Plan for STORE Guards

## Orientation
- AGENTS.md (navigation rules, plan checklist)
- README.md (repo entry points + search cookbook)
- docs/context.md and docs/status.md (mission, focus, anchors)
- Review docs/decisions/ADR-0001-anchor-navigation.md for anchor expectations
- Existing tests under tests/ to avoid overlapping with previous helpers

## Goal
Document and execute a prioritized plan for adding reproducible tests that lock in the successful STORE behaviors captured in the latest log, namely: (1) checkout retry after inventory shortfalls, (2) uncertainty/clarification flow requiring candidate confirmation, and (3) validation gating before reporting completion.

## Non-goals
- Refactoring production code or altering StoreGuard/UncertaintyManager implementations beyond what the tests need to instantiate them.
- Touching files under repo-erc3-agents/ (per repo rule).
- Adding more than the necessary scaffolding (e.g., avoid creating new fixtures unless required).

## Contracts / Risks to Preserve
- ERC3/OpenRouter credentials remain unset during tests; rely on fake clients.
- Validation guard requires at least one successful `mode="validation"` execution before completion (AICODE-CONTRACT logic from docs/context.md).
- Guard behavior must continue to log and block `ReportTaskCompletion` until validation/coupon conditions are satisfied.

## Entry points / Affected files
1. `tests/` – new test modules focusing on guard behavior.
2. `agent.py` – to understand the hooks used when simulating client responses and guard states.
3. `store_helpers.py` – for CouponVerifier/PaginationGuard references of expected API.

## Step-by-step plan
1. **Design scenario scaffolding** – sketch out fake store client behaviors (checkout failure, coupon rejection, missing validation) plus needed helper instance initialization and log expectations. (Priority: High)
2. **Test checkout retry behavior** – write a new test file that instantiates `StoreGuard`/`run_agent` with a burnout client that throws inventory errors once, ensures `StoreGuard.adjust_inventory_for_add` reduces quantity, and that the agent retries checkout successfully on second attempt. (Priority: High)
3. **Test uncertainty confirmation loop** – simulate an ambiguous task text, create a fake NextStep response that triggers `UncertaintyManager`, and verify candidate prompting plus reminder enforcement before completion. (Priority: Medium)
4. **Test validation gating** – ensure `ValidationTracker` prevents `ReportTaskCompletion` until a successful `Req_ComputeWithPython` with `mode="validation"` is recorded, then allow completion. (Priority: Medium)
5. **Document test flow** – add comments or docstrings in the new tests explaining their coverage alignment with log observations (inventory shortfall, clarification loop, validation guard). (Priority: Low)
6. **Update plan/status if needed** – if new anchors or focus statements arise from the tests, document them under README/`docs/status.md`. (Priority: Low)

## Validation plan
- `./scripts/lint-aicode.sh` (anchor hygiene)
- `./.venv/bin/python -m pytest tests/test_store_helpers.py tests/test_agent_helpers.py tests/test_deterministic_tools.py tests/test_python_execution.py` (existing suites)
- `./.venv/bin/python -m pytest tests/test_uncertainty_guard.py tests/test_checkout_retry.py tests/test_validation_gate.py` (new files once added)

## Rollback plan
- Revert `docs/plan-test-coverage.md` and any new tests if they introduce blocking failures before completion.
