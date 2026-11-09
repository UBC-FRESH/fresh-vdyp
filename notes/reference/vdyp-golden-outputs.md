# VDYP7 console-output inventory

Date: 2026-11-09
Status: observed from the local install; not reproduced by `fresh-vdyp`
Runtime: not exercised

The local installation ships one console sample run inside `console_input.zip`
and two root-level log or error files. They are candidate golden outputs for
Phase 3, not validated fixtures. None of these files is committed.

## Candidate outputs

| Artifact | Container | Size (bytes) | SHA256 | Status |
| --- | --- | ---: | --- | --- |
| `console_input.zip` | install root | 777322 | `cc9dc24db1bb81574c969d9cf773b51dfaee70da1f6ea2538983fb2620ae6639` | Archive; do not commit |
| `console_input/ConsoleOutput.txt` | `console_input.zip` | 50510 | `e7b9f11931352de0aa4febc2e4470ef7d5feff47c0d0203b47ea5fe323c81320` | Formatted yield table, run completed 2021-01-15 18:45:21 |
| `console_input/ConsoleErrors.txt` | `console_input.zip` | 3768 | `aebdcb23583215238df720fbe24986b21cd279db4db2de59f8700f0520f60386` | Informational messages for the same run |
| `console_input/Params-Console.txt` | `console_input.zip` | 764 | `cd82169cbd1fcff4ee21ebf793861057f64d8e18d5eae4a5724fb1fc4ba86f7a` | Command-line arguments for the same run |
| `console_input/loggingOutput.txt` | `console_input.zip` | 16260383 | `091553a2c461948f758dc6ec80eebe192a713b988cb87f5bc9e51a87eb8a5099` | Large debug log; do not commit |
| `loggingOutput.txt` | install root | 30249 | `6d002eec2e8134e558d263e09e2641a24cb9570c87c690e15874837973bde972` | Root log from a separate run |
| `ConsoleErrors.txt` | install root | 95 | `e6843d42ab6de6292add14d3671386d06feb5d33052c11e604b385ffd24162a3` | Failed run: `FILE_NOT_FOUND` for `.\Console` |

## Run versions in `ConsoleOutput.txt`

```text
VDYP7 Console:                    7.16k
VDYP7 Extended Core DLL:          7.28l
VDYP7CORE DLL:                    7.19f
Supporting Calc Library:          7.1g 2016-Jan-27
VDYP7 Low Level I/O DLL:          7.23d
VDYP SI Wrapper:                  7.12j
SINDEX:                           1.51
```

## Limits

- The archive output is a formatted text table, not `csvyieldtable` CSV output.
  Phase 3 must produce and parse the CSV form against this runtime.
- `fresh-vdyp` has not reproduced any of these outputs. They are evidence that a
  run once succeeded, not a validated golden fixture.
- The root `ConsoleErrors.txt` is a failed-run record: the input path `.\Console`
  was missing. It is kept as a failure example, not as a success case.
