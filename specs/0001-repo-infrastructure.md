# 0001: Repo infrastructure specification

Status: proposed
Version: 1

Source of truth for the repo infrastructure work, the step before any pipeline code. Decisions marked **[DECISION]** have a proposed default, confirm before implementation. Slice 1 specifics live in `specs/0002-slice-1-consolidation.md`; this document covers what every slice builds on.

## 1. Purpose and scope

**In:** Python package skeleton, `pyproject.toml` with dev tooling (ruff, pytest, mypy), the live extension map `extensions.json` (seeded and validated), the layout constants module, README updated, and the English-only policy applied repo-wide.

**Out:** pipeline logic (Slice 1 onward), the local web server and its console entry point (later slices, see §3), exiftool integration, `config.json` loading .

## 2. English-only policy

Decision 2026-08-22: nothing in the project is Portuguese. Code, identifiers, comments, docs, specs, report text, config keys, output folder names. This revokes the 2026-08-09 decision that output folders would keep Portuguese names.

| Old (pt) | New (en) | Consumed by |
|---|---|---|
| mestre/ | master/ | all slices |
| consolidado/ | consolidated/ | slice 1 |
| quarentena/ | quarantine/ | all slices |
| relatorios/ | reports/ | slice 1 |
| sem_data/ | undated/ | slice 3 |
| Fotos/ | Photos/ | slice 3 |
| Vídeos/ | Videos/ | slice 3 |
| Músicas/ | Music/ | slice 3 |
| Documentos/ | Documents/ | slice 3 |
| Outros/ | Other/ | slice 3 |
| extensoes.json | extensions.json | slice 3 (seeded now) |

Acceptance: `grep -riE 'mestre|quarentena|relatorios|consolidado|sem_data|extensoes|Fotos|Vídeos|Músicas|Documentos|Outros' docs .github README.md PLAN.md` returns nothing. Lower-case JSON keys like `photos` are not affected.

## 3. Package skeleton

- `memory_drawer/` package with `__init__.py` (module docstring + `__version__ = "0.1.0"`).
- `memory_drawer/__main__.py`: argparse CLI. Registers the `slice1` subcommand now (prints a clear "not implemented yet" message with a non-zero exit); each slice registers its own subcommands. `python -m memory_drawer --help` is the acceptance.
- **No console script in pyproject.toml.** **[DECISION]** The original issue template mentioned an entry point to start the local server; the server only exists in a later slice, so the console script is deferred until that slice. `python -m memory_drawer` is the entry until then.

## 4. pyproject.toml

- Build backend: hatchling (`[build-system] requires = ["hatchling"]`).
- `requires-python = ">=3.12"` (dev machine has 3.12.7; the Windows machine must install 3.12+).
- Runtime dependency: Pillow (only one so far; exiftool stays out of the package, it is invoked as an external binary in slice 2).
- `[project.optional-dependencies] dev = ["ruff", "pytest", "mypy"]`.
- `[tool.ruff]`: `target-version = "py312"`, `line-length = 100`, `select = ["E4", "E7", "E9", "F", "I", "UP"]`.
- `[tool.mypy]`: `python_version = "3.12"`, `ignore_missing_imports = true` (Pillow ships no stubs), `check_untyped_defs = true`.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `addopts = "-q"`.

## 5. extensions.json

- Location: repo root, `extensions.json` (renamed from `extensoes.json`).
- Schema: top-level object with keys exactly `photos`, `videos`, `music`, `documents` (lower case); each maps to an array of lower-case extensions without the dot. `other` is implicit: anything unlisted classifies as Other, never forced (PLAN.md §8 rule).
- Validation, enforced by `tests/test_extensions.py`: keys are only the four known categories; every extension lower-case and dotless; no extension twice within a category; no extension in two categories.
- Seed: the lists from PLAN.md §8 with one fix. **[DECISION]** `mod` appears in both the videos and the music lists in PLAN.md; it is an Amiga module audio format, so it stays only under music.
- Consumption (slice 3, not here): the classify phase reads this file.

## 6. Layout constants module (memory_drawer/layout.py)

Single source of truth for the master folder structure, consumed by every slice:

```python
MASTER = "master"             # root of the archive
CONSOLIDATED = "consolidated"
QUARANTINE = "quarantine"
REPORTS = "reports"
UNDATED = "undated"           # consumed by slice 3
MANIFEST = "manifest.jsonl"

CATEGORY_DIRS = {             # consumed by slice 3
    "photos": "Photos",
    "videos": "Videos",
    "music": "Music",
    "documents": "Documents",
    "other": "Other",
}
```

Only `MASTER`, `CONSOLIDATED`, `QUARANTINE`, `REPORTS`, `MANIFEST` are used now; the rest are seeded by this spec and consumed later. Thumbnails: slice 1 embeds them in reports as data URIs, so no thumbnail folder exists. **[DECISION]** A `thumbnails/` directory is only created if a later slice stops embedding.

## 7. Setup and tooling (what "passing" means)

Target machine is Windows; the dev machine is Linux. Commands differ only in the venv path:

```
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"     (Windows)
.venv/bin/pip install -e ".[dev]"         (Linux)

.venv\Scripts\python -m memory_drawer --help
.venv\Scripts\ruff check .
.venv\Scripts\mypy memory_drawer
.venv\Scripts\pytest
```

All four commands clean. `ruff check .` and `mypy memory_drawer` are part of the dev loop from now on, not optional.

## 8. README update

- New "Setup" section with the venv commands above.
- "Status": infrastructure in place, Slice 1 in progress.
- Tagline, principles, license unchanged.

## 9. Acceptance criteria

- [ ] `python -m memory_drawer --help` works in a fresh venv (Windows and Linux)
- [ ] ruff, mypy, pytest clean on the skeleton
- [ ] `extensions.json` validates against the schema in §5 (test included; `mod` under music only)
- [ ] English-only grep from §2 returns nothing across docs, templates, README, PLAN.md
- [ ] README shows setup and the current entry point

## Change log

- 2026-08-22, v1: created as part of the spec-driven conversion (previously `docs/01-repo-infra-spec.md`). Status proposed, awaiting approval of the three decisions.
