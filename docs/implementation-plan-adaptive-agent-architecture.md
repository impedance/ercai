# Implementation Plan: Adaptive Agent Architecture + Deterministic Tools

## Orientation
- Read `README.md`, `AGENTS.md`, `docs/context.md`, `docs/status.md`.
- Run `rg -n "AICODE-"` to understand existing anchors before editing files.
- Review ADR-0002 for Python execution and related tradeoffs.
- This plan now includes STORE reliability work; keep STORE as the baseline benchmark when writing docs and prompts.

## Goal
Deliver a flexible agent architecture that can handle escalating benchmark complexity by:
- Adding deterministic compute + validation tools for algorithmic tasks.
- Introducing a standardized tool-result protocol (structured success/error payloads).
- Adding structured parsing and pre-submit validation flows.
- Implementing uncertainty handling (hypothesis + verification) to reduce ambiguous failures.
- Integrating STORE-specific reliability guards (pagination discipline, checkout invariant, coupon verification) into the core loop instead of ad-hoc prompts.
- Removing transitional wording: treat STORE as the default benchmark and keep the focus there.

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
- `agent.py` (compute execution, validation, uncertainty workflow, tool dispatch, pagination helper, checkout guard, coupon comparison; basket normalization lives here to avoid schema churn)
- `lib.py` (schema enforcement, result parsing, error handling signals; optional response normalization for STORE payloads if needed)
- `deterministic_tools.py` (structured parsing helpers that feed `Req_ParseStructured` and log schema warnings)
- `python_executor.py` (sandboxed Python execution guardrails: AST validation, safe builtins, timeout, and output limits)
- `store_helpers.py` (STORE guard utilities: pagination caps, normalized basket views, coupon verification, checkout tracking)
- `docs/status.md` (current focus/next steps)
- `docs/decisions/*` (ADR for adaptive architecture/tool protocol, if needed)
- `docs/implementation-plan-template.md` (reference only, no changes)
- `tests/test_python_execution.py`, `tests/test_deterministic_tools.py`, `tests/test_store_helpers.py` (unit suites that prove the new deterministic helpers and guardrails behave as expected)

## Outstanding tasks
- All previously listed implementation actions for the adaptive agent architecture are now in place; the focus has shifted to monitoring guard metrics and STORE runs so the new behavior stays reliable.

## 80/20 flexibility add-ons
- Feature flags per deterministic tool (compute/parse/validate intent) with safe defaults to disable new paths quickly.
- Deterministic tool guardrails: short CPU timeout and max output length to prevent hangs/memory blowups.
- Retry/fallback policy: if parse/validate fails, optionally return the raw LLM answer with a logged warning instead of hard-stopping.
- Structured logging for tool calls/results (success/error) to spot failure patterns without extra instrumentation.
- Minimal prompt addendum (not a rewrite) to route algorithmic work to deterministic tools and apply STORE guardrails (pagination cap, checkout requirement).

## Backlog (<= 2h per task, in priority order)
1. [ ] Draft the minimal prompt addendum for deterministic tools + STORE guardrails.
2. [ ] Design feature flags (env names, defaults) and injection points in the agent loop.
3. [ ] Document the `Req_ComputeWithPython` guardrails (AST, builtins, timeout, max output) so the prompt and docs can cite concrete safety limits.
4. [ ] Sketch the validation conveyor: pre-submit checks, retry vs. fail rules.
5. [ ] Write the initial test plan and skeleton tests for compute/parse/validate and STORE helpers.
6. [ ] Instrument metrics/logs that track deterministic tool usage, coupon guard verdicts, and checkout enforcement outcomes.

## Validation plan
- `./scripts/lint-aicode.sh` *(completed)*
- `python -m pytest tests/test_agent_helpers.py tests/test_python_execution.py tests/test_deterministic_tools.py tests/test_store_helpers.py` *(completed)*
- STORE smoke test: verify pagination errors disappear, coupons reflect real discounts, checkout guard triggers, and basket parsing tolerates nulls *(pending live STORE session)*.
- Re-run STORE benchmark: confirm spec2 fix and no regressions on other tasks *(pending benchmark access)*.

## Rollback plan
- Feature flag to disable compute/parse/validate tools in `agent.py`.
- Revert to prior prompt/policy if tool routing increases errors.
- Remove new tool schemas from `schemas.py` if they cause schema mismatch.
