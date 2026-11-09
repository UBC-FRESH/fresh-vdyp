# Phase close-out report: P2 Coefficient catalog and parser

Phase: P2 Coefficient catalog and parser
Parent issue: #13
Pull request: #20, `feature/p2-coefficient-catalog` into `main`
Evidence head: `74d0cfa`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #20.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #20, and delete the branch `feature/p2-coefficient-catalog`.
2. Close parent issue #13 with a closeout comment that cites the merge commit.
3. Launch P3: create its parent issue and child issues, create
   `feature/p3-console-runner` from the merge commit, set the phase status in
   `ROADMAP.md`, and start P3.1.

Settings changes: none are outstanding. Repository visibility is public and
GitHub Pages is enabled, both applied on 2026-11-09 at the maintainer's
instruction:

```bash
gh api --method PATCH repos/UBC-FRESH/fresh-vdyp -f visibility=public
gh api --method POST repos/UBC-FRESH/fresh-vdyp/pages -f build_type=workflow
```

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Every coefficient row round-trips through raw, normalized, and manifest forms. | 38 CSV assets with 3,260 rows; end-to-end test compares catalog, CSV, and manifest row counts and hashes. | met |
| Column counts, species keys, BEC keys, and control references validate. | 38 schemas; 0 missing control targets; species and BEC validate against `SP0.DAT` and `BEC0.DAT`; `BG` recorded as a known aggregate. | met |
| The catalog exposes equation family, source file, row count, and columns. | `bundle catalog`, `notes/reference/vdyp-key-catalog.json`, and `notes/reference/vdyp-normalized-manifest.json`. | met |
| A user can inspect the bundle without the Windows UI. | `bundle validate`, `bundle catalog`, and `bundle extract` run from `scripts/fresh_vdyp.py`. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #13 created before `feature/p2-coefficient-catalog` and before activation commit `0a3938a`.
- Branch from `main`: `feature/p2-coefficient-catalog` from `d627751`.
- Commit messages that start with task IDs: `0a3938a` (`P2.1`), `2e3cb55` (`P2.1`), `7aad4d1` (`P2.2`), `3cdaf89` (`P2.3`), `ec2c261` (`P2.4`), `18d1115` (`P2.5`), `770ffba` (`P2.6`), `74d0cfa` (`P2.6`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `0a3938a` activated P2; `74d0cfa` checked P2.1-P2.6 and recorded completion.
- Child issues closed with closeout evidence: #14, #15, #16, #17, #18, #19.
- Approval gates: the visibility and Pages changes were explicitly approved by the maintainer on 2026-11-09; no tag or release was created.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `2e3cb55` P2.1 | lint, format, types, tests, validator, docs | all GREEN |
| `7aad4d1` P2.2 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `3cdaf89` P2.3 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `ec2c261` P2.4 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `18d1115` P2.5 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `770ffba` P2.6 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `74d0cfa` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 530 tests. Coverage of
`scripts/` is 95.19%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42551765391 | `74d0cfa` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42548949492 | `d627751` | success | Docs build and Pages deploy after Pages was enabled. |
| 42548209210 | `a7c3940` | success | Phase 1 report head. |
| 42548086456 | `50fa325` | success | Phase 1 evidence head. |

The earlier `Docs` deployment failures are resolved. The Pages site is live at
<https://ubc-fresh.github.io/fresh-vdyp/>.

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| 11 families have no categorical key. | Numeric helper tables carry no species/BEC column. | Marked `unmapped` with the explicit reason "no key columns in schema". |
| 2 families remain unsupported. | `COMPLIM.COE` and `REGDQI04.COE` have variable row shapes. | Recorded as unsupported; parsing is deferred until a dedicated schema exists. |
| Several schemas were corrected during P2.3. | `REGHL` is a species pair, increment files start with BEC, and `GROWBA11` starts with C/I. | Updated the schemas, tests, and model reference note in `3cdaf89`. |
| `BG` appears in increment files but not `BEC0.DAT`. | `BG` is an aggregate code, not a BEC zone. | Accepted as a documented BEC alias rather than marked invalid. |
| Coefficient units are not assigned. | The bundle does not label every coefficient unit. | The optional `units` manifest field is omitted rather than guessed. |
| 33 `coe` files are unreferenced by either control file. | Some are alternates, helpers, or legacy files. | Their role stays explicit and undecided; catalog work did not invent a link. |

## 6. Next phase

P3 Console runner and yield parser. Goal: run `VDYP7Console` safely and turn its
CSV yield tables into typed rows.

- P3.1 Implement runtime discovery and a Wine/Windows adapter.
- P3.2 Build a minimal polygon/layer input fixture.
- P3.3 Run `VDYP7Console` and capture stdout, stderr, and message files.
- P3.4 Parse `csvyieldtable` output into typed curve rows.
- P3.5 Add runner and parser tests with a golden output.
- P3.6 Record runtime failures without substituting invented values.

Acceptance criteria are in `ROADMAP.md` Phase 3. Recommended defaults for open choices:

- Discover the install through `VDYP_INSTALL`, `VDYP_CFG_DIR`, and
  `VDYP_CONSOLE`; do not hard-code a host path.
- Build the adapter around a documented command line and a temporary working
  directory, and capture all four streams: stdout, stderr, errors, and output.
- Use the shipped `console_input.zip` sample as the first controlled input, then
  shrink it to a minimal fixture.
- Treat the formatted `ConsoleOutput.txt` sample as an oracle only after P3
  reproduces it; parse `csvyieldtable` CSV as the primary output.
- A failed runtime is a recorded finding with its command and output, never a
  substituted curve.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
