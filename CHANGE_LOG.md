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
