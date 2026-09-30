# Development guide

Internal employee administration, attendance, payroll and applicant registry for Talenta Center.

## Status
Initial Django backend slice implemented. M1 is not complete; there is no React UI or payroll engine yet. See the [backend handover](docs/04-backend-handover.md) for implemented endpoints, verification and remaining work.

## Private planning

Company-specific scope, payroll specifications and build plans are kept outside the public history. Local working copies are in the ignored `.private/planning/` folder. Do not publish that folder or local private archival branches. Push explicit public branches only, never `--all` or `--mirror`.

The [backend handover](docs/04-backend-handover.md) describes the implemented API and remaining work.

## Selected stack
Django + Django REST Framework, React/TypeScript, managed PostgreSQL, Django authentication, one repository and same-origin deployment.

## Immediate implementation milestone
Implementation was authorized in the build session. Continue M1 with controlled unit/account administration, richer employee fields and effective-dated assignment workflows, then the React HR interface. Payroll policy gates O1–O9 remain open as recorded in the planning documents.

## Data handling
Do not commit real employee/payroll data, source workbook exports, credentials, uploaded files or database backups. Use synthetic test fixtures. Approved historical payroll must remain immutable.

Dedicated BPJS/THR/PPh/koperasi modules are deferred. The proposed external-amount bridge still requires confirmation.

## Local backend

Python 3.12.14 and dependency versions are pinned in `.python-version` and `uv.lock`. Use `uv`; do not mix the machine's Python/pip installations.

```bash
uv sync --frozen
uv run python backend/manage.py migrate --noinput
uv run python backend/manage.py bootstrap_roles
uv run python backend/manage.py runserver 127.0.0.1:8085
```

PostgreSQL must be running before migrations, tests or API use. The development default is a separate synthetic-data-only instance on `127.0.0.1:55439`, database/user `hrm_dev`. The existing database service on port `5432` was not modified. To use another isolated development database, set `DATABASE_URL`; `uv run --env-file .env ...` loads an explicitly provided environment file. `.env` is not auto-loaded by Django.

The installed Windows PostgreSQL 15 binaries were used because Docker Desktop was not running. Commands below are for Git Bash. Initialize once, then use the start/stop commands as needed.

```bash
PG_BIN='C:/Program Files/PostgreSQL/15/bin'
mkdir -p .local
"$PG_BIN/initdb.exe" -D .local/postgres -U hrm_dev -A trust --encoding=UTF8 --no-locale
"$PG_BIN/pg_ctl.exe" -D .local/postgres -l .local/postgres.log -o '-h 127.0.0.1 -p 55439' -w start
"$PG_BIN/createdb.exe" -h 127.0.0.1 -p 55439 -U hrm_dev hrm_dev
```

Skip `initdb` and `createdb` if this cluster/database already exists. The cluster has already been initialized on this machine. Trust authentication lets local processes connect without a password: use only synthetic data, never expose it to a network or import real employee/payroll records. This is not the production database configuration.

```bash
PG_BIN='C:/Program Files/PostgreSQL/15/bin'
"$PG_BIN/pg_ctl.exe" -D .local/postgres -l .local/postgres.log -o '-h 127.0.0.1 -p 55439' -w start
"$PG_BIN/pg_ctl.exe" -D .local/postgres -m fast -w stop
```

The migration user must be able to enable `btree_gist`, or an authorized database administrator must enable it first. Tests create and destroy an isolated `test_` database; the test role needs `CREATEDB`. Never point tests at a production database.

## Checks

Follow the [development workflow](docs/05-development-workflow.md): separate RED test, GREEN implementation and optional REFACTOR commits for each behavior.

```bash
uv run pytest -q
uv run python backend/manage.py check
uv run python backend/manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
```

GitHub Actions configuration is in `.github/workflows/backend.yml`. Check the repository's Actions page for remote verification results.

## Accounts and deployment

`bootstrap_roles` creates role groups only. It grants no access and creates no users. `createsuperuser` creates a technical account, not an HR approver. Business groups and unit grants currently require explicit trusted maintenance through Django's management shell; there is no account-administration API or Django Admin route yet.

Deployment uses `config.settings.staging` or `config.settings.production` with explicit `DJANGO_SECRET_KEY`, PostgreSQL `DATABASE_URL` and `DJANGO_ALLOWED_HOSTS`. Provision separate databases and secrets for each environment. HTTPS cookies and SSL redirect are enabled. Database TLS, trusted reverse-proxy configuration, rate limiting, recovery/MFA, hosting and release operations still need implementation/validation before launch. HSTS subdomain/preload options are opt-in (`DJANGO_HSTS_INCLUDE_SUBDOMAINS=true`, `DJANGO_HSTS_PRELOAD=true`) and require domain-owner approval; without these opt-ins Django reports W005/W021 in `check --deploy`. No production-readiness claim is made.
