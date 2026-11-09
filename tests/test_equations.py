"""Tests for the VTOTREG4 whole-stem volume family."""

from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

from equations import (
    AGE_100_TOLERANCE,
    MATURE_TOLERANCE,
    VALIDATED_MIN_AGE,
    EquationError,
    GrowthCoefficients,
    WholeStemCoefficients,
    basal_area_increment,
    close_utilization_ratio,
    estimate_basal_area_increment,
    estimate_close_utilization_volume,
    estimate_non_primary_height,
    estimate_quad_mean_diameter_increment,
    estimate_utilization_components,
    estimate_whole_stem_volume,
    family_status,
    load_growth_coefficients,
    load_reghl,
    load_regvcu,
    load_regvu,
    load_volume_groups,
    load_vtotreg4,
    main,
    non_primary_lorey_height,
    quad_mean_diameter_increment,
    ratio,
    validate_against_golden,
    whole_stem_volume_per_hectare,
    whole_stem_volume_per_tree,
)

ROOT: Path = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
INSTALL = os.environ.get("VDYP_INSTALL")
CONFIG = Path(INSTALL) / "VDYP_CFG" if INSTALL else None


def test_load_vtotreg4_from_a_synthetic_file(tmp_path: Path) -> None:
    path = tmp_path / "VTOTREG4.COE"
    path.write_text("6 1 2 3 4 5 6 7 8 9\n", encoding="ascii")
    rows = load_vtotreg4(path)
    assert rows[6].coefficients == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
    assert rows[6].volume_group == 6


def test_load_vtotreg4_rejects_a_short_row(tmp_path: Path) -> None:
    path = tmp_path / "VTOTREG4.COE"
    path.write_text("6 1 2 3\n", encoding="ascii")
    with pytest.raises(ValueError, match="expected 10 tokens"):
        load_vtotreg4(path)


def test_load_volume_groups_maps_group_10_to_11(tmp_path: Path) -> None:
    path = tmp_path / "VGRPDEF1.DAT"
    path.write_text("AT BWBS  6\nAT ESSF 10\n", encoding="ascii")
    groups = load_volume_groups(path)
    assert groups[("AT", "BWBS")] == 6
    assert groups[("AT", "ESSF")] == 11


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, math.exp(1.0)),
        (1, 10.0),
        (2, 20.0),
        (3, math.exp(10.0)),
        (4, math.exp(0.1)),
        (5, math.exp(20.0)),
        (6, math.exp(100.0)),
        (7, math.exp(200.0)),
        (8, math.exp(2.0)),
    ],
)
def test_each_coefficient_term_is_wired(index: int, expected: float) -> None:
    coefficients = [0.0] * 9
    coefficients[index] = 1.0
    value = whole_stem_volume_per_tree(coefficients, lorey_height=20.0, quad_mean_diameter=10.0)
    assert value == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_per_hectare_multiplies_per_tree_by_tph() -> None:
    coefficients = [1.0] + [0.0] * 8
    per_tree = whole_stem_volume_per_tree(coefficients, 20.0, 10.0)
    per_ha = whole_stem_volume_per_hectare(
        coefficients, lorey_height=20.0, quad_mean_diameter=10.0, trees_per_hectare=500.0
    )
    assert per_ha == pytest.approx(per_tree * 500.0)


@pytest.mark.parametrize(("height", "diameter"), [(0.0, 10.0), (20.0, 0.0), (-1.0, 10.0)])
def test_positive_height_and_diameter_are_required(height: float, diameter: float) -> None:
    with pytest.raises(EquationError):
        whole_stem_volume_per_tree([0.0] * 9, height, diameter)


def test_tph_must_not_be_negative() -> None:
    with pytest.raises(EquationError):
        whole_stem_volume_per_hectare(
            [0.0] * 9, lorey_height=20.0, quad_mean_diameter=10.0, trees_per_hectare=-1.0
        )


def test_family_status_threshold() -> None:
    assert family_status(VALIDATED_MIN_AGE) == "validated"
    assert family_status(VALIDATED_MIN_AGE - 1) == "experimental"


def test_estimate_returns_validated_at_maturity() -> None:
    coefficients = {
        6: WholeStemCoefficients(6, (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "x", 1)
    }
    groups = {("AT", "BWBS"): 6}
    estimate = estimate_whole_stem_volume(
        coefficients,
        groups,
        species="AT",
        bec="BWBS",
        lorey_height=20.0,
        quad_mean_diameter=10.0,
        trees_per_hectare=100.0,
        age=100,
    )
    assert estimate.status == "validated"
    assert estimate.value == pytest.approx(1000.0)
    assert estimate.volume_group == 6


def test_estimate_is_experimental_before_the_threshold() -> None:
    coefficients = {6: WholeStemCoefficients(6, (0.0,) * 9, "x", 1)}
    groups = {("AT", "BWBS"): 6}
    estimate = estimate_whole_stem_volume(
        coefficients,
        groups,
        species="AT",
        bec="BWBS",
        lorey_height=20.0,
        quad_mean_diameter=10.0,
        trees_per_hectare=100.0,
        age=50,
    )
    assert estimate.status == "experimental"
    assert "young-stand" in estimate.reason


def test_unknown_keys_are_not_implemented() -> None:
    estimate = estimate_whole_stem_volume(
        {},
        {},
        species="ZZ",
        bec="BWBS",
        lorey_height=20.0,
        quad_mean_diameter=10.0,
        trees_per_hectare=100.0,
        age=100,
    )
    assert estimate.status == "not_implemented"
    assert estimate.volume_group is None


def test_missing_coefficient_row_is_not_implemented() -> None:
    estimate = estimate_whole_stem_volume(
        {},
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        lorey_height=20.0,
        quad_mean_diameter=10.0,
        trees_per_hectare=100.0,
        age=100,
    )
    assert estimate.status == "not_implemented"
    assert estimate.volume_group == 6


@pytest.mark.skipif(not INSTALL, reason="VDYP_INSTALL is not set")
def test_age_100_matches_the_console() -> None:
    assert CONFIG is not None
    rows = validate_against_golden(CONFIG, GOLDEN)
    age_100 = [row for row in rows if row["age"] == 100]
    assert len(age_100) == 1
    assert float(str(age_100[0]["relative_error"])) <= AGE_100_TOLERANCE


@pytest.mark.skipif(not INSTALL, reason="VDYP_INSTALL is not set")
def test_mature_rows_stay_within_tolerance() -> None:
    assert CONFIG is not None
    rows = validate_against_golden(CONFIG, GOLDEN)
    mature = [row for row in rows if int(str(row["age"])) >= VALIDATED_MIN_AGE]
    assert mature
    assert max(float(str(row["relative_error"])) for row in mature) <= MATURE_TOLERANCE


@pytest.mark.skipif(not INSTALL, reason="VDYP_INSTALL is not set")
def test_cli_validation_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert CONFIG is not None
    assert main(["--config-dir", str(CONFIG), "--golden", str(GOLDEN)]) == 0
    output = capsys.readouterr().out
    assert "age-100 tolerance 1%: PASS" in output
    assert "mature (>=80) tolerance 3%: PASS" in output


def write_synthetic_case(tmp_path: Path) -> tuple[Path, Path]:
    config = tmp_path / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (coe / "VTOTREG4.COE").write_text("6 0 1 0 0 0 0 0 0 0\n", encoding="ascii")
    (coe / "VGRPDEF1.DAT").write_text("AT BWBS 6\n", encoding="ascii")
    golden = tmp_path / "golden.csv"
    golden.write_text(
        "PRJ_VOL_WS,PRJ_TOTAL_AGE,SPECIES_1_CODE,PRJ_LOREY_HT,PRJ_DIAMETER,PRJ_TPH\n"
        "1000,100,AT,20,10,100\n",
        encoding="ascii",
    )
    return config, golden


def test_validate_against_golden_with_a_synthetic_case(tmp_path: Path) -> None:
    config, golden = write_synthetic_case(tmp_path)
    rows = validate_against_golden(config, golden)
    assert len(rows) == 1
    assert rows[0]["status"] == "validated"
    assert float(str(rows[0]["relative_error"])) == pytest.approx(0.0, abs=1e-12)


def test_cli_validation_with_a_synthetic_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config, golden = write_synthetic_case(tmp_path)
    assert main(["--config-dir", str(config), "--golden", str(golden)]) == 0
    output = capsys.readouterr().out
    assert "age-100 tolerance 1%: PASS" in output
    assert "mature (>=80) tolerance 3%: PASS" in output


def test_load_regvcu_from_a_synthetic_file(tmp_path: Path) -> None:
    path = tmp_path / "REGVCU.COE"
    path.write_text("1 6 -7.425 0.0 0.15032\n", encoding="ascii")
    rows = load_regvcu(path)
    assert rows[(1, 6)] == pytest.approx((-7.425, 0.0, 0.15032))


def test_load_regvu_from_a_synthetic_file(tmp_path: Path) -> None:
    path = tmp_path / "REGVU.COE"
    path.write_text("1 6 -1.14241 1.35050 0.82758 -1.14570\n", encoding="ascii")
    rows = load_regvu(path)
    assert rows[(1, 6)] == pytest.approx((-1.14241, 1.35050, 0.82758, -1.14570))


def test_ratio_is_clamped() -> None:
    assert ratio(0.0, 7.0) == pytest.approx(0.5)
    assert ratio(10.0, 7.0) == 1.0
    assert ratio(-10.0, 7.0) == 0.0


def test_close_utilization_ratio_and_aggregate() -> None:
    assert close_utilization_ratio((0.0, 0.0, 0.0), 10.0, 20.0) == pytest.approx(0.5)
    coefficients = {(uc, 6): (0.0, 0.0, 0.0) for uc in (1, 2, 3, 4)}
    estimate = estimate_close_utilization_volume(
        coefficients,
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        whole_stem_by_class={1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0},
        dq_by_class={1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0},
        lorey_height=20.0,
    )
    assert estimate.value == pytest.approx(200.0)
    assert estimate.status == "experimental"
    assert "oracle" in estimate.reason


def test_close_utilization_missing_class_is_not_implemented() -> None:
    coefficients = {(uc, 6): (0.0, 0.0, 0.0) for uc in (1, 2, 3)}
    estimate = estimate_close_utilization_volume(
        coefficients,
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        whole_stem_by_class={1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0},
        dq_by_class={1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0},
        lorey_height=20.0,
    )
    assert estimate.status == "not_implemented"
    assert "[4]" in estimate.reason


def test_utilization_components_are_normalized() -> None:
    coefficients = {(uc, 6): (0.0, 1.0, 0.0, 0.0) for uc in (1, 2, 3, 4)}
    estimate = estimate_utilization_components(
        coefficients,
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        base_area_by_class={1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0},
        dq_by_class={1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0},
        dq_all=10.0,
        lorey_height=20.0,
        total_all=1600.0,
    )
    assert estimate.status == "experimental"
    assert sum(estimate.components.values()) == pytest.approx(1600.0)
    assert estimate.components[1] == pytest.approx(400.0)


def test_utilization_components_missing_class_is_not_implemented() -> None:
    estimate = estimate_utilization_components(
        {(1, 6): (0.0, 1.0, 0.0, 0.0)},
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        base_area_by_class={1: 10.0},
        dq_by_class={1: 10.0},
        dq_all=10.0,
        lorey_height=20.0,
        total_all=100.0,
    )
    assert estimate.status == "not_implemented"
    assert "[2, 3, 4]" in estimate.reason


def test_utilization_components_zero_sum_is_not_implemented() -> None:
    coefficients = {(uc, 6): (0.0, 0.0, 0.0, 0.0) for uc in (1, 2, 3, 4)}
    estimate = estimate_utilization_components(
        coefficients,
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        base_area_by_class={1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
        dq_by_class={1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0},
        dq_all=10.0,
        lorey_height=20.0,
        total_all=100.0,
    )
    assert estimate.status == "not_implemented"
    assert "not positive" in estimate.reason


def test_load_reghl_and_height_equations(tmp_path: Path) -> None:
    path = tmp_path / "REGHL.COE"
    path.write_text("AC AT C 1 0.86323 1.00505\nAC AT I 2 0.5 1.0\n", encoding="ascii")
    rows = load_reghl(path)
    first = rows[("AC", "AT", "C")]
    assert first.equation_index == 1
    assert non_primary_lorey_height(first, lead_height=30.0, primary_height=25.0) == pytest.approx(
        1.3 + 0.86323 * (30.0 - 1.3) ** 1.00505
    )
    second = rows[("AC", "AT", "I")]
    assert non_primary_lorey_height(second, lead_height=30.0, primary_height=25.0) == pytest.approx(
        1.3 + 0.5 * (25.0 - 1.3)
    )


def test_reghl_rejects_an_unknown_equation_index() -> None:
    from equations import ReghlCoefficients

    row = ReghlCoefficients("AC", "AT", "C", 3, (1.0, 1.0))
    with pytest.raises(EquationError):
        non_primary_lorey_height(row, lead_height=30.0, primary_height=25.0)


def test_estimate_non_primary_height_is_experimental() -> None:
    from equations import ReghlCoefficients

    rows = {("AC", "AT", "C"): ReghlCoefficients("AC", "AT", "C", 1, (1.0, 1.0))}
    estimate = estimate_non_primary_height(
        rows,
        non_primary="AC",
        primary="AT",
        region="C",
        lead_height=30.0,
        primary_height=25.0,
    )
    assert estimate.status == "experimental"
    assert estimate.value == pytest.approx(30.0)


def test_missing_reghl_row_uses_the_public_default() -> None:
    estimate = estimate_non_primary_height(
        {},
        non_primary="AC",
        primary="AT",
        region="C",
        lead_height=30.0,
        primary_height=25.0,
    )
    assert estimate.status == "experimental"
    assert "default" in estimate.reason
    assert estimate.value == pytest.approx(25.0)


def test_load_growth_coefficients(tmp_path: Path) -> None:
    path = tmp_path / "BASP05.COE"
    path.write_text("1 9 -0.0896 0.007892 0.00105\n", encoding="ascii")
    rows = load_growth_coefficients(path, family="basp05")
    assert rows[1].model == 9
    assert rows[1].coefficients == pytest.approx((-0.0896, 0.007892, 0.00105))


def test_basal_area_increment_models() -> None:
    for model in (3, 8, 9):
        row = GrowthCoefficients(1, model, (0.0, 0.0, 0.0))
        value = basal_area_increment(
            row,
            ba_start=100.0,
            ba_end=110.0,
            species_ba_start=50.0,
            dominant_height=20.0,
            years_at_breast_height=10.0,
            species_lorey_height=15.0,
        )
        assert value == pytest.approx(5.0), model


def test_basal_area_increment_handles_a_full_species_share() -> None:
    row = GrowthCoefficients(1, 3, (0.0, 0.0, 0.0))
    value = basal_area_increment(
        row,
        ba_start=100.0,
        ba_end=110.0,
        species_ba_start=100.0,
        dominant_height=20.0,
        years_at_breast_height=10.0,
        species_lorey_height=15.0,
    )
    assert value == pytest.approx(10.0)


def test_basal_area_increment_rejects_an_unknown_model() -> None:
    row = GrowthCoefficients(1, 1, (0.0, 0.0, 0.0))
    with pytest.raises(EquationError):
        basal_area_increment(
            row,
            ba_start=100.0,
            ba_end=110.0,
            species_ba_start=50.0,
            dominant_height=20.0,
            years_at_breast_height=10.0,
            species_lorey_height=15.0,
        )


def test_quad_mean_diameter_increment() -> None:
    row = GrowthCoefficients(1, 9, (0.0, 0.0, 0.0))
    value = quad_mean_diameter_increment(
        row,
        dq_start=10.0,
        dq_end=12.0,
        species_dq_start=10.0,
        layer_lorey_height=20.0,
        species_lorey_height=10.0,
    )
    assert value == pytest.approx(2.0)


def test_quad_mean_diameter_increment_clamps_at_the_minimum() -> None:
    row = GrowthCoefficients(1, 9, (-1000.0, 0.0, 0.0))
    value = quad_mean_diameter_increment(
        row,
        dq_start=10.0,
        dq_end=12.0,
        species_dq_start=10.0,
        layer_lorey_height=20.0,
        species_lorey_height=10.0,
    )
    assert value == pytest.approx(7.51 - 10.0)


def test_increment_wrappers_are_experimental_or_not_implemented() -> None:
    rows = {1: GrowthCoefficients(1, 3, (0.0, 0.0, 0.0))}
    ba = estimate_basal_area_increment(
        rows,
        1,
        ba_start=100.0,
        ba_end=110.0,
        species_ba_start=50.0,
        dominant_height=20.0,
        years_at_breast_height=10.0,
        species_lorey_height=15.0,
    )
    assert ba.status == "experimental"
    missing = estimate_basal_area_increment(
        rows,
        2,
        ba_start=100.0,
        ba_end=110.0,
        species_ba_start=50.0,
        dominant_height=20.0,
        years_at_breast_height=10.0,
        species_lorey_height=15.0,
    )
    assert missing.status == "not_implemented"
    dq = estimate_quad_mean_diameter_increment(
        {1: GrowthCoefficients(1, 9, (0.0, 0.0, 0.0))},
        1,
        dq_start=10.0,
        dq_end=12.0,
        species_dq_start=10.0,
        layer_lorey_height=20.0,
        species_lorey_height=10.0,
    )
    assert dq.status == "experimental"


def test_whole_stem_requires_nine_coefficients() -> None:
    with pytest.raises(EquationError):
        whole_stem_volume_per_tree([0.0] * 8, 20.0, 10.0)


def test_close_utilization_ratio_requires_three_coefficients() -> None:
    with pytest.raises(EquationError):
        close_utilization_ratio((0.0, 0.0), 10.0, 20.0)


def test_close_utilization_unknown_group_is_not_implemented() -> None:
    estimate = estimate_close_utilization_volume(
        {},
        {},
        species="AT",
        bec="BWBS",
        whole_stem_by_class={1: 1.0},
        dq_by_class={1: 10.0},
        lorey_height=20.0,
    )
    assert estimate.status == "not_implemented"


def test_utilization_unknown_group_is_not_implemented() -> None:
    estimate = estimate_utilization_components(
        {},
        {},
        species="AT",
        bec="BWBS",
        base_area_by_class={1: 1.0},
        dq_by_class={1: 10.0},
        dq_all=10.0,
        lorey_height=20.0,
        total_all=100.0,
    )
    assert estimate.status == "not_implemented"


def test_utilization_wrong_coefficient_count_is_not_implemented() -> None:
    estimate = estimate_utilization_components(
        {(1, 6): (0.0, 1.0, 0.0)},
        {("AT", "BWBS"): 6},
        species="AT",
        bec="BWBS",
        base_area_by_class={1: 10.0},
        dq_by_class={1: 10.0},
        dq_all=10.0,
        lorey_height=20.0,
        total_all=100.0,
    )
    assert estimate.status == "not_implemented"
    assert "4 coefficients" in estimate.reason


def test_reghl_height_must_exceed_1_3() -> None:
    from equations import ReghlCoefficients

    row = ReghlCoefficients("AC", "AT", "C", 1, (1.0, 1.0))
    with pytest.raises(EquationError):
        non_primary_lorey_height(row, lead_height=1.3, primary_height=25.0)


def test_reghl_requires_two_coefficients() -> None:
    from equations import ReghlCoefficients

    row = ReghlCoefficients("AC", "AT", "C", 1, (1.0,))
    with pytest.raises(EquationError):
        non_primary_lorey_height(row, lead_height=30.0, primary_height=25.0)


def test_basal_area_increment_rejects_invalid_inputs() -> None:
    row = GrowthCoefficients(1, 3, (0.0, 0.0, 0.0))
    with pytest.raises(EquationError):
        basal_area_increment(
            row,
            ba_start=0.0,
            ba_end=10.0,
            species_ba_start=5.0,
            dominant_height=20.0,
            years_at_breast_height=10.0,
            species_lorey_height=15.0,
        )
    with pytest.raises(EquationError):
        basal_area_increment(
            row,
            ba_start=100.0,
            ba_end=110.0,
            species_ba_start=0.0,
            dominant_height=20.0,
            years_at_breast_height=10.0,
            species_lorey_height=15.0,
        )


def test_quad_mean_diameter_increment_rejects_invalid_inputs() -> None:
    row = GrowthCoefficients(1, 9, (0.0, 0.0, 0.0))
    with pytest.raises(EquationError):
        quad_mean_diameter_increment(
            row,
            dq_start=7.0,
            dq_end=12.0,
            species_dq_start=10.0,
            layer_lorey_height=20.0,
            species_lorey_height=10.0,
        )
    with pytest.raises(EquationError):
        quad_mean_diameter_increment(
            row,
            dq_start=10.0,
            dq_end=12.0,
            species_dq_start=7.0,
            layer_lorey_height=20.0,
            species_lorey_height=10.0,
        )


def test_dq_increment_missing_row_is_not_implemented() -> None:
    estimate = estimate_quad_mean_diameter_increment(
        {},
        1,
        dq_start=10.0,
        dq_end=12.0,
        species_dq_start=10.0,
        layer_lorey_height=20.0,
        species_lorey_height=10.0,
    )
    assert estimate.status == "not_implemented"


def test_volume_groups_skip_short_and_non_numeric_rows(tmp_path: Path) -> None:
    path = tmp_path / "VGRPDEF1.DAT"
    path.write_text("AT\nAT BWBS not-a-number\nAT ESSF 10\n", encoding="ascii")
    groups = load_volume_groups(path)
    assert groups == {("AT", "ESSF"): 11}


def test_validate_against_golden_skips_blank_volume(tmp_path: Path) -> None:
    config, golden = write_synthetic_case(tmp_path)
    golden.write_text(
        "PRJ_VOL_WS,PRJ_TOTAL_AGE,SPECIES_1_CODE,PRJ_LOREY_HT,PRJ_DIAMETER,PRJ_TPH\n"
        ",100,AT,20,10,100\n"
        "1000,100,AT,20,10,100\n",
        encoding="ascii",
    )
    rows = validate_against_golden(config, golden)
    assert len(rows) == 1


def test_cli_returns_one_for_unreadable_inputs(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--config-dir",
                str(tmp_path / "absent-config"),
                "--golden",
                str(tmp_path / "absent.csv"),
            ]
        )
        == 1
    )
