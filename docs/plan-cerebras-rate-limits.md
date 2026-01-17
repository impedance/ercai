# <!-- AICODE-NOTE: PLAN/RATE_LIMIT document the rate-limit workstream ref: lib.py -->

## Orientation
- `lib.py` (AICODE-NOTE: NAV/LLM) contains the OpenRouter/Cerebras wrapper that issues every completion request.
- `README.md` + `docs/context.md`/`docs/status.md` describe the LLM configuration story and living focus (anchors already in place).
- No ADR directly covers rate-limiting, but we must preserve the schema-enforcement and guard logging contracts described in `docs/context.md`.

## Goal
Enforce Cerebras free-tier request quotas (10/min, 100/hour, 100/day) inside `MyLLM` while still allowing overrides via environment variables; update the public docs so operators know why the pacing exists and how to adjust it.

## Non-goals
- Removing or reworking the JSON schema recovery/repair logic in `lib.py`.
- Touching the ERC3 session orchestration or STORE agent logic; the rate limiter only lives in the LLM wrapper.
- Implementing a fully pluggable multi-provider quota controller beyond Cerbras/OpenRouter defaults.

## Contracts / Risks to Preserve
- Keep the schema-first parsing guards and `AICODE-TRAP: TRAP/JSON_EXTRACTION` heuristics untouched while inserting the rate limiter.
- Avoid blocking all requests by ensuring the limiter only enforces positive quotas and falls back to no-limit when values are absent/zero.
- Maintain the current logging cadence so ops can diagnose why a pause happened (e.g., a log entry when we sleep).

## Entry points / Affected files
- `lib.py` (AICODE-NOTE: NAV/LLM) – add the rate-limiter helper, configure Cerebras defaults, and call it before `chat.completions.create`.
- `README.md` (AICODE-LINK: docs/cerebras.md) – mention the new limits and optional `LLM_REQUESTS_*` overrides under the LLM configuration section.
- `docs/status.md` (AICODE-NOTE: STATUS/ENTRY) – note that the living focus now includes tracking the Cerebras rate-limiting guard and how to tune it if the portal status changes.

## Step-by-step plan
1. Assemble a JSON registry (e.g., `docs/cerebras-rate-limits.json`) describing every Cerebras model of interest with its minute/hour/day request caps and a recommended `delay_seconds` to stay safely under the quota (free tier, preview, etc.). Make sure the README or docs reference this file for operators.
2. Implement a loader in `lib.py` that reads the JSON file only when using Cerebras, picks the current `CEREBRAS_MODEL`, and defaults to the matching limits plus delay; merge in any positive overrides from `LLM_REQUESTS_PER_MINUTE`, `_PER_HOUR`, `_PER_DAY`, or `LLM_REQUEST_DELAY` environment variables before instantiating the limiter.
3. Upgrade `RateLimiter` so it enforces both sliding-window quotas and the optional delay between requests (sleeping as needed without busy waits). Ensure it can be safely disabled (when all limits/delay are `None`), but still logs when it pauses.
4. Replace the hardcoded Cerebras defaults in `MyLLM` with values from the loader; keep the existing OpenRouter path untouched (i.e., the limiter stays disabled when no Cerebras config is present).
5. Update docs/status/README anchors to describe the configurable model-to-limit mapping, where to find the JSON, and how to adjust the overrides if Cerebras changes quotas; mention the living focus on monitoring this limiter.
6. Run `./scripts/lint-aicode.sh` and the relevant pytest subset (`./.venv/bin/python -m pytest tests/test_python_execution.py`) once the loader is in place to catch regressions and verify logs.

## Validation plan
- `./scripts/lint-aicode.sh`
- `./.venv/bin/python -m pytest tests/test_python_execution.py`

## Rollback plan
- Revert the `lib.py` changes (removing the limiter) and restore the original docs if the new pacing causes unexpected stalls or the overrides do not behave.
