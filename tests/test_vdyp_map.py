"""Tests for the VDYP7 control-sequence join."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vdyp_map import (
    build_control_map,
    classify_target,
    looks_like_file,
    main,
    resolve_target,
    roots_from_environment,
)


def control_line(sequence: str, value: str = "", description: str = "") -> str:
    return f"{sequence:<4}{value:<50}{description}"


def write_install(root: Path) -> Path:
    config = root / "VDYP_CFG"
    coefficients = config / "coe"
    coefficients.mkdir(parents=True, exist_ok=True)
    for name in (
        "VTOTREG4.COE",
        "regvu.coe",
        "Becdef.dat",
        "BEC0.DAT",
        "SIEQN.PRM",
        "UNUSED1.COE",
        "unused2.prm",
    ):
        (coefficients / name).write_text("x\n", encoding="ascii")
    (config / "VDYP.CTR").write_text(
        "\n".join(
            [
                control_line("001", "00999999", "Max polygons"),
                control_line("009", "coe\\becdef.dat", "BEC definitions"),
                control_line("090", "coe\\VTOTREG4.coe", "Whole stem"),
                control_line("091", "coe\\regvu.coe", "Utilization"),
                control_line("011", "vp_fip2.dat", "Polygon input"),
                control_line("025", "", "Nullifies site curve"),
                control_line("099", "coe\\absent.coe", "Missing target"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    (config / "VDYPBACK.CTR").write_text(
        control_line("011", "\\bcgrow\\backtst\\VP_IN36.dat", "External input") + "\n",
        encoding="ascii",
    )
    return config


def test_looks_like_file_distinguishes_values() -> None:
    assert looks_like_file("coe\\VTOTREG4.coe")
    assert looks_like_file("vp_fip2.dat")
    assert not looks_like_file("00999999")
    assert not looks_like_file("-1   1   2   2   1   1")
    assert not looks_like_file("")


def test_resolve_target_is_case_insensitive() -> None:
    index = {"vdyp_cfg/coe/vtotreg4.coe": "VDYP_CFG/coe/VTOTREG4.COE"}
    assert resolve_target("coe\\vtotreg4.coe", index) == "VDYP_CFG/coe/VTOTREG4.COE"


def test_resolve_target_returns_none_for_an_unknown_path() -> None:
    assert resolve_target("coe\\absent.coe", {}) is None


@pytest.mark.parametrize(
    ("value", "resolved", "status"),
    [
        ("", None, "empty"),
        ("00999999", None, "not_a_file"),
        ("coe\\x.coe", "VDYP_CFG/coe/x.coe", "resolved"),
        ("coe\\x.coe", None, "missing"),
        ("vp_fip2.dat", None, "runtime"),
        ("\\bcgrow\\backtst\\VP_IN36.dat", None, "external"),
        ("/bcgrow/VP_IN36.dat", None, "external"),
    ],
)
def test_classify_target(value: str, resolved: str | None, status: str) -> None:
    assert classify_target(value, resolved) == status


def test_build_control_map_joins_entries(tmp_path: Path) -> None:
    config = write_install(tmp_path / "install")
    control_map = build_control_map(tmp_path / "install", config)
    statuses = {
        (entry.control_file, entry.sequence_id): entry.status for entry in control_map.entries
    }
    assert statuses[("VDYP_CFG/VDYP.CTR", "001")] == "not_a_file"
    assert statuses[("VDYP_CFG/VDYP.CTR", "009")] == "resolved"
    assert statuses[("VDYP_CFG/VDYP.CTR", "090")] == "resolved"
    assert statuses[("VDYP_CFG/VDYP.CTR", "011")] == "runtime"
    assert statuses[("VDYP_CFG/VDYP.CTR", "025")] == "empty"
    assert statuses[("VDYP_CFG/VDYP.CTR", "099")] == "missing"
    assert statuses[("VDYP_CFG/VDYPBACK.CTR", "011")] == "external"


def test_build_control_map_preserves_resolved_case_and_kind(tmp_path: Path) -> None:
    config = write_install(tmp_path / "install")
    control_map = build_control_map(tmp_path / "install", config)
    resolved = {
        entry.sequence_id: (entry.resolved_path, entry.kind)
        for entry in control_map.entries
        if entry.status == "resolved"
    }
    assert resolved["090"] == ("VDYP_CFG/coe/VTOTREG4.COE", "coefficient")
    assert resolved["009"] == ("VDYP_CFG/coe/Becdef.dat", "data")
    assert resolved["091"] == ("VDYP_CFG/coe/regvu.coe", "coefficient")


def test_build_control_map_reports_unreferenced_bundle_files(tmp_path: Path) -> None:
    config = write_install(tmp_path / "install")
    control_map = build_control_map(tmp_path / "install", config)
    assert control_map.unreferenced_bundle_files == (
        "VDYP_CFG/coe/BEC0.DAT",
        "VDYP_CFG/coe/SIEQN.PRM",
        "VDYP_CFG/coe/UNUSED1.COE",
        "VDYP_CFG/coe/unused2.prm",
    )


def test_control_map_serialization_has_no_absolute_paths(tmp_path: Path) -> None:
    config = write_install(tmp_path / "install")
    control_map = build_control_map(tmp_path / "install", config)
    serialized = json.dumps(control_map.to_dict())
    assert str(tmp_path) not in serialized
    payload = control_map.to_dict()
    assert payload["entry_count"] == 8
    assert payload["counts"] == {
        "resolved": 3,
        "runtime": 1,
        "empty": 1,
        "missing": 1,
        "not_a_file": 1,
        "external": 1,
    }


def test_control_map_missing_targets_are_listed(tmp_path: Path) -> None:
    config = write_install(tmp_path / "install")
    control_map = build_control_map(tmp_path / "install", config)
    assert control_map.to_dict()["missing_targets"] == [
        {"control_file": "VDYP_CFG/VDYP.CTR", "sequence": "099", "value": "coe\\absent.coe"}
    ]


def test_build_control_map_rejects_a_missing_root(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        build_control_map(tmp_path / "absent", tmp_path / "config")


def test_main_writes_the_map(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = write_install(tmp_path / "install")
    output = tmp_path / "out" / "map.json"
    assert (
        main(
            [
                "--install-root",
                str(tmp_path / "install"),
                "--config-dir",
                str(config),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["entry_count"] == 8
    assert "Wrote" in capsys.readouterr().out


def test_main_derives_the_config_dir_from_the_install_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_install(tmp_path / "install")
    assert config == tmp_path / "install" / "VDYP_CFG"
    monkeypatch.setenv("VDYP_INSTALL", str(tmp_path / "install"))
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    output = tmp_path / "map.json"
    assert main(["--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["entry_count"] == 8
    assert roots_from_environment() == (tmp_path / "install", None)
    capsys.readouterr()


def test_main_without_roots_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_INSTALL", raising=False)
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    assert main(["--output", str(tmp_path / "map.json")]) == 2
    assert "error:" in capsys.readouterr().err


def test_main_with_a_missing_install_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = write_install(tmp_path / "install")
    assert (
        main(
            [
                "--install-root",
                str(tmp_path / "absent"),
                "--config-dir",
                str(config),
                "--output",
                str(tmp_path / "map.json"),
            ]
        )
        == 2
    )
    assert "error:" in capsys.readouterr().err
