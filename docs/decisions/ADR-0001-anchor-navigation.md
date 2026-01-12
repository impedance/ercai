# ADR-0001: Anchor-based navigation + living index

## Status
Accepted

## Context
This repo is an agent for the ERC3 corporate challenge. Without consistent documentation, future agents will spend time rediscovering entry points, stack requirements, and how anchors are used to annotate invariants.

## Decision
Adopt a lightweight navigation system composed of:
1. `README.md` as the canonical index with layout, entry points, commands, and a search cookbook.
2. `AICODE-*` anchors placed near entry points, invariants, and tests so `rg -n "AICODE-"` surfaces critical context.
3. `docs/status.md` as the living focus board and `docs/context.md` as the stable mission/stack/invariants snapshot.
4. `docs/decisions` to capture architectural tradeoffs and `docs/implementation-plan-template.md` to enforce a plan-first workflow.
5. A local `lint:aicode` command to enforce anchor hygiene across non-documentation files.

## Consequences
- Pros: newcomers can discover navigation via README + anchors; invariants stay close to code; the plan-first process keeps non-trivial work structured.
- Cons: maintenance overhead to keep anchors dated and README sections current; the linter must stay in sync with the allowed prefix list.
- Discipline: contributors must consult `AGENTS.md`, `docs/context.md`, `docs/status.md`, and run `rg -n "AICODE-"` before editing; non-trivial changes require filling the implementation plan template.

## Related
- `AGENTS.md`
- `docs/context.md`
- `docs/status.md`
- `docs/aicode-anchors.md`
- `docs/implementation-plan-template.md`
