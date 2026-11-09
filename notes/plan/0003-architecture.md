# Architecture plan

Date: 2026-11-09
Status: draft

## Package layout

```text
src/fresh_vdyp/
  __init__.py
  version.py
  provenance.py          source manifests, hashes, citations
  bundle/
    control.py           VDYP.CTR / VDYPBACK.CTR parsing
    coe.py               coefficient families
    prm.py               parameter files
    dat.py               data files
    catalog.py           family/control index
    validate.py          counts, ranges, references
  runner/
    discovery.py         find console, config, Wine/Windows path
    console.py           VDYP7Console command builder
    output.py            csvyieldtable parser
    runtime.py           process execution and failure evidence
  curves/
    schema.py            typed yield-table rows
    service.py           query, units, provenance
    golden.py            golden curve fixtures
  model/
    whole_stem.py        VTOTREG4
    close_util.py        REGVCU
    utilization.py       REGVU
    height.py            REGHL
    basal_area.py        REGBA25 / BASP05 / BASP06
    diameter.py          DQSP05 / DQSP06
    validation.py        family validation matrix
  api/
    service.py           shared typed service layer
    models.py            pydantic request/response models
  cli.py                 Typer application
  web/
    app.py               FastAPI application
    static/              FRESH-style UI
  agent/
    tools.py             bounded assistant tools
    prompts.py           provenance-first system prompts
```

## Core service layer

CLI, API, web, and assistant call the same service functions.

```python
class CurveQuery(BaseModel):
    feature_id: str
    species: str | None = None
    site_index: float | None = None
    age_start: int | None = None
    age_end: int | None = None
    increment: int = 10
    utilization: str | None = None


class CurvePoint(BaseModel):
    age: int
    year: int
    species: str | None
    height_m: float | None
    diameter_cm: float | None
    tph: float | None
    basal_area_m2_ha: float | None
    volume_m3_ha: float | None
    provenance: Provenance
```

The first implementation runs the console and parses its output. It does not
replace the console with Python equations until a family is validated.

## CLI

```bash
fresh-vdyp bundle extract --source "$VDYP_CFG_DIR" --out "$FRESH_VDYP_CACHE"
fresh-vdyp bundle validate --catalog "$FRESH_VDYP_CACHE/manifest.json"
fresh-vdyp bundle catalog --family whole_stem_volume
fresh-vdyp run console --input fixture.csv --out curve.csv
fresh-vdyp curve query --feature-id 1 --age-start 0 --age-end 250
fresh-vdyp model validate --family whole_stem_volume
fresh-vdyp serve --host 127.0.0.1 --port 8801
```

Every command supports `--json` and writes provenance.

## API

```text
GET  /health
GET  /bundle
GET  /bundle/{asset_id}
POST /curves/query
POST /model/validate
GET  /runs/{run_id}
GET  /provenance/{asset_id}
```

Responses include:

```text
request
result
provenance
evidence
runtime
warnings
```

## Web UI

FRESH-style views:

- bundle catalog with control-sequence map;
- coefficient family browser;
- console run form and yield-table preview;
- curve explorer;
- validation matrix by equation family;
- provenance drawer;
- assistant panel.

The UI must work without the assistant.

## LLM assistant

Bounded tools:

```text
search_bundle(query)
describe_coefficient_file(file_id)
lookup_control_sequence(sequence)
run_console(scenario)
query_curve(query)
validate_family(family)
get_provenance(asset_id)
```

Rules:

- Every answer exposes source file, control sequence, and query inputs.
- The assistant may summarize and compare but may not invent coefficients,
  equations, or curves.
- Unsupported families return `not_implemented`.
- The assistant never claims full VDYP parity.

## Runtime strategy

Preferred order:

1. Native Windows console on the authoritative host.
2. Wine console on Linux with a documented runtime.
3. Golden output fixtures when the runtime is unavailable.

A failed runtime is recorded with command, stdout, stderr, exit code, and
message file. It never triggers a silent Python substitute.

## FEMIC integration

```python
from fresh_vdyp import query_curve, validate_family
```

FEMIC integration should be optional:

```toml
[project.optional-dependencies]
fresh-vdyp = ["fresh-vdyp>=0.1"]
```

The adapter passes provenance through and records the package version, console
version, and bundle manifest hash.

## Non-negotiable boundaries

- No full binary rewrite.
- No hidden coefficients.
- No raw bundle commits.
- No equation family promoted without console validation.
- No assistant answer without provenance.
