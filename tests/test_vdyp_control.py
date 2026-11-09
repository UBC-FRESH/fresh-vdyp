"""Tests for the VDYP7 control-file and column parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vdyp_control import (
    build_artifacts,
    config_from_environment,
    load_column_table,
    load_control_file,
    main,
    parse_column_line,
    parse_column_text,
    parse_control_text,
)

CONTROL_TEXT = (
    "  0    VDYP.CTR      input file for VDYP7.for        (Revision date 2009.03.18)\n"
    "  0    General Format is col 1-3   0 OR a parameter number\n"
    "\n"
    "001 00999999                                          Max # of Polygons to process (I8)\n"
    "009 coe\\becdef.dat                                    BEC Zone Definitions\n"
    "025                                                   Nullifies above siteCurve #\n"
    "090 coe\\VTOTREG4.coe                                  "
    "Total stand WholeStem Vol  RD_YVT1  IPSJF117\n"
)

COLUMN_TEXT = (
    "*COLUMNS\n"
    "'ID\tName\tUnits\tDecimals\tDescription\tWidth\tHeader ID\n"
    "0\tTable Num\t-\t0\tTable Number\t8\t0\n"
    "20  Pct Stk\t%\t0\tPcnt Stockable\t3\t10\n"
    "97\tCFS Bio stem\ttons/ha\t1\tCFS\tBio\tstem\t8\t17\n"
    "\n"
    "*HEADERS\n"
    "'ID\tDescription\n"
    "0\tTable Num|\n"
)


def test_control_text_counts_and_entries() -> None:
    parsed = parse_control_text(CONTROL_TEXT, source_file="VDYP_CFG/VDYP.CTR")
    assert parsed.source_file == "VDYP_CFG/VDYP.CTR"
    assert len(parsed.entries) == 4
    assert parsed.comment_lines == 2
    assert parsed.blank_lines == 1
    assert [entry.sequence for entry in parsed.entries] == ["001", "009", "025", "090"]


def test_control_entry_fields_keep_leading_zeros_and_slices() -> None:
    parsed = parse_control_text(CONTROL_TEXT, source_file="VDYP_CFG/VDYP.CTR")
    first = parsed.entries[0]
    assert first.sequence == "001"
    assert first.value == "00999999"
    assert first.description.startswith("Max # of Polygons")
    assert first.line_number == 4
    assert first.codes == ()


def test_control_entry_without_a_value_is_preserved() -> None:
    parsed = parse_control_text(CONTROL_TEXT, source_file="VDYP_CFG/VDYP.CTR")
    nullify = parsed.entries[2]
    assert nullify.sequence == "025"
    assert nullify.value == ""


def test_control_codes_are_uppercased() -> None:
    parsed = parse_control_text(CONTROL_TEXT, source_file="VDYP_CFG/VDYP.CTR")
    assert parsed.entries[3].codes == ("RD_YVT1", "IPSJF117")


def test_control_rejects_a_malformed_sequence() -> None:
    with pytest.raises(ValueError, match="invalid sequence"):
        parse_control_text("A01 value\n", source_file="VDYP_CFG/VDYP.CTR")


def test_control_serialization_is_stable() -> None:
    parsed = parse_control_text(CONTROL_TEXT, source_file="VDYP_CFG/VDYP.CTR")
    payload = parsed.to_dict()
    assert payload["entry_count"] == 4
    assert isinstance(payload["entries"], list)


def test_load_control_file_defaults_the_source_label(tmp_path: Path) -> None:
    path = tmp_path / "VDYP.CTR"
    path.write_text(CONTROL_TEXT, encoding="ascii")
    parsed = load_control_file(path)
    assert parsed.source_file == "VDYP.CTR"


def test_column_text_parses_the_quirks() -> None:
    parsed = parse_column_text(COLUMN_TEXT, source_file="VDYP_CFG/VDYP.tcl")
    assert parsed.source_file == "VDYP_CFG/VDYP.tcl"
    assert len(parsed.columns) == 3
    first = parsed.columns[0]
    assert (first.id, first.name, first.units, first.decimals) == (0, "Table Num", "-", 0)
    assert (first.description, first.width, first.header_id, first.line_number) == (
        "Table Number",
        8,
        0,
        3,
    )


def test_column_text_repairs_the_row_20_quirk() -> None:
    parsed = parse_column_text(COLUMN_TEXT, source_file="VDYP_CFG/VDYP.tcl")
    column = parsed.columns[1]
    assert column.id == 20
    assert column.name == "Pct Stk"
    assert column.description == "Pcnt Stockable"


def test_column_text_rejoins_embedded_description_tabs() -> None:
    parsed = parse_column_text(COLUMN_TEXT, source_file="VDYP_CFG/VDYP.tcl")
    column = parsed.columns[2]
    assert column.description == "CFS Bio stem"
    assert column.units == "tons/ha"
    assert column.header_id == 17


def test_column_text_requires_the_section() -> None:
    with pytest.raises(ValueError, match="no \\*COLUMNS"):
        parse_column_text("'ID\tName\n", source_file="VDYP_CFG/VDYP.tcl")


def test_column_text_rejects_duplicate_ids() -> None:
    text = (
        "*COLUMNS\n"
        "'ID\tName\tUnits\tDecimals\tDescription\tWidth\tHeader ID\n"
        "0\tA\t-\t0\tA\t1\t0\n"
        "0\tB\t-\t0\tB\t1\t0\n"
    )
    with pytest.raises(ValueError, match="duplicate column id"):
        parse_column_text(text, source_file="VDYP_CFG/VDYP.tcl")


def test_column_line_rejects_a_short_row() -> None:
    with pytest.raises(ValueError, match="fewer than 7 fields"):
        parse_column_line("0\tA\t-\t0", line_number=3, source_file="VDYP_CFG/VDYP.tcl")


def test_column_line_rejects_a_non_integer_field() -> None:
    with pytest.raises(ValueError, match="malformed column field"):
        parse_column_line(
            "0\tA\t-\tx\tA\t1\t0",
            line_number=3,
            source_file="VDYP_CFG/VDYP.tcl",
        )


def test_load_column_table_defaults_the_source_label(tmp_path: Path) -> None:
    path = tmp_path / "VDYP.tcl"
    path.write_text(COLUMN_TEXT, encoding="ascii")
    parsed = load_column_table(path)
    assert parsed.source_file == "VDYP.tcl"


def write_config(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "VDYP.CTR").write_text(CONTROL_TEXT, encoding="ascii")
    (root / "VDYPBACK.CTR").write_text(CONTROL_TEXT, encoding="ascii")
    (root / "VDYP.tcl").write_text(COLUMN_TEXT, encoding="ascii")


def test_build_artifacts_writes_three_files(tmp_path: Path) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    output = tmp_path / "out"
    counts = build_artifacts(config, output)
    assert counts == {"vdyp-ctr.json": 4, "vdypback-ctr.json": 4, "vdyp-columns.json": 3}
    payload = json.loads((output / "vdyp-ctr.json").read_text(encoding="utf-8"))
    assert payload["source_file"] == "VDYP_CFG/VDYP.CTR"
    assert payload["entry_count"] == 4


def test_main_writes_artifacts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    output = tmp_path / "out"
    assert main(["--config-dir", str(config), "--output-dir", str(output)]) == 0
    assert (output / "vdyp-columns.json").is_file()
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    output = tmp_path / "out"
    assert main(["--output-dir", str(output)]) == 0
    assert config_from_environment() == config
    capsys.readouterr()


def test_main_without_a_config_dir_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    assert main(["--output-dir", str(tmp_path / "out")]) == 2
    assert "VDYP_CFG_DIR" in capsys.readouterr().err


def test_main_with_a_missing_source_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "empty"
    config.mkdir()
    assert main(["--config-dir", str(config), "--output-dir", str(tmp_path / "out")]) == 2
    assert "error:" in capsys.readouterr().err
