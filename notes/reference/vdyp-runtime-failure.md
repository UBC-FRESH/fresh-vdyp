# VDYP7 console runtime failure

Date: 2026-11-09
Host: Linux x86_64, Ubuntu 24.04 userland
Wine: `wine-9.0 (Ubuntu 9.0~repack-4build3)`
Status: **resolved on 2026-11-09 by WineHQ stable 11.0**; the console then ran successfully. The original failure is kept below as history.

## Resolution

WineHQ stable 11.0 was installed on 2026-11-09 after distro Wine 9.0 failed at
startup. `wine cmd /c echo hi` then returned 0, and `VDYP7Console.exe` accepted
the synthetic fixture. The first successful run produced 301 rows and exit 0.

## What happened

Every attempt to start a Windows process under Wine ended with a core dump:

```text
free(): invalid pointer
timeout: the monitored command dumped core
```

Exit status was 134 (SIGABRT) or 139 (SIGSEGV). `wine --version` succeeds, and
Wine creates the prefix directory, then the first process crashes.

## Commands tried

```bash
# The console itself
wine "$VDYP_INSTALL/VDYP7Console.exe"

# A built-in command, to separate Wine from the console
wine cmd /c echo hi

# Explicit 32-bit prefix
WINEARCH=win32 WINEPREFIX="$HOME/.wine-test32" wine cmd /c echo hi

# 64-bit loader
/usr/lib/wine/wine64 cmd /c echo hi

# Different filesystems and prefixes
WINEPREFIX=/dev/shm/gep-wine wine cmd /c echo hi
WINEPREFIX=/var/tmp/gep-wine wine cmd /c echo hi
```

All of them failed the same way. `libwine:amd64`, `libwine:i386`, `wine32`, and
`wine64` are installed, and `ldd` reports no missing libraries.

## Diagnosis

This is a **host Wine failure**, not a VDYP model failure. Because `wine cmd`
also crashes, the console binary itself is not implicated.

## Consequence

- No `VDYP7Console` run was produced.
- No yield table or curve was generated or invented.
- The synthetic input fixture in `fixtures/console-input/` is not yet accepted
  by a console run.
- P3.3 (run and capture), P3.5 (golden output), and the run half of P3.6 are
  blocked on this host.

## Runner reproduction

`scripts/run_console.py` isolated the input, copied `VDYP.INI`, and ran the
console through the adapter. The record is:

```text
status: failed
failure_code: NONZERO-EXIT
exit_code: -6          (SIGABRT)
mode: wine
stdout: (empty)
stderr: free(): invalid pointer
output: (not created)
errors: (not created)
```

The runner wrote no curve, and the record is kept outside the repository.

## What is needed to proceed

A working 32-bit Wine runtime, a Windows host, or a container image with a
functioning Wine. Then:

1. Run the synthetic fixture with `-ofmt CSVYieldTable`.
2. Capture `ConsoleOutput.txt`, `ConsoleErrors.txt`, and the CSV output.
3. Reproduce the run twice and compare.
4. Record the runtime version and the exact command.

A failed run stays a finding. No Python curve is substituted for it.
