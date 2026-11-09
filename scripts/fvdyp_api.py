#!/usr/bin/env python3
"""FastAPI service and FRESH-style page over the bundle and curve services.

Endpoints:

- ``GET /health``
- ``GET /bundle/catalog``
- ``POST /curves/query``
- ``GET /equations/matrix``
- ``GET /`` (a small HTML page that works without an assistant)

Every data-bearing response carries provenance. The service reuses
``bundle_service`` and ``curve_api``; it does not duplicate their logic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from bundle_service import catalog_payload
from curve_api import CurveQuery, CurveQueryError, load_service

APP_VERSION: Final[str] = "0.1.0"
DEFAULT_GOLDEN_CSV: Final[Path] = Path("fixtures/yield-output/golden-full.csv")
DEFAULT_GOLDEN_METADATA: Final[Path] = Path("fixtures/yield-output/metadata.json")
DEFAULT_SCHEMA: Final[Path] = Path("notes/reference/vdyp-columns.json")
DEFAULT_ALIASES: Final[Path] = Path("notes/reference/vdyp-csv-header-aliases.json")
DEFAULT_MATRIX: Final[Path] = Path("notes/reference/vdyp-equation-matrix.json")

INDEX_HTML: Final[str] = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>fresh-vdyp</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; color: #1f2933; }
    h1 { margin-bottom: 0.2rem; }
    .muted { color: #616e7c; }
    section { border-top: 1px solid #d9e2ec; margin-top: 1.5rem; padding-top: 1rem; }
    table { border-collapse: collapse; margin-top: 0.5rem; }
    th, td { border-bottom: 1px solid #d9e2ec; padding: 0.3rem 0.6rem; text-align: left; }
    input { margin: 0.2rem; }
    pre { background: #f5f7fa; padding: 0.8rem; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>fresh-vdyp</h1>
  <p class="muted">A typed view of the VDYP7 bundle, curves, and equation status.</p>
  <section>
    <h2>Bundle catalog</h2>
    <button id="load-catalog">Load catalog</button>
    <pre id="catalog">Not loaded.</pre>
  </section>
  <section>
    <h2>Curve query</h2>
    <form id="curve-form">
      <label>Species <input name="species" placeholder="AT"></label>
      <label>Year start <input name="year_start" type="number"></label>
      <label>Year end <input name="year_end" type="number"></label>
      <label>Age start <input name="age_start" type="number"></label>
      <label>Age end <input name="age_end" type="number"></label>
      <button type="submit">Query</button>
    </form>
    <div id="curve-status"></div>
    <pre id="provenance">No query yet.</pre>
    <table id="curve-table"></table>
  </section>
  <section>
    <h2>Equation validation</h2>
    <button id="load-matrix">Load matrix</button>
    <pre id="matrix">Not loaded.</pre>
  </section>
  <script>
    const $ = (id) => document.getElementById(id);
    $("load-catalog").onclick = async () => {
      const response = await fetch("/bundle/catalog");
      $("catalog").textContent = JSON.stringify(await response.json(), null, 2);
    };
    $("load-matrix").onclick = async () => {
      const response = await fetch("/equations/matrix");
      $("matrix").textContent = JSON.stringify(await response.json(), null, 2);
    };
    $("curve-form").onsubmit = async (event) => {
      event.preventDefault();
      const data = new FormData(event.target);
      const body = {};
      for (const [key, value] of data.entries()) {
        if (value !== "") {
          const numeric = key.includes("year") || key.includes("age");
          body[key] = numeric ? Number(value) : value;
        }
      }
      const response = await fetch("/curves/query", {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
      });
      const payload = await response.json();
      $("curve-status").textContent = `${payload.status || "error"} ${payload.reason || ""}`;
      $("provenance").textContent = JSON.stringify(payload.provenance || payload, null, 2);
      const table = $("curve-table");
      table.innerHTML = "";
      const points = payload.points || [];
      if (points.length) {
        const headers = ["year", "age", "species", "volume_ws", "volume_cu",
          "lorey_height", "diameter", "tph", "ba"];
        table.innerHTML = "<tr>" + headers.map((h) => `<th>${h}</th>`).join("") + "</tr>" +
          points.map((point) => "<tr>" + headers.map((h) => {
            const value = h === "species" ? point.species.join(",") : point[h];
            return `<td>${value === null ? "" : value}</td>`;
          }).join("") + "</tr>").join("");
      }
    };
  </script>
</body>
</html>
"""


class CurveQueryRequest(BaseModel):
    """A curve query request body.

    Attributes
    ----------
    species : str or None
        Species code filter.
    year_start : int or None
        First included year.
    year_end : int or None
        Last included year.
    age_start : int or None
        First included age.
    age_end : int or None
        Last included age.
    """

    species: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    age_start: int | None = None
    age_end: int | None = None

    def to_query(self) -> CurveQuery:
        """Build the service query.

        Returns
        -------
        CurveQuery
            The typed query.
        """
        return CurveQuery(
            species=self.species,
            year_start=self.year_start,
            year_end=self.year_end,
            age_start=self.age_start,
            age_end=self.age_end,
        )


class CurvePointResponse(BaseModel):
    """One curve point in an API response."""

    year: int
    age: int
    species: list[str]
    volume_ws: float | None
    volume_cu: float | None
    volume_d: float | None
    volume_dw: float | None
    volume_dwb: float | None
    dom_height: float | None
    lorey_height: float | None
    diameter: float | None
    tph: float | None
    ba: float | None
    site_index: float | None
    pct_stockable: float | None
    units: dict[str, str]


class ProvenanceResponse(BaseModel):
    """Source and runtime provenance."""

    source_file: str
    runtime: str
    console_version: str
    control_sequence: str
    query: dict[str, object]


class CurveResponse(BaseModel):
    """A curve query response."""

    status: str
    reason: str
    provenance: ProvenanceResponse
    points: list[CurvePointResponse] = Field(default_factory=list)


def _config_from_environment() -> Path | None:
    value = os.environ.get("VDYP_CFG_DIR")
    return Path(value) if value else None


def create_app(
    *,
    config_dir: Path | None = None,
    golden_csv: Path = DEFAULT_GOLDEN_CSV,
    metadata: Path = DEFAULT_GOLDEN_METADATA,
    schema: Path = DEFAULT_SCHEMA,
    aliases: Path = DEFAULT_ALIASES,
    matrix: Path = DEFAULT_MATRIX,
) -> FastAPI:
    """Build the FastAPI application.

    Parameters
    ----------
    config_dir : Path or None, optional
        VDYP_CFG directory for bundle endpoints.
    golden_csv : Path, optional
        Curve CSV.
    metadata : Path, optional
        Run metadata.
    schema : Path, optional
        Column schema.
    aliases : Path, optional
        Header aliases.
    matrix : Path, optional
        Equation matrix.

    Returns
    -------
    FastAPI
        The configured application.
    """
    application = FastAPI(title="fresh-vdyp", version=APP_VERSION)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION}

    @application.get("/bundle/catalog")
    def bundle_catalog() -> dict[str, object]:
        selected = config_dir if config_dir is not None else _config_from_environment()
        if selected is None:
            raise HTTPException(status_code=400, detail="VDYP_CFG_DIR is not configured")
        try:
            return catalog_payload(selected)
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.post("/curves/query", response_model=CurveResponse)
    def query_curves(request: CurveQueryRequest) -> CurveResponse:
        try:
            service = load_service(golden_csv, metadata, schema_path=schema, alias_path=aliases)
            result = service.query(request.to_query())
        except CurveQueryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return CurveResponse(
            status=result.status,
            reason=result.reason,
            provenance=ProvenanceResponse(
                source_file=result.provenance.source_file,
                runtime=result.provenance.runtime,
                console_version=result.provenance.console_version,
                control_sequence=result.provenance.control_sequence,
                query=result.provenance.query,
            ),
            points=[
                CurvePointResponse(
                    year=point.year,
                    age=point.age,
                    species=list(point.species),
                    volume_ws=point.volume_ws,
                    volume_cu=point.volume_cu,
                    volume_d=point.volume_d,
                    volume_dw=point.volume_dw,
                    volume_dwb=point.volume_dwb,
                    dom_height=point.dom_height,
                    lorey_height=point.lorey_height,
                    diameter=point.diameter,
                    tph=point.tph,
                    ba=point.ba,
                    site_index=point.site_index,
                    pct_stockable=point.pct_stockable,
                    units=point.units,
                )
                for point in result.points
            ],
        )

    @application.get("/equations/matrix")
    def equation_matrix() -> dict[str, object]:
        try:
            payload = json.loads(matrix.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="matrix is not an object")
        return payload

    @application.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    return application


app = create_app()
