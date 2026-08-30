"""consolidate command behavior (spec 0002 §3)."""

import json

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


def test_without_dry_run_exits_1(capsys):
    assert main(["consolidate"]) == 1
    assert "not implemented yet" in capsys.readouterr().out


def test_help_lists_consolidate(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "consolidate" in capsys.readouterr().out
