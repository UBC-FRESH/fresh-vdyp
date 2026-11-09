#!/usr/bin/env python3
"""Parse VDYP7 ``.COE`` coefficient families into typed rows.

The source files are fixed-width numeric tables. Negative values sometimes touch
the previous field, so a whitespace split is not reliable. :func:`tokenize_row`
finds alphabetic labels and numbers in order, which restores one token per
field. Each family then uses a named schema, and a family without a registered
stable schema is rejected explicitly instead of being guessed.

Command-line usage::

    python scripts/coe_parser.py --coe-dir "$VDYP_CFG_DIR/coe" \
        --output notes/reference/vdyp-coe-summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

CoeValue = int | float | str
ColumnKind = Literal["number", "text"]

TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z][A-Za-z0-9]*|[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
)
INTEGER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[-+]?\d+$")
NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?$"
)
COMMENT_PREFIXES: Final[tuple[str, ...]] = ("#", "*", ";")
UNSUPPORTED_FAMILIES: Final[dict[str, str]] = {
    "complim": "variable token count: text and numeric columns vary by row",
    "regdqi04": "variable token count: one summary row and multi-coefficient rows",
}


@dataclass(frozen=True)
class CoeSchema:
    """The named columns and kinds of one coefficient family.

    Attributes
    ----------
    family : str
        Lowercase family name, normally the source file stem.
    columns : tuple of str
        Column names in source order.
    kinds : tuple of str
        One ``"number"`` or ``"text"`` kind for each column.
    """

    family: str
    columns: tuple[str, ...]
    kinds: tuple[ColumnKind, ...]


@dataclass(frozen=True)
class CoeRow:
    """One parsed coefficient row.

    Attributes
    ----------
    line_number : int
        One-based line number in the source file.
    values : tuple of int or float or str
        Values in schema column order.
    """

    line_number: int
    values: tuple[CoeValue, ...]

    def to_dict(self, columns: Sequence[str]) -> dict[str, object]:
        """Render the row as a JSON-ready mapping.

        Parameters
        ----------
        columns : sequence of str
            Column names in the same order as ``values``.

        Returns
        -------
        dict of str to object
            ``line_number`` plus one entry per column.
        """
        payload: dict[str, object] = {"line_number": self.line_number}
        payload.update(zip(columns, self.values, strict=True))
        return payload


@dataclass(frozen=True)
class CoeTable:
    """One parsed coefficient table.

    Attributes
    ----------
    family : str
        Lowercase family name.
    source_file : str
        Repository-relative source label.
    columns : tuple of str
        Column names in source order.
    rows : tuple of CoeRow
        Parsed data rows.
    """

    family: str
    source_file: str
    columns: tuple[str, ...]
    rows: tuple[CoeRow, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the table as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The family, source, columns, row count, and rows.
        """
        return {
            "family": self.family,
            "source_file": self.source_file,
            "columns": list(self.columns),
            "row_count": len(self.rows),
            "rows": [row.to_dict(self.columns) for row in self.rows],
        }


@dataclass(frozen=True)
class FamilySummary:
    """The parse status of one ``.COE`` file.

    Attributes
    ----------
    family : str
        Lowercase family name.
    source_file : str
        Repository-relative source label.
    status : str
        ``"parsed"`` or ``"unsupported"``.
    columns : tuple of str
        Column names for a parsed family, empty otherwise.
    row_count : int
        Parsed data rows.
    reason : str
        Why an unsupported family was rejected, empty otherwise.
    """

    family: str
    source_file: str
    status: str
    columns: tuple[str, ...]
    row_count: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Render the summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The family, source, status, columns, row count, and reason.
        """
        return {
            "family": self.family,
            "source_file": self.source_file,
            "status": self.status,
            "columns": list(self.columns),
            "row_count": self.row_count,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CoeSummary:
    """The parse summary for a coefficient directory.

    Attributes
    ----------
    families : tuple of FamilySummary
        One entry per ``.COE`` file, sorted by family name.
    """

    families: tuple[FamilySummary, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Totals and one entry per family.
        """
        parsed = sum(1 for item in self.families if item.status == "parsed")
        return {
            "family_count": len(self.families),
            "parsed_count": parsed,
            "unsupported_count": len(self.families) - parsed,
            "families": [item.to_dict() for item in self.families],
        }


class UnsupportedFamilyError(ValueError):
    """Raised when a coefficient family has no stable schema.

    Parameters
    ----------
    family : str
        Family that could not be parsed.
    reason : str
        Why the family is unsupported.
    """

    def __init__(self, family: str, reason: str) -> None:
        self.family = family
        self.reason = reason
        super().__init__(f"unsupported coefficient family {family!r}: {reason}")


class CoeParseError(ValueError):
    """Raised when a coefficient row does not match its schema.

    Parameters
    ----------
    source_file : str
        Source label.
    line_number : int
        One-based line number, or ``0`` for a file-level finding.
    message : str
        Explanation of the mismatch.
    """

    def __init__(self, source_file: str, line_number: int, message: str) -> None:
        self.source_file = source_file
        self.line_number = line_number
        self.message = message
        super().__init__(f"{source_file}:{line_number}: {message}")


def _columns(prefix: str, count: int) -> tuple[str, ...]:
    """Build positional column names.

    Parameters
    ----------
    prefix : str
        Prefix for each name.
    count : int
        Number of names.

    Returns
    -------
    tuple of str
        ``prefix0`` through ``prefix<count-1>``.
    """
    return tuple(f"{prefix}{index}" for index in range(count))


def _schema(
    family: str,
    columns: tuple[str, ...],
    text_positions: tuple[int, ...] = (),
) -> CoeSchema:
    """Build one schema with text positions marked.

    Parameters
    ----------
    family : str
        Lowercase family name.
    columns : tuple of str
        Column names.
    text_positions : tuple of int, optional
        Indexes that hold text rather than numbers.

    Returns
    -------
    CoeSchema
        The schema with one kind per column.
    """
    return CoeSchema(
        family=family,
        columns=columns,
        kinds=tuple(
            "text" if index in text_positions else "number" for index in range(len(columns))
        ),
    )


_INCREMENT = ("bec", "label", "flag", *_columns("v", 16))

COE_SCHEMAS: Final[dict[str, CoeSchema]] = {
    "bafip16": _schema("bafip16", (*_columns("c", 8), "flag"), (8,)),
    "basp05": _schema("basp05", ("group", "species", *_columns("c", 3))),
    "basp06": _schema("basp06", ("species", "group", *_columns("c", 3), "flag"), (0, 5)),
    "dqfip16z": _schema("dqfip16z", _columns("c", 7)),
    "dqsp05": _schema("dqsp05", ("group", "species", *_columns("c", 3))),
    "dqsp06": _schema("dqsp06", ("species", "group", *_columns("c", 3), "flag"), (0, 5)),
    "gb01": _schema("gb01", _columns("c", 10)),
    "gd19": _schema("gd19", _columns("c", 11)),
    "gd20": _schema("gd20", _columns("c", 11)),
    "gd23": _schema("gd23", _columns("c", 8)),
    "growba11": _schema("growba11", ("coastal_interior", *_columns("c", 4)), (0,)),
    "growba27": _schema("growba27", _INCREMENT, (0, 1)),
    "pct_40": _schema("pct_40", ("group", *_columns("c", 2), "species"), (3,)),
    "pct_407": _schema("pct_407", ("group", *_columns("c", 2), "species"), (3,)),
    "regba25": _schema("regba25", _INCREMENT, (0, 1)),
    "regbav01": _schema("regbav01", ("species", "coastal_interior", *_columns("c", 3)), (0, 1)),
    "regbreak": _schema("regbreak", _columns("c", 5)),
    "regdq18": _schema("regdq18", _INCREMENT, (0, 1)),
    "regdq24": _schema("regdq24", _INCREMENT, (0, 1)),
    "regdq26": _schema("regdq26", _INCREMENT, (0, 1)),
    "regdql2": _schema("regdql2", _columns("c", 9)),
    "reghl": _schema(
        "reghl",
        ("species", "species_2", "coastal_interior", "curve", *_columns("c", 2)),
        (0, 1, 2),
    ),
    "regvcu": _schema("regvcu", ("group", "species", *_columns("c", 3))),
    "regvdu": _schema("regvdu", ("group", "species", *_columns("c", 3))),
    "regvu": _schema("regvu", ("group", "species", *_columns("c", 4))),
    "regvwu": _schema("regvwu", ("species", *_columns("c", 6)), (0,)),
    "regyhlp": _schema("regyhlp", ("species", "coastal_interior", *_columns("c", 3)), (0, 1)),
    "regyhlpa": _schema("regyhlpa", ("species", "coastal_interior", *_columns("c", 2)), (0, 1)),
    "regyhlpc": _schema("regyhlpc", ("species", "coastal_interior", *_columns("c", 3)), (0, 1)),
    "top309": _schema("top309", _columns("c", 3)),
    "top98": _schema("top98", _columns("c", 3)),
    "upperb02": _schema("upperb02", ("species", "coastal_interior", *_columns("c", 2)), (0, 1)),
    "vtotreg4": _schema("vtotreg4", ("group", *_columns("b", 9))),
    "yldba309": _schema("yldba309", _columns("c", 9)),
    "yldba405": _schema("yldba405", _INCREMENT, (0, 1)),
    "yldba407": _schema("yldba407", _INCREMENT, (0, 1)),
    "ylddq309": _schema("ylddq309", _columns("c", 7)),
    "ylddq45": _schema("ylddq45", _INCREMENT, (0, 1)),
}


def tokenize_row(line: str) -> tuple[str, ...]:
    """Split one fixed-width row into labels and numbers.

    Parameters
    ----------
    line : str
        One source row.

    Returns
    -------
    tuple of str
        Tokens in source order. Concatenated numbers such as
        ``0.000000-0.0000285`` become two tokens.
    """
    return tuple(TOKEN_PATTERN.findall(line))


def coerce_value(token: str, kind: ColumnKind) -> CoeValue:
    """Convert one token to its schema type.

    Parameters
    ----------
    token : str
        Token from :func:`tokenize_row`.
    kind : {"number", "text"}
        Expected column kind.

    Returns
    -------
    int or float or str
        An integer for an integer token, a float for a decimal token, or the
        text token unchanged.

    Raises
    ------
    ValueError
        When the token does not match the expected kind.
    """
    if kind == "text":
        if not any(character.isalpha() for character in token):
            raise ValueError(f"expected a text token, found {token!r}")
        return token
    if NUMBER_PATTERN.fullmatch(token) is None:
        raise ValueError(f"expected a number token, found {token!r}")
    return int(token) if INTEGER_PATTERN.fullmatch(token) is not None else float(token)


def schema_for(family: str) -> CoeSchema:
    """Look up the schema for one family.

    Parameters
    ----------
    family : str
        Family name, case-insensitive.

    Returns
    -------
    CoeSchema
        The registered schema.

    Raises
    ------
    UnsupportedFamilyError
        When the family has a known variable shape or no schema.
    """
    key = family.lower()
    reason = UNSUPPORTED_FAMILIES.get(key)
    if reason is not None:
        raise UnsupportedFamilyError(key, reason)
    schema = COE_SCHEMAS.get(key)
    if schema is None:
        raise UnsupportedFamilyError(key, "no schema is registered")
    return schema


def parse_coe_text(text: str, *, source_file: str, family: str) -> CoeTable:
    """Parse coefficient text against a family schema.

    Parameters
    ----------
    text : str
        Full source text with LF or CRLF line endings.
    source_file : str
        Repository-relative source label.
    family : str
        Family name, normally the file stem.

    Returns
    -------
    CoeTable
        The parsed rows.

    Raises
    ------
    UnsupportedFamilyError
        When the family has no stable schema.
    CoeParseError
        When a row has the wrong token count, the wrong token kind, or the file
        has no data rows.
    """
    schema = schema_for(family)
    rows: list[CoeRow] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIXES):
            continue
        tokens = tokenize_row(line)
        if len(tokens) != len(schema.columns):
            raise CoeParseError(
                source_file,
                line_number,
                f"expected {len(schema.columns)} tokens, found {len(tokens)}",
            )
        try:
            values = tuple(
                coerce_value(token, kind) for token, kind in zip(tokens, schema.kinds, strict=True)
            )
        except ValueError as exc:
            raise CoeParseError(source_file, line_number, str(exc)) from exc
        rows.append(CoeRow(line_number=line_number, values=values))
    if not rows:
        raise CoeParseError(source_file, 0, "no data rows")
    return CoeTable(
        family=schema.family,
        source_file=source_file,
        columns=schema.columns,
        rows=tuple(rows),
    )


def parse_coe_file(path: Path, *, source_file: str | None = None) -> CoeTable:
    """Read and parse one coefficient file.

    Parameters
    ----------
    path : Path
        Source file. Its stem selects the schema.
    source_file : str or None, optional
        Repository-relative source label. Defaults to ``VDYP_CFG/coe/<name>``.

    Returns
    -------
    CoeTable
        The parsed table.
    """
    label = source_file or f"VDYP_CFG/coe/{path.name}"
    return parse_coe_text(
        path.read_text(encoding="ascii"),
        source_file=label,
        family=path.stem,
    )


def build_summary(coe_dir: Path) -> CoeSummary:
    """Parse every ``.COE`` file in a directory and summarize the results.

    Parameters
    ----------
    coe_dir : Path
        Directory that holds the coefficient files.

    Returns
    -------
    CoeSummary
        One status entry per file, sorted by family name.

    Raises
    ------
    NotADirectoryError
        When ``coe_dir`` is not a directory.
    """
    if not coe_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {coe_dir}")
    summaries: list[FamilySummary] = []
    paths = sorted(
        (path for path in coe_dir.iterdir() if path.is_file() and path.suffix.lower() == ".coe"),
        key=lambda path: path.stem.lower(),
    )
    for path in paths:
        family = path.stem.lower()
        label = f"VDYP_CFG/coe/{path.name}"
        reason = UNSUPPORTED_FAMILIES.get(family)
        if reason is not None:
            summaries.append(FamilySummary(family, label, "unsupported", (), 0, reason))
            continue
        table = parse_coe_file(path, source_file=label)
        summaries.append(FamilySummary(family, label, "parsed", table.columns, len(table.rows), ""))
    return CoeSummary(families=tuple(summaries))


def write_summary(summary: CoeSummary, output: Path) -> None:
    """Write a coefficient summary as pretty JSON.

    Parameters
    ----------
    summary : CoeSummary
        Summary to serialize.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The summary is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary.to_dict(), indent=2) + "\n", encoding="utf-8")


def coe_dir_from_environment() -> Path | None:
    """Resolve the coefficient directory from ``VDYP_CFG_DIR``.

    Returns
    -------
    Path or None
        ``VDYP_CFG_DIR/coe`` when the variable is set, otherwise ``None``.
    """
    value = os.environ.get("VDYP_CFG_DIR")
    return Path(value) / "coe" if value else None


def main(argv: Sequence[str] | None = None) -> int:
    """Summarize the coefficient directory from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the summary is written, and ``2`` on a missing directory or
        a parse failure.
    """
    parser = argparse.ArgumentParser(description="Parse and summarize VDYP7 .COE families.")
    parser.add_argument("--coe-dir", type=Path, help="coe directory; defaults to VDYP_CFG_DIR")
    parser.add_argument("--output", type=Path, required=True, help="summary path to write")
    args = parser.parse_args(argv)
    coe_dir: Path | None = args.coe_dir if args.coe_dir is not None else coe_dir_from_environment()
    if coe_dir is None:
        print("error: pass --coe-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    try:
        summary = build_summary(coe_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_summary(summary, args.output)
    payload = summary.to_dict()
    print(
        f"Wrote {payload['family_count']} families "
        f"({payload['parsed_count']} parsed, {payload['unsupported_count']} unsupported)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
