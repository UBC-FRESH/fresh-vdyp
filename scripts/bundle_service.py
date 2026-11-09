#!/usr/bin/env python3
"""Service layer for the first ``fresh-vdyp`` bundle commands.

The service keeps validation, catalog inspection, and extraction out of the CLI
so the commands share one typed implementation. Every result names the source
model and the source files behind it.

Command-line usage is through ``scripts/fvdyp_cli.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from inventory_vdyp import CITATION
from key_inference import build_catalog as build_key_catalog
from normalize import (
    NormalizationResult,
    build_normalized_catalog,
    write_manifest,
)
from vdyp_map import build_control_map

SOURCE_MODEL: Final[str] = "VDYP7"
REQUIRED_FILES: Final[tuple[str, ...]] = (
    "VDYP.CTR",
    "VDYPBACK.CTR",
    "coe/SP0.DAT",
    "coe/BEC0.DAT",
)


@dataclass(frozen=True)
class BundleDiagnostic:
    """One finding from bundle validation.

    Attributes
    ----------
    severity : {"error", "warning"}
        Whether the finding blocks a valid bundle.
    code : str
        Stable finding code, such as ``MISSING-FILE``.
    message : str
        Explanation of the finding.
    """

    severity: Literal["error", "warning"]
    code: str
    message: str

    def render(self) -> str:
        """Render the finding as one line of text.

        Returns
        -------
        str
            Severity, code, and message, padded into columns.
        """
        return f"{self.severity:<8}{self.code:<20}{self.message}"


def _find_entry(directory: Path, name: str) -> Path | None:
    """Find a file or directory by name, ignoring case.

    Parameters
    ----------
    directory : Path
        Directory to search.
    name : str
        Name to match, case-insensitively.

    Returns
    -------
    Path or None
        The matching entry, or ``None`` when it is absent.
    """
    target = name.lower()
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if path.name.lower() == target:
            return path
    return None


def find_ci(directory: Path, name: str) -> Path | None:
    """Find a file by name, ignoring case.

    Parameters
    ----------
    directory : Path
        Directory to search.
    name : str
        File name to match, case-insensitively.

    Returns
    -------
    Path or None
        The matching file, or ``None`` when it is absent or is a directory.
    """
    path = _find_entry(directory, name)
    return path if path is not None and path.is_file() else None


def required_path(config_dir: Path, relative: str) -> Path | None:
    """Resolve a required configuration file by relative name.

    Parameters
    ----------
    config_dir : Path
        Configuration root.
    relative : str
        Relative name, such as ``coe/SP0.DAT``.

    Returns
    -------
    Path or None
        The file when present, otherwise ``None``.
    """
    parts = relative.split("/")
    current = config_dir
    for part in parts[:-1]:
        entry = _find_entry(current, part)
        if entry is None or not entry.is_dir():
            return None
        current = entry
    return find_ci(current, parts[-1])


def validate_bundle(config_dir: Path) -> tuple[BundleDiagnostic, ...]:
    """Validate the bundle structure, control map, and key catalog.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and ``coe``.

    Returns
    -------
    tuple of BundleDiagnostic
        Errors and warnings. An empty tuple means the bundle is valid.
    """
    findings: list[BundleDiagnostic] = []
    if not config_dir.is_dir():
        return (BundleDiagnostic("error", "MISSING-DIR", "configuration directory does not exist"),)
    for relative in REQUIRED_FILES:
        if required_path(config_dir, relative) is None:
            findings.append(
                BundleDiagnostic("error", "MISSING-FILE", f"required file is missing: {relative}")
            )
    if findings:
        return tuple(findings)
    control_map = build_control_map(config_dir.parent, config_dir)
    for entry in control_map.entries:
        if entry.status == "missing":
            findings.append(
                BundleDiagnostic(
                    "error",
                    "MISSING-TARGET",
                    f"{entry.control_file} sequence {entry.sequence_id} "
                    f"targets a missing file: {entry.value}",
                )
            )
    catalog = build_key_catalog(config_dir, control_map=control_map)
    for family in catalog.families:
        if family.status == "invalid":
            findings.append(
                BundleDiagnostic(
                    "error",
                    "INVALID-KEYS",
                    f"{family.family}: {family.reason}",
                )
            )
        elif family.status == "unsupported":
            findings.append(
                BundleDiagnostic(
                    "warning",
                    "UNSUPPORTED-FAMILY",
                    f"{family.family}: {family.reason}",
                )
            )
    return tuple(findings)


def catalog_payload(config_dir: Path) -> dict[str, object]:
    """Build the read-only catalog summary for a bundle.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and ``coe``.

    Returns
    -------
    dict of str to object
        Source model, citation, lookups, counts, and one entry per family.
    """
    catalog = build_key_catalog(config_dir)
    payload = catalog.to_dict()
    return {
        "source_model": SOURCE_MODEL,
        "citation": CITATION,
        "lookups": payload["lookups"],
        "family_count": payload["family_count"],
        "row_count": payload["row_count"],
        "status_counts": payload["status_counts"],
        "families": payload["families"],
    }


def extract_bundle(
    config_dir: Path,
    output_dir: Path,
    *,
    extracted_at: str,
) -> NormalizationResult:
    """Normalize a bundle and write its CSV files, manifest, and summary.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and ``coe``.
    output_dir : Path
        Destination directory for ``.csv``, ``manifest.json``, and
        ``summary.json``.
    extracted_at : str
        ISO 8601 UTC timestamp recorded in every manifest entry.

    Returns
    -------
    NormalizationResult
        The normalized assets, unsupported families, and manifest entries.
    """
    result = build_normalized_catalog(config_dir, output_dir, extracted_at=extracted_at)
    write_manifest(result, output_dir)
    return result
