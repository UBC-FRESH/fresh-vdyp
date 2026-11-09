"""Tests for the bundle service layer and the fresh-vdyp CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bundle_service import (
    BundleDiagnostic,
    catalog_payload,
    extract_bundle,
    find_ci,
    required_path,
    validate_bundle,
)

ROOT: Path = Path(__file__).resolve().parents[1]
SCRIPTS: Path = ROOT / "scripts"
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
EXTRACTED_AT = "2026-11-09T00:00:00Z"


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(
    root: Path,
    *,
    missing_target: bool = False,
    invalid_species: bool = False,
    unsupported: bool = False,
) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    lines = [control_line("090", "coe\\VTOTREG4.coe", "Whole stem")]
    if missing_target:
        lines.append(control_line("091", "coe\\ABSENT.coe", "Missing"))
    (config / "VDYP.CTR").write_text("\n".join(lines) + "\n", encoding="ascii")
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (config / "VDYP.tcl").write_text("*COLUMNS\n", encoding="ascii")
    (coe / "SP0.DAT").write_text("AC\nAT\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nESSF\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    if invalid_species:
        (coe / "REGHL.COE").write_text("ZZ AT C 1 0.8 1.0\n", encoding="ascii")
    if unsupported:
        (coe / "COMPLIM.COE").write_text("AC C 49.4 153.3\n", encoding="ascii")
    return config


def codes(findings: tuple[BundleDiagnostic, ...]) -> list[str]:
    return [finding.code for finding in findings]


def test_required_path_and_find_ci(tmp_path: Path) -> None:
    (tmp_path / "coe").mkdir()
    (tmp_path / "coe" / "SP0.DAT").write_text("AC\n", encoding="ascii")
    assert find_ci(tmp_path / "coe", "sp0.dat") == tmp_path / "coe" / "SP0.DAT"
    assert required_path(tmp_path, "coe/SP0.DAT") == tmp_path / "coe" / "SP0.DAT"
    assert required_path(tmp_path, "coe/BEC0.DAT") is None
    assert find_ci(tmp_path, "absent") is None


def test_validate_accepts_a_complete_bundle(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    assert validate_bundle(config) == ()


def test_validate_reports_missing_required_files(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    (config / "VDYP.CTR").unlink()
    findings = validate_bundle(config)
    assert "MISSING-FILE" in codes(findings)
    assert any("VDYP.CTR" in finding.message for finding in findings)


def test_validate_reports_a_missing_target(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install", missing_target=True)
    findings = validate_bundle(config)
    assert "MISSING-TARGET" in codes(findings)


def test_validate_reports_invalid_keys(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install", invalid_species=True)
    findings = validate_bundle(config)
    assert "INVALID-KEYS" in codes(findings)
    assert any(finding.severity == "error" for finding in findings)


def test_validate_warns_about_unsupported_families(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install", unsupported=True)
    findings = validate_bundle(config)
    assert codes(findings) == ["UNSUPPORTED-FAMILY"]
    assert findings[0].severity == "warning"


def test_validate_reports_a_missing_directory(tmp_path: Path) -> None:
    findings = validate_bundle(tmp_path / "absent")
    assert codes(findings) == ["MISSING-DIR"]


def test_catalog_payload_names_the_source(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    payload = catalog_payload(config)
    assert payload["source_model"] == "VDYP7"
    assert payload["family_count"] == 1
    assert payload["row_count"] == 2


def test_extract_bundle_writes_csv_and_manifest(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "out"
    result = extract_bundle(config, output, extracted_at=EXTRACTED_AT)
    assert len(result.assets) == 1
    assert (output / "vtotreg4.csv").is_file()
    assert (output / "manifest.json").is_file()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["source_file"] == "VDYP_CFG/coe/VTOTREG4.COE"


def test_bundle_diagnostic_renders() -> None:
    rendered = BundleDiagnostic("error", "MISSING-FILE", "gone").render()
    assert "error" in rendered
    assert "MISSING-FILE" in rendered
    assert "gone" in rendered


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "fresh_vdyp.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_lists_bundle_commands() -> None:
    result = run_cli("bundle", "--help")
    assert result.returncode == 0
    assert "extract" in result.stdout
    assert "validate" in result.stdout
    assert "catalog" in result.stdout


def test_cli_catalog_runs(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "catalog.json"
    result = run_cli("bundle", "catalog", "--config-dir", str(config), "--json", str(output))
    assert result.returncode == 0, result.stderr
    assert "Source model: VDYP7" in result.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["family_count"] == 1


def test_cli_validate_passes_a_valid_bundle(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    result = run_cli("bundle", "validate", "--config-dir", str(config))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s), 0 warning(s)" in result.stdout


def test_cli_validate_fails_a_missing_target(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install", missing_target=True)
    result = run_cli("bundle", "validate", "--config-dir", str(config))
    assert result.returncode == 1
    assert "MISSING-TARGET" in result.stdout


def test_cli_extract_writes_outputs(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "normalized"
    result = run_cli(
        "bundle",
        "extract",
        "--config-dir",
        str(config),
        "--output-dir",
        str(output),
        "--extracted-at",
        EXTRACTED_AT,
    )
    assert result.returncode == 0, result.stderr
    assert (output / "manifest.json").is_file()
    assert "Source model: VDYP7" in result.stdout


def test_cli_without_a_config_dir_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    result = run_cli("bundle", "validate")
    assert result.returncode == 2
    assert "VDYP_CFG_DIR" in result.stderr


def test_cli_rejects_an_unknown_action() -> None:
    result = run_cli("bundle", "bogus")
    assert result.returncode == 2
