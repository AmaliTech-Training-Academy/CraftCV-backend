# Contributing

These rules apply regardless of which language or framework is selected for the
backend.

## Branches

Create work from an up-to-date `main` branch. Do not commit directly to `main`
or `develop`. Every branch must reference its ticket, using this format:

```text
<type>/crf-<ticket-number>-<short-kebab-case-description>
```

Allowed types:

| Type | Use |
| --- | --- |
| `feat` | New user-facing capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Internal change with no behavior change |
| `test` | Test-only change |
| `chore` | Maintenance |
| `build` | Build or dependency change |
| `ci` | CI/CD change |
| `perf` | Performance improvement |
| `hotfix` | Urgent production fix |
| `release` | Release preparation |

Examples: `feat/crf-3-resume-export`, `fix/crf-42-token-expiry`,
`chore/crf-7-bump-django`.

Use lowercase letters and numbers, separated by hyphens. The ticket key `crf`
and its number come first, followed by a short description — a bare
`feat/crf-12` is rejected. Keep a branch focused on one concern and delete it
after merge.

The branch name is checked when you commit and again when you push; a push from
a branch without a ticket reference fails with an example-driven error.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) with an
imperative, concise subject:

```text
<type>(optional-scope): <description>
```

Examples:

```text
feat(auth): add refresh token rotation
fix: reject expired reset links
docs: document local setup
```

Allowed commit types are `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, and `revert`. Use `fix` for hotfix commits and
`chore` for release preparation. Add `!` before the colon for a breaking change,
and explain it in the commit body. Commit subjects must be no more than 72
characters. Keep commits small, buildable, and free of unrelated formatting.

## Pull requests

- Use a Conventional Commit title; squash-merging will make it the final commit
  subject, and nothing in CI checks it for you. GitHub titles a pull request
  from the branch name by default, so this almost always needs editing.
- Explain what changed, why it changed, and how it was tested.
- Link the relevant issue and call out migrations or breaking changes.
- Keep pull requests focused and request review only after checks pass.
- Prefer squash merge into `main`; never force-push `main`.

## Local quality checks

Run `sh scripts/setup-hooks.sh` or `.\scripts\setup-hooks.ps1` once per clone.
Three hooks then run automatically:

| Hook | Checks |
| --- | --- |
| `pre-commit` | Blocks commits on `main` and `develop`, validates the current branch name, runs Git's whitespace/error checks, **lints the staged Python files**, and **requires a test alongside staged application code** |
| `commit-msg` | Validates the commit subject |
| `pre-push` | Re-validates the branch name and every commit subject being pushed, then runs the **build and the unit tests** |

Lint runs on commit because it is fast. The build and the test suite run once
per push instead, through the same entry point CI uses:

```sh
sh scripts/check.sh lint            # ruff lint + format check
sh scripts/check.sh tests-required  # staged code must ship with a test
sh scripts/check.sh build           # django system checks + missing migrations
sh scripts/check.sh test            # django unit tests
sh scripts/check.sh all
```

Install `requirements-dev.txt` or the hooks will stop with instructions. Lint
failures are mostly fixable with `python -m ruff check --fix .` and
`python -m ruff format .`. `SKIP_PUSH_CHECKS=1 git push` skips the build and
tests for an emergency push; CI still runs them.

`pre-push` is the backstop: a branch missing its `crf-<number>` ticket
reference, or a commit subject that skipped `commit-msg` via `--no-verify`,
fails there before it reaches the remote. Pushes of `main` and `develop`, and
branch deletions, are not blocked. Every rule lives in
`scripts/validate-conventions.sh`, which prints correct and incorrect examples
on failure; change the `ticket_key` variable there if the project key changes.

Hooks improve local feedback but can be bypassed. The GitHub workflows repeat
every check: `repository-standards` for the conventions and `CI` for lint,
build, and tests. Repository administrators should also protect the default
branch by requiring pull requests, approvals, and the `repository-standards`,
`lint`, and `build-and-test` status checks, and by blocking force pushes and
deletion.

## Tests come with the change

A commit that stages application code without staging a test is rejected. Write
the test in `apps/<app>/tests.py`, `apps/<app>/tests/test_*.py`, or `tests/` for
repository-level rules, and stage it in the same commit.

Exempt, because there is no behaviour to assert: migrations, `__init__.py`,
`apps.py`, `asgi.py`, `wsgi.py`, `manage.py`, `craftcv/settings.py`, and every
non-Python file.

The gate looks at file names, not at coverage, so it cannot tell a real test
from an empty one. It is a reminder, not a substitute for review: a reviewer
should still ask whether the test asserts the behaviour that changed. When a
change genuinely has nothing to assert, make that a deliberate, visible choice:

```sh
SKIP_TEST_CHECK=1 git commit
```

## The stack

Python 3.12 with Django 6.1 and Django REST Framework. Tooling that is in
place:

- **ruff** for linting and formatting, configured in `pyproject.toml`.
- **`scripts/check.sh`** as the single entry point for every gate, used by the
  hooks and by CI.
- Pinned direct dependencies in `requirements.txt` and `requirements-dev.txt`.
- `.editorconfig` covers Python indentation and line length so editors agree
  with ruff.

Still open, for whoever picks them up:

1. A dependency lock file.
2. A static type checker, wired into `scripts/check.sh` and CI.

Anything added to the quality gates belongs in `scripts/check.sh` so that the
hooks and CI stay in step.
