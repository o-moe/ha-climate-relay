# Epic 1 GUI Smoke Suite

## Purpose

This suite verifies the Home Assistant GUI/UX surfaces delivered by Epic 1 as a
single release boundary:

- integration options flow
- single regulation-profile setup
- validation errors for invalid profile input
- schedule field persistence
- daily override reset option flow
- public manual-override service surface through HA/API smoke checks
- manual override context and end-time explanation on the area climate entity

## Preconditions

1. The intended Epic 1 release candidate is installed on
   `http://haos-test.local:8123`.
2. `HOME_ASSISTANT_TOKEN` is available, either exported in the shell or stored
   in ignored `.env.local`.
3. The dedicated `codex` HA test user can access configuration pages.
4. The dedicated no-area fixture exists or can be prepared by
   `scripts/ha_prepare_no_area_fixture.py`.

Repository-local execution:

```bash
uv run python scripts/run_epic_acceptance.py --epic 1 --skip-gui
uv run python scripts/run_epic_acceptance.py --epic 1
```

For release review, the result is treated as Epic 1 acceptance evidence.

## Cases

### 1. Global Options Flow

- Open the Climate Relay integration options flow.
- Verify global settings render with the expected HA-native selectors.
- Enable and disable the daily override reset option.
- Verify missing required reset time renders an inline validation error.
- Verify canceling from the reset-time step does not persist pending changes.
- Save valid global settings and reopen the flow successfully.

### 2. Regulation Profile Options Flow

- Open the regulation-profile options step.
- Save a valid primary-climate-backed profile with home/away targets and daily
  schedule times.
- Reopen the flow and verify persisted values.
- Select the dedicated no-area fixture.
- Expect the inline validation error requiring the primary climate entity to
  belong to a Home Assistant area.
- Correct the validation error and save successfully.

### 3. Public Action Surface

- Verify `climate_relay_core.set_global_mode` exists.
- Verify `climate_relay_core.set_area_override` exists.
- Verify `climate_relay_core.clear_area_override` exists.
- Fail if the public service surface is missing or drifts away from the
  documented schema.

### 4. Manual Override Behavior

- Call `set_area_override` for the configured area/profile with a duration
  termination.
- Verify the area climate entity exposes `active_control_context` as
  `manual_override`.
- Verify temporary overrides expose offset-aware `override_ends_at`.
- Call a second override for the same area/profile and verify replacement
  semantics.
- Call `clear_area_override` and verify the entity returns to scheduled control.

## Failure Signals

- options flow cannot be opened, saved, canceled, or reopened
- validation errors do not render inline
- GUI automation exits zero after Playwright-reported errors
- public service/action schemas are missing or incomplete
- manual override state does not appear on the area climate entity
- temporary override end time is missing or malformed
- clear override leaves stale manual-override state
- GUI failure screenshots are not reported or written under
  `artifacts/acceptance/`
