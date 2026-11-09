# Equation validation matrix

Date: 2026-11-09
Console: 7.16k under Wine 11.0
Input: `fixtures/console-input/Console` (synthetic, AT/BWBS)
Golden output: `fixtures/yield-output/golden-full.csv`

This is not a claim of full VDYP7 parity. A family is listed as `validated` only
for the domain and tolerance shown. The machine-readable form is
`notes/reference/vdyp-equation-matrix.json`.

## VTOTREG4 whole-stem volume

| Field | Value |
| --- | --- |
| Equation source | [`bcgov/nr-vdyp` `EstimationMethods.estimateWholeStemVolumePerTree`](https://github.com/bcgov/nr-vdyp/blob/main/lib/vdyp-common/src/main/java/ca/bc/gov/nrs/vdyp/common/EstimationMethods.java) (EMP090, Apache-2.0) |
| Coefficient file | `VDYP_CFG/coe/VTOTREG4.COE` |
| Coefficient row | volume group 6 (`AT`/`BWBS` from `VGRPDEF1.DAT`) |
| Implementation | `scripts/equations.py` |
| Form | `ln(V_tree) = b0 + b1 ln(DQ) + b2 ln(HL) + b3 DQ + b4/DQ + b5 HL + b6 DQ^2 + b7 HL DQ + b8 HL/DQ` |
| Per-hectare | `V_tree * TPH` |
| Age-100 console | 436.39481 m3/ha |
| Age-100 Python | 432.74646 m3/ha |
| Age-100 relative error | 0.836% |
| Age-100 tolerance | 1% |
| Mature range | age >= 80 |
| Mature maximum error | 2.21% |
| Mature tolerance | 3% |
| Status | `validated` for age >= 80; `experimental` below 80 |

### Notes

- The console rounds `PRJ_LOREY_HT`, `PRJ_DIAMETER`, and `PRJ_TPH` in its CSV.
  That rounding is part of the stated tolerance.
- No coefficient was tuned to the sample. The nine coefficients are read from
  the bundle at runtime.
- Ages below 80 diverge more (up to about 17% at age 23). That is the young-stand
  / small-component path, not the static whole-stem equation. Those rows return
  `experimental`.
- `VGRPDEF1.DAT` group 10 is replaced with 11, matching the public source.

## Families not yet validated

| Family | Status |
| --- | --- |
| `REGVCU` close-utilization volume | `experimental` — implemented; synthetic vectors only; no per-class oracle |
| `REGVU` utilization component | `experimental` — implemented; synthetic vectors only; no per-class oracle |
| `REGHL` non-primary height | `experimental` — implemented; per-species height oracle unavailable |
| BA increment | `not_implemented` |
| DQ increment | `not_implemented` |

### Utilization-class oracle gap

`REGVCU` and `REGVU` operate on utilization classes 1-4 and then sum or
normalize into class 0. The reproduced `CSVYieldTable` exposes only class 0
columns (`PRJ_VOL_WS`, `PRJ_VOL_CU`, `PRJ_BA`, `PRJ_TPH`, and so on). It does
not expose class 1-4 basal area, TPH, DQ, or whole-stem volume.

Without those vectors, a Python `REGVCU`/`REGVU` result cannot be validated
against the console. Both families are implemented from the public source and
tested with synthetic per-class vectors, but they are marked `experimental`.
They stay outside the validated matrix until an oracle output with per-class
detail is captured.

### Height oracle gap

`REGHL.COE` converts a lead or primary height into a non-primary Lorey height.
The console CSV exposes only stand-level dominant and Lorey heights, not
per-species heights. `REGHL` is implemented and unit-tested with synthetic
species pairs, but it stays `experimental` until a per-species height output is
captured.

### Increment families

BA and DQ increment families are deferred. They require a controlled
multi-year state sequence and an increment-level oracle case; no implementation
is claimed.
