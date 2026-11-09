# Phase close-out report: P4 Curve API and public datasets

Phase: P4 Curve API and public datasets
Parent issue: #29
Pull request: #35, `feature/p4-curve-api` into `main`
Evidence head: `ecb5dd2`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #35.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #35, and delete the branch `feature/p4-curve-api`.
2. Close parent issue #29 with a closeout comment that cites the merge commit.
3. Launch P5: create its parent issue and child issues, create
   `feature/p5-python-equations` from the merge commit, set the phase status in
   `ROADMAP.md`, and start P5.1.

Settings changes: none are proposed. The WineHQ stable 11.0 runtime change was
already applied and recorded in the Phase 3 report.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| A query returns typed volumes, heights, diameters, and density with provenance. | `CurvePoint` and `CurveResult`; every result carries source file, runtime, console version, control sequence, and query inputs. | met |
| Unsupported species/site combinations fail explicitly. | Unknown species returns `empty`; missing columns return `unsupported` with a reason. Site-index filtering is not exposed yet. | met with a stated limit |
| The golden dataset reproduces from a documented input and console version. | `fixtures/yield-output/golden-full.csv`, 301 rows, SHA256 `36eca18f...67ceb`; reproduction command and metadata tracked. | met |
| No curve is published without source and runtime metadata. | Dataset manifest validates with `scripts/provenance.py`; service attaches provenance to every result. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #29 created before `feature/p4-curve-api` and before activation commit `df1fe1d`.
- Branch from `main`: `feature/p4-curve-api` from `53ebc2c`.
- Commit messages that start with task IDs: `df1fe1d` (`P4.1`), `c4fe03d` (`P4.1-P4.3`), `1eea51b` (`P4.4`), `ecb5dd2` (`P4.5`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `df1fe1d` activated P4; `ecb5dd2` checked P4.1-P4.5 and recorded completion.
- Child issues closed with closeout evidence: #30, #31, #32, #33, #34.
- Approval gates: no tag, release, or settings change was made in P4.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `c4fe03d` P4.1-P4.3 | lint, format, types, tests, validator, docs | all GREEN |
| `1eea51b` P4.4 | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `ecb5dd2` P4.5 | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 647 tests. Coverage of
`scripts/` is 95.49%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42567126931 | `ecb5dd2` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42566133936 | `c76304e` | success | Phase 3 report head. |
| 42565968116 | `c73518d` | success | Phase 3 evidence head. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| The golden CSV arrived with CRLF line endings. | The console writes Windows line endings. | The tracked copy is LF-normalized; metadata records the raw output hash separately from the dataset hash. |
| The run emitted 33 of 101 schema columns. | The console writes the columns needed for this input shape. | The API returns `None` for absent fields and never zero-fills them. |
| Site-index filtering is not exposed. | P4 focused on age/year and species queries. | Recorded as a limit; site index is returned as a point field. |
| The dataset is synthetic and Wine-produced. | One synthetic polygon, one layer, one species, Wine 11.0. | Stated in the dataset README, manifest, and report. |
| A 10-row subset also exists. | P3.5 needed a tiny parser fixture. | `golden-sample.csv` stays as the small parser fixture; `golden-full.csv` is the P4 dataset. |

## 6. Next phase

P5 Incremental Python equations. Goal: reimplement documented equation families
in Python and validate each against the console oracle.

- P5.1 Implement whole-stem volume (`VTOTREG4`) and validate.
- P5.2 Implement close-utilization volume (`REGVCU`) and validate.
- P5.3 Implement utilization volume (`REGVU`) and validate.
- P5.4 Implement height/Lorey height (`REGHL`) and validate.
- P5.5 Implement BA and DQ increment families and validate.
- P5.6 Add a family-by-family validation matrix and tolerance report.

Acceptance criteria are in `ROADMAP.md` Phase 5. Recommended defaults for open choices:

- Start with `REGHL` or `VTOTREG4` using the published family-promotion order.
- Build one controlled console case per family with the same runtime metadata.
- Promote a family only when it matches within a documented tolerance.
- Return `not_implemented` or `experimental` for every family without a
  validation case.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
