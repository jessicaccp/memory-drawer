---
name: "02: Slice 1. Consolidate + hash + byte-exact dedupe + report"
about: First pipeline slice (PLAN.md phases 1-3). Validate on a test subset before the real archive.
title: "02: Slice 1. Consolidate + hash + byte-exact dedupe + report"
labels: slice-1
---

## Goal
First working slice of the pipeline (PLAN.md §5, phases 1-3): pull all backups into a master folder, hash original bytes, dedupe byte-identical files automatically, and produce the phase report.

## Scope (in)
- **Consolidate**: copy source folders into `mestre/`; record provenance (source path) per file in a manifest; pair Takeout `.json` sidecars by exact base name (`IMG_1234.JPG` ↔ `IMG_1234.JPG.json`); never modify sources.
- **Hash**: SHA-256 of original bytes, written before any metadata write.
- **Dedupe byte-exact**: group by hash; survivor = first encountered (deterministic); losers moved to `quarentena/`; sidecar JSON of losers merged into survivor (only when base-name parity holds); manifest updated.
- **Report**: self-contained HTML per phase with embedded thumbnails; every group, survivor, losers, sizes, hashes, provenance paths.

## Scope (out)
Metadata restoration, date/similar review queues, classification, organization, renaming. Covered in later slices.

## Acceptance criteria
- [ ] Runs on a **test subset** (user-provided folder of mixed files, incl. duplicates + a Takeout export pair) before touching the real archive
- [ ] Sources untouched: filesystem of source folders unchanged (verify mtime)
- [ ] Every byte-identical group has exactly one survivor, rest in quarantine
- [ ] Quarantine contains **nothing deleted**; report lists every decision
- [ ] Sidecar merge: survivor receives `photoTakenTime`/geo only when base-name + hash parity both hold; mismatches flagged, never guessed
- [ ] Report opens in a browser with thumbnails, no external assets
- [ ] Phase can be **re-run safely** (idempotent; manifest-driven)
