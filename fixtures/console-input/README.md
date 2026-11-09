# Console input fixture

A tiny, synthetic input for `VDYP7Console`. It is shaped after the CSV headers
shipped with the sample run, but it is not BC government data.

```text
Console/
  POLYGON.csv      one polygon
  POLYGON_ID.csv   its identifier
  LAYER.csv        one layer
  SPECIES.csv      one 100 percent AT species row
  HISTORY.csv      one empty history row
  NON_VEG.csv      one non-vegetation component
  OTHER_VEG.csv    header only
  VRIADJST.csv     header only
```

`manifest.json` records each file's synthetic status, size, and purpose.

Status: **accepted by a console run on 2026-11-09** under Wine 11.0. The run
returned exit 0 and produced 301 CSV rows. The evidence is
`fixtures/yield-output/` and `notes/reference/vdyp-golden-outputs.md`.

To try it, use the runner planned in P3.3 with `-i ./Console` and a copy of the
install's `VDYP.INI`. Do not add the raw BC sample data here.
