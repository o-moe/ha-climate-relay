# Iteration 1.2 GUI Smoke Suite

## Purpose

This suite verifies the Home Assistant GUI/UX surfaces introduced by iteration
`1.2`: the first `Regulation Profile` options-flow step and the resulting
area-bound Climate Relay climate entity.

## Preconditions

1. Push the current feature branch so the HA test instance can see the latest
   build.
2. Run `scripts/ha_prepare_test_instance.py`.
3. Run `scripts/ha_smoke_test.py`.
4. Run `scripts/ha_prepare_no_area_fixture.py`.
5. Open `http://haos-test.local:8123/` in the Playwright Chromium test
   session.
6. Log in with the dedicated HA admin test user if required.
7. If HACS defaults to an older commit-like version in `Erneut herunterladen`,
   open the version dropdown and explicitly select the intended iteration-1.2
   release before restarting Home Assistant.

Repository-local execution shortcut:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/run_iteration_acceptance.py --iteration 1.2
```

The shortcut installs `v0.1.0-alpha.8` explicitly for
`update.climaterelaycore_update`, because the HACS update entity may report a
commit-like `latest_version` that is not the intended iteration-1.2 build.

## Scope

- transition from `Global Settings` into `Regulation Profile`
- regulation-profile form rendering
- selector persistence and suggested values
- required-primary-climate validation
- area-assignment validation
- optional-source clearing behavior
- resulting area-bound climate entity visibility

## Case 1: Global settings advances into Regulation Profile

- Open the `Climate Relay` integration detail page.
- Open `Configure`.
- Leave the global step in a valid state with daily reset disabled.
- Continue the flow.
- Expect the next step title to be `Regulation Profile`.
- Fail if the flow returns directly to `Erfolg` or closes without showing the
  profile step.

## Case 2: Regulation Profile renders the expected fields

- On the `Regulation Profile` step, expect the following fields:
  - `Primary climate entity`
  - `Humidity sensor`
  - `Window contact`
  - `Home target temperature`
  - `Away target type`
  - `Away target value`
- Expect the explanatory text for the primary climate field to mention reuse of
  the Home Assistant area.
- Fail if the dialog opens blank, labels are missing, or the selector layout is
  malformed.

## Case 3: Missing primary climate shows validation error

- Leave `Primary climate entity` empty.
- Fill the remaining required numeric/select fields with valid values.
- Attempt to continue or save the flow.
- Expect the step to remain open.
- Expect an inline error for the primary climate field.
- Fail if the flow accepts the payload without a selected primary climate.

## Case 4: Primary climate without Home Assistant area is rejected

- Choose a climate entity that exists but has no Home Assistant area
  assignment.
- Fill the remaining required fields with valid values.
- Attempt to continue or save the flow.
- Expect the step to remain open.
- Expect the primary climate field to surface the error
  `Assign the primary climate entity to a Home Assistant area first.`
- Fail if the flow accepts an unassigned climate entity.

## Case 5: Suggested values re-open correctly

- Save a valid profile once.
- Re-open `Configure` and move back to `Regulation Profile`.
- Expect the previously saved values to render again:
  - primary climate
  - humidity sensor, if configured
  - window contact, if configured
  - home target temperature
  - away target type
  - away target value
- Fail if previously saved values are missing, reset, or shifted to different
  fields.

## Case 6: Optional source selectors can be cleared

- Start from a saved profile that already has `Humidity sensor` and
  `Window contact` populated.
- Clear one or both optional selectors.
- Save the flow.
- Re-open `Regulation Profile`.
- Expect the cleared optional selectors to remain empty.
- Fail if the old optional entity values reappear after save.

## Case 7: Primary climate cannot be accidentally cleared on an existing profile

- Start from a saved profile.
- Attempt to clear the `Primary climate entity`.
- Save the flow.
- Expect the step to remain open with the primary-climate validation error.
- Fail if the flow silently removes the primary climate or saves a broken
  profile.

## Case 8: Away target type and value persist together

- Save a valid profile with one away-target mode, for example `Absolute
  temperature`.
- Re-open the profile and confirm both the mode and numeric value persisted.
- Change the mode to `Relative delta`, adjust the numeric value, and save.
- Re-open again and confirm the updated mode/value pair persists together.
- Fail if the numeric value persists under the wrong mode or the selector
  reverts unexpectedly.

## Case 9: Resulting profile climate entity is visible in HA

- After saving a valid profile, use HA search or the entities view to find the
  new Climate Relay climate entity.
- Expect one integration-owned climate entity for the configured profile.
- Expect the user-facing name to match the resolved HA area name when one is
  available.
- Expect the climate entity to expose understandable state text and normal HA
  climate presentation.
- Fail if the entity is missing, unnamed, or rendered as a broken placeholder.

## Current Operational Status

- The repository code and tests define iteration `1.2` as a real second step
  in the options flow: `Global Settings` should route into `Regulation
  Profile`.
- The repository also defines two core GUI error paths for that step:
  - missing primary climate -> `Select exactly one primary climate entity.`
  - selected primary climate without area -> `Assign the primary climate entity
    to a Home Assistant area first.`
- Verified on 2026-04-25 in the real HA GUI:
  - HACS `Erneut herunterladen` initially defaulted to commit-like version
    `61a9d13`
  - opening `Benötigst du eine andere Version?` exposed the actual iteration
    releases
  - selecting `v0.1.0-alpha.8` and restarting Home Assistant activated the
    iteration-1.2 build
  - after that change, `Global Settings -> OK` advanced into
    `Regulation Profile` instead of ending at `Erfolg`
  - the live required-field error path is verified:
    `Select exactly one primary climate entity.`
  - the live primary-climate selector is verified and exposes at least two
    HA-area-bound climate entities in the fixture:
    `Living Room` and `Office`
  - the saved-selector reopen path is verified:
    after saving `Office`, re-opening `Configure` and returning to
    `Regulation Profile` showed `Office` prefilled again
  - the optional-source persistence path is verified:
    after saving `Office Humidity` and `Office Window`, both selectors reopened
    prefilled on the next `Regulation Profile` visit
  - the optional-source clearing path is verified:
    clearing `Humidity sensor` and `Window contact`, saving, and reopening left
    both selectors empty
  - the dedicated no-area fixture is now automation-managed:
    `scripts/ha_prepare_no_area_fixture.py` creates or reuses a separate
    `Virtual Climate` entry titled `No Area Fixture` and keeps its device
    intentionally unassigned to any HA area
  - the dedicated no-area fixture is verified in the real browser flow:
    the `Primary climate entity` picker shows `No Area Fixture` without an area
    subtitle, and submitting the form renders
    `Assign the primary climate entity to a Home Assistant area first.`
  - saving a valid profile with `Office` as the primary climate succeeded
  - the integration surface expanded from `2 Geräte` to `3 Geräte`
  - a new area-bound device `Küche` appeared on the integration page after save
- This means iteration `1.2` is now partially operationalized end to end in the
  real HA GUI:
  - step transition verified
  - required-primary-climate validation verified
  - no-area validation verified
  - selector reopen/persistence verified
  - optional-source clearing verified
  - positive save path verified
  - resulting area-bound surface growth verified
- Still open for later hardening:
  - no additional iteration-1.2 fixture blockers remain

## Failure Signals

- `Configure` still ends at `Erfolg` after the global step
- missing `Regulation Profile` title or malformed selector layout
- missing validation for empty primary climate
- missing validation for climate entities without HA area assignment
- cleared optional selectors reappearing after save
- away-target mode and value drifting out of sync after reopen
- missing or broken integration-owned climate entity after valid save
