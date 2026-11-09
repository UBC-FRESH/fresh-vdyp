"""Tests for the VDYP7 bundle inventory tool."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from inventory_vdyp import (
    BundleManifest,
    FileRecord,
    build_manifest,
    classify,
    iter_files,
    main,
    root_from_environment,
    sha256_file,
    slugify,
    write_manifest,
)

CONTENT: dict[str, bytes] = {
    "VDYP_CFG/VDYP.CTR": b"001 test\n",
    "VDYP_CFG/VDYP7LoggingConfig.txt": b"log\n",
    "VDYP_CFG/coe/VTOTREG4.COE": b"1 2 3\n",
    "VDYP_CFG/coe/regvu.coe": b"4 5\n",
    "VDYP_CFG/coe/SIEQN.PRM": b"6\n",
    "VDYP_CFG/coe/BEC0.DAT": b"7\n",
    "SampleData/plot.csv": b"a,b\n",
    "VDYP7Console.exe": b"MZ",
    "README.md": b"# readme\n",
    "bundle.zip": b"PK",
    "db.mdb": b"MDB",
    "Programming/demo.for": b"program\n",
    "Vdyp.ini": b"[x]\n",
    "notes.unknown": b"?\n",
    "A.txt": b"upper\n",
    "a.txt": b"lower\n",
}


def make_bundle(root: Path) -> dict[str, bytes]:
    for name, data in CONTENT.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return CONTENT


def test_sha256_file_hashes_the_contents(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"abc")
    assert sha256_file(path) == hashlib.sha256(b"abc").hexdigest()


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("VDYP_CFG/coe/X.COE", "coefficient"),
        ("VDYP_CFG/coe/X.prm", "parameter"),
        ("VDYP_CFG/coe/X.DAT", "data"),
        ("VDYP_CFG/VDYP.CTR", "control"),
        ("VDYP_CFG/VDYP.tcl", "control"),
        ("Vdyp.ini", "control"),
        ("VDYP_CFG/VDYP7LoggingConfig.txt", "control"),
        ("VDYP7Console.exe", "binary"),
        ("VDYP7CORE.DLL", "binary"),
        ("README.md", "document"),
        ("Programing/table.csv", "data"),
        ("bundle.zip", "archive"),
        ("bundle.mdb", "database"),
        ("Programming/demo.for", "source"),
        ("notes.unknown", "other"),
        ("SampleData/plot.DAT", "sample"),
    ],
)
def test_classify_uses_the_extension_and_sample_directory(name: str, kind: str) -> None:
    assert classify(Path(name)) == kind


def test_slugify_normalizes_a_relative_path() -> None:
    assert slugify("VDYP_CFG/coe/X.COE") == "vdyp-cfg-coe-x-coe"


def test_slugify_falls_back_when_nothing_remains() -> None:
    assert slugify("---") == "file"


def test_build_manifest_covers_every_file(tmp_path: Path) -> None:
    content = make_bundle(tmp_path)
    manifest = build_manifest(tmp_path)
    assert manifest.file_count == len(content)
    assert {record.relative_path for record in manifest.files} == set(content)
    assert manifest.total_bytes == sum(len(data) for data in content.values())
    assert manifest.schema_version == 1
    assert manifest.source_model == "VDYP7"
    assert manifest.source_version == "7"
    assert "Province of British Columbia" in manifest.citation


def test_manifest_paths_are_relative_and_hashes_are_full_length(tmp_path: Path) -> None:
    make_bundle(tmp_path)
    manifest = build_manifest(tmp_path)
    for record in manifest.files:
        assert not record.relative_path.startswith("/")
        assert ":" not in record.relative_path
        assert len(record.sha256) == 64


def test_manifest_kinds_match_the_helper(tmp_path: Path) -> None:
    make_bundle(tmp_path)
    manifest = build_manifest(tmp_path)
    kinds = {record.relative_path: record.kind for record in manifest.files}
    assert kinds["VDYP_CFG/coe/VTOTREG4.COE"] == "coefficient"
    assert kinds["SampleData/plot.csv"] == "sample"
    assert kinds["VDYP7Console.exe"] == "binary"


def test_ids_are_unique_including_case_collisions(tmp_path: Path) -> None:
    make_bundle(tmp_path)
    manifest = build_manifest(tmp_path)
    identifiers = [record.id for record in manifest.files]
    assert len(identifiers) == len(set(identifiers))
    collision_ids = {
        record.id for record in manifest.files if record.relative_path.lower() == "a.txt"
    }
    assert len(collision_ids) == 2
    assert any(identifier.endswith("-2") for identifier in collision_ids)


def test_manifest_serialization_is_deterministic(tmp_path: Path) -> None:
    make_bundle(tmp_path)
    first = json.dumps(build_manifest(tmp_path).to_dict(), indent=2)
    second = json.dumps(build_manifest(tmp_path).to_dict(), indent=2)
    assert first == second


def test_iter_files_skips_symlinks(tmp_path: Path) -> None:
    make_bundle(tmp_path)
    target = tmp_path / "README.md"
    link = tmp_path / "linked.md"
    link.symlink_to(target)
    names = {path.name for path in iter_files(tmp_path)}
    assert "linked.md" not in names
    assert "README.md" in names


def test_build_manifest_rejects_a_file_root(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        build_manifest(path)


def test_write_manifest_creates_parent_directories(tmp_path: Path) -> None:
    manifest = BundleManifest(
        schema_version=1,
        source_model="VDYP7",
        source_version="7",
        citation="cite",
        file_count=1,
        total_bytes=1,
        files=(
            FileRecord(
                id="vdyp-file",
                kind="other",
                relative_path="file",
                size_bytes=1,
                sha256="0" * 64,
            ),
        ),
    )
    output = tmp_path / "nested" / "manifest.json"
    write_manifest(manifest, output)
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_main_writes_a_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    make_bundle(tmp_path)
    output = tmp_path / "out" / "manifest.json"
    assert main(["--root", str(tmp_path), "--output", str(output)]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["file_count"] == len(CONTENT)
    assert "Wrote" in capsys.readouterr().out


def test_main_uses_vdyp_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_bundle(tmp_path)
    monkeypatch.setenv("VDYP_INSTALL", str(tmp_path))
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    output = tmp_path / "manifest.json"
    assert main(["--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["file_count"] == len(CONTENT)
    assert root_from_environment() == tmp_path
    capsys.readouterr()


def test_main_uses_the_config_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_bundle(tmp_path)
    monkeypatch.delenv("VDYP_INSTALL", raising=False)
    monkeypatch.setenv("VDYP_CFG_DIR", str(tmp_path / "VDYP_CFG"))
    output = tmp_path / "manifest.json"
    assert main(["--output", str(output)]) == 0
    assert root_from_environment() == tmp_path
    capsys.readouterr()


def test_main_without_a_root_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.delenv("VDYP_INSTALL", raising=False)
    monkeypatch.delenv("VDYP_CFG_DIR", raising=False)
    output = tmp_path / "manifest.json"
    assert main(["--output", str(output)]) == 2
    assert "VDYP_INSTALL" in capsys.readouterr().err


def test_main_with_a_missing_root_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "manifest.json"
    assert main(["--root", str(tmp_path / "missing"), "--output", str(output)]) == 2
    assert "not a directory" in capsys.readouterr().err
