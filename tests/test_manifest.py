"""Manifest behavior (spec 0003)."""

from dataclasses import asdict

import pytest

from memory_drawer.manifest import (
    HEADER,
    ManifestError,
    Record,
    already_ingested,
    append,
    load,
    lookup,
    rewrite,
)


def record(**overrides) -> Record:
    base = dict(
        file_id="00000001",
        source_id="hdd1",
        source_path="D:\\backups\\hdd1\\IMG_1234.JPG",
        rel_path="IMG_1234.JPG",
        dest_path="E:\\master\\consolidated\\hdd1\\IMG_1234.JPG",
        size=2843562,
        sha256="ab12",
        src_mtime="2011-06-04T14:22:11-03:00",
        kind="file",
        sidecar_of=None,
        group_id=None,
        status="ingested",
        quarantine_path=None,
        merged_from=[],
        errors=[],
    )
    base.update(overrides)
    return Record(**base)


def test_round_trip(tmp_path):
    path = tmp_path / "manifest.jsonl"
    first = record()
    second = record(file_id="00000002", kind="sidecar", sidecar_of="IMG_1234.JPG")
    append(path, [first, second])
    loaded = load(path)
    assert [asdict(r) for r in loaded.records] == [asdict(first), asdict(second)]
    assert not loaded.truncated


def test_append_no_duplicate_header(tmp_path):
    path = tmp_path / "manifest.jsonl"
    append(path, [record(file_id="00000001")])
    append(path, [record(file_id="00000002")])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER
    assert lines.count(HEADER) == 1
    assert len(load(path).records) == 2


def test_missing_file_is_empty(tmp_path):
    manifest = load(tmp_path / "nope.jsonl")
    assert manifest.records == []
    assert not manifest.truncated


def test_empty_file_is_empty(tmp_path):
    path = tmp_path / "manifest.jsonl"
    path.write_text("", encoding="utf-8")
    manifest = load(path)
    assert manifest.records == []
    assert not manifest.truncated


def test_already_ingested_match(tmp_path):
    path = tmp_path / "manifest.jsonl"
    rec = record()
    append(path, [rec])
    loaded = load(path)
    assert already_ingested(loaded.records, rec.source_path, rec.size, rec.src_mtime, rec.sha256)


@pytest.mark.parametrize("field", ["size", "src_mtime", "sha256"])
def test_already_ingested_field_differs(tmp_path, field):
    path = tmp_path / "manifest.jsonl"
    rec = record()
    append(path, [rec])
    loaded = load(path)
    kwargs = {
        "source_path": rec.source_path,
        "size": rec.size,
        "src_mtime": rec.src_mtime,
        "sha256": rec.sha256,
    }
    kwargs[field] = "x" if field in {"src_mtime", "sha256"} else 0
    assert not already_ingested(loaded.records, **kwargs)


def test_already_ingested_path_differs(tmp_path):
    path = tmp_path / "manifest.jsonl"
    rec = record()
    append(path, [rec])
    loaded = load(path)
    assert not already_ingested(
        loaded.records, "D:\\elsewhere\\x.JPG", rec.size, rec.src_mtime, rec.sha256
    )


def test_lookup_found(tmp_path):
    path = tmp_path / "manifest.jsonl"
    rec = record()
    append(path, [rec])
    loaded = load(path)
    assert lookup(loaded.records, rec.source_path) == rec


def test_lookup_missing(tmp_path):
    path = tmp_path / "manifest.jsonl"
    append(path, [record()])
    loaded = load(path)
    assert lookup(loaded.records, "D:\\nope\\x.JPG") is None


def test_truncated_last_line(tmp_path):
    path = tmp_path / "manifest.jsonl"
    append(path, [record()])
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"file_id": "00000002",')  # partial write, no newline
    manifest = load(path)
    assert manifest.truncated
    assert len(manifest.records) == 1


def test_corrupt_middle_line(tmp_path):
    path = tmp_path / "manifest.jsonl"
    append(path, [record()])
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not json}\n")
    append(path, [record(file_id="00000002")])
    with pytest.raises(ManifestError, match="corrupt line 3"):
        load(path)


def test_missing_header(tmp_path):
    path = tmp_path / "manifest.jsonl"
    path.write_text('{"a": 1}\n', encoding="utf-8")
    with pytest.raises(ManifestError, match="missing header"):
        load(path)


def test_binary_garbage(tmp_path):
    path = tmp_path / "manifest.jsonl"
    path.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(ManifestError, match="UTF-8"):
        load(path)


def test_rewrite_preserves_content(tmp_path):
    path = tmp_path / "manifest.jsonl"
    first = record()
    second = record(file_id="00000002", status="quarantined")
    append(path, [first])
    rewrite(path, [first, second])
    loaded = load(path)
    assert [asdict(r) for r in loaded.records] == [asdict(first), asdict(second)]
    assert loaded.records[1].status == "quarantined"


def test_rewrite_failure_keeps_original(tmp_path, monkeypatch):
    path = tmp_path / "manifest.jsonl"
    rec = record()
    append(path, [rec])
    monkeypatch.setattr(
        "memory_drawer.manifest.os.replace", lambda a, b: (_ for _ in ()).throw(OSError("boom"))
    )
    with pytest.raises(OSError):
        rewrite(path, [record(status="quarantined")])
    assert load(path).records == [rec]


def test_unicode_round_trip(tmp_path):
    path = tmp_path / "manifest.jsonl"
    rec = record(
        source_path="D:\\bkp\\foto ção é 😀.JPG",
        rel_path="foto ção é 😀.JPG",
    )
    append(path, [rec])
    loaded = load(path)
    assert loaded.records[0].source_path == rec.source_path
