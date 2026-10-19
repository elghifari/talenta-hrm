# Employee Administration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved A-shell employee-administration slice with real Django sessions, scoped reads, HR writes and reproducible synthetic acceptance.

**Architecture:** React/TypeScript in `frontend/` calls relative `/api/` endpoints through a same-origin development proxy. Django remains authoritative for authorization, validation, storage and audit. A small session boundary owns authentication and request generations; feature pages own record state and never persist it in browser storage.

**Tech Stack:** Existing Django/DRF/PostgreSQL/uv; Vite, React, TypeScript, React Router, native fetch, plain CSS, npm lockfile; Vitest/React Testing Library; Python Playwright/pytest against Django live_server and an isolated test database.

**Spec:** `docs/superpowers/specs/2026-10-19-employee-administration-design.md`, `docs/superpowers/specs/2026-10-19-hris-ui-brief.md`, and `PRODUCT.md`.

## Global Constraints

- Keep Django/DRF + React/TypeScript, one repository and same-origin `/api/` access.
- Implement login/logout, employee list/detail/create/edit only. Writable employee fields remain `employee_code` and `full_name`.
- Preserve role/unit checks, strict input validation, text codes with leading zeros, transactional audits and current concurrency behavior.
- Selected shell: persistent navy sidebar, light working surfaces, blue primary actions, dedicated pages and labeled mobile Menu. No second sidebar or modal-led editing.
- Approved English module names: Personnel, Attendance, Payroll, Recruitment, Settings; Applicants belongs inside Recruitment. Only Personnel has working navigation in this slice.
- Retain the selected study's Indonesian task labels and feedback. Do not create salary/unit columns unsupported by the current employee API.
- No SSO, GA work, payroll, production deployment, real employee data, new logo/photos or invented dashboard metrics.
- No component library, query cache, global state package, form framework or shared GA package.
- Local RED/GREEN/optional REFACTOR commits are authorized. No push, main merge or unrelated staging. Preserve the existing uncommitted DEVELOPMENT.md paragraph.
- Do not count unavailable dependencies/database, syntax errors or import failures as behavioral RED. Setup is a separate prerequisite commit.
- Finish each behavior's RED/GREEN cycle before writing the next behavior's implementation. The grouped scenarios below are a queue, not permission to write every test at once.
- Implementation uses test-driven-development and antislop-code throughout. Comments describe non-obvious constraints only.

## Review Focus

1. A write commits but its response/refetch is lost: show the known/uncertain outcome and never auto-replay; test in Task 5.
2. An old account's delayed response arrives after logout/new login: discard it and never restore that account's records/draft; test in Task 3.
3. A valid session gets non-JSON CSRF denial while identity verification has a network failure: preserve uncertainty, avoid raw HTML and never invent logout; test in Task 3.
4. Dirty editing meets browser Back, direct navigation, logout or page unload: warn for ordinary departure, clear on confirmed logout/expiry, and never strand the user; test in Task 5.
5. Missing assets, unknown `/api/` paths or traversal-like URLs reach the SPA fallback: serve proper errors, not application HTML or arbitrary files; test in Task 2.

## Narrow tooling correction for review

The spec initially proposed React Router declarative mode. Its supported `useBlocker` API is available in Data/Framework modes, not declarative mode. Use `createBrowserRouter`/`RouterProvider` in Data mode solely to obtain supported navigation blocking, retaining ordinary components, fetch and the same package. No framework/server rendering, loaders/actions framework or extra state library is required. Update the spec's mode wording in the setup commit after plan approval.

Use Python Playwright with pytest so Django's existing isolated database/live_server fixtures own test data and server teardown. This avoids a second Node end-to-end runner and a custom seed HTTP endpoint.

## File map and interfaces

| Files | Responsibility |
| --- | --- |
| `backend/accounts/capabilities.py` | Server-computed employee read/write policy |
| `backend/accounts/views.py`, `backend/employees/permissions.py` | Consume that same policy; preserve endpoint semantics |
| `backend/config/frontend.py`, `backend/config/urls.py`, `backend/config/settings/development.py` | Development-only built SPA and constrained asset serving; explicit proxy origin trust |
| `frontend/package.json`, `package-lock.json`, `tsconfig*.json`, `vite.config.ts`, `eslint.config.js`, `index.html`, `.node-version` | Pinned build/test tooling and frontend entry |
| `frontend/src/api/client.ts`, `client.test.ts` | Typed fetch failures, CSRF and decoding |
| `frontend/src/auth/SessionProvider.tsx`, `session.test.tsx`, `LoginPage.tsx` | Session lifecycle, generation guard and login |
| `frontend/src/app/router.tsx`, `AppShell.tsx`, `shell.test.tsx`, `main.tsx`, `styles.css` | Routes, selected A shell and responsive presentation |
| `frontend/src/employees/api.ts`, `types.ts`, `EmployeeListPage.tsx`, `EmployeeDetailPage.tsx`, `reads.test.tsx` | Record types and read pages |
| `frontend/src/employees/EmployeeForm.tsx`, `EmployeeCreatePage.tsx`, `EmployeeEditPage.tsx`, `writes.test.tsx`, `useUnsavedChanges.ts` | Field errors, dirty PATCH and write outcomes |
| `frontend/src/test/setup.ts`, `frontend/src/test/render.tsx` | DOM test setup and a real memory-router/session test wrapper |
| `tests/test_capabilities.py`, `tests/test_frontend_routes.py`, `tests/test_browser_harness.py` | Backend capability/routing/harness contracts |
| `tests/browser/conftest.py`, `tests/browser/test_employee_workflow.py`, `tests/browser/test_access.py`, `tests/browser/test_session.py` | Synthetic real-browser acceptance |
| `pyproject.toml`, `uv.lock`, `.gitignore`, `.github/workflows/backend.yml` | Browser test dependencies, generated-artifact ignores and CI |
| `README.md`, `DEVELOPMENT.md`, `docs/04-backend-handover.md` | Reproducible startup/checks, delivered behavior and remaining limits |

```ts
export type Employee = { id: string; employee_code: string; full_name: string };
export type EmployeeInput = Pick<Employee, 'employee_code' | 'full_name'>;
export type Identity = {
  id: number;
  email: string;
  capabilities: { employees_read: boolean; employees_write: boolean };
};
export type ApiFailureKind = 'http' | 'network' | 'protocol';
export class ApiError extends Error {
  constructor(
    public kind: ApiFailureKind,
    public status: number | null,
    public body: unknown,
    public writeOutcome: 'rejected' | 'uncertain' | null,
  ) { super('API request failed'); }
}
```

HTTP 400/403 is a rejected write; transport failure, malformed success or server failure must not be represented as a guaranteed rejection. The API layer does not redirect. Session resolution belongs to the session boundary.

## Shared cycle and check commands

For each behavior below, first add its focused test, run it and capture the intended assertion failure. Stage only that test for `test(red): <behavior>`. Then implement, run the targeted test and all suites currently applicable, and stage only that implementation for `feat(green): <behavior>` or `fix(green): <behavior>`. Record actual commands/results in commit bodies. Refactor only after green, in a separate tested commit.

```bash
uv run pytest -q
uv run python backend/manage.py check
uv run python backend/manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend test -- --run
npm.cmd --prefix frontend run build
```

Frontend commands apply once its test infrastructure exists. Browser checks apply once Task 6 provides its fixture. Use `npm` instead of `npm.cmd` in Linux CI.

### Task 1: Shared capability policy

**Files:** `backend/accounts/capabilities.py`, `backend/accounts/views.py`, `backend/employees/permissions.py`, `tests/test_capabilities.py`; retain all existing authorization tests.

**Interfaces:** Produce `employee_capabilities(user) -> dict[str, bool]` with exact keys `employees_read` and `employees_write`. Consume Django's authenticated user and existing HR/KEPALA_UNIT groups. Identity adds the dictionary as `capabilities` without removing id/email.

- [ ] Write the first failing identity-capability test, run `uv run pytest tests/test_capabilities.py -q`, and commit its observed missing-capabilities failure.

```python
@pytest.mark.django_db
def test_hr_identity_exposes_employee_capabilities(django_user_model):
    from django.contrib.auth.models import Group
    from django.test import Client

    user = django_user_model.objects.create_user(email="hr@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    assert client.get("/api/auth/me/").json()["capabilities"] == {
        "employees_read": True,
        "employees_write": True,
    }
```

- [ ] Implement HR both true, manager read-only and all other accounts false. Keep anonymous identity 403. Make EmployeePermission consume the same helper; leave compensation HR-only and leave unit queryset scoping untouched.

```python
def employee_capabilities(user):
    names = set(user.groups.values_list("name", flat=True)) if user.is_authenticated else set()
    return {
        "employees_read": "HR" in names or "KEPALA_UNIT" in names,
        "employees_write": "HR" in names,
    }
```

- [ ] Run targeted tests and full backend checks; commit GREEN. Then add separate regression cases for HR+manager, manager without grants, other roles, superuser without HR and anonymous access. Compare identity capabilities with direct endpoint outcomes; no new field should confer authority.

### Task 2: Tooling and local same-origin frontend integration

**Files:** tooling/config files in the file map, `backend/config/frontend.py`, development settings/URLs, `tests/test_frontend_routes.py`, `frontend/src/test/setup.ts`, `frontend/src/test/render.tsx`.

**Interfaces:** Vite on loopback `5173` forwards `/api/` to loopback Django `8085`. Django-built mode reads `frontend/dist/.vite/manifest.json` entry `src/main.tsx` and serves files only from `frontend/dist/assets/`, under development settings. Missing build returns controlled 503; unknown API routes remain 404, never SPA HTML. Staging/production must not acquire a DEBUG file server.

- [ ] Read `.python-version`, inspect package engine requirements with `npm.cmd view vite engines --json` and `npm.cmd view vitest engines --json`, select a compatible supported Node runtime and pin its exact tested version in `.node-version` and CI. Do not install into another project or globally replace Node.
- [ ] Create the frontend manifest manually and install exact dependencies, committing `package-lock.json`. Runtime: React, React DOM, React Router. Development: TypeScript, Vite/React plugin, Vitest, jsdom, Testing Library/jest-dom/user-event, ESLint/TypeScript/React hooks lint. Add Python `pytest-playwright` in a dedicated browser dependency group and lock it with uv. Record setup as `build: configure frontend and browser test tools`.
- [ ] Scripts must expose `dev`, `build`, `typecheck`, `lint`, `test`; `build` typechecks before bundling. Configure Vite `build.manifest: true` and relative/browser asset paths compatible with Django's manifest integration. Bind local servers to loopback with strict ports.
- [ ] Write a route test that provides a temporary synthetic build manifest/entry and expects a nested `/employees/<uuid>/edit` GET to include its entry URL. Run it, observe missing SPA behavior and commit RED.

```python
@pytest.mark.django_db
def test_unknown_api_is_not_a_spa_page(client):
    response = client.get("/api/not-a-real-endpoint/")
    assert response.status_code == 404
    assert b'<div id="root"' not in response.content
```

- [ ] Implement SPA HTML from trusted manifest entries, ensure normalized resolved asset paths stay within the asset directory, use correct MIME types, and exclude API/static/assets failures from the fallback. Do not expose `dist/.vite/manifest.json` or an arbitrary filesystem handler. Add explicit CSRF trusted origins for loopback Vite only in development; preserve CSRF middleware and all staging/production restrictions.
- [ ] Add focused routing tests one cycle at a time: missing manifest, malformed manifest, missing asset, traversal-like asset path, missing frontend route, staging/production exclusion and API miss. Test generated CSS/chunk references using a real frontend build in the integration checks.
- [ ] Run backend checks, frontend tools and build; commit GREEN. Do not count config/setup failures as RED. Update the spec to Data-mode router setup with the concrete dirty-navigation reason.

### Task 3: Session boundary and typed transport

**Files:** API/session/login files in the map; `frontend/src/api/client.test.ts`, `frontend/src/auth/session.test.tsx`.

**Interfaces:** `apiRequest<T>(path, options) -> Promise<T>`, `getCsrf(signal?) -> Promise<string>`. `SessionProvider` exposes `status` (`checking`, `authenticated`, `anonymous`, `error`), `identity`, `generation`, `login(email,password)`, `logout()`, `checkDeniedRequest()`, and `retryIdentity()`. Identity uses a non-recursive transport path. Account/session changes advance generation and abort or invalidate old requests.

- [ ] Start with a test that passes a fetch stub to the real API client, records its request, and asserts relative `/api/` plus `credentials: 'same-origin'`. Verify the expected assertion failure before implementing the request contract.

```ts
const fetcher = vi.fn().mockResolvedValue(new Response('', { status: 204 }));
await apiRequest('/api/auth/logout/', { method: 'POST', csrfToken: 'synthetic', fetcher });
expect(fetcher).toHaveBeenCalledWith('/api/auth/logout/', expect.objectContaining({
  credentials: 'same-origin', method: 'POST',
}));
```

- [ ] In separate cycles implement CSRF before unsafe requests, 204 without JSON decoding, content-type-aware errors, and runtime shape checks for identity/employee responses. Never render raw response HTML. Do not retry writes automatically.
- [ ] Implement identity bootstrap; anonymous initial load must not claim expiry. Network/protocol bootstrap failure offers retry, not fake logout.
- [ ] Implement form-encoded login using `username`, refresh CSRF after successful authentication, then resolve identity. Invalid credentials stay generic; disable duplicate submission. Clear password input after successful login.
- [ ] Implement logout with confirmed-session handling. On protected 403, verify identity: anonymous means expiry; authenticated means denied/CSRF feedback; verification failure remains uncertain. Avoid recursive 403 checks on `/me/` and never erase the session on every server/network error.
- [ ] Add component tests for a delayed old-session response arriving after logout/new login, failed logout retaining authentication, HTML 403 with identity-network failure, and session expiry clearing records/drafts. Use controlled promises to order completion, not arbitrary sleep timers.
- [ ] Run component suite, typecheck/lint/build and backend regression checks; finish each cycle with its own GREEN commit.

### Task 4: Approved A shell, employee list and detail

**Files:** router/shell/styles and employee read files in the map; `shell.test.tsx`, `reads.test.tsx`.

**Interfaces:** `listEmployees(signal?) -> Promise<Employee[]>`, `getEmployee(id, signal?) -> Promise<Employee>`. Data router maps `/`, `/login`, `/employees`, `/employees/new`, `/employees/:id`, `/employees/:id/edit`, plus explicit frontend not-found. Authenticated layout wraps records and includes Personnel only as a functional module link.

- [ ] Write a shell test with an authenticated HR identity and assert an accessible Personnel link, signed-in email and logout. Assert there are no working future-module links. Observe its failure, commit RED, then build the selected shell and commit GREEN after checks.

```tsx
expect(screen.getByRole('link', { name: 'Personnel' })).toHaveAttribute('href', '/employees');
expect(screen.queryByRole('link', { name: 'Payroll' })).not.toBeInTheDocument();
```

- [ ] Use the selected study as composition evidence, not copied application logic. Navy sidebar, light records, blue primary actions, one navigation level, modest corners and system sans. Name links are semantic links, not buttons. Do not add metrics/search/status columns or generated assets.
- [ ] Implement list loading, ordered real rows, HR empty/create action, manager empty/read-only message and failed-read retry in independent cycles. Guard routes by capabilities but do not interpret guards as backend enforcement.
- [ ] Implement detail/back navigation, HR edit action, and identical unavailable treatment for missing/outside-unit 404. Preserve loading/error states and invalidate responses when id/session changes.
- [ ] Test direct create/edit routes for managers, denied-role entry, unknown routes and long names/codes. Route resolution must wait for session bootstrap without briefly showing protected content.
- [ ] Style phone rows as labeled stacked records. Menu is keyboard reachable, closeable by Escape, exposes current location/account/logout and restores focus on close. Test it at narrow widths; no fixed footer may obscure content.
- [ ] Run focused tests and all applicable suites before each GREEN commit. Capture selected A at desktop/phone in the final UI review, not in a repeated polishing loop.

### Task 5: HR create/edit and trustworthy save feedback

**Files:** employee write/form/unsaved-navigation files and `writes.test.tsx`.

**Interfaces:** `createEmployee(input, signal?) -> Promise<Employee>`, `patchEmployee(id, changes: Partial<EmployeeInput>, signal?) -> Promise<Employee>`. Form consumes initial values and read/write capability. Persisted original values are the dirty comparison baseline. `useUnsavedChanges(dirty)` uses the supported router blocker and beforeunload for ordinary departures; session teardown overrides blocking and destroys drafts.

- [ ] First test dirty payload derivation before implementation. Then wire the shared form in the next cycle, keeping blank/duplicate/server validation associated with fields.

```ts
expect(changedFields(
  { employee_code: '0001', full_name: 'Pegawai Contoh A' },
  { employee_code: '0001', full_name: 'Pegawai Contoh B' },
)).toEqual({ full_name: 'Pegawai Contoh B' });
```

- [ ] Implement required/length checks (code 64, name 200) without numeric code coercion; authoritative server errors still map to fields/non-field summary. Preserve values on recoverable validation errors, focus the first invalid field and prevent duplicate submit.
- [ ] Implement create -> persisted detail. Explain identity creation does not assign a unit. No-op edit makes no PATCH and therefore creates no new audit event.
- [ ] Implement dirty-only PATCH and post-save GET. Separate save-confirmed/refetch-failed from write-uncertain. A timeout/server failure never triggers an automatic mutation retry or a claim of guaranteed rejection. Provide read-back/return-to-record recovery before the user explicitly retries.
- [ ] Add controlled-response tests: POST persisted but response lost; PATCH 200 followed by GET 503; HTTP 400 versus malformed 201; account expiry during save; late response after route/session changes. Never show stale success on another record/account.
- [ ] Test dirty Cancel, sidebar navigation, browser Back and unload; declining departure preserves inputs, accepting leaves, and a confirmed logout/expiry still clears protected state. Reauthentication does not resurrect or replay the draft.
- [ ] Test form status announcements, readonly route access and maximum-length fields. Run targeted/component/backend suites, typecheck/lint/build; commit each completed behavior cycle independently.

### Task 6: Real-browser and direct API acceptance

**Files:** browser fixtures/tests, `tests/test_browser_harness.py`, `pyproject.toml`, `uv.lock`, `.gitignore`.

**Interfaces:** Browser suite uses pytest-django's disposable test database, `transaction=True` and live_server, with fixture-created HR/manager/other-role users, synthetic units/current assignments and identity records. Playwright contexts stay in memory. No seed/reset endpoints or default persistent-development seeds. Use pytest `--ignore=tests/browser` for ordinary backend checks; run `uv run --group browser pytest tests/browser -q --browser chromium` explicitly for browser acceptance.

- [ ] Establish browser dependency/fixture smoke setup without claiming it as behavioral RED. Build frontend first. Browser suite aborts clearly if build/browser is missing and cleans up contexts/servers through fixture finalizers.
- [ ] Add a harness test proving browser fixtures cannot reuse the configured persistent database as their writable target. Use pytest's actual test-database lifecycle, not a manually named database presumed safe.
- [ ] First acceptance: real form login, identity bootstrap and list on Django-built same origin. Run and observe the missing end-to-end behavior if not already complete; existing working behavior is regression evidence, not manufactured RED.
- [ ] Extend one behavior at a time: create leading-zero code -> reload list/detail -> edit -> reload; blank/duplicate rejection; invalid login; logout; session expiry by deleting the test session server-side, not faking a 403 response.

```python
@pytest.mark.django_db(transaction=True)
def test_hr_create_survives_reload(page, live_server, hr_account):
    page.goto(live_server.url + "/login")
    page.get_by_label("Email").fill(hr_account.email)
    page.get_by_label("Sandi").fill(hr_account.password)
    page.get_by_role("button", name="Masuk", exact=True).click()
    page.get_by_role("button", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Kode pegawai").fill("0099")
    page.get_by_label("Nama lengkap").fill("Pegawai Contoh Browser")
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    page.reload()
    assert page.get_by_text("0099", exact=True).is_visible()
```

- [ ] After real manager login, use `page.context.request` with the session cookie and fresh CSRF token to directly POST/PATCH employee endpoints. Assert 403 and read database/audit counts to prove nothing changed. Direct outside-unit GET returns 404; manager list excludes child-unit, expired/future and unassigned employees; a second granted unit is visible.
- [ ] Test HR+manager, no-grant managers and other roles against backend policy; retain compensation-denial and no implicit superuser authority tests. Never put salary data in employee UI fixtures/responses.
- [ ] Test missing-CSRF mutation rejection separately from role denial. A role-denial test sends a valid token so a CSRF failure cannot disguise broken permissions.
- [ ] Run one real proxy smoke through Vite using live_server's dynamically assigned backend URL in the proxy target. Verify CSRF Origin handling, login, write and logout through Vite, not only Django built mode. Teardown the spawned Vite process even on failure.
- [ ] Exercise keyboard-only navigation, phone Menu and selected A at 360/390/768/1280/1440 widths, long allowed values and 200% text enlargement. Capture one batched desktop/phone round; fix together and confirm once. Record actual contrast and console results. Acceptance must be real, not the old design-study role toggle.

### Task 7: CI, reproducibility, review and handover

**Files:** `.github/workflows/backend.yml`, README, DEVELOPMENT, handover, selected design documentation.

**Interfaces:** Clean checkout installs from npm/uv locks, builds frontend, runs backend/component/browser checks with PostgreSQL and provisioned Chromium. CI action references remain commit-pinned. Development guide names the two loopback ports and the built verification command.

- [ ] Add a focused CI-configuration contract test to `tests/test_ci_configuration.py` for frontend build before browser checks, browser installation and retained backend commands; observe missing steps, commit RED, then add the minimum CI steps. Resolve official action commit SHAs during implementation rather than inventing them in this plan.
- [ ] CI: uv sync including browser group; exact Node from `.node-version`; `npm ci`; typecheck/lint/component tests/build; existing migrations/backend checks; `uv run --group browser playwright install --with-deps chromium`; explicit browser suite. Test artifacts remain ignored/private; do not upload cookie/session traces or screenshots with real data.
- [ ] Update local instructions for Vite 5173 -> Django 8085, explicit loopback CSRF setup and local Django-built mode. Integrate around, and preserve verbatim, the existing uncommitted DEVELOPMENT paragraph. Stage only new owned documentation hunks; if safe partial staging is unavailable, leave DEVELOPMENT uncommitted and report it rather than bundling user changes.
- [ ] Run all checks from Shared cycle commands plus the explicit browser suite and proxy smoke. Independently review the whole branch for scope, security, stale-state races, validation, responsive A fidelity and comment hygiene. Prefer native execution plus one fresh final reviewer for this tightly coupled slice; no review is replaced by the synthetic design study.
- [ ] Address material review findings with reproducing RED/GREEN cycles, then rerun complete checks. Record only observed results; do not claim remote CI unless it actually ran.
- [ ] Document final tokens from the implemented UI in DESIGN.md and `.impeccable/design.json` at UI finish, not by inventing a pre-build brand system. Update handover with acceptance commands/results, known same-field concurrency limits and the incomplete M1 boundary.
- [ ] Commit only completed owned changes. Do not push or merge main. Report next M1 increment as controlled account/unit administration, then richer records, then assignment/compensation write workflows.

## Self-review and execution gate

Coverage: capability/session policy -> Tasks 1/3; same-origin and built routes -> Task 2; approved A/read states -> Task 4; create/edit and uncertain outcomes -> Task 5; real persistence/direct permission/audit evidence -> Task 6; CI/docs/final review -> Task 7. Each Review Focus item has an owning test queue. No schema/payroll/GA expansion is planned.

Resolve generated package versions/action SHAs from official sources during setup, commit exact tested values and never fabricate resolved versions. Test snippets above establish concrete contracts; implement and execute them within their own vertical cycles rather than prewriting the whole test queue.

Owner reviews this plan and selects native or subagent-driven execution before runtime implementation. Native is recommended here to avoid repeated context costs across the shared session/router/forms interfaces; use one independent whole-branch review at the end.
