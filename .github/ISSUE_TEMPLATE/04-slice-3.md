---
name: "04: Slice 3. Classify + organize + rename"
about: Classify by extension, then organize by date with rename (photos/videos only). Collisions and undated files handled safely.
title: "04: Slice 3. Classify + organize + rename"
labels: slice-3
---

## Goal
PLAN.md §5, phases 7-8: classify by extension into Fotos/Vídeos/Músicas/Documentos/Outros, then organize by date with rename, photos/videos only.

## Scope (in)
- **Classify**: `extensoes.json` map; unknown extension → `Outros` (never forced).
- **Organize**: `Fotos/YYYY/YYYY-MM/yyyy-mm-dd_hh-mm-ss.ext` (local time, best date from Slice 2); `Músicas/` `Documentos/` `Outros/` flat; collisions get a suffix (`_2`); no reliable date → `sem_data/`, not renamed, flagged in report; months >1000 files auto-split by day.
- **Report**: rename/move log, old path, new path, date source used.

## Scope (out)
Similar review and final Drive sync. Covered in later slices.

## Acceptance criteria
- [ ] Every photo/video lands in `Fotos|Vídeos/YYYY/YYYY-MM` with the exact `yyyy-mm-dd_hh-mm-ss` pattern (local time)
- [ ] Collision test: two files resolving to the same name get distinct suffixes
- [ ] Undated files are never renamed, never silently dropped, flagged
- [ ] Unknown extension → `Outros`, listed in report
- [ ] All original bytes preserved: hash of moved file == hash before move
- [ ] Run on test subset first; dry-run mode shows planned moves before executing
