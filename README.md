# memory-drawer

> Every archive starts as the drawer where memories pile up for years. This tool turns that drawer into an archive.

memory-drawer consolidates a scattered archive into one master folder, removes exact duplicates, restores metadata that exports stripped away, and organizes files by type and date. Photos and videos are the main focus, but every kind of file is handled.

It works on a copy and nothing is lost: originals are never touched, duplicates go to a quarantine folder, and every decision is reviewed by the owner through self-contained HTML reports with thumbnails.

## Principles

- **Works on a copy.** Original backups are never touched.
- **Nothing is lost.** Files only move to a quarantine folder; only a human removes them.
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

In development. Work is organized by numbered specs in [specs/](specs/), each approved before implementation.

## License

[CC BY-NC 4.0](LICENSE): share and adapt, noncommercial use only, attribution required.
