"""Tests for the synthetic fixture bundle and its provenance example."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from provenance import validate_manifest
from vdyp_control import load_column_table, load_control_file

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURES: Path = ROOT / "fixtures"
MINI: Path = FIXTURES / "mini-bundle"


def test_fixture_manifest_lists_every_file_with_its_size() -> None:
    manifest = json.loads((MINI / "manifest.json").read_text(encoding="utf-8"))
    listed = {item["path"]: item["size_bytes"] for item in manifest["files"]}
    actual = {
        path.relative_to(MINI).as_posix(): path.stat().st_size
        for path in MINI.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    assert listed == actual
    assert manifest["status"] == "synthetic"


def test_fixture_bundle_is_small() -> None:
    total = sum(path.stat().st_size for path in MINI.rglob("*") if path.is_file())
    assert total < 2000


def test_fixture_control_file_parses() -> None:
    parsed = load_control_file(MINI / "control" / "VDYP.CTR")
    assert [entry.sequence for entry in parsed.entries] == ["001", "025", "090", "091"]
    assert parsed.comment_lines == 1
    assert parsed.entries[0].value == "00000010"
    assert parsed.entries[1].value == ""
    assert parsed.entries[2].codes == ("RD_YVT1", "IPSJF117")


def test_fixture_column_table_parses() -> None:
    parsed = load_column_table(MINI / "control" / "VDYP.tcl")
    assert [column.id for column in parsed.columns] == [0, 20, 100]
    assert parsed.columns[1].name == "Pct Stk"
    assert parsed.columns[1].description == "Pcnt Stockable"
    assert parsed.columns[2].units == "m3/ha"


def test_example_manifest_entry_is_valid() -> None:
    payload = json.loads(
        (FIXTURES / "manifests" / "example-coefficient.json").read_text(encoding="utf-8")
    )
    assert validate_manifest(payload) == ()


def test_example_manifest_hash_matches_the_fixture() -> None:
    payload = json.loads(
        (FIXTURES / "manifests" / "example-coefficient.json").read_text(encoding="utf-8")
    )
    source = ROOT / payload["source_file"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == payload["source_sha256"]
