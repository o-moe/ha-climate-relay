# GUI Smoke Suites

## Purpose

This directory holds the Home Assistant GUI/UX smoke suites that are executed
per iteration.

Each iteration gets its own suite file instead of appending new checks to one
large shared checklist. This keeps acceptance scope bounded and makes it clear
which user-visible HA behaviors belong to which increment.

## Execution Model

The intended execution order for a real HA acceptance run is:

1. run `scripts/ha_prepare_test_instance.py`
2. run `scripts/ha_smoke_test.py`
3. execute the iteration-specific GUI smoke suite in the Playwright Chromium
   test browser

The API scripts verify environment readiness and backend-facing HA surfaces.
The GUI suite then verifies the narrow HA frontend behaviors that matter for
that iteration.

The Codex in-app browser remains useful for quick inspection, but the current
Home Assistant configuration controls are more reliably automated in Playwright
Chromium. Treat Playwright Chromium as the default execution path for real GUI
smoke runs.

## Naming

- iteration suites: `iteration-<epic>.<iteration>.md`
- optional future epic-wide suites: `epic-<epic>.md`

Examples:

- `iteration-1.1.md`
- `iteration-1.2.md`
- `iteration-2.1.md`

## Authoring Rules

- only include checks for user-visible HA behaviors introduced or changed in
  that iteration
- keep the suite small enough to run as a smoke test, not as broad exploratory
  regression coverage
- prefer stable HA navigation and assertions over visual pixel checks
- include at least one meaningful non-happy-path or validation-path check when
  the iteration changes a user input flow
- state preconditions explicitly, including required API preparation steps
- ensure the browser test user has the permissions required for the HA surfaces
  under test; configuration-page suites require an HA user that can access
  configuration routes
- define expected success signals and explicit failure signals

## Current Suites

- [iteration-1.1.md](./iteration-1.1.md)
- [template.md](./template.md)
