"""Tests for coefficient normalization and the provenance manifest."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from coe_parser import parse_coe_file
from inventory_vdyp import sha256_file
from normalize import (
    build_normalized_catalog,
    format_value,
    main,
    manifest_entry,
    normalize_table,
    utc_now,
    write_csv,
    write_manifest,
)
from provenance import ManifestError, validate_manifest

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
EXTRACTED_AT = "2026-11-09T00:00:00Z"


def test_format_value_is_stable() -> None:
    assert format_value(1) == "1"
    assert format_value(-1.00505) == "-1.00505"
    assert format_value("AC") == "AC"


def test_write_csv_preserves_line_and_columns(tmp_path: Path) -> None:
    table = parse_coe_file(FIXTURE_COE)
    path = tmp_path / "vtotreg4.csv"
    digest = write_csv(table, path)
    assert digest == sha256_file(path)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][:2] == ["source_line", "group"]
    assert len(rows[0]) == 11
    assert rows[1][0] == "1"
    assert rows[1][1] == "1"
    assert rows[2][1] == "2"


def test_manifest_entry_validates_and_hashes_match(tmp_path: Path) -> None:
    table = parse_coe_file(FIXTURE_COE)
    asset, entry = normalize_table(
        table,
        FIXTURE_COE,
        tmp_path,
        extracted_at=EXTRACTED_AT,
        equation_family="whole_stem_volume",
        control_sequence="090",
    )
    assert validate_manifest(entry) == ()
    assert entry["normalized_sha256"] == sha256_file(tmp_path / "vtotreg4.csv")
    assert entry["source_sha256"] == sha256_file(FIXTURE_COE)
    assert entry["row_count"] == 2
    assert entry["family"] == "whole_stem_volume"
    assert entry["control_sequence"] == "090"
    assert asset.normalized_sha256 == entry["normalized_sha256"]


def test_manifest_entry_rejects_a_bad_normalized_hash(tmp_path: Path) -> None:
    table = parse_coe_file(FIXTURE_COE)
    with pytest.raises(ManifestError, match="normalized_sha256"):
        manifest_entry(
            table,
            source_sha256=sha256_file(FIXTURE_COE),
            normalized_sha256="BAD",
            extracted_at=EXTRACTED_AT,
            equation_family="whole_stem_volume",
            control_sequence="090",
        )


def test_normalization_is_deterministic(tmp_path: Path) -> None:
    table = parse_coe_file(FIXTURE_COE)
    first = tmp_path / "first"
    second = tmp_path / "second"
    _, entry_one = normalize_table(
        table,
        FIXTURE_COE,
        first,
        extracted_at=EXTRACTED_AT,
        equation_family="whole_stem_volume",
        control_sequence="090",
    )
    _, entry_two = normalize_table(
        table,
        FIXTURE_COE,
        second,
        extracted_at=EXTRACTED_AT,
        equation_family="whole_stem_volume",
        control_sequence="090",
    )
    assert (first / "vtotreg4.csv").read_bytes() == (second / "vtotreg4.csv").read_bytes()
    assert entry_one == entry_two


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (config / "VDYP.CTR").write_text(
        "\n".join(
            [
                control_line("090", "coe\\VTOTREG4.coe", "Whole stem"),
                control_line("121", "coe\\GROWBA27.coe", "BA growth"),
                control_line("061", "coe\\COMPLIM.coe", "Species limits"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (coe / "SP0.DAT").write_text("AC\nAT\nB\nC\nD\nE\nF\nH\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nBG\nBWBS\nCDF\nCWH\nESSF\nICH\nIDF\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    line = " ".join(["AT", "A0", "1", *(["0.5"] * 16)])
    (coe / "GROWBA27.COE").write_text(line + "\n", encoding="ascii")
    (coe / "COMPLIM.COE").write_text("AC C 49.4 153.3\n", encoding="ascii")
    return config


def test_build_normalized_catalog_covers_supported_families(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    result = build_normalized_catalog(config, tmp_path / "normalized", extracted_at=EXTRACTED_AT)
    payload = result.to_dict()
    assert payload["asset_count"] == 2
    assert payload["row_count"] == 3
    assert payload["unsupported_count"] == 1
    assert (tmp_path / "normalized" / "vtotreg4.csv").is_file()
    assert (tmp_path / "normalized" / "growba27.csv").is_file()
    assert not (tmp_path / "normalized" / "complim.csv").exists()
    assert all(validate_manifest(entry) == () for entry in result.manifest)


def test_write_manifest_writes_both_files(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "normalized"
    result = build_normalized_catalog(config, output, extracted_at=EXTRACTED_AT)
    write_manifest(result, output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert len(manifest) == 2
    assert summary["asset_count"] == 2
    assert summary["unsupported"][0]["family"] == "complim"


def test_main_writes_the_catalog(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "out"
    assert (
        main(
            [
                "--config-dir",
                str(config),
                "--output-dir",
                str(output),
                "--extracted-at",
                EXTRACTED_AT,
            ]
        )
        == 0
    )
    assert (output / "manifest.json").is_file()
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_config(tmp_path / "install")
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    output = tmp_path / "out"
    assert main(["--output-dir", str(output), "--extracted-at", EXTRACTED_AT]) == 0
    assert (output / "manifest.json").is_file()
    capsys.readouterr()


def test_main_without_a_directory_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    assert main(["--output-dir", str(tmp_path / "out")]) == 2
    assert "VDYP_CFG_DIR" in capsys.readouterr().err


def test_main_with_a_missing_directory_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "--config-dir",
                str(tmp_path / "absent"),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )
    assert "error:" in capsys.readouterr().err


def test_utc_now_ends_with_z() -> None:
    assert utc_now().endswith("Z")


def test_sha_helper_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_bytes(b"abc")
    assert sha256_file(path) == hashlib.sha256(b"abc").hexdigest()
