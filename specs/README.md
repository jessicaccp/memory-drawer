# Specs

Source of truth for implementation, one numbered spec per slice. `PLAN.md` holds the requirements; specs hold the per-slice contracts.

Workflow: a spec is written, reviewed, then approved (status field), then implemented against its acceptance criteria. Editing a spec creates a new version: the previous version stays in git history and the spec's change log records the edit.

Status values: `proposed`, `approved`, `in-progress`, `done`, `superseded`.

| # | Spec | Status |
|---|---|---|
| 0001 | [Repo infrastructure](0001-repo-infrastructure.md) | proposed |
