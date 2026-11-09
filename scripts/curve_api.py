#!/usr/bin/env python3
"""Typed curve query API over a parsed VDYP yield table.

The service turns :class:`yield_parser.YieldTable` rows into typed curve points,
supports inclusive year/age and species filters, and attaches provenance to every
result. A query with no matches is ``empty``; a table missing a required column
is ``unsupported``. Neither case invents a point.

Command-line usage::

    python scripts/curve_api.py --csv fixtures/yield-output/golden-full.csv \
        --metadata fixtures/yield-output/metadata.json --age-start 100 --age-end 100
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from yield_parser import (
    DEFAULT_ALIASES,
    DEFAULT_SCHEMA,
    YieldRow,
    YieldTable,
    parse_yield_csv,
)

ResultStatus = Literal["ok", "empty", "unsupported"]
YEAR_COLUMN: Final[str] = "Year"
AGE_COLUMN: Final[str] = "Age"
SPECIES_COLUMNS: Final[tuple[str, ...]] = tuple(f"Spcs {index} Cd" for index in range(1, 7))
REQUIRED_COLUMNS: Final[tuple[str, ...]] = (YEAR_COLUMN, AGE_COLUMN)
FIELD_COLUMNS: Final[dict[str, str]] = {
    "volume_ws": "Vol ws",
    "volume_cu": "Vol cu",
    "volume_d": "Vol d",
    "volume_dw": "Vol dw",
    "volume_dwb": "Vol dwb",
    "dom_height": "Dom Ht",
    "lorey_height": "Lorey Ht",
    "diameter": "Dia",
    "tph": "TPH",
    "ba": "BA",
    "site_index": "SI",
    "pct_stockable": "Pct Stk",
}


class CurveQueryError(ValueError):
    """Raised when a query range is invalid.

    Parameters
    ----------
    message : str
        Explanation of the invalid input.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class CurveQuery:
    """A curve query with inclusive bounds.

    Attributes
    ----------
    species : str or None
        Species code filter, case-insensitive.
    year_start : int or None
        First included projection year.
    year_end : int or None
        Last included projection year.
    age_start : int or None
        First included age.
    age_end : int or None
        Last included age.
    """

    species: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    age_start: int | None = None
    age_end: int | None = None

    def validate(self) -> None:
        """Validate the query bounds.

        Returns
        -------
        None
            The query is valid.

        Raises
        ------
        CurveQueryError
            When a range is reversed or the species filter is empty.
        """
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_start > self.year_end
        ):
            raise CurveQueryError("year_start must not exceed year_end")
        if (
            self.age_start is not None
            and self.age_end is not None
            and self.age_start > self.age_end
        ):
            raise CurveQueryError("age_start must not exceed age_end")
        if self.species is not None and not self.species.strip():
            raise CurveQueryError("species filter must not be empty")

    def to_dict(self) -> dict[str, object]:
        """Render the query as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The filter values.
        """
        return {
            "species": self.species,
            "year_start": self.year_start,
            "year_end": self.year_end,
            "age_start": self.age_start,
            "age_end": self.age_end,
        }


@dataclass(frozen=True)
class CurveProvenance:
    """Source and runtime metadata attached to every curve result.

    Attributes
    ----------
    source_file : str
        Source CSV label.
    runtime : str
        Runtime that produced the source, such as ``Wine 11.0``.
    console_version : str
        Console version, such as ``7.16k``.
    control_sequence : str
        Control sequence behind the curve, or an empty string.
    query : dict of str to object
        Query inputs.
    """

    source_file: str
    runtime: str
    console_version: str
    control_sequence: str
    query: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """Render the provenance as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source, runtime, console, control sequence, and query.
        """
        return {
            "source_file": self.source_file,
            "runtime": self.runtime,
            "console_version": self.console_version,
            "control_sequence": self.control_sequence,
            "query": self.query,
        }


@dataclass(frozen=True)
class CurvePoint:
    """One typed curve point.

    Attributes
    ----------
    year : int
        Projection year.
    age : int
        Total age.
    species : tuple of str
        Species codes present on the row.
    volume_ws : float or None
        Whole-stem volume.
    volume_cu : float or None
        Close-utilization volume.
    volume_d : float or None
        Volume net of decay.
    volume_dw : float or None
        Volume net of decay and waste.
    volume_dwb : float or None
        Volume net of decay, waste, and breakage.
    dom_height : float or None
        Dominant height.
    lorey_height : float or None
        Lorey height.
    diameter : float or None
        Quadratic mean diameter.
    tph : float or None
        Trees per hectare.
    ba : float or None
        Basal area.
    site_index : float or None
        Site index.
    pct_stockable : float or None
        Percent stockable.
    units : dict of str to str
        Units for each field.
    """

    year: int
    age: int
    species: tuple[str, ...]
    volume_ws: float | None
    volume_cu: float | None
    volume_d: float | None
    volume_dw: float | None
    volume_dwb: float | None
    dom_height: float | None
    lorey_height: float | None
    diameter: float | None
    tph: float | None
    ba: float | None
    site_index: float | None
    pct_stockable: float | None
    units: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        """Render the point as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The point fields, species list, and units.
        """
        return {
            "year": self.year,
            "age": self.age,
            "species": list(self.species),
            "volume_ws": self.volume_ws,
            "volume_cu": self.volume_cu,
            "volume_d": self.volume_d,
            "volume_dw": self.volume_dw,
            "volume_dwb": self.volume_dwb,
            "dom_height": self.dom_height,
            "lorey_height": self.lorey_height,
            "diameter": self.diameter,
            "tph": self.tph,
            "ba": self.ba,
            "site_index": self.site_index,
            "pct_stockable": self.pct_stockable,
            "units": self.units,
        }


@dataclass(frozen=True)
class CurveResult:
    """The result of one curve query.

    Attributes
    ----------
    status : {"ok", "empty", "unsupported"}
        Result status.
    reason : str
        Explanation for ``empty`` or ``unsupported``, empty for ``ok``.
    query : CurveQuery
        The query inputs.
    provenance : CurveProvenance
        Source and runtime metadata.
    points : tuple of CurvePoint
        Matching points in source order.
    """

    status: ResultStatus
    reason: str
    query: CurveQuery
    provenance: CurveProvenance
    points: tuple[CurvePoint, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the result as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Status, reason, query, provenance, point count, and points.
        """
        return {
            "status": self.status,
            "reason": self.reason,
            "query": self.query.to_dict(),
            "provenance": self.provenance.to_dict(),
            "point_count": len(self.points),
            "points": [point.to_dict() for point in self.points],
        }


def _value(row: YieldRow, columns: Sequence[str], name: str) -> object:
    """Read one cell from a row by column name.

    Parameters
    ----------
    row : YieldRow
        Row to read.
    columns : sequence of str
        Column names aligned with the row.
    name : str
        Column name.

    Returns
    -------
    object
        The cell value, or ``None`` when the column is absent.
    """
    try:
        index = list(columns).index(name)
    except ValueError:
        return None
    return row.values[index]


def _int_value(row: YieldRow, columns: Sequence[str], name: str) -> int | None:
    value = _value(row, columns, name)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _float_value(row: YieldRow, columns: Sequence[str], name: str) -> float | None:
    value = _value(row, columns, name)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


@dataclass(frozen=True)
class CurveService:
    """A curve service over one parsed yield table.

    Attributes
    ----------
    table : YieldTable
        Parsed yield table.
    runtime : str
        Runtime label.
    console_version : str
        Console version label.
    control_sequence : str
        Control sequence, or an empty string.
    """

    table: YieldTable
    runtime: str
    console_version: str
    control_sequence: str = ""

    def _columns(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.table.columns)

    def _units(self) -> dict[str, str]:
        by_name = {column.name: column.units for column in self.table.columns}
        return {
            field: by_name.get(column, "")
            for field, column in {**FIELD_COLUMNS, "year": YEAR_COLUMN, "age": AGE_COLUMN}.items()
        }

    def unsupported_reason(self) -> str:
        """Return why the table cannot answer a curve query.

        Returns
        -------
        str
            Empty when the table has the required columns, otherwise a reason.
        """
        columns = set(self._columns())
        missing = [name for name in REQUIRED_COLUMNS if name not in columns]
        if missing:
            return f"missing columns: {', '.join(missing)}"
        return ""

    def query(self, query: CurveQuery) -> CurveResult:
        """Run one query against the table.

        Parameters
        ----------
        query : CurveQuery
            Filters to apply.

        Returns
        -------
        CurveResult
            Matching points or an explicit empty/unsupported result.

        Raises
        ------
        CurveQueryError
            When the query bounds are invalid.
        """
        query.validate()
        provenance = CurveProvenance(
            source_file=self.table.source_file,
            runtime=self.runtime,
            console_version=self.console_version,
            control_sequence=self.control_sequence,
            query=query.to_dict(),
        )
        reason = self.unsupported_reason()
        if reason:
            return CurveResult("unsupported", reason, query, provenance, ())
        columns = self._columns()
        species_filter = query.species.strip().upper() if query.species is not None else None
        points: list[CurvePoint] = []
        for row in self.table.rows:
            year = _int_value(row, columns, YEAR_COLUMN)
            age = _int_value(row, columns, AGE_COLUMN)
            if year is None or age is None:
                continue
            if query.year_start is not None and year < query.year_start:
                continue
            if query.year_end is not None and year > query.year_end:
                continue
            if query.age_start is not None and age < query.age_start:
                continue
            if query.age_end is not None and age > query.age_end:
                continue
            species = tuple(
                str(value)
                for name in SPECIES_COLUMNS
                if (value := _value(row, columns, name)) is not None and str(value).strip() != ""
            )
            if species_filter is not None and species_filter not in {
                code.upper() for code in species
            }:
                continue
            points.append(
                CurvePoint(
                    year=year,
                    age=age,
                    species=species,
                    volume_ws=_float_value(row, columns, FIELD_COLUMNS["volume_ws"]),
                    volume_cu=_float_value(row, columns, FIELD_COLUMNS["volume_cu"]),
                    volume_d=_float_value(row, columns, FIELD_COLUMNS["volume_d"]),
                    volume_dw=_float_value(row, columns, FIELD_COLUMNS["volume_dw"]),
                    volume_dwb=_float_value(row, columns, FIELD_COLUMNS["volume_dwb"]),
                    dom_height=_float_value(row, columns, FIELD_COLUMNS["dom_height"]),
                    lorey_height=_float_value(row, columns, FIELD_COLUMNS["lorey_height"]),
                    diameter=_float_value(row, columns, FIELD_COLUMNS["diameter"]),
                    tph=_float_value(row, columns, FIELD_COLUMNS["tph"]),
                    ba=_float_value(row, columns, FIELD_COLUMNS["ba"]),
                    site_index=_float_value(row, columns, FIELD_COLUMNS["site_index"]),
                    pct_stockable=_float_value(row, columns, FIELD_COLUMNS["pct_stockable"]),
                    units=self._units(),
                )
            )
        if not points:
            return CurveResult("empty", "no rows match the query", query, provenance, ())
        return CurveResult("ok", "", query, provenance, tuple(points))


def load_service(
    csv_path: Path,
    metadata_path: Path,
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    alias_path: Path | None = DEFAULT_ALIASES,
) -> CurveService:
    """Load a curve service from a CSV output and its metadata file.

    Parameters
    ----------
    csv_path : Path
        Yield-table CSV.
    metadata_path : Path
        Run metadata with ``runtime`` and ``console_version``.
    schema_path : Path, optional
        Column schema.
    alias_path : Path or None, optional
        CSV header alias file.

    Returns
    -------
    CurveService
        Service over the parsed table.

    Raises
    ------
    CurveQueryError
        When the metadata is not a JSON object.
    """
    table = parse_yield_csv(csv_path, schema_path=schema_path, alias_path=alias_path)
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CurveQueryError("metadata must be a JSON object")
    return CurveService(
        table=table,
        runtime=str(payload.get("runtime", "unknown")),
        console_version=str(payload.get("console_version", "unknown")),
        control_sequence=str(payload.get("control_sequence", "")),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Query a curve CSV from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` on success, ``1`` on a query error, and ``2`` on an input error.
    """
    parser = argparse.ArgumentParser(description="Query a parsed VDYP curve table.")
    parser.add_argument("--csv", type=Path, required=True, help="yield-table CSV")
    parser.add_argument("--metadata", type=Path, required=True, help="run metadata JSON")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="column schema")
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES, help="header aliases")
    parser.add_argument("--species", help="species code filter")
    parser.add_argument("--year-start", type=int)
    parser.add_argument("--year-end", type=int)
    parser.add_argument("--age-start", type=int)
    parser.add_argument("--age-end", type=int)
    parser.add_argument("--json", type=Path, help="also write the result")
    args = parser.parse_args(argv)
    try:
        service = load_service(
            args.csv, args.metadata, schema_path=args.schema, alias_path=args.aliases
        )
        result = service.query(
            CurveQuery(
                species=args.species,
                year_start=args.year_start,
                year_end=args.year_end,
                age_start=args.age_start,
                age_end=args.age_end,
            )
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"status: {result.status}")
    if result.reason:
        print(f"reason: {result.reason}")
    print(f"points: {len(result.points)}")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
