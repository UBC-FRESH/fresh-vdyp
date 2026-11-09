# Data and provenance contract

Date: 2026-11-09
Status: binding (Phase 1)

## Principles

1. The BC government owns VDYP7 and its coefficient/control bundle.
2. Every value must be traceable to a source file and a processing step.
3. Raw government bundles are not committed to this repository.
4. Small fixtures are allowed; large normalized assets are release artifacts.
5. Reimplemented logic is labelled `reimplemented`, never presented as the
   original model.
6. A failed runtime is recorded as a failed run, not filled with invented data.

## Source roots

Use environment variables or documented discovery:

```text
VDYP_INSTALL       VDYP7 installation root
VDYP_CFG_DIR       VDYP_CFG directory
VDYP_CONSOLE       VDYP7Console executable path
FRESH_VDYP_CACHE   local cache for extracted assets
```

Do not hard-code personal or machine-specific paths in tracked files.

## Source classes

### Control files

Observed locally:

```text
VDYP_CFG/VDYP.CTR
VDYP_CFG/VDYPBACK.CTR
VDYP_CFG/VDYP.tcl
VDYP_CFG/VDYP7LoggingConfig.txt
```

`VDYP.CTR` maps numbered control sequences to coefficient and parameter files.
The sequence numbers are the join keys between the model steps and the files.

### Coefficient and parameter files

Observed locally in `VDYP_CFG/coe`:

```text
40 .COE files
7  .PRM files
33 .DAT files
about 568 KB total
```

The files are ASCII, not binary. Family names indicate the model step, such as:

```text
VTOTREG4.COE     total whole-stem volume
REGVU.COE        utilization volume
REGVCU.COE       close-utilization volume
REGVDU.COE       volume net of decay
REGVWU.COE       volume net of decay and waste
REGHL.COE        height / Lorey height
REGBA25.COE      basal-area increment
BASP05.COE       BA growth, primary species
BASP06.COE       BA growth, non-primary species
DQSP05.COE       DQ growth, primary species
DQSP06.COE       DQ growth, non-primary species
YLDBA407.COE     BA yield
YLDDQ45.COE      DQ yield
```

The coefficient files do not always carry a header that names every column. The
control-file comments and public documentation are part of the column mapping.

### Runtime and output

Observed locally:

```text
VDYP7Console.exe
VDYP7Batch.exe
WinVDYP7.exe
VDYP7CORE.dll
VDYP7Interface.dll
VDYP7IO.dll
VDYPSI32.dll
```

`VDYP7Console` emits formatted yield tables or `csvyieldtable` output. The
yield-table schema is described in `VDYP_CFG/VDYP.tcl` and the public Volume 3
console guide.

## Manifest schema

Each extracted asset gets one manifest entry:

```yaml
id: vdyp-vtotreg4
kind: vdyp_coefficient_table
source_model: VDYP7
source_version: "7"
source_file: "VDYP_CFG/coe/VTOTREG4.COE"
source_sha256: "<sha256>"
extracted_at_utc: "2026-11-09T00:00:00Z"
extractor: "fresh-vdyp 0.1.0"
parser_version: 1
family: whole_stem_volume
control_sequence: "090"
columns:
  - curve_group
  - b0
  - b1
  - b2
row_count: 74
units:
  b0: log_m3
citation: "Province of British Columbia. VDYP7 coefficient bundle."
notes: ""
```

### Validation

`scripts/provenance.py` is the executable form of this schema. Run it on a
manifest before publishing:

```bash
python scripts/provenance.py --manifest path/to/manifest.json
```

Required fields:

```text
id  kind  source_model  source_version  source_file  source_sha256
extracted_at_utc  extractor  parser_version  citation
```

Optional fields:

```text
family  control_sequence  columns  row_count  units  notes  normalized_sha256
```

Field rules:

- `id` matches `^vdyp-[a-z0-9]+(?:-[a-z0-9]+)*$` and is unique within a manifest.
- `kind` is a lowercase underscore name, such as `vdyp_coefficient_table`.
- `source_sha256` is 64 lowercase hexadecimal characters.
- `normalized_sha256`, when present, is 64 lowercase hexadecimal characters.
- `extracted_at_utc` is ISO 8601 ending in `Z` with a UTC offset.
- `source_file` is a forward-slash relative path without `..` or a drive letter.
- `parser_version` is an integer of at least 1.
- `row_count`, when present, is an integer of at least 0.
- `columns`, when present, is a non-empty list of unique names.
- `units`, when present, maps field names to unit strings.

Stable finding codes are `MISSING-FIELD`, `INVALID-ID`, `INVALID-KIND`,
`INVALID-SHA256`, `INVALID-TIMESTAMP`, `INVALID-SOURCE-FILE`,
`INVALID-PARSER-VERSION`, `INVALID-ROW-COUNT`, `INVALID-COLUMNS`,
`INVALID-UNITS`, and `INVALID-PAYLOAD`.

The inventory, control-map, and column files under `notes/reference/` are
repository artifacts, not extracted-asset manifests. They carry source labels
and counts, but they do not need this per-asset entry shape.

## Asset layout

```text
manifest.json
bundle/
  control/
    vdyp_ctr.json
    vdypback_ctr.json
  coefficients/
    vtotreg4/
      data.parquet
      metadata.json
    regvu/
      data.parquet
      metadata.json
  curves/
    golden/
      yield_table.csv
      metadata.json
fixtures/
  ...
```

Raw files stay outside the repository. The release includes normalized
Parquet/CSV plus the manifest, not the original install.

## Citation format

Each data page and API response should expose:

```text
Source: Province of British Columbia, VDYP7, VDYP_CFG/coe/VTOTREG4.COE
Extracted: 2026-11-09
Extractor: fresh-vdyp 0.1.0
SHA256: ...
```

For derived outputs:

```text
Source model: VDYP7
Source file: VDYP_CFG/coe/...
Processing: fresh-vdyp <version>, <command>
Runtime: VDYP7Console <version> / Wine or Windows
Evidence: reimplemented | model_output | validated_against
```

## Publication boundary

- Do not commit `VDYP_CFG/`, `coe/`, `.COE`, `.PRM`, `.DAT`, or large extracted
  assets.
- Do commit parsers, schemas, manifests, tests, tiny fixtures, and download
  instructions.
- Do not strip source metadata from a normalized table.
- Do not flatten a coefficient table without recording its family, control
  sequence, and original columns.
