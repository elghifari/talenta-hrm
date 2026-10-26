# Talenta HRM

Employee administration for Talenta Center, built with Django and PostgreSQL.

Talenta HRM is in active development, starting with employee records, unit-based access and compensation history. Attendance, payroll and applicant workflows are planned.

## What works today

- HR can sign in through the React interface and create, view and update employee records.
- Unit managers can read employees in units they have been granted access to.
- Personnel includes a dashboard, employee records and Cabang/Divisi management.
- HR can read compensation history separately from employee identity records.
- Employee and organization changes are audited.

## Local development

Run commands from the repository root. Use synthetic data only. Keep employee records, payroll files, credentials and database backups out of Git.

You'll need uv, Python 3.12.14 (`.python-version`), Node 26.7.0 (`.node-version`) and PostgreSQL 15. Use uv rather than mixing the machine's Python/pip installations. Dependencies are locked in `uv.lock` and `frontend/package-lock.json`.

The database commands below are for Windows Git Bash. Adjust `PG_BIN` for your PostgreSQL installation. Use `npm.cmd` in place of `npm` if its Windows wrapper reports a TTY error.

### Database setup

Development settings default to:

```text
postgresql://hrm_dev@127.0.0.1:55439/hrm_dev
```

This uses a separate local cluster under ignored `.local/postgres/`, on port 55439 rather than an existing service on port 5432. PostgreSQL must be running before migrations, tests or API use.

Initialize a new cluster once:

```bash
PG_BIN='C:/Program Files/PostgreSQL/15/bin'
mkdir -p .local
"$PG_BIN/initdb.exe" -D .local/postgres -U hrm_dev -A trust --encoding=UTF8 --no-locale
```

Skip initialization if `.local/postgres/PG_VERSION` already exists. Do not reinitialize an existing cluster or point these commands at another application's database directory.

Start the cluster:

```bash
PG_BIN='C:/Program Files/PostgreSQL/15/bin'
"$PG_BIN/pg_ctl.exe" -D .local/postgres -l .local/postgres.log -o '-h 127.0.0.1 -p 55439' -w start
```

Create the development database once, after the cluster starts:

```bash
"$PG_BIN/createdb.exe" -h 127.0.0.1 -p 55439 -U hrm_dev hrm_dev
```

Skip `createdb` if `hrm_dev` already exists. In later sessions, start the existing cluster without repeating initialization or database creation.

Trust authentication allows local processes to connect without a password. Keep this cluster bound to loopback and use synthetic data only. Never expose it to a network or import real employee/payroll records. This is not a production database configuration.

To stop the local cluster:

```bash
PG_BIN='C:/Program Files/PostgreSQL/15/bin'
"$PG_BIN/pg_ctl.exe" -D .local/postgres -m fast -w stop
```

To use another isolated development database, set `DATABASE_URL`. You can copy `.env.example` to ignored `.env` and edit it, but Django does not load `.env` automatically. Pass it explicitly to uv, for example:

```bash
uv run --env-file .env python backend/manage.py check
```

Use the same environment for migrations, the server and tests. The migration role must be able to enable `btree_gist`, or a database administrator must enable it first. Tests create and destroy a separate `test_` database, so the test role needs `CREATEDB`. Never point tests at production.

### Backend

With PostgreSQL running:

```bash
uv sync --frozen
uv run python backend/manage.py migrate --noinput
uv run python backend/manage.py bootstrap_roles
uv run python backend/manage.py runserver 127.0.0.1:8085
```

`bootstrap_roles` creates groups only. It does not create users or grant access. A technical superuser is not automatically an HR approver, and there is no account-administration interface yet.

For a synthetic local HR login, open the management shell:

```bash
uv run python backend/manage.py shell
```

Create the account once, entering its password through the terminal prompt:

```python
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

user = get_user_model().objects.create_user(email="synthetic-hr@example.test")
user.set_password(getpass("Synthetic local password: "))
user.save(update_fields=["password"])
user.groups.add(Group.objects.get(name="HR"))
```

Use an isolated synthetic database. Unit-manager accounts additionally need explicit unit grants through trusted maintenance. Setup and browser tests do not create permanent development login accounts.

### Frontend

Keep Django running on port 8085. In a second shell:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Vite forwards relative `/api/` requests to Django on `127.0.0.1:8085`, so browser authentication stays same-origin. Development settings trust loopback Vite origins on port 5173. Do not add wildcard CORS/CSRF trust. `HRM_API_TARGET` overrides the proxy backend target for isolated tests.

For a local built-app check:

```bash
npm --prefix frontend run build
```

With Django running, open `http://127.0.0.1:8085`. Development settings serve the Vite build and support employee deep-link reloads. A missing/invalid build returns 503; unknown API/asset paths remain errors. Staging and production do not enable this local asset handler.

## Checks

Keep PostgreSQL running. Ordinary backend checks do not require Chromium:

```bash
uv run pytest -q
uv run python backend/manage.py check
uv run python backend/manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
```

Frontend checks:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Build first, then run real-browser acceptance:

```bash
uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser pytest --run-browser tests/browser -q
```

The browser suite uses real Chromium, Django's live server and pytest's disposable PostgreSQL database. It creates synthetic accounts and records only there, then tears them down. Ordinary `uv run pytest -q` excludes browser tests. CI provisions Chromium's Linux dependencies explicitly in `.github/workflows/backend.yml`.

Keep screenshots and test artifacts synthetic. Local screenshots are ignored under `.local/ui-review/`; browser authentication state is not uploaded.

Use separate RED test, GREEN implementation and optional REFACTOR commits for behavior changes. Do not commit or push unrelated local files.

## Deployment and remaining work

Frontend and `/api/` are intended to share one origin. Production frontend serving, hosting, database TLS, reverse-proxy configuration, rate limiting, account recovery/MFA and release operations still need implementation or validation. This guide does not establish production readiness.

Staging and production use `config.settings.staging` or `config.settings.production`, with explicit `DJANGO_SECRET_KEY`, PostgreSQL `DATABASE_URL` and `DJANGO_ALLOWED_HOSTS`. Use separate databases and secrets per environment. HTTPS cookies and SSL redirects are enabled. HSTS subdomain/preload options require domain-owner approval before enabling `DJANGO_HSTS_INCLUDE_SUBDOMAINS=true` or `DJANGO_HSTS_PRELOAD=true`.

Next: controlled, audited account/unit administration, richer employee records, then effective-dated assignment and compensation writes. Attendance and payroll remain unimplemented. Employee edits currently use same-field last-writer-wins; that does not establish a policy for future payroll revisions.
