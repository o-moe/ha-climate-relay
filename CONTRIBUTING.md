# Contributing

## Engineering baseline

These rules are repository-wide and intended to remain stable over time.

- Develop every increment test-first.
- Start each required behavior with a failing automated test or executable
  specification.
- Apply professional, language-specific engineering practices according to the
  current state of the art.
- Apply `SOLID` and Clean Code principles independent of programming language.
- Treat enterprise-grade source code and test quality as the baseline
  expectation.
- Public Python behavior must be protected by unit tests and/or integration tests.
- Prefer `unittest` for pure rule and behavior tests.
- Use `pytest` as the standard test runner.
- Run statement and branch coverage for backend changes.
- Keep the Python toolchain minimal and reproducible.
- Use `ruff` for formatting and linting.
- Use `pyproject.toml` and `uv.lock` as the source of truth for Python tooling.
- Keep Home Assistant integration code aligned with UI-configurable integration practices.
- For Home Assistant work, always prefer official, documented, canonical Home
  Assistant patterns over custom or improvised solutions, especially in
  config/options flows, selectors, entities, and other user-facing UI.
- Keep `README.md` user-focused and update it in every iteration that changes
  installation, operation, supported user-facing behavior, or known
  limitations.
- Move developer-internal repository guidance into `docs/` or
  developer-oriented contribution documents rather than expanding `README.md`
  with internal workflow content.
- Follow the repository release-channel rules in
  `docs/release-policy.md` instead of using ad hoc tags or exposing arbitrary
  feature branches as long-lived user-facing install targets.
- Before publishing alpha, beta, or stable releases, keep
  `custom_components/climate_relay_core/manifest.json` and
  `.github/release-plan.json` aligned with the intended epic, iteration, and
  stable target version.
- Do not publish any release or pre-release until the exact target commit has
  green GitHub checks and the relevant Home Assistant smoke tests have been
  completed for newly changed user-facing surfaces.

## Standard commands

```bash
uv python install 3.14
uv sync --locked --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python -m build
```

## Testing policy

- Public backend behavior requires tests.
- Rule evaluation code should be covered with focused unit tests.
- Integration entry points and config flows should gain integration-style tests as they evolve.
- Tests should verify behavior, remain deterministic, and be easy to diagnose
  when they fail.
- New backend features are not complete until the exposed behavior is covered by
  tests, all quality gates are green, and the related documentation is updated.
- User-visible backend features are not complete until the matching user-facing
  README content is updated as well.
