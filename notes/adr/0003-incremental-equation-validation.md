# ADR 0003: Validate equation families individually against the console

Status: proposed
Date: 2026-11-09
Issues: TBD

## Context

The coefficient files are plain text, but the equation forms are partly in the
compiled model. A full rewrite cannot be trusted without an oracle. Decompiling
the entire native binary is expensive and hard to map back to the coefficient
tables.

## Decision

Implement and promote equation families one at a time. Each family gets:

- an equation note;
- a coefficient mapping;
- a controlled console case;
- bias, RMSE, and maximum-error evidence;
- a promotion decision.

A family that fails validation remains `experimental` or `not_implemented`.

Targeted decompilation is allowed only for a specific unresolved routine, and
the recovered form must still be validated against the console.

## Consequences

Easier:

- incremental progress;
- clear validation evidence;
- failures are local, not global;
- no full-binary dependency.

Harder:

- the model layer grows slowly;
- each family needs its own test fixture;
- some equations may remain unresolved.

## Alternatives considered

- Full decompilation first. Rejected: high cost and poor traceability.
- Fit a black-box statistical emulator. Deferred: useful for interpolation, but
  not a substitute for a validated equation family.
