"""Tests for the bounded assistant tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from assistant_tools import (
    TOOL_SPECS,
    AssistantAnswer,
    AssistantAnswerError,
    catalog_search,
    curve_query,
    provenance_lookup,
    validate_answer,
    validation_status,
)
from curve_api import CurveQuery, CurveService, load_service

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
GOLDEN = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA = ROOT / "fixtures" / "yield-output" / "metadata.json"
SCHEMA = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"
MATRIX = ROOT / "notes" / "reference" / "vdyp-equation-matrix.json"


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


def service() -> CurveService:
    return load_service(GOLDEN, METADATA, schema_path=SCHEMA, alias_path=ALIASES)


def test_tool_specs_are_bounded() -> None:
    names = {spec.name for spec in TOOL_SPECS}
    assert names == {"catalog_search", "curve_query", "provenance_lookup", "validation_status"}


def test_catalog_search_is_source_backed(tmp_path: Path) -> None:
    answer = catalog_search(write_config(tmp_path / "install"), "VTOTREG4")
    assert "1 families" in answer.text
    assert answer.sources
    assert answer.data["families"]


def test_catalog_search_no_match_still_has_a_source(tmp_path: Path) -> None:
    answer = catalog_search(write_config(tmp_path / "install"), "does-not-exist")
    assert answer.sources == ("VDYP_CFG",)


def test_curve_query_is_source_backed() -> None:
    answer = curve_query(service(), CurveQuery(age_start=100, age_end=100))
    assert "ok: 1 points" in answer.text
    assert answer.sources[0] == "golden-full.csv"
    assert answer.sources[1] == "Wine 11.0"


def test_provenance_lookup() -> None:
    answer = provenance_lookup(service())
    assert answer.sources
    assert answer.data["console_version"] == "7.16k"


def test_validation_status_known_and_unknown() -> None:
    known = validation_status(MATRIX, "VTOTREG4")
    assert "validated" in known.text
    unknown = validation_status(MATRIX, "NOPE")
    assert "not_implemented" in unknown.text


def test_validate_answer_rejects_an_empty_source() -> None:
    with pytest.raises(AssistantAnswerError):
        validate_answer(AssistantAnswer("text", ()))


def test_validate_answer_rejects_a_blank_source() -> None:
    with pytest.raises(AssistantAnswerError):
        validate_answer(AssistantAnswer("text", ("  ",)))
