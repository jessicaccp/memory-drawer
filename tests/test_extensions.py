"""Validate extensions.json against its schema."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
KNOWN_CATEGORIES = {"photos", "videos", "music", "documents"}


@pytest.fixture(scope="module")
def ext_map() -> dict[str, list[str]]:
    return json.loads((ROOT / "extensions.json").read_text(encoding="utf-8"))


def test_categories_are_exactly_the_known_four(ext_map: dict[str, list[str]]) -> None:
    assert set(ext_map) == KNOWN_CATEGORIES


def test_extensions_are_lowercase_dotless_and_nonempty(ext_map: dict[str, list[str]]) -> None:
    for exts in ext_map.values():
        assert exts, "category must not be empty"
        for ext in exts:
            assert ext == ext.lower(), f"extension not lower case: {ext}"
            assert "." not in ext, f"extension has a dot: {ext}"


def test_no_extension_twice_within_a_category(ext_map: dict[str, list[str]]) -> None:
    for category, exts in ext_map.items():
        assert len(exts) == len(set(exts)), f"duplicate extension in {category}"


def test_no_extension_in_two_categories(ext_map: dict[str, list[str]]) -> None:
    seen: dict[str, str] = {}
    for category, exts in ext_map.items():
        for ext in exts:
            assert ext not in seen, f"{ext} listed in both {seen[ext]} and {category}"
            seen[ext] = category


def test_mod_is_music_only(ext_map: dict[str, list[str]]) -> None:
    assert "mod" in ext_map["music"]
    assert "mod" not in ext_map["videos"]
