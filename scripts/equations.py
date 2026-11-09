#!/usr/bin/env python3
"""Validated VDYP7 equation families.

The first family is whole-stem volume from ``VTOTREG4.COE``. The equation and
coefficient order come from the public ``bcgov/nr-vdyp`` source
(``EstimationMethods.estimateWholeStemVolumePerTree``, EMP090, Apache-2.0):

``log(V_per_tree) = b0 + b1*ln(DQ) + b2*ln(HL) + b3*DQ + b4/DQ + b5*HL
+ b6*DQ^2 + b7*HL*DQ + b8*HL/DQ``

Coefficients are loaded from the bundle; nothing is hard-coded. Per-hectare
volume is per-tree volume times TPH. The family is validated on the mature
static path; younger rows return ``experimental``.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from coe_parser import parse_coe_file
from config_parser import parse_dat_file

FamilyStatus = Literal["validated", "experimental", "not_implemented"]
VALIDATED_MIN_AGE: Final[int] = 80
AGE_100_TOLERANCE: Final[float] = 0.01
MATURE_TOLERANCE: Final[float] = 0.03
COEFFICIENT_COUNT: Final[int] = 9


class EquationError(ValueError):
    """Raised when an equation input or coefficient row is invalid."""


@dataclass(frozen=True)
class WholeStemCoefficients:
    """One VTOTREG4 coefficient row.

    Attributes
    ----------
    volume_group : int
        Volume group identifier.
    coefficients : tuple of float
        Nine coefficients in source order.
    source_file : str
        Source label.
    line_number : int
        One-based source line.
    """

    volume_group: int
    coefficients: tuple[float, ...]
    source_file: str
    line_number: int


@dataclass(frozen=True)
class WholeStemEstimate:
    """One whole-stem volume estimate and its family status.

    Attributes
    ----------
    value : float
        Per-hectare whole-stem volume, or ``0.0`` when not implemented.
    status : {"validated", "experimental", "not_implemented"}
        Family status.
    reason : str
        Why the status is not ``validated``, empty otherwise.
    volume_group : int or None
        Resolved volume group, or ``None``.
    """

    value: float
    status: FamilyStatus
    reason: str
    volume_group: int | None


def load_vtotreg4(path: Path) -> dict[int, WholeStemCoefficients]:
    """Load VTOTREG4 coefficients by volume group.

    Parameters
    ----------
    path : Path
        ``VTOTREG4.COE`` file.

    Returns
    -------
    dict of int to WholeStemCoefficients
        One row per volume group.

    Raises
    ------
    EquationError
        When a row does not have nine coefficients.
    """
    table = parse_coe_file(path, source_file="VDYP_CFG/coe/VTOTREG4.COE")
    result: dict[int, WholeStemCoefficients] = {}
    for row in table.rows:
        group = int(row.values[0])
        coefficients = tuple(float(value) for value in row.values[1:])
        if len(coefficients) != COEFFICIENT_COUNT:
            raise EquationError(f"VTOTREG4 group {group} has {len(coefficients)} coefficients")
        result[group] = WholeStemCoefficients(
            group, coefficients, table.source_file, row.line_number
        )
    return result


def load_volume_groups(path: Path) -> dict[tuple[str, str], int]:
    """Load the species/BEC to volume-group map.

    The public source replaces group 10 with 11; this function applies the same
    rule.

    Parameters
    ----------
    path : Path
        ``VGRPDEF1.DAT`` file.

    Returns
    -------
    dict of (str, str) to int
        Keys are upper-case ``(species, BEC)`` pairs.
    """
    table = parse_dat_file(path, source_file="VDYP_CFG/coe/VGRPDEF1.DAT")
    result: dict[tuple[str, str], int] = {}
    for record in table.records:
        if len(record.tokens) < 3:
            continue
        species, bec, raw_group = record.tokens[0], record.tokens[1], record.tokens[2]
        try:
            group = int(raw_group)
        except ValueError:
            continue
        if group == 10:
            group = 11
        result[(species.upper(), bec.upper())] = group
    return result


def whole_stem_volume_per_tree(
    coefficients: Sequence[float],
    lorey_height: float,
    quad_mean_diameter: float,
) -> float:
    """Estimate whole-stem volume per tree.

    Parameters
    ----------
    coefficients : sequence of float
        Nine coefficients in source order.
    lorey_height : float
        Lorey height in metres. Must be positive.
    quad_mean_diameter : float
        Quadratic mean diameter in centimetres. Must be positive.

    Returns
    -------
    float
        Per-tree volume in cubic metres.

    Raises
    ------
    EquationError
        When the coefficient count or an input is invalid.
    """
    if len(coefficients) != COEFFICIENT_COUNT:
        raise EquationError(f"expected {COEFFICIENT_COUNT} coefficients")
    if lorey_height <= 0.0 or quad_mean_diameter <= 0.0:
        raise EquationError("lorey_height and quad_mean_diameter must be positive")
    b = [float(value) for value in coefficients]
    log_volume = (
        b[0]
        + b[1] * math.log(quad_mean_diameter)
        + b[2] * math.log(lorey_height)
        + b[3] * quad_mean_diameter
        + b[4] / quad_mean_diameter
        + b[5] * lorey_height
        + b[6] * quad_mean_diameter * quad_mean_diameter
        + b[7] * lorey_height * quad_mean_diameter
        + b[8] * lorey_height / quad_mean_diameter
    )
    return math.exp(log_volume)


def whole_stem_volume_per_hectare(
    coefficients: Sequence[float],
    *,
    lorey_height: float,
    quad_mean_diameter: float,
    trees_per_hectare: float,
) -> float:
    """Estimate whole-stem volume per hectare.

    Parameters
    ----------
    coefficients : sequence of float
        Nine coefficients in source order.
    lorey_height : float
        Lorey height in metres.
    quad_mean_diameter : float
        Quadratic mean diameter in centimetres.
    trees_per_hectare : float
        Trees per hectare. Must not be negative.

    Returns
    -------
    float
        Per-hectare volume in cubic metres.

    Raises
    ------
    EquationError
        When TPH is negative or another input is invalid.
    """
    if trees_per_hectare < 0.0:
        raise EquationError("trees_per_hectare must not be negative")
    return (
        whole_stem_volume_per_tree(coefficients, lorey_height, quad_mean_diameter)
        * trees_per_hectare
    )


def family_status(age: int) -> FamilyStatus:
    """Return the family status for an age.

    Parameters
    ----------
    age : int
        Total stand age.

    Returns
    -------
    {"validated", "experimental"}
        ``validated`` at age 80 and above; otherwise ``experimental``.
    """
    return "validated" if age >= VALIDATED_MIN_AGE else "experimental"


def estimate_whole_stem_volume(
    coefficients_by_group: Mapping[int, WholeStemCoefficients],
    volume_groups: Mapping[tuple[str, str], int],
    *,
    species: str,
    bec: str,
    lorey_height: float,
    quad_mean_diameter: float,
    trees_per_hectare: float,
    age: int,
) -> WholeStemEstimate:
    """Estimate whole-stem volume with an explicit family status.

    Parameters
    ----------
    coefficients_by_group : mapping of int to WholeStemCoefficients
        Parsed VTOTREG4 rows.
    volume_groups : mapping of (str, str) to int
        Parsed species/BEC volume-group map.
    species : str
        Species code.
    bec : str
        BEC zone code.
    lorey_height : float
        Lorey height in metres.
    quad_mean_diameter : float
        Quadratic mean diameter in centimetres.
    trees_per_hectare : float
        Trees per hectare.
    age : int
        Total stand age.

    Returns
    -------
    WholeStemEstimate
        Value and status. An unknown key or missing row is
        ``not_implemented``; an age below 80 is ``experimental``.
    """
    group = volume_groups.get((species.upper(), bec.upper()))
    if group is None:
        return WholeStemEstimate(
            0.0,
            "not_implemented",
            f"no volume group for species {species!r} and BEC {bec!r}",
            None,
        )
    row = coefficients_by_group.get(group)
    if row is None:
        return WholeStemEstimate(
            0.0,
            "not_implemented",
            f"no VTOTREG4 coefficients for volume group {group}",
            group,
        )
    value = whole_stem_volume_per_hectare(
        row.coefficients,
        lorey_height=lorey_height,
        quad_mean_diameter=quad_mean_diameter,
        trees_per_hectare=trees_per_hectare,
    )
    status = family_status(age)
    reason = "" if status == "validated" else "young-stand path is not validated (age < 80)"
    return WholeStemEstimate(value, status, reason, group)


def validate_against_golden(
    config_dir: Path,
    golden_csv: Path,
    *,
    bec: str = "BWBS",
) -> list[dict[str, object]]:
    """Compare the equation with the console output.

    Parameters
    ----------
    config_dir : Path
        ``VDYP_CFG`` directory with ``coe``.
    golden_csv : Path
        Reproduced ``CSVYieldTable`` output.
    bec : str, optional
        BEC zone of the input case.

    Returns
    -------
    list of dict of str to object
        One row per non-empty console volume with age, console value,
        reimplementation value, relative error, and status.
    """
    coefficients = load_vtotreg4(config_dir / "coe" / "VTOTREG4.COE")
    groups = load_volume_groups(config_dir / "coe" / "VGRPDEF1.DAT")
    rows: list[dict[str, object]] = []
    with golden_csv.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            volume = record.get("PRJ_VOL_WS", "")
            if not volume:
                continue
            age = int(record["PRJ_TOTAL_AGE"])
            estimate = estimate_whole_stem_volume(
                coefficients,
                groups,
                species=record["SPECIES_1_CODE"],
                bec=bec,
                lorey_height=float(record["PRJ_LOREY_HT"]),
                quad_mean_diameter=float(record["PRJ_DIAMETER"]),
                trees_per_hectare=float(record["PRJ_TPH"]),
                age=age,
            )
            console = float(volume)
            error = abs(estimate.value - console) / console if console else 0.0
            rows.append(
                {
                    "age": age,
                    "console": console,
                    "python": estimate.value,
                    "relative_error": error,
                    "status": estimate.status,
                }
            )
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the family from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the age-100 case is within 1 percent and mature rows are
        within 3 percent, and ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description="Validate VTOTREG4 against console output.")
    parser.add_argument("--config-dir", type=Path, required=True, help="VDYP_CFG directory")
    parser.add_argument("--golden", type=Path, required=True, help="golden CSV output")
    parser.add_argument("--bec", default="BWBS", help="BEC zone of the input case")
    args = parser.parse_args(argv)
    try:
        rows = validate_against_golden(args.config_dir, args.golden, bec=args.bec)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    age_100 = [row for row in rows if row["age"] == 100]
    mature = [row for row in rows if int(str(row["age"])) >= VALIDATED_MIN_AGE]
    age_100_ok = bool(age_100) and all(
        float(str(row["relative_error"])) <= AGE_100_TOLERANCE for row in age_100
    )
    mature_ok = all(float(str(row["relative_error"])) <= MATURE_TOLERANCE for row in mature)
    print(f"rows: {len(rows)}")
    if age_100:
        row = age_100[0]
        print(
            f"age 100: console={row['console']} python={row['python']} "
            f"error={float(str(row['relative_error'])):.4%}"
        )
    print(f"age-100 tolerance 1%: {'PASS' if age_100_ok else 'FAIL'}")
    print(f"mature (>=80) tolerance 3%: {'PASS' if mature_ok else 'FAIL'}")
    return 0 if age_100_ok and mature_ok else 1


if __name__ == "__main__":
    sys.exit(main())
