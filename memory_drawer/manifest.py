"""JSONL manifest of every file in the archive (spec 0003)."""

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HEADER = "# memory-drawer manifest v1"


class ManifestError(Exception):
    """Raised when the manifest is missing its header or corrupt in the middle."""


@dataclass
class Record:
    file_id: str
    source_id: str
    source_path: str
    rel_path: str
    dest_path: str
    size: int
    sha256: str
    src_mtime: str
    kind: str
    sidecar_of: str | None = None
    group_id: str | None = None
    status: str = "ingested"
    quarantine_path: str | None = None
    merged_from: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    records: list[Record]
    truncated: bool = False


def _to_dict(record: Record) -> dict:
    return {
        "file_id": record.file_id,
        "source_id": record.source_id,
        "source_path": record.source_path,
        "rel_path": record.rel_path,
        "dest_path": record.dest_path,
        "size": record.size,
        "sha256": record.sha256,
        "src_mtime": record.src_mtime,
        "kind": record.kind,
        "sidecar_of": record.sidecar_of,
        "group_id": record.group_id,
        "status": record.status,
        "quarantine_path": record.quarantine_path,
        "merged_from": record.merged_from,
        "errors": record.errors,
    }


def _from_dict(data: dict) -> Record:
    try:
        return Record(
            file_id=data["file_id"],
            source_id=data["source_id"],
            source_path=data["source_path"],
            rel_path=data["rel_path"],
            dest_path=data["dest_path"],
            size=data["size"],
            sha256=data["sha256"],
            src_mtime=data["src_mtime"],
            kind=data["kind"],
            sidecar_of=data.get("sidecar_of"),
            group_id=data.get("group_id"),
            status=data.get("status", "ingested"),
            quarantine_path=data.get("quarantine_path"),
            merged_from=data.get("merged_from", []),
            errors=data.get("errors", []),
        )
    except KeyError as exc:
        raise ManifestError(f"record is missing key {exc}") from exc


def append(path: str | Path, records: list[Record]) -> None:
    """Append records, writing the header only when the file is new or empty.

    Records always have the full shape: the Record dataclass requires every
    field at construction, so a malformed record cannot be created.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    is_new = not target.exists() or target.stat().st_size == 0
    with target.open("a", encoding="utf-8") as fh:
        if is_new:
            fh.write(HEADER + "\n")
        for record in records:
            fh.write(json.dumps(_to_dict(record), ensure_ascii=False) + "\n")


def load(path: str | Path) -> Manifest:
    """Read the manifest. Tolerates a truncated last line, flags it as such."""
    target = Path(path)
    if not target.exists():
        return Manifest(records=[])
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError(f"manifest is not valid UTF-8: {target}") from exc
    if not text:
        return Manifest(records=[])
    lines = text.split("\n")
    if lines[0] != HEADER:
        raise ManifestError(f"missing header line in {target}")
    ended_with_newline = text.endswith("\n")
    records: list[Record] = []
    truncated = False
    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            if not ended_with_newline and lineno == len(lines):
                truncated = True
                break
            raise ManifestError(f"corrupt line {lineno} in {target}")
        if not isinstance(data, dict):
            raise ManifestError(f"corrupt line {lineno} in {target}")
        records.append(_from_dict(data))
    return Manifest(records=records, truncated=truncated)


def lookup(records: list[Record], source_path: str) -> Record | None:
    """Return the record for a source path, or None."""
    for record in records:
        if record.source_path == source_path:
            return record
    return None


def already_ingested(
    records: list[Record], source_path: str, size: int, src_mtime: str, sha256: str
) -> bool:
    """True only when all four fields match an existing record."""
    return any(
        record.source_path == source_path
        and record.size == size
        and record.src_mtime == src_mtime
        and record.sha256 == sha256
        for record in records
    )


def rewrite(path: str | Path, records: list[Record]) -> None:
    """Atomically replace the manifest with the given records (temp file + os.replace)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".manifest-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(HEADER + "\n")
            for record in records:
                fh.write(json.dumps(_to_dict(record), ensure_ascii=False) + "\n")
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
