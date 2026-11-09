# fresh-vdyp

A public, tested Python package for reading the BC VDYP7 coefficient and control
bundle, wrapping the VDYP7Console runner, exposing typed yield curves, and
validating incremental Python growth equations against the official console
outputs.

`fresh-vdyp` is an interoperability and reimplementation layer. It does not
claim authorship of VDYP7 or BC government data. It exists so the model's
plain-text coefficients, control files, and yield tables can be catalogued,
queried, tested, and used by tools such as FEMIC without a GUI boundary.

Repository: <https://github.com/UBC-FRESH/fresh-vdyp>

## Status

Phase 3 (console runner and yield parser) is queued for approval. `ROADMAP.md` lists the phases,
and GitHub issues carry the live status. The first working milestone is the
source inventory and coefficient catalog, not a full VDYP growth-model rewrite.

## What this is

- A parser and catalog for the VDYP7 `VDYP_CFG/coe` bundle.
- A control-file map for `VDYP.CTR`, `VDYPBACK.CTR`, `.COE`, `.PRM`, and `.DAT`.
- A runner and parser for `VDYP7Console` CSV yield tables.
- A typed Python curve API and public data assets.
- An incremental Python equation layer validated one family at a time.
- A Typer CLI, FastAPI service, FRESH-style web UI, and bounded LLM assistant.
- A package that FEMIC and other UBC-FRESH tools can depend on.

## What this is not

- A claim that UBC-FRESH invented VDYP7.
- A byte-for-byte clone of the native VDYP7 binaries.
- A substitute for measured field data or a complete growth-model validation.
- A place to commit raw government model bundles or credentials.

## Source and attribution

Every extracted coefficient, control file, curve, and derived value records:

```text
source
source version
source file
source SHA256
extraction date
citation
```

The original source remains the BC government's work. Reimplemented logic is
labelled `reimplemented` and validated against console outputs where possible.

## Plan

Read these in order:

1. [`notes/plan/0001-program-plan.md`](notes/plan/0001-program-plan.md)
2. [`notes/plan/0002-data-provenance.md`](notes/plan/0002-data-provenance.md)
3. [`notes/plan/0003-architecture.md`](notes/plan/0003-architecture.md)
4. [`notes/plan/0004-validation-release.md`](notes/plan/0004-validation-release.md)
5. [`notes/reference/vdyp-inventory.md`](notes/reference/vdyp-inventory.md)
6. [`notes/reference/vdyp-model-map.md`](notes/reference/vdyp-model-map.md)

## Quick start

This seed is a planning repository. The Python package and data workflows land
in Phase 2. Until then, the workflow gates are:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/dashboard.py
```

## Bundle inspection

Until the installable package lands, the first commands run from the repository:

```bash
export VDYP_CFG_DIR=/path/to/VDYP_CFG
python scripts/fresh_vdyp.py bundle validate
python scripts/fresh_vdyp.py bundle catalog
python scripts/fresh_vdyp.py bundle extract --output-dir data/normalized
```

`validate` checks required files, control targets, and key lookups. `catalog`
prints the family and row counts. `extract` writes normalized CSV files plus a
provenance manifest; the CSV files stay under ignored `data/normalized/`.

## Repository map

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Operating contract for coding agents |
| `HANDOFF.md` | First-read handoff note for a new session agent |
| `ROADMAP.md` | Plan of record and issue tracker map |
| `CHANGE_LOG.md` | Dated narrative of changes |
| `notes/plan/` | Detailed program, data, architecture, and validation plans |
| `notes/reference/` | VDYP inventory and coefficient-map facts |
| `notes/adr/` | Accepted design decisions |
| `docs/` | Sphinx RTFM surface |
| `scripts/check_workflow.py` | Workflow validator |
| `tests/` | pytest suite, including planning-surface checks |

## License and citation

Code is MIT licensed. Coefficient files and model outputs retain their original
BC government attribution. Cite the source model and file, not only this package.
