"""Config loading and validation rules (spec 0002 §4)."""

import json

import pytest

from memory_drawer.config import ConfigError, load_config


@pytest.fixture
def tree(tmp_path):
    master = tmp_path / "master"
    master.mkdir()
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello", encoding="utf-8")
    return tmp_path, master, src


def write_config(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def valid(master, src):
    return {"master": str(master), "sources": [{"id": "s1", "path": str(src)}]}


def test_valid_config(tree):
    tmp_path, master, src = tree
    config = load_config(write_config(tmp_path, valid(master, src)))
    assert config.master == master.resolve()
    assert config.sources[0].id == "s1"
    assert config.sources[0].path == src.resolve()


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.json")


def test_invalid_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(path)


def test_config_path_is_directory(tmp_path, tree):
    tmp_path, _, _ = tree
    with pytest.raises(ConfigError, match="is a directory"):
        load_config(tmp_path)


def test_binary_config_file(tmp_path, tree):
    tmp_path, _, _ = tree
    path = tmp_path / "config.json"
    path.write_bytes(b"\x00\xff\x00")
    with pytest.raises(ConfigError, match="could not be read"):
        load_config(path)


def test_root_not_object(tmp_path, tree):
    tmp_path, _, _ = tree
    with pytest.raises(ConfigError, match="JSON object"):
        load_config(write_config(tmp_path, ["master"]))


def test_unknown_key(tmp_path, tree):
    tmp_path, master, src = tree
    data = valid(master, src)
    data["extra"] = 1
    with pytest.raises(ConfigError, match="unknown keys: extra"):
        load_config(write_config(tmp_path, data))


def test_master_not_string(tmp_path):
    with pytest.raises(ConfigError, match="master must be"):
        load_config(write_config(tmp_path, {"master": 5, "sources": []}))


def test_master_not_existing_dir(tmp_path, tree):
    tmp_path, _, src = tree
    data = valid(tmp_path / "missing", src)
    with pytest.raises(ConfigError, match="not an existing directory"):
        load_config(write_config(tmp_path, data))


def test_empty_sources(tmp_path, tree):
    tmp_path, master, _ = tree
    with pytest.raises(ConfigError, match="non-empty list"):
        load_config(write_config(tmp_path, {"master": str(master), "sources": []}))


def test_source_not_object(tmp_path, tree):
    tmp_path, master, _ = tree
    data = {"master": str(master), "sources": ["s1"]}
    with pytest.raises(ConfigError, match="id and path"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize("bad_id", [".", ".."])
def test_source_id_dot(tmp_path, tree, bad_id):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": bad_id, "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize(
    "bad_id", ["CON", "con", "NUL", "AUX", "PRN", "COM1", "COM9", "LPT1", "LPT9"]
)
def test_source_id_windows_reserved(tmp_path, tree, bad_id):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": bad_id, "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize("bad_id", ["a:b", "a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"])
def test_source_id_invalid_chars(tmp_path, tree, bad_id):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": bad_id, "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


def test_source_id_control_char(tmp_path, tree):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": "a\tb", "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


def test_source_id_trailing_dot(tmp_path, tree):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": "id.", "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


def test_source_id_stripped(tmp_path, tree):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": "  hdd1  ", "path": str(src)}]}
    config = load_config(write_config(tmp_path, data))
    assert config.sources[0].id == "hdd1"


def test_expandvars(tmp_path, monkeypatch):
    master = tmp_path / "master"
    master.mkdir()
    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.setenv("MD_MASTER", str(master))
    monkeypatch.setenv("MD_SRC", str(src))
    data = {"master": "$MD_MASTER", "sources": [{"id": "s1", "path": "$MD_SRC"}]}
    config = load_config(write_config(tmp_path, data))
    assert config.master == master.resolve()
    assert config.sources[0].path == src.resolve()


def test_source_missing_id(tmp_path, tree):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"path": str(src)}]}
    with pytest.raises(ConfigError, match="non-empty id"):
        load_config(write_config(tmp_path, data))


def test_source_missing_path(tmp_path, tree):
    tmp_path, master, _ = tree
    data = {"master": str(master), "sources": [{"id": "s1"}]}
    with pytest.raises(ConfigError, match="non-empty path"):
        load_config(write_config(tmp_path, data))


def test_source_id_with_separator(tmp_path, tree):
    tmp_path, master, src = tree
    data = {"master": str(master), "sources": [{"id": "a/b", "path": str(src)}]}
    with pytest.raises(ConfigError, match="not a valid folder name"):
        load_config(write_config(tmp_path, data))


def test_duplicate_source_ids(tmp_path, tree):
    tmp_path, master, src = tree
    data = {
        "master": str(master),
        "sources": [
            {"id": "s1", "path": str(src)},
            {"id": "s1", "path": str(src)},
        ],
    }
    with pytest.raises(ConfigError, match="unique: s1"):
        load_config(write_config(tmp_path, data))


def test_source_not_existing_dir(tmp_path, tree):
    tmp_path, master, _ = tree
    data = {"master": str(master), "sources": [{"id": "s1", "path": str(tmp_path / "nope")}]}
    with pytest.raises(ConfigError, match="not an existing directory"):
        load_config(write_config(tmp_path, data))


def test_source_inside_master(tmp_path, tree):
    tmp_path, master, _ = tree
    inner = master / "inner"
    inner.mkdir()
    data = {"master": str(master), "sources": [{"id": "s1", "path": str(inner)}]}
    with pytest.raises(ConfigError, match="inside master"):
        load_config(write_config(tmp_path, data))


def test_master_equals_source(tmp_path, tree):
    tmp_path, master, _ = tree
    data = {"master": str(master), "sources": [{"id": "s1", "path": str(master)}]}
    with pytest.raises(ConfigError, match="inside master"):
        load_config(write_config(tmp_path, data))


def test_master_inside_source(tmp_path, tree):
    tmp_path, _, src = tree
    inner = src / "master"
    inner.mkdir()
    data = {"master": str(inner), "sources": [{"id": "s1", "path": str(src)}]}
    with pytest.raises(ConfigError, match="master is inside source"):
        load_config(write_config(tmp_path, data))


def test_overlapping_sources_allowed(tmp_path, tree):
    tmp_path, master, src = tree
    inner = src / "inner"
    inner.mkdir()
    data = {
        "master": str(master),
        "sources": [
            {"id": "s1", "path": str(src)},
            {"id": "s2", "path": str(inner)},
        ],
    }
    config = load_config(write_config(tmp_path, data))
    assert len(config.sources) == 2


def test_relative_paths_resolved(tmp_path, monkeypatch):
    master = tmp_path / "master"
    master.mkdir()
    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.chdir(tmp_path)
    data = {"master": "master", "sources": [{"id": "s1", "path": "src"}]}
    config = load_config(write_config(tmp_path, data))
    assert config.master == master.resolve()
    assert config.sources[0].path == src.resolve()


def test_utf8_bom_config(tmp_path, tree):
    tmp_path, master, src = tree
    path = tmp_path / "config.json"
    body = json.dumps(valid(master, src)).encode("utf-8")
    path.write_bytes(b"\xef\xbb\xbf" + body)
    config = load_config(path)
    assert config.master == master.resolve()


def test_unicode_paths(tmp_path):
    master = tmp_path / "área mestre"
    master.mkdir()
    src = tmp_path / "bkp ãçê"
    src.mkdir()
    (src / "foto é 01.txt").write_text("x", encoding="utf-8")
    data = {"master": str(master), "sources": [{"id": "b1", "path": str(src)}]}
    config = load_config(write_config(tmp_path, data))
    assert config.master == master.resolve()
    assert config.sources[0].path == src.resolve()
