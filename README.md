# CraftCV Backend

Backend for CraftCV, a web application that helps individuals build a seamless CV.

The stack is **Python / Django 6.1** with **Django REST Framework**, OpenAPI
schema generation via **drf-spectacular**, and **django-debug-toolbar** for
local development.

> **Status:** project scaffold only. `apps/users` and `apps/cv_builder` are
> registered and wired into settings, but contain no models, serializers,
> views, or routes yet. The only routes that exist today are Django admin and
> the API documentation endpoints listed below.

## Requirements

- Python 3.12 (the version CI runs and the linter targets)
- pip and `venv`

## Getting started

```sh
git clone <repository-url>
cd craftcv_backend
```

Enable the version-controlled Git hooks in `.githooks/` (once per clone). They
enforce the branch and commit conventions, including the `crf-<ticket-number>`
reference every branch name must carry — for example
`feat/crf-3-cv-template-export`:

```sh
sh scripts/setup-hooks.sh
```

```powershell
.\scripts\setup-hooks.ps1
```

Create and activate a virtual environment:

```sh
python -m venv venv
source venv/bin/activate
```

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies and create your local environment file:

```sh
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

`requirements-dev.txt` holds the tooling the Git hooks need, so install it even
if you only plan to run the server. Settings are read from `.env` through
`python-dotenv`; the defaults in `.env.example` use SQLite. Set `SECRET_KEY`
for anything beyond a throwaway local database. `.env` is git-ignored and must
never be committed.

Apply migrations and start the development server:

```sh
python manage.py migrate
python manage.py runserver
```

## Available endpoints

| Path | Description |
| --- | --- |
| `/admin/` | Django admin |
| `/api/schema/` | OpenAPI schema (download) |
| `/api/swagger/` | Swagger UI |
| `/api/redoc/` | ReDoc UI |

The debug toolbar routes are also mounted while `DEBUG` is on.

## Project structure

```text
craftcv_backend/
├── apps/                 # Django apps
│   ├── cv_builder/       # CV creation domain (scaffold)
│   └── users/            # Accounts and authentication (scaffold)
├── craftcv/              # Project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── tests.py          # Smoke tests for the project wiring
│   ├── asgi.py
│   └── wsgi.py
├── scripts/              # check.sh, hook installers, convention checks
├── tests/                # Repository-level tests (the convention rules)
├── .githooks/            # pre-commit, commit-msg, pre-push
├── .github/workflows/    # CI and repository-standards
├── manage.py
├── pyproject.toml        # ruff configuration
├── requirements.txt
└── requirements-dev.txt  # Tooling the hooks need
```

New apps live under `apps/` and are registered in `INSTALLED_APPS` with their
dotted path (for example `apps.users`).

## Quality checks

`scripts/check.sh` is the one command that runs every gate. The Git hooks and
GitHub Actions both call it, so local and CI results cannot drift.

```sh
sh scripts/check.sh lint     # ruff lint + format check
sh scripts/check.sh build    # django system checks + missing migrations
sh scripts/check.sh test     # django unit tests
sh scripts/check.sh all      # all of the above
```

It finds `venv/` (or `.venv/`) on its own; set `PYTHON=/path/to/python` to
override.

When to expect each one:

| Moment | What runs |
| --- | --- |
| `git commit` | Branch and subject conventions, whitespace, and **lint on staged Python files** |
| `git push` | The same conventions, then **build and unit tests** |
| Pull request / push to `main`, `develop` | Lint, build, and tests again in GitHub Actions |

Lint runs on commit because it is fast; the slower build and test run once per
push. Fix lint failures with `python -m ruff check --fix .` and
`python -m ruff format .`. For an emergency push, `SKIP_PUSH_CHECKS=1 git push`
skips the build and tests — CI still runs them.

Linter and formatter rules live in `pyproject.toml` (ruff, line length 100).

## Tests

```sh
python manage.py test
```

`craftcv/tests.py` holds smoke tests for the URL wiring and
`tests/test_conventions.py` covers `scripts/validate-conventions.sh`, the rules
the Git hooks enforce. Feature tests belong in the app that owns the behaviour.
`settings.py` detects test runs and skips loading the debug toolbar.

The convention tests shell out to the script once per case, which is slow on
Windows (roughly 20 seconds) and quick on Linux. Run a subset with
`python manage.py test tests` or `python manage.py test craftcv`.

## Known gaps

These are tracked as follow-up work and are intentionally listed here so they
are not mistaken for finished configuration:

- No dependency lock file: `requirements.txt` pins direct dependencies only.
- No static type checking.
- No production settings module; `DEBUG` defaults to off and is turned on
  through `.env` for local work.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit message
format, pull request expectations, and local quality checks.
