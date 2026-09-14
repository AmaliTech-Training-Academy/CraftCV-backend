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

- Python (version not pinned yet — see
  [CONTRIBUTING.md](CONTRIBUTING.md#adding-the-backend-stack))
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
pip install -r requirements.txt
cp .env.example .env
```

Set at least `SECRET_KEY` and `DB_ENGINE` in `.env`; the defaults in
`.env.example` use SQLite. `.env` is git-ignored and must never be committed.

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
│   ├── asgi.py
│   └── wsgi.py
├── scripts/              # Git hook installers and convention checks
├── .githooks/            # commit-msg and pre-commit hooks
├── manage.py
└── requirements.txt
```

New apps live under `apps/` and are registered in `INSTALLED_APPS` with their
dotted path (for example `apps.users`).

## Tests

```sh
python manage.py test
```

`settings.py` detects test runs and skips loading the debug toolbar. There are
no tests yet beyond the generated placeholders.

## Known gaps

These are tracked as follow-up work and are intentionally listed here so they
are not mistaken for finished configuration:

- `DEBUG` is hard-coded to `True` and `ALLOWED_HOSTS` is empty in
  `craftcv/settings.py`; neither reads from `.env` yet.
- `DATABASES['default']['NAME']` is hard-coded to `db.sqlite3`, so the
  `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` variables in
  `.env.example` are not used.
- No formatter, linter, type checker, dependency lock file, or CI build/test
  job yet — CI currently validates repository conventions only.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit message
format, pull request expectations, and local quality checks.
