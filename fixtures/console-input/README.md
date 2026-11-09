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

Status: **not yet accepted by a console run.** The host Wine runtime is broken;
see `notes/reference/vdyp-runtime-failure.md`. The fixture is committed so the
first working runtime can test it immediately.

To try it, use the runner planned in P3.3 with `-i ./Console` and a copy of the
install's `VDYP.INI`. Do not add the raw BC sample data here.
