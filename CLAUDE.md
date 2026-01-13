# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ercai** is an autonomous AI agent designed to compete in the ERC3 (Enterprise RAG Challenge) benchmarking platform. The agent automatically solves structured tasks by combining:

- **ERC3 SDK** - Connects to the challenge platform, manages sessions, and submits results
- **LLM reasoning** - Uses free OpenRouter-hosted models (e.g., Xiaomi Mimo) to understand tasks and plan actions
- **Tool execution** - Calls STORE APIs (e.g., `Req_ListProducts`, `Req_ViewBasket`, `Req_AddProductToBasket`, `Req_CheckoutBasket`) and the deterministic `Req_ComputeWithPython` helper to complete tasks

### How It Works

1. **Agent connects** to the ERC3 platform and registers a session for the STORE benchmark
2. **Receives tasks** from the platform (e.g., "Get the secret string and transform it")
3. **Uses LLM** to reason about the task and decide which tools to call
4. **Executes actions** via the ERC3 store client (list products, inspect baskets, manage coupons, checkout, or run Python helpers)
5. **Gets evaluated** by the platform with scores and logs

### Purpose

- **AI agent benchmarking** - Test how well autonomous agents solve structured tasks
- **Competition** - Agents compete for accuracy (see `flags=["compete_accuracy"]`)
- **Research** - Study how LLMs handle API-driven workflows with schema validation

This is essentially a sandbox for building and testing corporate AI agents that interact with external systems through structured APIs.

## Essential Commands

### Running the Agent
```bash
python main.py
```
Requires environment variables: `ERC3_API_KEY`, `OPENROUTER_API_KEY`, `MODEL` (optional, defaults to `openai/gpt-4o-mini`)

### Linting
```bash
./scripts/lint-aicode.sh
```
Validates AICODE anchor hygiene (required prefix format, dates on CONTRACT/TRAP entries)

## Navigation Protocol (Required Reading)

This repository follows the AICODE navigation system. Before making changes:

1. Read `AGENTS.md` - repo protocol and bootstrap checklist
2. Read `README.md` - repository map and entry points
3. Run `rg -n "AICODE-"` - discover all anchors before adding new ones
4. Read `docs/context.md` - mission, stack, and invariants
5. Read `docs/status.md` - current focus and next steps

For non-trivial work: write an implementation plan using `docs/plan-template.md` before implementing.

## Architecture Overview

### Core Components

**Session Orchestration** (`main.py`)
- Initializes ERC3 session with benchmark="store"
- Iterates through tasks from the ERC3 platform
- Manages task lifecycle: start_task → run_agent → complete_task → submit_session

-**Agent Loop** (`agent.py`)
- Schema-guided reasoning loop (max 10 steps per task)
- System prompt instructs agent to use STORE tools (browse catalog, view/add/remove basket items, apply/remove coupons, checkout) and the deterministic `Req_ComputeWithPython`
- Executes actions via `store_client.dispatch()` and logs `Req_ComputeWithPython` runs as auxiliary tool calls
- Logs LLM calls to ERC3 platform via `api.log_llm()`
- Terminates when `ReportTaskCompletion` is returned

**LLM Wrapper** (`lib.py`)
- OpenRouter-compatible client (via OpenAI SDK)
- Forces JSON-only responses by appending schema hints to user messages
- Heuristic fallback: extracts JSON between first `{` and last `}`
- **TRAP**: JSON extraction can misroute when model adds conversational text

**Schemas** (`schemas.py`)
- `NextStep`: wraps agent reasoning (current_state, plan, task_completed, function)
- `ReportTaskCompletion`: signals task completion to agent loop
- Union of STORE tools plus `Req_ComputeWithPython` for deterministic transformations

### Data Flow

1. ERC3 SDK provides task list via `session_status()`
2. Each task flows through: platform start → agent reasoning loop → platform complete
3. Agent uses LLM to generate `NextStep` schemas (thinking + tool call)
4. Tool results feed back into conversation history as tool messages
5. Loop continues until `ReportTaskCompletion` or step limit (10)

## Critical Invariants

### Environment Keys (main.py:16, lib.py:18)
Both `ERC3_API_KEY` and `OPENROUTER_API_KEY` must be set before runtime. Missing keys cause immediate startup failure.

### Schema Compliance (agent.py:30, lib.py:52)
LLM responses must validate against `NextStep` schema before dispatch. Platform rejects malformed tool calls.

### Read-Only References
Do not modify anything under `repo-erc3-agents/` - these are reference implementations from ERC3.

## AICODE Anchor Rules

Allowed prefixes (enforced by `./scripts/lint-aicode.sh`):
- `AICODE-NOTE:` - entry points, navigation
- `AICODE-TODO:` - pending work
- `AICODE-CONTRACT:` - invariants (requires `[YYYY-MM-DD]`)
- `AICODE-TRAP:` - sharp edges (requires `[YYYY-MM-DD]`)
- `AICODE-LINK:` - cross-references
- `AICODE-ASK:` - open questions

Before adding anchors, search existing ones with `rg -n "AICODE-"` to avoid duplicates.

## Known Risks

1. Heuristic JSON parsing in `lib.py:42-49` can fail when models return extra text
2. No automated tests - behavior is manually verified
3. Agent limited to 10 reasoning steps per task (agent.py:28)

## Where Context Lives

- **Navigation**: `README.md` + `AICODE-NOTE: NAV/...` anchors near code
- **Status**: `docs/status.md` (living focus)
- **Mission/Stack/Invariants**: `docs/context.md` (stable)
- **Decisions**: `docs/decisions/` (tradeoffs, ADRs)

## Development Workflow

For non-trivial changes:
1. Fill out `docs/plan-template.md`
2. Update affected `AICODE-*` anchors
3. Refresh `README.md` if entry points change
4. Update `docs/status.md` if focus shifts
5. Run `./scripts/lint-aicode.sh` before committing
