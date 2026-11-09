# Phase close-out report: P3 Console runner and yield parser

Phase: P3 Console runner and yield parser
Parent issue: #21
Pull request: #28, `feature/p3-console-runner` into `main`
Evidence head: `c73518d`, the head that the gates and CI run below cover
Report commit: the commit that adds this report. Its CI run is posted on pull request #28.
Date: 2026-11-09
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #28, and delete the branch `feature/p3-console-runner`.
2. Close parent issue #21 with a closeout comment that cites the merge commit.
3. Launch P4: create its parent issue and child issues, create
   `feature/p4-curve-api` from the merge commit, set the phase status in
   `ROADMAP.md`, and start P4.1.

Runtime change already applied with the maintainer's instruction to use a working
runtime. No further settings change is proposed.

```bash
sudo dpkg --add-architecture i386
sudo curl -fsSL -o /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
sudo curl -fsSL -o /etc/apt/sources.list.d/winehq-noble.sources https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources
sudo apt-get update
sudo apt-get install -y --install-recommends winehq-stable
```

WineHQ stable 11.0 replaced distro Wine 9.0, which crashed on every Windows
process, including `wine cmd`. The earlier failure remains recorded in
`notes/reference/vdyp-runtime-failure.md`.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| A known input produces a parsed curve table with source and runtime metadata. | Synthetic fixture accepted; 301 rows; 10-row golden subset; Wine 11.0 and console 7.16k in metadata. | met |
| Missing binary, config, or Wine paths fail with a clear error. | Stable codes `MISSING-CONSOLE`, `MISSING-CONFIG`, `MISSING-WINE`, `RUNTIME-UNAVAILABLE`; tests for each. | met |
| Output columns and units match the VDYP yield-table schema. | Real header mapped through `notes/reference/vdyp-csv-header-aliases.json` to the 101-column schema; units come from the schema. | met with a stated limit (the run emitted 33 columns) |
| A failed run is recorded as a failed run, not a silent fallback. | Wine 9 failure recorded with command, exit -6, and stderr; no curve substituted. | met |

## 2. Workflow compliance

- Parent issue before the branch: parent issue #21 created before `feature/p3-console-runner` and before activation commit `8ae10b3`.
- Branch from `main`: `feature/p3-console-runner` from `17d274e`.
- Commit messages that start with task IDs: `8ae10b3` (`P3.1`), `f363acb` (`P3.1`), `84ec7ec` (`P3.2`), `e450c2c` (`P3.3`/`P3.6`), `e092efd` (`P3.4`), `439a772` (`P3.4`), `2ca2ddb` (`P3.2`), `8e5aa03` (`P3.3`), `d1f02cf` (`P3.5`), `c73518d` (`P3.5`).
- Gates for each commit: section 3.
- Roadmap and changelog in step: `8ae10b3` activated P3; `c73518d` checked P3.1-P3.6 and recorded completion.
- Child issues closed with closeout evidence: #22, #23, #24, #25, #26, #27.
- Approval gates: WineHQ installation was requested by the maintainer ("use a working runtime"); no tag or release was created.

## 3. Gate evidence

| Commit | Gates | Result |
| --- | --- | --- |
| `f363acb` P3.1 | lint, format, types, tests, validator, docs | all GREEN |
| `84ec7ec` P3.2 fixture | lint, format, types, tests, validator, docs | all GREEN |
| `e450c2c` P3.3/P3.6 | lint, format, types, tests, validator, docs | all GREEN |
| `e092efd` P3.4 | lint, format, types, tests, validator, docs | all GREEN |
| `439a772` coverage | lint, format, types, tests, validator, docs | all GREEN |
| `8e5aa03` runner defaults | lint, format, types, tests, validator, docs | all GREEN |
| `d1f02cf` golden output | lint, format, types, tests, validator, docs | all GREEN; clean `sphinx-build -W` |
| `c73518d` final | lint, format, types, tests, validator, docs | all GREEN |

Local environment: Python 3.12.3, WineHQ stable 11.0. The suite collected 622
tests. Coverage of `scripts/` is 95.86%, above the 95 percent gate.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 42565968116 | `c73518d` | success | Quality gates, Green dashboard summary, and Pre-commit parity all pass. |
| 42551892671 | `b5e602f` | success | Phase 2 report head. |
| 42551765391 | `74d0cfa` | success | Phase 2 evidence head. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| Host Wine 9.0 crashed on every Windows process. | Distro Wine 9.0 was incompatible with the host kernel; even `wine cmd` failed. | Installed WineHQ stable 11.0; `wine cmd` and the console then ran. The failure and resolution are recorded. |
| The console rejected the first run with no age range. | The runner did not pass `-agestart`/`-ageend`. | Added `-agestart 0 -ageend 300 -inc 1` and related defaults; the console then accepted the fixture. |
| The console could not initialize with a Unix `-c` path. | Wine passed the Unix path through to the Windows file API. | The runner copies `VDYP_CFG` into the isolated work dir and uses `-c VDYP_CFG\`. |
| The real CSV header differs from `VDYP.tcl` names. | `CSVYieldTable` uses names such as `PRJ_VOL_WS` and `PROJECTION_YEAR`. | Added a tracked alias map; `DISTRICT` and `PRJ_MODE` are accepted and dropped as extras. |
| The run emitted 33 of 101 columns. | The console writes the columns needed for this input shape. | The parser accepts a validated subset; missing columns are absent, not invented. |
| The golden output is a 10-row subset. | The full output is large and regenerable. | Full hash and row count are recorded; the subset is enough for parser tests. |

## 6. Next phase

P4 Curve API and public datasets. Goal: expose a stable typed curve API and
publish a small public curve dataset.

- P4.1 Define `CurveQuery` and `CurvePoint` models with provenance.
- P4.2 Build a curve service over parsed console outputs.
- P4.3 Add age/year queries, units, and explicit unsupported cases.
- P4.4 Publish a golden curve dataset and manifest.
- P4.5 Add API, property, and regression tests.

Acceptance criteria are in `ROADMAP.md` Phase 4. Recommended defaults for open choices:

- Build the service over the P3 `YieldTable` and the P2 catalog; do not re-read
  the console output by hand.
- Make provenance a required field on every curve point: source file, runtime,
  console version, control sequence, and query inputs.
- Treat unsupported species/site combinations as explicit errors.
- Publish only the synthetic fixture run until a larger public dataset has a
  clear redistribution basis.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
