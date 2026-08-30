# 0002: Config and CLI

Status: approved
Version: 3

Source of truth for the config and CLI work: the user-facing entry of the pipeline. It defines `config.json` and the `consolidate` command with a dry-run mode that shows the plan without touching anything. Builds on spec 0001 (package skeleton, layout constants). Decisions marked **[DECISION]** have a proposed default, confirm before implementation.

## 1. Purpose and scope

**In:**
- `config.json`: master folder and source folders, loaded and validated before anything runs
- CLI command `consolidate` with `--dry-run`
- Dry-run output: per-source file counts and byte totals, grand total, free-space check on the master drive
- `config.example.json` committed; `config.json` gitignored

`config.json` is the machine-readable source of truth. An interactive flow (folder pickers with confirmation) is planned so the user never edits JSON by hand; it will generate this file.

**Out:**
- Copying, hashing, dedupe, quarantine, reports (each is its own spec)
- Any write to the master folder

## 2. Config schema

```json
{
  "master": "E:\\master",
  "sources": [
    { "id": "hdd1", "path": "D:\\backups\\hdd1" },
    { "id": "takeout", "path": "D:\\backups\\takeout" }
  ]
}
```

- `master`: the archive root folder
- `sources`: the backup folders to consolidate, each with an `id` (label used in folder names) and a `path`
- Paths may be relative, or contain environment variables (`%VAR%` on Windows, `$VAR` elsewhere); they are expanded and resolved to absolute on load **[DECISION D1]**

## 3. CLI surface

```
python -m memory_drawer consolidate [--config PATH] [--dry-run]
```

- `consolidate`: the command that drives the pipeline; in this spec it only validates and dry-runs
- `--config PATH`: config file, default `config.json` in the working directory **[DECISION D2]**
- `--dry-run`: validate the config, walk the sources read-only, print the plan, touch nothing **[DECISION D3]**
- Without `--dry-run`, print "copying is not implemented yet" and exit 1 **[DECISION D4]**
- Exit codes: 0 success, 1 validation error or not implemented, 2 usage error, 130 interrupted
- Console output is UTF-8 with replacement on encoding errors, so accented names print on any Windows console

## 4. Validation rules (fail fast)

Run in order, stop at the first error. Message format: `config error: <detail>`.

1. The config file exists and parses as JSON
2. Top-level keys are exactly `master` and `sources` (unknown keys rejected) **[DECISION D5]**
3. `master` is a non-empty string and an existing directory
4. `sources` is a non-empty list
5. Each source has a non-empty `id` and a non-empty `path`
6. Source `id`s are unique and valid folder names: stripped of surrounding whitespace, no path separators, no Windows-reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, case-insensitive), no `: * ? " < > |` or control characters, no trailing dot, not `.` or `..`
7. Each source `path` is an existing directory
8. `master` is not inside any source and no source is inside `master` (real paths; prevents copying the archive into itself)
9. Overlapping sources are allowed; duplicates are handled later **[DECISION D6]**

The free-space check is a warning, not an error: after the dry-run walk, if the master drive has less free space than the total source size, print a warning and exit 0.

## 5. Dry-run output

Plain text, English, one line per item. Example:

```
Config OK: E:\master
  hdd1    D:\backups\hdd1        1234 files, 1.2 GB
  takeout D:\backups\takeout     567 files, 890 MB
Total: 1801 files, 2.1 GB
Free space on E: 120 GB (OK)
```

The walk is read-only, sorted, and does not follow symlinks. Directories that cannot be read are skipped and counted; the count is shown as a warning line. If the master drive cannot be queried, free space prints as unknown. Neither case fails the run.

## 6. Layout

- `memory_drawer/config.py`: load and validate, raises `ConfigError` with the message from §4
- `memory_drawer/__main__.py`: `consolidate` subcommand wiring
- `config.example.json`: committed template with placeholder paths
- `config.json`: real paths, gitignored

## 7. Tests

- `tests/test_config.py`: a valid config passes; every rule in §4 fails with the right message (fixtures via `tmp_path`)
- `tests/test_cli.py`: `--dry-run` prints per-source counts and totals; missing config file exits 1; `--help` lists `consolidate`

## 8. Acceptance criteria

- [ ] `consolidate --dry-run` on a valid config prints the plan and touches nothing
- [ ] Every validation rule fails fast with a clear message
- [ ] Free-space warning shown when the master drive is tight
- [ ] `just check` green
- [ ] `config.example.json` committed, `config.json` ignored

## Change log

- 2026-08-22, v3: hardened. Ids reject Windows-reserved names, invalid characters and trailing dots; paths expand environment variables; walk tolerates unreadable directories; free space degrades to unknown; interrupted exits 130; console output is UTF-8.
- 2026-08-22, v2: approved, decisions D1-D6 confirmed.
- 2026-08-22, v1: created as the project's second spec, status proposed.
