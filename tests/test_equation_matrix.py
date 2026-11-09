"""Tests for the family-by-family equation validation matrix."""

from __future__ import annotations

import json
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
MATRIX: Path = ROOT / "notes" / "reference" / "vdyp-equation-matrix.json"
STATUSES = {"validated", "experimental", "not_implemented"}


def matrix() -> dict[str, object]:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_matrix_states_it_is_not_full_parity() -> None:
    payload = matrix()
    note = str(payload["note"]).lower()
    assert "not full" in note


def test_every_row_has_a_known_status_and_evidence() -> None:
    rows = matrix()["families"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        assert row["status"] in STATUSES
        evidence = ROOT / str(row["evidence"])
        assert evidence.is_file(), row["family"]


def test_validated_rows_have_a_tolerance_and_error() -> None:
    rows = matrix()["families"]
    assert isinstance(rows, list)
    validated = [row for row in rows if row["status"] == "validated"]
    assert validated
    for row in validated:
        assert float(str(row["error"])) <= float(str(row["tolerance"]))


def test_vtotreg4_is_the_validated_family() -> None:
    rows = matrix()["families"]
    assert isinstance(rows, list)
    validated = {row["family"] for row in rows if row["status"] == "validated"}
    assert validated == {"VTOTREG4"}


def test_unimplemented_rows_state_a_reason() -> None:
    rows = matrix()["families"]
    assert isinstance(rows, list)
    for row in rows:
        if row["status"] != "validated":
            assert str(row["reason"]).strip()
