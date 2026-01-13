# ercai

<!-- AICODE-NOTE: NAV/README repo map for ercai, use README + docs for onboarding -->
<!-- AICODE-LINK: docs/decisions/ADR-0001-anchor-navigation.md -->

Corporate agent canvas for ERC3 challengers: orchestrates the ERC3 SDK, a custom LLM wrapper, and OpenRouter tokens so the agent can solve STORE benchmark tasks via the challenge portal.
Docs and prompts treat STORE as the canonical benchmark focus; the adaptive agent architecture plan keeps that message aligned across deterministic tooling and navigation.
<!-- AICODE-LINK: docs/implementation-plan-adaptive-agent-architecture.md -->

## For coding agents (read first)
- `AGENTS.md` — repo protocol + bootstrap checklist + navigation expectations (read before editing).
- `docs/context.md` + `docs/status.md` — mission/stack context and living focus (status anchors at the top).
- `rg -n "AICODE-"` — find normalized anchors across code and docs before adding new ones.

## Repository layout
- `AGENTS.md` — navigation rules, mandatory documents, and the two-step plan requirement (search with `rg -n "AICODE-" AGENTS.md`).
- `README.md` — this index + quick commands + search cookbook (search pointer: `rg -n "AICODE-" README.md`).
- `main.py` — orchestrates ERC3 session lifecycle and iterates over tasks for the STORE benchmark (search `rg -n "start_session" main.py`).
- `agent.py` — store benchmark reasoning agent that routes tool calls through the store client (search `rg -n "run_agent" agent.py`).
- `lib.py` — OpenRouter/OpenAI client wrapper enforcing JSON output hints (search `rg -n "OpenRouter" lib.py`).
- `schemas.py` — Pydantic schemas describing tool usage (search `rg -n "NextStep" schemas.py`).
- `.env` — local secrets placeholder (do not commit real keys).
- `repo-erc3-agents/` — reference agents supplied by ERC3 for additional benchmarks (read `repo-erc3-agents/README.MD`).
- `scripts/lint-aicode.sh` — anchor policy checker (search `rg -n "AICODE-NOTE" scripts`).
- `docs/` — navigation/context/status plus decisions and plan template; read anchors before editing.
- `docs/implementation-plan-adaptive-agent-architecture.md` — outlines the adaptive, STORE-first architecture and deterministic tooling roadmap (search `rg -n "STORE" docs/implementation-plan-adaptive-agent-architecture.md`).

## Entry points
All entry points target the STORE benchmark as the default workload.
- `main.py` — entry script to bootstrap ERC3 session for the STORE benchmark, log tasks, run `run_agent`, and submit results (search pointer: `rg -n "submit_session" main.py`).
- `agent.py` — core reasoning agent driving STORE tools, logging tool uses, and signaling completion events (search pointer: `rg -n "run_agent" agent.py`).
- `lib.py` — LLM wrapper that enforces JSON schema compliance and retries via heuristics for tool extraction (search pointer: `rg -n "response_format" lib.py`).

## Common tasks
- `python main.py` — start a STORE benchmark session (requires `ERC3_API_KEY`, `OPENROUTER_API_KEY`, `MODEL`/`MICRO` env variables per `.env`).
- `./scripts/lint-aicode.sh` — verify anchors use only allowed prefixes and include dates on CONTRACT/TRAP entries.

## Search cookbook
Run these `rg -n` commands from the repo root for fast discovery:
1. `rg -n "AICODE-"` — locate anchors before adding new ones.
2. `rg -n "ERC3_API_KEY" -g'*.py'` — find where ERC3 auth is loaded.
3. `rg -n "OPENROUTER_API_KEY" -g'*.py'` — trace OpenRouter dependencies.
4. `rg -n "run_agent" agent.py` — inspect how the agent loop is invoked.
5. `rg -n "store_client" agent.py` — see tool dispatch patterns.
6. `rg -n "NextStep" schemas.py` — understand the NextStep schema.
7. `rg -n "model_dump_json" lib.py` — follow the logging and fallback path that binds to ERC3 tools.
8. `rg -n "submit_session" main.py` — verify the final submission step.
