"""Consolidation: copy sources into the master folder."""

import json
import os
import shutil
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from memory_drawer.config import Config, Source
from memory_drawer.fsutil import copy_stream, sha256_file, walk_sorted
from memory_drawer.layout import CONSOLIDATED
from memory_drawer.manifest import Kind, Record, Status, append, load, rewrite

BATCH = 100


class ConsolidateAbort(Exception):
    """Raised when a run cannot continue at all (destination root not creatable)."""


@dataclass(slots=True)
class ScanResult:
    count: int
    total: int
    errors: int


@dataclass(slots=True)
class ConsolidateResult:
    copied: int = 0
    re_copied: int = 0
    already_present: int = 0
    skipped: int = 0
    kind_fixes: int = 0
    bytes_copied: int = 0
    walk_errors: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    case_diffs: list[str] = field(default_factory=list)


def scan(source: Path) -> ScanResult:
    """Count regular files and total bytes in a source, read-only."""
    count = 0
    total = 0
    errors = 0

    def onerror(exc: OSError) -> None:
        nonlocal errors
        errors += 1

    try:
        for base, names in walk_sorted(source, onerror):
            for name in names:
                full = base / name
                if full.is_symlink() or not full.is_file():
                    continue
                try:
                    total += full.stat().st_size
                except OSError:
                    continue
                count += 1
    except OSError:
        errors += 1
    return ScanResult(count=count, total=total, errors=errors)


def _iso_mtime(st: os.stat_result) -> str:
    return datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")


def _next_file_id(records: list[Record]) -> str:
    highest = 0
    for record in records:
        try:
            highest = max(highest, int(record.file_id))
        except ValueError:
            continue
    return f"{highest + 1:08d}"


def _cleanup(path: Path) -> None:
    with suppress(OSError):
        path.unlink()


def _copy_with_retry(src: Path, dst: Path, result: ConsolidateResult) -> str | None:
    """Copy with one retry, cleaning partial artifacts, returning the source sha256."""
    last_error: OSError | None = None
    for _ in range(2):
        try:
            sha256 = copy_stream(src, dst)
        except OSError as exc:
            last_error = exc
            _cleanup(dst)
            continue
        except BaseException:
            _cleanup(dst)
            raise
        try:
            match = dst.stat().st_size == src.stat().st_size
        except OSError as exc:
            last_error = exc
            match = False
        if not match:
            _cleanup(dst)
            continue
        try:
            shutil.copystat(src, dst)
        except OSError as exc:
            result.warnings.append(f"could not preserve mtime for {src}: {exc}")
        return sha256
    result.errors.append(f"copy failed for {src}: {last_error}")
    _cleanup(dst)
    return None


def _unique_dest(dst: Path) -> Path:
    candidate = dst
    n = 2
    while candidate.exists():
        candidate = dst.with_name(f"{dst.stem}_{n}{dst.suffix}")
        n += 1
    return candidate


def _ensure_parent(path: Path, result: ConsolidateResult) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        result.errors.append(f"could not create {path.parent}: {exc}")
        return False
    return True


def _is_sidecar_of(lower_names: dict[str, str], name: str) -> str | None:
    """Return the media name when name is that media's sidecar, else None."""
    if not name.lower().endswith(".json"):
        return None
    return lower_names.get(name[:-5].lower())


def _kind_of(sidecar_of: str | None) -> Kind:
    return Kind.SIDECAR if sidecar_of is not None else Kind.FILE


def _matches(record: Record, size: int, src_mtime: str, sha256: str) -> bool:
    """True when the record matches all four fingerprint fields."""
    return record.size == size and record.src_mtime == src_mtime and record.sha256 == sha256


def _make_record(
    next_id: str,
    source: Source,
    full: Path,
    rel: str,
    target: Path,
    size: int,
    sha256: str,
    src_mtime: str,
    kind: Kind,
    sidecar_of: str | None,
    record_errors: list[str],
) -> Record:
    return Record(
        file_id=next_id,
        source_id=source.id,
        source_path=str(full),
        rel_path=rel,
        dest_path=str(target),
        size=size,
        sha256=sha256,
        src_mtime=src_mtime,
        kind=kind,
        sidecar_of=sidecar_of,
        status=Status.INGESTED,
        errors=record_errors,
    )


def _copy_source(
    config: Config,
    source: Source,
    records: list[Record],
    by_path: dict[str, list[Record]],
    result: ConsolidateResult,
    manifest_path: Path,
) -> None:
    source_root = source.path
    dest_root = config.master / CONSOLIDATED / source.id
    try:
        dest_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConsolidateAbort(f"could not create destination root {dest_root}: {exc}") from exc

    next_id = _next_file_id(records)
    pending: list[Record] = []
    processed = 0

    def onerror(exc: OSError) -> None:
        result.walk_errors += 1

    def flush() -> None:
        if pending:
            append(manifest_path, pending)
            pending.clear()

    try:
        for base, names in walk_sorted(source_root, onerror):
            lower_names = {name.lower(): name for name in names}
            for name in names:
                full = base / name
                if full.is_symlink() or not full.is_file():
                    result.skipped += 1
                    continue
                try:
                    st = full.stat()
                except OSError as exc:
                    result.errors.append(f"could not stat {full}: {exc}")
                    continue
                size = st.st_size
                src_mtime = _iso_mtime(st)
                rel = full.relative_to(source_root).as_posix()
                dst = dest_root / rel
                sidecar_of = _is_sidecar_of(lower_names, name)
                if sidecar_of is not None and sidecar_of != name[:-5]:
                    result.case_diffs.append(str(full))
                kind = _kind_of(sidecar_of)

                path_records = by_path.get(str(full), [])
                rec = path_records[0] if path_records else None
                if rec is not None:
                    if rec.status == Status.QUARANTINED:
                        result.skipped += 1
                        continue
                    meta_matches = any(
                        r.size == size and r.src_mtime == src_mtime for r in path_records
                    )
                    if meta_matches:
                        check_sha = sha256_file(full)
                        if any(_matches(r, size, src_mtime, check_sha) for r in path_records):
                            if rec.kind != kind or rec.sidecar_of != sidecar_of:
                                rec.kind = kind
                                rec.sidecar_of = sidecar_of
                                result.kind_fixes += 1
                            if dst.exists():
                                result.already_present += 1
                            else:
                                if not _ensure_parent(dst, result):
                                    continue
                                if _copy_with_retry(full, dst, result) is not None:
                                    result.re_copied += 1
                                    result.bytes_copied += size
                            continue
                    target = _unique_dest(dst)
                else:
                    if dst.exists():
                        result.errors.append(f"destination exists without a record: {dst}")
                        continue
                    target = dst

                if not _ensure_parent(target, result):
                    continue
                sha = _copy_with_retry(full, target, result)
                if sha is None:
                    continue
                record_errors: list[str] = []
                if sidecar_of is not None:
                    try:
                        json.loads(target.read_text(encoding="utf-8-sig"))
                    except ValueError, UnicodeDecodeError, OSError:
                        record_errors.append("sidecar is not valid JSON")
                record = _make_record(
                    next_id,
                    source,
                    full,
                    rel,
                    target,
                    size,
                    sha,
                    src_mtime,
                    kind,
                    sidecar_of,
                    record_errors,
                )
                next_id = f"{int(next_id) + 1:08d}"
                records.append(record)
                by_path.setdefault(str(full), []).append(record)
                pending.append(record)
                result.copied += 1
                result.bytes_copied += size
                processed += 1
                if processed % 500 == 0:
                    print(f"{processed} files processed from {source.id}", file=sys.stderr)
                if len(pending) >= BATCH:
                    flush()
    except OSError as exc:
        result.errors.append(f"walk failed for {source_root}: {exc}")
    flush()


def consolidate(config: Config, manifest_path: Path) -> ConsolidateResult:
    """Copy all sources into the master folder, returning the run summary."""
    records = load(manifest_path).records
    by_path: dict[str, list[Record]] = {}
    for record in records:
        by_path.setdefault(record.source_path, []).append(record)
    result = ConsolidateResult()
    for source in config.sources:
        _copy_source(config, source, records, by_path, result, manifest_path)
    if result.kind_fixes:
        rewrite(manifest_path, records)
    return result
