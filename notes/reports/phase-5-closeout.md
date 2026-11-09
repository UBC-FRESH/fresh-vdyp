# Phase close-out report: P5 Incremental Python equations

Phase: P5 Incremental Python equations
Parent issue: #36
Pull request: #43, `feature/p5-python-equations` into `main`
Evidence head: `7b5a365`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #43.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #43, and delete the branch `feature/p5-python-equations`.
2. Close parent issue #36 with a closeout comment that cites the merge commit.
3. Launch P6: create its parent issue and child issues, create
   `feature/p6-interfaces` from the merge commit, set the phase status in
   `ROADMAP.md`, and start P6.1.

Settings changes: none are proposed.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Each implemented family has an equation note, unit tests, and a console validation case. | VTOTREG4 has all three. REGVCU, REGVU, REGHL, and the increments have equation notes and synthetic tests, but no console case because the oracle lacks the required detail. | met with a stated limit |
| Unimplemented families return `not_implemented`, not guessed values. | Missing groups, classes, or coefficient rows return `not_implemented` with a reason. | met |
| A family is promoted only when its validation error is within the documented tolerance. | Only VTOTREG4 is `validated`; age 100 0.836% (1%), mature max 2.21% (3%). | met |
| The package never claims full VDYP parity. | `notes/reference/vdyp-equation-matrix.json` states it; all non-validated families are explicit. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #36 created before `feature/p5-python-equations` and before activation commit `52494ea`.
- Branch from `main`: `feature/p5-python-equations` from `ba6f339`.
- Commit messages that start with task IDs: `52494ea` (`P5.1`), `567dd22` (`P5.1`), `fc64fd7` (`P5.2`), `6e6982a` (`P5.2-P5.3`), `e062ec3` (`P5.4-P5.6`), `bce75cd` (`P5.5`), `7b5a365` (`P5.5`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `52494ea` activated P5; `7b5a365` checked P5.1-P5.6 and recorded completion.
- Child issues closed with closeout evidence: #37, #38, #39, #40, #41, #42.
- Approval gates: no tag, release, or settings change was made in P5.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `567dd22` P5.1 | lint, format, types, tests, validator, docs | all GREEN |
| `6e6982a` P5.2-P5.3 | lint, format, types, tests, validator, docs | all GREEN |
| `e062ec3` P5.4-P5.6 | lint, format, types, tests, validator, docs | all GREEN |
| `bce75cd` P5.5 | lint, format, types, tests, validator, docs | all GREEN |
| `7b5a365` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 730 tests. Coverage of
`scripts/` is 95.96%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42575336513 | `7b5a365` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42567291376 | `33cc402` | success | Phase 4 report head. |
| 42567126931 | `ecb5dd2` | success | Phase 4 evidence head. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| Only VTOTREG4 is validated. | `REGVCU`/`REGVU` need class 1-4 vectors; `REGHL` needs per-species heights; increments need an increment-level case. The console CSV has none of these. | Implemented as `experimental` with synthetic tests; recorded the oracle gap in the matrix. |
| `DCSV` could not supply per-class output. | It is a flat input format, not an output format. | Recorded the failed probe; the error is in the validation note. |
| Young ages diverge from VTOTREG4. | The young-stand/small-component path is separate. | VTOTREG4 is validated for age >= 80; younger rows are `experimental`. |
| Coefficients are loaded at runtime. | Avoid tuning to the sample. | The implementation and tests load the bundle; no coefficient is hard-coded. |

## 6. Next phase

P6 CLI, API, web, and agent. Goal: make the package usable through a typed API,
CLI, FRESH-style web UI, and bounded assistant tools.

- P6.1 Build the Typer CLI and command contracts.
- P6.2 Build the FastAPI service and typed response models.
- P6.3 Build the FRESH-style bundle, curve, and validation UI.
- P6.4 Add LLM tools for catalog search, curve query, provenance, and validation.
- P6.5 Add API, CLI, UI, and assistant tests.

Acceptance criteria are in `ROADMAP.md` Phase 6. Recommended defaults for open choices:

- Build on the existing curve service and bundle service; do not duplicate them.
- Make provenance a required response field on every endpoint.
- Keep the assistant additive and unable to invent coefficients or curves.
- Use the synthetic golden dataset for the first UI; do not publish a BC dataset
  without a redistribution basis.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
