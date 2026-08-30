# 0004: Consolidate

Status: approved
Version: 3

Source of truth for the consolidation work: copying every source into the master folder with provenance, hashing original bytes during the copy, pairing Takeout sidecars, driven by the manifest for safe reruns. Builds on spec 0002 (config, dry-run scan) and spec 0003 (manifest). Decisions marked **[DECISION]** have a proposed default, confirm before implementation.

## 1. Purpose and scope

**In:**
- Copy each source into `master/consolidated/<source_id>/<rel_path>`, preserving mtime, computing SHA-256 of the original bytes during the copy
- Sidecar pairing (exact base name, case-insensitive)
- Manifest append for every successful copy; rerun skip rules with self-healing
- Console summary and exit codes

**Out:**
- Dedupe, quarantine, sidecar JSON merge, HTML report (each is its own spec)
- The self-contained HTML phase report is produced by the report piece, not here; 0004 ships only the console summary
- Any modification of sources

## 2. The copy loop

Sources are processed in config order, each walked sorted and without following symlinks. Before the first copy, free space on the master drive is compared with the total source size; when it is short, a warning is printed, matching the 0002 rule (warning, not failure). For every file:

1. Compute the fingerprint (size, mtime) and apply the skip rules (section 4).
2. Stream the copy: read the source in 1 MiB chunks, write to the destination, feed each chunk to the SHA-256 hash as it is read. The hash is always of the original bytes, before any write to the master.
3. Verify the destination size equals the source size. On mismatch, clean up the partial copy and retry once **[DECISION D6]**.
4. On success, append the manifest record (`kind=file` or `kind=sidecar`).
5. Progress: one stderr line per 500 files.

mtime is preserved with `shutil.copystat` after the streamed copy. Windows long paths need no manual handling: Python 3.14 uses extended-length paths automatically.

## 3. Sidecar pairing

- For a media file named `N`, any file named `N + ".json"` in the same directory is its sidecar, matched case-insensitively; all matches pair **[DECISION D5]**.
- Both files are copied; the sidecar record gets `kind=sidecar` and `sidecar_of=N`.
- A JSON with no matching media is an orphan and is copied as a regular file (`kind=file`).
- Case-only differences between the media and its sidecar are flagged in the report.
- A sidecar whose JSON does not parse is still copied and flagged in its record errors; it is never dropped **[DECISION D12]**.

## 4. Idempotency and reruns

Checked per file before copying:

| Situation | Behavior |
|---|---|
| Record with the 4-field match (0003 §5) and dest file present | skip |
| Record with the 4-field match, dest missing, status `ingested` or `survivor` | re-copy, self-healing **[DECISION D2]** |
| Record with status `quarantined` | skip, never re-copy **[DECISION D2]** |
| No record | copy as new |

Failed copies are **not** appended to the manifest: the manifest only holds successfully ingested files. Failures are counted and listed, and the next run retries them naturally **[DECISION D3]**. Reruns do not re-hash existing copies; integrity checking is a future piece, not this one **[DECISION D8]**. A changed file (any of the four fields differs from every record) counts as new and is copied to a suffixed destination (`name_2.ext`, then `_3`, and so on), so both versions stay in the master and the old record stays valid. A file whose kind changed between runs (an orphan JSON that gained its media, or the reverse) is corrected in place on the rerun through the atomic rewrite.

## 5. Error handling

| Failure | Behavior |
|---|---|
| Source file vanished before copy | error, continue |
| Source file unreadable | error, continue |
| Source changed mid-copy (size mismatch) | retry once, then error **[D6]** |
| Write error, disk full | clean up the partial copy, error, continue |
| Destination root for a source cannot be created | abort the run with a clear message **[D10]** |
| mtime preservation fails | warning in the record, not fatal **[D11]** |
| Sidecar JSON invalid | copied, flagged **[D12]** |
| Destination exists with no manifest record | error, skip, never overwrite |
| Directory unreadable during the walk | skipped and counted, per 0002 |
| Interrupted (Ctrl+C) | clean exit 130, per 0002; everything appended so far stays |

Exit codes: 0 when no file errors, 1 when any file error occurred, 2 usage error, 130 interrupted.

## 6. Safety rules

- Sources are opened read-only; nothing is ever written inside a source.
- The program removes only the partial artifacts it created in this run that failed verification. Nothing else is removed, ever **[DECISION D4]**. This is the single interpretation of "never delete": the rule protects user data; a partial artifact of the current run is not user data.
- Existing destinations without a record are never overwritten; quarantined files are never touched.
- Single run at a time; concurrent runs are not supported **[DECISION D9]**, matching the no-locking note in 0003.
- Filenames with control characters are escaped in console lines, so terminal output stays clean.

## 7. CLI

```
python -m memory_drawer consolidate [--config PATH] [--dry-run]
```

- Without `--dry-run`: performs the copy described above. This replaces the "copying is not implemented yet" behavior of 0002.
- `--dry-run`: unchanged from 0002 (validate, preview the plan, touch nothing).
- Console summary after the run: files copied, already present, skipped (symlinks and non-regular files), errors, total bytes.

## 8. Layout

- `memory_drawer/fsutil.py`: shared file helpers (chunked hashing, copy with hash, sorted walk, console-safe text)
- `memory_drawer/consolidate.py`: the source walk (shared with the dry-run scan), the copy loop, sidecar pairing, the console summary
- `memory_drawer/__main__.py`: command wiring; the dry-run scan lives in `consolidate.py` so both modes share one walk
- Manifest at `<master>/manifest.jsonl`, per 0003

## 9. Tests

`tests/test_consolidate.py`, on `tmp_path` fixtures:

- Basic copy: file lands at the right destination, mtime preserved, manifest record matches the source hash
- Rerun: nothing new is copied; a second run appends nothing
- Self-heal: record present, dest deleted, rerun re-copies
- Quarantined record: never re-copied
- Symlinks skipped, non-regular files skipped
- Sidecar pairing (kind, sidecar_of), orphan JSON as a regular file, case-insensitive pairing
- Invalid-JSON sidecar copied and flagged
- Failed copy (monkeypatched): no manifest record, no partial file left in master, run continues
- Size mismatch after copy: retry once, then error
- Source vanished mid-run: error recorded, run continues
- Empty source: zero records, exit 0
- Errors present: exit 1
- Zero-byte file and Unicode names copy correctly

## 10. Acceptance criteria

- [ ] Sources untouched after a run (bytes and mtime identical)
- [ ] Every copied file has a manifest record whose hash is of the original bytes
- [ ] Rerun copies nothing new and self-heals a missing copy
- [ ] Failed copies leave no manifest record and no partial file in master
- [ ] Symlinks and non-regular files are never copied
- [ ] Sidecar pairing works, orphans are files, invalid JSON is flagged
- [ ] Exit 1 on file errors, 0 on a clean run
- [ ] `just check` green

## Change log

- 2026-08-22, v3: shared file helpers moved to `fsutil.py`; kind corrections applied on rerun.
- 2026-08-22, v2: approved, decisions D1-D12 confirmed. Changed files copy to a suffixed destination, preserving both versions.
- 2026-08-22, v1: created as the project's fourth spec, status proposed.
