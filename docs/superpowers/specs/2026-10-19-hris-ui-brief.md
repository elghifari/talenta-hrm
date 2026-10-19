# HRIS UI brief: persistent sidebar

Date: 2026-10-19
Status: concept A and module names approved. This brief records the selected direction for the employee-administration slice; it does not authorize additional modules or replace implementation-plan review.

## Selected direction

Use concept A from the synthetic shell comparison: a persistent navy sidebar, a light working surface, a compact account header and code-first employee records. The interface is for operating on records, not viewing a decorative dashboard.

HR mainly uses desktop/laptop; managers use desktop and phone. ENERGY 1 / RHYTHM 1 / MOTION 1. Maintain predictable positions and concise feedback rather than introducing decorative motion.

Approved English module labels:

- Personnel
- Attendance
- Payroll
- Recruitment, with Applicants inside it
- Settings

Personnel is deliberately broader than an employee list: later assignments, positions and compensation administration can live within it. These labels do not authorize features or change role access.

## Shell and navigation

Desktop: full-height sidebar on the left; product name as text at its top; working module selection below. The account header contains route context, signed-in email and logout. The content area starts with the page title and one primary action, followed immediately by the records or form.

The comparison study shows future module labels to evaluate the overall information architecture. The implemented slice exposes only functional destinations. Do not ship dead Attendance, Payroll, Recruitment or Settings links, invent dashboard metrics, or expand account administration to populate the shell. Add destinations when their workflows exist and the user has the relevant access.

Use a single navigation level for this slice. Do not inherit concept C's second sidebar. Local record navigation belongs in the page, with a return-to-list action and explicit detail/edit routes.

At intermediate widths, reduce navigation width and content padding before compromising record readability. On phones, replace the sidebar with a labeled Menu; show the current module and account/logout access inside it. Employee rows stack code above name. Forms become one column. No hover-only controls or icon-only navigation.

## Employee screens

| Screen | Composition and actions |
| --- | --- |
| Login | Standalone narrow form with product name, email, password, submit and generic credential feedback; no authenticated sidebar |
| List | Personnel selected; Data pegawai title, brief task description and HR-only Tambah pegawai action; code/name table directly below |
| Detail | Return-to-list action, employee name heading, HR-only Ubah data action, labeled code/name values; no fabricated unit, salary or employment status |
| Create | Dedicated page, code/name inputs, unique-code guidance, save/cancel and a note that assignment is separate |
| Edit | Same form structure as create, prefilled from persisted detail; save dirty fields only, refetch after success, warn before discarding changes |
| Manager | Same record structure with a concise read-only notice; no create/edit controls or unauthorized fields |

English module names are approved. Indonesian task labels and form feedback remain as shown in the selected study; the module-name decision does not require translating every field or message.

Do not add search, bulk operations, extra table columns, photos, row action menus or sorting controls without corresponding scope/API support. Do not turn the two-field identity form into a drawer or modal: dedicated pages remain the selected flow.

## State and feedback design

- Loading names the requested resource without blocking unrelated navigation.
- HR empty state offers creation; manager empty state explains that no employees are available within current access.
- Validation appears at the affected field, with focus on the first error and entered values retained.
- Successful create/edit shows confirmed save feedback. A successful write followed by a failed refetch does not invite resubmitting the write.
- Failed reads offer retry. An uncertain write explains that its outcome must be checked before retrying.
- A live session without permission shows access denied. Missing and outside-unit records share a non-disclosing unavailable view.
- Expiry clears protected records/drafts and returns to login with context; it never silently replays a mutation.
- Logout failure is visible; the UI must not claim that a server session ended when it could not confirm it.

The backend remains authoritative for every permission and write. The study's role switch and in-memory save messages are review controls, not application features or acceptance evidence.

## Visual starting points

Carry the selected study's navy navigation (`#163049`), blue action accent (`#315a85`), light working ground (`#f7f9fb`) and white record surfaces into implementation as starting values. These describe the selected study, not an existing corporate brand or a finished token system. Recheck contrast in every implemented state.

Use the system sans-serif stack shown in the study for readable office records and no font-download dependency. Modest corners, flat record surfaces and structural spacing keep names and identifiers dominant. Keep employee codes as text and use tabular numerals where useful. Product name remains text; no generated logo, portraits or illustration assets.

Keyboard focus, labels/error associations, announced feedback, 44px minimum touch targets, text reflow and long-field handling are required. Verify phone, intermediate and desktop widths. The approved shell does not justify clipping text or shrinking navigation labels to fit.

## Design evidence and limits

Local design study: `.private/design/hris-shell-study.html`.

Local browser-check evidence: `.private/design/review/verification.json` and desktop/phone captures. The study was exercised in headless Edge with Playwright, including layouts at 360, 390, 768, 1280 and 1440px; menu, role presentation, list/detail/form navigation, blank/duplicate feedback, create/edit simulations and state controls. No uncaught JavaScript errors were reported; sampled visible text pairs passed AA calculations. These are design-study checks, not comprehensive accessibility certification.

The study is explicitly synthetic, local and in-memory. It does not demonstrate session authentication, server permissions, audit integrity or persistence after reload. Those remain real application acceptance requirements in the employee-administration specification.

## Handoff boundary

A and the English module names are settled. Do not reopen the shell comparison during implementation without a concrete constraint. Reconcile the implementation plan with this brief and the employee-administration specification. Keep the existing DEVELOPMENT.md change untouched. Local commits are authorized; pushing is not.
