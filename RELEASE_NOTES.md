# fresh-vdyp 0.1.0 release notes

Date: 2026-11-09
Status: release candidate. Assets are built locally; no tag, PyPI upload, or
GitHub release has been created.

## What this is

`fresh-vdyp` is an interoperability and reimplementation layer for the BC VDYP7
coefficient bundle, console runner, and yield curves. It is not a claim of
authorship over VDYP7 or BC government data.

## Install

```bash
python -m pip install dist/fresh_vdyp-0.1.0-py3-none-any.whl
fvdyp --help
```

The wheel does not bundle normalized data. Use a local VDYP installation and the
synthetic golden dataset in the repository for the first run.

## Interfaces

```bash
fvdyp bundle validate --config-dir "$VDYP_CFG_DIR"
fvdyp curve query --age-start 100 --age-end 100
fvdyp equation matrix
```

```python
import fresh_vdyp

service = fresh_vdyp.load_service(csv_path, metadata_path)
result = service.query(fresh_vdyp.CurveQuery(age_start=100, age_end=100))
```

The FastAPI service is `uvicorn fvdyp_api:app`; the root page is a small
FRESH-style bundle/curve/validation view.

## Validation status

| Family | Status |
| --- | --- |
| VTOTREG4 whole-stem volume | validated for age >= 80; age 100 error 0.836% (1% tolerance), mature max 2.21% (3%) |
| REGVCU close-utilization | experimental; per-class oracle unavailable |
| REGVU utilization component | experimental; per-class oracle unavailable |
| REGHL non-primary height | experimental; per-species height oracle unavailable |
| BA increment | experimental; synthetic state vectors only |
| DQ increment | experimental; synthetic state vectors only |

The machine-readable matrix is `notes/reference/vdyp-equation-matrix.json`.

## Known gaps

- Only VTOTREG4 is promoted. The other families are experimental.
- The young-stand / small-component path is outside the validated VTOTREG4
  domain.
- The console CSV exposes only utilization class 0 and no per-species heights.
- No FEMIC output fixture is available yet; the release regression uses the
  synthetic console dataset.
- The console was exercised under Wine 11.0, not native Windows.
- The assistant tools are deterministic and offline; there is no live LLM
  provider.
- The release assets are not published yet.

## Data

The first dataset is synthetic: one polygon, one layer, one species, produced by
the synthetic input under Wine 11.0 with console 7.16k. It is not BC data. The
manifest is `fixtures/yield-output/dataset-manifest.json`.

## Citation

Cite the source model and files, not only this package:

```text
Province of British Columbia. VDYP7 (Variable Density Yield Projection),
VDYP7Console 7.16k, VDYP_CFG control files and coefficient bundle.
https://www2.gov.bc.ca/gov/content/industry/forestry/managing-our-forest-resources/forest-inventory/growth-and-yield-modelling/variable-density-yield-projection-vdyp
```

Equation forms are ported from the public `bcgov/nr-vdyp` source (Apache-2.0),
with attribution. Reimplemented logic is labelled `reimplemented` and is
validated against console output where stated.
