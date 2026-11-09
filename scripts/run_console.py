#!/usr/bin/env python3
"""Run ``VDYP7Console`` in an isolated directory and capture every stream.

The runner copies the input tree and ``VDYP_CFG`` into a temporary working
directory, builds the console command through :mod:`vdyp_runtime`, captures
stdout and stderr, and records the output and error files. A failed run is a
recorded finding with a stable code; it never falls back to generated curves.

Command-line usage::

    python scripts/run_console.py --input-dir fixtures/console-input \
        --work-dir runtime/console-run --json runtime/console-run/record.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from normalize import utc_now
from vdyp_runtime import RuntimeInfo, RuntimeUnavailableError, discover_runtime

OUTPUT_NAME = "ConsoleOutput.txt"
ERROR_NAME = "ConsoleErrors.txt"
DEFAULT_TIMEOUT = 300.0
RunStatus = Literal["success", "failed"]


@dataclass(frozen=True)
class RunRecord:
    """The evidence from one console run.

    Attributes
    ----------
    status : {"success", "failed"}
        Whether the run produced a non-empty output file with exit status 0.
    failure_code : str
        Stable failure code, empty on success.
    failure_message : str
        Human-readable failure detail, empty on success.
    exit_code : int
        Process exit status, or ``-1`` when the process could not start.
    mode : str
        Runtime mode from :class:`vdyp_runtime.RuntimeInfo`.
    command : tuple of str
        Command vector that was executed.
    work_dir : str
        Working-directory name, without its parent path.
    stdout : str
        Captured standard output.
    stderr : str
        Captured standard error.
    output_file : str
        Output file name, empty when it was not created.
    output_bytes : int
        Output file size.
    output_sha256 : str
        Output file SHA256, empty when it was not created.
    error_file : str
        Error file name, empty when it was not created.
    error_bytes : int
        Error file size.
    started_at_utc : str
        ISO 8601 UTC start time.
    duration_seconds : float
        Wall-clock duration.
    """

    status: RunStatus
    failure_code: str
    failure_message: str
    exit_code: int
    mode: str
    command: tuple[str, ...]
    work_dir: str
    stdout: str
    stderr: str
    output_file: str
    output_bytes: int
    output_sha256: str
    error_file: str
    error_bytes: int
    started_at_utc: str
    duration_seconds: float

    def to_dict(self) -> dict[str, object]:
        """Render the record as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The status, command, streams, and file evidence.
        """
        return {
            "status": self.status,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "exit_code": self.exit_code,
            "mode": self.mode,
            "command": list(self.command),
            "work_dir": self.work_dir,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output_file": self.output_file,
            "output_bytes": self.output_bytes,
            "output_sha256": self.output_sha256,
            "error_file": self.error_file,
            "error_bytes": self.error_bytes,
            "started_at_utc": self.started_at_utc,
            "duration_seconds": self.duration_seconds,
        }


def sha256_file(path: Path) -> str:
    """Hash one captured file.

    Parameters
    ----------
    path : Path
        File to hash.

    Returns
    -------
    str
        Lowercase hexadecimal SHA256.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def build_parameters(
    *,
    output_format: str,
    has_ini: bool,
    extra_args: Sequence[str] = (),
) -> tuple[str, ...]:
    """Build the console argument vector.

    Parameters
    ----------
    output_format : str
        Output format passed with ``-ofmt``.
    has_ini : bool
        Whether ``VDYP.INI`` was copied into the working directory.
    extra_args : sequence of str, optional
        Additional console arguments.

    Returns
    -------
    tuple of str
        Arguments after the executable. The configuration is always the copied
        ``VDYP_CFG`` directory in the working directory.
    """
    parameters: list[str] = []
    if has_ini:
        parameters.extend(("-ini", "VDYP.INI"))
    parameters.extend(
        (
            "-i",
            "Console",
            "-o",
            OUTPUT_NAME,
            "-e",
            ERROR_NAME,
            "-c",
            "VDYP_CFG\\",
            "-d",
            ".",
            "-ofmt",
            output_format,
            "-agestart",
            "0",
            "-ageend",
            "300",
            "-inc",
            "1",
            "-forcerefyear",
            "Yes",
            "-includeyearrows",
            "No",
            "-progressFrequency",
            "Never",
        )
    )
    parameters.extend(extra_args)
    return tuple(parameters)


def failure_record(
    *,
    code: str,
    message: str,
    mode: str,
    command: Sequence[str] = (),
    work_dir: Path,
    started_at: str,
    started: float,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = -1,
) -> RunRecord:
    """Build a failed run record.

    Parameters
    ----------
    code : str
        Stable failure code.
    message : str
        Human-readable detail.
    mode : str
        Runtime mode.
    command : sequence of str, optional
        Command vector, empty when it was never built.
    work_dir : Path
        Working directory.
    started_at : str
        ISO 8601 UTC start time.
    started : float
        ``time.perf_counter`` value from the start.
    stdout : str, optional
        Captured standard output.
    stderr : str, optional
        Captured standard error.
    exit_code : int, optional
        Exit status, ``-1`` when the process did not start.

    Returns
    -------
    RunRecord
        A record with status ``failed``.
    """
    return RunRecord(
        status="failed",
        failure_code=code,
        failure_message=message,
        exit_code=exit_code,
        mode=mode,
        command=tuple(command),
        work_dir=work_dir.name,
        stdout=stdout,
        stderr=stderr,
        output_file="",
        output_bytes=0,
        output_sha256="",
        error_file="",
        error_bytes=0,
        started_at_utc=started_at,
        duration_seconds=round(time.perf_counter() - started, 2),
    )


def run_console(
    runtime: RuntimeInfo,
    *,
    input_dir: Path,
    work_dir: Path,
    config_dir: Path | None = None,
    ini_path: Path | None = None,
    output_format: str = "CSVYieldTable",
    extra_args: Sequence[str] = (),
    timeout: float = DEFAULT_TIMEOUT,
) -> RunRecord:
    """Run the console once and capture its evidence.

    Parameters
    ----------
    runtime : RuntimeInfo
        Discovered runtime.
    input_dir : Path
        Directory copied to ``work_dir/Console``.
    work_dir : Path
        Isolated working directory. Created when absent.
    config_dir : Path or None, optional
        Configuration directory. Defaults to ``runtime.config_dir``.
    ini_path : Path or None, optional
        ``VDYP.INI`` to copy into the working directory.
    output_format : str, optional
        Console output format.
    extra_args : sequence of str, optional
        Additional console arguments.
    timeout : float, optional
        Seconds before the process is terminated.

    Returns
    -------
    RunRecord
        Success or failure evidence. A missing output file is a failure even
        when the process exits 0.
    """
    started_at = utc_now()
    started = time.perf_counter()
    config = config_dir if config_dir is not None else runtime.config_dir
    if not runtime.console.is_file():
        return failure_record(
            code="MISSING-CONSOLE",
            message="console executable does not exist",
            mode=runtime.mode,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
        )
    if not config.is_dir():
        return failure_record(
            code="MISSING-CONFIG",
            message="configuration directory does not exist",
            mode=runtime.mode,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
        )
    if not input_dir.is_dir():
        return failure_record(
            code="MISSING-INPUT",
            message="input directory does not exist",
            mode=runtime.mode,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
        )
    work_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(input_dir, work_dir / "Console", dirs_exist_ok=True)
    shutil.copytree(config, work_dir / "VDYP_CFG", dirs_exist_ok=True)
    has_ini = ini_path is not None and ini_path.is_file()
    if has_ini and ini_path is not None:
        shutil.copy2(ini_path, work_dir / "VDYP.INI")
    parameters = build_parameters(
        output_format=output_format,
        has_ini=has_ini,
        extra_args=extra_args,
    )
    try:
        command = runtime.command(parameters)
    except RuntimeUnavailableError as exc:
        return failure_record(
            code=exc.code,
            message=exc.message,
            mode=runtime.mode,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
        )
    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return failure_record(
            code="TIMEOUT",
            message=f"console exceeded {timeout} seconds",
            mode=runtime.mode,
            command=command,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
            stdout=stdout,
            stderr=stderr,
        )
    except OSError as exc:
        return failure_record(
            code="RUNTIME-UNAVAILABLE",
            message=str(exc),
            mode=runtime.mode,
            command=command,
            work_dir=work_dir,
            started_at=started_at,
            started=started,
        )
    output_path = work_dir / OUTPUT_NAME
    error_path = work_dir / ERROR_NAME
    output_exists = output_path.is_file()
    output_bytes = output_path.stat().st_size if output_exists else 0
    error_exists = error_path.is_file()
    error_bytes = error_path.stat().st_size if error_exists else 0
    if completed.returncode != 0:
        status: RunStatus = "failed"
        code = "NONZERO-EXIT"
        message = f"console exited with status {completed.returncode}"
    elif not output_exists or output_bytes == 0:
        status = "failed"
        code = "MISSING-OUTPUT"
        message = "console exited 0 but produced no output file"
    else:
        status = "success"
        code = ""
        message = ""
    return RunRecord(
        status=status,
        failure_code=code,
        failure_message=message,
        exit_code=completed.returncode,
        mode=runtime.mode,
        command=command,
        work_dir=work_dir.name,
        stdout=completed.stdout,
        stderr=completed.stderr,
        output_file=OUTPUT_NAME if output_exists else "",
        output_bytes=output_bytes,
        output_sha256=sha256_file(output_path) if output_exists else "",
        error_file=ERROR_NAME if error_exists else "",
        error_bytes=error_bytes,
        started_at_utc=started_at,
        duration_seconds=round(time.perf_counter() - started, 2),
    )


def write_record(record: RunRecord, output: Path) -> None:
    """Write a run record as pretty JSON.

    Parameters
    ----------
    record : RunRecord
        Record to serialize.
    output : Path
        Destination file. Missing parent directories are created.

    Returns
    -------
    None
        The record is written to ``output``.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the console from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` on a successful run, ``1`` on a recorded failure, and ``2`` when
        the runtime cannot be discovered.
    """
    parser = argparse.ArgumentParser(description="Run VDYP7Console and record the evidence.")
    parser.add_argument("--input-dir", type=Path, required=True, help="console input tree")
    parser.add_argument("--work-dir", type=Path, required=True, help="isolated working directory")
    parser.add_argument("--config-dir", type=Path, help="VDYP_CFG directory; defaults to env")
    parser.add_argument("--ini", type=Path, help="VDYP.INI to copy into the working directory")
    parser.add_argument("--output-format", default="CSVYieldTable", help="console output format")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds")
    parser.add_argument("--json", type=Path, help="run record path")
    args = parser.parse_args(argv)
    try:
        runtime = discover_runtime(config_dir=args.config_dir)
    except RuntimeUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    record = run_console(
        runtime,
        input_dir=args.input_dir,
        work_dir=args.work_dir,
        config_dir=args.config_dir,
        ini_path=args.ini,
        output_format=args.output_format,
        timeout=args.timeout,
    )
    if args.json is not None:
        write_record(record, args.json)
    print(f"status: {record.status}")
    if record.failure_code:
        print(f"failure: {record.failure_code} - {record.failure_message}")
    print(f"exit: {record.exit_code}")
    print(f"output: {record.output_file} ({record.output_bytes} bytes)")
    return 0 if record.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
