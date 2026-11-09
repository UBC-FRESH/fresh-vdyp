#!/usr/bin/env python3
"""Validate provenance-manifest entries against the fresh-vdyp contract.

Every extracted asset gets one manifest entry. This module is the executable
form of ``notes/plan/0002-data-provenance.md``: it checks the required fields,
the identifier and SHA256 shapes, the UTC timestamp, the relative source path,
and the optional column, unit, and row-count types.

Command-line usage::

    python scripts/provenance.py --manifest path/to/manifest.json

The exit status is ``0`` when the manifest is valid, ``1`` when it has findings,
and ``2`` when the file is missing or is not valid JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^vdyp-[a-z0-9]+(?:-[a-z0-9]+)*$")
KIND_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "id",
    "kind",
    "source_model",
    "source_version",
    "source_file",
    "source_sha256",
    "extracted_at_utc",
    "extractor",
    "citation",
)
OPTIONAL_FIELDS: Final[tuple[str, ...]] = (
    "family",
    "control_sequence",
    "columns",
    "row_count",
    "units",
    "notes",
)


@dataclass(frozen=True)
class Diagnostic:
    """One finding from provenance validation.

    Attributes
    ----------
    code : str
        Stable finding code, such as ``MISSING-FIELD``.
    field_name : str
        Manifest field that the finding concerns.
    message : str
        Explanation of what to change.
    """

    code: str
    field_name: str
    message: str

    def render(self) -> str:
        """Render the finding as one line of text.

        Returns
        -------
        str
            The code, field, and message, padded into columns.
        """
        return f"{self.code:<20}{self.field_name:<20}{self.message}"


class ManifestError(ValueError):
    """Raised when a manifest entry has one or more validation findings.

    Parameters
    ----------
    diagnostics : sequence of Diagnostic
        The findings that make the entry invalid.
    """

    def __init__(self, diagnostics: Sequence[Diagnostic]) -> None:
        self.diagnostics: tuple[Diagnostic, ...] = tuple(diagnostics)
        message = "; ".join(item.render() for item in self.diagnostics)
        super().__init__(message)


def _string_field(entry: Mapping[str, object], name: str) -> str | None:
    """Read a required non-empty string field.

    Parameters
    ----------
    entry : mapping of str to object
        Manifest entry to inspect.
    name : str
        Field name.

    Returns
    -------
    str or None
        The stripped value, or ``None`` when the field is missing, empty, or
        not a string.
    """
    value = entry.get(name)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _is_utc_timestamp(value: str) -> bool:
    """Report whether a string is an ISO 8601 UTC timestamp ending in ``Z``.

    Parameters
    ----------
    value : str
        Candidate timestamp.

    Returns
    -------
    bool
        ``True`` when the value parses and its offset is exactly UTC.
    """
    if not value.endswith("Z"):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() == dt.timedelta(0)


def _is_relative_source_file(value: str) -> bool:
    """Report whether a source path is repository-relative and safe.

    Parameters
    ----------
    value : str
        Source file value.

    Returns
    -------
    bool
        ``True`` for a forward-slash relative path without ``..`` or a drive
        letter.
    """
    return (
        bool(value)
        and not value.startswith(("/", "\\"))
        and "\\" not in value
        and ".." not in value.split("/")
        and ":" not in value
    )


def validate_manifest_entry(entry: Mapping[str, object]) -> tuple[Diagnostic, ...]:
    """Validate one manifest entry.

    Parameters
    ----------
    entry : mapping of str to object
        One JSON-like manifest entry.

    Returns
    -------
    tuple of Diagnostic
        Findings in a stable field order. The tuple is empty when the entry is
        valid.
    """
    findings: list[Diagnostic] = []
    values: dict[str, str] = {}
    for name in REQUIRED_FIELDS:
        value = _string_field(entry, name)
        if value is None:
            findings.append(
                Diagnostic("MISSING-FIELD", name, "required non-empty string is missing")
            )
            continue
        values[name] = value

    identifier = values.get("id")
    if identifier is not None and ID_PATTERN.fullmatch(identifier) is None:
        findings.append(
            Diagnostic("INVALID-ID", "id", "expected a lowercase 'vdyp-' slug with hyphens")
        )
    kind = values.get("kind")
    if kind is not None and KIND_PATTERN.fullmatch(kind) is None:
        findings.append(Diagnostic("INVALID-KIND", "kind", "expected a lowercase underscore kind"))
    digest = values.get("source_sha256")
    if digest is not None and SHA256_PATTERN.fullmatch(digest) is None:
        findings.append(
            Diagnostic("INVALID-SHA256", "source_sha256", "expected 64 lowercase hex characters")
        )
    timestamp = values.get("extracted_at_utc")
    if timestamp is not None and not _is_utc_timestamp(timestamp):
        findings.append(
            Diagnostic(
                "INVALID-TIMESTAMP",
                "extracted_at_utc",
                "expected an ISO 8601 UTC timestamp ending in 'Z'",
            )
        )
    source_file = values.get("source_file")
    if source_file is not None and not _is_relative_source_file(source_file):
        findings.append(
            Diagnostic(
                "INVALID-SOURCE-FILE",
                "source_file",
                "expected a forward-slash relative path without '..' or a drive",
            )
        )

    parser_version = entry.get("parser_version")
    if parser_version is None:
        findings.append(
            Diagnostic("MISSING-FIELD", "parser_version", "required integer is missing")
        )
    elif (
        not isinstance(parser_version, int)
        or isinstance(parser_version, bool)
        or parser_version < 1
    ):
        findings.append(
            Diagnostic("INVALID-PARSER-VERSION", "parser_version", "expected an integer >= 1")
        )

    row_count = entry.get("row_count")
    if row_count is not None:
        if isinstance(row_count, int) and not isinstance(row_count, bool):
            if row_count < 0:
                findings.append(
                    Diagnostic("INVALID-ROW-COUNT", "row_count", "expected an integer >= 0")
                )
        else:
            findings.append(
                Diagnostic("INVALID-ROW-COUNT", "row_count", "expected an integer >= 0")
            )

    columns = entry.get("columns")
    if columns is not None:
        if not isinstance(columns, list) or not columns:
            findings.append(
                Diagnostic("INVALID-COLUMNS", "columns", "expected a non-empty list of names")
            )
        elif not all(isinstance(item, str) and item.strip() for item in columns):
            findings.append(
                Diagnostic("INVALID-COLUMNS", "columns", "every column name must be non-empty")
            )
        elif len(set(columns)) != len(columns):
            findings.append(Diagnostic("INVALID-COLUMNS", "columns", "column names must be unique"))

    units = entry.get("units")
    if units is not None:
        if not isinstance(units, dict):
            findings.append(
                Diagnostic("INVALID-UNITS", "units", "expected a mapping of field to unit")
            )
        elif not all(
            isinstance(key, str) and isinstance(value, str) for key, value in units.items()
        ):
            findings.append(
                Diagnostic("INVALID-UNITS", "units", "every key and value must be a string")
            )
    return tuple(findings)


def validate_manifest(payload: object) -> tuple[Diagnostic, ...]:
    """Validate a manifest payload that is one entry or a list of entries.

    Parameters
    ----------
    payload : object
        Decoded JSON value.

    Returns
    -------
    tuple of Diagnostic
        Findings for every entry, prefixed by the entry index when the payload
        is a list.
    """
    if isinstance(payload, dict):
        items: list[object] = [payload]
    elif isinstance(payload, list):
        items = payload
    else:
        return (
            Diagnostic(
                "INVALID-PAYLOAD",
                "manifest",
                "expected an object or a list of objects",
            ),
        )
    findings: list[Diagnostic] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            findings.append(Diagnostic("INVALID-PAYLOAD", f"[{index}]", "expected an object"))
            continue
        for finding in validate_manifest_entry(item):
            findings.append(
                Diagnostic(
                    finding.code,
                    f"[{index}].{finding.field_name}",
                    finding.message,
                )
            )
    return tuple(findings)


def require_valid(entry: Mapping[str, object]) -> None:
    """Raise when one entry has validation findings.

    Parameters
    ----------
    entry : mapping of str to object
        Manifest entry to validate.

    Returns
    -------
    None
        The entry is valid.

    Raises
    ------
    ManifestError
        When one or more findings are present.
    """
    findings = validate_manifest_entry(entry)
    if findings:
        raise ManifestError(findings)


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a manifest file from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the manifest is valid, ``1`` when it has findings, and ``2``
        when the file cannot be read or parsed.
    """
    parser = argparse.ArgumentParser(description="Validate provenance-manifest entries.")
    parser.add_argument("--manifest", type=Path, required=True, help="JSON manifest to validate")
    args = parser.parse_args(argv)
    try:
        payload: object = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = validate_manifest(payload)
    for finding in findings:
        print(finding.render())
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
