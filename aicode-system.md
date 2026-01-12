# Universal bootstrap prompt: README + AICODE + AGENTS (portable)

Copy/paste everything below into another coding agent to initialize the same navigation + anchor system in a new or existing repository.

---

## PROMPT (English, agent-ready)

You are an agent working in a repository that may be brand new or already has code. Your job is to initialize a lightweight “README as index + AICODE anchors + living status + ADRs” documentation and navigation system.

### Non-negotiable goals
1) Make the repo easy to navigate via `README.md` + `rg -n "AICODE-"` (no line-number links).
2) Keep “why/how to not break things” close to code with short, grep-friendly `AICODE-*` anchors.
3) Keep current focus and next steps in `docs/status.md` (short lists, not a diary).
4) Provide a two-step workflow for non-trivial changes: write an implementation plan first, then implement.
5) Integrate a local `lint:aicode` check and run available tests after changes.

### First: determine whether this repo is “new” or “existing”

If any of these are true, treat it as “new / unclear” and ask the user questions before writing files:
- No meaningful code yet, or only scaffolding.
- No `README.md`, or README is empty/placeholder.
- No test/lint commands are discoverable.
- You cannot confidently infer the project’s domain/stack from files.

#### Ask the user (keep it short, bullet form)
1) Project name + 1–2 sentence mission.
2) Primary stack/languages (or “unknown / decide for me”).
3) What are the “do not break” invariants (3–7 bullets)? If unknown, ask for permission to infer and propose.
4) Where should “current focus/next steps” live (default: `docs/status.md`)—confirm.
5) Preferred docs language (English by default) and preferred tone (terse vs. detailed).
6) Existing commands to run (install/dev/test/lint/build). If unknown, ask permission to infer from repo files.

If the repo is “existing”, you may proceed immediately, but still ask Q2/Q6 if commands are unclear.

### Phase 1: repo scan (do before editing)
1) Inspect repo structure (top-level dirs, key files).
2) Detect stack + commands:
   - Node: `package.json` scripts
   - Python: `pyproject.toml`, `pytest.ini`, `requirements*`
   - Go: `go.mod`, `Makefile`
   - Rust: `Cargo.toml`
   - Java: `build.gradle`, `pom.xml`
   - etc.
3) Search for existing anchor-like patterns:
   - Run `rg -n "AICODE-" .` (or a fallback if `rg` is unavailable; ask user to install ripgrep if missing).
4) Read any existing `README.md` and `docs/` to avoid deleting valuable info; you may reorganize.

### Phase 2: create/normalize the documentation structure

Create these files/directories if they don’t exist; if they exist, update them to match the system without breaking existing content.

#### 2.1 `AGENTS.md` (repo protocol; root)
Create/replace with a concise, strict protocol for agents and humans:
- “New navigation scheme”: `README.md` index + `AICODE-*` anchors + `docs/status.md` + `docs/decisions/*`.
- “Required documents”: list at least:
  - `docs/aicode-anchors.md`
  - `docs/context.md`
  - `docs/status.md`
  - `docs/decisions/*` (ADRs)
  - `docs/implementation-plan-template.md`
- “Session boot checklist” (mandatory):
  1) Read `AGENTS.md`
  2) Read `README.md` (repo map)
  3) Run `rg -n "AICODE-"` (narrow by dir if needed)
  4) Read `docs/context.md` + `docs/status.md`
  5) If product/roadmap relevant: read the repo’s plan doc (create `docs/roadmap.md` or `docs/product-plan.md` if none exists)
- “Two-step development (plan -> implementation)” for non-trivial changes:
  - Plan must include: scope + non-goals + affected entry points/files + relevant anchors to read/update + test/check list.
- “README as index (protocol)”:
  - Must include (minimum): Repository layout, Entry points, Common tasks, Search cookbook.
  - Use file paths + `rg -n` pointers (no line-number links).
  - If README index is stale after structural changes, update it.
- “AICODE rules (critical)” (mirror the rules in `docs/aicode-anchors.md`):
  - Only allowed prefixes.
  - `TRAP/CONTRACT` require date `[YYYY-MM-DD]`.
  - Before adding new anchors, search existing anchors to avoid duplicates.
- “Where to write context”:
  - Navigation: `README.md` (+ targeted `AICODE-NOTE: NAV/...` near code)
  - Status: `docs/status.md`
  - Mission/stack/invariants: `docs/context.md`
  - Why/tradeoffs: `docs/decisions/*` (+ `AICODE-LINK:` from code if needed)
- “Minimum done”:
  - Updated/removed affected anchors.
  - Updated README index if structure/entry points changed.
  - Updated `docs/status.md` if focus/plan changed.
  - Checks run: `lint:aicode` + project tests (or the closest equivalent).
- Optional: “Interaction rules” (only if the user requested).

#### 2.2 `docs/aicode-anchors.md` (normative rules + schema)
Create it using these normative rules (portable across repos):
- Purpose: keep critical context discoverable via `rg -n "AICODE-"`.
- Allowed prefixes (only these):
  - `AICODE-NOTE:`
  - `AICODE-TODO:`
  - `AICODE-CONTRACT:` (date required)
  - `AICODE-TRAP:` (date required)
  - `AICODE-LINK:`
  - `AICODE-ASK:`
- One anchor per line; first line must be self-contained in `rg` output.
- Must use valid comment syntax for the language (or HTML comments in Markdown).
- `CONTRACT/TRAP` must include a date `[YYYY-MM-DD]` on the same line.
- Lifecycle:
  - Update/remove anchors after behavior changes.
  - Convert/remove resolved `AICODE-TODO`.
  - Convert closed `AICODE-ASK` into a `AICODE-NOTE` with `decision:` + `ref:`.
- Topic namespace goes inside the text after `:` (do not invent new prefixes):
  - `NAV/<slug>` navigation entry points
  - `CONTRACT/<slug>` invariants (use with `AICODE-CONTRACT`)
  - `TRAP/<slug>` sharp edges (use with `AICODE-TRAP`)
  - `DECISION/<id>` ADR references
  - `STATUS/<slug>` (use only inside `docs/status.md`)
  - `TEST/<slug>` testing pointers
- Recommended fields (short): `ref:`, `scope:`, `risk:`, `test:`, `decision:`, `owner:`.
- Anti-patterns:
  - No essays/logs.
  - No secrets/tokens.
  - No obvious comments (“increment i”).
  - Don’t use `AICODE-TODO` as a global tracker (use `docs/todo.md` if needed).
- Include examples and “where to place anchors” guidance (entry points, storage/schema, data invariants, sharp edges, links).

#### 2.3 `docs/context.md` (concise mission/stack/invariants)
Create a short, stable context file:
- Mission + users + UX goals (short).
- Stack summary (detected/inferred; ask user if uncertain).
- Architecture patterns + invariants (“do not break” list).
- “Where to look first” entry points (paths).
- Put 2–4 HTML-comment anchors at the top (e.g., `AICODE-NOTE: CONTEXT/BOOT ...`, plus key `AICODE-CONTRACT` invariants if they are already known).

#### 2.4 `docs/status.md` (living focus)
Create a short status file:
- Current focus (1–3 bullets).
- Next steps (top 5).
- Known risks (short).
- Fast orientation commands (a few `rg -n` examples).
- Add 1–2 HTML-comment anchors at the top (`AICODE-NOTE: STATUS/FOCUS ...`, `AICODE-NOTE: STATUS/ENTRY ...`).

#### 2.5 `docs/decisions/ADR-0001-anchor-navigation.md` (why this system)
Create the ADR describing:
- Context: need fast navigation without fragile line links.
- Decision: README as map + AICODE anchors + status in `docs/status.md`.
- Consequences: pros/cons and discipline requirements.
- Related docs: `AGENTS.md`, `docs/aicode-anchors.md`, `docs/status.md`.

#### 2.6 `docs/implementation-plan-template.md`
Create a template for non-trivial changes:
- Quick orientation steps (read README/context/status + search anchors).
- Goal, Non-goals, Contracts/risks, Entry points/files, Step-by-step plan, Validation plan, Rollback plan.
- Validation must include `lint:aicode` + tests (adapt to stack).

### Phase 3: integrate an AICODE linter command
Goal: a simple local check that fails on:
1) unknown AICODE prefixes;
2) missing dates for `AICODE-CONTRACT` and `AICODE-TRAP`.

Implement in the most native way for the repo:
- If `package.json` exists: add `scripts/lint:aicode` and wire `scripts/lint-aicode.sh` (or a Node script) so `npm run lint:aicode` works.
- Otherwise: add `scripts/lint-aicode.sh` and document a command in README (or add a Makefile target if the repo already uses Make).

The linter should:
- Use `rg --pcre2` if available.
- Exclude heavy build dirs (examples: `.git`, `node_modules`, build outputs).
- Exclude `docs/**` and `*.md` from strict prefix/date validation (anchors in docs are okay but not enforced).

### Phase 4: update `README.md` into an index map
Rewrite/extend README to include these sections (minimum):
1) “For coding agents (read first)”
   - Point to `AGENTS.md`, then `docs/context.md` + `docs/status.md`, then `rg -n "AICODE-"`.
2) “Repository layout” (10–25 items)
   - `path` — purpose; search pointer: `AICODE-...` or a real `rg -n "..." path`.
3) “Entry points” (3–10)
   - The most important bootstrap/config/data-access/state/core-flow files; each with a search pointer.
4) “Common tasks”
   - Only commands that actually exist (from scripts/Makefile/etc).
5) “Search cookbook” (8–15 real `rg -n ...` commands)
   - Tailor to the detected stack (storage schema, migrations, API routes, auth, background jobs, selectors, etc).

Rules:
- Prefer file paths over prose.
- No line-number links.
- Keep each bullet short and actionable.

### Phase 5: seed minimal high-value AICODE anchors in code (only if the repo has code)
Do not spam anchors. Add a few strategic anchors to make navigation stable:
- 1–2 `AICODE-NOTE: NAV/...` near the primary entry point(s) and core modules.
- 1 `AICODE-NOTE: NAV/TESTS` pointing to how to validate key behavior.
- If you can identify real invariants, add 1–3 `AICODE-CONTRACT` anchors (with date).
- If you find a sharp edge/regression-prone area, add 1 `AICODE-TRAP` anchor (with date).

Before adding, always search for existing anchors to avoid duplicates.

### Phase 6: validation (must do before finishing)
1) Run the AICODE linter you integrated (`npm run lint:aicode`, `make lint-aicode`, or `./scripts/lint-aicode.sh`).
2) Run the repo’s existing tests (whatever is standard for the stack). If no tests exist, clearly report that and propose the minimum next step, but do not invent a whole testing framework without user consent.

### Deliverable
When done, report:
- Which files you created/updated (paths).
- The exact commands to run for `lint:aicode` and tests.
- Where to start reading (`README.md` -> `AGENTS.md` -> `docs/context.md` + `docs/status.md` -> `rg -n "AICODE-"`).

---

## Notes for the agent
- Keep everything short, grep-friendly, and maintainable.
- Do not add new `AICODE-*` prefixes; only use the allowed list.
- `AICODE-CONTRACT` and `AICODE-TRAP` must include `[YYYY-MM-DD]` on the same line.
