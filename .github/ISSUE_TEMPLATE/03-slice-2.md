---
name: "03: Slice 2. Metadata restore + date review queue"
about: Fill metadata gaps from Takeout JSONs (never overwrite), then resolve real date conflicts in a review UI.
title: "03: Slice 2. Metadata restore + date review queue"
labels: slice-2
---

## Goal
PLAN.md §5, phases 4-5: fill metadata gaps from Takeout JSONs (never overwrite), then let the owner resolve real date conflicts in a review UI.

## Scope (in)
- **Restore**: for survivors lacking EXIF dates/GPS, write from paired JSON (`photoTakenTime`, `geoData`); EXIF > JSON; **all** EXIF date tags read (`DateTimeOriginal` primary; `CreateDate`, `DateTimeDigitized`, `ModifyDate` for consistency); UTC-3, or `timeZoneOffsetSeconds` when present.
- **Date review queue**: files whose sources disagree by >12h or different calendar day, or with no reliable source, appear in the local web UI with all sources shown (EXIF / JSON / filename pattern / filesystem dates); owner selects the correct one (or "leave as-is"); choice written to EXIF.
- **Report**: before→after per file; conflicts flagged; sources used.

## Scope (out)
Similar review, classification, organization. Covered in later slices.

## Acceptance criteria
- [ ] Gap-fill only: files with existing EXIF dates are never overwritten
- [ ] Minutes-level clock noise auto-resolves by priority, never queued
- [ ] Review queue contains exactly the conflict/undated set (threshold test)
- [ ] Chosen date written via exiftool; re-run does not duplicate writes
- [ ] Report shows every source value per conflicted file
- [ ] Test subset: a Takeout export (JSON present), a stripped file, a file with healthy EXIF, each handled correctly
