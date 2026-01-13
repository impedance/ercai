# Implementation Plan: Adaptive Agent Architecture + Deterministic Tools

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Review ADR-0002 for Python execution and related tradeoffs.
- This plan now includes STORE reliability work; clean up leftover “demo → store transition” mentions so STORE is the baseline.

## Goal
Deliver a flexible agent architecture that can handle escalating benchmark complexity by:
- Adding deterministic compute + validation tools for algorithmic tasks.
- Introducing a standardized tool-result protocol (structured success/error payloads).
- Adding structured parsing and pre-submit validation flows.
- Implementing uncertainty handling (hypothesis + verification) to reduce ambiguous failures.
- Integrating STORE-specific reliability guards (pagination discipline, checkout invariant, coupon verification) into the core loop instead of ad-hoc prompts.
- Removing transitional wording: treat STORE as the default benchmark, not a migration from DEMO.

## Non-goals
- Full sandbox isolation (containers/seccomp) beyond the current eval-only Python sandbox.
- End-to-end model routing/ensemble orchestration across multiple LLM providers.
- A full policy-learning system (no RL or automated prompt tuning).
- Building a general UI or external monitoring service.

## Contracts / Risks to Preserve
- `ERC3_API_KEY` and `OPENROUTER_API_KEY` must exist before any run (see `docs/context.md`).
- All tool usage must flow through `NextStep`/`ReportTaskCompletion` schemas.
- LLM outputs must remain schema-aligned JSON before dispatching tools.
- Sandbox safety: no imports, no file/network access for compute tools.
- STORE invariants: pagination limits must be respected; successful tasks must perform `Req_CheckoutBasket`; coupon handling must rely on observed `discount`/`total`; basket parsing must tolerate nullable fields.

## Relevant AICODE anchors
- `AICODE-NOTE: NAV/MAIN` in `main.py`
- `AICODE-NOTE: NAV/AGENT` in `agent.py`
- `AICODE-NOTE: NAV/LLM` in `lib.py`
- `AICODE-NOTE: NAV/TESTS` in `scripts/lint-aicode.sh`
- `AICODE-CONTRACT: CONTRACT/REQUIRED_KEYS` in `docs/context.md`
- `AICODE-TRAP: TRAP/JSON_EXTRACTION` in `lib.py`

## Entry points / Affected files
- `schemas.py` (new tool schemas + unified tool result schema; consider tolerance for null basket items)
- `agent.py` (compute execution, validation, uncertainty workflow, tool dispatch, pagination helper, checkout guard, coupon comparison)
- `lib.py` (schema enforcement, result parsing, error handling signals; optional response normalization for STORE payloads)
- `docs/status.md` (current focus/next steps)
- `docs/decisions/*` (ADR for adaptive architecture/tool protocol, if needed)
- `docs/implementation-plan-template.md` (reference only, no changes)
- `tests/` (new unit tests for compute/validation/parsing and STORE reliability helpers)

## Step-by-step plan
1. Clean up transition wording: remove leftover “DEMO→STORE” phrasing from prompts/docs; treat STORE as the default benchmark (session metadata already set).
2. Review `agent.py`, `schemas.py`, and `lib.py` to map current tool flow, error handling, and logging.
3. Define a standard tool-result envelope (e.g., `{"ok": bool, "result": ..., "error": ...}`) and add schema support in `schemas.py`; include STORE-specific responses (basket parsing, coupon apply) so nullable fields don’t blow up.
4. Implement `Req_ComputeWithPython` execution (ADR-0002) with AST validation and whitelisted builtins; document allowed builtins in the prompt to avoid `print`/unsupported calls.
5. Add `Req_ValidateWithPython` (or reuse compute with validation helper) to enforce format/length/invariants before `ReportTaskCompletion` (for STORE: ensure checkout happened and basket total/discount match expectations).
6. Add `Req_ParseStructured` (CSV/JSON/list parsing) using Python + schema checks, returning structured results.
7. Implement STORE reliability guards in `agent.py`:
   - Pagination helper: cap `limit` to allowed threshold, iterate `offset` until `next_offset == -1`, and avoid repeated failing calls.
   - Checkout guard: require `Req_CheckoutBasket` before `ReportTaskCompletion`; surface invariant violations as errors.
   - Coupon verification: after `Req_ApplyCoupon`, call `Req_ViewBasket`, compare `discount`/`total`, and stop when the best coupon is applied; ignore coupons that keep `discount` null.
   - Basket tolerance: normalize `Resp_ViewBasket` when `items` is `null` to avoid validation crashes.
8. Implement an uncertainty workflow in `agent.py`:
   - If task is ambiguous, generate 2–3 interpretations.
   - Validate candidate outputs through compute/parse/validate tools.
   - Only submit when a candidate passes validation (and checkout in STORE).
9. Update system prompt/policy to:
   - Route deterministic operations to compute/parse tools.
   - Require validation before final answer/checkout.
   - Provide guidance on ambiguity resolution and STORE tool availability (remove demo-only tools).
10. Add tests:
   - Compute: string reversal, arithmetic, list transforms.
   - Parse: CSV split/index, JSON decoding, schema mismatch.
   - Validate: length/format checks, failure cases.
   - STORE helpers: pagination caps, coupon comparison logic, checkout guard, basket `null` normalization.
11. Update docs:
   - `docs/status.md` with current focus/progress.
   - Add ADR for tool protocol/uncertainty workflow if needed.
12. Run checks: `./scripts/lint-aicode.sh` and the most relevant tests.

### Step 3 Detailed Task Plan (1-2 hours)
Goal: ship a minimal, safe `Req_ComputeWithPython` tool end-to-end without touching other tools.

Scope:
- Add schema for `Req_ComputeWithPython`.
- Implement `execute_python()` with AST validation + safe builtins.
- Wire the agent loop to call compute tool and return its result.
- Add minimal unit tests for the executor.

Non-goals:
- No prompt rewrites beyond a small tool availability note.
- No new parsing/validation tools yet.
- No feature flags (unless needed to avoid regressions).

Checklist:
1. Inspect current `NextStep` union and tool dispatch path.
2. Add `Req_ComputeWithPython` in `schemas.py` and update the `NextStep` union.
3. Implement `execute_python()` in `agent.py`:
   - `ast.parse(..., mode="eval")`
   - restrict `__builtins__`
   - return `{"result": str(result), "error": None}` or error text
4. Wire `Req_ComputeWithPython` branch in the agent loop:
   - log tool call
   - execute
   - append tool call + tool result messages
5. Add tests (new `tests/test_python_execution.py`):
   - string reverse
   - list indexing
   - import attempt blocked
6. Sanity check by running a minimal spec2-like flow locally (manual or test).

Exit criteria:
- Unit tests pass.
- No changes needed in other tools to keep existing tasks working.

## Validation plan
- `./scripts/lint-aicode.sh`
- Unit tests for compute/parse/validate modules (to be added under `tests/`)
- STORE smoke test: verify pagination errors disappear, coupons reflect real discounts, checkout guard triggers, and basket parsing tolerates nulls.
- Re-run demo benchmark: confirm spec2 fix and no regressions on other tasks

## Rollback plan
- Feature flag to disable compute/parse/validate tools in `agent.py`.
- Revert to prior prompt/policy if tool routing increases errors.
- Remove new tool schemas from `schemas.py` if they cause schema mismatch.
