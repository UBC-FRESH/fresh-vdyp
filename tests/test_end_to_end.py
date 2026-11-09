"""End-to-end catalog tests over a synthetic fixture bundle."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bundle_service import catalog_payload, extract_bundle, validate_bundle
from inventory_vdyp import sha256_file
from provenance import validate_manifest

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
EXTRACTED_AT = "2026-11-09T00:00:00Z"


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (config / "VDYP.CTR").write_text(
        "\n".join(
            [
                control_line("061", "coe\\COMPLIM.coe", "Species limits"),
                control_line("090", "coe\\VTOTREG4.coe", "Whole stem"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (coe / "SP0.DAT").write_text("AC\nAT\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nESSF\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    (coe / "COMPLIM.COE").write_text("AC C 49.4 153.3\n", encoding="ascii")
    return config


def test_synthetic_bundle_catalog_and_extract_agree(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    findings = validate_bundle(config)
    assert [finding for finding in findings if finding.severity == "error"] == []

    catalog = catalog_payload(config)
    output = tmp_path / "normalized"
    result = extract_bundle(config, output, extracted_at=EXTRACTED_AT)
    summary = result.to_dict()

    assert catalog["family_count"] == 2
    assert catalog["row_count"] == summary["row_count"] == 2
    assert summary["asset_count"] == 1
    assert summary["unsupported_count"] == 1

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    assert validate_manifest(manifest[0]) == ()
    assert manifest[0]["source_sha256"] == sha256_file(config / "coe" / "VTOTREG4.COE")

    with (output / "vtotreg4.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == manifest[0]["row_count"]
    assert [row["source_line"] for row in rows] == ["1", "2"]
