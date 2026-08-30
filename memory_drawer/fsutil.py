"""Shared file helpers: chunked hashing, copy with hash, sorted walks."""

import hashlib
from collections.abc import Callable, Iterator
from pathlib import Path

CHUNK = 4 * 1024 * 1024


def _iter_chunks(fh) -> Iterator[bytes]:
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            return
        yield chunk


def sha256_file(path: Path) -> str:
    """Hash a file in chunks, never loading it whole."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in _iter_chunks(fh):
            digest.update(chunk)
    return digest.hexdigest()


def copy_stream(src: Path, dst: Path) -> str:
    """Copy src to dst in chunks, returning the sha256 of the source bytes."""
    digest = hashlib.sha256()
    with src.open("rb") as fin, dst.open("wb") as fout:
        for chunk in _iter_chunks(fin):
            digest.update(chunk)
            fout.write(chunk)
    return digest.hexdigest()


def walk_sorted(root: Path, onerror: Callable[[OSError], None]) -> Iterator[tuple[Path, list[str]]]:
    """Walk a tree without following symlinks, yielding sorted directories and files."""
    for base, dirs, files in root.walk(on_error=onerror, follow_symlinks=False):
        dirs.sort()
        yield base, sorted(files)
