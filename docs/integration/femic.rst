FEMIC integration
=================

`fresh-vdyp` is an optional package dependency for FEMIC. The package exposes a
small facade so FEMIC can import one name and call the same services as the CLI
and API.

Install the wheel or add `fresh-vdyp` to the FEMIC environment, then:

.. code-block:: python

   import os
   from pathlib import Path

   import fresh_vdyp

   service = fresh_vdyp.load_service(
       Path("fixtures/yield-output/golden-full.csv"),
       Path("fixtures/yield-output/metadata.json"),
   )
   result = service.query(fresh_vdyp.CurveQuery(age_start=100, age_end=100))
   assert result.provenance.source_file == "golden-full.csv"

Bundle validation uses the same service layer:

.. code-block:: python

   diagnostics = fresh_vdyp.validate_bundle(Path(os.environ["VDYP_CFG_DIR"]))

Package boundary
----------------

- FEMIC owns its pipeline and its data.
- `fresh-vdyp` owns bundle parsing, the console adapter, typed curves, and the
  equation validation matrix.
- `fresh-vdyp` does not import FEMIC.
- FEMIC may import `fresh_vdyp` or the compatible top-level modules
  (`curve_api`, `bundle_service`, `equations`).

Data prerequisites
------------------

- A local VDYP installation for bundle commands: `VDYP_INSTALL` and
  `VDYP_CFG_DIR`.
- The synthetic golden dataset for curve commands, or a reproduced console
  output with its metadata.

Limits
------

- Only VTOTREG4 is validated.
- The console path was exercised under Wine 11.0.
- The current dataset is synthetic.

FEMIC repository change
-----------------------

The optional dependency and this guide were merged in
`UBC-FRESH/femic#610` on 2026-11-09 (merge commit `c86a464`). FEMIC keeps its
existing VDYP path when the package is absent.
