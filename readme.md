# Talenta HRM

Internal HR administration for Talenta Center, built with Django/DRF, React/TypeScript and PostgreSQL.

## Current functionality

- Employee records, search/filter/grouping and HR create/edit.
- Reviewed 11-column CSV import, including Cabang/Divisi placement and employment classification, explicit confirmation and auditable changes.
- Personnel overview, upcoming contract expiries, employment status and editable PKWT type.
- Cabang-owned Divisi, with independent Kinerja/Pelimpahan settings.
- Scoped, read-only employee access for Kepala Divisi through existing grants.
- Activity log available only to active accounts with both HR and HR Manager roles.

Attendance, payroll calculations, PKWT generation and production rollout are not implemented. Compensation history is an HR-only API; there is no salary-editing screen.

## Quick start

Use uv, Python 3.12.14, Node 26.7.0 and PostgreSQL 15. Versions/dependencies are pinned in `.python-version`, `.node-version`, `uv.lock` and `frontend/package-lock.json`.

Use a dedicated development database with permission to enable `btree_gist`; the test user needs `CREATEDB`. Set `DATABASE_URL` when using a different target. Development defaults to a separate loopback-only PostgreSQL instance at `127.0.0.1:55439`, database/user `hrm_dev`. Never initialize over an existing cluster, use production for tests or import real personnel data into the synthetic local environment.

```bash
uv sync --frozen
uv run python backend/manage.py migrate --noinput
uv run python backend/manage.py bootstrap_roles
uv run python backend/manage.py runserver 127.0.0.1:8085
```

In another terminal:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. On Windows Git Bash, use `npm.cmd` if the npm wrapper reports a TTY error. The Vite proxy keeps frontend and API authentication on the same origin. `bootstrap_roles` creates groups, not users; business-role accounts and grants require explicit trusted maintenance. Technical superusers do not receive business access automatically.

For the built frontend, run `npm --prefix frontend run build`, then open Django at `http://127.0.0.1:8085`. Source changes require another build in this mode.

## Checks and safety

```bash
uv run pytest -q
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Real-browser acceptance additionally requires the browser dependency group and Chromium:

```bash
uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser pytest --run-browser tests/browser -q
```

Tests use a disposable PostgreSQL database. Keep real employee/payroll files, credentials, backups and browser authentication state out of Git. Production serving, security/operations and live-payroll acceptance remain separate work. Do not publish private planning or push archival branches.

## Local maintainer documentation

Start the next local session with `docs/08-progress-report.md` for the current checkpoint, demo-file instructions and pending source access. When present, `PRODUCT.md` defines scope, `DESIGN.md` defines interface/copy conventions, `DEVELOPMENT.md` owns detailed setup/workflow, and `docs/08-progress-report.md` records the current checkpoint. These are local/ignored maintainer files, not files promised in a clean clone. Completed plans and handovers live under `docs/archive/`; they are historical evidence, not current instructions.
