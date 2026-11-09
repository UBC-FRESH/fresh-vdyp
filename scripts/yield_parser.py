#!/usr/bin/env python3
"""Parse ``csvyieldtable`` output into typed curve rows.

The parser loads the tracked 101-column schema from
``notes/reference/vdyp-columns.json``, maps the CSV header by normalized name,
and coerces numeric cells. Unknown columns, missing required columns, and ragged
rows fail explicitly. Blank cells stay ``None``; nothing is interpolated.

Command-line usage::

    python scripts/yield_parser.py --csv path/to/output.csv --summary
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_SCHEMA: Final[Path] = Path("notes/reference/vdyp-columns.json")
REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("year", "age", "vol ws")
NORMALIZE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")
INTEGER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[-+]?\d+$")
NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?$"
)

CellValue = int | float | str | None


@dataclass(frozen=True)
class YieldColumn:
    """One column from the VDYP yield-table schema.

    Attributes
    ----------
    id : int
        Column identifier.
    name : str
        Column name from ``VDYP.tcl``.
    units : str
        Unit label, empty when the source has none.
    decimals : int
        Displayed decimals.
    description : str
        Long description.
    """

    id: int
    name: str
    units: str
    decimals: int
    description: str


@dataclass(frozen=True)
class YieldRow:
    """One parsed yield-table row.

    Attributes
    ----------
    line_number : int
        One-based line number in the CSV file.
    values : tuple of int or float or str or None
        Values aligned with the table columns.
    """

    line_number: int
    values: tuple[CellValue, ...]

    def to_dict(self, columns: Sequence[YieldColumn]) -> dict[str, object]:
        """Render the row as a JSON-ready mapping.

        Parameters
        ----------
        columns : sequence of YieldColumn
            Columns aligned with ``values``.

        Returns
        -------
        dict of str to object
            ``line_number`` plus one entry per column name.
        """
        payload: dict[str, object] = {"line_number": self.line_number}
        payload.update(zip((column.name for column in columns), self.values, strict=True))
        return payload


@dataclass(frozen=True)
class YieldTable:
    """One parsed yield-table CSV.

    Attributes
    ----------
    source_file : str
        Repository-relative source label.
    columns : tuple of YieldColumn
        Columns in CSV header order.
    rows : tuple of YieldRow
        Data rows.
    provenance : dict of str to object
        Runtime or run metadata attached by the caller.
    """

    source_file: str
    columns: tuple[YieldColumn, ...]
    rows: tuple[YieldRow, ...]
    provenance: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Render the table as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source, columns, row count, rows, and provenance.
        """
        return {
            "source_file": self.source_file,
            "columns": [
                {
                    "id": column.id,
                    "name": column.name,
                    "units": column.units,
                    "decimals": column.decimals,
                }
                for column in self.columns
            ],
            "row_count": len(self.rows),
            "provenance": self.provenance,
            "rows": [row.to_dict(self.columns) for row in self.rows],
        }


class YieldParseError(ValueError):
    """Raised when a yield CSV does not match the schema.

    Parameters
    ----------
    code : str
        Stable finding code.
    message : str
        Explanation of the mismatch.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def normalize_name(name: str) -> str:
    """Normalize a column name for matching.

    Parameters
    ----------
    name : str
        Header or schema name.

    Returns
    -------
    str
        Lowercase words joined by single spaces.
    """
    return NORMALIZE_PATTERN.sub(" ", name.strip().lower()).strip()


def load_schema(path: Path = DEFAULT_SCHEMA) -> tuple[YieldColumn, ...]:
    """Load the yield-table schema from a tracked JSON artifact.

    Parameters
    ----------
    path : Path, optional
        Schema artifact, by default ``notes/reference/vdyp-columns.json``.

    Returns
    -------
    tuple of YieldColumn
        Columns in schema order.

    Raises
    ------
    YieldParseError
        When the file has no columns or a malformed record.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise YieldParseError("SCHEMA-UNREADABLE", str(exc)) from exc
    raw_columns = payload.get("columns") if isinstance(payload, dict) else None
    if not isinstance(raw_columns, list) or not raw_columns:
        raise YieldParseError("SCHEMA-EMPTY", "schema has no columns")
    columns: list[YieldColumn] = []
    for item in raw_columns:
        if not isinstance(item, dict):
            raise YieldParseError("SCHEMA-MALFORMED", "schema column is not an object")
        try:
            columns.append(
                YieldColumn(
                    id=int(item["id"]),
                    name=str(item["name"]),
                    units=str(item.get("units", "")),
                    decimals=int(item["decimals"]),
                    description=str(item.get("description", "")),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise YieldParseError("SCHEMA-MALFORMED", str(exc)) from exc
    return tuple(columns)


def coerce_cell(cell: str) -> CellValue:
    """Convert one CSV cell to a typed value.

    Parameters
    ----------
    cell : str
        Raw cell text.

    Returns
    -------
    int or float or str or None
        ``None`` for a blank cell, an integer or float for a numeric cell, and
        the stripped text otherwise.
    """
    text = cell.strip()
    if not text:
        return None
    if INTEGER_PATTERN.fullmatch(text) is not None:
        return int(text)
    if NUMBER_PATTERN.fullmatch(text) is not None:
        return float(text)
    return text


def parse_yield_text(
    text: str,
    *,
    source_file: str,
    schema: Sequence[YieldColumn],
    provenance: Mapping[str, object] | None = None,
    required: Sequence[str] = REQUIRED_COLUMNS,
) -> YieldTable:
    """Parse yield-table CSV text.

    Parameters
    ----------
    text : str
        CSV text, with LF or CRLF line endings.
    source_file : str
        Repository-relative source label.
    schema : sequence of YieldColumn
        Known columns.
    provenance : mapping of str to object or None, optional
        Runtime or run metadata to attach.
    required : sequence of str, optional
        Required normalized column names.

    Returns
    -------
    YieldTable
        Parsed rows with the header-order columns.

    Raises
    ------
    YieldParseError
        On an unknown or duplicate header, a missing required column, no data
        rows, or a ragged row.
    """
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise YieldParseError("EMPTY", "CSV has no header")
    header = [normalize_name(name) for name in rows[0]]
    if len(set(header)) != len(header):
        raise YieldParseError("DUPLICATE-COLUMN", "CSV header has duplicate names")
    schema_by_name = {normalize_name(column.name): column for column in schema}
    unknown = [name for name in header if name not in schema_by_name]
    if unknown:
        raise YieldParseError("UNKNOWN-COLUMN", f"unknown columns: {', '.join(unknown)}")
    missing = [name for name in required if name not in header]
    if missing:
        raise YieldParseError("MISSING-COLUMN", f"missing columns: {', '.join(missing)}")
    columns = tuple(schema_by_name[name] for name in header)
    data: list[YieldRow] = []
    for line_number, raw in enumerate(rows[1:], start=2):
        if not raw:
            continue
        if len(raw) != len(columns):
            raise YieldParseError(
                "RAGGED-ROW",
                f"line {line_number}: expected {len(columns)} fields, found {len(raw)}",
            )
        data.append(YieldRow(line_number, tuple(coerce_cell(cell) for cell in raw)))
    if not data:
        raise YieldParseError("NO-ROWS", "CSV has no data rows")
    metadata = dict(provenance) if provenance is not None else {}
    return YieldTable(source_file, columns, tuple(data), metadata)


def parse_yield_csv(
    path: Path,
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    source_file: str | None = None,
    provenance: Mapping[str, object] | None = None,
) -> YieldTable:
    """Read and parse one yield-table CSV file.

    Parameters
    ----------
    path : Path
        CSV file.
    schema_path : Path, optional
        Schema artifact.
    source_file : str or None, optional
        Repository-relative label. Defaults to the file name.
    provenance : mapping of str to object or None, optional
        Runtime or run metadata.

    Returns
    -------
    YieldTable
        Parsed table.
    """
    return parse_yield_text(
        path.read_text(encoding="utf-8-sig"),
        source_file=source_file or path.name,
        schema=load_schema(schema_path),
        provenance=provenance,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse a yield CSV from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` on success, ``1`` on a parse error, and ``2`` on an unreadable
        file.
    """
    parser = argparse.ArgumentParser(description="Parse VDYP7 csvyieldtable output.")
    parser.add_argument("--csv", type=Path, required=True, help="CSV output file")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="column schema")
    parser.add_argument("--json", type=Path, help="also write the parsed table")
    parser.add_argument("--summary", action="store_true", help="print only the summary")
    args = parser.parse_args(argv)
    try:
        table = parse_yield_csv(args.csv, schema_path=args.schema)
    except YieldParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"source: {table.source_file}")
    print(f"columns: {len(table.columns)}")
    print(f"rows: {len(table.rows)}")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(table.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
