# Reproduced yield output

A small sample of a real `VDYP7Console` run on the synthetic
`fixtures/console-input/Console` fixture. It was reproduced on 2026-11-09 under
Wine 11.0 with the bundled console version 7.16k.

Files:

- `golden-sample.csv` — the 33-column `CSVYieldTable` header plus 10 rows.
- `metadata.json` — source, runtime, command, full-output SHA256, full row count
  (301), and subset row count (10).

The full output is not committed because it is regenerable and large. The
subset is enough to test header aliases and typed parsing.

This is synthetic input and synthetic output, not BC government data.
