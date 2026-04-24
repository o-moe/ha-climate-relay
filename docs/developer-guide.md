# Developer Guide

## Purpose

This document is the developer-focused repository entry point. User-facing
documentation belongs in [README.md](../README.md).

## Repository Structure

- `custom_components/climate_relay_core/`: Home Assistant custom integration
- `tests/components/climate_relay_core/`: backend tests
- `frontend/`: frontend scaffold for later user-facing UI work
- `docs/`: product, architecture, engineering, and planning documents

## Local Development

```bash
uv python install 3.14
uv sync --locked --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python -m build
```

## Home Assistant Test Instance

- The default manual smoke-test target for this repository is
  `http://haos-test.local:8123`.
- User-visible integration changes should be installed and exercised there
  before an increment is considered release-ready.
- This instance is intended for manual verification of install/upgrade flows,
  config and options dialogs, entity naming, and other Home Assistant UI
  behavior that is not reliably proven by Python-only tests.

## Quality Gates

Every backend iteration is expected to satisfy the same checks locally and in
CI:

- formatting
- linting
- tests
- statement and branch coverage
- package build

## Documentation Responsibilities

- `README.md` is reserved for user-focused documentation.
- Every completed iteration must update `README.md` when the user-visible
  installation flow, operating flow, limitations, or supported features change.
- Developer-internal workflow, governance, and implementation material belongs
  in `docs/` and `CONTRIBUTING.md`.

## Distribution Strategy

- The Home Assistant integration is distributed from this repository as an
  `Integration`-type HACS custom repository.
- The future user interface is intended to be distributed as a separate
  `Dashboard`-type HACS custom repository.
- The current `frontend/` directory remains development scaffolding until that
  separate dashboard distribution exists.
- Published versions and test channels follow [release-policy.md](./release-policy.md).
- The release version is taken from
  `custom_components/climate_relay_core/manifest.json`.
- Stable versions are epic-scoped; iteration builds reuse that target version
  with alpha and beta suffixes.
- The release title epic and iteration labels are taken from
  `.github/release-plan.json`.

## Release Readiness Checklist

Before cutting any alpha, beta, or stable release, verify all of the following:

- the exact target commit already has green GitHub checks for formatting,
  linting, tests, coverage, build, hassfest, and HACS validation
- `README.md` on the release target is user-focused and matches the published
  installation path
- `manifest.json`, `strings.json`, and `translations/en.json` are aligned for
  user-visible naming and config labels
- HACS/Home Assistant brand assets render as valid images
- the integration can be installed or upgraded in a real HA instance
- newly introduced config or options flows can be opened, saved, and re-opened
  without frontend errors

## Iteration 1.1 Lessons

The first vertical slice exposed several Home Assistant-specific failure modes
that future increments should proactively guard against:

- HACS repository pages render the published branch or release README, so user
  documentation must be correct on the actually distributed ref, not only on a
  feature branch.
- Invalid or corrupt brand assets can pass unnoticed in the repo while still
  degrading the HA/HACS UI experience.
- Home Assistant options flows are sensitive to schema shape and step design;
  generic list fields, always-visible optional time selectors, and improvised
  conditional fields can break the frontend even when local Python-side
  validation looks correct.
- Conditional inputs in Home Assistant should default to documented canonical
  patterns, especially additional steps in data-entry flows instead of custom
  same-step interactivity assumptions.
- Options-flow behavior must be verified in the real HA UI for save, cancel,
  re-open, and validation-error behavior; mock-heavy Python tests are useful
  but do not capture all frontend/runtime edge cases.
- Release automation promises must track actual completed actions. Do not tell
  users that a follow-up release "will be" created later unless the current
  turn also performs or conclusively verifies that action.
- User-facing naming needs to be reviewed in the real HA UI, not only in code
  and tests.

## Automation Opportunities

- The current test instance already supports reliable manual smoke testing.
- The next sensible automation step is a small scripted smoke-test checklist
  for release candidates:
  install/upgrade in HACS, restart HA, open the integration options flow,
  validate save/cancel paths, and verify the expected entity surfaces.
- If browser automation is introduced later, it should target the dedicated
  test instance rather than the production Home Assistant environment.

## Documentation Map

- User entry point: [README.md](../README.md)
- Discovery: [discovery.md](./discovery.md)
- Requirements: [requirements.md](./requirements.md)
- Verification Matrix: [verification-matrix.md](./verification-matrix.md)
- HA automation strategy: [ha-automation-strategy.md](./ha-automation-strategy.md)
- GUI smoke suites: [gui-smoke-suites/README.md](./gui-smoke-suites/README.md)
- Implementation Plan: [implementation-plan.md](./implementation-plan.md)
- Release Policy: [release-policy.md](./release-policy.md)
- Rules: [rules.md](./rules.md)
- Architecture: [architecture.md](./architecture.md)
- Engineering Standards: [engineering-standards.md](./engineering-standards.md)
- Contribution workflow: [../CONTRIBUTING.md](../CONTRIBUTING.md)
