# Epic 1: Foundation Complete

## Purpose

Epic 1 establishes the installable Home Assistant integration baseline for
Climate Relay. It delivers one area-bound regulation profile, global presence
control, schedule-based target resolution, manual area overrides, simulation
mode, and the Home Assistant service surface needed to operate and verify that
baseline.

Epic 1 also includes the hardening pass completed before Epic 2. That pass
closed the interim-review findings without adding Epic 2 product behavior.

## Delivered Scope

- one installable Home Assistant custom integration instance
- global mode control with `auto`, `home`, and `away`
- automatic presence resolution from configured `person` entities
- configurable unknown/unavailable presence handling
- one area-bound regulation profile anchored to a primary HA `climate` entity
- one integration-owned area climate entity with sparse explanatory attributes
- configurable home and away targets
- one daily local home schedule window
- central effective-regulation resolver for manual override, schedule/global
  mode, and fallback priority
- simulation mode that logs intended climate writes without calling devices
- confirmed actuation boundary for real `climate.set_temperature` writes
- manual area override services for create, replace, clear, and termination
  semantics
- Home Assistant service-boundary validation with operator-readable errors
- timer lifecycle cleanup for repeated schedule and override rescheduling
- API and GUI acceptance runner coverage against the dedicated HA test instance

## Current Limitations

- only one user-configurable area-bound regulation profile is supported
- schedule editing is limited to one daily home window
- manual overrides are service/action based; no dedicated dashboard control is
  shipped yet
- window automation is intentionally not enabled in Epic 1
- global mode and manual override runtime state remain in memory; full durable
  runtime persistence is deferred to the reliability epic
- full multi-area add/edit/remove configuration is deferred to a later epic

## Hardening Decisions

- Effective target selection belongs in pure domain code. The Home Assistant
  climate entity adapts HA state and consumes resolver output.
- A target is treated as applied only after the blocking
  `climate.set_temperature` service call succeeds. Failed writes remain
  retryable.
- Public service handlers convert invalid area/profile references and invalid
  override termination payloads into `HomeAssistantError`.
- Timer rescheduling cancels and replaces the active callback without
  accumulating stale removal hooks.
- Window priority is represented only as a future resolver placeholder. No
  window automation behavior is exposed in Epic 1.

## Verification Evidence

Local verification completed on 2026-04-30:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python -m build
```

Home Assistant acceptance completed on 2026-04-30 against
`http://haos-test.local:8123`:

```bash
uv run python scripts/run_epic_acceptance.py --epic 1 --skip-gui
uv run python scripts/run_epic_acceptance.py --epic 1
```

The acceptance runner installs the final Epic 1 pre-release baseline, prepares
the dedicated HA fixtures, verifies the public service surface through the API,
executes the options-flow GUI regression, and verifies manual override behavior.

## Release Boundary

Epic 1 targets stable version `v0.1.0`. The epic is release-ready after the
hardening branch is merged and GitHub quality gates pass on the exact release
commit. The official Epic 1 closure is the stable GitHub release `v0.1.0` with
release title `Epic 1`.

Release notes should describe Epic 1 as a foundation release and explicitly
state that window automation, durable runtime persistence, full multi-area
configuration, and the dedicated dashboard UI are later-epic work.
