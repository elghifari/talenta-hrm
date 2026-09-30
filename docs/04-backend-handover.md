# Backend handover

Status: initial backend slice implemented, locally verified and independently reviewed. No blocking findings remain in this slice. Not a completed M1 milestone or a live-payroll release.
Verified locally: 2026-09-30. Planning documents 01–03 remain the behavioral baseline.

## Implemented

- Python 3.12.14, Django 5.2.17 LTS, DRF 3.16.1, PostgreSQL; locked uv environment.
- Custom personal-email user model, Django password authentication and sessions, CSRF-protected login/logout, identity endpoint. Login accepts Django's `username` form field containing the email; not JSON credentials.
- Explicit Django groups: HR, KEPALA_UNIT, FINANCE, TECHNICAL_ADMIN, INTERN. No implicit HR access for staff/superusers. Bootstrap is idempotent and does not assign users.
- Employee UUID identity and unique text employee code (leading zeros preserved). HR create/list/detail/PATCH; no destructive employee endpoint.
- Unit hierarchy and explicit account/unit grants. Managers can read employees with a current assignment in a granted unit; descendant units do not inherit grants. This is a least-privilege initial behavior, not a settled subtree-access policy. Old assignments do not confer current access.
- Effective-dated employee assignments and compensation component amounts. Intervals are start-inclusive/end-exclusive, null end means open-ended. PostgreSQL exclusion constraints reject overlaps; date checks reject empty/backwards periods. Compensation amounts are nonnegative decimals. These are storage contracts, not payroll proration or cycle-boundary approval rules.
- Separate HR-only compensation history read endpoint. Employee responses contain no compensation fields. Finance salary/export permissions remain unresolved and denied here; no finance approval workflow is implemented.
- Employee API create/update and actor/action/target audit records are saved in one database transaction. Audit records do not copy names or amounts. Concurrent duplicate employee-code writes return a field-level 400 after rollback; unrelated database errors are not disguised as input errors. PATCH saves only supplied fields so disjoint concurrent edits are preserved. No claim of immutable payroll snapshots or complete audit coverage for management-shell writes.
- Public readiness endpoint checks the database; unavailable database returns 503 without connection details.
- Separate development/staging/production settings modules. Deployment requires secret, PostgreSQL URL and explicit hosts; HTTPS defaults. CI configuration uses PostgreSQL and commit-pinned GitHub actions.

## API

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/health/` | 200 ready, 503 database unavailable |
| GET | `/api/auth/csrf/` | CSRF token and cookie |
| POST | `/api/auth/login/` | Form-encoded email in `username`, password, CSRF; generic 400 on invalid credentials |
| GET | `/api/auth/me/` | Current authenticated account id/email |
| POST | `/api/auth/logout/` | CSRF required; session cleared, 204 |
| GET, POST | `/api/employees/` | HR list/create; manager unit-scoped list only |
| GET, PATCH | `/api/employees/{uuid}/` | HR read/update; manager scoped read only |
| GET | `/api/employees/{uuid}/compensation/` | HR compensation history only |

Unauthenticated access to protected endpoints returns 403 with session authentication. Outside-unit detail reads return 404. Unknown and read-only employee input fields return 400 rather than being silently discarded. No payroll fields are writable through the employee API.

## Verification evidence

- `uv sync --frozen`: successful with the pinned Python interpreter.
- `uv run pytest -q`: 53 passed, including real PostgreSQL constraints, concurrent database writes and a real HTTP server round-trip with a cookie jar.
- TDD cycles observed missing scaffold, email user contract/creation, session endpoints and invalid-login response, manager scoping, assignment constraints, compensation history/constraints, employee audits/update, strict input validation, account bootstrap/validation, deployment settings, readiness and CI configuration fail before their implementations. Existing negative-access/CSRF behaviors also have regression tests; they were not artificially broken to manufacture RED results.
- Live HTTP: health 200; anonymous employee list 403; CSRF retrieval; email login 200; current account 200; employee creation 201; detail read 200; PATCH 200 with read-back; missing-CSRF logout 403; valid logout 204; post-logout identity 403. Synthetic fixtures are confined to pytest's test database.
- Development migrations applied successfully. `check`: no issues. `makemigrations --check --dry-run`: no changes.
- `ruff check .`: passed. `ruff format --check .`: passed.
- Review-driven RED/GREEN: simultaneous creates initially returned 201/500, code PATCH races 200/500, and disjoint PATCHes lost a persisted field. Corrected results are 201/400, 200/400 and both disjoint edits preserved. Five real PostgreSQL race/rollback tests now pass, including unrelated audit foreign-key errors and atomic rollback. Parent re-ran the full suite: 53 passed.
- Production/staging `check --deploy --fail-level WARNING` passes for explicit synthetic configuration with domain/HSTS opt-ins. This is configuration testing, not proof of a deployed secure service. Default HSTS domain opt-ins require confirmation and emit W005/W021 until settled.
- CI file exists and its check commands passed locally. Remote CI has not run; nothing has been pushed.
- Independent re-review: passed, no blocking security or logic findings for this slice. The reviewer inspected the fixes/tests; the parent independently executed the 53-test suite. Nonblocking follow-up: add unique-error classification tests for other tables/constraints when extending write paths.

## Current concurrency limits

Employee identity edits to the same field remain last-writer-wins; optimistic revision checks are not implemented here. A PATCH response's omitted fields can reflect its originally loaded snapshot; GET returns current persisted state. Refetch after editing before using the entire employee record. The duplicate-code handler matches the database's verified constraint name, so any future constraint rename must update that handler and its regression tests. These identity-write choices do not authorize last-writer-wins for future payroll revisions.

## Remaining M1 work

1. Controlled, audited account/role/unit administration and unit hierarchy validation. Decide whether subtree access is ever granted explicitly.
2. Coded positions, HR-confirmed grade, education/service dates, schedules, and richer employee validation. The current employee API has only code/name/id.
3. HR assignment and compensation write workflows, history/correction controls, effective payroll-period selection and concurrency protection. Current assignments/compensation are model foundations and read APIs, maintained only through trusted operations.
4. Employee import with explicit source identity mapping, duplicate review and synthetic workbook tests.
5. React/TypeScript HR workflows and an agreed design direction. No UI, logo, photos or public application portal created.
6. Production controls and operations: login rate limiting, recovery/MFA decisions, private media/storage, backups/restores, hosting/TLS/proxy, monitoring and retention approval. Django Admin maintenance tooling is not enabled yet.

Keep calculations, recommendations and deferred-module bridge decisions behind the existing O1–O9 gates. No attendance/payroll/approval/payslip/applicant implementation is implied by this slice.

## Local state

See README for exact commands. Isolated synthetic PostgreSQL 15 cluster: ignored `.local/postgres`, loopback port 55439, database/user `hrm_dev`, local trust authentication. Existing PostgreSQL on port 5432 was not modified. The development database contains schema and role groups only; tests use their own database. No real source workbook/payroll rows or prototype credentials were imported. No web server is kept running by this handover.

## Delivery gate

- Hard gate PASS for this backend slice: tests exercised the app and actual HTTP actions; no fabricated people/data, production claims, assets or UI were added. UI-specific mobile/theme/contrast/keyboard items do not apply to this slice.
- Purpose gate PASS: no visual techniques introduced; the backend changes correspond to the documented authentication, employee access and history boundaries.
- Liveliness/design gate NOT APPLICABLE: no UI was built. Set direction and antislop mode before frontend work.
- Craftsmanship PASS for the implemented slice: valid/error/denied access paths and database constraints exercised, no dead UI controls. Full M1 acceptance remains incomplete.
- Comment hygiene PASS: comments are migration provenance, targeted `noqa` annotations and single-line concurrency-test synchronization constraints; no banners, line-by-line narration, vague TODOs or padded explanatory blocks. Comment auditing did not alter runtime behavior.
