#!/usr/bin/env python3
"""Join VDYP7 control sequences to the files in an installation.

The map resolves each path-like control value case-insensitively against the
install tree, classifies the result, and reports the bundle files that no
sequence references. It distinguishes resolved bundle files from runtime
input/output names, external paths, missing coefficient targets, empty
nullifications, and non-file parameters.

Command-line usage::

    python scripts/vdyp_map.py --install-root "$VDYP_INSTALL" \
        --config-dir "$VDYP_CFG_DIR" --output notes/reference/vdyp-control-map.json
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

from inventory_vdyp import classify, iter_files
from vdyp_control import CONTROL_FILES, load_control_file

MapStatus = Literal["resolved", "runtime", "external", "missing", "not_a_file", "empty"]

BUNDLE_SUFFIXES: Final[frozenset[str]] = frozenset({".coe", ".prm", ".dat"})
BUNDLE_PREFIX: Final[str] = "vdyp_cfg/coe/"


@dataclass(frozen=True)
class MappedEntry:
    """One control entry joined to the install tree.

    Attributes
    ----------
    control_file : str
        Repository-relative control file that supplied the entry.
    sequence_id : str
        Three-character sequence number.
    value : str
        Raw value from columns 5-54.
    description : str
        Description text from the control file.
    status : str
        One of ``resolved``, ``runtime``, ``external``, ``missing``,
        ``not_a_file``, or ``empty``.
    resolved_path : str or None
        Install-relative path when the status is ``resolved``.
    kind : str or None
        File kind from :func:`inventory_vdyp.classify` when resolved.
    """

    control_file: str
    sequence_id: str
    value: str
    description: str
    status: MapStatus
    resolved_path: str | None
    kind: str | None

    def to_dict(self) -> dict[str, object]:
        """Render the entry as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The joined entry fields.
        """
        return {
            "control_file": self.control_file,
            "sequence": self.sequence_id,
            "value": self.value,
            "description": self.description,
            "status": self.status,
            "resolved_path": self.resolved_path,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ControlMap:
    """The joined control map for one installation.

    Attributes
    ----------
    control_files : tuple of str
        Repository-relative control files that were read.
    entries : tuple of MappedEntry
        Joined entries in control-file order.
    unreferenced_bundle_files : tuple of str
        Files under ``VDYP_CFG/coe`` that no resolved entry references.
    """

    control_files: tuple[str, ...]
    entries: tuple[MappedEntry, ...]
    unreferenced_bundle_files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the map as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Counts, missing targets, unreferenced files, and entries.
        """
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.status] = counts.get(entry.status, 0) + 1
        missing = [
            {
                "control_file": entry.control_file,
                "sequence": entry.sequence_id,
                "value": entry.value,
            }
            for entry in self.entries
            if entry.status == "missing"
        ]
        return {
            "control_files": list(self.control_files),
            "entry_count": len(self.entries),
            "counts": counts,
            "missing_targets": missing,
            "unreferenced_bundle_files": list(self.unreferenced_bundle_files),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def looks_like_file(value: str) -> bool:
    """Report whether a control value looks like a file path.

    Parameters
    ----------
    value : str
        Raw value from columns 5-54.

    Returns
    -------
    bool
        ``True`` when the value has a path separator or a suffix and contains a
        letter. Purely numeric parameters return ``False``.
    """
    has_separator = "\\" in value or "/" in value
    has_suffix = "." in value
    return (has_separator or has_suffix) and any(character.isalpha() for character in value)


def resolve_target(value: str, index: dict[str, str]) -> str | None:
    """Resolve a control value against a case-insensitive install index.

    Parameters
    ----------
    value : str
        Raw value from columns 5-54.
    index : dict of str to str
        Lowercase install-relative path to original-case path.

    Returns
    -------
    str or None
        The original-case relative path, or ``None`` when no candidate exists.
    """
    normalized = value.replace("\\", "/").lstrip("/")
    candidates = [normalized]
    if normalized.lower().startswith("coe/"):
        candidates.append(f"VDYP_CFG/{normalized}")
    else:
        candidates.append(f"VDYP_CFG/{normalized}")
        candidates.append(f"VDYP_CFG/coe/{normalized}")
    for candidate in candidates:
        found = index.get(candidate.lower())
        if found is not None:
            return found
    return None


def classify_target(value: str, resolved: str | None) -> MapStatus:
    """Classify one control target after resolution.

    Parameters
    ----------
    value : str
        Raw value from columns 5-54.
    resolved : str or None
        Resolved relative path, or ``None``.

    Returns
    -------
    {"resolved", "runtime", "external", "missing", "not_a_file", "empty"}
        The join status.
    """
    if not value:
        return "empty"
    if not looks_like_file(value):
        return "not_a_file"
    if resolved is not None:
        return "resolved"
    if value.startswith(("\\", "/")):
        return "external"
    normalized = value.replace("\\", "/").lstrip("/")
    if normalized.lower().startswith("coe/"):
        return "missing"
    return "runtime"


def build_control_map(install_root: Path, config_dir: Path) -> ControlMap:
    """Join every control entry to the install tree.

    Parameters
    ----------
    install_root : Path
        VDYP7 installation root.
    config_dir : Path
        Directory that contains the control files.

    Returns
    -------
    ControlMap
        Joined entries and the unreferenced coefficient, parameter, and data
        files under ``VDYP_CFG/coe``.

    Raises
    ------
    NotADirectoryError
        When the install root is not a directory.
    """
    if not install_root.is_dir():
        raise NotADirectoryError(f"not a directory: {install_root}")
    index: dict[str, str] = {}
    for path in iter_files(install_root):
        relative = path.relative_to(install_root).as_posix()
        index[relative.lower()] = relative
    entries: list[MappedEntry] = []
    referenced: set[str] = set()
    control_labels: list[str] = []
    for name in CONTROL_FILES:
        label = f"VDYP_CFG/{name}"
        control_labels.append(label)
        parsed = load_control_file(config_dir / name, source_file=label)
        for entry in parsed.entries:
            resolved = resolve_target(entry.value, index)
            status = classify_target(entry.value, resolved)
            if resolved is not None:
                referenced.add(resolved.lower())
            entries.append(
                MappedEntry(
                    control_file=label,
                    sequence_id=entry.sequence,
                    value=entry.value,
                    description=entry.description,
                    status=status,
                    resolved_path=resolved,
                    kind=classify(Path(resolved)) if resolved is not None else None,
                )
            )
    unreferenced = sorted(
        relative
        for key, relative in index.items()
        if key.startswith(BUNDLE_PREFIX)
        and Path(relative).suffix.lower() in BUNDLE_SUFFIXES
        and key not in referenced
    )
    return ControlMap(
        control_files=tuple(control_labels),
        entries=tuple(entries),
        unreferenced_bundle_files=tuple(unreferenced),
    )


def write_map(control_map: ControlMap, output: Path) -> None:
    """Write a control map as pretty JSON.

    Parameters
    ----------
    control_map : ControlMap
        Map to serialize.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The map is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(control_map.to_dict(), indent=2) + "\n", encoding="utf-8")


def roots_from_environment() -> tuple[Path | None, Path | None]:
    """Resolve the install root and config directory from the environment.

    Returns
    -------
    tuple of (Path or None, Path or None)
        ``VDYP_INSTALL`` and ``VDYP_CFG_DIR`` values when set and non-empty.
    """
    install = os.environ.get("VDYP_INSTALL")
    config = os.environ.get("VDYP_CFG_DIR")
    return (Path(install) if install else None, Path(config) if config else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Build a control map from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the map is written, and ``2`` when a root is missing or
        unreadable.
    """
    parser = argparse.ArgumentParser(description="Join VDYP7 control sequences to bundle files.")
    parser.add_argument("--install-root", type=Path, help="install root; defaults to VDYP_INSTALL")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument("--output", type=Path, required=True, help="map path to write")
    args = parser.parse_args(argv)
    env_install, env_config = roots_from_environment()
    install_root = args.install_root if args.install_root is not None else env_install
    config_dir = args.config_dir if args.config_dir is not None else env_config
    if config_dir is None and install_root is not None:
        config_dir = install_root / "VDYP_CFG"
    if config_dir is None or install_root is None:
        print("error: pass --install-root and --config-dir, or set both env vars", file=sys.stderr)
        return 2
    try:
        control_map = build_control_map(install_root, config_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_map(control_map, args.output)
    counts = control_map.to_dict()["counts"]
    entry_count = len(control_map.entries)
    unreferenced_count = len(control_map.unreferenced_bundle_files)
    print(f"Wrote {entry_count} entries and {unreferenced_count} unreferenced bundle files")
    print(f"Counts: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
