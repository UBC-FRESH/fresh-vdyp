#!/usr/bin/env python3
"""The first ``fresh-vdyp`` command-line surface.

The commands run from the repository with ``python scripts/fresh_vdyp.py`` until
the installable package lands::

    python scripts/fresh_vdyp.py bundle extract --config-dir "$VDYP_CFG_DIR"
    python scripts/fresh_vdyp.py bundle validate --config-dir "$VDYP_CFG_DIR"
    python scripts/fresh_vdyp.py bundle catalog --config-dir "$VDYP_CFG_DIR"

Every command reports the source model. The configuration directory defaults to
``VDYP_CFG_DIR``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from bundle_service import SOURCE_MODEL, catalog_payload, extract_bundle, validate_bundle
from normalize import DEFAULT_OUTPUT_DIR, utc_now


def config_from_environment() -> Path | None:
    """Resolve the configuration directory from ``VDYP_CFG_DIR``.

    Returns
    -------
    Path or None
        The environment value when set and non-empty, otherwise ``None``.
    """
    value = os.environ.get("VDYP_CFG_DIR")
    return Path(value) if value else None


def resolve_config(args: argparse.Namespace) -> Path | None:
    """Resolve the configuration directory from arguments or environment.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments with an optional ``config_dir``.

    Returns
    -------
    Path or None
        The configuration directory, or ``None`` when it is not supplied.
    """
    value: Path | None = args.config_dir
    return value if value is not None else config_from_environment()


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser with ``bundle extract``, ``validate``, and ``catalog``.
    """
    parser = argparse.ArgumentParser(prog="fresh-vdyp", description="Inspect a VDYP7 bundle.")
    bundle = parser.add_subparsers(dest="command", required=True).add_parser(
        "bundle", help="bundle commands"
    )
    actions = bundle.add_subparsers(dest="action", required=True)

    extract = actions.add_parser("extract", help="normalize coefficient tables")
    extract.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    extract.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"destination directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    extract.add_argument("--extracted-at", default=None, help="ISO 8601 UTC timestamp")

    validate = actions.add_parser("validate", help="validate the bundle structure")
    validate.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")

    catalog = actions.add_parser("catalog", help="print the family catalog")
    catalog.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    catalog.add_argument("--json", type=Path, help="also write the catalog as JSON")
    return parser


def run_extract(args: argparse.Namespace) -> int:
    """Run ``bundle extract``.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments.

    Returns
    -------
    int
        ``0`` on success and ``2`` on a missing directory or parse failure.
    """
    config_dir = resolve_config(args)
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    extracted_at: str = args.extracted_at if args.extracted_at is not None else utc_now()
    try:
        result = extract_bundle(config_dir, args.output_dir, extracted_at=extracted_at)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = result.to_dict()
    print(f"Source model: {SOURCE_MODEL}")
    print(f"Extracted {payload['asset_count']} families with {payload['row_count']} rows")
    print(f"Unsupported families: {payload['unsupported_count']}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")
    return 0


def run_validate(args: argparse.Namespace) -> int:
    """Run ``bundle validate``.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments.

    Returns
    -------
    int
        ``0`` when there are no errors, ``1`` when errors are found, and ``2``
        when the configuration directory is not supplied.
    """
    config_dir = resolve_config(args)
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    findings = validate_bundle(config_dir)
    for finding in findings:
        print(finding.render())
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = len(findings) - errors
    print(f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def run_catalog(args: argparse.Namespace) -> int:
    """Run ``bundle catalog``.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments.

    Returns
    -------
    int
        ``0`` on success and ``2`` when the configuration directory is missing.
    """
    config_dir = resolve_config(args)
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    try:
        payload = catalog_payload(config_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Source model: {payload['source_model']}")
    print(f"Families: {payload['family_count']}")
    print(f"Rows: {payload['row_count']}")
    print(f"Status counts: {payload['status_counts']}")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Catalog: {args.json}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line surface.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        The command's exit status.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "extract":
        return run_extract(args)
    if args.action == "validate":
        return run_validate(args)
    if args.action == "catalog":
        return run_catalog(args)
    parser.error(f"unknown action: {args.action}")


if __name__ == "__main__":
    sys.exit(main())
