# `STORE` benchmark transition plan

## Orientation
- README.md, AGENTS.md, docs/context.md, docs/status.md already reviewed (per repository bootstrap checklist)
- `rg -n "AICODE-"` used to confirm existing anchors before touching files
- No additional ADR beyond ADR-0002 directly impacts STORE switch, but review if new invariants appear

## Goal
Switch the agent from the DEMO benchmark to the STORE benchmark: start sessions against `benchmark="store"`, drive tasks with `store` tools, and document the new flow without regressing existing DEMO behavior.

## Non-goals
- Re-architect the schema-guided reasoning loop beyond what's necessary for STORE tool bindings.
- Implement additional STORE-specific policies/heuristics (keep behavior minimal).
- Add new storage/integration layers outside `main.py`, `agent.py`, `schemas.py`, and supporting docs.

## Contracts / Risks to Preserve
- `ERC3_API_KEY`/`OPENROUTER_API_KEY` must still come from `.env` ([docs/context.md], ADR-0002). Respect existing anchor `AICODE-CONTRACT: CONTRACT/ENV_KEYS`.
- Keep deterministic Python execution and schema validation working for future DEMO usage.
- `Req_ComputeWithPython` sandboxing must remain untouched while wiring new tools.

## Entry points / Affected files
- `main.py`: switch session+metadata for STORE benchmark, ensure logging/metrics still work.
- `agent.py`: swap `demo_client` usage for `store_client`, update handling of store tool union.
- `schemas.py`: extend `NextStep.function` union (or create STORE-specific schema) to include `erc3.store.Req_*` definitions.
- `docs/status.md`/README: mention STORE support and new verification commands.
- `tests/`: see if existing tests need adjustments or new validation (maybe reuse existing test harness).

## Step-by-step plan
1. **Benchmark + session plumbing** (~1.5h)  
   - Update `main.py` to start a STORE session (`benchmark="store"`, adjust `name`/`architecture` metadata).  
   - Ensure `status.tasks` handling still works and `core.get_store_client` is available (inject additional helper if needed).  
   - Keep logging format identical so anchors remain valid.

2. **Store tool schema updates** (~1.5h)  
   - Import relevant `erc3.store` `Req_*` models and add them to `NextStep.function`, keeping existing DEMO tools available if needed (or create a STORE-specific schema).  
   - Document schema change near affected files with `AICODE-NOTE` anchors referencing STORE entry points.

3. **Agent loop adaptation** (~2h)  
   - Replace `demo_client = api.get_demo_client(task)` with `store_client = api.get_store_client(task)` (or make client selection configurable).  
   - Ensure agent logic dispatches to `store_client` for store tools and retains Python execution path unchanged.  
   - Wire STORE tool results back into `messages` history in the same shape as demo version so schema validations stay consistent.

4. **Docs/status + README updates** (~1h)  
   - Note STORE benchmark usage and relevant `rg -n` anchors in `README.md` and `docs/status.md` (update `STATUS/FOCUS` to mention switch if needed).  
   - Mention new entry point `agent.py` for STORE flow with `AICODE-NOTE: NAV/STORE_AGENT`.

5. **Validation + testing** (~1h)  
   - Run `./scripts/lint-aicode.sh` (ensures anchors still compliant).  
   - Execute existing tests (`python -m pytest tests/test_python_execution.py` or similar) to confirm nothing broke; optionally run STORE session in dry-run if environment allows.  
   - Review `logs/*` (after a sample run) to confirm STORE steps logged correctly.

## Validation plan
- `./scripts/lint-aicode.sh`
- `python -m pytest tests/test_python_execution.py`
- Optionally run `python main.py` with `ERC3_API_KEY`/`OPENROUTER_API_KEY` to ensure STORE session completes.

## Rollback plan
- Revert to DEMO by switching `main.py` back to `benchmark="demo"` and restoring the original `run_agent` client logic.  
- If new schema causes issues, keep `Req_ComputeWithPython` path but avoid dispatching STORE tools until resolved, then reintroduce incrementally.
