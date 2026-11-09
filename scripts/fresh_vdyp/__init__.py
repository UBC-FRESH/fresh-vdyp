"""The public ``fresh_vdyp`` facade.

The implementation lives in the top-level modules installed from ``scripts/``.
This package re-exports the stable service entry points so FEMIC and other
callers can import one name::

    import fresh_vdyp
    service = fresh_vdyp.load_service(csv_path, metadata_path)
    result = service.query(fresh_vdyp.CurveQuery(age_start=100, age_end=100))
"""

from __future__ import annotations

from bundle_service import (
    BundleDiagnostic,
    catalog_payload,
    extract_bundle,
    validate_bundle,
)
from curve_api import (
    CurvePoint,
    CurveProvenance,
    CurveQuery,
    CurveResult,
    CurveService,
    load_service,
)
from equations import (
    FamilyEstimate,
    WholeStemCoefficients,
    estimate_whole_stem_volume,
    load_volume_groups,
    load_vtotreg4,
)
from yield_parser import YieldTable, parse_yield_csv

__version__ = "0.1.0"

__all__ = [
    "BundleDiagnostic",
    "CurvePoint",
    "CurveProvenance",
    "CurveQuery",
    "CurveResult",
    "CurveService",
    "FamilyEstimate",
    "WholeStemCoefficients",
    "YieldTable",
    "__version__",
    "catalog_payload",
    "estimate_whole_stem_volume",
    "extract_bundle",
    "load_service",
    "load_volume_groups",
    "load_vtotreg4",
    "parse_yield_csv",
    "validate_bundle",
]
