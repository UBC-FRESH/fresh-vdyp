# fresh-vdyp program plan

Date: 2026-11-09
Status: planning baseline
Owner: UBC-FRESH

## Mission

Make BC's VDYP7 coefficient bundle, console runner, and yield curves usable from
Python, with explicit provenance and tests, so public research and UBC-FRESH
tools can query the model without a Windows GUI boundary.

`fresh-vdyp` is an interoperability and reimplementation layer. It does not
claim authorship of VDYP7 or BC government data.

## Users

- UBC-FRESH researchers who need VDYP curves in Python.
- FEMIC and related tools that need a stable curve and coefficient package.
- Public users who need to inspect the plain-text VDYP coefficient bundle.
- Reviewers who need to see the source and validation for every published value.

## Scope

In scope:

1. Extract and catalog the plain-text `VDYP_CFG/coe` bundle.
2. Parse `VDYP.CTR`, `VDYPBACK.CTR`, `.COE`, `.PRM`, and `.DAT` files.
3. Run `VDYP7Console` under a documented runtime and parse `csvyieldtable` output.
4. Publish typed yield curves with source and runtime metadata.
5. Reimplement equation families incrementally in Python.
6. Validate each family against the official console output.
7. Provide a Python API, Typer CLI, FastAPI service, FRESH-style web UI, and
   bounded LLM assistant.
8. Package `fresh-vdyp` so FEMIC and other UBC-FRESH tools can depend on it.

Out of scope:

- A byte-for-byte clone of the native VDYP7 binaries.
- Full model parity in the first release.
- Replacing the official console runner before a family is validated.
- Committing raw government bundles or large data assets.
- Paid data acquisition, field campaigns, or new remote-sensing purchases.

## Three targets

### Target A — public data and runner layer

Extract the bundle, wrap the console, parse yield tables, and publish typed
curves. This is the first release and the direct analogue of `fresh-tipsy`.

### Target B — independent Python growth engine

Implement one equation family at a time using the `.COE` coefficients and the
control-file map. Validate each family against the console oracle.

### Target C — full standalone clone

Possible only after substantial reverse engineering or access to the full model
design documentation. Not the first target.

## Product shape

```text
VDYP bundle                (external, not committed)
        ↓
parser + control map       (committed code)
        ↓
coefficient catalog        (release artifacts + manifest)
        ↓
console runner + parser    (committed code)
        ↓
typed curve API / dataset
        ↓
incremental Python equations
        ↓
CLI / API / web / assistant
        ↓
FEMIC dependency
```

## Phase shape

| Phase | Outcome |
| --- | --- |
| P0 | Attribution, license, citation, agent contract |
| P1 | Bundle inventory and control-file map |
| P2 | Coefficient/parameter catalog and parser |
| P3 | Console runner and yield-table parser |
| P4 | Typed curve API and public datasets |
| P5 | Incremental validated Python equations |
| P6 | CLI, API, web UI, and assistant |
| P7 | Golden validation, packaging, and FEMIC integration |

## Evidence levels

Every output carries one of:

```text
source_table          directly read from a VDYP control/coefficient file
model_output          produced by a VDYP7Console run
reimplemented         produced by fresh-vdyp code
validated_against     matches a named console output within tolerance
experimental          documented but not yet fully validated
not_implemented       equation family not yet ported
```

No output is published without a source and an evidence level.

## Main risks

- The native VDYP console may fail under Wine or a missing runtime.
- The `.COE` files contain coefficients but not always the equation form.
- Some control sequences and column positions need confirmation.
- Full model parity requires the design documentation or targeted reverse
  engineering.
- FAN$IER is out of scope; this package is about VDYP growth curves.

## Definition of done for the first public release

- The bundle catalog covers all accessible `coe` files and control files.
- A clean environment can install the package and fetch the data manifest.
- A user can run the console, parse curves, and query the typed API.
- At least one Python equation family is validated against the console.
- FEMIC can depend on the package and call one documented curve query.
- Every artifact cites its BC source and carries an evidence level.
