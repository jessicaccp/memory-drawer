# 0003: Manifest

Status: approved
Version: 2

Source of truth for the manifest: the JSONL record of every file in the archive, the basis for provenance and idempotency. Builds on spec 0001 (layout constants) and spec 0002 (config). Decisions marked **[DECISION]** have a proposed default, confirm before implementation.

## 1. Purpose and scope

**In:**
- Record schema, one JSON object per file
- JSONL file at `<master>/manifest.jsonl` (the `MANIFEST` constant from spec 0001 §6)
- Append-only writes with a format-version header line
- Read: full load into memory, lookup by source path
- Idempotency rule: a file already ingested is skipped on reruns

**Out:**
- Copying, hashing, dedupe, quarantine, reports (each is its own spec)
- Editing or deleting existing records; the manifest only grows, except for the documented atomic rewrite (see D1)

## 2. File format

- Path: `<master>/manifest.jsonl`
- Line 1 is the header: `# memory-drawer manifest v1`
- One JSON object per line after the header, UTF-8, compact (no pretty printing)
- A trailing newline after every record
- The header doubles as a corruption check: a valid manifest always starts with it

## 3. Record schema

```json
{
  "file_id": "00000001",
  "source_id": "hdd1",
  "source_path": "D:\\backups\\hdd1\\IMG_1234.JPG",
  "rel_path": "IMG_1234.JPG",
  "dest_path": "E:\\master\\consolidated\\hdd1\\IMG_1234.JPG",
  "size": 2843562,
  "sha256": "ab12…",
  "src_mtime": "2011-06-04T14:22:11-03:00",
  "kind": "file",
  "sidecar_of": null,
  "group_id": null,
  "status": "ingested",
  "quarantine_path": null,
  "merged_from": [],
  "errors": []
}
```

- `file_id`: zero-padded sequential integer, unique within the manifest **[DECISION D4]**
- `source_id` and `source_path`: from the config (spec 0002), absolute
- `rel_path`: path relative to the source root, forward slashes
- `dest_path`: where the copy lives, `consolidated/<source_id>/<rel_path>`
- `size`, `src_mtime`, `sha256`: of the original bytes
- `src_mtime`: ISO 8601 with offset
- `kind`: `file` or `sidecar`
- `sidecar_of`: base name of the media file, null for regular files
- `status`: `ingested`, `survivor`, `quarantined`, or `error`
- `merged_from`: list of sidecar paths merged into this file, empty by default
- `errors`: list of messages, empty by default

## 4. Module (memory_drawer/manifest.py)

- `append(path, records)`: opens in append mode, writes the header if the file is new or empty, writes each record as a line. Validates that every record has the required keys; a malformed record raises `ManifestError`. **[DECISION D6]**
- `load(path) -> Manifest`: parses the file. `Manifest` carries `records` (list) and `truncated` (bool). A missing file is an empty manifest, not an error.
- `lookup(records, source_path) -> Record | None`: exact match on the absolute source path.
- `already_ingested(records, source_path, size, src_mtime, sha256) -> bool`: true only when all four fields match an existing record **[DECISION D2]**.
- `rewrite(path, records)`: writes to a temp file in the same directory, then `os.replace` (atomic). Only used by a phase that changes statuses; append is the normal write path **[DECISION D1]**.

## 5. Idempotency rule

A file is already ingested when a record exists with the same `source_path` and `size` and `src_mtime` and `sha256`. If any field differs, the file counts as new and gets a new record; duplicates that result are resolved later. This makes reruns stable: nothing already ingested is re-copied, and nothing already decided is revisited.

## 6. Robustness

- Header check: a non-empty manifest whose first line is not the header is invalid, `ManifestError` **[DECISION D5]**.
- Truncated last line (crash mid-append, invalid JSON at the end): tolerated, the load completes and `truncated` is set **[DECISION D3]**.
- Corrupt line in the middle: `ManifestError` with the line number, nothing silent.
- Decode failure (binary garbage): `ManifestError`.
- All reads use the same file the whole run wrote to; no locking is needed for single-user local use.

## 7. Layout

- `memory_drawer/manifest.py`: the module described in §4
- The manifest file itself lives in the master folder, per the `MANIFEST` constant (spec 0001 §6)
- No other new files

## 8. Tests

`tests/test_manifest.py`:

- Append then load round-trips identical records
- Appending to an existing file does not repeat the header
- `already_ingested` is true on the exact four-field match, false when any field differs
- `lookup` finds by source path, returns None when absent
- A truncated trailing line loads with `truncated` set and all prior records intact
- A corrupt middle line raises `ManifestError`
- A non-empty file without the header raises `ManifestError`
- `rewrite` survives a reload with identical content
- Accented and emoji paths round-trip intact

## 9. Acceptance criteria

- [ ] Round-trip: append then load returns identical records
- [ ] Rerun safety: `already_ingested` is true only on the four-field match
- [ ] A crashed append (truncated last line) loads without data loss and is flagged
- [ ] `rewrite` is atomic and content-preserving
- [ ] `just check` green
- [ ] Accented and emoji paths survive the round-trip

## Change log

- 2026-08-22, v2: approved, decisions D1-D6 confirmed.
- 2026-08-22, v1: created as the project's third spec, status proposed.
