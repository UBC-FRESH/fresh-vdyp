"""Schema coverage tests for every supported .COE family."""

from __future__ import annotations

import pytest

from coe_parser import COE_SCHEMAS, UNSUPPORTED_FAMILIES, parse_coe_text
from key_inference import EQUATION_FAMILIES


@pytest.mark.parametrize("family", sorted(COE_SCHEMAS))
def test_every_schema_is_internally_consistent(family: str) -> None:
    schema = COE_SCHEMAS[family]
    assert schema.family == family
    assert len(schema.columns) == len(schema.kinds)
    assert len(set(schema.columns)) == len(schema.columns)
    assert all(column for column in schema.columns)
    assert set(schema.kinds) <= {"number", "text"}


@pytest.mark.parametrize("family", sorted(COE_SCHEMAS))
def test_every_supported_family_parses_one_synthetic_row(family: str) -> None:
    schema = COE_SCHEMAS[family]
    tokens = ["AC" if kind == "text" else "1" for kind in schema.kinds]
    table = parse_coe_text(
        " ".join(tokens) + "\n",
        source_file=f"VDYP_CFG/coe/{family.upper()}.COE",
        family=family,
    )
    assert table.family == family
    assert table.columns == schema.columns
    assert len(table.rows) == 1
    assert len(table.rows[0].values) == len(schema.columns)


def test_equation_registry_covers_every_coe_family() -> None:
    assert set(EQUATION_FAMILIES) == set(COE_SCHEMAS) | set(UNSUPPORTED_FAMILIES)


def test_unsupported_families_have_no_schema() -> None:
    assert set(UNSUPPORTED_FAMILIES).isdisjoint(COE_SCHEMAS)
