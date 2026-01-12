<!-- AICODE-NOTE: STATUS/FOCUS living focus on repo navigation + docs upkeep -->
<!-- AICODE-NOTE: STATUS/ENTRY use this file to align on immediate tasks before editing code -->

# Status

## Current focus
- **[2026-01-12]** Design and implement Python execution capability for algorithmic tasks (see ADR-0002)
  - Agent failed spec2 task due to LLM transcription errors in string reversal
  - Adding `Req_ComputeWithPython` tool for deterministic operations
  - Status: Architecture documented, implementation pending
- Document the `ercai` codebase and highlight the ERC3/OpenRouter integration points.
- Provide a lightweight navigation system (README + anchors + ADR) so new agents can bootstrap quickly.

## Next steps
1. **[Priority]** Implement Python execution tool (ADR-0002):
   - Update `schemas.py` with `Req_ComputeWithPython`
   - Add secure execution engine in `agent.py`
   - Update system prompt with usage guidelines
   - Test on failed spec2 task (target score: 0.0 → 1.0)
2. Wire the agent to additional free models or verify the existing Xiaomi/OpenRouter setup still functions.
3. Capture new invariants/traps if more APIs are added (link via `docs/decisions`).
4. Ship a lightweight testing harness if the ERC3 SDK exposes stable fixtures.
5. Expand `repo-erc3-agents/` references with README notes on which agents are closest to `ercai`.

## Known risks
- **[2026-01-12]** LLM transcription errors in algorithmic tasks (spec2: 0.0 score) - mitigation in progress via ADR-0002
- Missing API keys (`ERC3_API_KEY`/`OPENROUTER_API_KEY`) cause immediate startup failure.
- Heuristic JSON parsing in `lib.py` can misroute tool calls when the model returns extra text.
- No automated tests yet, so behavior has only been manually verified.

## Fast orientation commands
- `rg -n "AICODE-"` — find anchors before editing (required check).
- `rg -n "run_agent" agent.py` — review the policy loop before changing it.
- `rg -n "NextStep" schemas.py` — confirm tool contract definitions.
- `./scripts/lint-aicode.sh` — guard anchors and dates before committing changes.
