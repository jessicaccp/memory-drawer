"""Shared file helpers (spec 0004 §8)."""

import hashlib

import pytest

from memory_drawer.fsutil import copy_stream, escape_control, sha256_file, walk_sorted


def test_sha256_file(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"hello")
    assert sha256_file(path) == hashlib.sha256(b"hello").hexdigest()


def test_sha256_empty_file(tmp_path):
    path = tmp_path / "e"
    path.write_bytes(b"")
    assert sha256_file(path) == hashlib.sha256(b"").hexdigest()


def test_copy_stream_copies_and_hashes(tmp_path):
    src = tmp_path / "s"
    data = b"data" * 1000
    src.write_bytes(data)
    dst = tmp_path / "d"
    assert copy_stream(src, dst) == hashlib.sha256(data).hexdigest()
    assert dst.read_bytes() == data


def test_copy_stream_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        copy_stream(tmp_path / "nope", tmp_path / "d")


def test_walk_sorted(tmp_path):
    root = tmp_path / "r"
    (root / "b").mkdir(parents=True)
    (root / "a").mkdir()
    (root / "b" / "2.txt").write_text("")
    (root / "b" / "1.txt").write_text("")
    (root / "a" / "x.txt").write_text("")
    seen = [(base.name, names) for base, names in walk_sorted(root, lambda exc: None)]
    assert seen == [("r", []), ("a", ["x.txt"]), ("b", ["1.txt", "2.txt"])]


def test_escape_control():
    assert escape_control("a\nb\tc") == "a\\x0ab\\x09c"
    assert escape_control("normal.txt") == "normal.txt"
    assert escape_control("del\x7f") == "del\\x7f"
