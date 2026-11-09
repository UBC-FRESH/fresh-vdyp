#!/usr/bin/env python3
"""Parse VDYP7 control files and the yield-table column definition.

The parser reads the fixed-column ``VDYP.CTR`` and ``VDYPBACK.CTR`` files and
the tab-separated ``*COLUMNS`` section of ``VDYP.tcl``. It preserves line
numbers, leading-zero sequence numbers, comments, and the literal description
text so later phases can join control sequences to coefficient files without
re-reading the raw bundle.

Command-line usage::

    python scripts/vdyp_control.py --config-dir "$VDYP_CFG_DIR" --output-dir out

The command writes ``vdyp-ctr.json``, ``vdypback-ctr.json``, and
``vdyp-columns.json``. ``--config-dir`` defaults to ``VDYP_CFG_DIR``.
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
from typing import Final

SEQUENCE_FIELD = slice(0, 3)
VALUE_FIELD = slice(4, 54)
DESCRIPTION_FIELD = slice(54, None)
SEQUENCE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{3}$")
CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:RD_[A-Za-z0-9]+|IPSJF\d+|IPFJF\d+)\b",
    re.IGNORECASE,
)
COLUMN_ID_WITH_NAME: Final[re.Pattern[str]] = re.compile(r"^(\d+)\s+(.*)$")
CONTROL_FILES: Final[tuple[str, ...]] = ("VDYP.CTR", "VDYPBACK.CTR")
COLUMN_FILE: Final[str] = "VDYP.tcl"


@dataclass(frozen=True)
class ControlEntry:
    """One numbered entry from a VDYP control file.

    Attributes
    ----------
    sequence : str
        Three-character sequence number, kept as text so leading zeros survive.
    value : str
        The field in columns 5-54, stripped. May be empty for a nullification.
    description : str
        The text after column 54, stripped.
    codes : tuple of str
        Upper-case ``RD_*``, ``IPSJF*``, and ``IPFJF*`` tokens found in the
        description.
    line_number : int
        One-based line number in the source file.
    """

    sequence: str
    value: str
    description: str
    codes: tuple[str, ...]
    line_number: int

    def to_dict(self) -> dict[str, object]:
        """Render the entry as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The entry fields under their manifest names.
        """
        return {
            "sequence": self.sequence,
            "value": self.value,
            "description": self.description,
            "codes": list(self.codes),
            "line_number": self.line_number,
        }


@dataclass(frozen=True)
class ControlFile:
    """The parsed entries and line counts of one control file.

    Attributes
    ----------
    source_file : str
        Repository-relative source label, such as ``VDYP_CFG/VDYP.CTR``.
    entries : tuple of ControlEntry
        Numbered entries in file order, including repeated sequence numbers.
    comment_lines : int
        Non-blank lines whose sequence field was blank or zero.
    blank_lines : int
        Whitespace-only lines.
    """

    source_file: str
    entries: tuple[ControlEntry, ...]
    comment_lines: int
    blank_lines: int

    def to_dict(self) -> dict[str, object]:
        """Render the control file as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source label, counts, and entries.
        """
        return {
            "source_file": self.source_file,
            "entry_count": len(self.entries),
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class ColumnSpec:
    """One column from the ``*COLUMNS`` section of ``VDYP.tcl``.

    Attributes
    ----------
    id : int
        Column identifier.
    name : str
        Short column name.
    units : str
        Unit label, or an empty string when the source has none.
    decimals : int
        Number of displayed decimals.
    description : str
        Long description, with embedded tab-separated fragments rejoined.
    width : int
        Display width.
    header_id : int
        Identifier of the header group.
    line_number : int
        One-based line number in the source file.
    """

    id: int
    name: str
    units: str
    decimals: int
    description: str
    width: int
    header_id: int
    line_number: int

    def to_dict(self) -> dict[str, object]:
        """Render the column as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The column fields under their manifest names.
        """
        return {
            "id": self.id,
            "name": self.name,
            "units": self.units,
            "decimals": self.decimals,
            "description": self.description,
            "width": self.width,
            "header_id": self.header_id,
            "line_number": self.line_number,
        }


@dataclass(frozen=True)
class ColumnTable:
    """The parsed ``*COLUMNS`` section of a VDYP report template.

    Attributes
    ----------
    source_file : str
        Repository-relative source label, such as ``VDYP_CFG/VDYP.tcl``.
    columns : tuple of ColumnSpec
        Columns in file order.
    """

    source_file: str
    columns: tuple[ColumnSpec, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the column table as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source label, column count, and columns.
        """
        return {
            "source_file": self.source_file,
            "column_count": len(self.columns),
            "columns": [column.to_dict() for column in self.columns],
        }


def parse_control_text(text: str, *, source_file: str) -> ControlFile:
    """Parse a control file from text.

    A line whose first three columns are blank or zero is a comment, as the
    file header states. A non-comment line must start with three digits; any
    other value raises an error instead of being silently skipped.

    Parameters
    ----------
    text : str
        Full control-file text, with LF or CRLF line endings.
    source_file : str
        Repository-relative source label recorded in the result.

    Returns
    -------
    ControlFile
        Entries in file order and the comment and blank line counts.

    Raises
    ------
    ValueError
        When a non-comment line does not start with a three-digit sequence.
    """
    entries: list[ControlEntry] = []
    comment_lines = 0
    blank_lines = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            blank_lines += 1
            continue
        sequence = line[SEQUENCE_FIELD].strip()
        if not sequence or sequence == "0":
            comment_lines += 1
            continue
        if SEQUENCE_PATTERN.fullmatch(sequence) is None:
            raise ValueError(f"{source_file}:{line_number}: invalid sequence {sequence!r}")
        value = line[VALUE_FIELD].strip()
        description = line[DESCRIPTION_FIELD].strip()
        codes = tuple(code.upper() for code in CODE_PATTERN.findall(description))
        entries.append(
            ControlEntry(
                sequence=sequence,
                value=value,
                description=description,
                codes=codes,
                line_number=line_number,
            )
        )
    return ControlFile(
        source_file=source_file,
        entries=tuple(entries),
        comment_lines=comment_lines,
        blank_lines=blank_lines,
    )


def parse_column_text(text: str, *, source_file: str) -> ColumnTable:
    """Parse the ``*COLUMNS`` section from a report-template text.

    Parameters
    ----------
    text : str
        Full template text, with LF or CRLF line endings.
    source_file : str
        Repository-relative source label recorded in the result.

    Returns
    -------
    ColumnTable
        Columns in file order.

    Raises
    ------
    ValueError
        When the section or a required field is missing, an integer field is
        malformed, or two columns share an identifier.
    """
    columns: list[ColumnSpec] = []
    seen_ids: set[int] = set()
    in_columns = False
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if line == "*COLUMNS":
            in_columns = True
            continue
        if not in_columns:
            continue
        if not line:
            break
        if line.startswith("'"):
            continue
        if line.startswith("*"):
            break
        column = parse_column_line(line, line_number=line_number, source_file=source_file)
        if column.id in seen_ids:
            raise ValueError(f"{source_file}:{line_number}: duplicate column id {column.id}")
        seen_ids.add(column.id)
        columns.append(column)
    if not columns:
        raise ValueError(f"{source_file}: no *COLUMNS entries found")
    return ColumnTable(source_file=source_file, columns=tuple(columns))


def parse_column_line(line: str, *, line_number: int, source_file: str) -> ColumnSpec:
    """Parse one tab-separated column line.

    The source has two quirks: row 20 separates its identifier from its name
    with spaces instead of a tab, and row 97 contains embedded tabs inside the
    description. This function repairs both without losing text.

    Parameters
    ----------
    line : str
        One data line from the ``*COLUMNS`` section.
    line_number : int
        One-based line number, used in error messages.
    source_file : str
        Repository-relative source label, used in error messages.

    Returns
    -------
    ColumnSpec
        The parsed column.

    Raises
    ------
    ValueError
        When fewer than seven fields remain or an integer field is malformed.
    """
    fields = line.split("\t")
    match = COLUMN_ID_WITH_NAME.match(fields[0])
    if match is not None:
        fields = [match.group(1), match.group(2), *fields[1:]]
    if len(fields) < 7:
        raise ValueError(f"{source_file}:{line_number}: column line has fewer than 7 fields")
    try:
        return ColumnSpec(
            id=int(fields[0]),
            name=fields[1].strip(),
            units=fields[2].strip(),
            decimals=int(fields[3]),
            description=" ".join(part.strip() for part in fields[4:-2]).strip(),
            width=int(fields[-2]),
            header_id=int(fields[-1]),
            line_number=line_number,
        )
    except ValueError as exc:
        raise ValueError(f"{source_file}:{line_number}: malformed column field") from exc


def load_control_file(path: Path, *, source_file: str | None = None) -> ControlFile:
    """Read and parse one control file.

    Parameters
    ----------
    path : Path
        Control file to read.
    source_file : str or None, optional
        Repository-relative source label. Defaults to the file name.

    Returns
    -------
    ControlFile
        The parsed control file.
    """
    return parse_control_text(
        path.read_text(encoding="ascii"),
        source_file=source_file or path.name,
    )


def load_column_table(path: Path, *, source_file: str | None = None) -> ColumnTable:
    """Read and parse one report-template file.

    Parameters
    ----------
    path : Path
        Template file to read.
    source_file : str or None, optional
        Repository-relative source label. Defaults to the file name.

    Returns
    -------
    ColumnTable
        The parsed column table.
    """
    return parse_column_text(
        path.read_text(encoding="ascii"),
        source_file=source_file or path.name,
    )


def write_json(payload: dict[str, object], output: Path) -> None:
    """Write one parsed artifact as pretty JSON.

    Parameters
    ----------
    payload : dict of str to object
        JSON-ready mapping.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The artifact is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_artifacts(config_dir: Path, output_dir: Path) -> dict[str, object]:
    """Parse every control artifact and write it to an output directory.

    Parameters
    ----------
    config_dir : Path
        Directory that contains ``VDYP.CTR``, ``VDYPBACK.CTR``, and
        ``VDYP.tcl``.
    output_dir : Path
        Directory for the three JSON artifacts.

    Returns
    -------
    dict of str to object
        Per-artifact counts keyed by output file name.

    Raises
    ------
    FileNotFoundError
        When a required source file is absent.
    """
    outputs: dict[str, object] = {}
    for name in CONTROL_FILES:
        source = config_dir / name
        parsed = load_control_file(source, source_file=f"VDYP_CFG/{name}")
        output = output_dir / f"{name.lower().replace('.ctr', '-ctr')}.json"
        write_json(parsed.to_dict(), output)
        outputs[output.name] = len(parsed.entries)
    columns = load_column_table(config_dir / COLUMN_FILE, source_file=f"VDYP_CFG/{COLUMN_FILE}")
    column_output = output_dir / "vdyp-columns.json"
    write_json(columns.to_dict(), column_output)
    outputs[column_output.name] = len(columns.columns)
    return outputs


def config_from_environment() -> Path | None:
    """Resolve the configuration directory from the documented environment.

    Returns
    -------
    Path or None
        ``VDYP_CFG_DIR`` when set and non-empty, otherwise ``None``.
    """
    value = os.environ.get("VDYP_CFG_DIR")
    return Path(value) if value else None


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the control files from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the artifacts are written, and ``2`` when the configuration
        directory is missing or unreadable.
    """
    parser = argparse.ArgumentParser(description="Parse VDYP7 control files and columns.")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument("--output-dir", type=Path, required=True, help="artifact directory")
    args = parser.parse_args(argv)
    config_dir: Path | None = (
        args.config_dir if args.config_dir is not None else config_from_environment()
    )
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    try:
        outputs = build_artifacts(config_dir, args.output_dir)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, count in outputs.items():
        print(f"Wrote {name} ({count} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
