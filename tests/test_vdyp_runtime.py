"""Tests for VDYP7 runtime discovery and the Wine command adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vdyp_runtime import (
    RuntimeInfo,
    RuntimeMode,
    RuntimeUnavailableError,
    check_runtime,
    detect_wine_version,
    discover_runtime,
    main,
)


def make_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "install"
    config = root / "VDYP_CFG"
    config.mkdir(parents=True)
    console = root / "VDYP7Console.exe"
    console.write_bytes(b"MZ")
    return root, config, console


def make_wine(tmp_path: Path) -> Path:
    wine = tmp_path / "wine"
    wine.write_text("#!/bin/sh\necho wine-9.0\n", encoding="utf-8")
    wine.chmod(0o755)
    return wine


def info(mode: RuntimeMode, console: Path, config: Path) -> RuntimeInfo:
    return RuntimeInfo(
        mode=mode,
        console=console,
        config_dir=config,
        install_root=console.parent,
        wine=None,
        wine_version="",
    )


def test_native_discovery_builds_a_plain_command(tmp_path: Path) -> None:
    root, config, console = make_tree(tmp_path)
    runtime = discover_runtime(
        install_root=root,
        config_dir=config,
        console=console,
        environ={},
        native_platform=True,
    )
    assert runtime.mode == "native"
    assert runtime.wine is None
    assert runtime.command(("--help",)) == (str(console), "--help")


def test_wine_discovery_prefixes_the_console(tmp_path: Path) -> None:
    root, config, console = make_tree(tmp_path)
    wine = make_wine(tmp_path)
    runtime = discover_runtime(
        install_root=root,
        config_dir=config,
        console=console,
        wine=wine,
        environ={},
        native_platform=False,
    )
    assert runtime.mode == "wine"
    assert runtime.wine_version == "wine-9.0"
    assert runtime.command(("-i", "in")) == (str(wine), str(console), "-i", "in")


def test_discovery_reads_environment_and_finds_console_case_insensitively(
    tmp_path: Path,
) -> None:
    root, config, console = make_tree(tmp_path)
    lower = root / "vdyp7console.EXE"
    console.rename(lower)
    wine = make_wine(tmp_path)
    runtime = discover_runtime(
        environ={
            "VDYP_INSTALL": str(root),
            "VDYP_CFG_DIR": str(config),
            "WINE": str(wine),
        },
        native_platform=False,
    )
    assert runtime.console == lower
    assert runtime.mode == "wine"
    assert runtime.config_dir == config


def test_discovery_requires_a_console(tmp_path: Path) -> None:
    with pytest.raises(RuntimeUnavailableError, match="MISSING-CONSOLE"):
        discover_runtime(environ={}, native_platform=False)


def test_unavailable_mode_is_reported(tmp_path: Path) -> None:
    root, config, console = make_tree(tmp_path)
    runtime = discover_runtime(
        install_root=root,
        config_dir=config,
        console=console,
        environ={},
        native_platform=False,
    )
    assert runtime.mode == "unavailable"
    assert "RUNTIME-UNAVAILABLE" in {finding.code for finding in check_runtime(runtime)}
    with pytest.raises(RuntimeUnavailableError):
        runtime.command(())


def test_check_reports_missing_pieces(tmp_path: Path) -> None:
    console = tmp_path / "missing.exe"
    config = tmp_path / "missing-config"
    runtime = info("wine", console, config)
    codes = {finding.code for finding in check_runtime(runtime)}
    assert {"MISSING-CONSOLE", "MISSING-CONFIG", "MISSING-WINE"} <= codes


def test_check_accepts_a_complete_runtime(tmp_path: Path) -> None:
    root, config, console = make_tree(tmp_path)
    runtime = discover_runtime(
        install_root=root,
        config_dir=config,
        console=console,
        environ={},
        native_platform=True,
    )
    assert check_runtime(runtime) == ()


def test_detect_wine_version_reads_the_command(tmp_path: Path) -> None:
    assert detect_wine_version(make_wine(tmp_path)) == "wine-9.0"


def test_detect_wine_version_handles_a_missing_binary(tmp_path: Path) -> None:
    assert detect_wine_version(tmp_path / "absent") == ""


def test_cli_check_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, config, _ = make_tree(tmp_path)
    wine = make_wine(tmp_path)
    monkeypatch.setenv("VDYP_INSTALL", str(root))
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    monkeypatch.setenv("WINE", str(wine))
    output = tmp_path / "runtime.json"
    assert main(["--check", "--json", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["wine_version"] == "wine-9.0"
    assert "mode: wine" in capsys.readouterr().out


def test_cli_without_a_console_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("VDYP_CONSOLE", raising=False)
    monkeypatch.delenv("VDYP_INSTALL", raising=False)
    assert main(["--check"]) == 2
    assert "MISSING-CONSOLE" in capsys.readouterr().err


def test_cli_with_a_missing_config_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _root, _config, console = make_tree(tmp_path)
    monkeypatch.setenv("VDYP_CONSOLE", str(console))
    monkeypatch.setenv("VDYP_CFG_DIR", str(tmp_path / "absent"))
    monkeypatch.setenv("WINE", str(make_wine(tmp_path)))
    assert main(["--check"]) == 1
    assert "MISSING-CONFIG" in capsys.readouterr().out
