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

- Use a Conventional Commit title; squash-merging will make it the final commit.
- Explain what changed, why it changed, and how it was tested.
- Link the relevant issue and call out migrations or breaking changes.
- Keep pull requests focused and request review only after checks pass.
- Prefer squash merge into `main`; never force-push `main`.

## Local quality checks

Run `sh scripts/setup-hooks.sh` or `.\scripts\setup-hooks.ps1` once per clone.
Three hooks then run automatically:

| Hook | Checks |
| --- | --- |
| `pre-commit` | Blocks commits on `main` and `develop`, validates the current branch name, and runs Git's whitespace/error checks on staged changes |
| `commit-msg` | Validates the commit subject |
| `pre-push` | Re-validates the branch name and every commit subject being pushed |

`pre-push` is the backstop: a branch missing its `crf-<number>` ticket
reference, or a commit subject that skipped `commit-msg` via `--no-verify`,
fails there before it reaches the remote. Pushes of `main` and `develop`, and
branch deletions, are not blocked. Every rule lives in
`scripts/validate-conventions.sh`, which prints correct and incorrect examples
on failure; change the `ticket_key` variable there if the project key changes.

Hooks improve local feedback but can be bypassed. The GitHub workflow repeats
the convention checks for pull requests. Repository administrators should also
protect `main` by requiring pull requests, approvals, and the
`repository-standards` status check, and by blocking force pushes and deletion.

## Adding the backend stack

When the technology is chosen, the first stack setup pull request should add:

1. The ecosystem's formatter and linter with committed configuration.
2. A test command and, where supported, a static type-check command.
3. Locked dependency versions and a documented supported runtime version.
4. CI steps for formatting, linting, tests, and type checking.
5. Editor integration that does not conflict with `.editorconfig`.

Prefer one canonical command (for example, `make check` or a package-manager
script named `check`) that runs every required quality gate locally and in CI.
