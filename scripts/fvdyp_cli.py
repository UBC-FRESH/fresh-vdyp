#!/usr/bin/env python3
"""The ``fvdyp`` Typer CLI over the bundle, curve, and equation services.

Commands reuse the same service functions as the API. Every data-bearing result
prints provenance: source file, runtime, console version, and query inputs.

Command-line usage::

    python scripts/fvdyp_cli.py bundle validate --config-dir "$VDYP_CFG_DIR"
    python scripts/fvdyp_cli.py curve query --age-start 100 --age-end 100
    python scripts/fvdyp_cli.py equation matrix
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from bundle_service import SOURCE_MODEL, catalog_payload, extract_bundle, validate_bundle
from curve_api import CurveQuery, load_service
from normalize import DEFAULT_OUTPUT_DIR, utc_now

APP_VERSION = "0.1.0"
DEFAULT_GOLDEN_CSV = Path("fixtures/yield-output/golden-full.csv")
DEFAULT_GOLDEN_METADATA = Path("fixtures/yield-output/metadata.json")
DEFAULT_SCHEMA = Path("notes/reference/vdyp-columns.json")
DEFAULT_ALIASES = Path("notes/reference/vdyp-csv-header-aliases.json")
DEFAULT_MATRIX = Path("notes/reference/vdyp-equation-matrix.json")

app = typer.Typer(help="Inspect a VDYP7 bundle, curves, and equation status.")
bundle_app = typer.Typer(help="Bundle commands.")
curve_app = typer.Typer(help="Curve commands.")
equation_app = typer.Typer(help="Equation commands.")
app.add_typer(bundle_app, name="bundle")
app.add_typer(curve_app, name="curve")
app.add_typer(equation_app, name="equation")

ConfigOption = Annotated[
    Path | None,
    typer.Option("--config-dir", envvar="VDYP_CFG_DIR", help="VDYP_CFG directory."),
]


def _require_config(config_dir: Path | None) -> Path:
    """Return the configuration directory or exit with a usage error.

    Parameters
    ----------
    config_dir : Path or None
        Value from the command line or environment.

    Returns
    -------
    Path
        The configuration directory.
    """
    if config_dir is None:
        typer.echo("error: pass --config-dir or set VDYP_CFG_DIR", err=True)
        raise typer.Exit(code=2)
    return config_dir


@app.command("version")
def version() -> None:
    """Print the CLI version."""
    typer.echo(f"fresh-vdyp {APP_VERSION}")


@bundle_app.command("validate")
def bundle_validate(config_dir: ConfigOption = None) -> None:
    """Validate the bundle structure and control map.

    Parameters
    ----------
    config_dir : Path or None
        VDYP_CFG directory from the option or ``VDYP_CFG_DIR``.
    """
    config = _require_config(config_dir)
    findings = validate_bundle(config)
    for finding in findings:
        typer.echo(finding.render())
    errors = sum(1 for finding in findings if finding.severity == "error")
    typer.echo(f"{errors} error(s), {len(findings) - errors} warning(s)")
    raise typer.Exit(code=1 if errors else 0)


@bundle_app.command("catalog")
def bundle_catalog(
    config_dir: ConfigOption = None,
    json_path: Annotated[Path | None, typer.Option("--json", help="Write JSON here.")] = None,
) -> None:
    """Print the family catalog.

    Parameters
    ----------
    config_dir : Path or None
        VDYP_CFG directory from the option or ``VDYP_CFG_DIR``.
    json_path : Path or None
        Optional JSON output path.
    """
    config = _require_config(config_dir)
    try:
        payload = catalog_payload(config)
    except (OSError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Source model: {payload['source_model']}")
    typer.echo(f"Families: {payload['family_count']}")
    typer.echo(f"Rows: {payload['row_count']}")
    typer.echo(f"Status counts: {payload['status_counts']}")
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        typer.echo(f"Catalog: {json_path}")


@bundle_app.command("extract")
def bundle_extract(
    config_dir: ConfigOption = None,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="Destination directory.")
    ] = DEFAULT_OUTPUT_DIR,
    extracted_at: Annotated[
        str | None, typer.Option("--extracted-at", help="UTC timestamp.")
    ] = None,
) -> None:
    """Normalize the bundle and write the manifest.

    Parameters
    ----------
    config_dir : Path or None
        VDYP_CFG directory from the option or ``VDYP_CFG_DIR``.
    output_dir : Path
        Destination directory.
    extracted_at : str or None
        ISO 8601 UTC timestamp; defaults to now.
    """
    config = _require_config(config_dir)
    timestamp = extracted_at if extracted_at is not None else utc_now()
    try:
        result = extract_bundle(config, output_dir, extracted_at=timestamp)
    except (OSError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    payload = result.to_dict()
    typer.echo(f"Source model: {SOURCE_MODEL}")
    typer.echo(f"Extracted {payload['asset_count']} families with {payload['row_count']} rows")
    typer.echo(f"Unsupported families: {payload['unsupported_count']}")
    typer.echo(f"Manifest: {output_dir / 'manifest.json'}")


@curve_app.command("query")
def curve_query(
    csv_path: Annotated[Path, typer.Option("--csv", help="Yield-table CSV.")] = DEFAULT_GOLDEN_CSV,
    metadata: Annotated[
        Path, typer.Option("--metadata", help="Run metadata JSON.")
    ] = DEFAULT_GOLDEN_METADATA,
    schema: Annotated[Path, typer.Option("--schema", help="Column schema.")] = DEFAULT_SCHEMA,
    aliases: Annotated[Path, typer.Option("--aliases", help="Header aliases.")] = DEFAULT_ALIASES,
    species: Annotated[str | None, typer.Option("--species", help="Species code.")] = None,
    year_start: Annotated[int | None, typer.Option("--year-start")] = None,
    year_end: Annotated[int | None, typer.Option("--year-end")] = None,
    age_start: Annotated[int | None, typer.Option("--age-start")] = None,
    age_end: Annotated[int | None, typer.Option("--age-end")] = None,
    json_path: Annotated[Path | None, typer.Option("--json", help="Write result JSON.")] = None,
) -> None:
    """Query a parsed curve table.

    Parameters
    ----------
    csv_path : Path
        Yield-table CSV.
    metadata : Path
        Run metadata JSON.
    schema : Path
        Column schema.
    aliases : Path
        CSV header aliases.
    species : str or None
        Species code filter.
    year_start : int or None
        First included year.
    year_end : int or None
        Last included year.
    age_start : int or None
        First included age.
    age_end : int or None
        Last included age.
    json_path : Path or None
        Optional result JSON path.
    """
    try:
        service = load_service(csv_path, metadata, schema_path=schema, alias_path=aliases)
        result = service.query(
            CurveQuery(
                species=species,
                year_start=year_start,
                year_end=year_end,
                age_start=age_start,
                age_end=age_end,
            )
        )
    except (OSError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"status: {result.status}")
    if result.reason:
        typer.echo(f"reason: {result.reason}")
    typer.echo(f"points: {len(result.points)}")
    typer.echo(f"source: {result.provenance.source_file}")
    typer.echo(f"runtime: {result.provenance.runtime}")
    typer.echo(f"console: {result.provenance.console_version}")
    typer.echo(f"query: {json.dumps(result.provenance.query)}")
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")


@equation_app.command("matrix")
def equation_matrix(
    matrix: Annotated[Path, typer.Option("--matrix", help="Matrix JSON.")] = DEFAULT_MATRIX,
    json_path: Annotated[Path | None, typer.Option("--json", help="Write JSON here.")] = None,
) -> None:
    """Print the family validation matrix.

    Parameters
    ----------
    matrix : Path
        Matrix JSON file.
    json_path : Path or None
        Optional JSON output path.
    """
    try:
        payload = json.loads(matrix.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    rows = payload.get("families") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        typer.echo("error: matrix has no families", err=True)
        raise typer.Exit(code=1)
    for row in rows:
        if isinstance(row, dict):
            typer.echo(f"{row.get('family')}: {row.get('status')}")
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
