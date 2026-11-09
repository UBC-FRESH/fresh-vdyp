# ADR 0005: Integrate with FEMIC through an optional package dependency

Status: proposed
Date: 2026-11-09
Issues: TBD

## Context

FEMIC already orchestrates VDYP runs and parses output tables. Copying more VDYP
code into FEMIC would duplicate the data contract and provenance rules.

## Decision

`fresh-vdyp` is the source package for the public VDYP bundle catalog, console
runner, curve API, and validated Python equation families.

FEMIC consumes it through an optional dependency and a thin adapter. The adapter
passes provenance through and records the package version, console version, and
bundle manifest hash. If the package is absent, FEMIC keeps its existing path.

## Consequences

Easier:

- one tested implementation;
- clear release versioning;
- incremental FEMIC adoption;
- provenance travels with the value.

Harder:

- package and FEMIC releases need coordination;
- the adapter needs a compatibility test;
- data assets must be available to FEMIC users.

## Alternatives considered

- Vendor the code into FEMIC. Rejected: duplicated implementation.
- Keep the package independent forever. Rejected: the goal is a usable
  dependency.
