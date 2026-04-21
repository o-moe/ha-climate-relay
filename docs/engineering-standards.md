# Engineering Standards

## Purpose

This document defines the non-negotiable engineering expectations for this repository.

## Delivery contract

- Every increment must be developed test-first.
- The first implementation artifact for every required behavior must be a
  failing automated test or executable specification.
- An increment is not complete until all behavior in scope is covered by the
  required tests at the appropriate verification levels.
- An increment is not final until all quality gates are green: formatting,
  linting, automated tests, coverage, and package build.
- An increment is not final until the relevant documentation is created or
  updated together with the code and tests.
- An increment with any user-visible effect is not final until `README.md` is
  updated with the current installation guidance, supported user workflow,
  limitations, and iteration status relevant to that effect.
- `README.md` shall remain user-focused; developer-internal workflow,
  governance, and implementation guidance shall live outside `README.md`.
- Release tags, GitHub releases, pre-releases, and temporary public test
  branches shall follow the documented repository release policy.
- The repository shall maintain explicit release metadata sufficient for
  automated alpha and beta publication, including the manifest version and the
  current iteration label used in release titles.
- Requirement-to-test traceability must remain current for every completed
  increment.
- No alpha, beta, or stable release shall be published until the corresponding
  GitHub quality gates for the exact target commit are green.

## Cross-language code quality principles

- Apply professional, language-specific best practices according to the current
  state of the art for the language, framework, and runtime in use.
- Apply `SOLID` and Clean Code principles across all projects, independent of
  programming language.
- Prefer designs with clear responsibilities, explicit boundaries, low
  coupling, and high cohesion.
- Keep public interfaces intentionally small, stable, and justified by concrete
  use cases.
- Treat readability, maintainability, diagnosability, and safe changeability as
  first-class design goals, not optional refinements.
- Enterprise-grade code quality is the baseline expectation for production code
  and automated tests.

## Source code standards

- Production code must be structured, idiomatic, and maintainable for the
  target language and ecosystem.
- Favor explicit domain modeling, predictable control flow, and strong typing
  or equivalent language-native safety mechanisms where available.
- Avoid unnecessary complexity, hidden side effects, temporal coupling, and
  ambiguous naming.
- Separate domain logic from framework, transport, persistence, and UI
  concerns.
- Error handling, logging, and configuration boundaries must be deliberate,
  testable, and suitable for production operation.
- New abstractions must earn their existence through reduced complexity,
  improved testability, or clearer boundaries.

## Test standards

- Automated tests must meet enterprise-grade standards for correctness,
  maintainability, determinism, and behavioral value.
- Tests must verify externally relevant behavior and not merely mirror the
  implementation structure.
- Test suites should emphasize fast, reliable unit tests for pure logic and add
  integration tests at architectural boundaries.
- Test names, fixtures, and assertions must communicate intent clearly and make
  failures diagnosable.
- Flaky tests, opaque fixtures, and incidental over-mocking are quality defects
  and should be treated as such.
- Where language-specific testing conventions exist, follow the strongest
  professional convention rather than the weakest acceptable one.

## Backend quality rules

- Public backend behavior must be covered by unit tests and/or integration tests.
- Pure rule logic should use `unittest`-style tests wherever possible.
- `pytest` is the standard test runner for local development and CI.
- Statement and branch coverage are mandatory for backend changes.
- Formatting and linting are mandatory for every backend change.

## Home Assistant integration rules

- Home Assistant config and options flows shall use HA-native selectors for
  user-facing inputs instead of generic Python container types.
- Conditional user inputs shall be modeled as conditional form structure where
  feasible, not merely as optional validators on always-visible fields.
- User-facing entity names, states, and config labels shall be defined through
  Home Assistant localization files rather than hardcoded UI strings.
- Changes to `strings.json` and translated runtime strings shall be kept in sync.
- HACS and Home Assistant brand assets must be valid image files and verified
  locally after creation or replacement.
- Any user-visible Home Assistant surface introduced in an increment shall
  receive at least one manual smoke test in a running HA instance before the
  increment is considered release-ready.

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
