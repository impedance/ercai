<!-- AICODE-NOTE: STATUS/FOCUS living focus on repo navigation + docs upkeep -->
<!-- AICODE-NOTE: STATUS/ENTRY use this file to align on immediate tasks before editing code -->

# Status

## Current focus
- Monitoring the deterministic validation + uncertainty guards after the rollout so we can spot regressions in candidate confirmations and checkout guard behavior.
- Keeping the adaptive architecture documentation (README/plan/status/ADR-0003) aligned with the STORE-first messaging and the completed guard workflow.
- Expanding telemetry around validation errors, candidate confirmations, and checkout gating so the new invariants stay visible operationally.
- Watching the Cerebras `zai-glm-4.7` path to ensure schema enforcement plus rate limits behave the way they did for OpenRouter.
- Monitoring the new Cerebras rate limiter (10/min, 100/hour, 100/day) to ensure the free-tier pacing stays visible in the smoke tests, keep `docs/cerebras-rate-limits.json` aligned with the portal caps, and confirm the `LLM_REQUESTS_*`/`LLM_REQUEST_DELAY` overrides remain accurate when Cerebras updates quotas. <!-- AICODE-LINK: docs/plan-cerebras-rate-limits.md --> <!-- AICODE-LINK: docs/cerebras-rate-limits.json -->

## Next steps
1. **[Priority]** Run the STORE smoke test and benchmark when the challenge portal is available to ensure the guards hold under real workloads.
2. Keep tracking logs/metrics around candidate confirmations and python validation counts; capture recurring failures as they surface.
3. Refresh README, status, and implementation plans if further architecture tweaks are required by STORE guard insights.
4. Verify the recent ambiguity/coupon/inventory guards on the next STORE smoke run so the new blocks behave as expected.
5. Ensure the new validation success metrics appear in the task summary/logging so we stop seeing the `no inference statistics` warning mentioned in the plans.

## Recent verification
- `./scripts/lint-aicode.sh`
- `.venv/bin/python -m pytest tests/test_agent_helpers.py tests/test_deterministic_tools.py tests/test_python_execution.py tests/test_store_helpers.py tests/test_checkout_retry.py tests/test_uncertainty_guard.py tests/test_validation_gate.py`

## Known risks
- Candidate-confirmation prompts add extra steps; the guard will re-prompt until the LLM echoes a `Candidate <id>` phrase.
- Shorter validation outputs (mode=`validation`) can trigger `OutputTooLong` when the LLM returns a verbose proof; the agent now logs that guard and re-requests a succinct check.
- Quota failures on `Req_ComputeWithPython` still look like Python errors; successful logging in `agent.py` is critical for post-mortem analysis.

## Fast orientation commands
- `rg -n "AICODE-"` — find anchors before editing (required check).
- `rg -n "run_agent" agent.py` — review the policy loop and new guard classes before changing logic.
- `rg -n "ValidationTracker" agent.py` — see how validation + uncertainty are enforced.
- `rg -n "NextStep" schemas.py` — confirm the available tools and new `mode`/`intent` fields.
- `./scripts/lint-aicode.sh` — guard anchors and dates before committing changes.
