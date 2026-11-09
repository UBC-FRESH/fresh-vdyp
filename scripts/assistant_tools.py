#!/usr/bin/env python3
"""Bounded assistant tools over the catalog, curves, provenance, and matrix.

Every handler is deterministic and returns an :class:`AssistantAnswer` with at
least one source. The validator rejects an answer without a source, so an
assistant cannot present a coefficient, equation, or curve without attribution.
No network or model provider is used.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from bundle_service import catalog_payload
from curve_api import CurveQuery, CurveService
from yield_parser import DEFAULT_ALIASES, DEFAULT_SCHEMA

DEFAULT_MATRIX: Final[Path] = Path("notes/reference/vdyp-equation-matrix.json")


class AssistantAnswerError(ValueError):
    """Raised when an answer has no usable source."""


@dataclass(frozen=True)
class ToolSpec:
    """The schema of one assistant tool.

    Attributes
    ----------
    name : str
        Tool name.
    description : str
        What the tool answers.
    parameters : dict of str to str
        Parameter names and their descriptions.
    """

    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantAnswer:
    """One source-backed assistant answer.

    Attributes
    ----------
    text : str
        Short answer text.
    sources : tuple of str
        Source labels. Must be non-empty.
    data : dict of str to object
        Structured result for a caller.
    """

    text: str
    sources: tuple[str, ...]
    data: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Render the answer as a JSON-ready mapping.

        Returns
        -------
        dict of str to object
            Text, sources, and data.
        """
        return {"text": self.text, "sources": list(self.sources), "data": self.data}


TOOL_SPECS: Final[tuple[ToolSpec, ...]] = (
    ToolSpec(
        "catalog_search",
        "Search the coefficient catalog by family, equation family, or status.",
        {"query": "case-insensitive text"},
    ),
    ToolSpec(
        "curve_query",
        "Query the typed curve service with optional species/year/age filters.",
        {
            "species": "species code",
            "year_start": "int",
            "year_end": "int",
            "age_start": "int",
            "age_end": "int",
        },
    ),
    ToolSpec(
        "provenance_lookup",
        "Return the source and runtime provenance of the loaded curve table.",
        {},
    ),
    ToolSpec(
        "validation_status",
        "Return the validation status of one equation family.",
        {"family": "family name"},
    ),
)


def validate_answer(answer: AssistantAnswer) -> None:
    """Validate that an answer names at least one source.

    Parameters
    ----------
    answer : AssistantAnswer
        Answer to validate.

    Returns
    -------
    None
        The answer is source-backed.

    Raises
    ------
    AssistantAnswerError
        When the source tuple is empty or contains a blank label.
    """
    if not answer.sources:
        raise AssistantAnswerError("answer has no source")
    if any(not source.strip() for source in answer.sources):
        raise AssistantAnswerError("answer has a blank source")


def catalog_search(config_dir: Path, query: str) -> AssistantAnswer:
    """Search the catalog and return matching families with their source files.

    Parameters
    ----------
    config_dir : Path
        VDYP_CFG directory.
    query : str
        Case-insensitive family, equation-family, or status text.

    Returns
    -------
    AssistantAnswer
        Matching families and source labels.
    """
    payload = catalog_payload(config_dir)
    rows = payload.get("families")
    families = rows if isinstance(rows, list) else []
    needle = query.strip().lower()
    matches = [
        row
        for row in families
        if isinstance(row, dict)
        and any(
            needle in str(row.get(key, "")).lower()
            for key in ("family", "equation_family", "status")
        )
    ]
    sources = tuple(
        str(row["source_file"])
        for row in matches
        if isinstance(row, dict) and row.get("source_file")
    ) or ("VDYP_CFG",)
    answer = AssistantAnswer(
        f"{len(matches)} families match {query!r}.",
        sources,
        {"families": matches},
    )
    validate_answer(answer)
    return answer


def curve_query(service: CurveService, query: CurveQuery) -> AssistantAnswer:
    """Run a curve query and return a source-backed summary.

    Parameters
    ----------
    service : CurveService
        Loaded curve service.
    query : CurveQuery
        Query inputs.

    Returns
    -------
    AssistantAnswer
        Status, point count, and provenance.
    """
    result = service.query(query)
    answer = AssistantAnswer(
        f"{result.status}: {len(result.points)} points. {result.reason}".strip(),
        (result.provenance.source_file, result.provenance.runtime),
        result.to_dict(),
    )
    validate_answer(answer)
    return answer


def provenance_lookup(service: CurveService) -> AssistantAnswer:
    """Return the provenance of the loaded curve table.

    Parameters
    ----------
    service : CurveService
        Loaded curve service.

    Returns
    -------
    AssistantAnswer
        Source file, runtime, console version, and schema labels.
    """
    answer = AssistantAnswer(
        f"Source {service.table.source_file}; runtime {service.runtime}.",
        (service.table.source_file, service.runtime),
        {
            "source_file": service.table.source_file,
            "runtime": service.runtime,
            "console_version": service.console_version,
            "control_sequence": service.control_sequence,
            "schema": str(DEFAULT_SCHEMA),
            "aliases": str(DEFAULT_ALIASES),
        },
    )
    validate_answer(answer)
    return answer


def validation_status(matrix: Path, family: str) -> AssistantAnswer:
    """Return the validation status of one family from the matrix.

    Parameters
    ----------
    matrix : Path
        Equation matrix JSON.
    family : str
        Family name.

    Returns
    -------
    AssistantAnswer
        Status and evidence, or ``not_implemented`` when the family is absent.
    """
    payload = json.loads(matrix.read_text(encoding="utf-8"))
    rows = payload.get("families") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise AssistantAnswerError("matrix has no families")
    match = next(
        (row for row in rows if isinstance(row, dict) and row.get("family") == family),
        None,
    )
    if match is None:
        answer = AssistantAnswer(
            f"{family}: not_implemented (not in the matrix).",
            (str(matrix),),
            {"family": family, "status": "not_implemented"},
        )
    else:
        answer = AssistantAnswer(
            f"{family}: {match.get('status')}.",
            (str(match.get("evidence", matrix)),),
            match,
        )
    validate_answer(answer)
    return answer
