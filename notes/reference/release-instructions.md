# Release instructions

Status: release candidate. Nothing below the approval line has been run.

## Build and verify

```bash
rm -rf dist build
python -m build
python scripts/dashboard.py
python scripts/provenance.py --manifest fixtures/yield-output/dataset-manifest.json
```

Record the wheel and sdist hashes in `notes/reference/release-manifest.json`.
Install the wheel into a clean target and import the facade:

```bash
python -m pip install --no-deps --target /tmp/fresh-vdyp-target dist/*.whl
PYTHONPATH=/tmp/fresh-vdyp-target python -c "import fresh_vdyp; print(fresh_vdyp.__version__)"
```

## Approval-gated publication

These commands create a tag and a GitHub release. Run them only after the
maintainer approves the phase close-out and the release notes.

```bash
git tag -a v0.1.0 -m "fresh-vdyp 0.1.0"
git push origin v0.1.0
gh release create v0.1.0 dist/fresh_vdyp-0.1.0-py3-none-any.whl dist/fresh_vdyp-0.1.0.tar.gz \
  --title "fresh-vdyp 0.1.0" --notes-file RELEASE_NOTES.md
```

PyPI upload is not included. It requires a separate approval, an account, and a
token.

## Data

The release carries a data manifest and a small synthetic dataset, not the BC
bundle. Do not attach `VDYP_CFG` or normalized CSV assets to the release.
