"""Tests for the synthetic console input fixture."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE: Path = ROOT / "fixtures" / "console-input"
CONSOLE: Path = FIXTURE / "Console"
EXPECTED = {
    "HISTORY.csv",
    "LAYER.csv",
    "NON_VEG.csv",
    "OTHER_VEG.csv",
    "POLYGON.csv",
    "POLYGON_ID.csv",
    "SPECIES.csv",
    "VRIADJST.csv",
}


def test_manifest_lists_every_file_with_its_size() -> None:
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    listed = {Path(item["path"]).name: item["size_bytes"] for item in manifest["files"]}
    actual = {path.name: path.stat().st_size for path in CONSOLE.iterdir() if path.is_file()}
    assert listed == actual
    assert manifest["status"] == "synthetic"


def test_expected_input_files_are_present() -> None:
    assert {path.name for path in CONSOLE.iterdir() if path.is_file()} == EXPECTED


def test_fixture_is_small() -> None:
    total = sum(path.stat().st_size for path in CONSOLE.iterdir() if path.is_file())
    assert total < 2000


def test_polygon_and_identifier_share_one_record() -> None:
    with (CONSOLE / "POLYGON.csv").open(encoding="ascii", newline="") as handle:
        polygons = list(csv.DictReader(handle))
    with (CONSOLE / "POLYGON_ID.csv").open(encoding="ascii", newline="") as handle:
        identifiers = list(csv.DictReader(handle))
    assert len(polygons) == 1
    assert len(identifiers) == 1
    assert polygons[0]["POLYGON_RCRD_ID"] == identifiers[0]["POLYGON_RCRD_ID"] == "1"


def test_one_layer_one_species() -> None:
    with (CONSOLE / "LAYER.csv").open(encoding="ascii", newline="") as handle:
        layers = list(csv.DictReader(handle))
    with (CONSOLE / "SPECIES.csv").open(encoding="ascii", newline="") as handle:
        species = list(csv.DictReader(handle))
    assert len(layers) == 1
    assert len(species) == 1
    assert species[0]["SPECIES_CD"] == "AT"
    assert species[0]["SPECIES_PCT"] == "100"


def test_optional_tables_are_header_only() -> None:
    for name in ("OTHER_VEG.csv", "VRIADJST.csv"):
        with (CONSOLE / name).open(encoding="ascii", newline="") as handle:
            rows = list(csv.reader(handle))
        assert len(rows) == 1
