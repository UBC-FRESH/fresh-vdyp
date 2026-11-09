# Fixtures

Small, synthetic, redistributable files for tests. None of these files is BC
government data, and none is copied from the official bundle.

## `mini-bundle/`

A miniature VDYP-shaped bundle for parser and join tests:

- `control/VDYP.CTR` — fixed-column control entries with a comment and a
  nullification.
- `control/VDYP.tcl` — a three-column `*COLUMNS` table, including the row-20
  space quirk.
- `coe/VTOTREG4.COE`, `coe/SIEQN.PRM`, `coe/BEC0.DAT` — two-row synthetic
  coefficient, parameter, and lookup tables.
- `manifest.json` — the source status, size, and purpose of every fixture file.

## `manifests/`

- `example-coefficient.json` — a valid provenance-manifest entry for the
  synthetic coefficient table. It exercises the `scripts/provenance.py` schema.

## Rules

- Keep fixtures tiny and readable.
- Mark every fixture `synthetic` or name the source and redistribution basis.
- Never add a raw `VDYP_CFG` bundle or a large sample database here.
