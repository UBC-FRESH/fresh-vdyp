# ADR 0001: Build the console/data layer before the Python model

Status: proposed
Date: 2026-11-09
Issues: TBD

## Context

VDYP7 is a native growth engine with a large coefficient bundle. The bundle
contains plain-text coefficients, but not a complete human-readable equation
specification. A full Python rewrite from day one would block on reverse
engineering before producing any public value.

## Decision

The first release is a data and runner layer:

- parse and catalog the coefficient bundle;
- wrap `VDYP7Console`;
- parse `csvyieldtable` output;
- expose typed curves with provenance.

Python equation families are added incrementally and validated against the
console oracle.

## Consequences

Easier:

- immediate public value;
- a clean validation oracle;
- no need to decompile the full binary first;
- provenance is direct.

Harder:

- the first release depends on the console runtime;
- equation parity is incremental;
- a clean install needs a runtime or golden fixtures.

## Alternatives considered

- Full Python rewrite first. Rejected: blocks on missing equation forms.
- Decompile everything first. Rejected: high effort and poor traceability.
- Only document the bundle. Rejected: no usable curve API.
