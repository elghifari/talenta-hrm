# Development workflow

## TDD commits

For new behavior and bug fixes, use separate commits for each small red-green-refactor cycle:

1. **RED:** write one focused test, run it and confirm it fails because the behavior is missing. Commit the test before writing its implementation: `test(red): <behavior>`. Record the test command and expected failure in the commit body. A typo, unavailable database or broken test setup does not count as RED.
2. **GREEN:** implement the minimum needed, run the targeted test and full suite, then commit: `feat(green): <behavior>` or `fix(green): <behavior>`. Record the verification command and result.
3. **REFACTOR**, when needed: improve structure without changing behavior, rerun the tests and commit separately: `refactor: <change>`. Do not manufacture a refactor just to complete the sequence.

Finish one behavior's cycle before starting the next. Do not batch all tests first and all implementations afterward. Stage only the changes belonging to the current phase.

RED commits intentionally fail the new test. Keep incomplete cycles on local feature branches; merge into `main` only after the full suite and repository checks pass. A complete branch may retain its RED commits; do not squash away the sequence. Do not push without explicit authorization.

Documentation-only changes do not require a failing behavior test. Record necessary setup/configuration separately; changes to runtime behavior still require test-first verification.

Use the commands under **Checks** in [the development guide](../DEVELOPMENT.md). Database regressions must use the isolated PostgreSQL test database, never production data.

## Existing baseline

The initial backend was committed with tests and implementation together. Its executed test-first cycles are recorded in the build session, not separate RED/GREEN commits. This convention applies to subsequent work. Privacy-only history filtering does not create RED/GREEN commits retroactively.

## Public and private documentation

Keep the README focused on the product, current work and a short route into local setup. A brief active-development note is enough; detailed operational limits belong in the development guide and backend handover.

Company-specific planning and payroll specifications stay private. Local working copies live in the ignored `.private/planning/` folder. A local-only `private/planning-archive` branch preserves the pre-publication history. Do not push private archival branches, and do not use `git push --all` or `git push --mirror`.
