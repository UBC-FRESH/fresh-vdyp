# Handoff: fresh-vdyp

Date: 2026-11-09
Repository: <https://github.com/UBC-FRESH/fresh-vdyp>
Branch: `main`
Status: Phase 2 active; parent issue #13 on branch `feature/p2-coefficient-catalog`.

This note is the first thing a new session agent should read after `AGENTS.md`.

## What this project is

`fresh-vdyp` is a public Python interoperability layer for the BC VDYP7
coefficient bundle, console runner, and yield curves. It will:

- parse and catalog `VDYP_CFG/VDYP.CTR`, `.COE`, `.PRM`, and `.DAT` files;
- run `VDYP7Console` under a documented runtime;
- parse `csvyieldtable` output into typed curves;
- expose a typed curve API and public golden dataset;
- reimplement equation families incrementally in Python;
- validate each family against the official console output;
- provide a Typer CLI, FastAPI service, FRESH-style web UI, and bounded LLM
  assistant;
- become an optional package dependency for FEMIC.

It is **not** a claim that UBC-FRESH invented VDYP7, and it is not a full binary
rewrite.

## Read in this order

1. `AGENTS.md` — operating contract and quality gates.
2. `ROADMAP.md` — phases P0–P7 and the detailed plan.
3. `notes/plan/0001-program-plan.md` — mission, scope, targets, evidence levels.
4. `notes/plan/0002-data-provenance.md` — source/manifest/citation contract.
5. `notes/plan/0003-architecture.md` — package, runner, API, web, assistant.
6. `notes/plan/0004-validation-release.md` — golden tests and release gates.
7. `notes/reference/vdyp-inventory.md` — observed bundle and runtime.
8. `notes/reference/vdyp-model-map.md` — control sequences and coefficient families.
9. `notes/adr/` — accepted design decisions.

If present, also read the untracked local file:

```text
notes/local/README.md
```

It contains host-specific VDYP install paths and the current runtime status.
It is intentionally ignored by Git.

## Current baseline

- The repo was seeded from `UBC-FRESH/ubc-fresh-dev-workflow`.
- The dashboard is green: lint, format, mypy, tests, validator, docs.
- A local VDYP7 bundle is available; its path is in the ignored local note.
- `VDYP_CFG/coe` contains 40 `.COE`, 7 `.PRM`, and 33 `.DAT` files, all ASCII.
- `VDYP_CFG/VDYP.tcl` defines 101 yield-table columns.
- The native binaries are 32-bit Windows PE executables.
- The console runtime was not exercised during planning; Phase 3 must test it.

## First milestone

Do **not** start with a full Python VDYP rewrite.

Start with P0 → P1 → P2 → P3:

1. Phase 0 is complete and merged; issue #1 is closed.
2. Phase 1 is active: bundle inventory, control-file map, provenance contract,
   and fixtures on `feature/p1-source-inventory`.
3. Move to P2: coefficient/parameter catalog and parser.
4. Move to P3: console runner and CSV yield-table parser.

The first real deliverable is:

```text
fresh-vdyp bundle extract
fresh-vdyp bundle validate
fresh-vdyp bundle catalog
fresh-vdyp run console
```

plus a manifest, tiny fixtures, and tests.

## Non-negotiable rules

- Cite BC VDYP7 and the source file on every published value.
- Do not commit the raw `VDYP_CFG` bundle or large normalized assets.
- Do not start with a full binary decompile.
- Use `VDYP7Console` as the oracle for Python equations.
- Promote an equation family only after console validation.
- Unimplemented families return `not_implemented`, not guessed values.
- Every CLI/API/web/assistant answer exposes provenance.
- A failed runtime is recorded as a failed run, not filled with guessed values.
- The assistant is additive; the UI must work without it.

## Commands

```bash
cd /path/to/fresh-vdyp
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/dashboard.py
```

The dashboard must be green before every commit.

## Suggested first commit sequence

```text
P0.1 activate phase 0 and create bootstrap issue
P0.2 verify attribution, citation, and public-safety rules
P1.1 inventory VDYP bundle and yield-table schema
P1.2 parse VDYP.CTR and freeze the control map
P2.1 implement the .COE parser
P2.2 implement the .PRM/.DAT parser
P2.3 build the catalog and CLI
P3.1 build the console runner
P3.2 parse csvyieldtable output
```

## Handoff state

- Local repo: seeded and committed.
- Remote: private `UBC-FRESH/fresh-vdyp`, `main` pushed.
- Phase 0: complete. Pull request #5 merged as `b73362a`; issue #1 closed; child issues #2-#4 closed.
- Phase 1: complete. Pull request #12 merged as `d627751`; issue #6 closed; child issues #7-#11 closed.
- Phase 2: active on `feature/p2-coefficient-catalog`; parent issue #13, child issues #14-#19 open.
- Python package: not scaffolded yet; that is Phase 2 work after the control map.
- Data assets: not committed; extraction starts in Phase 2.
- Runtime: not yet exercised; test in Phase 3.
