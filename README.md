# CraftCV Backend

CraftCV is a Django REST API for account management and CV creation. Users can maintain reusable career details, select a template, and assemble one or more CVs from their saved sections.

## Contents

- [Technology](#technology)
- [Architecture](#architecture)
- [Local setup](#local-setup)
- [Run with Docker Compose](#run-with-docker-compose)
- [API overview](#api-overview)
- [Typical usage](#typical-usage)
- [API conventions](#api-conventions)
- [Quality checks](#quality-checks)
- [Project layout](#project-layout)

## Technology

- Python 3.12
- Django 6.1 and Django REST Framework
- PostgreSQL for the Docker development stack; SQLite can be used for a lightweight local setup
- Simple JWT for access tokens and refresh-token cookies
- drf-spectacular for OpenAPI, Swagger UI, and ReDoc
- Redis in Docker Compose for Django's cache and request throttling
- Ruff for linting and formatting

## Architecture

The Django project is configured in `craftcv/`. The API is split into two domain apps:

- **`apps.users`** owns the custom email-based user model, registration, login, email verification, password reset, and related services.
- **`apps.cv_builder`** owns templates, personal details, CVs, and reusable CV sections. CV section records belong to a user; a CV links to selected records through many-to-many relationships.
- **`core`** contains shared API behavior, including the DRF exception handler.

The project uses UUID identifiers for users, CVs, templates, and CV sections. CV and section endpoints require authentication and scope personal records to the current user. Templates are read-only through the API and are populated by data migrations.

## Local setup

### Requirements

- Python 3.12 and pip
- Git
- PostgreSQL 17 if using PostgreSQL directly, or Docker Desktop / Docker Engine for the Compose setup

### Create an environment

From the repository root, create and activate a virtual environment.

**macOS / Linux**

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install project and development dependencies, then create your private environment file:

```sh
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

macOS / Linux:

```sh
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The `.env` file is ignored by Git. Use a private `SECRET_KEY` and do not commit credentials or production secrets.

### Configure a local database

The checked-in `.env.example` is set up for PostgreSQL. For a local PostgreSQL server, make sure its database and user match `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `.env`; set `DB_HOST` and `DB_PORT` to the values reachable from your host.

To use SQLite instead, set these values in `.env`:

```dotenv
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

When using SQLite, the other `DB_*` connection fields are not used. SQLite is convenient for development and tests; use PostgreSQL when you need to match the Compose database behavior.

### Configure email

Email verification and password-reset messages use the configured Resend SMTP backend. Set these values in `.env` for real delivery:

```dotenv
DEFAULT_FROM_EMAIL=CraftCV <verified-sender@example.com>
RESEND_API_KEY=your-resend-api-key
```

Without valid mail credentials, the API can still run, but verification and reset emails will not reach users. Email send failures are logged by the application.

### Migrate and start the API

```sh
python manage.py migrate
python manage.py runserver
```

The local API is available at <http://127.0.0.1:8000>. `DEBUG=True` in the example environment enables Django's debug toolbar during local development. Do not use debug mode or example credentials in a public deployment.

## Run with Docker Compose

Compose starts the Django application, PostgreSQL, and Redis. Create `.env` as described above, then run:

```sh
docker compose up --build
```

In a second terminal, apply migrations:

```sh
docker compose exec web python manage.py migrate
```

The API is available at <http://127.0.0.1:8000>. Compose publishes PostgreSQL on host port `5142` and connects the web container to the database service internally. The database and Redis data are held in named volumes.

Useful commands:

```sh
docker compose logs -f web       # follow application logs
docker compose exec web python manage.py showmigrations
docker compose down              # stop containers and keep data volumes
docker compose down -v           # stop containers and delete database/cache data
```

The Compose web service runs Gunicorn. For live code reloading during development, stop Compose and run Django on the host with `python manage.py runserver` against a reachable database, or adjust the Compose command for your local workflow.

## API overview

All endpoints use the `/api/` prefix and trailing slashes. JSON request and response fields use **camelCase** (for example, `professionalTitle`), while the Python model and serializer fields use snake_case. Authenticated requests use this header:

```http
Authorization: JWT <access-token>
```

### Documentation and health of the API surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/docs/schema/` | Download the OpenAPI schema |
| `GET` | `/api/docs/swagger/` | Swagger UI |
| `GET` | `/api/docs/redoc/` | ReDoc UI |
| `GET` | `/admin/` | Django admin site |

### Authentication

All authentication routes are under `/api/auth/`.

| Method | Path | Auth required | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Create an account and send an email verification code |
| `POST` | `/api/auth/verify-email/` | No | Verify the email with the six-digit code; returns an access token and sets the refresh cookie |
| `POST` | `/api/auth/resend-verification/` | No | Request a replacement verification code |
| `POST` | `/api/auth/login/` | No | Log in with email and password; returns an access token and sets the refresh cookie |
| `POST` | `/api/auth/refresh/` | Refresh cookie | Return a new access token using the `refreshToken` cookie |
| `POST` | `/api/auth/logout/` | Yes | Blacklist the refresh token, if supplied, and clear its cookie |
| `GET` | `/api/auth/me/` | Yes | Return the current user's profile |
| `POST` | `/api/auth/forgot-password/` | No | Request a password-reset code |
| `POST` | `/api/auth/verify-code/` | No | Check a password-reset code without consuming it |
| `POST` | `/api/auth/reset-password/` | No | Set a new password using a valid reset code |

Registration request:

```json
{
  "email": "person@example.com",
  "password": "StrongPassword123!",
  "agreeToTerms": true
}
```

Login request:

```json
{
  "email": "person@example.com",
  "password": "StrongPassword123!",
  "rememberMe": false
}
```

Registration returns a message and email address; it does **not** sign the user in. Verify the email, then use the returned access token in the `Authorization` header. The refresh token is stored in an HttpOnly cookie by the API. Browser clients must send requests with credentials enabled when they need that cookie, and the frontend origin must be allowed by the CORS settings.

Login is blocked until the account's email is verified. Password reset responses do not reveal whether an email address has an account. Authentication endpoints have per-action throttling; clients should respect HTTP `429` responses and the `Retry-After` header.

### Templates

Template endpoints require authentication and return the available templates.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/templates/` | List templates |
| `GET` | `/api/templates/{template_id}/` | Retrieve a template |

Template IDs are UUIDs. The initial migrations seed the built-in templates; query this endpoint and use a returned `templateId` when creating a CV.

### CVs

All CV endpoints require authentication. A user's CV list and detail endpoints only expose that user's CVs.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/cvs/` | List the current user's CVs |
| `POST` | `/api/cvs/` | Create a CV |
| `GET` | `/api/cvs/{cv_id}/` | Retrieve a CV |
| `PATCH` | `/api/cvs/{cv_id}/` | Update CV fields and section selections |
| `DELETE` | `/api/cvs/{cv_id}/` | Delete a CV |
| `POST` | `/api/cvs/{cv_id}/duplicate/` | Duplicate a CV and copy its sections |

Example create request (IDs are UUIDs returned by the relevant endpoints):

```json
{
  "title": "Backend Engineer",
  "professionalTitle": "Senior Backend Engineer",
  "professionalSummary": "Backend developer with experience building APIs.",
  "template": "<template-uuid>",
  "educations": ["<education-uuid>"],
  "experiences": ["<experience-uuid>"],
  "skills": ["<skill-uuid>"]
}
```

Related section IDs must belong to the authenticated user. The `personalDetail` object in CV responses is read-only and reflects the user's current personal details. CV edits update `lastSavedAt`.

### Personal details and reusable sections

These endpoints require authentication. Collection `GET` returns the current user's records; collection `POST` creates one. Detail endpoints support retrieval, partial/full update, and deletion for the current user's record only.

| Resource | Collection | Detail |
| --- | --- | --- |
| Personal details | — | `/api/cvs/personal-details/` |
| Education | `/api/cvs/educations/` | `/api/cvs/educations/{education_id}/` |
| Experience | `/api/cvs/experiences/` | `/api/cvs/experiences/{experience_id}/` |
| Skills | `/api/cvs/skills/` | `/api/cvs/skills/{skill_id}/` |
| Certifications | `/api/cvs/certifications/` | `/api/cvs/certifications/{certification_id}/` |
| Languages | `/api/cvs/languages/` | `/api/cvs/languages/{language_id}/` |
| Awards | `/api/cvs/awards/` | `/api/cvs/awards/{award_id}/` |
| Additional information | `/api/cvs/additional-information/` | `/api/cvs/additional-information/{additional_info_id}/` |

Personal details use `PUT` to create the record when one does not exist or replace it when it does; use `PATCH` for a partial update. Section details support `GET`, `PATCH`, `PUT`, and `DELETE`. `displayOrder` controls a section's ordering in the CV.

## Typical usage

1. Register with an email, password, and `agreeToTerms: true`.
2. Submit the emailed code to `/api/auth/verify-email/`.
3. Keep the returned access token in the client and send it as `Authorization: JWT …`. Let the browser retain the HttpOnly refresh cookie; call `/api/auth/refresh/` when the access token expires.
4. Save personal details and create reusable sections such as education, experience, and skills.
5. Fetch templates from `/api/templates/` and choose a template UUID.
6. Create a CV using the template UUID and IDs of the sections to include. Use `PATCH` to update the CV later.
7. Duplicate a CV when you want an independent copy. Its section records are copied too, so later edits to the copy do not change the original.

### Idempotent section creation

Section collection `POST` endpoints accept an optional `Idempotency-Key` header. This is useful when retrying a request after a network timeout:

```http
Idempotency-Key: 6d862e4d-4f90-45ba-a153-43fa45a51c65
```

For the same authenticated user, endpoint, key, and request payload, the API replays the original response and adds `Idempotent-Replayed: true`. Reusing the key with a different payload returns `409 Conflict`. Keys expire after 24 hours. Use a new unique key for every distinct create operation. Requests without this header behave as ordinary creates.

Expired records for a key are cleaned up during a request using that key. To remove other expired records periodically, run:

```sh
python manage.py purge_idempotency_records
```

## API conventions

- Send and accept JSON for ordinary API requests. The API's JSON parser and renderer convert field names between camelCase on the wire and snake_case in Python.
- Use the UUID identifiers returned by the API; do not assume database IDs are sequential integers.
- `401` means authentication is missing or invalid; `403` means the request is authenticated but not allowed; `404` is also used when a requested CV or section does not belong to the current user.
- Validation errors return `400`. Authentication throttling returns `429` with retry information. Idempotency payload conflicts return `409`.
- Successful deletes use HTTP `204 No Content`.
- CORS defaults allow the configured local frontend origins in `craftcv/settings.py`. Update `CORS_ALLOWED_ORIGINS` for the frontend deployment; do not enable all origins for a credentialed production client.

## Quality checks

The shared check script is `scripts/check.sh`:

```sh
sh scripts/check.sh lint            # Ruff lint and format checks
sh scripts/check.sh tests-required  # staged application code must include a test
sh scripts/check.sh build           # Django checks and missing-migration check
sh scripts/check.sh test            # Django test suite
sh scripts/check.sh all             # lint, build, and tests
```

On Windows, run these commands in Git Bash or another shell that provides `sh`. To run tests directly:

```sh
python manage.py test
```

Install the repository's Git hooks once per clone if you want the local branch, commit, lint, and test-presence checks:

```sh
sh scripts/setup-hooks.sh
```

PowerShell alternative:

```powershell
.\scripts\setup-hooks.ps1
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit messages, pull request expectations, and hook behavior.

## Project layout

```text
apps/
  users/                 Accounts, authentication, verification, email services
  cv_builder/            Templates, CVs, reusable sections, and CV endpoints
core/                    Shared API exception handling
craftcv/                 Django settings, root URLs, ASGI and WSGI entry points
scripts/                 Local checks, hook setup, and convention validation
tests/                   Repository tooling tests
.githooks/               Optional local Git hooks
Dockerfile               Gunicorn application image
compose.yaml             Local application, PostgreSQL, and Redis services
buildspec.yml            Build/check pipeline definition
manage.py                Django management entry point
requirements.txt         Runtime dependencies
requirements-dev.txt     Ruff and development tooling
```
