# Validation, release, and FEMIC integration plan

Date: 2026-11-09
Status: draft

## Validation ladder

### Bundle extraction

- Raw file SHA256 matches the manifest.
- Field count matches the declared family grammar.
- Control-sequence references resolve to existing files.
- Species/BEC keys and curve groups are explicit.
- No duplicate asset IDs.
- Normalized row count matches the raw data block.

### Console runner

- A known fixture produces a yield table.
- Missing console, config, or Wine path fails explicitly.
- stdout, stderr, exit code, and message file are captured.
- A failed run is recorded as a failed run.
- The same input and runtime version reproduce the same output checksum.

### Yield parser

- Every column in the yield table maps to a typed field or a documented raw
  field.
- Units are explicit.
- Age/year rows and feature IDs are preserved.
- Empty or unsupported yield rows are reported, not zero-filled.

### Python equations

For each family:

1. document the equation form and coefficient mapping;
2. implement it with typed inputs and outputs;
3. compare against a console golden case;
4. report bias, RMSE, and max error;
5. promote only within the documented tolerance;
6. otherwise return `not_implemented` or `experimental`.

Family order:

```text
VTOTREG4   whole-stem volume
REGVCU     close-utilization volume
REGVU      utilization volume
REGHL      height / Lorey height
REGBA25    BA increment
BASP05/06  species BA growth
DQSP05/06  species DQ growth
YLDBA407   BA yield
YLDDQ45    DQ yield
```

### Interfaces

- CLI snapshots for help, success, and error paths.
- API contract tests for status codes and schema.
- Web smoke tests for bundle, curve, validation, and provenance views.
- Assistant tools tested with a fake provider.
- Every assistant response test asserts provenance is present.

## Golden evidence

Store golden fixtures for:

- one `VDYP.CTR` control map;
- one `.COE` family;
- one `.PRM` or `.DAT` parameter file;
- one console input and one `csvyieldtable` output;
- one Python equation family comparison.

Golden files are small, redistributable, and carry source metadata. If an
output cannot be redistributed, store a checksum and a reproduction command.

## Package release

Artifacts:

```text
fresh-vdyp wheel + sdist
fresh-vdyp-data manifest
normalized coefficient catalog
golden curve dataset
checksums
citation file
known-gaps list
```

Release checks:

```text
python -m build
pip install dist/*.whl in a clean environment
fresh-vdyp --help
fresh-vdyp bundle validate
fresh-vdyp run console --help
pytest
sphinx-build -b html docs _build/html -W
python scripts/check_workflow.py
```

## Data asset release

- Raw source files are not redistributed.
- Normalized assets are released with a manifest and citation.
- Each asset records the source version and extraction command.
- A user can rebuild the assets from a local VDYP install.
- If redistribution terms differ for a file, publish the manifest and rebuild
  instructions instead of the file.

## FEMIC integration

1. Publish `fresh-vdyp` as a package.
2. Add an optional dependency in FEMIC.
3. Add a thin adapter that calls `query_curve` or `validate_family`.
4. Pass `fresh-vdyp` and console provenance through FEMIC outputs.
5. Add a FEMIC integration test that works with a tiny fixture and skips when
   the optional package is absent.
6. Back-link the dependency in FEMIC docs and changelog.

## Release gates

- All bundle and runner tests pass.
- At least one Python equation family validates against the console.
- CLI/API/web/assistant tests pass.
- No raw data or personal paths in tracked files.
- Attribution appears in README, docs, API responses, and CLI `--json`.
- The package installs in a clean environment.
- The data manifest is stable and checksummed.

## Known gaps to record at release

- Which VDYP7 version and bundle files are covered.
- Which equation families are extracted, reimplemented, or still missing.
- Which species/site/BEC ranges are unsupported.
- Which runtime paths work and which fail.
- Any validation tolerance or observed bias.
