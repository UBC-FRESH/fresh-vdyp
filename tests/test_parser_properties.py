"""Property tests for the coefficient parsers and normalizer."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from coe_parser import coerce_value, parse_coe_text

NUMBER = st.floats(allow_nan=False, allow_infinity=False, width=64)
ROW = st.tuples(*([NUMBER] * 9))


@settings(max_examples=50, deadline=None)
@given(rows=st.lists(ROW, min_size=1, max_size=4))
def test_row_count_and_source_order_are_conserved(
    rows: list[tuple[float, ...]],
) -> None:
    lines = [
        f"{index} " + " ".join(str(value) for value in row)
        for index, row in enumerate(rows, start=1)
    ]
    table = parse_coe_text(
        "\n".join(lines) + "\n",
        source_file="VDYP_CFG/coe/VTOTREG4.COE",
        family="vtotreg4",
    )
    assert len(table.rows) == len(rows)
    assert [row.line_number for row in table.rows] == list(range(1, len(rows) + 1))
    for index, (parsed, original) in enumerate(zip(table.rows, rows, strict=True), start=1):
        assert parsed.values[0] == index
        assert parsed.values[1:] == original


@settings(max_examples=50, deadline=None)
@given(value=NUMBER)
def test_number_tokens_round_trip(value: float) -> None:
    assert coerce_value(str(value), "number") == value
