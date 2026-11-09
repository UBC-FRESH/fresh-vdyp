"""Tests for the fvdyp Typer CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from fvdyp_cli import app

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
GOLDEN: Path = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA: Path = ROOT / "fixtures" / "yield-output" / "metadata.json"
SCHEMA: Path = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES: Path = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"
MATRIX: Path = ROOT / "notes" / "reference" / "vdyp-equation-matrix.json"

runner = CliRunner()


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (config / "VDYP.CTR").write_text(
        control_line("090", "coe\\VTOTREG4.coe", "Whole stem") + "\n", encoding="ascii"
    )
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (coe / "SP0.DAT").write_text("AC\nAT\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nBWBS\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    return config


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "fresh-vdyp 0.1.0" in result.stdout


def test_bundle_catalog_and_validate(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    catalog = runner.invoke(app, ["bundle", "catalog", "--config-dir", str(config)])
    assert catalog.exit_code == 0, catalog.stdout
    assert "Families: 1" in catalog.stdout
    validate = runner.invoke(app, ["bundle", "validate", "--config-dir", str(config)])
    assert validate.exit_code == 0, validate.stdout
    assert "0 error(s)" in validate.stdout


def test_bundle_catalog_writes_json(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "catalog.json"
    result = runner.invoke(
        app, ["bundle", "catalog", "--config-dir", str(config), "--json", str(output)]
    )
    assert result.exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["family_count"] == 1


def test_bundle_extract(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "normalized"
    result = runner.invoke(
        app,
        [
            "bundle",
            "extract",
            "--config-dir",
            str(config),
            "--output-dir",
            str(output),
            "--extracted-at",
            "2026-11-09T00:00:00Z",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (output / "manifest.json").is_file()


def test_curve_query() -> None:
    result = runner.invoke(
        app,
        [
            "curve",
            "query",
            "--csv",
            str(GOLDEN),
            "--metadata",
            str(METADATA),
            "--schema",
            str(SCHEMA),
            "--aliases",
            str(ALIASES),
            "--age-start",
            "100",
            "--age-end",
            "100",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "status: ok" in result.stdout
    assert "points: 1" in result.stdout
    assert "runtime: Wine 11.0" in result.stdout
    assert "source: golden-full.csv" in result.stdout


def test_curve_query_rejects_a_bad_range() -> None:
    result = runner.invoke(
        app,
        [
            "curve",
            "query",
            "--csv",
            str(GOLDEN),
            "--metadata",
            str(METADATA),
            "--schema",
            str(SCHEMA),
            "--aliases",
            str(ALIASES),
            "--age-start",
            "10",
            "--age-end",
            "1",
        ],
    )
    assert result.exit_code == 1
    assert "age_start must not exceed age_end" in result.stderr


def test_equation_matrix() -> None:
    result = runner.invoke(app, ["equation", "matrix", "--matrix", str(MATRIX)])
    assert result.exit_code == 0
    assert "VTOTREG4: validated" in result.stdout
    assert "REGVCU: experimental" in result.stdout


def test_missing_config_is_a_usage_error() -> None:
    result = runner.invoke(app, ["bundle", "validate"])
    assert result.exit_code == 2
    assert "VDYP_CFG_DIR" in result.stderr
