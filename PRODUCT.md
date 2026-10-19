# Talenta HRM

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Django/DRF, React/TypeScript, PostgreSQL, one repository and same-origin frontend/API. Django session authentication; no SSO in the current slice. Frontend tooling is proposed in the employee-administration specification and remains subject to design/plan review.

## Users

HR maintains employee identity and eventually manages attendance/payroll workflows. Unit managers read employees within explicitly granted units and eventually supply unit operational inputs. Finance has a later payroll sign-off role; it does not currently have employee-administration access by default. Technical access does not imply business authority.

HR mainly uses a laptop/desktop. Managers use a mix of desktop and phone. Employee self-service is outside the current scope.

## Product Purpose

Replace fragmented spreadsheet and message handoffs with employee administration and, in later increments, attendance intake and auditable payroll. The immediate outcome is reliable employee create/read/update for HR and scoped, read-only access for managers.

## Operating Context

A legacy Apps Script payroll application over spreadsheets provides terminology and workflow evidence, not approved visual direction or automatically authoritative calculation rules. The owner requested reviewing familiar vocabulary and workflows while replacing its visual design.

Design the overall HRIS shell and navigation first, then detail the employee-administration slice. The selected direction is now implemented in the first employee-administration slice; verification and limits are recorded in docs/06-employee-ui-handover.md. Future modules may appear in clearly labeled planning diagrams, but must not masquerade as working product navigation.

## Capabilities and Constraints

The current application supports React session login/logout, employee identity list/detail and HR create/edit, unit-scoped manager reads, server capability metadata, effective-dated storage and employee-change auditing. HR compensation-history reads remain API-only. Employee identity exposes UUID, text employee code and full name. Creating identity does not create an assignment.

Preserve server-side authorization, strict validation, text codes with leading zeros and transactional audits. Do not send unauthorized salary or outside-unit data to the client. Unit descendants do not inherit grants automatically.

This slice excludes account/unit administration, richer employee fields, assignment and compensation writes, imports, payroll, cross-app integration and production deployment. Future workflow designs must remain distinguishable from current capabilities.

## Evidence on Hand

README.md, DEVELOPMENT.md, backend code/tests, docs/04-backend-handover.md, docs/05-development-workflow.md and docs/superpowers/specs/2026-10-19-employee-administration-design.md. Private planning and legacy source are local reference material and must not be copied into public artifacts wholesale.

The backend's 53-test suite and repository checks were executed during context refresh on 2026-10-19. The first React employee-administration slice is implemented locally. The owner subsequently selected concept A from the synthetic shell study: persistent navy sidebar, light record surfaces and blue primary actions. The selected direction is recorded in docs/superpowers/specs/2026-10-19-hris-ui-brief.md. This supersedes the earlier light/teal minimal-header proposal. No logo, photo or illustration assets are approved; the study does not establish an existing corporate brand system.

Use explicitly synthetic records for design demonstrations and test acceptance. No real employee/payroll data, credentials or unsupported claims belong in design artifacts.

## Product Principles

- Keep server authorization independent of presentation.
- Make save results, validation and current access understandable.
- Preserve employee identity and history across workflow changes.
- Design only genuine actions; distinguish future scope from implemented behavior.
- Settle high-impact interaction and layout decisions before product coding.

## Accessibility & Inclusion

Responsive browser workflows, keyboard access, visible focus, associated labels/errors and adequate contrast are required. Manager tasks must remain usable on phones. Indonesian interface language is proposed in the current specification; confirm it during surface design.

## Design Decisions

The owner selected concept A, the persistent-sidebar shell, and approved these English module labels: Personnel, Attendance, Payroll, Recruitment and Settings. Personnel covers the broader employee-administration scope. Applicants names the applicant list within Recruitment. These labels supersede the earlier provisional Indonesian module names; they do not change backend permissions or the current implementation scope.

The persistent-sidebar structure is settled. Use dedicated employee list/detail/create/edit pages and a labeled Menu on phones, not a second sidebar or modal-led editing. The selected study uses Indonesian task labels with English module names. Future modules must not expand this implementation slice or appear as dead product links. Detailed implementation tokens and non-text assets are not yet a finished design system.
