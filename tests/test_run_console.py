"""Tests for the isolated console runner and failure records."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from run_console import (
    build_parameters,
    main,
    run_console,
    write_record,
)
from vdyp_runtime import RuntimeInfo


def make_console(tmp_path: Path, *, body: str | None = None) -> Path:
    console = tmp_path / "VDYP7Console.exe"
    script = body or (
        "#!/bin/sh\n"
        'out=""\n'
        'err=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in\n'
        '    -o) out="$2"; shift 2 ;;\n'
        '    -e) err="$2"; shift 2 ;;\n'
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        'echo "fake stdout"\n'
        'echo "fake stderr" >&2\n'
        'printf "a,b\\n1,2\\n" > "$out"\n'
        'printf "no errors\\n" > "$err"\n'
        "exit 0\n"
    )
    console.write_text(script, encoding="utf-8")
    console.chmod(0o755)
    return console


def make_runtime(tmp_path: Path, console: Path) -> RuntimeInfo:
    config = tmp_path / "VDYP_CFG"
    config.mkdir(exist_ok=True)
    return RuntimeInfo(
        mode="native",
        console=console,
        config_dir=config,
        install_root=tmp_path,
        wine=None,
        wine_version="",
    )


def make_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "POLYGON.csv").write_text("a\n1\n", encoding="ascii")
    return input_dir


def test_build_parameters_without_ini() -> None:
    parameters = build_parameters(
        config_dir=Path("cfg"),
        output_format="CSVYieldTable",
        has_ini=False,
        extra_args=("-inc", "1"),
    )
    assert "-ini" not in parameters
    assert parameters[-2:] == ("-inc", "1")
    assert "CSVYieldTable" in parameters


def test_build_parameters_with_ini() -> None:
    parameters = build_parameters(
        config_dir=Path("cfg"), output_format="CSVYieldTable", has_ini=True
    )
    assert parameters[:2] == ("-ini", "VDYP.INI")


def test_successful_run_captures_everything(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)
    record = run_console(
        runtime,
        input_dir=make_input(tmp_path),
        work_dir=tmp_path / "work",
    )
    assert record.status == "success"
    assert record.exit_code == 0
    assert record.failure_code == ""
    assert record.stdout.strip() == "fake stdout"
    assert record.stderr.strip() == "fake stderr"
    assert record.output_bytes > 0
    assert len(record.output_sha256) == 64
    assert record.error_file == "ConsoleErrors.txt"
    assert (tmp_path / "work" / "ConsoleOutput.txt").is_file()
    assert (tmp_path / "work" / "Console" / "POLYGON.csv").is_file()


def test_nonzero_exit_is_a_failure(tmp_path: Path) -> None:
    console = make_console(
        tmp_path,
        body="#!/bin/sh\necho oops >&2\nexit 3\n",
    )
    runtime = make_runtime(tmp_path, console)
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    assert record.status == "failed"
    assert record.failure_code == "NONZERO-EXIT"
    assert record.exit_code == 3
    assert "oops" in record.stderr


def test_zero_exit_without_output_is_a_failure(tmp_path: Path) -> None:
    console = make_console(tmp_path, body="#!/bin/sh\nexit 0\n")
    runtime = make_runtime(tmp_path, console)
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    assert record.status == "failed"
    assert record.failure_code == "MISSING-OUTPUT"


def test_missing_input_is_a_failure(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)
    record = run_console(runtime, input_dir=tmp_path / "absent", work_dir=tmp_path / "work")
    assert record.failure_code == "MISSING-INPUT"


def test_missing_config_is_a_failure(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)
    record = run_console(
        runtime,
        input_dir=make_input(tmp_path),
        work_dir=tmp_path / "work",
        config_dir=tmp_path / "absent-config",
    )
    assert record.failure_code == "MISSING-CONFIG"


def test_missing_console_is_a_failure(tmp_path: Path) -> None:
    runtime = make_runtime(tmp_path, tmp_path / "absent.exe")
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    assert record.failure_code == "MISSING-CONSOLE"


def test_timeout_is_a_failure(tmp_path: Path) -> None:
    console = make_console(tmp_path, body="#!/bin/sh\nsleep 5\n")
    runtime = make_runtime(tmp_path, console)
    record = run_console(
        runtime,
        input_dir=make_input(tmp_path),
        work_dir=tmp_path / "work",
        timeout=0.5,
    )
    assert record.failure_code == "TIMEOUT"


def test_unavailable_runtime_is_a_failure(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    config = tmp_path / "VDYP_CFG"
    config.mkdir(exist_ok=True)
    runtime = RuntimeInfo(
        mode="unavailable",
        console=console,
        config_dir=config,
        install_root=tmp_path,
        wine=None,
        wine_version="",
    )
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    assert record.failure_code == "RUNTIME-UNAVAILABLE"


def test_write_record(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    output = tmp_path / "record.json"
    write_record(record, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["command"][0] == str(console)


def make_wine(tmp_path: Path) -> Path:
    wine = tmp_path / "wine"
    wine.write_text('#!/bin/sh\nexec "$@"\n', encoding="utf-8")
    wine.chmod(0o755)
    return wine


def test_cli_records_a_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    console = make_console(tmp_path)
    config = tmp_path / "VDYP_CFG"
    config.mkdir()
    monkeypatch.setenv("VDYP_CONSOLE", str(console))
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    monkeypatch.setenv("WINE", str(make_wine(tmp_path)))
    record_path = tmp_path / "record.json"
    result = main(
        [
            "--input-dir",
            str(make_input(tmp_path)),
            "--work-dir",
            str(tmp_path / "work"),
            "--json",
            str(record_path),
        ]
    )
    assert result == 0
    assert json.loads(record_path.read_text(encoding="utf-8"))["status"] == "success"
    assert "status: success" in capsys.readouterr().out


def test_ini_is_copied_into_the_work_dir(tmp_path: Path) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)
    ini = tmp_path / "VDYP.INI"
    ini.write_text("[section]\n", encoding="ascii")
    record = run_console(
        runtime,
        input_dir=make_input(tmp_path),
        work_dir=tmp_path / "work",
        ini_path=ini,
    )
    assert record.status == "success"
    assert (tmp_path / "work" / "VDYP.INI").is_file()


def test_oserror_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    console = make_console(tmp_path)
    runtime = make_runtime(tmp_path, console)

    def raise_oserror(*args: object, **kwargs: object) -> None:
        raise OSError("cannot execute")

    monkeypatch.setattr("run_console.subprocess.run", raise_oserror)
    record = run_console(runtime, input_dir=make_input(tmp_path), work_dir=tmp_path / "work")
    assert record.failure_code == "RUNTIME-UNAVAILABLE"


def test_cli_without_a_runtime_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_CONSOLE", raising=False)
    monkeypatch.delenv("VDYP_INSTALL", raising=False)
    assert (
        main(["--input-dir", str(make_input(tmp_path)), "--work-dir", str(tmp_path / "work")]) == 2
    )
    assert "MISSING-CONSOLE" in capsys.readouterr().err


def test_cli_failure_without_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    console = make_console(tmp_path, body="#!/bin/sh\nexit 4\n")
    config = tmp_path / "VDYP_CFG"
    config.mkdir()
    monkeypatch.setenv("VDYP_CONSOLE", str(console))
    monkeypatch.setenv("VDYP_CFG_DIR", str(config))
    monkeypatch.setenv("WINE", str(make_wine(tmp_path)))
    result = main(["--input-dir", str(make_input(tmp_path)), "--work-dir", str(tmp_path / "work")])
    assert result == 1
    assert "failure: NONZERO-EXIT" in capsys.readouterr().out
