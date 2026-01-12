<!-- AICODE-NOTE: STATUS/FOCUS living focus on repo navigation + docs upkeep -->
<!-- AICODE-NOTE: STATUS/ENTRY use this file to align on immediate tasks before editing code -->

# Status

## Current focus
- Document the `ercai` codebase and highlight the ERC3/OpenRouter integration points.
- Provide a lightweight navigation system (README + anchors + ADR) so new agents can bootstrap quickly.
- Implement and run the `lint:aicode` script to guard anchor hygiene.

## Next steps
1. Wire the agent to additional free models or verify the existing Xiaomi/OpenRouter setup still functions.
2. Capture new invariants/traps if more APIs are added (link via `docs/decisions`).
3. Ship a lightweight testing harness if the ERC3 SDK exposes stable fixtures.
4. Expand `repo-erc3-agents/` references with README notes on which agents are closest to `ercai`.
5. Track outstanding docs tasks in `docs/status.md` as more context appears.

## Known risks
- Missing API keys (`ERC3_API_KEY`/`OPENROUTER_API_KEY`) cause immediate startup failure.
- Heuristic JSON parsing in `lib.py` can misroute tool calls when the model returns extra text.
- No automated tests yet, so behavior has only been manually verified.

## Fast orientation commands
- `rg -n "AICODE-"` — find anchors before editing (required check).
- `rg -n "run_agent" agent.py` — review the policy loop before changing it.
- `rg -n "NextStep" schemas.py` — confirm tool contract definitions.
- `./scripts/lint-aicode.sh` — guard anchors and dates before committing changes.
