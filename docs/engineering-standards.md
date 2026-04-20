# Engineering Standards

## Purpose

This document defines the non-negotiable engineering expectations for this repository.

## Backend quality rules

- Public backend behavior must be covered by unit tests and/or integration tests.
- Pure rule logic should use `unittest`-style tests wherever possible.
- `pytest` is the standard test runner for local development and CI.
- Statement and branch coverage are mandatory for backend changes.
- Formatting and linting are mandatory for every backend change.

## Tooling baseline

The Python toolchain for this repository is intentionally small:

- `uv` for environment management and command execution
- `ruff` for formatting and linting
- `pytest` and `pytest-cov` for tests and coverage
- `build` for package builds

Standard commands:

- `uv python install 3.14`
- `uv sync --locked --group dev`
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- `uv run python -m build`

## Repository policy

- Public repository content must remain in English.
- Public repository content must avoid external manufacturer references.
- The local developer workflow and CI workflow must use the same locked dependency process.
- The backend architecture should remain frontend-agnostic and keep domain logic separate from Home Assistant adapters.
