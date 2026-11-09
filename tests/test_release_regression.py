"""Release-level golden regression over the synthetic evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from curve_api import CurveQuery, load_service
from equations import validate_against_golden
from provenance import validate_manifest

ROOT: Path = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA = ROOT / "fixtures" / "yield-output" / "metadata.json"
DATASET_MANIFEST = ROOT / "fixtures" / "yield-output" / "dataset-manifest.json"
EQUATION_MATRIX = ROOT / "notes" / "reference" / "vdyp-equation-matrix.json"
SCHEMA = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"
RELEASE_NOTES = ROOT / "RELEASE_NOTES.md"
INSTALL = os.environ.get("VDYP_INSTALL")


def test_dataset_manifest_and_hash() -> None:
    manifest = json.loads(DATASET_MANIFEST.read_text(encoding="utf-8"))
    assert validate_manifest(manifest) == ()
    assert manifest[0]["row_count"] == 301
    assert manifest[0]["source_sha256"] == hashlib.sha256(GOLDEN.read_bytes()).hexdigest()


def test_curve_age_100_regression() -> None:
    service = load_service(GOLDEN, METADATA, schema_path=SCHEMA, alias_path=ALIASES)
    result = service.query(CurveQuery(age_start=100, age_end=100))
    assert result.status == "ok"
    assert len(result.points) == 1
    assert result.points[0].volume_ws == pytest.approx(436.39481)
    assert result.provenance.runtime == "Wine 11.0"


def test_equation_matrix_regression() -> None:
    matrix = json.loads(EQUATION_MATRIX.read_text(encoding="utf-8"))
    rows = {row["family"]: row for row in matrix["families"]}
    assert rows["VTOTREG4"]["status"] == "validated"
    assert float(rows["VTOTREG4"]["error"]) <= float(rows["VTOTREG4"]["tolerance"])


def test_release_notes_record_the_femic_gap() -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8").lower()
    assert "femic" in text
    assert "no femic output fixture" in text


@pytest.mark.skipif(not INSTALL, reason="VDYP_INSTALL is not set")
def test_console_regression_matches_the_golden_data() -> None:
    assert INSTALL is not None
    config = Path(INSTALL) / "VDYP_CFG"
    rows = validate_against_golden(config, GOLDEN)
    age_100 = [row for row in rows if row["age"] == 100]
    assert age_100
    assert float(str(age_100[0]["relative_error"])) <= 0.01
