"""Enforce the English-only policy (spec 0001 §2): no Portuguese in the repo.

The forbidden terms live here as data so that specs stay English-only.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = [
    "mestre",
    "quarentena",
    "relatorios",
    "consolidado",
    "sem_data",
    "extensoes",
    "Fotos",
    "Vídeos",
    "Músicas",
    "Documentos",
    "Outros",
]
EXCLUDE_DIRS = {".git", ".venv"}


def test_no_forbidden_terms() -> None:
    self_name = Path(__file__).name
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name == self_name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for term in FORBIDDEN:
            if term.lower() in text.lower():
                hits.append(f"{path}: {term}")
    assert not hits, "forbidden terms found:\n" + "\n".join(hits)
