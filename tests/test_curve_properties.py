"""Property tests for curve query filtering."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from curve_api import CurveQuery, load_service

ROOT: Path = Path(__file__).resolve().parents[1]
CSV = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA = ROOT / "fixtures" / "yield-output" / "metadata.json"
SCHEMA = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"
TOTAL_ROWS = 301


@settings(max_examples=30, deadline=None)
@given(
    start=st.integers(min_value=1990, max_value=2300),
    width=st.integers(min_value=0, max_value=100),
    age_start=st.integers(min_value=0, max_value=200),
    age_width=st.integers(min_value=0, max_value=100),
)
def test_filters_never_add_rows_and_stay_in_bounds(
    start: int,
    width: int,
    age_start: int,
    age_width: int,
) -> None:
    result = load_service(CSV, METADATA, schema_path=SCHEMA, alias_path=ALIASES).query(
        CurveQuery(
            year_start=start,
            year_end=start + width,
            age_start=age_start,
            age_end=age_start + age_width,
        )
    )
    assert len(result.points) <= TOTAL_ROWS
    for point in result.points:
        assert start <= point.year <= start + width
        assert age_start <= point.age <= age_start + age_width


@settings(max_examples=20, deadline=None)
@given(species=st.sampled_from(["AT", "FD", "CW", "HW"]))
def test_species_filter_only_returns_matching_points(species: str) -> None:
    result = load_service(CSV, METADATA, schema_path=SCHEMA, alias_path=ALIASES).query(
        CurveQuery(species=species)
    )
    for point in result.points:
        assert species in point.species
