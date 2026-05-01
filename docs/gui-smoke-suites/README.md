# GUI Smoke Suites

## Purpose

This directory holds Home Assistant GUI/UX smoke suites for accepted epic
release boundaries.

During active development, narrow executable checks may still be added
incrementally. At epic closure, the lasting documentation is consolidated into
one epic-level suite so release review focuses on the delivered epic rather
than the sequence of implementation iterations.

## Execution Model

The intended execution order for a real HA acceptance run is:

1. run `scripts/ha_prepare_test_instance.py`
2. run `scripts/ha_smoke_test.py`
3. execute the epic GUI smoke suite in the Playwright Chromium test browser

If an epic suite depends on a special HA fixture, add that preparation step
explicitly before the GUI suite. Epic 1 uses
`scripts/ha_prepare_no_area_fixture.py` to guarantee a dedicated area-less
`Virtual Climate` source for the `primary_climate_area_required` validation
path.

The API scripts verify environment readiness and backend-facing HA surfaces.
The GUI suite then verifies the narrow HA frontend behaviors that matter for
that epic release boundary.

The Codex in-app browser remains useful for quick inspection, but the current
Home Assistant configuration controls are more reliably automated in Playwright
Chromium. Treat Playwright Chromium as the default execution path for real GUI
smoke runs.

Current Epic 1 regression entry point:

```bash
export HOME_ASSISTANT_TOKEN='<long-lived-token>'
uv run python scripts/run_epic_acceptance.py --epic 1
```

- when an epic adds or changes a GUI flow, expand its acceptance runner in
  parallel with the implementation
- keep the epic suite and runner aligned, so the documented smoke cases are
  directly executable
- install the intended build explicitly when HACS `latest_version`
  does not identify that build
- prefer failing the CLI run over silently downgrading checks, so regression
  status is obvious from one command

## Naming

- epic suites: `epic-<epic>.md`

Examples:

- `epic-1.md`
- `epic-2.md`

## Authoring Rules

- only include checks for user-visible HA behaviors delivered by that epic
- keep the suite small enough to run as a smoke test, not as broad exploratory
  regression coverage
- prefer stable HA navigation and assertions over visual pixel checks
- include at least one meaningful non-happy-path or validation-path check when
  the epic changes a user input flow
- state preconditions explicitly, including required API preparation steps
- ensure the browser test user has the permissions required for the HA surfaces
  under test; configuration-page suites require an HA user that can access
  configuration routes
- define expected success signals and explicit failure signals

## Current Suites

- [epic-1.md](./epic-1.md)
