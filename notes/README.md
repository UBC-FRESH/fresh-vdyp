# Notes

Notes are the persistent, agent-friendly context for this project. They hold
what a future reader, human or agent, needs and cannot get from the code, the
issues, or the changelog alone.

## Plans

- [`plan/0001-program-plan.md`](plan/0001-program-plan.md): mission, scope, targets,
  evidence levels, risks, and first-release definition of done.
- [`plan/0002-data-provenance.md`](plan/0002-data-provenance.md): source classes,
  manifest schema, asset layout, citation, and publication boundary.
- [`plan/0003-architecture.md`](plan/0003-architecture.md): package layout, runner,
  curve API, CLI, web, assistant, and FEMIC boundary.
- [`plan/0004-validation-release.md`](plan/0004-validation-release.md): validation
  ladder, golden evidence, release checks, and integration gates.

## Reference

- [`reference/vdyp-inventory.md`](reference/vdyp-inventory.md): observed VDYP7
  install, control files, coefficient bundle, output schema, and runtime note.
- [`reference/vdyp-model-map.md`](reference/vdyp-model-map.md): control sequences,
  coefficient families, known gaps, and promotion order.

## Decisions

- [`adr/0001-console-and-data-first.md`](adr/0001-console-and-data-first.md):
  build the console/data layer before the Python model.
- [`adr/0002-code-and-coefficient-assets.md`](adr/0002-code-and-coefficient-assets.md):
  code in Git, bundle assets as release artifacts.
- [`adr/0003-incremental-equation-validation.md`](adr/0003-incremental-equation-validation.md):
  validate each equation family against the console.
- [`adr/0004-attribution-and-evidence-labels.md`](adr/0004-attribution-and-evidence-labels.md):
  per-value provenance and evidence labels.
- [`adr/0005-femic-package-boundary.md`](adr/0005-femic-package-boundary.md): FEMIC
  consumes `fresh-vdyp` through an optional dependency.

## Reports

- `reports/`: phase close-out reports. Start from
  [`reports/phase-closeout-template.md`](reports/phase-closeout-template.md).
