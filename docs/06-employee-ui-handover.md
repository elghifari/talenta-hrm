# Employee administration UI handover

Local verification checkpoint: 2026-10-19. This delivers the first employee-administration React slice, not all of M1 or a payroll/production release.

## Delivered

- Approved A shell: persistent navy Personnel navigation, light records and blue primary actions; phone Menu and stacked rows. Future module labels remain reserved, without dead links.
- Personal-email session login/logout with CSRF, post-login token refresh, identity bootstrap and server-computed employee capabilities.
- HR list/detail/create/edit for text employee code and full name. Leading zeros remain intact. PATCH sends changed fields only; untouched forms do not write.
- Managers see scoped read-only records. Other roles and technical superusers do not gain implicit business access. Endpoint authorization remains authoritative.
- Loading, true empty states, field/server validation, access denial, unavailable records, network errors, session expiry and uncertain-save feedback.
- Successful writes refetch persisted state. Lost mutation responses never auto-replay. A confirmed write followed by failed refetch is not reported as an unsaved record.
- Dirty Cancel/navigation warning, browser-unload protection and dirty logout confirmation. Logout/expiry destroys protected drafts and old-session responses cannot refill them.
- Real same-origin development proxy and development-only manifest/asset integration for built-app deep-link reloads. Unknown API/asset paths are not SPA success pages.

The employee API still contains only id/code/name. Creating identity does not assign a unit. There is no unit, assignment, salary, import or account-administration UI in this slice. Compensation-history reads remain an HR-only API, not a new UI screen.

## Verification evidence

Executed locally at this checkpoint:

| Check | Observed result |
| --- | --- |
| Backend pytest suite | 73 passed |
| Frontend Vitest suite | 16 passed |
| Real Chromium/Django/PostgreSQL suite | 13 passed |
| npm clean lockfile install | Passed; npm reported zero known vulnerabilities at install time |
| TypeScript, ESLint, Vite build | Passed |
| Django system check | No issues |
| Migration drift | No changes detected |
| Ruff lint/format | Passed |
| Impeccable mechanical detector | Empty findings array |
| Git whitespace check | Passed |

Browser evidence includes create/edit persisted after reload, blank/duplicate input, actor/action/target audits, two explicit manager unit grants, no child-unit inheritance, expired/future/unassigned exclusions, valid-CSRF direct manager POST/PATCH denials with unchanged database/audits, outside-unit API 404, compensation denial, no-CSRF HR denial, role-denied UI, invalid login, real session invalidation, logout, dirty navigation and a Vite-proxy login/write/logout round-trip.

Additional resilience evidence: failed-read retry, true HR/manager empty states, a write committed by Django with its browser response deliberately aborted (one row, one audit, no automatic retry), loaded-heading keyboard focus, long allowed names/codes, no page overflow at 360/390/768/1280/1440px, and 200% text enlargement. Frontend controlled-response tests exercise old-session response rejection and identity-network failure after 403.

Synthetic screenshots are in ignored `.local/ui-review/` (`desktop.png`, `mobile.png`, `create.png`). The runtime contrast sample recorded 29 visible text/background pairs with a minimum ratio of 5.41:1; this is a sample, not a comprehensive accessibility certification. No screenshot contains real employee data.

The proxy test exposed an existing invalid logout response body: JSON `{}` with HTTP 204. A direct-view regression observed it fail before the handler was corrected to return an empty response. A separate RED/GREEN cycle fixed focus on asynchronously loaded detail headings.

No GitHub Actions run or deployment is claimed. CI configuration now installs the pinned Node version, builds/tests the frontend, provisions Chromium and runs backend plus explicit browser suites; it remains to be verified remotely when a push is authorized.

## Run and verify

Follow DEVELOPMENT.md. Normal development: Django on loopback 8085, Vite on loopback 5173 with relative `/api/` forwarding. Local built mode: build frontend first, then open Django on 8085. The local built asset handler is not enabled by staging/production settings.

```bash
uv run pytest -q
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
uv sync --frozen --group browser
uv run --group browser playwright install chromium
uv run --group browser pytest --run-browser tests/browser -q
```

Use `npm.cmd` on Windows Git Bash if its npm wrapper requires it. Browser tests create users/units/records only in pytest's disposable database and tear down browser/server resources. They do not seed a development login. Port 5173 must be free for the proxy smoke. Django async protection is not disabled: browser lifecycle is function-scoped and live ORM assertions use short-lived worker threads.

For a synthetic local HR login, a trusted maintainer can use Django's management shell after `bootstrap_roles`:

```python
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

user = get_user_model().objects.create_user(email="synthetic-hr@example.test")
user.set_password(getpass("Synthetic local password: "))
user.save(update_fields=["password"])
user.groups.add(Group.objects.get(name="HR"))
```

Use an isolated synthetic development database only. This is explicit trusted maintenance, not a new account-administration interface. Do not reuse test/demo credentials for production or paste passwords into chat. A technical superuser without HR is deliberately not an HR approver.

## Limits and next increment

- Same-field employee edits remain last-writer-wins. This slice does not authorize that policy for future payroll revisions.
- No controlled account/unit administration, assignment/compensation write API, richer employee fields, import, payroll, SSO, GA integration or production frontend serving.
- Browser unload prompts remain subject to browser behavior. In-app dirty navigation has explicit confirmation.
- No account recovery/MFA, login-rate limiting, hosting/TLS/reverse-proxy validation or production acceptance is implied.
- Next M1 increment: controlled, audited account/unit administration; then richer employee records; then assignment and compensation write workflows.

Detailed spec and selected UI brief remain under `docs/superpowers/specs/`. The implementation plan is under `docs/superpowers/plans/`. Local RED/GREEN commits preserve observed failures and passing verification. Do not push or merge without owner authorization.
