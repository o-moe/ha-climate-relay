# Contributing

## Engineering baseline

These rules are repository-wide and intended to remain stable over time.

- Public Python behavior must be protected by unit tests and/or integration tests.
- Prefer `unittest` for pure rule and behavior tests.
- Use `pytest` as the standard test runner.
- Run statement and branch coverage for backend changes.
- Keep the Python toolchain minimal and reproducible.
- Use `ruff` for formatting and linting.
- Use `pyproject.toml` and `uv.lock` as the source of truth for Python tooling.
- Keep Home Assistant integration code aligned with UI-configurable integration practices.

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
- New backend features are not complete until the exposed behavior is covered by tests.
