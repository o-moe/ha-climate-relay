# Iteration 1.4 GUI Smoke Suite

## Purpose

This suite verifies the Home Assistant GUI/UX surfaces introduced by iteration
`1.4`: area-scoped manual override actions, replacement and clearing behavior,
temporary override end-time explanation, and return to scheduled control.

## Preconditions

1. Push the current feature branch so the HA test instance can see the latest
   build.
2. Publish the intended alpha pre-release for the exact branch commit.
3. Run `scripts/ha_prepare_test_instance.py`.
4. Run `scripts/ha_smoke_test.py`.
5. Open `http://haos-test.local:8123/` in the Playwright Chromium test
   session.
6. Log in with the dedicated HA admin test user if required.
7. If HACS defaults to an older commit-like version in `Erneut herunterladen`,
   open the version dropdown and explicitly select the intended iteration-1.4
   release before restarting Home Assistant.

Repository-local execution shortcut:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/run_iteration_acceptance.py --iteration 1.4
```

The shortcut installs `v0.1.0-alpha.20` explicitly for
`update.climaterelaycore_update`, following the alpha verification path in
[release-policy.md](../release-policy.md).

## Scope

- `climate_relay_core.set_area_override`
- `climate_relay_core.clear_area_override`
- duration, fixed-clock, next-timeblock, and persistent termination semantics
- replacement of an existing override by a newer override for the same area
- area climate entity `active_control_context`
- area climate entity `override_ends_at`

## Case 1: Manual override service is available

- Open Developer Tools > Actions.
- Search for `Climate Relay`.
- Expect actions for setting presence control, setting an area override, and
  clearing an area override.
- Fail if area override actions are missing or exposed outside the integration
  domain.

## Case 2: Duration override exposes end time

- Call `climate_relay_core.set_area_override` for the configured area/profile
  with `termination_type = duration`, `duration_minutes = 45`, and an absolute
  target temperature.
- Inspect the Climate Relay area climate entity.
- Expect `active_control_context` to be `manual_override`.
- Expect `override_ends_at` to be present as an offset-aware timestamp.
- Fail if the target remains schedule-controlled or the end time is missing.

## Case 3: Replacement keeps one active intent

- While Case 2 is still active, call `set_area_override` again for the same
  area/profile with a different target and termination.
- Inspect the area climate entity.
- Expect the newer target and newer termination explanation.
- Fail if the old target remains active or multiple override states are visible.

## Case 4: Clear override returns to schedule

- Call `climate_relay_core.clear_area_override` for the same area/profile.
- Inspect the area climate entity.
- Expect `active_control_context` to return to `schedule` when the primary
  climate entity is available.
- Expect `override_ends_at` to be absent.
- Fail if the manual target remains active after clearing.

## Case 5: Fixed-clock next occurrence is explainable

- Call `set_area_override` with `termination_type = until_time` using a local
  wall-clock time that has already passed today.
- Inspect `override_ends_at`.
- Expect the date to be the next occurrence of that wall-clock time, not an
  immediate expiry.
- Fail if the override disappears immediately.

## Failure Signals

- missing area override actions
- override action accepts an incomplete termination definition
- active override does not set `manual_override` context
- temporary override does not expose `override_ends_at`
- replacement leaves stale target or stale end-time data
- clear action fails to remove the override
