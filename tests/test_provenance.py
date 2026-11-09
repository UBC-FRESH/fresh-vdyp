"""Tests for the provenance-manifest validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provenance import (
    REQUIRED_FIELDS,
    Diagnostic,
    ManifestError,
    main,
    require_valid,
    validate_manifest,
    validate_manifest_entry,
)

VALID: dict[str, object] = {
    "id": "vdyp-vtotreg4",
    "kind": "vdyp_coefficient_table",
    "source_model": "VDYP7",
    "source_version": "7",
    "source_file": "VDYP_CFG/coe/VTOTREG4.COE",
    "source_sha256": "a" * 64,
    "extracted_at_utc": "2026-11-09T00:00:00Z",
    "extractor": "fresh-vdyp 0.1.0",
    "parser_version": 1,
    "family": "whole_stem_volume",
    "control_sequence": "090",
    "columns": ["curve_group", "b0", "b1"],
    "row_count": 74,
    "units": {"b0": "log_m3"},
    "citation": "Province of British Columbia. VDYP7 coefficient bundle.",
    "notes": "",
}


def codes(entry: dict[str, object]) -> list[str]:
    return [finding.code for finding in validate_manifest_entry(entry)]


def test_a_complete_entry_is_valid() -> None:
    assert validate_manifest_entry(VALID) == ()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("id", "VTOTREG4", "INVALID-ID"),
        ("id", "vdyp-", "INVALID-ID"),
        ("kind", "VDYP", "INVALID-KIND"),
        ("source_sha256", "A" * 64, "INVALID-SHA256"),
        ("source_sha256", "abc", "INVALID-SHA256"),
        ("extracted_at_utc", "2026-11-09T00:00:00", "INVALID-TIMESTAMP"),
        ("extracted_at_utc", "2026-11-09T00:00:00+01:00", "INVALID-TIMESTAMP"),
        ("source_file", "/tmp/VDYP.CTR", "INVALID-SOURCE-FILE"),
        ("source_file", "coe\\VDYP.CTR", "INVALID-SOURCE-FILE"),
        ("source_file", "coe/../VDYP.CTR", "INVALID-SOURCE-FILE"),
        ("source_file", "C:/VDYP.CTR", "INVALID-SOURCE-FILE"),
        ("parser_version", 0, "INVALID-PARSER-VERSION"),
        ("parser_version", "1", "INVALID-PARSER-VERSION"),
        ("parser_version", True, "INVALID-PARSER-VERSION"),
        ("row_count", -1, "INVALID-ROW-COUNT"),
        ("row_count", "3", "INVALID-ROW-COUNT"),
        ("columns", [], "INVALID-COLUMNS"),
        ("columns", ["b0", "b0"], "INVALID-COLUMNS"),
        ("columns", [1, 2], "INVALID-COLUMNS"),
        ("units", [], "INVALID-UNITS"),
        ("units", {"b0": 1}, "INVALID-UNITS"),
    ],
)
def test_invalid_values_produce_stable_codes(field: str, value: object, code: str) -> None:
    entry = dict(VALID)
    entry[field] = value
    assert code in codes(entry)


@pytest.mark.parametrize("field", [*REQUIRED_FIELDS, "parser_version"])
def test_each_required_field_is_enforced(field: str) -> None:
    entry = {key: value for key, value in VALID.items() if key != field}
    findings = validate_manifest_entry(entry)
    assert [(item.code, item.field_name) for item in findings] == [("MISSING-FIELD", field)]


def test_unknown_fields_are_allowed() -> None:
    entry = dict(VALID)
    entry["future_field"] = "value"
    assert validate_manifest_entry(entry) == ()


def test_optional_fields_may_be_absent() -> None:
    entry = {
        key: value
        for key, value in VALID.items()
        if key not in {"family", "control_sequence", "columns", "row_count", "units", "notes"}
    }
    assert validate_manifest_entry(entry) == ()


def test_validate_manifest_prefixes_the_index() -> None:
    findings = validate_manifest([VALID, {**VALID, "id": "BAD"}])
    assert findings
    assert all(finding.field_name.startswith("[1].") for finding in findings)
    assert findings[0].code == "INVALID-ID"


def test_validate_manifest_accepts_one_object() -> None:
    assert validate_manifest(VALID) == ()


def test_validate_manifest_rejects_a_non_object_list_member() -> None:
    findings = validate_manifest([VALID, "bad"])
    assert [(item.code, item.field_name) for item in findings] == [("INVALID-PAYLOAD", "[1]")]


def test_validate_manifest_rejects_a_scalar() -> None:
    findings = validate_manifest("bad")
    assert [(item.code, item.field_name) for item in findings] == [("INVALID-PAYLOAD", "manifest")]


def test_require_valid_returns_none_for_a_valid_entry() -> None:
    require_valid(VALID)


def test_require_valid_raises_with_the_findings() -> None:
    entry = {key: value for key, value in VALID.items() if key != "citation"}
    with pytest.raises(ManifestError) as raised:
        require_valid(entry)
    assert raised.value.diagnostics[0].code == "MISSING-FIELD"


def test_diagnostic_renders_columns() -> None:
    rendered = Diagnostic("MISSING-FIELD", "id", "missing").render()
    assert "MISSING-FIELD" in rendered
    assert "id" in rendered
    assert "missing" in rendered


def test_main_accepts_a_valid_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps([VALID]), encoding="utf-8")
    assert main(["--manifest", str(path)]) == 0
    assert "0 finding(s)" in capsys.readouterr().out


def test_main_reports_an_invalid_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps([{**VALID, "id": "BAD"}]), encoding="utf-8")
    assert main(["--manifest", str(path)]) == 1
    output = capsys.readouterr().out
    assert "INVALID-ID" in output
    assert "1 finding(s)" in output


def test_main_reports_bad_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{", encoding="utf-8")
    assert main(["--manifest", str(path)]) == 2
    assert "error:" in capsys.readouterr().err


def test_main_reports_a_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--manifest", str(tmp_path / "absent.json")]) == 2
    assert "error:" in capsys.readouterr().err
