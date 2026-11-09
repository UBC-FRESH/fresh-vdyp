# Phase close-out report: P1 Source inventory and control map

Phase: P1 Source inventory and control map
Parent issue: #6
Pull request: #12, `feature/p1-source-inventory` into `main`
Evidence head: `50fa325`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #12.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #12, and delete the branch `feature/p1-source-inventory`.
2. Close parent issue #6 with a closeout comment that cites the merge commit.
3. Launch P2: create its parent issue and child issues, create
   `feature/p2-coefficient-catalog` from the merge commit, set the phase status
   in `ROADMAP.md`, and start P2.1.

Settings changes, each with its exact command. Each one runs only after its own approval.

- Enable GitHub Pages, which still makes the `Docs` workflow fail on `main`:
  `gh api --method POST repos/UBC-FRESH/fresh-vdyp/pages -f build_type=workflow`
- Change repository visibility only if the project is ready to be public:
  `gh repo edit UBC-FRESH/fresh-vdyp --visibility public --accept-visibility-change-consequences`

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Every source file has a stable identifier, source version, path, and SHA256. | `notes/reference/vdyp-bundle-manifest.json`: 211 files, relative paths, 64-character SHA256. | met |
| The control-sequence map explains which coefficient files drive which steps. | `notes/reference/vdyp-control-map.json`: 112 entries, 89 resolved, 0 missing, 33 unreferenced. | met |
| Yield-table columns and units are documented. | `notes/reference/vdyp-columns.json`: 101 columns with name, units, decimals, description, width, and header id. | met |
| No raw government bundle is committed; only fixtures and manifests are tracked. | `git ls-files fixtures` shows synthetic files only; `.gitignore` still excludes the raw bundle. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #6 created before `feature/p1-source-inventory` and before activation commit `552215b`.
- Branch from `main`: `feature/p1-source-inventory` from `b73362a`.
- Commit messages that start with task IDs: `552215b` (`P1.1`), `30819a1` (`P1.1`), `26e15fc` (`P1.2`), `3c3d2fb` (`P1.3`), `21c045f` (`P1.4`), `3aa7926` (`P1.5`), `50fa325` (`P1.5`).
- Gates for each commit: see section 3.
- Roadmap and changelog in step: `552215b` activated P1; `50fa325` checked P1.1-P1.5 and recorded completion.
- Child issues closed with closeout evidence: #7, #8, #9, #10, #11 each closed with a verification comment.
- Approval gates: no visibility, Pages, tag, or release change was made.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `30819a1` P1.1 | lint, format, types, tests, validator, docs | all GREEN |
| `26e15fc` P1.2 | lint, format, types, tests, validator, docs | all GREEN |
| `3c3d2fb` P1.3 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `21c045f` P1.4 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `3aa7926` P1.5 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `50fa325` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 298 tests, including 123
new cases. Coverage of `scripts/` stayed above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42548086456 | `50fa325` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42546774898 | `5aa46c9` | success | Phase 0 report head. |
| 42546662987 | `604f14c` | success | Phase 0 evidence head. |
| 42544454816 | `f204901` | failure | `Docs` deploy failed: GitHub Pages is not enabled. Build job passed. Pre-existing. |
| 42544431052 | `fb985ee` | failure | `Docs` deploy failed for the same reason. Pre-existing. |

The `Docs` build passes locally and in every CI quality job. Only the Pages
deployment step on `main` fails. Enabling Pages is listed as an approval-gated
settings change above.

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| The planned `.DAT` count was correct only after a case-insensitive count. | The bundle mixes upper- and lower-case extensions. | The inventory normalizes case and records the observed 40/7/33 per-file counts in `notes/reference/vdyp-inventory.md`. |
| `MappedEntry.sequence` was renamed to `sequence_id`. | Sphinx reported an ambiguous cross-reference with `ControlEntry.sequence`. | The JSON field remains `sequence`; only the Python attribute changed. |
| The shipped console output is a formatted table, not `csvyieldtable` CSV. | The sample run predates or bypasses the CSV form. | Recorded as a limit; P3 must produce and parse the CSV form. |
| The console runtime was not exercised. | No adapter exists yet. | Recorded in the golden inventory and deferred to P3. |
| `Docs` deploy fails on `main`. | GitHub Pages is not enabled. | Recorded with the exact enable command; not run. |

## 6. Next phase

P2 Coefficient catalog and parser. Goal: convert the plain-text coefficient
bundle into a normalized, validated catalog.

- P2.1 Implement `.COE` family parsers.
- P2.2 Implement `.PRM`, `.DAT`, and `VDYP.CTR` parsers.
- P2.3 Infer family, species/BEC, site-curve, and parameter keys.
- P2.4 Write normalized Parquet/CSV plus a checksum manifest.
- P2.5 Add `bundle extract`, `bundle validate`, and `bundle catalog` commands.
- P2.6 Add parser, schema, and catalog tests.

Acceptance criteria are in `ROADMAP.md` Phase 2. Recommended defaults for open choices:

- Use the P1 control map as the join key; do not re-parse raw control files in P2.
- Treat the 33 unreferenced `coe` files as `unmapped` until a control reference or
  public documentation explains them.
- Keep normalized assets out of Git; the manifest and tiny fixtures stay tracked.
- Start with `VTOTREG4.COE` (74 rows, nine coefficients) because its family shape
  is the best documented.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
