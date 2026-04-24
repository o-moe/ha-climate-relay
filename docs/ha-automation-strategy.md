# Home Assistant Automation Strategy

## Purpose

This document evaluates how manual Home Assistant acceptance can be reduced or
replaced for this repository.

The current cost imbalance is clear:

- implementation changes are often small
- real Home Assistant acceptance currently dominates cycle time
- Python-only tests already cover backend behavior well, but not the real HA UI
  and distribution surfaces

## Current Baseline

As of 2026-04-23, the repository already has strong local automated evidence:

- `uv run pytest` passes
- coverage remains above the required threshold
- backend logic, config flow branching, runtime services, and entity exposure
  are already heavily exercised in-process

What is still mostly manual:

- install or upgrade behavior in a real HA instance
- config and options flow rendering in the HA frontend
- entity naming and placement as rendered by HA
- future HACS install and upgrade validation

## Constraint Summary

The dedicated HA smoke-test target `http://haos-test.local:8123` is reachable
and now supports both API smoke tests and real browser automation.

Current browser finding as of 2026-04-24:

- the dedicated admin test user `codex` can log in successfully
- the Codex in-app browser is still useful for inspection, but some HA
  configuration controls do not react reliably there
- the same flows work correctly in an isolated Playwright Chromium session
- the browser automation path is therefore viable, but it should use
  Playwright Chromium as the primary execution surface

This means GUI automation is no longer blocked by missing credentials. The
remaining practical constraint is choosing the reliable browser harness.

## Automation Options

### Option 1: Strengthen local HA-facing tests further

Description:
Extend the existing Python integration tests to cover more Home Assistant-facing
shapes and regression cases.

Strengths:

- fastest to run
- fully autonomous in the repository
- no external credentials or HA instance required

Weaknesses:

- does not prove real frontend rendering
- does not prove HACS installation or upgrade behavior
- does not catch browser-specific HA form regressions

Assessment:
Necessary, but it does not solve the expensive manual acceptance problem by
itself.

### Option 2: API-driven smoke tests against the dedicated HA test instance

Description:
Drive the dedicated HA instance through authenticated REST and WebSocket calls
instead of the browser wherever possible.

Typical checks:

- integration is installed
- expected config entry exists
- expected entities exist with the right names and state shape
- expected services are registered
- service calls produce the expected state transitions

Strengths:

- much faster and more stable than UI automation
- ideal for regression smoke tests after each iteration
- good fit for backend-first verification

Weaknesses:

- needs a long-lived access token or equivalent stable auth mechanism
- still does not prove UI rendering details
- HACS flows remain outside the main coverage path

Assessment:
This is the highest-value next step. It removes most of the manual acceptance
that is currently wasted on checking state, entities, and service behavior.

### Option 3: Browser smoke tests against the dedicated HA instance

Description:
Use Codex browser automation to exercise the HA frontend directly for selected
critical flows.

Best suited for:

- open integration options flow
- save and cancel paths
- validation error rendering
- entity labels and placement checks
- later, selected dashboard-card checks

Strengths:

- directly validates the real HA UI
- catches the exact class of frontend/runtime regressions that Python tests miss

Weaknesses:

- slower and more brittle than API checks
- still sensitive to browser-harness differences
- should be kept to a small smoke-test checklist, not broad regression coverage

Assessment:
This should exist, but only as a thin top layer above API-driven smoke tests.
It is the wrong primary tool for every iteration check.

### Option 4: Disposable end-to-end HA environment

Description:
Spin up a fully controlled HA test environment per branch or per verification
run, install the integration there, then run smoke tests against it.

Strengths:

- strongest reproducibility
- avoids drift in the long-lived shared test instance
- best long-term base for release verification

Weaknesses:

- highest setup cost
- requires infrastructure work beyond the current repository baseline
- may be excessive before the feature surface grows further

Assessment:
Good medium-term target, but not the first move.

## Recommended Strategy

Use a two-layer approach:

1. Make API-driven HA smoke tests the default acceptance path for iteration work.
2. Add a very small browser-driven checklist only for UI-specific behaviors.

This gives the best return:

- most acceptance moves from manual HA clicking into stable automation
- only the truly UI-specific risk remains in browser smoke tests
- the dedicated HA instance can still be reused instead of building a full
  disposable environment immediately

## Concrete Next Steps

### Immediate

- create a dedicated automation credential for the HA test instance
- prefer a long-lived access token for smoke-test scripts
- define one stable test fixture installation in HA that Codex can rely on
- implement a repository-local smoke-test script for:
  - config entry presence
  - expected entity surface
  - expected service registration
  - one service-driven state transition

Current repository entry point:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/ha_smoke_test.py
```

Recommended pre-test preparation:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/ha_prepare_test_instance.py
uv run python scripts/ha_smoke_test.py
```

Verified on 2026-04-23 against `http://haos-test.local:8123`:

- `ha_prepare_test_instance.py` completed successfully end-to-end
- the script correctly handled the Home Assistant restart handshake even when
  the restart service answered with HTTP `504`
- both update entities finished in the expected up-to-date state
- `ha_smoke_test.py` completed successfully after the restart
- the browser session could re-enter Home Assistant and return to
  `/home/overview`

Useful stricter examples:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/ha_smoke_test.py \
  --expect-select-friendly-name 'Climate Relay Presence Control' \
  --expect-effective-presence away \
  --expect-unknown-state-handling away \
  --expect-simulation-mode on \
  --expect-fallback-temperature 20.0
```

For later area-centric increments, tighten the room surface explicitly:

```bash
uv run python scripts/ha_smoke_test.py --expect-room-count 1
```

### Next

- keep the browser checklist intentionally short and run it in Playwright
  Chromium
- operationalize the iteration-specific suites as executable Playwright runs,
  starting with the Climate Relay options flow:
  - open integration
  - open configure
  - verify expected fields render
  - verify non-happy-path validation
  - verify save and cancel paths
  - verify `Presence Control` surface in HA UI

Verified GUI/UX smoke coverage for iteration 1.1 in Playwright Chromium:

1. Login and app-shell reachability
2. Open `Climate Relay` integration detail page
3. Open `Configure`
4. Verify the global settings form renders the expected fields
5. Toggle the daily reset option and verify the second-step reset-time flow
6. Verify missing reset time renders the validation error
7. Verify cancel from the second step discards pending changes
8. Verify empty tracked presence entities renders the validation error
9. Verify save path persists a benign field change and re-opens cleanly
10. Re-open `Configure` and verify canceled values were not persisted

Recommended GUI assertions:

- no red error toasts
- no blank modal or stuck spinner
- expected translated field labels are visible
- second-step flow appears only when the reset option is enabled
- validation errors are rendered inline for invalid payloads
- save returns control to the HA page without broken navigation
- persisted values match the previously submitted configuration

### Later

- evaluate whether HACS install and upgrade should be automated in the same
  environment or in a disposable release-verification environment

## Decision

The repository should not continue to treat real-HA acceptance as mainly manual.
The next implementation step should be authenticated API smoke testing against
the dedicated HA instance, with browser automation added only for the narrow HA
frontend behaviors that cannot be proven through the API.

## Iteration Workflow

For future iterations, the default acceptance path should be:

1. implement and verify the code change locally
2. run `ha_prepare_test_instance.py`
3. run `ha_smoke_test.py`
4. run a narrow browser smoke suite for the user-visible HA surface changed in
   that iteration

This means GUI/UX acceptance should be created incrementally together with each
iteration rather than postponed into a later manual-only phase.

The iteration-specific GUI suite files live under
[`docs/gui-smoke-suites/`](./gui-smoke-suites/README.md).
