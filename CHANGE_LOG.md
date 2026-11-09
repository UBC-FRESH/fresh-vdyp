# Change Log

Newest entries last. Each milestone gets a dated entry that matches the roadmap status and the GitHub issue comments.

## 2026-11-09

- Created fresh-vdyp from the UBC-FRESH dev workflow seed. The agent contract, roadmap, docs skeleton, and validator came from the seed. Every phase is planned, and no parent issues exist yet.
- Added the program, data/provenance, architecture, and validation/release plans under `notes/plan/`.
- Added VDYP7 bundle and coefficient-map inventories under `notes/reference/`.
- Added ADRs for console/data-first delivery, code/data separation, incremental equation validation, attribution labels, and the FEMIC package boundary.
- Added MIT license, code of conduct, and citation metadata.
- Created the private `UBC-FRESH/fresh-vdyp` GitHub repository and pushed the seed on `main`.
- Created Phase 0 parent issue #1 and activated P0 on `feature/p0-bootstrap`; P0.4 is complete.
- Confirmed the seed already carries attribution in `README.md`, `AGENTS.md`, `CITATION.cff`, and `docs/overview.rst`; P0.1-P0.3 still need their checks recorded.
- Verified P0.1-P0.3 at `10305b0`: attribution is present in the root files and docs, and the dashboard is green. Closed child issues #2-#4.
- Opened pull request #5 with the Phase 0 close-out report and queued it for maintainer approval. Recorded the pre-existing `Docs` Pages deployments failure and the missing labels.
- Merged pull request #5 as `b73362a`, closed Phase 0 parent issue #1, and deleted `feature/p0-bootstrap`; P0 is complete.
- Launched Phase 1 with parent issue #6, child issues #7-#11, and branch `feature/p1-source-inventory`.
- Completed P1.1-P1.5: 211-file inventory; control and column parsers (57/55/101); control map (112 entries, 0 missing); binding provenance validator; synthetic fixtures and a golden-output inventory. Closed child issues #7-#11.
- Opened pull request #12 with the Phase 1 close-out report and queued it for maintainer approval.
- Merged pull request #12 as `d627751`, closed Phase 1 parent issue #6, and deleted `feature/p1-source-inventory`; P1 is complete.
- Launched Phase 2 with parent issue #13, child issues #14-#19, and branch `feature/p2-coefficient-catalog`.
- Completed P2.1-P2.6: `.COE` schemas (38 supported, 2 explicit unsupported), structural PRM/DAT parser, key catalog, normalized CSV manifest, bundle commands, and expanded tests. Closed child issues #14-#19.
- Opened pull request #20 with the Phase 2 close-out report and queued it for maintainer approval.
- Merged pull request #20 as `17d274e`, closed Phase 2 parent issue #13, and deleted `feature/p2-coefficient-catalog`; P2 is complete.
- Launched Phase 3 with parent issue #21, child issues #22-#27, and branch `feature/p3-console-runner`.
- P3 progress: runtime adapter, isolated runner, failure records, synthetic console input, and typed `csvyieldtable` parser. Closed #22, #24, #25, #27. #23 and #26 are blocked because host Wine crashes on every Windows process; the failure is recorded and no curve was invented.
- Installed WineHQ stable 11.0, which fixed the host startup crash. The synthetic console input was accepted and produced 301 CSV rows. Closed #23 and #26; P3 is complete pending review.
- Opened pull request #28 with the Phase 3 close-out report and queued it for maintainer approval.
- Merged pull request #28 as `53ebc2c`, closed Phase 3 parent issue #21, and deleted `feature/p3-console-runner`; P3 is complete.
- Launched Phase 4 with parent issue #29, child issues #30-#34, and branch `feature/p4-curve-api`.
- Completed P4.1-P4.5: typed curve API and service, 301-row synthetic curve dataset, provenance manifest, and unit/property/regression tests. Closed child issues #30-#34.
- Opened pull request #35 with the Phase 4 close-out report and queued it for maintainer approval.
- Merged pull request #35 as `ba6f339`, closed Phase 4 parent issue #29, and deleted `feature/p4-curve-api`; P4 is complete.
- Launched Phase 5 with parent issue #36, child issues #37-#42, and branch `feature/p5-python-equations`.
- Completed P5.1-P5.6: VTOTREG4 validated (0.836% age-100 error); REGVCU, REGVU, REGHL, and BA/DQ increments implemented as experimental; validation matrix records all gaps. Closed child issues #37-#42.
- Opened pull request #43 with the Phase 5 close-out report and queued it for maintainer approval.
- Merged pull request #43 as `39ce9ce`, closed Phase 5 parent issue #36, and deleted `feature/p5-python-equations`; P5 is complete.
- Launched Phase 6 with parent issue #44, child issues #45-#49, and branch `feature/p6-interfaces`.
- Completed P6.1-P6.5: Typer CLI, FastAPI service, FRESH-style page, bounded assistant tools, and interface tests. Closed child issues #45-#49.
- Opened pull request #50 with the Phase 6 close-out report and queued it for maintainer approval.
- Merged pull request #50 as `ce9151a`, closed Phase 6 parent issue #44, and deleted `feature/p6-interfaces`; P6 is complete.
- Launched Phase 7 with parent issue #51, child issues #52-#56, and branch `feature/p7-release-integration`.
- Completed P7.1-P7.5: installable package and facade, release regression, release manifest, FEMIC integration docs, and release notes. Closed #52-#56. Publication and the FEMIC repository change are queued for approval.
- Opened pull request #57 with the Phase 7 close-out report and queued it for maintainer approval.
- Merged pull request #57 as `bf93896`, closed Phase 7 parent issue #51, and deleted `feature/p7-release-integration`; P0-P7 are complete. The 0.1.0 release candidate is built; tag, release, PyPI upload, and the FEMIC repository change remain separate approvals.
- Published tag `v0.1.0` and GitHub release `fresh-vdyp 0.1.0` with the wheel and sdist. PyPI upload was not run (no credentials); the FEMIC repository change remains pending its own approval and a clean branch.
- Published `fresh-vdyp 0.1.0` to PyPI with the `release.yml` trusted-publisher workflow (environment `pypi`). TestPyPI rejected the same claims, so it is not configured for this publisher.
- Merged the optional FEMIC dependency and back-link guide in `UBC-FRESH/femic#610` (merge commit `c86a464`).
