# Equation validation matrix

Date: 2026-11-09
Console: 7.16k under Wine 11.0
Input: `fixtures/console-input/Console` (synthetic, AT/BWBS)
Golden output: `fixtures/yield-output/golden-full.csv`

This is not a claim of full VDYP7 parity. A family is listed as `validated` only
for the domain and tolerance shown.

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
| `REGVCU` close-utilization volume | `not_implemented` |
| `REGVU` utilization component | `not_implemented` |
| `REGHL` height / Lorey height | `not_implemented` |
| BA increment | `not_implemented` |
| DQ increment | `not_implemented` |
