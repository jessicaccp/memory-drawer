# 0001: Repo infrastructure specification

Status: done
Version: 6

Source of truth for the repo infrastructure work, the step before any pipeline code.

## 1. Purpose and scope

**In:** Python package skeleton, `pyproject.toml` with dev tooling (ruff, pytest, mypy), the live extension map `extensions.json` (seeded and validated), the layout constants module, README updated, and the English-only policy applied repo-wide.

**Out:** pipeline logic, the local web server and its console entry point (see §3), exiftool integration, `config.json` loading.

## 2. English-only policy

Nothing in the project is Portuguese: code, identifiers, comments, docs, specs, report text, config keys, output folder names.

Folder names, definitive:

- master/
- consolidated/
- quarantine/
- reports/

Extension map file: `extensions.json` (repo root).

Acceptance: the English-only policy is enforced by `tests/test_no_portuguese.py`; the forbidden terms live there as data so that specs stay English-only.

## 3. Package skeleton

- `memory_drawer/` package with `__init__.py` (module docstring + `__version__ = "0.1.0"`).
- `memory_drawer/__main__.py`: argparse CLI (help and version). Commands are added when their spec is implemented. `python -m memory_drawer --help` is the acceptance.
- **No console script in pyproject.toml.** `python -m memory_drawer` is the entry point; a console script is added when a spec requires one.

## 4. pyproject.toml

- Build backend: hatchling (`[build-system] requires = ["hatchling"]`).
- `requires-python = ">=3.14"` (uv installs 3.14 on both machines; the Windows machine does not need a system Python).
- Runtime dependency: Pillow (only one so far; exiftool stays out of the package, it is invoked as an external binary).
- Dev tools in `[dependency-groups] dev = ["ruff", "pytest", "mypy"]` (PEP 735, installed by `uv sync`).
- `[tool.ruff]`: `target-version = "py314"`, `line-length = 100`, `select = ["E4", "E7", "E9", "F", "I", "UP"]`.
- `[tool.mypy]`: `python_version = "3.14"`, `ignore_missing_imports = true` (Pillow ships no stubs), `check_untyped_defs = true`.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `addopts = "-q"`.

## 5. extensions.json

- Location: repo root, `extensions.json`.
- Schema: top-level object with keys exactly `photos`, `videos`, `music`, `documents` (lower case); each maps to an array of lower-case extensions without the dot. `other` is implicit: anything unlisted classifies as Other, never forced (PLAN.md §8 rule).
- Validation, enforced by `tests/test_extensions.py`: keys are only the four known categories; every extension lower-case and dotless; no extension twice within a category; no extension in two categories.
- Seed: the lists from PLAN.md §8, with `mod` only under music (it is an Amiga module audio format, listed under both videos and music in PLAN.md).

## 6. Layout constants module (memory_drawer/layout.py)

Single source of truth for the master folder structure:

```python
MASTER = "master"  # root of the archive
CONSOLIDATED = "consolidated"
QUARANTINE = "quarantine"
REPORTS = "reports"
MANIFEST = "manifest.jsonl"
```

Thumbnails: reports embed them as data URIs, so no thumbnail folder exists. A `thumbnails/` directory is only added when a spec requires it.

## 7. Setup and tooling (what "passing" means)

The environment is managed by uv (https://docs.astral.sh/uv/). uv installs its own Python 3.14, so the machine does not need a system Python:

```
uv sync
```

This creates `.venv` and installs the package and dev tools (ruff, mypy, pytest) from pyproject.toml, pinned by `uv.lock`. Commands run through `uv run`:

```
uv run python -m memory_drawer --help
uv run ruff check .
uv run ruff format --check .
uv run mypy memory_drawer
uv run pytest
```

Project recipes live in `justfile`: `just check` runs all four checks, `just format` formats. All checks clean. `ruff check .` and `mypy memory_drawer` are part of the dev loop from now on, not optional.

## 8. README update

- New "Setup" section with the venv commands above.
- "Status": infrastructure in place.
- Tagline, principles, license unchanged.

## 9. Acceptance criteria

- [ ] `uv sync` from a clean checkout, then `uv run python -m memory_drawer --help` works (Windows and Linux)
- [ ] ruff, ruff format --check, mypy, pytest clean on the skeleton
- [ ] `extensions.json` validates against the schema in §5 (test included; `mod` under music only)
- [ ] English-only grep from §2 returns nothing across the repo (specs exempt)
- [ ] README shows setup and the current entry point

## Change log

- 2026-08-22, v6: Python pinned to 3.14 (pyproject, ruff, mypy, `.python-version`).
- 2026-08-22, v5: environment moved to uv (dev tools in a dependency group, setup via `uv sync`), ruff format added to the checks, project recipes in `justfile`.
- 2026-08-22, v4: English-only acceptance moved into a test so no Portuguese text stays in specs; the placeholder command stub removed, commands arrive with their specs.
- 2026-08-22, v3: implemented on feature/01-infra, acceptance criteria verified (Linux; Windows venv check pending on the target machine).
- 2026-08-22, v2: approved, the three decisions confirmed.
- 2026-08-22, v1: created as the project's first spec. Status proposed, awaiting approval of the three decisions.
