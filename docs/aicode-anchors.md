# AICODE Anchors

Purpose: keep critical context discoverable with `rg -n "AICODE-"`.

## Allowed Prefixes (only these)
- `AICODE-NOTE:`
- `AICODE-TODO:`
- `AICODE-CONTRACT:` (date required `[YYYY-MM-DD]`)
- `AICODE-TRAP:` (date required `[YYYY-MM-DD]`)
- `AICODE-LINK:`
- `AICODE-ASK:`

## Format Rules
- One anchor per line; the line must be self-contained in `rg` output.
- Use valid comment syntax for the language (Markdown uses `<!-- -->`).
- `AICODE-CONTRACT` and `AICODE-TRAP` must include `[YYYY-MM-DD]` on the same line.
- Before adding a new anchor, search existing anchors to avoid duplicates.

## Topic Namespace (after the colon)
Do not invent new prefixes. Use one of these namespaces in the anchor text:
- `NAV/<slug>` entry points
- `CONTRACT/<slug>` invariants (use with `AICODE-CONTRACT`)
- `TRAP/<slug>` sharp edges (use with `AICODE-TRAP`)
- `DECISION/<id>` ADR references
- `STATUS/<slug>` only in `docs/status.md`
- `TEST/<slug>` testing pointers

Recommended fields (short): `ref:`, `scope:`, `risk:`, `test:`, `decision:`, `owner:`.

## Lifecycle
- Update/remove anchors when behavior changes.
- Remove resolved `AICODE-TODO`.
- Convert closed `AICODE-ASK` into `AICODE-NOTE` with `decision:` and `ref:`.

## Anti-Patterns
- No essays/logs.
- No secrets/tokens.
- No obvious comments ("increment i").
- Do not use `AICODE-TODO` as a global tracker (use `docs/todo.md` if needed).

## Placement Guidance
- Entry points and core modules: `AICODE-NOTE: NAV/...` near the top.
- Invariants: `AICODE-CONTRACT: CONTRACT/...` near checks or validation.
- Sharp edges: `AICODE-TRAP: TRAP/...` right before risky logic.
- Cross-file coupling: `AICODE-LINK:` near the boundary.

## Examples
```js
// AICODE-NOTE: NAV/CONTENT entry: extractPageContent ref: content_script.js
// AICODE-CONTRACT: CONTRACT/SELECTION required user selection to export [2025-10-24]
// AICODE-TRAP: TRAP/CORS canvas taints, use background fetch fallback [2025-10-24]
// AICODE-LINK: ./epub_generator.js#createEPUB
```

```md
<!-- AICODE-NOTE: STATUS/FOCUS ref: docs/status.md -->
```
