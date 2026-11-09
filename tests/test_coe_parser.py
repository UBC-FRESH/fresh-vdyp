"""Tests for the VDYP7 .COE family parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coe_parser import (
    CoeParseError,
    ColumnKind,
    UnsupportedFamilyError,
    build_summary,
    coerce_value,
    main,
    parse_coe_file,
    parse_coe_text,
    schema_for,
    tokenize_row,
)

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"


def test_tokenizer_splits_concatenated_numbers() -> None:
    line = "  4 -11.12631   1.93159   1.27268 -0.001400   0.00000  0.000000-0.0000285"
    tokens = tokenize_row(line)
    assert tokens == (
        "4",
        "-11.12631",
        "1.93159",
        "1.27268",
        "-0.001400",
        "0.00000",
        "0.000000",
        "-0.0000285",
    )


def test_tokenizer_keeps_labels_and_scientific_notation() -> None:
    assert tokenize_row("AT   A0 1  1.5E-3") == ("AT", "A0", "1", "1.5E-3")
    assert tokenize_row("AC AT C 1   0.86323   1.00505") == (
        "AC",
        "AT",
        "C",
        "1",
        "0.86323",
        "1.00505",
    )


@pytest.mark.parametrize(
    ("token", "kind", "expected"),
    [
        ("1", "number", 1),
        ("-10.5", "number", -10.5),
        ("1.5E-3", "number", 0.0015),
        ("A0", "text", "A0"),
    ],
)
def test_coerce_value(token: str, kind: ColumnKind, expected: object) -> None:
    assert coerce_value(token, kind) == expected


def test_coerce_rejects_a_text_token_in_a_number_column() -> None:
    with pytest.raises(ValueError, match="expected a number"):
        coerce_value("AC", "number")


def test_coerce_rejects_a_numeric_token_in_a_text_column() -> None:
    with pytest.raises(ValueError, match="expected a text"):
        coerce_value("1", "text")


def test_schema_for_returns_a_registered_family() -> None:
    schema = schema_for("VTOTREG4")
    assert schema.family == "vtotreg4"
    assert schema.columns[0] == "group"
    assert len(schema.columns) == 10


@pytest.mark.parametrize("family", ["complim", "regdqi04", "not_a_family"])
def test_schema_for_rejects_unsupported_families(family: str) -> None:
    with pytest.raises(UnsupportedFamilyError):
        schema_for(family)


def test_parse_coe_file_reads_the_fixture() -> None:
    table = parse_coe_file(FIXTURE_COE)
    assert table.family == "vtotreg4"
    assert table.source_file == "VDYP_CFG/coe/VTOTREG4.COE"
    assert table.columns[0] == "group"
    assert len(table.rows) == 2
    assert table.rows[0].values[0] == 1
    assert table.rows[1].values[1] == pytest.approx(-10.41832)
    payload = table.to_dict()
    assert payload["row_count"] == 2
    assert isinstance(payload["rows"], list)


def test_parse_text_family_columns() -> None:
    table = parse_coe_text(
        "AC AT C 1   0.86323   1.00505\n",
        source_file="VDYP_CFG/coe/REGHL.COE",
        family="reghl",
    )
    assert table.columns == ("species", "bec", "coastal_interior", "curve", "c0", "c1")
    assert table.rows[0].values == ("AC", "AT", "C", 1, 0.86323, 1.00505)


def test_parse_flagged_family() -> None:
    table = parse_coe_text(
        "AC  0  -0.08787  0.016335   0.00907   DX\n",
        source_file="VDYP_CFG/coe/BASP06.COE",
        family="basp06",
    )
    assert table.rows[0].values == ("AC", 0, -0.08787, 0.016335, 0.00907, "DX")


def test_parse_increment_family() -> None:
    line = " ".join(["AT", "A0", "1", *(["0.5"] * 16)])
    table = parse_coe_text(line + "\n", source_file="VDYP_CFG/coe/YLDBA405.COE", family="yldba405")
    assert len(table.rows[0].values) == 19
    assert table.rows[0].values[:3] == ("AT", "A0", 1)


def test_parse_skips_comments_and_blanks() -> None:
    text = "# comment\n\n  1 " + " ".join(["0.1"] * 9) + "\n"
    table = parse_coe_text(text, source_file="VDYP_CFG/coe/VTOTREG4.COE", family="vtotreg4")
    assert len(table.rows) == 1
    assert table.rows[0].line_number == 3


def test_parse_rejects_the_wrong_token_count() -> None:
    with pytest.raises(CoeParseError, match="expected 10 tokens, found 2"):
        parse_coe_text("1 2\n", source_file="VDYP_CFG/coe/VTOTREG4.COE", family="vtotreg4")


def test_parse_rejects_a_text_token_in_a_number_position() -> None:
    text = " ".join(["AC", *["0.1"] * 9]) + "\n"
    with pytest.raises(CoeParseError, match="expected a number"):
        parse_coe_text(text, source_file="VDYP_CFG/coe/VTOTREG4.COE", family="vtotreg4")


def test_parse_rejects_an_empty_table() -> None:
    with pytest.raises(CoeParseError, match="no data rows"):
        parse_coe_text(
            "# only a comment\n", source_file="VDYP_CFG/coe/VTOTREG4.COE", family="vtotreg4"
        )


def test_build_summary_reports_parsed_and_unsupported(tmp_path: Path) -> None:
    (tmp_path / "vtotreg4.coe").write_bytes(FIXTURE_COE.read_bytes())
    (tmp_path / "regyhlp.coe").write_text(
        "AC C   1.00160   0.20508  -0.0013743\n", encoding="ascii"
    )
    (tmp_path / "complim.coe").write_text("AC C  49.4 153.3\n", encoding="ascii")
    summary = build_summary(tmp_path)
    payload = summary.to_dict()
    assert payload["family_count"] == 3
    assert payload["parsed_count"] == 2
    assert payload["unsupported_count"] == 1
    families = payload["families"]
    assert isinstance(families, list)
    unsupported = [
        item for item in families if isinstance(item, dict) and item["status"] == "unsupported"
    ]
    assert unsupported[0]["family"] == "complim"


def test_build_summary_rejects_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        build_summary(tmp_path / "absent")


def test_main_writes_the_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "vtotreg4.coe").write_bytes(FIXTURE_COE.read_bytes())
    output = tmp_path / "out" / "summary.json"
    assert main(["--coe-dir", str(tmp_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["parsed_count"] == 1
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "VDYP_CFG"
    config.mkdir()
    (config / "coe").mkdir()
    (config / "coe" / "vtotreg4.coe").write_bytes(FIXTURE_COE.read_bytes())
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    output = tmp_path / "summary.json"
    assert main(["--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["parsed_count"] == 1
    capsys.readouterr()


def test_main_without_a_directory_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    assert main(["--output", str(tmp_path / "summary.json")]) == 2
    assert "VDYP_CFG_DIR" in capsys.readouterr().err


def test_main_with_a_missing_directory_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--coe-dir", str(tmp_path / "absent"), "--output", str(tmp_path / "s.json")]) == 2
    assert "error:" in capsys.readouterr().err
