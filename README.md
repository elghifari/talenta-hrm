# Talenta HRM

Employee administration for Talenta Center, built with Django and PostgreSQL.

Talenta HRM is in active development, starting with employee records, unit-based access and compensation history. Attendance, payroll and applicant workflows are planned.

## What works today

- HR can create, view and update employee records.
- Unit managers can read employees in units they have been granted access to.
- HR can read compensation history separately from employee identity records.
- Employee changes produce audit records. PostgreSQL constraints protect effective-dated assignments and compensation periods.

## Run locally

You'll need uv, Python 3.12 and PostgreSQL 15. Configure an isolated development database first; the [development guide](DEVELOPMENT.md) covers database setup, environment variables and account access.

With PostgreSQL configured and running:

```bash
uv sync --frozen
uv run python backend/manage.py migrate --noinput
uv run python backend/manage.py bootstrap_roles
uv run python backend/manage.py runserver 127.0.0.1:8085
```

This starts the API. `bootstrap_roles` creates role groups, not users or access grants.

Use synthetic data for development and tests. Keep employee records, payroll files, credentials and database backups out of the repository.

## Next work

Next up: account and unit administration, richer employee records, assignment and compensation editing, and the React/TypeScript interface.

## Documentation

- [Development guide](DEVELOPMENT.md): setup, checks and deployment notes.
- [Backend handover](docs/04-backend-handover.md): API routes, verification and known limits.
- [Development workflow](docs/05-development-workflow.md): separate red, green and optional refactor commits.

Company-specific planning and payroll specifications remain private.
