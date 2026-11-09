# Reproduced yield output

A real `VDYP7Console` run on the synthetic
`fixtures/console-input/Console` fixture. It was reproduced on 2026-11-09 under
WineHQ stable 11.0 with the bundled console version 7.16k.

Files:

- `golden-full.csv` — the full 301-row, 33-column `CSVYieldTable` output. The
  console wrote CRLF; this copy is normalized to LF.
- `golden-sample.csv` — the header plus 10 rows, used by the smaller parser
  tests.
- `metadata.json` — source, runtime, console version, command, raw-output
  SHA256, dataset SHA256, and row counts.
- `dataset-manifest.json` — a provenance-validated entry for `golden-full.csv`,
  checked by `scripts/provenance.py`.
- `README.md` — this note.

The dataset is synthetic input and synthetic output, not BC government data. It
is not a native-Windows parity claim.

Reproduction command, from a working directory containing `Console/` and
`VDYP_CFG/`:

```bash
wine VDYP7Console.exe -i Console -o ConsoleOutput.txt -e ConsoleErrors.txt \
  -c VDYP_CFG/ -d . -ofmt CSVYieldTable -agestart 0 -ageend 300 -inc 1
```
