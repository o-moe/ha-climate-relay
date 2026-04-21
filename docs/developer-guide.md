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
