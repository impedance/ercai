<!-- AICODE-NOTE: CONTEXT/BOOT ercai is a corporate ERC3 agent stitching together ERC3 SDK + OpenRouter LLM hooks -->
<!-- AICODE-CONTRACT: CONTRACT/REQUIRED_KEYS ERC3_API_KEY and OPENROUTER_API_KEY must be defined before any run to avoid silent failures [2025-01-01] -->

# Context

## Mission
`ercai` is a corporate agent that bridges internal APIs with the ERC3 challenge platform; its primary job is to autonomously solve ERC3 benchmark tasks (currently the STORE benchmark) while leaning on free OpenRouter-hosted models whenever possible.

## Stack
- Python 3.11+ (virtual environment in `.venv`).
- ERC3 SDK for benchmark/session management.
- `openrouter.ai`/OpenAI-compatible client through `OpenAI` from the `openai` package.
- Cerebras Cloud (default `zai-glm-4.7` via `CEREBRAS_API_KEY`) for broader schema-backed reasoning when credentials exist.
<!-- AICODE-LINK: docs/cerebras.md -->
- `pydantic` for schema validation and `dotenv` for `ERC3_API_KEY`/`OPENROUTER_API_KEY` loading.

## Invariants (do not break)
1. ERC3/API credentials must never be hardcoded; they live in `.env` (or environment) and are validated before every run.
2. Tasks must always pass through `NextStep`/`ReportTaskCompletion` schemas so the ERC3 platform can validate tool usage.
3. LLM responses must be forced into JSON matching the expected schema before dispatching actions to reduce platform errors.

## Where to look first
- `main.py` for session orchestration and status logging (`AICODE-NOTE: NAV/MAIN` anchors live inside the file).
- `agent.py` for the schema-guided agent loop and ERC3 store tool calls.
- `lib.py` for the OpenRouter wrapper that enforces JSON-only replies.
- `docs/status.md` for the living focus, next steps, and risks.
- `docs/decisions/ADR-0001-anchor-navigation.md` for why this navigation+docs system exists.
