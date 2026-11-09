# fresh-vdyp Roadmap

This roadmap is the plan of record and the issue tracker map for `fresh-vdyp`.
Keep it in step with the GitHub issues, `CHANGE_LOG.md`, and `notes/`.
`scripts/check_workflow.py` parses the phase headers, status lines, and
checkboxes below, so keep their format.

Every phase starts as `planned` with `Parent issue: TBD`. Activate a phase only
after its parent issue exists and the maintainer approves it.

## Issue Tracker Map

| Phase | Parent issue | Branch | Status |
| --- | --- | --- | --- |
| P0 Bootstrap and attribution | #1 | `feature/p0-bootstrap` | complete |
| P1 Source inventory and control map | #6 | `feature/p1-source-inventory` | complete |
| P2 Coefficient catalog and parser | #13 | `feature/p2-coefficient-catalog` | complete |
| P3 Console runner and yield parser | #21 | `feature/p3-console-runner` | complete |
| P4 Curve API and public datasets | #29 | `feature/p4-curve-api` | complete |
| P5 Incremental Python equations | #36 | `feature/p5-python-equations` | complete |
| P6 CLI, API, web, and agent | #44 | `feature/p6-interfaces` | pr-open |
| P7 Validation, packaging, and FEMIC integration | TBD | `feature/p7-release-integration` | planned |

## Lifecycle Map

| Stage | Phases | Exit criteria |
| --- | --- | --- |
| Bootstrap and inventory | P0, P1 | Attribution, bundle inventory, and control-file map recorded |
| Data and runner | P2, P3 | Coefficient catalog and console yield parser pass their gates |
| Curves and equations | P4, P5 | Typed curve API and at least one validated equation family |
| Interfaces | P6 | CLI, API, FRESH-style web UI, and assistant tools pass tests |
| Verify and release | P7 | Golden checks, package build, release assets, and FEMIC integration |

## Conventions

- A phase is `P<n>`. A task is `P<n>.<m>`. A subtask is a checklist item inside
  the task's issue body. Three levels at most.
- Status values are `planned`, `active`, `pr-open`, `complete`, and `deferred`.
- A phase becomes `complete` only after its pull request merges to `main` and its
  parent issue closes.
- Every published artifact carries source, version, path, SHA256, and citation.
- `fresh-vdyp` is a reimplementation and interoperability layer. It does not
  claim authorship of VDYP7 or BC government data.

## Phase 0: Bootstrap and attribution

Parent issue: #1
Branch: `feature/p0-bootstrap`
Status: complete

Goal: make the repository's public purpose, attribution, and agent contract
unambiguous before code lands.

- [x] P0.1 Adapt `README.md`, `AGENTS.md`, `CITATION.cff`, and `LICENSE`
- [x] P0.2 Add source-attribution and no-authorship rules to the docs
- [x] P0.3 Confirm the workflow validator, tests, and docs build pass
- [x] P0.4 Create the GitHub repository and Phase 0 parent issue

Acceptance criteria:

- A reader can tell what `fresh-vdyp` is, what it is not, and which BC sources it
  depends on.
- The seed's validator and docs gates are green.
- Attribution language appears in `README.md`, `AGENTS.md`, and `CITATION.cff`.

## Phase 1: Source inventory and control map

Parent issue: #6
Branch: `feature/p1-source-inventory`
Status: complete

Goal: inventory the VDYP7 bundle and freeze the control-file and provenance
contract before extraction begins.

- [x] P1.1 Inventory install binaries, configuration, coefficient, and sample files
- [x] P1.2 Parse `VDYP.CTR`, `VDYPBACK.CTR`, and report column definitions
- [x] P1.3 Map control sequences to `.COE`, `.PRM`, and `.DAT` files
- [x] P1.4 Write the data-provenance contract and source-citation manifest
- [x] P1.5 Capture tiny fixtures and a golden console-output inventory

Acceptance criteria:

- Every source file has a stable identifier, source version, path, and SHA256.
- The control-sequence map explains which coefficient files drive which steps.
- Yield-table columns and units are documented.
- No raw government bundle is committed; only fixtures and manifests are tracked.

## Phase 2: Coefficient catalog and parser

Parent issue: #13
Branch: `feature/p2-coefficient-catalog`
Status: complete

Goal: convert the plain-text coefficient bundle into a normalized, validated
catalog.

- [x] P2.1 Implement `.COE` family parsers
- [x] P2.2 Implement `.PRM`, `.DAT`, and `VDYP.CTR` parsers
- [x] P2.3 Infer family, species/BEC, site-curve, and parameter keys
- [x] P2.4 Write normalized Parquet/CSV plus checksum manifest
- [x] P2.5 Add `fresh-vdyp bundle extract`, `validate`, and `catalog` commands
- [x] P2.6 Add parser, schema, and catalog tests

Acceptance criteria:

- Every coefficient row round-trips through raw, normalized, and manifest forms.
- Column counts, species keys, BEC keys, and control references validate.
- The catalog exposes equation family, source file, row count, and columns.
- A user can inspect the bundle without the Windows UI.

## Phase 3: Console runner and yield parser

Parent issue: #21
Branch: `feature/p3-console-runner`
Status: complete

Goal: run `VDYP7Console` safely and turn its CSV yield tables into typed rows.

- [x] P3.1 Implement runtime discovery and a Wine/Windows adapter
- [x] P3.2 Build a minimal polygon/layer input fixture
- [x] P3.3 Run `VDYP7Console` and capture stdout, stderr, and message files
- [x] P3.4 Parse `csvyieldtable` output into typed curve rows
- [x] P3.5 Add runner and parser tests with a golden output
- [x] P3.6 Record runtime failures without substituting invented values

Acceptance criteria:

- A known input produces a parsed curve table with source and runtime metadata.
- Missing binary, config, or Wine paths fail with a clear error.
- Output columns and units match the VDYP yield-table schema.
- A failed run is recorded as a failed run, not a silent fallback.

## Phase 4: Curve API and public datasets

Parent issue: #29
Branch: `feature/p4-curve-api`
Status: complete

Goal: expose a stable typed curve API and publish a small public curve dataset.

- [x] P4.1 Define `CurveQuery` and `CurvePoint` models with provenance
- [x] P4.2 Build a curve service over parsed console outputs
- [x] P4.3 Add age/year queries, units, and explicit unsupported cases
- [x] P4.4 Publish a golden curve dataset and manifest
- [x] P4.5 Add API, property, and regression tests

Acceptance criteria:

- A query returns typed volumes, heights, diameters, and density with provenance.
- Unsupported species/site combinations fail explicitly.
- The golden dataset reproduces from a documented input and console version.
- No curve is published without source and runtime metadata.

## Phase 5: Incremental Python equations

Parent issue: #36
Branch: `feature/p5-python-equations`
Status: complete

Goal: reimplement documented equation families in Python and validate each one
against the console oracle.

- [x] P5.1 Implement whole-stem volume (`VTOTREG4`) and validate
- [x] P5.2 Implement close-utilization volume (`REGVCU`) and validate
- [x] P5.3 Implement utilization volume (`REGVU`) and validate
- [x] P5.4 Implement height/Lorey height (`REGHL`) and validate
- [x] P5.5 Implement BA and DQ increment families and validate
- [x] P5.6 Add a family-by-family validation matrix and tolerance report

Acceptance criteria:

- Each implemented family has an equation note, unit tests, and a console
  validation case.
- Unimplemented families return `not_implemented`, not guessed values.
- A family is promoted only when its validation error is within the documented
  tolerance.
- The package never claims full VDYP parity.

## Phase 6: CLI, API, web, and agent

Parent issue: #44
Branch: `feature/p6-interfaces`
Status: pr-open

Goal: make the package usable by people and agents through a typed API, CLI,
FRESH-style web UI, and bounded assistant tools.

- [x] P6.1 Build the Typer CLI and command contracts
- [x] P6.2 Build the FastAPI service and typed response models
- [x] P6.3 Build the FRESH-style bundle, curve, and validation UI
- [x] P6.4 Add LLM tools for catalog search, curve query, provenance, and validation
- [x] P6.5 Add API, CLI, UI, and assistant tests

Acceptance criteria:

- Every web/assistant answer exposes its source file, control sequence, and query
  inputs.
- The assistant cannot invent a coefficient, equation, or curve.
- CLI and API share the same typed service layer.
- The UI works without an LLM; the assistant is additive.

## Phase 7: Validation, packaging, and FEMIC integration

Parent issue: TBD
Branch: `feature/p7-release-integration`
Status: planned

Goal: prove the package, publish it, and make it a usable dependency for FEMIC.

- [ ] P7.1 Run golden regression against VDYP7Console and FEMIC outputs
- [ ] P7.2 Build and test the Python package and data manifest
- [ ] P7.3 Publish release assets and a stable data manifest
- [ ] P7.4 Add the FEMIC dependency and back-link documentation
- [ ] P7.5 Write release notes, known gaps, and citation instructions

Acceptance criteria:

- A clean environment installs the package and uses the data assets.
- FEMIC can import `fresh_vdyp` and call a documented curve or validation query.
- Golden checks pass; unsupported equations and gaps are explicit.
- Release notes cite VDYP7, the control files, and all source coefficients.

## Detailed Next Steps Notes

1. Create the GitHub repository and the Phase 0 parent issue. This needs
   maintainer approval.
2. Activate Phase 0 by setting its parent issue number and its status to
   `active`, here and in the tracker map.
3. Read `notes/plan/0001-program-plan.md` before opening any code task.
4. Read `notes/reference/vdyp-inventory.md` and
   `notes/reference/vdyp-model-map.md` before touching coefficient files.
5. Do not implement Phase 5 equations until Phase 1's control map and Phase 3's
   console oracle are green.
