<!-- AICODE-NOTE: STATUS/FOCUS living focus on repo navigation + docs upkeep -->
<!-- AICODE-NOTE: STATUS/ENTRY use this file to align on immediate tasks before editing code -->

# Status

## Current focus
- **[2026-01-12]** Design and implement Python execution capability for algorithmic tasks (see ADR-0002)
  - Agent failed spec2 task due to LLM transcription errors in string reversal
  - Added `Req_ComputeWithPython` tool backed by `python_executor.py` with timeout/output limits and new tests covering the spec2 reversal case
  - Status: Implementation complete (sandboxed exec, guard rails, and `tests/test_python_execution.py`)
- Document the `ercai` codebase and highlight the ERC3/OpenRouter integration points.
- Provide a lightweight navigation system (README + anchors + ADR) so new agents can bootstrap quickly.
- <!-- AICODE-LINK: docs/implementation-plan-adaptive-agent-architecture.md -->
- Treat the STORE benchmark as the baseline focus and continue improving reliability via the adaptive architecture plan.
- Reinforced README + plan messaging so docs and prompts now treat STORE as the canonical benchmark per `docs/implementation-plan-adaptive-agent-architecture.md`.
- Added structured parsing (`Req_ParseStructured`) and improved STORE guard helpers (pagination cap, coupon verification, basket normalization, checkout guard) to keep deterministic tools centralized.
- Broadened deterministic coverage with new unit suites (`tests/test_deterministic_tools.py`, `tests/test_store_helpers.py`) in addition to the Python executor tests.

## Next steps
1. **[Priority]** Extend deterministic tool coverage and validation headroom:
   - Reuse `Req_ComputeWithPython` via `mode`/`intent` flags for pre-submit validation rather than spinning up a new tool
   - Define format/length invariants and guard clauses before `ReportTaskCompletion`
   - Draft prompt guidance for ambiguity resolution around deterministic helpers
2. **[Priority]** Validate STORE benchmark flow:
   - Confirm `main.py` starts sessions with `benchmark="store"` and retains logging/metrics
   - Ensure `agent.py` routes tool calls through `store_client` and the store schema stays in sync
   - Run a smoke session or review logs to prove STORE tasks complete end-to-end (per the adaptive architecture plan)
3. Wire the agent to additional free models or verify the existing Xiaomi/OpenRouter setup still functions.
4. Capture new invariants/traps if more APIs are added (link via `docs/decisions`).
5. Ship a lightweight testing harness if the ERC3 SDK exposes stable fixtures.
6. Expand `repo-erc3-agents/` references with README notes on which agents are closest to `ercai`.

## Known risks
- **[2026-01-12]** LLM transcription errors in algorithmic tasks (spec2: 0.0 score) - mitigation in progress via ADR-0002
- Missing API keys (`ERC3_API_KEY`/`OPENROUTER_API_KEY`) cause immediate startup failure.
- Heuristic JSON parsing in `lib.py` can misroute tool calls when the model returns extra text.
- Automated tests currently cover only `tests/test_python_execution.py`; the rest of the flow still relies on manual verification.

## Fast orientation commands
- `rg -n "AICODE-"` — find anchors before editing (required check).
- `rg -n "run_agent" agent.py` — review the policy loop before changing it.
- `rg -n "NextStep" schemas.py` — confirm tool contract definitions.
- `./scripts/lint-aicode.sh` — guard anchors and dates before committing changes.
