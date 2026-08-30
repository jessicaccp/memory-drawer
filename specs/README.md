# Specs

Source of truth for implementation, one numbered spec per piece of work. Specs hold the implementation contracts.

Workflow: a spec is written, reviewed, then approved (status field), then implemented against its acceptance criteria. Editing a spec creates a new version: the previous version stays in git history and the spec's change log records the edit.

Status values: `proposed`, `approved`, `in-progress`, `done`, `superseded`.

| # | Spec | Status |
|---|---|---|
| 0001 | [Repo infrastructure](0001-repo-infrastructure.md) | done |
| 0002 | [Config and CLI](0002-config-and-cli.md) | done |
| 0003 | [Manifest](0003-manifest.md) | done |
| 0004 | [Consolidate](0004-consolidate.md) | approved |
| 0005 | [Code quality](0005-code-quality.md) | approved |
