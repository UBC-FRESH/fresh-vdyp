"""Tests for the csvyieldtable parser."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from yield_parser import (
    REQUIRED_COLUMNS,
    YieldColumn,
    coerce_cell,
    load_alias_config,
    load_schema,
    main,
    normalize_name,
    parse_yield_csv,
    parse_yield_text,
)

ROOT: Path = Path(__file__).resolve().parents[1]
SCHEMA: Path = ROOT / "notes" / "reference" / "vdyp-columns.json"


def columns_for(*names: str) -> tuple[YieldColumn, ...]:
    schema = load_schema(SCHEMA)
    by_name = {column.name: column for column in schema}
    return tuple(by_name[name] for name in names)


def test_schema_loads_101_columns() -> None:
    schema = load_schema(SCHEMA)
    assert len(schema) == 101
    assert schema[0].name == "Table Num"
    assert schema[7].units == "yr"


def test_normalize_name_collapses_punctuation() -> None:
    assert normalize_name(" Spcs 1 Vol ws ") == "spcs 1 vol ws"
    assert normalize_name("Vol_ws") == "vol ws"


@pytest.mark.parametrize(
    ("cell", "value"),
    [
        ("", None),
        ("  ", None),
        ("12", 12),
        ("-3", -3),
        ("12.5", 12.5),
        ("1e-3", 0.001),
        ("AT", "AT"),
    ],
)
def test_coerce_cell(cell: str, value: object) -> None:
    assert coerce_cell(cell) == value


def test_parse_text_maps_header_order_and_types() -> None:
    columns = columns_for("Year", "Age", "Vol ws", "Vol cu", "Spcs 1 Cd")
    text = "Year,Age,Vol ws,Vol cu,Spcs 1 Cd\n2001,50,100.5,90.2,AT\n2002,51,,91.0,B\n"
    table = parse_yield_text(
        text,
        source_file="ConsoleOutput.csv",
        schema=columns,
        provenance={"mode": "wine"},
    )
    assert [column.name for column in table.columns] == [
        "Year",
        "Age",
        "Vol ws",
        "Vol cu",
        "Spcs 1 Cd",
    ]
    assert len(table.rows) == 2
    assert table.rows[0].values == (2001, 50, 100.5, 90.2, "AT")
    assert table.rows[1].values == (2002, 51, None, 91.0, "B")
    assert table.provenance == {"mode": "wine"}
    assert table.columns[2].units == "m3/ha"


def test_required_columns_are_documented() -> None:
    assert REQUIRED_COLUMNS == ("year", "age", "vol ws")


def test_unknown_column_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="UNKNOWN-COLUMN"):
        parse_yield_text(
            "Year,Age,Vol ws,Nope\n2001,50,1,2\n",
            source_file="x.csv",
            schema=columns,
        )


def test_missing_required_column_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="MISSING-COLUMN"):
        parse_yield_text("Year,Age\n2001,50\n", source_file="x.csv", schema=columns)


def test_duplicate_header_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="DUPLICATE-COLUMN"):
        parse_yield_text(
            "Year,Age,Vol ws,Vol ws\n2001,50,1,2\n", source_file="x.csv", schema=columns
        )


def test_ragged_row_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="RAGGED-ROW"):
        parse_yield_text("Year,Age,Vol ws\n2001,50\n", source_file="x.csv", schema=columns)


def test_no_rows_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="NO-ROWS"):
        parse_yield_text("Year,Age,Vol ws\n", source_file="x.csv", schema=columns)


def test_parse_csv_file_with_the_tracked_schema(tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    path.write_text("Year,Age,Vol ws\n2001,50,100.5\n", encoding="utf-8")
    table = parse_yield_csv(path, schema_path=SCHEMA, source_file="ConsoleOutput.csv")
    assert table.source_file == "ConsoleOutput.csv"
    assert table.rows[0].values == (2001, 50, 100.5)


def test_to_dict_contains_columns_and_rows() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    table = parse_yield_text(
        "Year,Age,Vol ws\n2001,50,100.5\n", source_file="x.csv", schema=columns
    )
    payload = table.to_dict()
    assert payload["row_count"] == 1
    column_payload = payload["columns"]
    assert isinstance(column_payload, list)
    assert column_payload[0]["name"] == "Year"
    rows = payload["rows"]
    assert isinstance(rows, list)
    assert rows[0]["Year"] == 2001


def test_cli_writes_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "out.csv"
    path.write_text("Year,Age,Vol ws\n2001,50,100.5\n", encoding="utf-8")
    output = tmp_path / "table.json"
    assert main(["--csv", str(path), "--schema", str(SCHEMA), "--json", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["row_count"] == 1
    assert "rows: 1" in capsys.readouterr().out


def test_cli_reports_a_parse_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "out.csv"
    path.write_text("Year,Age\n2001,50\n", encoding="utf-8")
    assert main(["--csv", str(path), "--schema", str(SCHEMA)]) == 1
    assert "MISSING-COLUMN" in capsys.readouterr().err


def test_schema_unreadable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SCHEMA-UNREADABLE"):
        load_schema(tmp_path / "absent.json")


def test_schema_empty(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text('{"columns": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="SCHEMA-EMPTY"):
        load_schema(path)


def test_schema_column_is_not_an_object(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text('{"columns": [1]}', encoding="utf-8")
    with pytest.raises(ValueError, match="SCHEMA-MALFORMED"):
        load_schema(path)


def test_schema_column_is_malformed(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text('{"columns": [{"id": "x", "name": "Year", "decimals": 0}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="SCHEMA-MALFORMED"):
        load_schema(path)


def test_empty_csv_text_fails() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    with pytest.raises(ValueError, match="EMPTY"):
        parse_yield_text("", source_file="x.csv", schema=columns)


def test_blank_csv_line_is_skipped() -> None:
    columns = columns_for("Year", "Age", "Vol ws")
    table = parse_yield_text("Year,Age,Vol ws\n\n2001,50,1\n", source_file="x.csv", schema=columns)
    assert len(table.rows) == 1


def test_cli_without_json_succeeds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "out.csv"
    path.write_text("Year,Age,Vol ws\n2001,50,100.5\n", encoding="utf-8")
    assert main(["--csv", str(path), "--schema", str(SCHEMA)]) == 0
    assert "rows: 1" in capsys.readouterr().out


GOLDEN: Path = ROOT / "fixtures" / "yield-output" / "golden-sample.csv"
GOLDEN_METADATA: Path = ROOT / "fixtures" / "yield-output" / "metadata.json"
ALIASES: Path = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"


def test_alias_config_loads() -> None:
    aliases, extra = load_alias_config(ALIASES)
    assert aliases["TABLE_NUM"] == "Table Num"
    assert "PRJ_VOL_WS" in aliases
    assert extra == ("DISTRICT", "PRJ_MODE")


def test_alias_config_unreadable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ALIAS-UNREADABLE"):
        load_alias_config(tmp_path / "absent.json")


def test_golden_sample_parses_with_aliases() -> None:
    table = parse_yield_csv(GOLDEN, schema_path=SCHEMA, alias_path=ALIASES)
    assert len(table.rows) == 10
    names = [column.name for column in table.columns]
    assert "Year" in names
    assert "Age" in names
    assert "Vol ws" in names
    assert "DISTRICT" not in names
    assert "PRJ_MODE" not in names
    first = dict(zip(names, table.rows[0].values, strict=True))
    assert first["Year"] == 2000
    assert first["Age"] == 0
    assert first["Spcs 1 Cd"] == "AT"
    assert table.columns[names.index("Vol ws")].units == "m3/ha"


def test_golden_metadata_matches_the_subset() -> None:
    metadata = json.loads(GOLDEN_METADATA.read_text(encoding="utf-8"))
    assert metadata["full_row_count"] == 301
    assert metadata["subset_row_count"] == 10
    assert len(metadata["full_output_sha256"]) == 64
    assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest() == metadata["subset_sha256"]
