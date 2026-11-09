"""Tests for package metadata and the public facade."""

from __future__ import annotations

import tomllib
from pathlib import Path

import fresh_vdyp

ROOT: Path = Path(__file__).resolve().parents[1]


def test_project_metadata() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    assert project["name"] == "fresh-vdyp"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"
    assert "typer>=0.12" in project["dependencies"]
    assert project["scripts"]["fvdyp"] == "fvdyp_cli:main"


def test_facade_exports_the_services() -> None:
    assert fresh_vdyp.__version__ == "0.1.0"
    assert fresh_vdyp.CurveQuery is not None
    assert fresh_vdyp.load_service is not None
    assert fresh_vdyp.validate_bundle is not None


def test_normalized_assets_are_not_package_modules() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    modules = payload["tool"]["setuptools"]["py-modules"]
    assert "normalize" in modules
    assert "data" not in modules
