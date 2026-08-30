"""Consolidation behavior."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from memory_drawer.config import Config, Source
from memory_drawer.consolidate import ConsolidateAbort, consolidate
from memory_drawer.layout import CONSOLIDATED, MANIFEST
from memory_drawer.manifest import load


def make_config(tmp_path, master=None, sources=None):
    master = master or (tmp_path / "master")
    master.mkdir(exist_ok=True)
    source_list = []
    for sid, path in sources or [("s1", tmp_path / "src1")]:
        path.mkdir(exist_ok=True)
        source_list.append(Source(id=sid, path=path.resolve()))
    return Config(master=master.resolve(), sources=source_list)


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(config, tmp_path):
    manifest_path = config.master / MANIFEST
    result = consolidate(config, manifest_path)
    records = load(manifest_path).records
    return result, records


def test_basic_copy_preserves_mtime(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    file = src / "foto.JPG"
    file.write_bytes(b"abc")
    os.utime(file, (1700000000, 1700000000))
    result, records = run(config, tmp_path)
    assert result.errors == []
    assert result.copied == 1
    dest = config.master / CONSOLIDATED / "s1" / "foto.JPG"
    assert dest.exists()
    assert dest.stat().st_mtime == 1700000000
    assert len(records) == 1
    rec = records[0]
    assert rec.source_path == str(file.resolve())
    assert rec.sha256 == sha_of(file)
    assert rec.size == 3
    assert rec.kind == "file"
    assert rec.status == "ingested"


def test_rerun_copies_nothing(tmp_path):
    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")
    result1, records1 = run(config, tmp_path)
    result2, records2 = run(config, tmp_path)
    assert result1.copied == 1
    assert result2.copied == 0
    assert result2.already_present == 1
    assert len(records2) == len(records1) == 1


def test_self_heal_recopies_missing_dest(tmp_path):
    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")
    run(config, tmp_path)
    dest = config.master / CONSOLIDATED / "s1" / "a.txt"
    dest.unlink()
    result, records = run(config, tmp_path)
    assert result.re_copied == 1
    assert dest.exists()
    assert len(records) == 1


def test_quarantined_never_recopied(tmp_path):
    config = make_config(tmp_path)
    file = config.sources[0].path / "a.txt"
    file.write_text("hello")
    run(config, tmp_path)
    dest = config.master / CONSOLIDATED / "s1" / "a.txt"
    dest.unlink()
    manifest_path = config.master / MANIFEST
    records = load(manifest_path).records
    records[0].status = "quarantined"
    from memory_drawer.manifest import rewrite

    rewrite(manifest_path, records)
    result, records = run(config, tmp_path)
    assert result.copied == 0
    assert result.skipped == 1
    assert not dest.exists()


def test_symlink_skipped(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("no symlink support")
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "real.txt").write_text("x")
    os.symlink(src / "real.txt", src / "link.txt")
    result, records = run(config, tmp_path)
    assert result.skipped == 1
    assert len(records) == 1
    assert (config.master / CONSOLIDATED / "s1" / "link.txt").exists() is False


def test_non_regular_file_skipped(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("no fifo support")
    config = make_config(tmp_path)
    os.mkfifo(config.sources[0].path / "pipe")
    result, records = run(config, tmp_path)
    assert result.skipped == 1
    assert records == []


def test_sidecar_pairing(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "IMG_1234.JPG").write_bytes(b"photo")
    (src / "IMG_1234.JPG.json").write_text('{"photoTakenTime": 1}')
    result, records = run(config, tmp_path)
    assert result.errors == []
    assert len(records) == 2
    side = next(r for r in records if r.kind == "sidecar")
    assert side.sidecar_of == "IMG_1234.JPG"
    assert (config.master / CONSOLIDATED / "s1" / "IMG_1234.JPG.json").exists()


def test_orphan_json_is_regular_file(tmp_path):
    config = make_config(tmp_path)
    (config.sources[0].path / "notes.json").write_text('{"a": 1}')
    _, records = run(config, tmp_path)
    assert len(records) == 1
    assert records[0].kind == "file"
    assert records[0].sidecar_of is None


def test_case_insensitive_pairing(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "IMG.JPG").write_bytes(b"photo")
    (src / "img.jpg.json").write_text("{}")
    result, records = run(config, tmp_path)
    assert len(records) == 2
    side = next(r for r in records if r.kind == "sidecar")
    assert side.sidecar_of == "IMG.JPG"
    assert len(result.case_diffs) == 1


def test_invalid_json_sidecar_flagged(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "IMG.JPG").write_bytes(b"photo")
    (src / "IMG.JPG.json").write_text("{not json")
    result, records = run(config, tmp_path)
    assert result.errors == []
    side = next(r for r in records if r.kind == "sidecar")
    assert side.errors == ["sidecar is not valid JSON"]
    assert (config.master / CONSOLIDATED / "s1" / "IMG.JPG.json").exists()


def test_failed_copy_no_record_no_partial(tmp_path, monkeypatch):
    from memory_drawer import consolidate as cons

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")

    def broken(src, dst):
        raise OSError("boom")

    monkeypatch.setattr(cons, "copy_stream", broken)
    result, records = run(config, tmp_path)
    assert records == []
    assert len(result.errors) == 1
    assert not (config.master / CONSOLIDATED / "s1" / "a.txt").exists()


def test_retry_once_then_success(tmp_path, monkeypatch):
    from memory_drawer import consolidate as cons

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")
    real = cons.copy_stream
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("transient")
        return real(src, dst)

    monkeypatch.setattr(cons, "copy_stream", flaky)
    result, _ = run(config, tmp_path)
    assert result.errors == []
    assert result.copied == 1
    assert (config.master / CONSOLIDATED / "s1" / "a.txt").exists()


def test_source_vanished_mid_run(tmp_path, monkeypatch):
    from memory_drawer import consolidate as cons

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")

    def vanished(src, dst):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(cons, "copy_stream", vanished)
    result, records = run(config, tmp_path)
    assert records == []
    assert len(result.errors) == 1


def test_empty_source(tmp_path):
    config = make_config(tmp_path)
    result, records = run(config, tmp_path)
    assert result.copied == 0
    assert result.errors == []
    assert records == []


def test_zero_byte_and_unicode(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "vazio.txt").write_bytes(b"")
    (src / "foto ção é 😀.JPG").write_bytes(b"x")
    result, _ = run(config, tmp_path)
    assert result.errors == []
    assert result.copied == 2
    assert (config.master / CONSOLIDATED / "s1" / "foto ção é 😀.JPG").exists()
    assert (config.master / CONSOLIDATED / "s1" / "vazio.txt").stat().st_size == 0


def test_changed_file_gets_suffixed_dest(tmp_path):
    config = make_config(tmp_path)
    file = config.sources[0].path / "a.txt"
    file.write_text("one")
    run(config, tmp_path)
    file.write_text("two")
    result, records = run(config, tmp_path)
    assert result.copied == 1
    assert len(records) == 2
    first = records[0]
    second = records[1]
    assert first.dest_path.endswith("a.txt")
    assert second.dest_path.endswith("a_2.txt")
    assert Path(first.dest_path).exists()
    assert Path(second.dest_path).exists()
    assert Path(first.dest_path).read_text() == "one"
    assert Path(second.dest_path).read_text() == "two"


def test_dest_without_record_is_error(tmp_path):
    config = make_config(tmp_path)
    file = config.sources[0].path / "a.txt"
    file.write_text("hello")
    dest = config.master / CONSOLIDATED / "s1" / "a.txt"
    dest.parent.mkdir(parents=True)
    dest.write_text("stray")
    result, records = run(config, tmp_path)
    assert records == []
    assert any("without a record" in e for e in result.errors)
    assert dest.read_text() == "stray"


def test_interrupt_flushes_pending_records(tmp_path, monkeypatch):
    from memory_drawer import consolidate as cons

    config = make_config(tmp_path)
    src = config.sources[0].path
    for i in range(5):
        (src / f"f{i}.txt").write_text("x")
    real = cons.copy_stream
    calls = {"n": 0}

    def interrupt_after(src_path, dst):
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt
        return real(src_path, dst)

    monkeypatch.setattr(cons, "copy_stream", interrupt_after)
    with pytest.raises(KeyboardInterrupt):
        consolidate(config, config.master / MANIFEST)
    records = load(config.master / MANIFEST).records
    assert len(records) == 2
    dests = list((config.master / CONSOLIDATED / "s1").iterdir())
    assert len(dests) == 2


def test_orphan_json_becomes_sidecar(tmp_path):
    config = make_config(tmp_path)
    src = config.sources[0].path
    (src / "IMG.JPG.json").write_text("{}")
    _, records = run(config, tmp_path)
    assert records[0].kind == "file"
    (src / "IMG.JPG").write_bytes(b"photo")
    result2, records2 = run(config, tmp_path)
    assert result2.copied == 1
    assert result2.kind_fixes == 1
    side = next(r for r in records2 if r.kind == "sidecar")
    assert side.sidecar_of == "IMG.JPG"


def test_abort_when_dest_root_not_creatable(tmp_path, monkeypatch):

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")

    def broken_mkdir(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "mkdir", broken_mkdir)
    with pytest.raises(ConsolidateAbort, match="destination root"):
        consolidate(config, config.master / MANIFEST)


def test_two_sources_both_copied(tmp_path):
    config = make_config(tmp_path, sources=[("s1", tmp_path / "src1"), ("s2", tmp_path / "src2")])
    (config.sources[0].path / "same.txt").write_text("dup")
    (config.sources[1].path / "same.txt").write_text("dup")
    result, records = run(config, tmp_path)
    assert result.copied == 2
    assert len(records) == 2
    assert (config.master / CONSOLIDATED / "s1" / "same.txt").exists()
    assert (config.master / CONSOLIDATED / "s2" / "same.txt").exists()


def test_nested_directories(tmp_path):
    config = make_config(tmp_path)
    nested = config.sources[0].path / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "x.txt").write_text("x")
    result, records = run(config, tmp_path)
    assert result.copied == 1
    assert records[0].rel_path == "sub/deeper/x.txt"
    assert (config.master / CONSOLIDATED / "s1" / "sub" / "deeper" / "x.txt").exists()


def test_cli_clean_run_exits_0(tmp_path, capsys):
    from memory_drawer.__main__ import main

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "master": str(config.master),
                "sources": [{"id": s.id, "path": str(s.path)} for s in config.sources],
            }
        ),
        encoding="utf-8",
    )
    assert main(["consolidate", "--config", str(cfg)]) == 0
    assert "Copied: 1 files" in capsys.readouterr().out


def test_cli_errors_exit_1(tmp_path, capsys, monkeypatch):
    from memory_drawer import consolidate as cons
    from memory_drawer.__main__ import main

    config = make_config(tmp_path)
    (config.sources[0].path / "a.txt").write_text("hello")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "master": str(config.master),
                "sources": [{"id": s.id, "path": str(s.path)} for s in config.sources],
            }
        ),
        encoding="utf-8",
    )

    def broken(src, dst):
        raise OSError("boom")

    monkeypatch.setattr(cons, "copy_stream", broken)
    assert main(["consolidate", "--config", str(cfg)]) == 1
    assert "Errors: 1" in capsys.readouterr().out
