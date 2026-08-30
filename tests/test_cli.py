"""consolidate command behavior."""

import json
import shutil

import pytest

from memory_drawer.__main__ import main


def make_config(tmp_path):
    master = tmp_path / "master"
    master.mkdir()
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello", encoding="utf-8")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps({"master": str(master), "sources": [{"id": "s1", "path": str(src)}]}),
        encoding="utf-8",
    )
    return cfg, master


def test_dry_run_prints_plan(tmp_path, capsys):
    cfg, _ = make_config(tmp_path)
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Config OK" in out
    assert "1 files, 5 B" in out
    assert "Total: 1 files" in out
    assert "Free space" in out


def test_dry_run_touches_nothing(tmp_path):
    cfg, master = make_config(tmp_path)
    src = cfg.parent / "src"
    before = {(p.name, p.read_bytes()) for p in src.iterdir()}
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    assert list(master.iterdir()) == []
    assert {(p.name, p.read_bytes()) for p in src.iterdir()} == before


def test_missing_config_exits_1(tmp_path, capsys):
    assert main(["consolidate", "--config", str(tmp_path / "nope.json"), "--dry-run"]) == 1
    assert "config error" in capsys.readouterr().out


def test_invalid_config_exits_1(tmp_path, capsys):
    cfg, master = make_config(tmp_path)
    cfg.write_text(json.dumps({"master": str(master), "sources": [], "extra": 1}), encoding="utf-8")
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 1
    assert "config error" in capsys.readouterr().out


def test_without_dry_run_needs_config(capsys):
    assert main(["consolidate"]) == 1
    assert "config error" in capsys.readouterr().out


def test_escape_control():
    from memory_drawer.__main__ import _escape_control

    assert _escape_control("a\nb\tc") == "a\\x0ab\\x09c"
    assert _escape_control("normal.txt") == "normal.txt"
    assert _escape_control("del\x7f") == "del\\x7f"


def test_help_lists_consolidate(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "consolidate" in capsys.readouterr().out


def test_consolidate_help_shows_options(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["consolidate", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--config" in out
    assert "--dry-run" in out


def test_usage_error_exits_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["consolidate", "--bogus"])
    assert exc_info.value.code == 2


def test_free_space_warning(tmp_path, capsys, monkeypatch):
    cfg, _ = make_config(tmp_path)

    class FakeUsage:
        free = 1

    monkeypatch.setattr(shutil, "disk_usage", lambda path: FakeUsage())
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "less than the total source size" in out


def test_walk_error_warns(tmp_path, capsys, monkeypatch):
    from memory_drawer import consolidate as cons

    cfg, _ = make_config(tmp_path)

    def broken_walk(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(cons.os, "walk", broken_walk)
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    assert "could not be read" in capsys.readouterr().out


def test_free_space_unknown(tmp_path, capsys, monkeypatch):
    from memory_drawer import __main__ as cli

    cfg, _ = make_config(tmp_path)

    def broken_usage(path):
        raise OSError("boom")

    monkeypatch.setattr(cli.shutil, "disk_usage", broken_usage)
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    assert "unknown" in capsys.readouterr().out


def test_keyboard_interrupt_exits_130(tmp_path, capsys, monkeypatch):
    from memory_drawer import consolidate as cons

    cfg, _ = make_config(tmp_path)

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cons, "copy_stream", interrupt)
    assert main(["consolidate", "--config", str(cfg)]) == 130
    assert "interrupted" in capsys.readouterr().out


def test_unicode_source_path_prints(tmp_path, capsys):
    master = tmp_path / "master"
    master.mkdir()
    src = tmp_path / "bkp ção"
    src.mkdir()
    (src / "foto é.txt").write_text("x", encoding="utf-8")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps({"master": str(master), "sources": [{"id": "b1", "path": str(src)}]}),
        encoding="utf-8",
    )
    assert main(["consolidate", "--config", str(cfg), "--dry-run"]) == 0
    assert "bkp ção" in capsys.readouterr().out
