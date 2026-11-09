"""Tests for the VDYP7 coefficient key catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coe_parser import parse_coe_text
from key_inference import (
    LookupSets,
    build_catalog,
    config_from_environment,
    keys_for_row,
    load_lookup_sets,
    main,
)

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE: Path = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
SPECIES = frozenset({"AC", "AT", "B", "C", "D", "E", "F", "H", "L", "MB"})
BEC = frozenset({"AT", "BWBS", "CDF", "CWH", "ESSF", "ICH", "IDF", "MH", "MS", "PP"})


def lookups() -> LookupSets:
    return LookupSets(species=SPECIES, bec=BEC)


def test_vtotreg4_group_is_a_key() -> None:
    table = parse_coe_text(
        "  1 " + " ".join(["0.1"] * 9) + "\n",
        source_file="VDYP_CFG/coe/VTOTREG4.COE",
        family="vtotreg4",
    )
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "mapped"
    assert [(key.name, key.value) for key in result.keys] == [("group", 1)]


def test_reghl_species_pair_and_coastal_indicator() -> None:
    table = parse_coe_text(
        "AC AT C 1 0.86323 1.00505\n", source_file="VDYP_CFG/coe/REGHL.COE", family="reghl"
    )
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "mapped"
    assert [(key.name, key.value) for key in result.keys] == [
        ("species", "AC"),
        ("species_2", "AT"),
        ("coastal_interior", "C"),
        ("curve", 1),
    ]


def test_unknown_species_marks_the_row_invalid() -> None:
    table = parse_coe_text(
        "ZZ AT C 1 0.86323 1.00505\n", source_file="VDYP_CFG/coe/REGHL.COE", family="reghl"
    )
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "invalid"
    assert "not in SP0.DAT" in result.reason


def test_increment_bec_label_and_flag_are_keys() -> None:
    line = " ".join(["AT", "A0", "1", *(["0.5"] * 16)])
    table = parse_coe_text(line + "\n", source_file="VDYP_CFG/coe/GROWBA27.COE", family="growba27")
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "mapped"
    assert [(key.name, key.value) for key in result.keys] == [
        ("bec", "AT"),
        ("label", "A0"),
        ("flag", 1),
    ]


def test_unknown_bec_marks_the_row_invalid() -> None:
    line = " ".join(["ZZ", "A0", "1", *(["0.5"] * 16)])
    table = parse_coe_text(line + "\n", source_file="VDYP_CFG/coe/GROWBA27.COE", family="growba27")
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "invalid"
    assert "not in BEC0.DAT" in result.reason


def test_bec_alias_bg_is_accepted() -> None:
    line = " ".join(["BG", "A0", "1", *(["0.5"] * 16)])
    table = parse_coe_text(line + "\n", source_file="VDYP_CFG/coe/GROWBA27.COE", family="growba27")
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "mapped"
    assert ("bec", "BG") in [(key.name, key.value) for key in result.keys]


def test_numeric_species_is_an_index() -> None:
    table = parse_coe_text(
        "1 2 0.1 0.2 0.3 0.4\n", source_file="VDYP_CFG/coe/REGVU.COE", family="regvu"
    )
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "mapped"
    assert [(key.name, key.value) for key in result.keys] == [
        ("group", 1),
        ("species_index", 2),
    ]


def test_a_family_with_no_key_columns_is_unmapped() -> None:
    table = parse_coe_text(
        " ".join(["0.1"] * 10) + "\n", source_file="VDYP_CFG/coe/GB01.COE", family="gb01"
    )
    result = keys_for_row(table, table.rows[0], lookups())
    assert result.status == "unmapped"
    assert "no key columns" in result.reason


def test_load_lookup_sets_reads_the_files(tmp_path: Path) -> None:
    (tmp_path / "SP0.DAT").write_text("AC\nAT\n", encoding="ascii")
    (tmp_path / "BEC0.DAT").write_text("AT\nESSF\n", encoding="ascii")
    sets = load_lookup_sets(tmp_path)
    assert sets.species == frozenset({"AC", "AT"})
    assert sets.bec == frozenset({"AT", "ESSF"})


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (config / "VDYP.CTR").write_text(
        "\n".join(
            [
                control_line("090", "coe\\VTOTREG4.coe", "Whole stem"),
                control_line("121", "coe\\GROWBA27.coe", "BA growth"),
                control_line("061", "coe\\COMPLIM.coe", "Species limits"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (coe / "SP0.DAT").write_text("\n".join(sorted(SPECIES)) + "\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("\n".join(sorted(BEC)) + "\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    line = " ".join(["AT", "A0", "1", *(["0.5"] * 16)])
    (coe / "GROWBA27.COE").write_text(line + "\n", encoding="ascii")
    (coe / "COMPLIM.COE").write_text("AC C 49.4 153.3\n", encoding="ascii")
    return config


def test_build_catalog_joins_sequences_and_statuses(tmp_path: Path) -> None:
    config = write_config(tmp_path / "install")
    catalog = build_catalog(config)
    payload = catalog.to_dict()
    assert payload["family_count"] == 3
    family_items = payload["families"]
    assert isinstance(family_items, list)
    families = {item["family"]: item for item in family_items}
    assert families["vtotreg4"]["control_sequences"] == ["090"]
    assert families["vtotreg4"]["status"] == "mapped"
    assert families["growba27"]["control_sequences"] == ["121"]
    assert families["complim"]["status"] == "unsupported"
    assert payload["status_counts"] == {"mapped": 2, "unsupported": 1}


def test_build_catalog_requires_a_coe_directory(tmp_path: Path) -> None:
    config = tmp_path / "VDYP_CFG"
    config.mkdir()
    with pytest.raises(NotADirectoryError):
        build_catalog(config)


def test_main_writes_the_catalog(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = write_config(tmp_path / "install")
    output = tmp_path / "out" / "catalog.json"
    assert main(["--config-dir", str(config), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["family_count"] == 3
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_config(tmp_path / "install")
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    output = tmp_path / "catalog.json"
    assert main(["--output", str(output)]) == 0
    assert config_from_environment() == config
    capsys.readouterr()


def test_main_without_a_directory_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    assert main(["--output", str(tmp_path / "catalog.json")]) == 2
    assert "VDYP_CFG_DIR" in capsys.readouterr().err


def test_main_with_a_missing_directory_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["--config-dir", str(tmp_path / "absent"), "--output", str(tmp_path / "c.json")]) == 2
    )
    assert "error:" in capsys.readouterr().err
