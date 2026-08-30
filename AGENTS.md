# AGENTS.md

Working agreement for AI agents in this repository. Read this before changing anything.

## Project

memory-drawer consolidates scattered backups into one organized archive. Python 3.14, target machine is Windows. Work is organized by numbered specs in `specs/`; only the spec being worked on exists at any time.

## Principles (non-negotiable)

- Never delete user data. Duplicates and rejects go to quarantine; only the owner removes them.
- Never modify sources. Work happens on the consolidated copy in the master folder.
- Hashes are computed from the original bytes, before any write.
- Provenance (source path) is recorded for every file.

## Before writing code

- Read the current spec in `specs/` first. Nothing is implemented without an approved spec.
- Specs carry `Status`, `Version` and a `Change log`. Flow: `proposed` -> `approved` -> `in-progress` -> `done`.
- `[DECISION]` markers in a spec are open questions for the owner. Do not implement until the owner accepts.
- The owner reviews every spec in chat before accepting. Never skip that review.

## Spec rules

- One spec per unit of work, created when the unit starts. A spec that is no longer current must not exist, not even in git history.
- Specs never reference `PLAN.md` (private, gitignored) and never reference specs that do not exist yet.
- Every spec edit bumps `Version` and adds a `Change log` entry. Status lives in the spec file and in `specs/README.md`; keep both in sync.

## Code rules

- English only everywhere: identifiers, comments, docs, reports, folder names. No em-dashes in text.
- Code never references specs or decisions in docstrings or comments.
- Modern Python 3.14: `pathlib`, dataclasses with `slots`, `StrEnum`, PEP 604 unions, `Path.walk`.
- Robustness first: anticipate failures and edge cases, especially Windows (UTF-8 BOM, reserved file names, console encoding, long paths). Fail fast with clear messages, never guess, never lose data.
- When something repeats, extract a shared helper (the `fsutil.py` pattern) instead of duplicating.
- Refactors never change behavior: `tests/test_golden.py` pins the pipeline output byte for byte.

## Communication

- Chat with the owner in PT-BR; all repo content in English.
- Prose is brief and objective, no filler.

## Continuous improvement

- Always look for gains in performance, memory use and modern Python idioms, following the PEPs.
- Any improvement must keep the result identical: the golden test stays green.
- An improvement that changes behavior or leaves the approved spec becomes a new spec, never a silent change.

## Commits and branches

- Commit only on explicit owner order ("commit", "implement the spec"). Never push without an explicit "push".
- Commit messages: one line, no body, no em-dash.
- Work happens on feature branches (`feature/NNNN-name`) based on `develop`. The owner merges PRs on GitHub.
- `main` stays frozen until the owner says otherwise.

## Tooling

- `uv` for the environment, `just` for recipes. `just check` runs ruff, ruff format check, mypy and pytest; `just format` formats.
- Python 3.14 is pinned in `.python-version`.

## Closing a unit

After implementing, before reporting back:

1. Audit the implementation against the spec (every section, every acceptance criterion).
2. Run `just check`; the whole suite must stay green, golden test included.
3. Mark the spec `done` (Status, Version, Change log, `specs/README.md` index).
4. Present the review with the acceptance table, without being asked.
5. Propose the next unit, so the owner never has to ask what comes next.
6. After a push, offer the PR title and body.
