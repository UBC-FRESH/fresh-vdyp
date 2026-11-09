#!/usr/bin/env python3
"""Infer join keys for VDYP7 coefficient rows.

The catalog records, for every parsed family, the equation family, the control
sequences that reference it, and the key columns available on each row. Species
and BEC text keys are validated against ``SP0.DAT`` and ``BEC0.DAT``. A row with
no key column is marked ``unmapped`` with a reason rather than given a guessed
key.

Command-line usage::

    python scripts/key_inference.py --config-dir "$VDYP_CFG_DIR" \
        --output notes/reference/vdyp-key-catalog.json
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

from coe_parser import UNSUPPORTED_FAMILIES, CoeRow, CoeTable, parse_coe_file, schema_for
from config_parser import parse_dat_file
from vdyp_map import ControlMap, build_control_map

RowStatus = Literal["mapped", "invalid", "unmapped"]
FamilyStatus = Literal["mapped", "partial", "unmapped", "invalid", "unsupported"]

EQUATION_FAMILIES: Final[dict[str, str]] = {
    "bafip16": "fip_helper",
    "basp05": "ba_growth_species",
    "basp06": "ba_growth_species",
    "complim": "species_limits",
    "dqfip16z": "fip_helper",
    "dqsp05": "dq_growth_species",
    "dqsp06": "dq_growth_species",
    "gb01": "growth_curve_helper",
    "gd19": "growth_curve_helper",
    "gd20": "growth_curve_helper",
    "gd23": "growth_curve_helper",
    "growba11": "ba_growth_empirical",
    "growba27": "ba_growth_empirical",
    "pct_40": "upper_bounds",
    "pct_407": "upper_bounds",
    "regba25": "ba_increment",
    "regbav01": "ba_adjustment",
    "regbreak": "breakage",
    "regdq18": "dq_increment",
    "regdq24": "dq_increment",
    "regdq26": "dq_increment",
    "regdqi04": "dq_increment",
    "regdql2": "dq_limits",
    "reghl": "height",
    "regvcu": "close_utilization_volume",
    "regvdu": "decay_volume",
    "regvu": "utilization_volume",
    "regvwu": "decay_waste_volume",
    "regyhlp": "height_primary",
    "regyhlpa": "height_primary",
    "regyhlpc": "height_primary",
    "top309": "top_height",
    "top98": "top_height",
    "upperb02": "upper_bounds",
    "vtotreg4": "whole_stem_volume",
    "yldba309": "ba_yield",
    "yldba405": "ba_yield",
    "yldba407": "ba_yield",
    "ylddq309": "dq_yield",
    "ylddq45": "dq_yield",
}
KEY_COLUMNS: Final[frozenset[str]] = frozenset(
    {"species", "species_2", "bec", "coastal_interior", "group", "curve", "label", "flag"}
)
BEC_ALIASES: Final[frozenset[str]] = frozenset({"BG"})


@dataclass(frozen=True)
class LookupSets:
    """The valid species and BEC vocabularies.

    Attributes
    ----------
    species : frozenset of str
        Species codes from ``SP0.DAT``.
    bec : frozenset of str
        BEC zone codes from ``BEC0.DAT``.
    bec_aliases : frozenset of str
        Aggregate codes that appear in increment files but not in ``BEC0.DAT``,
        currently ``BG``.
    """

    species: frozenset[str]
    bec: frozenset[str]
    bec_aliases: frozenset[str] = BEC_ALIASES


@dataclass(frozen=True)
class KeyValue:
    """One inferred key value on a coefficient row.

    Attributes
    ----------
    name : str
        Key name, such as ``species`` or ``group``.
    value : str or int
        Key value.
    source_column : str
        Source column that supplied the value.
    """

    name: str
    value: str | int
    source_column: str

    def to_dict(self) -> dict[str, object]:
        """Render the key as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The key name, value, and source column.
        """
        return {"name": self.name, "value": self.value, "source_column": self.source_column}


@dataclass(frozen=True)
class RowKeys:
    """The inferred keys for one coefficient row.

    Attributes
    ----------
    line_number : int
        One-based source line.
    keys : tuple of KeyValue
        Inferred keys.
    status : {"mapped", "invalid", "unmapped"}
        Whether the row has valid keys, invalid lookup values, or no key columns.
    reason : str
        Explanation for ``invalid`` or ``unmapped``, empty otherwise.
    """

    line_number: int
    keys: tuple[KeyValue, ...]
    status: RowStatus
    reason: str


@dataclass(frozen=True)
class FamilyKeys:
    """The key summary of one ``.COE`` family.

    Attributes
    ----------
    family : str
        Lowercase family name.
    equation_family : str
        Equation-family label, or ``unmapped``.
    control_sequences : tuple of str
        Control sequences that reference the file.
    columns : tuple of str
        Source columns.
    row_count : int
        Parsed rows.
    mapped_rows : int
        Rows with valid keys.
    invalid_rows : int
        Rows with a species or BEC value outside the lookup.
    unmapped_rows : int
        Rows with no key column.
    status : {"mapped", "partial", "unmapped", "invalid", "unsupported"}
        Family-level rollup.
    reason : str
        Explanation for an unsupported or unmapped family, empty otherwise.
    """

    family: str
    equation_family: str
    control_sequences: tuple[str, ...]
    columns: tuple[str, ...]
    row_count: int
    mapped_rows: int
    invalid_rows: int
    unmapped_rows: int
    status: FamilyStatus
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Render the family as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The family, equation family, sequences, counts, and status.
        """
        return {
            "family": self.family,
            "equation_family": self.equation_family,
            "control_sequences": list(self.control_sequences),
            "columns": list(self.columns),
            "row_count": self.row_count,
            "mapped_rows": self.mapped_rows,
            "invalid_rows": self.invalid_rows,
            "unmapped_rows": self.unmapped_rows,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class KeyCatalog:
    """The inferred key catalog for a configuration tree.

    Attributes
    ----------
    lookups : LookupSets
        Species and BEC vocabularies used for validation.
    families : tuple of FamilyKeys
        One entry per ``.COE`` family.
    """

    lookups: LookupSets
    families: tuple[FamilyKeys, ...]

    def to_dict(self) -> dict[str, object]:
        """Render the catalog as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Lookup vocabularies, totals, and one entry per family.
        """
        status_counts: dict[str, int] = {}
        for family in self.families:
            status_counts[family.status] = status_counts.get(family.status, 0) + 1
        return {
            "lookups": {
                "species": sorted(self.lookups.species),
                "bec": sorted(self.lookups.bec),
                "bec_aliases": sorted(self.lookups.bec_aliases),
            },
            "family_count": len(self.families),
            "row_count": sum(family.row_count for family in self.families),
            "status_counts": status_counts,
            "families": [family.to_dict() for family in self.families],
        }


def load_lookup_sets(coe_dir: Path) -> LookupSets:
    """Load the species and BEC vocabularies from the lookup files.

    Parameters
    ----------
    coe_dir : Path
        Directory that contains ``SP0.DAT`` and ``BEC0.DAT``.

    Returns
    -------
    LookupSets
        The valid code sets.

    Raises
    ------
    FileNotFoundError
        When either lookup file is missing.
    """
    by_stem = {path.stem.lower(): path for path in coe_dir.iterdir() if path.is_file()}
    species = parse_dat_file(by_stem["sp0"], source_file="VDYP_CFG/coe/SP0.DAT")
    bec = parse_dat_file(by_stem["bec0"], source_file="VDYP_CFG/coe/BEC0.DAT")
    return LookupSets(
        species=frozenset(record.tokens[0] for record in species.records if record.tokens),
        bec=frozenset(record.tokens[0] for record in bec.records if record.tokens),
    )


def keys_for_row(table: CoeTable, row: CoeRow, lookups: LookupSets) -> RowKeys:
    """Infer and validate the keys of one coefficient row.

    Parameters
    ----------
    table : CoeTable
        Parsed table that owns the row.
    row : CoeRow
        Row to inspect.
    lookups : LookupSets
        Valid species and BEC vocabularies.

    Returns
    -------
    RowKeys
        The keys and a status. A species or BEC value outside the lookup makes
        the row ``invalid``; a row with no key columns is ``unmapped``.
    """
    schema = schema_for(table.family)
    keys: list[KeyValue] = []
    invalid: list[str] = []
    for column, kind, value in zip(schema.columns, schema.kinds, row.values, strict=True):
        if column not in KEY_COLUMNS:
            continue
        if column in {"species", "species_2"}:
            if kind == "text":
                text = str(value)
                if text not in lookups.species:
                    invalid.append(f"{column} {text!r} is not in SP0.DAT")
                keys.append(KeyValue(column, text, column))
            else:
                keys.append(KeyValue("species_index", int(value), column))
            continue
        if column == "bec":
            if kind == "text":
                text = str(value)
                if text not in lookups.bec and text not in lookups.bec_aliases:
                    invalid.append(f"bec {text!r} is not in BEC0.DAT")
                keys.append(KeyValue("bec", text, column))
            else:
                keys.append(KeyValue("bec_index", int(value), column))
            continue
        if kind == "text":
            keys.append(KeyValue(column, str(value), column))
        else:
            keys.append(KeyValue(column, int(value), column))
    if invalid:
        return RowKeys(row.line_number, tuple(keys), "invalid", "; ".join(invalid))
    if not keys:
        return RowKeys(row.line_number, (), "unmapped", "no key columns in schema")
    return RowKeys(row.line_number, tuple(keys), "mapped", "")


def build_catalog(config_dir: Path, *, control_map: ControlMap | None = None) -> KeyCatalog:
    """Build the key catalog for a configuration tree.

    Parameters
    ----------
    config_dir : Path
        Directory that contains the control files and ``coe``.
    control_map : ControlMap or None, optional
        Pre-built control map. When omitted, it is built from the configuration
        and install root.

    Returns
    -------
    KeyCatalog
        The validated key catalog.

    Raises
    ------
    NotADirectoryError
        When the configuration or coefficient directory is missing.
    """
    coe_dir = config_dir / "coe"
    if not coe_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {coe_dir}")
    mapping = control_map or build_control_map(config_dir.parent, config_dir)
    sequences: dict[str, list[str]] = {}
    for entry in mapping.entries:
        if entry.status != "resolved" or entry.resolved_path is None:
            continue
        name = Path(entry.resolved_path).name.lower()
        sequences.setdefault(name, [])
        if entry.sequence_id not in sequences[name]:
            sequences[name].append(entry.sequence_id)
    lookups = load_lookup_sets(coe_dir)
    families: list[FamilyKeys] = []
    for path in sorted(coe_dir.iterdir(), key=lambda item: item.stem.lower()):
        if not path.is_file() or path.suffix.lower() != ".coe":
            continue
        family = path.stem.lower()
        equation_family = EQUATION_FAMILIES.get(family, "unmapped")
        reason = UNSUPPORTED_FAMILIES.get(family)
        if reason is not None:
            families.append(
                FamilyKeys(
                    family,
                    equation_family,
                    tuple(sequences.get(path.name.lower(), [])),
                    (),
                    0,
                    0,
                    0,
                    0,
                    "unsupported",
                    reason,
                )
            )
            continue
        table = parse_coe_file(path, source_file=f"VDYP_CFG/coe/{path.name}")
        results = [keys_for_row(table, row, lookups) for row in table.rows]
        mapped = sum(1 for item in results if item.status == "mapped")
        invalid = sum(1 for item in results if item.status == "invalid")
        unmapped = sum(1 for item in results if item.status == "unmapped")
        if invalid:
            status: FamilyStatus = "invalid"
            family_reason = "one or more rows have species or BEC values outside the lookup"
        elif mapped and unmapped:
            status = "partial"
            family_reason = "some rows have no key columns"
        elif mapped:
            status = "mapped"
            family_reason = ""
        else:
            status = "unmapped"
            family_reason = "no rows have key columns"
        families.append(
            FamilyKeys(
                family,
                equation_family,
                tuple(sequences.get(path.name.lower(), [])),
                table.columns,
                len(table.rows),
                mapped,
                invalid,
                unmapped,
                status,
                family_reason,
            )
        )
    return KeyCatalog(lookups=lookups, families=tuple(families))


def write_catalog(catalog: KeyCatalog, output: Path) -> None:
    """Write a key catalog as pretty JSON.

    Parameters
    ----------
    catalog : KeyCatalog
        Catalog to serialize.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The catalog is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog.to_dict(), indent=2) + "\n", encoding="utf-8")


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
    """Build the key catalog from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the catalog is written, and ``2`` on a missing directory or
        a parse failure.
    """
    parser = argparse.ArgumentParser(description="Infer VDYP7 coefficient keys.")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument("--output", type=Path, required=True, help="catalog path to write")
    args = parser.parse_args(argv)
    config_dir: Path | None = (
        args.config_dir if args.config_dir is not None else config_from_environment()
    )
    if config_dir is None:
        print("error: pass --config-dir or set VDYP_CFG_DIR", file=sys.stderr)
        return 2
    try:
        catalog = build_catalog(config_dir)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_catalog(catalog, args.output)
    payload = catalog.to_dict()
    print(f"Wrote {payload['family_count']} families with {payload['row_count']} rows")
    print(f"Status counts: {payload['status_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
