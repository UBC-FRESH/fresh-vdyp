#!/usr/bin/env python3
"""Parse the structural shape of VDYP7 control, parameter, and data files.

This parser records line-oriented structure, not equation semantics. ``.DAT``
files become either a one-token lookup or a token table. ``.PRM`` files become
keyed rows whose first token is the key. ``.CTR`` files reuse the P1 control
parser. Comment, blank-line, and line-number rules are explicit, so later phases
can infer species, BEC, and equation keys from a stable shape.

Command-line usage::

    python scripts/config_parser.py --config-dir "$VDYP_CFG_DIR" \
        --output notes/reference/vdyp-config-summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from vdyp_control import load_control_file

DatFormat = Literal["lookup", "table", "empty"]
COMMENT_PREFIXES: Final[tuple[str, ...]] = ("#", "*", ";")
DATA_SUFFIXES: Final[frozenset[str]] = frozenset({".dat"})
PARAMETER_SUFFIXES: Final[frozenset[str]] = frozenset({".prm"})


@dataclass(frozen=True)
class DatRecord:
    """One data row from a ``.DAT`` file.

    Attributes
    ----------
    line_number : int
        One-based line number.
    tokens : tuple of str
        Whitespace-separated tokens in source order.
    """

    line_number: int
    tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the record as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The line number and tokens.
        """
        return {"line_number": self.line_number, "tokens": list(self.tokens)}


@dataclass(frozen=True)
class DatTable:
    """A parsed ``.DAT`` file.

    Attributes
    ----------
    source_file : str
        Repository-relative source label.
    format : {"lookup", "table", "empty"}
        ``lookup`` when every data row has exactly one token, ``table`` when a
        row has more, and ``empty`` when there are no data rows.
    records : tuple of DatRecord
        Data rows in source order.
    comment_lines : int
        Non-blank lines that start with a comment marker.
    blank_lines : int
        Whitespace-only lines.
    """

    source_file: str
    format: DatFormat
    records: tuple[DatRecord, ...]
    comment_lines: int
    blank_lines: int

    def to_dict(self) -> dict[str, object]:
        """Render the table as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source, format, counts, and records.
        """
        return {
            "source_file": self.source_file,
            "format": self.format,
            "row_count": len(self.records),
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True)
class PrmRecord:
    """One data row from a ``.PRM`` file.

    Attributes
    ----------
    line_number : int
        One-based line number.
    key : str
        First token, treated as the record key.
    tokens : tuple of str
        Remaining tokens in source order.
    """

    line_number: int
    key: str
    tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the record as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The line number, key, and remaining tokens.
        """
        return {
            "line_number": self.line_number,
            "key": self.key,
            "tokens": list(self.tokens),
        }


@dataclass(frozen=True)
class PrmTable:
    """A parsed ``.PRM`` file.

    Attributes
    ----------
    source_file : str
        Repository-relative source label.
    records : tuple of PrmRecord
        Keyed rows in source order.
    comment_lines : int
        Non-blank lines that start with a comment marker.
    blank_lines : int
        Whitespace-only lines.
    """

    source_file: str
    records: tuple[PrmRecord, ...]
    comment_lines: int
    blank_lines: int

    def to_dict(self) -> dict[str, object]:
        """Render the table as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The source, counts, and records.
        """
        return {
            "source_file": self.source_file,
            "format": "keyed",
            "row_count": len(self.records),
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True)
class FileSummary:
    """The parse status of one control, parameter, or data file.

    Attributes
    ----------
    source_file : str
        Repository-relative source label.
    kind : str
        ``control``, ``parameter``, or ``data``.
    format : str
        Detected structure, such as ``control``, ``keyed``, ``lookup``,
        ``table``, or ``empty``.
    row_count : int
        Parsed data rows.
    comment_lines : int
        Non-blank comment lines.
    blank_lines : int
        Whitespace-only lines.
    """

    source_file: str
    kind: str
    format: str
    row_count: int
    comment_lines: int
    blank_lines: int

    def to_dict(self) -> dict[str, object]:
        """Render the summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The file, kind, format, and counts.
        """
        return {
            "source_file": self.source_file,
            "kind": self.kind,
            "format": self.format,
            "row_count": self.row_count,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
        }


@dataclass(frozen=True)
class ConfigSummary:
    """The structural summary of a configuration directory.

    Attributes
    ----------
    files : tuple of FileSummary
        One entry per control, parameter, and data file.
    """

    files: tuple[FileSummary, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Counts and one entry per file.
        """
        return {
            "file_count": len(self.files),
            "total_rows": sum(item.row_count for item in self.files),
            "files": [item.to_dict() for item in self.files],
        }


class ConfigParseError(ValueError):
    """Raised when a configuration row violates its declared shape.

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


def _data_lines(text: str) -> tuple[list[tuple[int, tuple[str, ...]]], int, int]:
    """Split text into data rows and count comments and blank lines.

    Parameters
    ----------
    text : str
        File text with LF or CRLF line endings.

    Returns
    -------
    tuple of (list of (int, tuple of str), int, int)
        Data rows with their line numbers, the comment-line count, and the
        blank-line count.
    """
    rows: list[tuple[int, tuple[str, ...]]] = []
    comment_lines = 0
    blank_lines = 0
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            blank_lines += 1
            continue
        if line.startswith(COMMENT_PREFIXES):
            comment_lines += 1
            continue
        rows.append((line_number, tuple(line.split())))
    return rows, comment_lines, blank_lines


def parse_dat_text(
    text: str,
    *,
    source_file: str,
    format_hint: Literal["auto", "lookup", "table"] = "auto",
) -> DatTable:
    """Parse a ``.DAT`` file into a lookup or a token table.

    Parameters
    ----------
    text : str
        File text with LF or CRLF line endings.
    source_file : str
        Repository-relative source label.
    format_hint : {"auto", "lookup", "table"}, optional
        ``auto`` chooses ``lookup`` when every row has one token. ``lookup``
        raises when a row has more than one token.

    Returns
    -------
    DatTable
        The parsed table.

    Raises
    ------
    ConfigParseError
        When a row is empty or violates the requested lookup format.
    """
    rows, comment_lines, blank_lines = _data_lines(text)
    if not rows:
        return DatTable(source_file, "empty", (), comment_lines, blank_lines)
    if format_hint == "lookup" or (
        format_hint == "auto" and all(len(tokens) == 1 for _, tokens in rows)
    ):
        for line_number, tokens in rows:
            if len(tokens) != 1:
                raise ConfigParseError(
                    source_file, line_number, "expected one token for a lookup row"
                )
        records = tuple(DatRecord(line_number, tokens) for line_number, tokens in rows)
        return DatTable(source_file, "lookup", records, comment_lines, blank_lines)
    records = tuple(DatRecord(line_number, tokens) for line_number, tokens in rows)
    return DatTable(source_file, "table", records, comment_lines, blank_lines)


def parse_prm_text(text: str, *, source_file: str) -> PrmTable:
    """Parse a ``.PRM`` file into keyed rows.

    A data row is any non-blank, non-comment line. Its first token is the key;
    the remaining tokens are kept in source order. A comment-only file is valid
    and yields zero records.

    Parameters
    ----------
    text : str
        File text with LF or CRLF line endings.
    source_file : str
        Repository-relative source label.

    Returns
    -------
    PrmTable
        The parsed keyed rows.

    Raises
    ------
    ConfigParseError
        When a data row has no key.
    """
    rows, comment_lines, blank_lines = _data_lines(text)
    records: list[PrmRecord] = []
    for line_number, tokens in rows:
        if not tokens:
            raise ConfigParseError(source_file, line_number, "data row has no tokens")
        records.append(PrmRecord(line_number, tokens[0], tokens[1:]))
    return PrmTable(source_file, tuple(records), comment_lines, blank_lines)


def parse_dat_file(path: Path, *, source_file: str | None = None) -> DatTable:
    """Read and parse one ``.DAT`` file.

    Parameters
    ----------
    path : Path
        Source file.
    source_file : str or None, optional
        Repository-relative source label. Defaults to
        ``VDYP_CFG/coe/<name>``.

    Returns
    -------
    DatTable
        The parsed table.
    """
    label = source_file or f"VDYP_CFG/coe/{path.name}"
    return parse_dat_text(path.read_text(encoding="ascii"), source_file=label)


def parse_prm_file(path: Path, *, source_file: str | None = None) -> PrmTable:
    """Read and parse one ``.PRM`` file.

    Parameters
    ----------
    path : Path
        Source file.
    source_file : str or None, optional
        Repository-relative source label. Defaults to
        ``VDYP_CFG/coe/<name>``.

    Returns
    -------
    PrmTable
        The parsed table.
    """
    label = source_file or f"VDYP_CFG/coe/{path.name}"
    return parse_prm_text(path.read_text(encoding="ascii"), source_file=label)


def build_summary(config_dir: Path) -> ConfigSummary:
    """Parse every control, parameter, and data file in a configuration tree.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and the ``coe`` directory.

    Returns
    -------
    ConfigSummary
        One entry per file, sorted by source label.

    Raises
    ------
    NotADirectoryError
        When ``config_dir`` or its ``coe`` directory is missing.
    """
    coe_dir = config_dir / "coe"
    if not coefficient_dir_ok(config_dir):
        raise NotADirectoryError(f"not a directory: {coe_dir}")
    summaries: list[FileSummary] = []
    for path in sorted(config_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.suffix.lower() == ".ctr":
            control = load_control_file(path, source_file=f"VDYP_CFG/{path.name}")
            summaries.append(
                FileSummary(
                    source_file=control.source_file,
                    kind="control",
                    format="control",
                    row_count=len(control.entries),
                    comment_lines=control.comment_lines,
                    blank_lines=control.blank_lines,
                )
            )
    for path in sorted(coe_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        label = f"VDYP_CFG/coe/{path.name}"
        if suffix in DATA_SUFFIXES:
            table = parse_dat_file(path, source_file=label)
            summaries.append(
                FileSummary(
                    label,
                    "data",
                    table.format,
                    len(table.records),
                    table.comment_lines,
                    table.blank_lines,
                )
            )
        elif suffix in PARAMETER_SUFFIXES:
            parameters = parse_prm_file(path, source_file=label)
            summaries.append(
                FileSummary(
                    label,
                    "parameter",
                    "keyed",
                    len(parameters.records),
                    parameters.comment_lines,
                    parameters.blank_lines,
                )
            )
    return ConfigSummary(files=tuple(summaries))


def coefficient_dir_ok(config_dir: Path) -> bool:
    """Report whether a configuration directory has a ``coe`` subdirectory.

    Parameters
    ----------
    config_dir : Path
        Directory to inspect.

    Returns
    -------
    bool
        ``True`` when ``config_dir/coe`` is a directory.
    """
    return config_dir.is_dir() and (config_dir / "coe").is_dir()


def write_summary(summary: ConfigSummary, output: Path) -> None:
    """Write a configuration summary as pretty JSON.

    Parameters
    ----------
    summary : ConfigSummary
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


def config_from_environment() -> Path | None:
    """Resolve the configuration directory from ``VDYP_CFG_DIR``.

    Returns
    -------
    Path or None
        The environment value when set and non-empty, otherwise ``None``.
    """
    value = os.environ.get("VDYP_CFG_DIR")
    return Path(value) if value else None


def main(argv: Sequence[str] | None = None) -> int:
    """Summarize control, parameter, and data files from the command line.

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
    parser = argparse.ArgumentParser(description="Parse VDYP7 control, PRM, and DAT shapes.")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument("--output", type=Path, required=True, help="summary path to write")
    args = parser.parse_args(argv)
    config_dir: Path | None = (
        args.config_dir if args.config_dir is not None else config_from_environment()
    )
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    try:
        summary = build_summary(config_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_summary(summary, args.output)
    payload = summary.to_dict()
    print(f"Wrote {payload['file_count']} files with {payload['total_rows']} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
