# ADR 0002: Keep code separate from the VDYP coefficient bundle

Status: proposed
Date: 2026-11-09
Issues: TBD

## Context

The VDYP coefficient bundle is a government model asset. It is compact enough to
copy, but committing it would obscure provenance, mix code review with data
review, and freeze a particular install in the repository.

## Decision

Track parsers, schemas, manifests, download instructions, and tiny fixtures.
Do not track the raw `VDYP_CFG` bundle or large normalized assets.

Publish normalized assets as release artifacts with a checksummed manifest. A
user can rebuild them from a local install using the CLI.

## Consequences

Easier:

- small repository and fast CI;
- clear attribution;
- independent data releases;
- no accidental drift from the official install.

Harder:

- a clean install needs a data-fetch or rebuild step;
- tests need fixtures;
- release engineering must publish and verify assets.

## Alternatives considered

- Commit the full bundle. Rejected: provenance and repository-size problems.
- Git LFS for the full bundle. Deferred: possible for a handful of fixtures, but
  not for the whole install.
