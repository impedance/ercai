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
- Hardening recent regressions: Python executor usability, plan-length validation retries, controlled ambiguity prompts, coupon/checkout gating, and inventory/budget pre-checks.

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

## Action plan (1–2h, по приоритету)
1. [x] P0 Python executor + prompt  
   - Разрешить безопасный однострочный exec (assign/assert/print), добавить `print/bool/any/all` в SAFE_BUILTINS.  
   - Обновить системный prompt: только однострочные выражения без многострочных текстов.  
   - Добавить unit-тест на executor (print, присваивание, assert, last_result).
2. [x] P0 last_result + хинты  
   - Сохранять payload store-вызовов в `python_context["last_result"]`.  
   - При NameError/SyntaxError — добавлять подсказку использовать last_result и однострочные выражения.
3. [x] P0 Retry при pydantic ValidationError (plan>5)  
   - Ловить в `llm.query` ошибки схемы и ретраить с напоминанием `plan<=5`, без прозы.
4. [ ] P1 Умеренный ambiguity-guard  
   - Триггер только по явным словам (`either/or/maybe/optional/?`), максимум одно уточнение; далее автопродолжение по Candidate 1.
5. [ ] P1 Купоны/checkout-гейт  
   - Блокировать checkout/ReportTaskCompletion при `coupon` с `discount` null/0; для “coupon doesn’t exist/requires item” — не чек-аутить с нулевой скидкой.
6. [ ] P1 Инвентарь/бюджет pre-check  
   - Если `available < requested`, автоматически снижать количество и логировать решение (без циклов уточнений).
7. [ ] P2 Метрики валидаций  
   - Логировать успешные валидации (`validation_tracker.records`) в финальный summary/steps, убрать “no inference statistics”.
8. [ ] P2 Проверки  
   - Прогнать `pytest` (включая новый тест executor), `./scripts/lint-aicode.sh`.

## 80/20 guardrails
- Минимальные фичфлаги для новых проверок (executor/ambiguity/coupon-гейт) с безопасными дефолтами.
- Сжатые таймауты/лимиты вывода для Python валидаций остаются обязательными.
- Структурное логирование купонных решений и checkout-инвариантов для быстрой диагностики.

## Validation plan
- `./scripts/lint-aicode.sh`
- `python -m pytest tests/test_agent_helpers.py tests/test_python_execution.py tests/test_deterministic_tools.py tests/test_store_helpers.py` (+ новый тест executor)
- STORE smoke test: проверить исчезновение SyntaxError/NameError в Python шагах, корректный купон/checkout-гейт, отсутствие зацикливания ambiguity.
- Полный STORE прогон: подтвердить, что tasks с купонами/инвентарём проходят без ложных checkout и без план>5 ошибок.

## Rollback plan
- Feature flag to disable compute/parse/validate tools in `agent.py`.
- Revert to prior prompt/policy if tool routing increases errors.
- Remove new tool schemas from `schemas.py` if they cause schema mismatch.
