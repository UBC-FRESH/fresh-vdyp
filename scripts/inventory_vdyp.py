#!/usr/bin/env python3
"""Inventory a local VDYP7 installation as a deterministic JSON manifest.

The manifest records every regular file under an installation root by relative
path, size, SHA256, and a coarse kind. It never records an absolute path, so the
manifest can be committed without publishing a machine-specific location.

Command-line usage::

    python scripts/inventory_vdyp.py --root "$VDYP_INSTALL" --output out.json

``--root`` defaults to ``VDYP_INSTALL``, then to the parent of ``VDYP_CFG_DIR``.
The output is byte-identical for the same tree, so a diff shows a real change in
the source bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

Kind = Literal[
    "binary",
    "control",
    "coefficient",
    "parameter",
    "data",
    "sample",
    "document",
    "archive",
    "database",
    "source",
    "other",
]

SCHEMA_VERSION: Final[int] = 1
SOURCE_MODEL: Final[str] = "VDYP7"
DEFAULT_SOURCE_VERSION: Final[str] = "7"
CITATION: Final[str] = "Province of British Columbia. VDYP7 coefficient and control bundle."
CHUNK_SIZE: Final[int] = 1 << 20
SLUG_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")
BINARY_SUFFIXES: Final[frozenset[str]] = frozenset({".exe", ".dll", ".lib", ".exp"})
CONTROL_SUFFIXES: Final[frozenset[str]] = frozenset({".ctr", ".tcl", ".ini"})
DOCUMENT_SUFFIXES: Final[frozenset[str]] = frozenset({".md", ".txt", ".doc", ".avi"})
SOURCE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".c", ".h", ".cpp", ".for", ".f", ".py", ".cmd", ".bat", ".sh", ".sql", ".bas", ".load"}
)


@dataclass(frozen=True)
class FileRecord:
    """One inventory entry for a regular file in the source bundle.

    Attributes
    ----------
    id : str
        Stable identifier derived from the relative path.
    kind : str
        Coarse classification of the file; see :func:`classify` for the values.
    relative_path : str
        Path from the install root, with forward slashes.
    size_bytes : int
        File size in bytes.
    sha256 : str
        Lowercase hexadecimal SHA256 of the file contents.
    """

    id: str
    kind: Kind
    relative_path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        """Render the record as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The record fields under their manifest names.
        """
        return {
            "id": self.id,
            "kind": self.kind,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class BundleManifest:
    """A deterministic inventory of one VDYP7 installation.

    Attributes
    ----------
    schema_version : int
        Manifest schema version.
    source_model : str
        Source model name, always ``"VDYP7"``.
    source_version : str
        Source model version label supplied by the caller.
    citation : str
        Citation required for every published value derived from the bundle.
    file_count : int
        Number of files in ``files``.
    total_bytes : int
        Sum of the file sizes.
    files : tuple of FileRecord
        One record per file, sorted by relative path.
    """

    schema_version: int
    source_model: str
    source_version: str
    citation: str
    file_count: int
    total_bytes: int
    files: tuple[FileRecord, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the manifest as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The manifest header and the list of file records.
        """
        return {
            "schema_version": self.schema_version,
            "source_model": self.source_model,
            "source_version": self.source_version,
            "citation": self.citation,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "files": [record.to_dict() for record in self.files],
        }


def sha256_file(path: Path) -> str:
    """Hash one file without loading it all into memory.

    Parameters
    ----------
    path : Path
        File to hash.

    Returns
    -------
    str
        Lowercase hexadecimal SHA256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative_path: Path) -> Kind:
    """Classify one bundle file from its relative path.

    Sample-data paths win over the extension, so a sample ``.DAT`` is reported
    as a sample rather than as a coefficient data table.

    Parameters
    ----------
    relative_path : Path
        Path relative to the install root.

    Returns
    -------
    str
        The coarse file kind; see the ``Kind`` alias for the allowed values.
    """
    parts = [part.lower() for part in relative_path.parts]
    suffix = relative_path.suffix.lower()
    name = relative_path.name.lower()
    if "sampledata" in parts:
        return "sample"
    if suffix == ".coe":
        return "coefficient"
    if suffix == ".prm":
        return "parameter"
    if suffix in {".dat", ".csv"}:
        return "data"
    if suffix in CONTROL_SUFFIXES or name == "vdyp7loggingconfig.txt":
        return "control"
    if suffix in BINARY_SUFFIXES:
        return "binary"
    if suffix in DOCUMENT_SUFFIXES:
        return "document"
    if suffix == ".zip":
        return "archive"
    if suffix == ".mdb":
        return "database"
    if suffix in SOURCE_SUFFIXES:
        return "source"
    return "other"


def slugify(text: str) -> str:
    """Turn a relative path into a lowercase identifier fragment.

    Parameters
    ----------
    text : str
        Text to normalize, normally a relative path.

    Returns
    -------
    str
        Lowercase words joined by single hyphens. ``"file"`` when nothing else
        remains.
    """
    slug = SLUG_PATTERN.sub("-", text.lower()).strip("-")
    return slug or "file"


def iter_files(root: Path) -> list[Path]:
    """List the regular, non-symlink files under a root in stable order.

    Parameters
    ----------
    root : Path
        Directory to walk.

    Returns
    -------
    list of Path
        Absolute paths, sorted by lowercase relative path so that the result is
        stable across platforms.
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort(key=str.lower)
        current = Path(dirpath)
        for name in sorted(filenames, key=str.lower):
            path = current / name
            if path.is_file() and not path.is_symlink():
                found.append(path)
    return sorted(found, key=lambda path: path.relative_to(root).as_posix().lower())


def build_manifest(root: Path, *, source_version: str = DEFAULT_SOURCE_VERSION) -> BundleManifest:
    """Inventory one installation root.

    Parameters
    ----------
    root : Path
        VDYP7 installation root.
    source_version : str, optional
        Source version label recorded in the manifest.

    Returns
    -------
    BundleManifest
        The header and one record per regular file.

    Raises
    ------
    NotADirectoryError
        When ``root`` is not a directory.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    records: list[FileRecord] = []
    used_ids: dict[str, int] = {}
    total_bytes = 0
    for path in iter_files(root):
        relative = path.relative_to(root)
        base_id = f"vdyp-{slugify(relative.as_posix())}"
        count = used_ids.get(base_id, 0) + 1
        used_ids[base_id] = count
        identifier = base_id if count == 1 else f"{base_id}-{count}"
        size = path.stat().st_size
        total_bytes += size
        records.append(
            FileRecord(
                id=identifier,
                kind=classify(relative),
                relative_path=relative.as_posix(),
                size_bytes=size,
                sha256=sha256_file(path),
            )
        )
    return BundleManifest(
        schema_version=SCHEMA_VERSION,
        source_model=SOURCE_MODEL,
        source_version=source_version,
        citation=CITATION,
        file_count=len(records),
        total_bytes=total_bytes,
        files=tuple(records),
    )


def write_manifest(manifest: BundleManifest, output: Path) -> None:
    """Write a manifest as pretty JSON with a trailing newline.

    Parameters
    ----------
    manifest : BundleManifest
        Manifest to serialize.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The manifest is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")


def root_from_environment() -> Path | None:
    """Resolve an install root from the documented environment variables.

    Returns
    -------
    Path or None
        ``VDYP_INSTALL`` when set and non-empty, then the parent of
        ``VDYP_CFG_DIR``, otherwise ``None``.
    """
    install = os.environ.get("VDYP_INSTALL")
    if install:
        return Path(install)
    config = os.environ.get("VDYP_CFG_DIR")
    if config:
        return Path(config).parent
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Inventory an installation from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the manifest is written, and ``2`` when the root is missing
        or not a directory.
    """
    parser = argparse.ArgumentParser(description="Inventory a VDYP7 installation.")
    parser.add_argument("--root", type=Path, help="install root; defaults to VDYP_INSTALL")
    parser.add_argument("--output", type=Path, required=True, help="manifest path to write")
    parser.add_argument(
        "--source-version",
        default=DEFAULT_SOURCE_VERSION,
        help=f"source version label (default: {DEFAULT_SOURCE_VERSION})",
    )
    args = parser.parse_args(argv)
    root: Path | None = args.root if args.root is not None else root_from_environment()
    if root is None:
        print("error: pass --root or set VDYP_INSTALL", file=sys.stderr)
        return 2
    try:
        manifest = build_manifest(root, source_version=args.source_version)
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_manifest(manifest, args.output)
    print(f"Wrote {manifest.file_count} files ({manifest.total_bytes} bytes) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
