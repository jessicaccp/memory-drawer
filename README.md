# memory-drawer

> Every archive starts as the drawer where photos pile up for years. This tool turns that drawer into an archive.

A personal tool to organize a twenty-year photo archive scattered across multiple backups: external drives, old CDs, a retired notebook, Google Drive, Google Photos and Google Takeout exports.

memory-drawer consolidates everything into one master folder, finds duplicates, restores metadata that exports stripped away, and organizes files by type and date. It never deletes a single file: duplicates go to a quarantine folder, and every decision is reviewed by the owner through reports with thumbnails.

## Principles

- **Never deletes.** Files only move to a quarantine folder; only a human removes them.
- **Works on a copy.** Original backups are never touched.
- **Human review where certainty ends.** Only byte-identical files are handled automatically.
- **Everything is reported.** HTML reports with thumbnails after every phase.

## Setup

Target machine is Windows; the dev machine is Linux. Commands differ only in the venv path.

```
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"     (Windows)
.venv/bin/pip install -e ".[dev]"         (Linux)
```

Run the CLI and the checks:

```
python -m memory_drawer --help
ruff check .
mypy memory_drawer
pytest
```

## Status

Early planning. Development is spec-driven: per-slice contracts live in [specs/](specs/), approved before implementation. Infrastructure in place.

## License

[CC BY-NC 4.0](LICENSE): share and adapt, noncommercial use only, attribution required.
