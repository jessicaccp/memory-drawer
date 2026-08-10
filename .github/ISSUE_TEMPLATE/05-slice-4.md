---
name: "05: Slice 4. Similar review queue (near-duplicates, images only)"
about: Human review of near-duplicates with thumbnails. Images only; videos stay byte-exact.
title: "05: Slice 4. Similar review queue (near-duplicates, images only)"
labels: slice-4
---

## Goal
PLAN.md §5, phase 6: surface near-duplicates (re-saved/re-encoded images) in a human review UI with thumbnails, the last piece where the owner decides. Videos remain byte-exact only (Slice 1).

## Scope (in)
- **Detection**: perceptual hash on normalized thumbnail (32×32 grayscale), conservative threshold; images only.
- **Review UI**: group-by-group with thumbnails + key metadata + provenance paths; actions per file: **keep / quarantine / not similar**; progress persisted so a session can resume.
- **Report**: every decision; thumbnails embedded.

## Scope (out)
Anything beyond images (videos, documents). Automatic deletion: never.

## Acceptance criteria
- [ ] A re-saved JPEG (same photo, re-encoded) groups with its original
- [ ] False-positive check: similar-but-distinct photos (e.g., a selfie burst) appear as separate groups or are separable with "not similar"
- [ ] "Not similar" splits a group permanently (persisted decision)
- [ ] Quarantine action only moves to `quarentena/`, nothing is deleted
- [ ] Resumable: close browser mid-review, reopen, continue from progress
- [ ] Test subset includes WhatsApp-style re-compressed images
