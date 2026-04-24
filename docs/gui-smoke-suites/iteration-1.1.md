# Iteration 1.1 GUI Smoke Suite

## Purpose

This suite verifies the Home Assistant GUI/UX surfaces introduced by iteration
`1.1`: installable integration baseline, global configuration, and the global
presence-control surface.

## Preconditions

1. Run `scripts/ha_prepare_test_instance.py`.
2. Run `scripts/ha_smoke_test.py` with the current iteration-1.1 assertions.
3. Open `http://haos-test.local:8123/` in the Playwright Chromium test
   session.
4. Log in with the dedicated HA test user if required.

## Scope

- Home Assistant app shell reachability after login
- Home Assistant app shell recovery after HA restart
- search-based discovery of Climate Relay UI surfaces
- `Settings > Devices & Services` navigation
- Climate Relay integration visibility
- Climate Relay options flow rendering
- conditional reset-time step behavior
- validation-error rendering for invalid options-flow input
- save/cancel/reopen behavior
- `Presence Control` entity visibility in Home Assistant UI

## Case 1: HA overview is reachable

- Open the HA root URL.
- Wait for the HA loader to finish.
- Expect the browser to land on `/home/overview`.
- Expect a normal HA shell with sidebar and overview content.
- Fail if the browser remains on the login form, a loading spinner, or a blank
  shell.

## Case 2: Devices & Services opens without frontend breakage

- Open `Settings > Devices & Services`.
- Expect the page to render normally.
- Expect no red error toast, blank page, or frozen loading state.

## Case 3: HA session recovers after restart

- Trigger the standard pre-test preparation flow before GUI checks.
- Re-open the HA root URL after the restart completes.
- Wait for the HA loader to finish.
- Expect the browser to return to the HA shell and finally to
  `/home/overview`.
- Fail if the session remains stuck on `Loading data`, falls into a login loop,
  or lands in a broken partial shell.

## Case 4: Search exposes the Presence Control UI surface

- Open the HA search UI with `ControlOrMeta + K`.
- Search for `Climate Relay`.
- Expect a result named `Presence Control`.
- Expect the result context to reference the Climate Relay surface rather than
  an unrelated entity.
- Fail if the search dialog opens but returns no Climate Relay-related entity
  result.

## Case 5: Climate Relay integration card is visible

- On `Devices & Services`, find the `Climate Relay` integration.
- Expect the integration card title to be visible.
- Expect the integration to appear as a normal HA integration card rather than
  a broken placeholder.

## Case 6: Configure opens the global settings form

- Open the `Climate Relay` integration card menu.
- Choose `Configure`.
- Expect the options flow modal to open.
- Expect the following labels to be visible in the initial step:
  - `Tracked presence entities`
  - `Unknown or unavailable presence handling`
  - `Fallback temperature`
  - `Enable daily override reset`
  - `Simulation mode`
  - `Verbose logging`
- Fail if the dialog opens blank, closes immediately, or shows malformed field
  layout.

## Case 7: Reset-time conditional step appears only when enabled

- In the initial step, enable `Enable daily override reset`.
- Continue the flow.
- Expect a dedicated second step that asks for `Daily override reset time`.
- Fail if the second step does not appear or if the control appears broken in
  the first step instead.

## Case 8: Validation error appears when no presence entity is configured

- Open `Configure`.
- Clear all values from `Tracked presence entities`.
- Attempt to continue or save the flow.
- Expect the dialog to remain open.
- Expect an inline validation error instead of silent acceptance.
- Fail if Home Assistant accepts the invalid payload or closes the dialog
  without surfacing the validation issue.

## Case 9: Validation error appears when reset time is missing

- Open `Configure`.
- Enable `Enable daily override reset`.
- Continue to the second step.
- Leave `Daily override reset time` empty.
- Attempt to continue or save.
- Expect the reset-time step to remain open with a visible validation error.
- Fail if the flow silently accepts the empty value or returns to the parent
  page without surfacing the error.

## Case 10: Cancel path leaves settings unchanged

- Open `Configure`.
- Change at least one non-destructive value.
- Cancel the flow.
- Re-open `Configure`.
- Expect the previous persisted values to still be present.

## Case 11: Cancel from the reset-time step discards pending changes

- Open `Configure`.
- Change at least one value in the first step.
- Enable `Enable daily override reset`.
- Continue to the reset-time step.
- Cancel the flow from the second step.
- Re-open `Configure`.
- Expect the original persisted values to still be present.
- Fail if partial pending values from the canceled flow were saved.

## Case 12: Save path persists values and reopens cleanly

- Open `Configure`.
- Set values that are valid for the current test fixture.
- Save the flow.
- Re-open `Configure`.
- Expect the saved values to be rendered again without frontend errors.

## Case 13: Presence Control is visible in HA UI

- Use the HA search UI to reach the visible `Presence Control` surface.
- Expect the label `Climate Relay Presence Control`.
- Expect the current value to match the backend/API smoke expectation.
- Fail if the entity is missing, unnamed, or rendered with broken state text.

## Current Operational Status

- The Playwright Chromium run for iteration 1.1 has a stable HA login path and
  lands on `/home/overview`.
- The Playwright Chromium run can now reach the HA integration pages directly,
  including `/config/integrations/dashboard` and
  `/config/integrations/integration/climate_relay_core`.
- The `Climate Relay` integration detail page is operationalized and the
  visible `Konfigurieren` control opens the options flow through automated
  clicks in Playwright Chromium.
- The initial `Global Settings` step is now fully inspectable and interactable
  through automation:
  - tracked presence entities selection and removal
  - unknown-state handling radios
  - fallback temperature input
  - daily-reset switch
  - simulation-mode switch
  - verbose-logging switch
  - `OK`
- The reset-time conditional step is operationalized end to end:
  - enabling `Enable daily override reset` opens the dedicated second step
  - submitting that step without a time keeps the dialog open
  - Home Assistant renders the validation error
    `Invalid time specified: None`
- The cancel path from the second step is also verified:
  - closing the `Daily Override Reset` step discards pending changes
  - re-opening `Global Settings` shows the daily-reset switch unchecked again
- The empty-presence-entities validation path is verified:
  - removing the only tracked entity leaves the form open
  - Home Assistant renders the validation error
    `Select at least one tracked presence entity.`
- The save and reopen path is verified with a benign round-trip change:
  - `Fallback temperature` was changed from `20` to `21`
  - the flow saved successfully and rendered the HA success dialog
  - re-opening `Global Settings` showed `Fallback temperature` persisted as
    `21`
  - the value was then restored to `20` and verified after another reopen so
    the test fixture remains clean
- The earlier interaction failures were specific to the Codex in-app browser
  session, not to the Climate Relay UI itself. Playwright Chromium is the
  reliable execution path for this suite.
- The HA search path to the `Presence Control` entity dialog remains a valid
  secondary GUI anchor:
  `ControlOrMeta + K` -> search `Climate Relay` -> `ArrowDown` -> `Enter`.

## Failure Signals

- login loop after a successful credential submit
- spinner or loader that never resolves
- missing `Climate Relay` integration card
- configure dialog not opening
- malformed or missing option labels
- invalid payload accepted without validation error
- missing validation for empty reset time when reset is enabled
- save/cancel causing broken navigation
- cancel from the second step persisting partial changes
- reopened form not reflecting persisted data
- missing or broken `Presence Control` entity presentation
