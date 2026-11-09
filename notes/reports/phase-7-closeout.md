# Phase close-out report: P7 Validation, packaging, and FEMIC integration

Phase: P7 Validation, packaging, and FEMIC integration
Parent issue: #51
Pull request: #57, `feature/p7-release-integration` into `main`
Evidence head: `017ed1f`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #57.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #57, and delete the branch `feature/p7-release-integration`.
2. Close parent issue #51 with a closeout comment that cites the merge commit.

Release publication and the FEMIC repository change are separate approvals. They
are listed below and are not run by this close-out.

Settings changes: none are proposed.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| A clean environment installs the package and uses the data assets. | Wheel installed with `--no-deps` into a clean target; `import fresh_vdyp` returns `0.1.0`; data manifest validates. | met |
| FEMIC can import `fresh_vdyp` and call a documented curve or validation query. | `docs/integration/femic.rst`; facade verified from the installed wheel. The FEMIC repository change is queued, not made. | met with a stated limit |
| Golden checks pass; unsupported equations and gaps are explicit. | `tests/test_release_regression.py`; matrix; release notes. | met |
| Release notes cite VDYP7, the control files, and all source coefficients. | `RELEASE_NOTES.md` citation section. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #51 created before `feature/p7-release-integration` and before activation commit `9577cdd`.
- Branch from `main`: `feature/p7-release-integration` from `ce9151a`.
- Commit messages that start with task IDs: `9577cdd` (`P7.1`), `ec02b10` (`P7.1-P7.5`), `017ed1f` (`P7.5`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `9577cdd` activated P7; `017ed1f` checked P7.1-P7.5 and recorded completion.
- Child issues closed with closeout evidence: #52, #53, #54, #55, #56.
- Approval gates: no tag, release, PyPI upload, or FEMIC repository change was made.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `ec02b10` P7.1-P7.5 | lint, format, types, tests, validator, docs | all GREEN |
| `017ed1f` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3. The suite collected 770 tests. Coverage of
`scripts/` is 97.67%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42579280002 | `017ed1f` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42576794604 | `203e1b5` | success | Phase 6 report head. |
| 42576597978 | `5900c13` | success | Phase 6 evidence head. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| Release assets are built but not published. | A tag, GitHub release, and PyPI upload are approval-gated. | `notes/reference/release-instructions.md` has the exact commands; `release-manifest.json` has the hashes. |
| The FEMIC repository was not modified. | Editing an external repository is approval-gated. | The import facade and integration page are ready; the dependency/back-link change is queued. |
| No FEMIC output fixture exists. | No FEMIC output was provided. | The release regression uses the synthetic console dataset; the gap is in the release notes. |
| The legacy argparse CLI was removed. | The Typer CLI supersedes it and the `fresh_vdyp` package shadows the module name. | Tests and README point to `scripts/fvdyp_cli.py`; the installed entry points are `fvdyp` and `fresh-vdyp`. |
| Dist files are not committed. | They are regenerable and ignored. | Only the release manifest and instructions are tracked. |

## 6. Release actions, each approval-gated

```bash
git tag -a v0.1.0 -m "fresh-vdyp 0.1.0"
git push origin v0.1.0
gh release create v0.1.0 dist/fresh_vdyp-0.1.0-py3-none-any.whl dist/fresh_vdyp-0.1.0.tar.gz \
  --title "fresh-vdyp 0.1.0" --notes-file RELEASE_NOTES.md
```

The FEMIC dependency change is a separate pull request in the FEMIC repository.
It is not made here.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
