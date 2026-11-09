# Phase close-out report: P6 CLI, API, web, and agent

Phase: P6 CLI, API, web, and agent
Parent issue: #44
Pull request: #50, `feature/p6-interfaces` into `main`
Evidence head: `5900c13`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #50.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #50, and delete the branch `feature/p6-interfaces`.
2. Close parent issue #44 with a closeout comment that cites the merge commit.
3. Launch P7: create its parent issue and child issues, create
   `feature/p7-release-integration` from the merge commit, set the phase status
   in `ROADMAP.md`, and start P7.1.

Settings changes: none are proposed.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Every web/assistant answer exposes its source file, control sequence, and query inputs. | API `CurveResponse.provenance`; CLI prints the same fields; assistant answers require sources. The synthetic curve has no single control sequence, so that field is empty. | met with a stated limit |
| The assistant cannot invent a coefficient, equation, or curve. | Tools are deterministic; `validate_answer` rejects a missing or blank source; no model or network call exists. | met |
| CLI and API share the same typed service layer. | Both call `bundle_service`, `curve_api`, and the matrix reader. | met |
| The UI works without an LLM; the assistant is additive. | The root page uses only the catalog, curve, and matrix endpoints. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #44 created before `feature/p6-interfaces` and before activation commit `d8fe6f0`.
- Branch from `main`: `feature/p6-interfaces` from `39ce9ce`.
- Commit messages that start with task IDs: `d8fe6f0` (`P6.1`), `0d57a64` (`P6.1-P6.5`), `5900c13` (`P6.5`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `d8fe6f0` activated P6; `5900c13` checked P6.1-P6.5 and recorded completion.
- Child issues closed with closeout evidence: #45, #46, #47, #48, #49.
- Approval gates: no tag, release, or settings change was made in P6.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `0d57a64` P6.1-P6.5 | lint, format, types, tests, validator, docs | all GREEN |
| `5900c13` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 770 tests. Coverage of
`scripts/` is 95.39%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42576597978 | `5900c13` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42575514501 | `e65cd91` | success | Phase 5 report head. |
| 42575336513 | `7b5a365` | success | Phase 5 evidence head. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No live LLM provider. | The phase needs bounded, testable tools before a provider. | Implemented deterministic tools and an offline source validator. |
| The page is small HTML/JS. | No frontend build toolchain is justified yet. | Kept it testable from Python; documented as a first UI. |
| The synthetic curve has no control sequence. | One console output can include several control steps. | The provenance field is present and empty; no sequence is guessed. |
| Interface dependencies were not in the dev requirements. | The seed did not anticipate P6. | Added Typer, FastAPI, pydantic, httpx, uvicorn, and jinja2. |

## 6. Next phase

P7 Validation, packaging, and FEMIC integration. Goal: prove the package,
publish it, and make it a usable dependency for FEMIC.

- P7.1 Run golden regression against VDYP7Console and FEMIC outputs.
- P7.2 Build and test the Python package and data manifest.
- P7.3 Publish release assets and a stable data manifest.
- P7.4 Add the FEMIC dependency and back-link documentation.
- P7.5 Write release notes, known gaps, and citation instructions.

Acceptance criteria are in `ROADMAP.md` Phase 7. Recommended defaults for open choices:

- Package the existing `scripts/` services as `fresh_vdyp` with console entry
  points, without moving the behavior.
- Keep normalized assets out of the wheel; ship the manifest and a download or
  extraction command.
- Run the golden regression against the synthetic dataset and a FEMIC fixture.
- Publish known gaps: one validated family, experimental families, and the
  young-stand path.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
