# Phase close-out report: P0 Bootstrap and attribution

Phase: P0 Bootstrap and attribution
Parent issue: #1
Pull request: #5, `feature/p0-bootstrap` into `main`
Evidence head: `604f14c`, the head that the gates and the CI runs below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #5.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #5, and delete the branch `feature/p0-bootstrap`.
2. Close parent issue #1 with a closeout comment that cites the merge commit.
3. Launch P1: create its parent issue and child issues, create
   `feature/p1-source-inventory` from the merge commit, set the phase status in
   `ROADMAP.md`, and start P1.1.

Settings changes, each with its exact command. Each one runs only after its own approval.

- Enable GitHub Pages, which currently makes the `Docs` workflow fail on `main`:
  `gh api --method POST repos/UBC-FRESH/fresh-vdyp/pages -f build_type=workflow`
- Change repository visibility only if the project is ready to be public:
  `gh repo edit UBC-FRESH/fresh-vdyp --visibility public --accept-visibility-change-consequences`

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| A reader can tell what `fresh-vdyp` is, what it is not, and which BC sources it depends on. | `README.md` "What this is", "What this is not", "Source and attribution"; `docs/overview.rst` overview and non-goals. | met |
| The seed's validator and docs gates are green. | Dashboard at `604f14c`: all six gates GREEN; CI run 42546662987 success. | met |
| Attribution language appears in `README.md`, `AGENTS.md`, and `CITATION.cff`. | `README.md` source section; `AGENTS.md` project-specific rules; `CITATION.cff` VDYP7 reference. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #1 created 2026-11-09 before `feature/p0-bootstrap` and before the roadmap activation commit `10305b0`.
- Branch from `main`: `feature/p0-bootstrap` from `f204901`.
- Commit messages that start with task IDs: `10305b0` (`P0.4`), `604f14c` (`P0.1-P0.3`), and this report commit (`P0 close-out`).
- Gates for each commit: see section 3.
- Roadmap and changelog in step: `10305b0` activated P0; `604f14c` checked P0.1-P0.3 and recorded their evidence.
- Child issues closed with closeout evidence: #2, #3, #4 each closed with a verification comment.
- Approval gates: creating the `phase` and `task` labels was approved in the session instruction "Plan and go"; no visibility, Pages, tag, or release change was made.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `10305b0` | lint, format, types, tests, validator, docs | all GREEN; `OVERALL: GREEN` |
| `604f14c` | lint, format, types, tests, validator, docs | all GREEN; `OVERALL: GREEN` |

Local environment: Python 3.12.3. Every gate is the repository's own command; none were skipped or weakened.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42546662987 | `604f14c` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42544454938 | `f204901` | success | Seed CI on `main`. |
| 42544431043 | `fb985ee` | success | Seed CI on `main`. |
| 42544454816 | `f204901` | failure | `Docs` deploy failed: GitHub Pages is not enabled. Build job passed. Pre-existing. |
| 42544431052 | `fb985ee` | failure | `Docs` deploy failed for the same reason. Pre-existing. |

The `Docs` build itself passes locally and in CI; only the Pages deployment step fails
with `HttpError: Not Found ... Ensure GitHub Pages has been enabled`. Enabling Pages is
listed as an approval-gated settings change above.

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| P0.1-P0.3 produced no code change. | The seed already carried the attribution, docs, and gate configuration the tasks require. | Recorded file evidence and gate output in #2-#4 instead of editing working text. |
| The `phase` and `task` labels did not exist. | The seed shipped issue templates before creating the labels. | Created both labels; applied them to #1-#4. |
| Repository is private while `README.md` describes a public package. | The seed was created privately. | Recorded as a limit; visibility change is listed for approval. |
| `Docs` deploy fails on `main`. | GitHub Pages has not been enabled for the repository. | Recorded above with the exact enable command; not run. |

## 6. Next phase

P1 Source inventory and control map. Goal: inventory the VDYP7 bundle and freeze the
control-file and provenance contract before extraction begins.

- P1.1 Inventory install binaries, configuration, coefficient, and sample files.
- P1.2 Parse `VDYP.CTR`, `VDYPBACK.CTR`, and report column definitions.
- P1.3 Map control sequences to `.COE`, `.PRM`, and `.DAT` files.
- P1.4 Write the data-provenance contract and source-citation manifest.
- P1.5 Capture tiny fixtures and a golden console-output inventory.

Acceptance criteria are in `ROADMAP.md` Phase 1. Recommended defaults for open choices:

- Inventory every file under the install root but publish only repository-relative
  identifiers, sizes, and SHA256 values.
- Parse both control files; treat `VDYP.CTR` as the main sequence and `VDYPBACK.CTR`
  as the fallback sequence.
- Derive the 101 output columns from `VDYP.tcl` and map units explicitly.
- Keep fixtures tiny and redistributable; defer console golden outputs to P3 unless the
  runtime is exercised under a documented adapter.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
