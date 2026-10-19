# Employee administration frontend

Date: 2026-10-19
Status: implemented locally after design and native execution-plan approval. See ../../06-employee-ui-handover.md for verification and remaining limits. The starting-point section below remains historical context.

## 1. Outcome and scope

Give HR a usable browser workflow for employee identity administration and unit managers a scoped, read-only view. Keep the existing Django/DRF authorization, validation, database constraints and employee-change audit behavior.

This slice includes:

- Personal-email login and logout using Django sessions.
- Employee list and detail.
- HR creation and editing of employee code and full name.
- Manager reads restricted to current assignments in explicitly granted units.
- Loading, empty, invalid-input, denied-access, unavailable-record, network/server-error and expired-session states.
- Reproducible synthetic browser acceptance and direct API permission tests.

It excludes account/unit administration, assignment writes, richer employee fields, compensation UI/writes, import, payroll, SSO, cross-application integration and production deployment. M1 remains incomplete after delivery.

New employee records have no assignment. HR can see them immediately; managers cannot see them until a current assignment is established through the existing trusted maintenance path. The UI must not imply that creating identity also assigns a unit.

## 2. Verified starting point

The repository has a Django/DRF backend and no frontend scaffold or package manifest. Employee responses contain only `id`, `employee_code` and `full_name`. The identity endpoint currently returns account `id` and `email` only.

Executed during context refresh on 2026-10-19:

- `uv sync --frozen`: passed.
- `uv run pytest -q`: 53 passed.
- `uv run python backend/manage.py check`: no issues.
- `uv run python backend/manage.py migrate --check`: passed.
- `uv run python backend/manage.py makemigrations --check --dry-run`: no changes.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 71 files formatted.

The documented isolated PostgreSQL cluster was started on loopback port 55439 before database verification. Historical handover results are not the evidence for these results. No remote CI or production verification is claimed.

## 3. Frontend tooling and boundaries

Use a `frontend/` workspace with Vite, React, TypeScript, React Router in Data mode for supported dirty-navigation blocking, native `fetch` and plain CSS. Use npm and commit its lockfile. Select and pin compatible package/runtime versions during setup; do not assume that the machine's currently installed Node release is the repository standard.

Use Playwright for browser acceptance. Add focused component tests with Vitest and React Testing Library for state transitions that are difficult to exercise deterministically through a live server. Mock only transport timing/failures where necessary; real browser workflows and authorization acceptance use Django and PostgreSQL.

Do not add a component library, query cache, global state package, form framework or shared GA package for this slice. Revisit only if an implementation constraint warrants a specific change.

Separate responsibilities:

- API client: relative URLs, cookie-backed requests, CSRF, response decoding and typed failure categories.
- Session boundary: identity bootstrap, capabilities, login/logout, expiry and cleanup.
- Employee pages: list, detail, create/edit orchestration and page-specific states.
- Employee form: labeled fields, dirty-field tracking, validation and pending submission.
- Shared presentation: shell, status/error feedback and small form primitives where reuse actually exists.

Do not mirror the backend's authorization rules in frontend role-name conditionals. The client consumes server-computed capabilities for presentation; every API operation remains independently protected.

## 4. Same-origin routing

Browser routes:

| Path | Screen |
| --- | --- |
| `/login` | Login |
| `/employees` | Employee list |
| `/employees/new` | HR create form |
| `/employees/:id` | Employee detail |
| `/employees/:id/edit` | HR edit form |
| `/` | Resolve session, then redirect to login or employee list |

Unknown frontend routes show a not-found screen. A signed-in account without employee-read access sees access denied rather than an empty employee list.

During development, the browser opens the Vite origin. Vite forwards `/api/` requests to loopback Django. Credentials and requests remain same-origin from the browser's perspective. Validate real login, CSRF rotation and mutations through this proxy; use narrowly scoped development configuration if origin handling requires it. Do not disable CSRF or use wildcard trust/CORS settings.

Provide a local built-asset smoke path served by Django so browser refreshes on nested routes load the application. The SPA fallback must not catch `/api/`, convert missing API routes into HTML success responses, or expose arbitrary filesystem paths. Asset references must work with the generated build manifest. This is local integration, not a production hosting configuration.

## 5. API contract

Keep the existing employee endpoints and writable fields unchanged:

| Operation | Request | Success |
| --- | --- | --- |
| List | `GET /api/employees/` | Existing array of scoped employees |
| Detail | `GET /api/employees/{uuid}/` | Existing identity representation |
| Create | `POST /api/employees/` | 201 with created identity |
| Edit | `PATCH /api/employees/{uuid}/` | 200; refetch detail after save |

Preserve unknown/read-only-field rejection, text codes with leading zeros, duplicate-code errors, atomic audits and existing concurrency tests. Send only changed fields on PATCH. An unchanged form does not submit a write or create an audit event.

Add an additive capability object to `GET /api/auth/me/`:

```json
{
  "id": 1,
  "email": "synthetic-hr@example.test",
  "capabilities": {
    "employees_read": true,
    "employees_write": true
  }
}
```

The example is synthetic. HR receives both capabilities. KEPALA_UNIT without HR receives read only; a manager with no grants may read an empty scoped list. Other roles receive neither. Staff/superuser flags confer no implicit business access. An HR-plus-manager account retains HR access. Capabilities must derive from the same policy as the employee endpoint, with regression tests guarding against drift. Do not return salary data, grant inventories or unrelated role details.

No schema migration should be required for this slice.

## 6. Session and failure behavior

1. Bootstrap with `/api/auth/me/` before rendering employee data. Anonymous access shows login without a spurious expired-session message.
2. Fetch CSRF before login. Submit email in the existing form field `username`, not JSON credentials.
3. Refresh CSRF after successful login because Django rotates the token. Resolve identity/capabilities before opening protected content.
4. Use cookie-backed authentication and relative API URLs. Do not store passwords, session tokens or employee records in local/session storage.
5. On successful logout, clear session and employee state and show login. If logout fails, report it rather than claiming the server session ended. A confirmed already-expired session may transition to login.
6. On a protected-request 403, check identity. If identity is now anonymous, clear employee state and show the expired-session message. If identity is authenticated, show permission/CSRF failure without pretending the user logged out. A failed identity network request is not proof of expiry.
7. Never automatically replay POST/PATCH after reauthentication or CSRF failure. The user reviews and explicitly submits again.
8. Ignore or cancel in-flight responses belonging to an old session or route. A late response must not repopulate employee data after logout, expiry or account switching.
9. Preserve an unsaved form only in current-session memory on ordinary recoverable errors. Clear it on logout/expiry and never restore one account's draft for another account.

Map 400 field errors to the corresponding input and show non-field errors in the form summary. Handle non-JSON CSRF/server responses without rendering raw HTML or stack traces. Do not translate every 400 into invalid login or every 403 into session expiry.

Missing and outside-unit employee details both show `Data pegawai tidak tersedia` without confirming existence. Network/server failures show a retry action for reads. For an uncertain write outcome, explain that saving could not be confirmed and require checking persisted data before retrying; do not claim the write failed or silently submit again.

## 7. Screen behavior

### Login

Email and password fields with appropriate autocomplete attributes, visible labels and a submit button. Invalid credentials show one generic Indonesian error. Pending requests prevent duplicate submission. An already-authenticated user opening login resolves to employee administration or access denied.

### Employee list

Show employee code and full name in backend order. Employee names link to detail. HR sees `Tambah pegawai`; managers do not. Managers see a concise read-only indication. No unit column, unit filter or salary information is invented from fields the API does not provide.

Show explicit loading and retryable error states. HR empty state offers creation; manager empty state explains that no employees are available within current access, without suggesting write access. Search, grouping, pagination and bulk actions are outside this slice.

### Create

Fields: `Kode pegawai` and `Nama lengkap`. Respect the existing maximum lengths of 64 and 200, requiredness and server validation. Preserve codes as strings. Success navigates to persisted detail with confirmation. Validation retains entered values. Explain that unit assignment is separate. Cancel returns to the list and warns before discarding dirty inputs.

### Detail and edit

Detail shows code and name. HR receives an edit action; managers have no edit controls. Direct access to the create/edit route without write capability shows access denied and never fetches data outside the existing read rules.

Editing starts from fetched detail. Save PATCHes dirty fields only and refetches detail. If PATCH succeeds but refetch fails, report that the save succeeded but current data could not be reloaded; do not resubmit. Show success only after confirmed server results. Warn before discarding dirty edits during in-app navigation and browser unload where supported.

Existing same-field last-writer-wins behavior remains. This slice does not introduce optimistic locking or imply stronger concurrency guarantees.

## 8. Selected visual direction

The owner selected concept A, the persistent-sidebar shell, after reviewing the synthetic design study. The approved English module names are Personnel, Attendance, Payroll, Recruitment and Settings, with Applicants inside Recruitment. See [the selected UI brief](2026-10-19-hris-ui-brief.md) for screen composition, responsive behavior and the distinction between future navigation and working destinations.

The local study is an in-memory design artifact, not an implemented React frontend or backend-connected acceptance demonstration.

Reading: employee-administration screens for HR and unit managers, using a compact office-records visual language. ENERGY 1 / RHYTHM 1 / MOTION 1.

| Decision | Purpose |
| --- | --- |
| English module names; concise Indonesian task labels and feedback as shown in the study | Keep module terminology consistent while preserving the task language in the selected screens |
| Navy persistent sidebar, light working surfaces and blue primary actions | Preserve the selected concept A hierarchy and reserve emphasis for the current task |
| System sans-serif text | Keep labels and mixed-case names readable without downloading fonts |
| Consistent code-first rows and aligned form labels | Make stable employee identifiers easy to compare and preserve their leading zeros |
| Persistent sidebar, compact account header and content-led pages | Keep orientation stable as real modules are added; omit dead future destinations and decorative dashboards |
| Dedicated create/edit pages | Support deep links, reloads and predictable focus without modal lifecycle complexity |
| Structural spacing and modest corners | Separate record sections and controls without floating cards or decorative pills |
| Hover/focus feedback only, reduced-motion support | Confirm interaction without distracting from record administration |

Use product name as text. No generated logo, avatar, photograph, illustration, decorative statistics or icon package. Ship one reviewed light theme, not an untested theme toggle.

At narrow widths, stack form controls and render employee rows in a readable stacked layout while preserving code/name labels. Do not truncate the only accessible employee name or cause horizontal page overflow. Verify at 360px, 768px and 1280px widths and with long allowed field values.

Use semantic headings, labels, tables/lists, links and buttons; visible keyboard focus; error associations; announced save/status feedback; focus transfer after navigation and failed submission. Touch targets are at least 44px. Verify text contrast against AA thresholds. Color alone must not communicate errors or read-only access.

## 9. Acceptance matrix

All fixtures are explicitly synthetic. Browser acceptance runs against an isolated disposable PostgreSQL test database, not the persistent development database. The harness provisions fixtures, starts real servers, runs tests and tears down its database/processes. It must not seed test users into an arbitrary configured database or print credentials into public artifacts.

| Scenario | Required evidence |
| --- | --- |
| HR login/logout | Real cookie and CSRF flow; invalid credentials; protected access after logout denied |
| Persistence | Create code with leading zeros, reload detail/list, edit name/code, reload and confirm server values |
| Invalid input | Blank/whitespace, overlength and duplicate codes; field feedback; no rejected write/audit persists |
| HR audit | Successful creation/update has correct actor/action/target; no-op form causes no update |
| Manager reads | Employees in multiple explicitly granted units visible; unassigned, expired, future and outside-unit assignments do not grant visibility |
| No descendant inheritance | Parent-unit grant does not expose employees in a child unit without an explicit grant |
| Denied writes | Authenticated manager POST/PATCH sent directly to API returns 403; employee state and audit count unchanged |
| Outside-unit detail | Direct API GET and guessed browser detail route reveal no employee data; API returns 404 |
| Other accounts | Finance, technical-admin, intern, ungrouped and superuser-without-HR cannot gain employee writes/compensation reads |
| Capabilities | HR, manager, combined groups, no grants and denied roles agree with actual endpoint permissions |
| Session expiry | Invalidate server session while a page is open; subsequent read/write leads to login with expiry feedback, clears data and never replays mutation |
| Authenticated denial | A valid session receiving 403 remains authenticated and shows a useful error |
| Failed transport | Loading, empty, failed reads, uncertain writes, failed logout and malformed/non-JSON errors behave as specified |
| Stale response | Delayed old-session response cannot refill data after logout or account change |
| Navigation | Direct nested URL load, refresh, back/forward, dirty-form cancellation and unknown paths work |
| API boundary | Unknown API routes remain API errors, never SPA HTML; no client compensation leakage |
| Accessibility/layout | Keyboard-only workflow, focus/error announcements, contrast, target size and defined viewport checks |

Extend existing regression tests rather than artificially breaking already-working permissions to manufacture RED. Use test-first cycles for genuinely new behavior and discovered bugs. Browser interception is acceptable for deterministic transport states, not as evidence that backend permissions work.

## 10. Delivery and commit workflow

The user authorized local commits without per-commit permission on 2026-10-19. Pushing still requires explicit permission.

- Use a local feature branch. Keep incomplete RED cycles off `main`.
- For each behavior, write one focused test, execute and observe the intended failure, then commit `test(red): <behavior>` with command and failure evidence.
- Implement the minimum, run targeted and full relevant suites, then commit `feat(green): <behavior>` or `fix(green): <behavior>` with verification results.
- Refactor only when useful, rerun checks and commit it separately. Do not batch all tests before all implementation or invent a refactor phase.
- Record setup/configuration separately. Missing dependencies, unavailable databases and syntax errors do not count as behavioral RED.
- Apply antislop-code comment hygiene throughout: comments explain non-obvious constraints; no banners, obvious restatements or workflow narration. This hygiene must not alter executable behavior.
- Preserve the user's existing uncommitted `DEVELOPMENT.md` paragraph. Do not include it accidentally in a spec or implementation commit.
- Keep private planning, local data, credentials, browser auth state, screenshots containing sensitive information and test database artifacts out of commits.
- Add frontend checks to CI; retain backend checks. Run type checking, frontend lint/tests/build, browser acceptance and the existing backend suite/checks before declaring completion.
- Document reproducible startup, built-app verification and synthetic acceptance. Report actual executed results and remaining limits. Do not claim M1, payroll or production readiness.

## 11. Delivery sequence and review gates

This is the scope/order, not the detailed implementation plan:

1. Add and test capability metadata without weakening endpoint checks.
2. Establish frontend tooling, same-origin routing and real session login/logout.
3. Deliver scoped list/detail with complete read states.
4. Deliver HR create/edit with validation, persistence and audit checks.
5. Finish adversarial acceptance, accessibility, built-route smoke coverage, CI and handover.

Owner review of this written specification comes before the detailed implementation plan. Review of that plan and selection of execution method come before product coding. Commit authorization removes per-commit prompts; it does not remove these design/plan review gates.

After this slice, the next M1 increment is controlled account/unit administration, followed by richer employee records, then assignment and compensation write workflows.

## 12. Specification self-review

- Scope is restricted to the existing identity fields and explicit session/capability integration.
- Server authorization stays authoritative; frontend controls are not permission evidence.
- Same-origin development and local built-asset paths are specified without deployment claims.
- Validation, session expiry, authenticated denial, ambiguous write outcomes and stale responses have defined outcomes.
- Concept A and the approved English module labels replace the earlier provisional teal/minimal-header direction. The synthetic study is not an application-verification claim; no brand assets or fake product claims were created.
- The acceptance matrix requires real persistence, direct denial checks and audit read-back.
- No unresolved payroll policy, private company specification or production data is needed for this slice.
- Implementation-plan review remains a gate. Nothing here claims that the frontend has been implemented or tested.
