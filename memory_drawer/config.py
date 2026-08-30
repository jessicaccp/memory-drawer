"""Load and validate config.json."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

VALID_KEYS = {"master", "sources"}
INVALID_ID_CHARS = r'\/:*?"<>|'
WINDOWS_RESERVED = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


@dataclass(frozen=True)
class Source:
    id: str
    path: Path


@dataclass(frozen=True)
class Config:
    master: Path
    sources: list[Source]


def _expand(raw: str) -> Path:
    """Expand environment variables and ~, resolve to an absolute real path."""
    return Path(os.path.expandvars(raw)).expanduser().resolve()


def _valid_source_id(source_id: str) -> bool:
    if any(ord(c) < 32 for c in source_id):
        return False
    if any(c in source_id for c in INVALID_ID_CHARS):
        return False
    if source_id in {".", ".."} or source_id.endswith("."):
        return False
    return source_id.upper() not in WINDOWS_RESERVED


def load_config(path: str | Path) -> Config:
    """Load and validate a config file, stopping at the first problem."""
    cfg_path = Path(path).expanduser()
    if not cfg_path.exists():
        raise ConfigError(f"config file not found: {cfg_path}")
    if cfg_path.is_dir():
        raise ConfigError(f"config file is a directory: {cfg_path}")
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config file is not valid JSON: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"config file could not be read: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a JSON object")
    unknown = set(raw) - VALID_KEYS
    if unknown:
        raise ConfigError(f"unknown keys: {', '.join(sorted(unknown))}")

    master_raw = raw.get("master")
    if not isinstance(master_raw, str) or not master_raw.strip():
        raise ConfigError("master must be a non-empty path string")
    master = _expand(master_raw.strip())
    if not master.is_dir():
        raise ConfigError(f"master is not an existing directory: {master}")

    sources_raw = raw.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ConfigError("sources must be a non-empty list")

    sources: list[Source] = []
    seen_ids: set[str] = set()
    for item in sources_raw:
        if not isinstance(item, dict):
            raise ConfigError("each source must be an object with id and path")
        source_id = item.get("id")
        source_path = item.get("path")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ConfigError("each source needs a non-empty id")
        source_id = source_id.strip()
        if not isinstance(source_path, str) or not source_path.strip():
            raise ConfigError(f"source {source_id} needs a non-empty path")
        source_path = source_path.strip()
        if not _valid_source_id(source_id):
            raise ConfigError(f"source id is not a valid folder name: {source_id}")
        if source_id in seen_ids:
            raise ConfigError(f"source ids must be unique: {source_id}")
        seen_ids.add(source_id)
        path = _expand(source_path)
        if not path.is_dir():
            raise ConfigError(f"source {source_id} is not an existing directory: {path}")
        sources.append(Source(id=source_id, path=path))

    for source in sources:
        if source.path == master or source.path.is_relative_to(master):
            raise ConfigError(f"source {source.id} is inside master: {source.path}")
        if master.is_relative_to(source.path):
            raise ConfigError(f"master is inside source {source.id}: {master}")

    return Config(master=master, sources=sources)
