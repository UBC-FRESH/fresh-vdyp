#!/usr/bin/env python3
"""Normalize parsed VDYP7 coefficient tables to CSV with a provenance manifest.

Each supported family becomes one CSV file with a ``source_line`` column followed
by the original schema columns. A manifest entry records the source file, its
SHA256, the normalized CSV SHA256, the equation family, and the control sequence.
Entries are validated with :mod:`provenance` before they are written.

Normalized CSV files are generated assets and are ignored by Git. The manifest
can be tracked because it carries hashes and source labels, not model data.

Command-line usage::

    python scripts/normalize.py --config-dir "$VDYP_CFG_DIR" \
        --output-dir data/normalized
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from coe_parser import UNSUPPORTED_FAMILIES, CoeTable, parse_coe_file
from inventory_vdyp import CITATION, sha256_file
from key_inference import build_catalog as build_key_catalog
from provenance import require_valid

EXTRACTOR: Final[str] = "fresh-vdyp 0.1.0"
PARSER_VERSION: Final[int] = 1
SOURCE_MODEL: Final[str] = "VDYP7"
SOURCE_VERSION: Final[str] = "7"
DEFAULT_OUTPUT_DIR: Final[Path] = Path("data/normalized")


@dataclass(frozen=True)
class NormalizedAsset:
    """One normalized family and its manifest entry.

    Attributes
    ----------
    family : str
        Lowercase family name.
    equation_family : str
        Equation-family label from the key catalog.
    control_sequence : str
        First control sequence that references the file, or an empty string.
    source_file : str
        Repository-relative source label.
    csv_file : str
        File name of the normalized CSV.
    row_count : int
        Number of data rows.
    normalized_sha256 : str
        SHA256 of the normalized CSV.
    """

    family: str
    equation_family: str
    control_sequence: str
    source_file: str
    csv_file: str
    row_count: int
    normalized_sha256: str

    def to_dict(self) -> dict[str, object]:
        """Render the asset summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The asset fields.
        """
        return {
            "family": self.family,
            "equation_family": self.equation_family,
            "control_sequence": self.control_sequence,
            "source_file": self.source_file,
            "csv_file": self.csv_file,
            "row_count": self.row_count,
            "normalized_sha256": self.normalized_sha256,
        }


@dataclass(frozen=True)
class UnsupportedFamily:
    """A family that was parsed for status but not normalized.

    Attributes
    ----------
    family : str
        Lowercase family name.
    source_file : str
        Repository-relative source label.
    reason : str
        Why the family has no stable schema.
    """

    family: str
    source_file: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Render the unsupported family as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The family, source, and reason.
        """
        return {"family": self.family, "source_file": self.source_file, "reason": self.reason}


@dataclass(frozen=True)
class NormalizationResult:
    """The assets and unsupported families from one normalization run.

    Attributes
    ----------
    assets : tuple of NormalizedAsset
        Normalized families.
    unsupported : tuple of UnsupportedFamily
        Families left unnormalized with a reason.
    manifest : tuple of dict of str to object
        Provenance entries, one per asset.
    """

    assets: tuple[NormalizedAsset, ...]
    unsupported: tuple[UnsupportedFamily, ...]
    manifest: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        """Render the result summary as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Counts, total rows, assets, and unsupported families.
        """
        return {
            "asset_count": len(self.assets),
            "row_count": sum(asset.row_count for asset in self.assets),
            "unsupported_count": len(self.unsupported),
            "assets": [asset.to_dict() for asset in self.assets],
            "unsupported": [item.to_dict() for item in self.unsupported],
        }


def utc_now() -> str:
    """Return the current UTC time as an ISO 8601 ``Z`` timestamp.

    Returns
    -------
    str
        Whole-second timestamp, such as ``2026-11-09T00:00:00Z``.
    """
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_value(value: int | float | str) -> str:
    """Format one typed value for CSV output.

    Parameters
    ----------
    value : int or float or str
        Value from a parsed row.

    Returns
    -------
    str
        The value as deterministic text.
    """
    return str(value)


def write_csv(table: CoeTable, path: Path) -> str:
    """Write one table as CSV and return the file SHA256.

    Parameters
    ----------
    table : CoeTable
        Parsed table.
    path : Path
        Destination CSV file. Parent directories are created.

    Returns
    -------
    str
        Lowercase hexadecimal SHA256 of the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("source_line", *table.columns))
        for row in table.rows:
            writer.writerow((str(row.line_number), *(format_value(value) for value in row.values)))
    return sha256_file(path)


def manifest_entry(
    table: CoeTable,
    *,
    source_sha256: str,
    normalized_sha256: str,
    extracted_at: str,
    equation_family: str,
    control_sequence: str,
) -> dict[str, object]:
    """Build and validate the provenance entry for one normalized table.

    Parameters
    ----------
    table : CoeTable
        Parsed table.
    source_sha256 : str
        SHA256 of the raw source file.
    normalized_sha256 : str
        SHA256 of the normalized CSV.
    extracted_at : str
        ISO 8601 UTC timestamp.
    equation_family : str
        Equation-family label.
    control_sequence : str
        First control sequence, or an empty string.

    Returns
    -------
    dict of str to object
        A provenance entry that passed :func:`provenance.require_valid`.

    Raises
    ------
    ManifestError
        When the constructed entry is invalid.
    """
    entry: dict[str, object] = {
        "id": f"vdyp-{table.family.replace('_', '-')}",
        "kind": "vdyp_coefficient_table",
        "source_model": SOURCE_MODEL,
        "source_version": SOURCE_VERSION,
        "source_file": table.source_file,
        "source_sha256": source_sha256,
        "normalized_sha256": normalized_sha256,
        "extracted_at_utc": extracted_at,
        "extractor": EXTRACTOR,
        "parser_version": PARSER_VERSION,
        "family": equation_family,
        "control_sequence": control_sequence,
        "columns": list(table.columns),
        "row_count": len(table.rows),
        "citation": CITATION,
    }
    require_valid(entry)
    return entry


def normalize_table(
    table: CoeTable,
    source_path: Path,
    output_dir: Path,
    *,
    extracted_at: str,
    equation_family: str,
    control_sequence: str,
) -> tuple[NormalizedAsset, dict[str, object]]:
    """Normalize one parsed table and build its manifest entry.

    Parameters
    ----------
    table : CoeTable
        Parsed table.
    source_path : Path
        Raw source file, used for its SHA256.
    output_dir : Path
        Destination directory for the CSV.
    extracted_at : str
        ISO 8601 UTC timestamp.
    equation_family : str
        Equation-family label.
    control_sequence : str
        First control sequence, or an empty string.

    Returns
    -------
    tuple of (NormalizedAsset, dict of str to object)
        The asset summary and the validated manifest entry.
    """
    csv_path = output_dir / f"{table.family}.csv"
    normalized_sha256 = write_csv(table, csv_path)
    entry = manifest_entry(
        table,
        source_sha256=sha256_file(source_path),
        normalized_sha256=normalized_sha256,
        extracted_at=extracted_at,
        equation_family=equation_family,
        control_sequence=control_sequence,
    )
    asset = NormalizedAsset(
        family=table.family,
        equation_family=equation_family,
        control_sequence=control_sequence,
        source_file=table.source_file,
        csv_file=csv_path.name,
        row_count=len(table.rows),
        normalized_sha256=normalized_sha256,
    )
    return asset, entry


def build_normalized_catalog(
    config_dir: Path,
    output_dir: Path,
    *,
    extracted_at: str,
) -> NormalizationResult:
    """Normalize every supported coefficient family in a configuration tree.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and ``coe``.
    output_dir : Path
        Destination directory for CSV files.
    extracted_at : str
        ISO 8601 UTC timestamp recorded in every entry.

    Returns
    -------
    NormalizationResult
        Assets, unsupported families, and the validated manifest entries.
    """
    catalog = build_key_catalog(config_dir)
    families = {item.family: item for item in catalog.families}
    coe_dir = config_dir / "coe"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: list[NormalizedAsset] = []
    unsupported: list[UnsupportedFamily] = []
    manifest: list[dict[str, object]] = []
    for path in sorted(coe_dir.iterdir(), key=lambda item: item.stem.lower()):
        if not path.is_file() or path.suffix.lower() != ".coe":
            continue
        family = path.stem.lower()
        reason = UNSUPPORTED_FAMILIES.get(family)
        if reason is not None:
            unsupported.append(UnsupportedFamily(family, f"VDYP_CFG/coe/{path.name}", reason))
            continue
        table = parse_coe_file(path, source_file=f"VDYP_CFG/coe/{path.name}")
        keys = families[family]
        sequence = keys.control_sequences[0] if keys.control_sequences else ""
        asset, entry = normalize_table(
            table,
            path,
            output_dir,
            extracted_at=extracted_at,
            equation_family=keys.equation_family,
            control_sequence=sequence,
        )
        assets.append(asset)
        manifest.append(entry)
    return NormalizationResult(
        assets=tuple(assets),
        unsupported=tuple(unsupported),
        manifest=tuple(manifest),
    )


def write_manifest(result: NormalizationResult, output_dir: Path) -> None:
    """Write the manifest and a summary to an output directory.

    Parameters
    ----------
    result : NormalizationResult
        Result to serialize.
    output_dir : Path
        Directory for ``manifest.json`` and ``summary.json``.

    Returns
    -------
    None
        The two JSON files are written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_text = json.dumps(list(result.manifest), indent=2) + "\n"
    (output_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
    summary_text = json.dumps(result.to_dict(), indent=2) + "\n"
    (output_dir / "summary.json").write_text(summary_text, encoding="utf-8")


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
    """Normalize a coefficient bundle from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the CSV files and manifest are written, and ``2`` on a
        missing directory or a parse failure.
    """
    parser = argparse.ArgumentParser(description="Normalize VDYP7 coefficient tables to CSV.")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"destination directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--extracted-at",
        default=None,
        help="ISO 8601 UTC timestamp; defaults to now",
    )
    args = parser.parse_args(argv)
    config_dir: Path | None = (
        args.config_dir if args.config_dir is not None else config_from_environment()
    )
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    extracted_at: str = args.extracted_at if args.extracted_at is not None else utc_now()
    try:
        result = build_normalized_catalog(config_dir, args.output_dir, extracted_at=extracted_at)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_manifest(result, args.output_dir)
    payload = result.to_dict()
    print(
        f"Wrote {payload['asset_count']} CSV files and manifest entries "
        f"with {payload['row_count']} rows"
    )
    print(f"Unsupported families: {payload['unsupported_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
