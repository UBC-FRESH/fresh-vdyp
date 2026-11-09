"""Tests for the VDYP7 control, PRM, and DAT structural parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config_parser import (
    ConfigParseError,
    build_summary,
    coefficient_dir_ok,
    main,
    parse_dat_file,
    parse_dat_text,
    parse_prm_file,
    parse_prm_text,
)


def test_dat_lookup_is_detected() -> None:
    table = parse_dat_text("AT\nBWBS\nESSF\n", source_file="VDYP_CFG/coe/BEC0.DAT")
    assert table.format == "lookup"
    assert [record.tokens for record in table.records] == [("AT",), ("BWBS",), ("ESSF",)]


def test_dat_table_is_detected() -> None:
    table = parse_dat_text("AC AT 2\nAC BG 2\n", source_file="VDYP_CFG/coe/BGRP.DAT")
    assert table.format == "table"
    assert table.records[0].tokens == ("AC", "AT", "2")


def test_dat_counts_comments_and_blanks() -> None:
    table = parse_dat_text("# comment\n\nAT\n", source_file="VDYP_CFG/coe/BEC0.DAT")
    assert table.comment_lines == 1
    assert table.blank_lines == 1
    assert table.records[0].line_number == 3


def test_dat_lookup_hint_rejects_a_wide_row() -> None:
    with pytest.raises(ConfigParseError, match="expected one token"):
        parse_dat_text(
            "AT\nAC AT 2\n",
            source_file="VDYP_CFG/coe/BEC0.DAT",
            format_hint="lookup",
        )


def test_dat_with_only_comments_is_empty() -> None:
    table = parse_dat_text("# nothing\n", source_file="VDYP_CFG/coe/BEC0.DAT")
    assert table.format == "empty"
    assert table.records == ()


def test_prm_keyed_rows_keep_the_key_and_tokens() -> None:
    table = parse_prm_text(
        "01  0.98  Small utl class\n02  0.98\n", source_file="VDYP_CFG/coe/CVADJ.PRM"
    )
    assert len(table.records) == 2
    assert table.records[0].key == "01"
    assert table.records[0].tokens == ("0.98", "Small", "utl", "class")


def test_prm_comment_only_is_valid() -> None:
    table = parse_prm_text("## comment\n", source_file="VDYP_CFG/coe/SIEQN.PRM")
    assert table.records == ()
    assert table.comment_lines == 1


def test_prm_preserves_single_token_rows() -> None:
    table = parse_prm_text("000\n098 1 1\n", source_file="VDYP_CFG/coe/mod19813.prm")
    assert [record.key for record in table.records] == ["000", "098"]


def test_file_wrappers_use_the_default_label(tmp_path: Path) -> None:
    dat = tmp_path / "BEC0.DAT"
    dat.write_text("AT\n", encoding="ascii")
    prm = tmp_path / "CVADJ.PRM"
    prm.write_text("01 0.98\n", encoding="ascii")
    assert parse_dat_file(dat).source_file == "VDYP_CFG/coe/BEC0.DAT"
    assert parse_prm_file(prm).records[0].key == "01"


def write_config(root: Path) -> None:
    coe = root / "coe"
    coe.mkdir(parents=True)
    (root / "VDYP.CTR").write_text(
        "001 00999999                                          Max polygons\n",
        encoding="ascii",
    )
    (coe / "SIEQN.PRM").write_text("## comment\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nBWBS\n", encoding="ascii")


def test_build_summary_covers_all_three_kinds(tmp_path: Path) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    summary = build_summary(config)
    payload = summary.to_dict()
    assert payload["file_count"] == 3
    files = payload["files"]
    assert isinstance(files, list)
    kinds = {item["kind"] for item in files}
    assert kinds == {"control", "parameter", "data"}


def test_build_summary_requires_a_coe_directory(tmp_path: Path) -> None:
    config = tmp_path / "VDYP_CFG"
    config.mkdir()
    with pytest.raises(NotADirectoryError):
        build_summary(config)


def test_coefficient_dir_ok(tmp_path: Path) -> None:
    assert not coefficient_dir_ok(tmp_path)
    (tmp_path / "coe").mkdir()
    assert coefficient_dir_ok(tmp_path)


def test_main_writes_the_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    output = tmp_path / "out" / "summary.json"
    assert main(["--config-dir", str(config), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["file_count"] == 3
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "VDYP_CFG"
    write_config(config)
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    output = tmp_path / "summary.json"
    assert main(["--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["file_count"] == 3
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
    assert (
        main(["--config-dir", str(tmp_path / "absent"), "--output", str(tmp_path / "s.json")]) == 2
    )
    assert "error:" in capsys.readouterr().err
