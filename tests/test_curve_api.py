"""Tests for the typed curve API and the published client dataset."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from curve_api import (
    CurvePoint,
    CurveQuery,
    CurveQueryError,
    CurveService,
    load_service,
    main,
)
from provenance import validate_manifest
from yield_parser import YieldColumn, YieldRow, YieldTable

ROOT: Path = Path(__file__).resolve().parents[1]
CSV: Path = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA: Path = ROOT / "fixtures" / "yield-output" / "metadata.json"
MANIFEST: Path = ROOT / "fixtures" / "yield-output" / "dataset-manifest.json"
SCHEMA: Path = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES: Path = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"


def service() -> CurveService:
    return load_service(CSV, METADATA, schema_path=SCHEMA, alias_path=ALIASES)


def test_query_all_rows() -> None:
    result = service().query(CurveQuery())
    assert result.status == "ok"
    assert len(result.points) == 301
    assert result.provenance.runtime == "Wine 11.0"
    assert result.provenance.console_version == "7.16k"
    assert result.provenance.source_file == "golden-full.csv"
    assert result.points[0].year == 2000
    assert result.points[0].age == 0


def test_age_100_regression() -> None:
    result = service().query(CurveQuery(age_start=100, age_end=100))
    assert result.status == "ok"
    assert len(result.points) == 1
    point = result.points[0]
    assert point.year == 2100
    assert point.age == 100
    assert point.species == ("AT",)
    assert point.volume_ws == pytest.approx(436.39481)
    assert point.units["volume_ws"] == "m3/ha"
    assert point.units["age"] == "yr"


def test_year_filter_is_inclusive() -> None:
    result = service().query(CurveQuery(year_start=2001, year_end=2003))
    assert [point.year for point in result.points] == [2001, 2002, 2003]


def test_species_filter_is_case_insensitive() -> None:
    result = service().query(CurveQuery(species="at"))
    assert result.status == "ok"
    assert len(result.points) == 301
    assert all("AT" in point.species for point in result.points)


def test_unknown_species_returns_empty() -> None:
    result = service().query(CurveQuery(species="FD"))
    assert result.status == "empty"
    assert result.points == ()
    assert "no rows" in result.reason


@pytest.mark.parametrize(
    "query",
    [
        CurveQuery(year_start=2010, year_end=2000),
        CurveQuery(age_start=10, age_end=1),
        CurveQuery(species="  "),
    ],
)
def test_invalid_query_raises(query: CurveQuery) -> None:
    with pytest.raises(CurveQueryError):
        service().query(query)


def test_missing_required_columns_is_unsupported() -> None:
    columns = (YieldColumn(6, "Year", "", 0, "Year"),)
    table = YieldTable(
        source_file="x.csv",
        columns=columns,
        rows=(YieldRow(1, (2000,)),),
        provenance={},
    )
    curve = CurveService(table, "Wine 11.0", "7.16k")
    result = curve.query(CurveQuery())
    assert result.status == "unsupported"
    assert "Age" in result.reason


def test_point_and_result_serialization() -> None:
    result = service().query(CurveQuery(age_start=100, age_end=100))
    payload = result.to_dict()
    assert payload["point_count"] == 1
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    assert provenance["runtime"] == "Wine 11.0"
    points = payload["points"]
    assert isinstance(points, list)
    point = points[0]
    assert point["year"] == 2100
    assert point["units"]["volume_ws"] == "m3/ha"


def test_curve_point_is_a_typed_dataclass() -> None:
    point = CurvePoint(
        year=2000,
        age=1,
        species=("AT",),
        volume_ws=1.0,
        volume_cu=None,
        volume_d=None,
        volume_dw=None,
        volume_dwb=None,
        dom_height=None,
        lorey_height=None,
        diameter=None,
        tph=None,
        ba=None,
        site_index=None,
        pct_stockable=None,
        units={"volume_ws": "m3/ha"},
    )
    assert point.to_dict()["species"] == ["AT"]


def test_load_service_rejects_non_object_metadata(tmp_path: Path) -> None:
    metadata = tmp_path / "bad.json"
    metadata.write_text("[]", encoding="utf-8")
    with pytest.raises(CurveQueryError):
        load_service(CSV, metadata, schema_path=SCHEMA, alias_path=ALIASES)


def test_cli_writes_a_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "result.json"
    assert (
        main(
            [
                "--csv",
                str(CSV),
                "--metadata",
                str(METADATA),
                "--schema",
                str(SCHEMA),
                "--aliases",
                str(ALIASES),
                "--age-start",
                "100",
                "--age-end",
                "100",
                "--json",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["point_count"] == 1
    assert "points: 1" in capsys.readouterr().out


def test_dataset_manifest_is_valid() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert validate_manifest(manifest) == ()
    assert manifest[0]["row_count"] == 301
    assert manifest[0]["source_sha256"] == hashlib.sha256(CSV.read_bytes()).hexdigest()
