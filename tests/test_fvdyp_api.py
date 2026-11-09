"""Tests for the FastAPI service and the FRESH-style page."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fvdyp_api import create_app

ROOT: Path = Path(__file__).resolve().parents[1]
FIXTURE_COE = ROOT / "fixtures" / "mini-bundle" / "coe" / "VTOTREG4.COE"
GOLDEN = ROOT / "fixtures" / "yield-output" / "golden-full.csv"
METADATA = ROOT / "fixtures" / "yield-output" / "metadata.json"
SCHEMA = ROOT / "notes" / "reference" / "vdyp-columns.json"
ALIASES = ROOT / "notes" / "reference" / "vdyp-csv-header-aliases.json"
MATRIX = ROOT / "notes" / "reference" / "vdyp-equation-matrix.json"


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_config(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coe = config / "coe"
    coe.mkdir(parents=True)
    (config / "VDYP.CTR").write_text(
        control_line("090", "coe\\VTOTREG4.coe", "Whole stem") + "\n", encoding="ascii"
    )
    (config / "VDYPBACK.CTR").write_text("", encoding="ascii")
    (coe / "SP0.DAT").write_text("AC\nAT\n", encoding="ascii")
    (coe / "BEC0.DAT").write_text("AT\nBWBS\n", encoding="ascii")
    (coe / "VTOTREG4.COE").write_bytes(FIXTURE_COE.read_bytes())
    return config


def client(config: Path | None = None) -> TestClient:
    app = create_app(
        config_dir=config,
        golden_csv=GOLDEN,
        metadata=METADATA,
        schema=SCHEMA,
        aliases=ALIASES,
        matrix=MATRIX,
    )
    return TestClient(app)


def test_health() -> None:
    response = client().get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_bundle_catalog(tmp_path: Path) -> None:
    response = client(write_config(tmp_path / "install")).get("/bundle/catalog")
    assert response.status_code == 200
    assert response.json()["family_count"] == 1


def test_bundle_catalog_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    response = client(None).get("/bundle/catalog")
    assert response.status_code == 400
    assert "VDYP_CFG_DIR" in response.json()["detail"]


def test_curve_query_age_100() -> None:
    response = client().post("/curves/query", json={"age_start": 100, "age_end": 100})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert len(payload["points"]) == 1
    point = payload["points"][0]
    assert point["year"] == 2100
    assert point["volume_ws"] == 436.39481
    assert point["units"]["volume_ws"] == "m3/ha"
    assert payload["provenance"]["runtime"] == "Wine 11.0"
    assert payload["provenance"]["console_version"] == "7.16k"


def test_curve_query_empty_species() -> None:
    response = client().post("/curves/query", json={"species": "FD"})
    payload = response.json()
    assert payload["status"] == "empty"
    assert payload["points"] == []


def test_curve_query_bad_range() -> None:
    response = client().post("/curves/query", json={"age_start": 10, "age_end": 1})
    assert response.status_code == 400
    assert "age_start" in response.json()["detail"]


def test_equation_matrix() -> None:
    response = client().get("/equations/matrix")
    assert response.status_code == 200
    families = {row["family"]: row["status"] for row in response.json()["families"]}
    assert families["VTOTREG4"] == "validated"
    assert families["REGVCU"] == "experimental"


def test_index_page_works_without_assistant() -> None:
    response = client().get("/")
    assert response.status_code == 200
    assert "fresh-vdyp" in response.text
    assert "Curve query" in response.text
    assert "Equation validation" in response.text
    assert "/curves/query" in response.text


def test_matrix_error_is_structured(tmp_path: Path) -> None:
    app = create_app(
        config_dir=None,
        golden_csv=GOLDEN,
        metadata=METADATA,
        schema=SCHEMA,
        aliases=ALIASES,
        matrix=tmp_path / "absent.json",
    )
    response = TestClient(app).get("/equations/matrix")
    assert response.status_code == 400
    assert "detail" in response.json()
