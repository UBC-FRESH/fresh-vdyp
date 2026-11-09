Overview
========

``fresh-vdyp`` is a public Python interoperability layer for the BC VDYP7
coefficient bundle, console runner, and yield curves. It is not a claim of
authorship over the BC model or its data.

The first release has four layers:

1. parse and catalog ``VDYP.CTR`` and the ``coe`` bundle;
2. run ``VDYP7Console`` and parse ``csvyieldtable`` output;
3. expose typed yield curves with provenance;
4. reimplement equation families incrementally and validate them against the
   console.

Read the plan in the repository:

- `program plan <https://github.com/UBC-FRESH/fresh-vdyp/blob/main/notes/plan/0001-program-plan.md>`_
- `data and provenance <https://github.com/UBC-FRESH/fresh-vdyp/blob/main/notes/plan/0002-data-provenance.md>`_
- `architecture <https://github.com/UBC-FRESH/fresh-vdyp/blob/main/notes/plan/0003-architecture.md>`_
- `validation and release <https://github.com/UBC-FRESH/fresh-vdyp/blob/main/notes/plan/0004-validation-release.md>`_

Source attribution
------------------

Every coefficient file, control map, curve, and derived value records the BC
source, version, file, SHA256, extraction date, and citation. Reimplemented
logic is labelled ``reimplemented`` and is validated against console output
where possible.

Non-goals
---------

- a byte-for-byte clone of the native VDYP7 binaries;
- full model parity in the first release;
- replacing the console before an equation family is validated;
- committing the raw government bundle or large data assets.
