# ADR 0004: Use per-value attribution and evidence labels

Status: proposed
Date: 2026-11-09
Issues: TBD

## Context

`fresh-vdyp` reads and reimplements parts of a BC government model. The package
must not blur the source model with the interoperability layer.

## Decision

Every public value carries:

```text
source
source version
source file or console run
source SHA256 where possible
processing step
evidence level
citation
```

Evidence levels are `source_table`, `model_output`, `reimplemented`,
`validated_against`, `experimental`, `not_implemented`, and `unavailable`.

README, CLI, API, web, and assistant all state that `fresh-vdyp` is an
interoperability layer, not the author of VDYP7.

## Consequences

Easier:

- auditability;
- visible validation gaps;
- model outputs are not mistaken for measured data;
- citation is part of the data contract.

Harder:

- every output path carries metadata;
- tests must assert provenance;
- the assistant needs a provenance tool and refusal rules.

## Alternatives considered

- Cite only in the README. Rejected: per-value provenance is needed for science.
- Treat reimplementation as equivalent to the source. Rejected: hides validation
  gaps.
