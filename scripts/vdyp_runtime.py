#!/usr/bin/env python3
"""Discover a VDYP7 console runtime and build its command vector.

The adapter supports native Windows execution and Linux through Wine. It reads
``VDYP_INSTALL``, ``VDYP_CFG_DIR``, ``VDYP_CONSOLE``, and ``WINE``, never a
hard-coded host path. The command remains a vector so the runner controls the
working directory.

Command-line usage::

    python scripts/vdyp_runtime.py --check
    python scripts/vdyp_runtime.py --check --json runtime.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RuntimeMode = Literal["native", "wine", "unavailable"]
CONSOLE_NAME = "VDYP7Console.exe"


@dataclass(frozen=True)
class RuntimeInfo:
    """The discovered runtime and its command inputs.

    Attributes
    ----------
    mode : {"native", "wine", "unavailable"}
        Execution mode.
    console : Path
        Console executable.
    config_dir : Path
        VDYP configuration directory.
    install_root : Path
        Installation root.
    wine : Path or None
        Wine executable in ``wine`` mode.
    wine_version : str
        Reported Wine version, or an empty string.
    """

    mode: RuntimeMode
    console: Path
    config_dir: Path
    install_root: Path
    wine: Path | None
    wine_version: str

    def to_dict(self) -> dict[str, object]:
        """Render the runtime as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            The mode, paths, and Wine version.
        """
        return {
            "mode": self.mode,
            "console": str(self.console),
            "config_dir": str(self.config_dir),
            "install_root": str(self.install_root),
            "wine": str(self.wine) if self.wine is not None else "",
            "wine_version": self.wine_version,
        }

    def command(self, parameters: Sequence[str]) -> tuple[str, ...]:
        """Build the console command vector.

        Parameters
        ----------
        parameters : sequence of str
            Console arguments after the executable.

        Returns
        -------
        tuple of str
            The executable vector, prefixed by Wine in Wine mode.

        Raises
        ------
        RuntimeUnavailableError
            When the runtime mode cannot run a command.
        """
        if self.mode == "native":
            return (str(self.console), *parameters)
        if self.mode == "wine" and self.wine is not None:
            return (str(self.wine), str(self.console), *parameters)
        raise RuntimeUnavailableError("RUNTIME-UNAVAILABLE", "no native or Wine runtime available")


@dataclass(frozen=True)
class RuntimeCheck:
    """One finding from a runtime check.

    Attributes
    ----------
    severity : {"error", "warning"}
        Whether the finding blocks a run.
    code : str
        Stable finding code.
    message : str
        Explanation of the finding.
    """

    severity: Literal["error", "warning"]
    code: str
    message: str

    def render(self) -> str:
        """Render the finding as one line of text.

        Returns
        -------
        str
            Severity, code, and message, padded into columns.
        """
        return f"{self.severity:<8}{self.code:<24}{self.message}"


class RuntimeUnavailableError(RuntimeError):
    """Raised when discovery cannot produce a usable runtime.

    Parameters
    ----------
    code : str
        Stable failure code.
    message : str
        Explanation of the missing piece.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def find_ci(directory: Path, name: str) -> Path | None:
    """Find a file by name, ignoring case.

    Parameters
    ----------
    directory : Path
        Directory to search.
    name : str
        File name to match.

    Returns
    -------
    Path or None
        The matching file, or ``None`` when it is absent.
    """
    target = name.lower()
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.name.lower() == target:
            return path
    return None


def detect_wine_version(wine: Path) -> str:
    """Ask a Wine executable for its version.

    Parameters
    ----------
    wine : Path
        Wine executable.

    Returns
    -------
    str
        First line of ``wine --version``, or an empty string on failure.
    """
    try:
        completed = subprocess.run(
            [str(wine), "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""


def discover_runtime(
    *,
    install_root: Path | None = None,
    config_dir: Path | None = None,
    console: Path | None = None,
    wine: Path | None = None,
    environ: Mapping[str, str] | None = None,
    native_platform: bool | None = None,
) -> RuntimeInfo:
    """Discover the runtime from arguments and documented environment variables.

    Parameters
    ----------
    install_root : Path or None, optional
        Installation root. Defaults to ``VDYP_INSTALL``.
    config_dir : Path or None, optional
        Configuration directory. Defaults to ``VDYP_CFG_DIR`` or
        ``install_root/VDYP_CFG``.
    console : Path or None, optional
        Console executable. Defaults to ``VDYP_CONSOLE`` or a case-insensitive
        search for ``VDYP7Console.exe``.
    wine : Path or None, optional
        Wine executable. Defaults to ``WINE`` or ``shutil.which("wine")``.
    environ : mapping of str to str or None, optional
        Environment to read. Defaults to ``os.environ``. When a mapping is
        supplied, the PATH search for Wine is disabled so tests stay
        deterministic.
    native_platform : bool or None, optional
        Force native-Windows detection. Defaults to ``os.name == "nt"``.

    Returns
    -------
    RuntimeInfo
        The discovered runtime.

    Raises
    ------
    RuntimeUnavailableError
        When the console or configuration directory cannot be found.
    """
    env = os.environ if environ is None else environ
    root_value = install_root if install_root is not None else env.get("VDYP_INSTALL")
    root = Path(root_value) if root_value else None
    console_value = console if console is not None else env.get("VDYP_CONSOLE")
    selected_console = Path(console_value) if console_value else None
    if selected_console is None and root is not None:
        selected_console = find_ci(root, CONSOLE_NAME)
    if selected_console is None:
        raise RuntimeUnavailableError(
            "MISSING-CONSOLE", "VDYP7Console.exe is not set and was not found"
        )
    if root is None:
        root = selected_console.parent
    config_value = config_dir if config_dir is not None else env.get("VDYP_CFG_DIR")
    selected_config = Path(config_value) if config_value else root / "VDYP_CFG"
    native = os.name == "nt" if native_platform is None else native_platform
    wine_value = wine if wine is not None else env.get("WINE")
    selected_wine = Path(wine_value) if wine_value else None
    if selected_wine is None and not native and environ is None:
        found = shutil.which("wine")
        selected_wine = Path(found) if found else None
    if native:
        mode: RuntimeMode = "native"
        selected_wine = None
    elif selected_wine is not None:
        mode = "wine"
    else:
        mode = "unavailable"
    version = detect_wine_version(selected_wine) if selected_wine is not None else ""
    return RuntimeInfo(
        mode=mode,
        console=selected_console,
        config_dir=selected_config,
        install_root=root,
        wine=selected_wine,
        wine_version=version,
    )


def check_runtime(info: RuntimeInfo) -> tuple[RuntimeCheck, ...]:
    """Check that a discovered runtime can actually run.

    Parameters
    ----------
    info : RuntimeInfo
        Runtime to check.

    Returns
    -------
    tuple of RuntimeCheck
        Errors and warnings. An empty tuple means the runtime is ready.
    """
    findings: list[RuntimeCheck] = []
    if not info.console.is_file():
        findings.append(
            RuntimeCheck("error", "MISSING-CONSOLE", f"console not found: {info.console.name}")
        )
    if not info.config_dir.is_dir():
        findings.append(
            RuntimeCheck(
                "error",
                "MISSING-CONFIG",
                f"configuration directory not found: {info.config_dir.name}",
            )
        )
    if info.mode == "unavailable":
        findings.append(
            RuntimeCheck("error", "RUNTIME-UNAVAILABLE", "no native or Wine runtime found")
        )
    if info.mode == "wine" and (info.wine is None or not info.wine.is_file()):
        findings.append(RuntimeCheck("error", "MISSING-WINE", "Wine executable not found"))
    if info.mode == "wine" and not info.wine_version:
        findings.append(
            RuntimeCheck("warning", "UNKNOWN-WINE-VERSION", "Wine did not report a version")
        )
    return tuple(findings)


def main(argv: Sequence[str] | None = None) -> int:
    """Check the runtime from the command line.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Arguments to parse. ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the runtime is ready, ``1`` when a check fails, and ``2``
        when discovery cannot find the console.
    """
    parser = argparse.ArgumentParser(description="Discover and check the VDYP7 console runtime.")
    parser.add_argument("--check", action="store_true", help="check the runtime")
    parser.add_argument("--json", type=Path, help="also write the runtime record")
    args = parser.parse_args(argv)
    try:
        info = discover_runtime()
    except RuntimeUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = check_runtime(info)
    for finding in findings:
        print(finding.render())
    print(f"mode: {info.mode}")
    print(f"console: {info.console.name}")
    print(f"config: {info.config_dir.name}")
    if info.wine_version:
        print(f"wine: {info.wine_version}")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(info.to_dict(), indent=2) + "\n", encoding="utf-8")
    errors = sum(1 for finding in findings if finding.severity == "error")
    print(f"{errors} error(s), {len(findings) - errors} warning(s)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
