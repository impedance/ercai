# AGENTS.md

This repository follows the AICODE navigation system described in `aicode-system.md`.

## Navigation System (required)
- README index + `rg -n "AICODE-"` anchors for fast discovery
- Living status in `docs/status.md`
- Stable context in `docs/context.md`
- Architectural decisions in `docs/decisions/*`

## Required Documents
- `docs/aicode-anchors.md`
- `docs/context.md`
- `docs/status.md`
- `docs/decisions/*`
- `docs/plan-template.md`

## Session Boot Checklist
1) Read `AGENTS.md`
2) Read `README.md` (repo map)
3) Run `rg -n "AICODE-"` (narrow by dir if needed)
4) Read `docs/context.md` + `docs/status.md`
5) If roadmap is relevant: read `docs/roadmap.md` or `docs/product-plan.md` (create if missing)

## Two-Step Development (plan -> implementation)
For non-trivial work, write an implementation plan first using
`docs/plan-template.md`, then implement.

Plan must include:
- Scope + non-goals
- Affected entry points/files
- Relevant AICODE anchors to read/update
- Risks/contracts to preserve
- Test/check list

## README as Index (protocol)
README must include:
- Repository layout (paths + purpose + search pointer)
- Entry points (with search pointers)
- Common tasks (real commands)
- Search cookbook (`rg -n` commands)

No line-number links. Keep bullets short and actionable.

## AICODE Rules (critical)
Allowed prefixes only:
- `AICODE-NOTE:`
- `AICODE-TODO:`
- `AICODE-CONTRACT:` (date required `[YYYY-MM-DD]`)
- `AICODE-TRAP:` (date required `[YYYY-MM-DD]`)
- `AICODE-LINK:`
- `AICODE-ASK:`

Before adding anchors, search existing ones to avoid duplicates.
For details, follow `docs/aicode-anchors.md`.

## Where to Write Context
- Navigation: `README.md` (+ targeted `AICODE-NOTE: NAV/...` near code)
- Status: `docs/status.md`
- Mission/stack/invariants: `docs/context.md`
- Why/tradeoffs: `docs/decisions/*` (+ `AICODE-LINK:` from code if needed)

## Minimum Done
- Updated/removed affected anchors
- README index refreshed if structure/entry points changed
- `docs/status.md` updated if focus/plan changed
- Checks run: `npm run lint:aicode` + repo tests (or closest equivalent)

<!-- AICODE-NOTE: NAV/AGENT_RESPONSE Если пользователь просит, отвечай на русском -->
- When the user explicitly asks, reply in Russian; otherwise stay in the language of the request.

## Development Environment
<!-- AICODE-NOTE: NAV/ENV Use `.venv` for Python tooling and tests -->
- Keep a `.venv/` in the repo root (add it via `python3 -m venv .venv` if missing) and run Python commands through `.venv/bin/python` so dependencies stay isolated.
- Install testing/dependency helpers with `.venv/bin/python -m pip install pytest` (repeat after recreating the venv) before running test suites.
- Run `./.venv/bin/python -m pytest ...` whenever tests are required; this aligns with the `Minimum Done` instruction about running repo tests.

## Repo-local rule
- Do not modify anything under `repo-erc3-agents/` (samples are read-only references).
