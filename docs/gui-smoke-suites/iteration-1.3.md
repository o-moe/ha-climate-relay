# Iteration 1.3 GUI Smoke Suite

## Purpose

This suite verifies the Home Assistant GUI/UX surfaces introduced by iteration
`1.3`: the first single-area schedule controls, schedule-derived room target
explanation, `next_change_at`, and simulation-mode suppression of climate
writes.

## Preconditions

1. Push the current feature branch so the HA test instance can see the latest
   build.
2. Run `scripts/ha_prepare_test_instance.py`.
3. Run `scripts/ha_smoke_test.py`.
4. Open `http://haos-test.local:8123/` in the Playwright Chromium test
   session.
5. Log in with the dedicated HA admin test user if required.
6. If HACS defaults to an older commit-like version in `Erneut herunterladen`,
   open the version dropdown and explicitly select the intended iteration-1.3
   release before restarting Home Assistant.

Repository-local execution shortcut:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/run_iteration_acceptance.py --iteration 1.3
```

The shortcut installs `v0.1.0-alpha.19` explicitly for
`update.climaterelaycore_update`, following the branch-based alpha verification
path in [release-policy.md](../release-policy.md).

## Scope

- daily home schedule start and end fields in the `Regulation Profile` step
- validation for equal schedule start and end times
- persisted schedule values on re-open
- room climate entity `active_control_context`
- room climate entity `next_change_at`
- simulation-mode dry-run behavior for computed climate target writes

## Case 1: Regulation Profile renders schedule fields

- Open the `Climate Relay` integration detail page.
- Open `Configure`.
- Leave the global step in a valid state and continue to `Regulation Profile`.
- Expect the fields `Home schedule start` and `Home schedule end`.
- Fail if the schedule fields are missing or rendered outside the profile
  dialog.

## Case 2: Equal schedule boundaries are rejected

- Set `Home schedule start` and `Home schedule end` to the same local time.
- Attempt to save the profile.
- Expect the step to remain open.
- Expect the inline validation error
  `Choose different start and end times for the daily home schedule.`
- Fail if the flow accepts a zero-length schedule window.

## Case 3: Scheduled room state exposes next change

- Save a valid profile with different schedule start and end times.
- Set `Presence Control` to `Home`.
- Inspect the resulting Climate Relay room climate entity through HA state or
  the API smoke test.
- Expect `active_control_context` to be `schedule`.
- Expect `next_change_at` to be present as an offset-aware timestamp.
- Fail if the entity has no next-change explanation while presence is home.

## Case 4: Away mode suppresses schedule next change

- Set `Presence Control` to `Away`.
- Inspect the room climate entity.
- Expect the target to resolve to the away target.
- Expect no schedule `next_change_at`, because away presence has priority over
  the room schedule.
- Fail if the schedule continues to explain the target while global away mode
  is active.

## Case 5: Simulation mode suppresses climate writes

- Keep simulation mode enabled.
- Trigger a schedule or global-mode transition that changes the computed room
  target.
- Expect the room entity state to update with the computed target.
- Expect operator logs to mention the suppressed `climate.set_temperature`
  action and intended target.
- Fail if the primary climate target changes through an actual write while
  simulation mode is enabled.

## Failure Signals

- missing schedule fields in `Regulation Profile`
- equal start/end times accepted
- missing `next_change_at` in home/schedule context
- `next_change_at` serialized without date/time/offset information
- simulation mode sends real climate writes instead of logging suppressed
  actions
