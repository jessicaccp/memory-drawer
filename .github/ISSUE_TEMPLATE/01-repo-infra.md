---
name: "01: Repo infrastructure"
about: First step, defines the skeleton before any code. Package, tooling, extensoes.json.
title: "01: Repo infrastructure"
labels: infra
---

## Goal
Set up the repo so all later slices land on solid ground: package skeleton, tooling, config, and the working document that drives the project.

## Deliverables
- Python package skeleton (`memory_drawer/`), `pyproject.toml` with `pyproject` build backend, entry point `memory-drawer` (CLI to start the local server).
- Dev tooling: `ruff`, `pytest`, `mypy` (config in `pyproject.toml`).
- `extensoes.json` — the live extension→category map (Fotos/Vídeos/Músicas/Documentos/Outros), seeded with the broad list from `PLAN.md` §8.
- Decision/config module: master folder layout, quarantine/reports/thumbnail locations, report dir.
- `PLAN.md` stays the requirements source of truth.

## Acceptance criteria
- [ ] `python -m memory_drawer --help` works from a fresh venv
- [ ] `ruff`, `mypy`, `pytest` all pass on the skeleton
- [ ] `extensoes.json` validates against a schema (all keys known categories)
- [ ] README reflects actual package entry point
