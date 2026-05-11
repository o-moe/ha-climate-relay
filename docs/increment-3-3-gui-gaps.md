# Increment 3.3 GUI Gaps

## Scope

Increment 3.3 starts the first GUI vertical slice with a minimal
`climate-relay-card` custom card. The card renders activated Climate Relay room
climate entities from backend-owned Home Assistant state and can call the
existing backend override services.

Increment 3.3a extends that slice with the smallest frontend-facing backend
contract needed to activate one room from the card. It adds narrow WebSocket
commands for candidate discovery and one-room activation, while still avoiding
a broad backend API, config subentries, a new persistence format, or an Options
Flow UX expansion.

Increment 3.3b adds minimal schedule editing for the currently supported daily
home window. It keeps the backend authoritative for validation, persistence,
reload, and schedule evaluation.

Increment 3.3c adds minimal room action capability projection on the room
climate entity. The custom card now renders Override/Resume controls from
backend-projected action state instead of assuming that a fixed override action
is always available.

## Implemented frontend slice

- Lovelace element: `climate-relay-card`
- Lovelace type: `custom:climate-relay-card`
- State source: Home Assistant climate entities exposing
  `primary_climate_entity_id`
- Visible room tile fields:
  - room display name from `friendly_name`
  - current temperature from `current_temperature`
  - target temperature from `temperature`
  - `active_control_context`
  - `degradation_status`
  - `next_change_at`
  - `override_ends_at`
  - `supported_room_actions`
  - `can_set_override`
  - `can_clear_override`
  - `manual_override_active`
  - `manual_override_target_temperature`
  - `manual_override_ends_at`
  - `manual_override_termination_type`
  - `schedule_home_start`
  - `schedule_home_end`
- Override and resume buttons call the existing
  `climate_relay_core.set_area_override` and
  `climate_relay_core.clear_area_override` services.
- The set-override button is shown only when `can_set_override` is true and is
  labeled `Override for 1h` because this increment still supports only the
  minimal fixed-duration card action.
- The resume button is shown only when `can_clear_override` is true.
- Candidate discovery uses the `climate_relay_core/room_candidates` WebSocket
  command and returns area/climate candidates with backend-owned availability
  reasons. The command is admin-only because it supports room configuration and
  exposes entity/area setup data.
- Room activation uses the `climate_relay_core/activate_room` WebSocket command
  and persists exactly one activated room through the existing `rooms` options
  shape. The command is admin-only because it mutates persistent config entry
  options.
- Schedule editing uses the `climate_relay_core/update_room_schedule`
  WebSocket command and updates only `schedule_home_start` and
  `schedule_home_end` for an already activated room. The command is admin-only
  because it mutates persistent config entry options.

## Remaining backend-facing gaps

### Room activation

Increment 3.3a implements the first activation path. The backend lists climate
candidates from Home Assistant state/entity registry context, marks missing
areas, duplicate primary climates, and duplicate HA areas as unavailable, and
activates one eligible primary climate through `room_management.activate_room`.
Candidate discovery excludes Climate Relay's own virtual room climate entities,
including state-machine entities that expose `primary_climate_entity_id` and
registry entries owned by this integration.

Activation updates config entry options through Home Assistant's config-entry
update mechanism. Runtime and entity refresh are handled by the existing config
entry update listener rather than a second direct reload in the WebSocket
handler.

Still open: richer room configuration after activation, optional humidity/window
selection, target-temperature configuration, room disable/update operations, and
stable profile-ID migration.

### Schedule editing

Increment 3.3b implements the minimal daily-window schedule editor. The backend
validates required start/end values, rejects invalid time values, rejects
identical start/end times, normalizes accepted values to ISO time strings with
seconds, rejects non-zero seconds or microseconds, and preserves the existing
flat `rooms` persistence shape. The accepted precision is minute-level:
`HH:MM` and `HH:MM:00` are accepted and persisted as `HH:MM:00`.

Still open: weekly schedules, multiple daily timeblocks, target-temperature
configuration in the schedule editor, richer schedule previews, and reload
persistence coverage in real-HA custom-card acceptance.

### Quick override

Increment 3.3c projects the minimal override capabilities required by the card
through room climate entity attributes. The card can set a one-hour duration
override through the existing service only when `can_set_override` is true. It
renders active manual override state from backend attributes and does not
evaluate the override lifecycle itself.

The existing override services currently accept an area ID, profile ID, or
primary climate entity ID through the `area_id` service field. The card uses the
room primary climate entity ID as a transitional room reference until a
dedicated stable room action reference exists.

Still open: free duration selection, fixed end time, until next schedule
change, until-cleared UI, structured frontend-facing service errors, and target
temperature defaults.

### Clear override / resume schedule

The card can call the existing clear service using the room primary climate
entity ID only when `can_clear_override` is true. Clearing remains backend-owned:
the frontend does not infer whether an override exists from
`active_control_context` or timestamps.

## Follow-up boundary

The next backend work should implement only the missing frontend-facing
operations discovered by this slice: room update, room disable, richer room
configuration, and persistence/reload acceptance coverage.
It should not return to broad backend-only room-management abstraction.

The existing `scripts/run_epic_acceptance.py` acceptance runner now includes an
Increment 3 schedule-editing and Override/Resume path (`--epic 3`) that reuses the existing HA
preparation and Playwright mechanisms. It injects the built custom card into
the HA frontend, edits schedule start/end through the GUI, sets a one-hour
override through the card, verifies backend-projected override attributes
through the HA API, clicks `Resume schedule`, and verifies that the manual
override is no longer active. It does not yet perform a config-entry
reload/restart persistence check for the custom-card flow. The runner loads the
ignored local `.env.local` file for `HOME_ASSISTANT_TOKEN` when the variable is
not already exported.

The schedule-editing path passed locally on 2026-05-10 against
`v0.2.0-alpha.38` on the dedicated HA test instance.
