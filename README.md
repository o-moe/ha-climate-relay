# ClimateRelayCore

ClimateRelayCore is a backend-first climate control project for Home Assistant.
It provides a generic thermostat domain model, scheduling rules, presence-aware
mode handling, and room-level automation hooks for optional sensors such as
humidity and window contacts.

## Project goals

- Provide a clean backend architecture that is independent from any specific frontend
- Work with generic Home Assistant `climate` entities and optional supporting sensors
- Keep automation and rule evaluation deterministic, testable, and maintainable
- Use a locked `uv` workflow so local development and CI follow the same build process

## Repository structure

- `custom_components/climate_relay_core/`: Home Assistant custom integration
- `tests/components/climate_relay_core/`: backend tests
- `frontend/`: frontend scaffold for future UI work
- `docs/`: product and technical design documents

## Local development

```bash
uv python install 3.14
uv sync --locked --group dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python -m build
```

## Quality gates

Every backend iteration is expected to satisfy the same checks locally and in CI:

- formatting
- linting
- tests
- statement and branch coverage
- package build

## Documentation

- [Discovery](./docs/discovery.md)
- [Requirements](./docs/requirements.md)
- [Verification Matrix](./docs/verification-matrix.md)
- [Rules](./docs/rules.md)
- [Architecture](./docs/architecture.md)
- [Engineering Standards](./docs/engineering-standards.md)
- [Contributing](./CONTRIBUTING.md)
