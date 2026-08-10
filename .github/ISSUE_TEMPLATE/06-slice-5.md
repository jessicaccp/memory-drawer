---
name: "06: Slice 5. Final reports + Google Drive sync"
about: Quarantine report (the human gate) + Drive sync workflow. Update README with the full user journey.
title: "06: Slice 5. Final reports + Google Drive sync"
labels: slice-5
---

## Goal
PLAN.md §5, phase 9 + §10: the final quarantine report (the human gate before anything is manually deleted) and the Drive sync story.

## Scope (in)
- **Quarantine report**: self-contained HTML listing everything in `quarentena/` with thumbnails, source path, hash, size, date, the last gate before the owner empties the folder manually.
- **Master report**: full picture after all phases (totals per category, files organized, space reclaimed).
- **Drive sync**: documented workflow (rclone or Drive app) mirroring the organized master to Google Drive; master stays the source of truth.
- **README**: update with usage guide + screenshots.

## Acceptance criteria
- [ ] Quarantine report opens in a browser, no external assets
- [ ] Every quarantine entry shows source path + reason + thumbnail
- [ ] Sync docs: clear step-by-step, tested with a small folder first
- [ ] README reflects the full user journey (test subset → real archive)
