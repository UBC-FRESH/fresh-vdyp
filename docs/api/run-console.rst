``run_console``
================

The console runner. It copies an input tree into an isolated working directory,
runs ``VDYP7Console`` through the runtime adapter, and records stdout, stderr,
the output file, the error file, and a stable failure code. A failed run is
never replaced with generated values.

.. automodule:: run_console
   :members:
   :show-inheritance:
