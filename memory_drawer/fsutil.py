"""Shared file helpers: chunked hashing, copy with hash, sorted walks."""

import hashlib
import os
from collections.abc import Callable, Iterator
from pathlib import Path

CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Hash a file in chunks, never loading it whole."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def copy_stream(src: Path, dst: Path) -> str:
    """Copy src to dst in chunks, returning the sha256 of the source bytes."""
    digest = hashlib.sha256()
    with src.open("rb") as fin, dst.open("wb") as fout:
        while True:
            chunk = fin.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            fout.write(chunk)
    return digest.hexdigest()


def walk_sorted(root: Path, onerror: Callable[[OSError], None]) -> Iterator[tuple[Path, list[str]]]:
    """Walk a tree without following symlinks, yielding sorted directories and files."""
    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror, followlinks=False):
        dirnames.sort()
        yield Path(dirpath), sorted(filenames)


def escape_control(text: str) -> str:
    """Make text console-safe by escaping control characters."""
    return "".join(f"\\x{ord(c):02x}" if ord(c) < 32 or ord(c) == 127 else c for c in text)
