# 0005: Code quality and modernization

Status: done
Version: 3

Source of truth for the readability and performance pass over the code: modern Python idioms, cleaner organization, faster execution, no behavior change. Builds on specs 0001 to 0004, which already define the tooling and the module layout. Decisions marked **[DECISION]** have a proposed default, confirm before implementation.

## 1. Purpose and scope

**In:**
- Modern Python idioms available in 3.14 (the pinned version)
- Cleaner structure inside the existing modules, no new modules
- Type safety for values that are currently loose strings
- Performance: remove the quadratic hot path, avoid wasted reads, fewer syscalls

**Out:**
- Any behavior change. The test suite passes unchanged, with the same count
- Any API change to the module surface used by the CLI
- New dependencies, new features, new modules

## 2. Patterns already in place (verified)

These patterns, defined across specs 0001 to 0004, are followed today and stay as they are:

- Dataclasses for data holders (config, manifest, results)
- PEP 604 unions (`str | None`) and built-in generics (`list[str]`)
- `pathlib` everywhere, no manual string path assembly
- Fail-fast validation with dedicated exception types
- Shared file helpers in `fsutil.py`, layout constants in `layout.py`
- UTF-8 reads with BOM tolerance, atomic writes (temp + replace)
- English-only identifiers and messages

## 3. Modernizations

1. **`Path.walk` replaces `os.walk`** in `fsutil.walk_sorted`. Available since 3.12, yields `Path` roots and sorts cleanly; `follow_symlinks=False` matches the current behavior **[DECISION D1]**.
2. **`Kind` and `Status` as `StrEnum`** in `manifest.py`. The values stay identical (`file`, `sidecar`, `ingested`, `survivor`, `quarantined`, `error`), so existing manifests remain readable. `StrEnum` members are strings, so JSON serialization and the `data.get("status", "ingested")` defaults keep working, with type checking on top **[DECISION D2]**.
3. **`slots=True` on every dataclass** (config, manifest, consolidate results): less memory, faster access, no attribute drift. `Source` and `Config` gain `slots` next to their existing `frozen` **[DECISION D3]**.
4. **One line writer in `manifest.py`**: the duplicated `json.dumps(_to_dict(record), ensure_ascii=False) + "\n"` in `append` and `rewrite` becomes a single `_line(record)` helper **[DECISION D4]**.
5. **Split the per-file loop in `consolidate.py`**: the long loop body in `_copy_source` gets focused helpers for the kind computation, the record assembly, and the destination decision, each with a one-line docstring. Behavior identical **[DECISION D5]**.
6. **`_human_size` without the unreachable assertion**: restructured so every path returns naturally **[DECISION D6]**.
7. **Ruff rules extended** with `SIM` (simplify) and `RUF` (ruff-specific), and the findings they raise are fixed. This changes the tooling config from spec 0001; that spec gets a version note **[DECISION D7]**.

## 4. Performance

The consolidation loop today is **quadratic**: `lookup` and `already_ingested` (0003) scan the whole records list, and both run for every file. With 100k files that is roughly 5 billion comparisons, the dominant cost of a run by far. The items below remove that and the other waste.

1. **Path index, O(n²) to O(n)** **[DECISION D8]**: build `by_path: dict[str, list[Record]]` once per run; per-file decisions use only that path's records (usually one or two). `lookup` and `already_ingested` stay unchanged as public API; `consolidate` uses the index internally.
2. **Hash only when size and mtime match** **[DECISION D9]**: the four-field match needs a hash, but when size or `src_mtime` differs the file is new by definition, and its hash is computed during the copy anyway. Today a changed file is hashed twice (once for the check, once for the copy) and an unchanged one is hashed once. With the guard, changed files are read once, unchanged ones only when the rare same-size-same-mtime collision needs confirmation.
3. **Batch manifest appends** **[DECISION D10]**: one file open per record becomes one per 100 records. Crash safety is preserved within the batch.
4. **`CHUNK` from 1 MiB to 4 MiB** **[DECISION D11]**: fewer read/write syscalls on copy and hash.
5. **Rerun trust heuristic (rejected by default)** **[DECISION D12]**: on rerun, treat a record whose size and `src_mtime` match as already present without re-hashing the source. This makes reruns read nothing, but a file with identical size and mtime yet different content would be skipped. The strict four-field match stays unless you accept the trade-off.
6. **Memory is fine at this scale, no change**: a record is roughly 0.5 KB, so 100k records load in tens of MB; the path index duplicates references, not data.

## 5. Non-goals and result stability

- No behavior change: the pipeline, the manifest format, the CLI output and the exit codes stay identical
- No streaming manifest, no multiprocessing, no new dependencies, no new modules
- No renames of public functions used by the CLI

Why each change cannot alter the result:

| Change | Why the result stays identical |
|---|---|
| D1 `Path.walk` | same sorted order, same `follow_symlinks=False`, so the same files in the same order |
| D2 `StrEnum` | identical string values, JSON-native, so manifest bytes are identical |
| D3 `slots` | memory layout only |
| D4 `_line` | identical serialization |
| D5 helpers | the same decisions and the same records, covered by the existing tests |
| D6 `_human_size` | the same numbers |
| D7 ruff rules | no runtime effect |
| D8 path index | a cache of the same search; `lookup` and `already_ingested` are unchanged API |
| D9 hash guard | the recorded hash always comes from the copy, unchanged; the guard preserves the exact four-field semantics |
| D10 batched appends | the same bytes in the same order |
| D11 chunk size | sha256 is independent of chunk boundaries; copied bytes are identical |
| D12 rerun heuristic | rejected, so nothing changes |

## 6. Verification

- `just check` green (ruff, ruff format, mypy, pytest)
- The 116 existing tests pass without modification
- A golden end-to-end test (`tests/test_golden.py`) is added and green before the refactor starts, pinning the exact manifest content, destination bytes, summary line and exit code. It must stay green through every change
- The diff is reviewed as refactoring-only: every changed line is a style, structure or index change, never a logic change

## 7. Acceptance criteria

- [ ] The 116 existing tests pass without modification
- [ ] `just check` green, including the golden test
- [ ] `kind` and `status` typed via `StrEnum`, values backward compatible with existing manifests
- [ ] Per-file decisions use the path index, no full-manifest scan in the loop
- [ ] No new dependencies, no new modules
- [ ] Diff is refactoring-only

## Change log

- 2026-08-22, v3: implemented and verified. 117 tests green, golden baseline unchanged, behavior identical.
- 2026-08-22, v2: approved, decisions D1-D12 confirmed. D12 stays rejected.
- 2026-08-22, v1: created as the project's fifth spec, status proposed.
