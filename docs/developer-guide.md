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
- The release title iteration label is taken from `.github/release-plan.json`.

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
- Home Assistant options flows are sensitive to schema shape; generic list
  fields and always-visible optional time selectors can break the frontend even
  when local Python-side validation looks correct.
- User-facing naming needs to be reviewed in the real HA UI, not only in code
  and tests.

## Documentation Map

- User entry point: [README.md](../README.md)
- Discovery: [discovery.md](./discovery.md)
- Requirements: [requirements.md](./requirements.md)
- Verification Matrix: [verification-matrix.md](./verification-matrix.md)
- Implementation Plan: [implementation-plan.md](./implementation-plan.md)
- Release Policy: [release-policy.md](./release-policy.md)
- Rules: [rules.md](./rules.md)
- Architecture: [architecture.md](./architecture.md)
- Engineering Standards: [engineering-standards.md](./engineering-standards.md)
- Contribution workflow: [../CONTRIBUTING.md](../CONTRIBUTING.md)
