# Frontend Interaction Model

## Purpose

This document defines the target interaction model for the Climate Relay
frontend. It constrains future frontend and backend work so that room-level
climate behavior is designed from user tasks rather than from backend
implementation artifacts.

## UI surfaces

### Increment 3.3 prototype card

The first GUI vertical slice uses a minimal Lovelace custom card named
`climate-relay-card` with Lovelace type `custom:climate-relay-card`.

The card is a validation scaffold for the room overview. It reads activated
room climate entities from Home Assistant state when they expose
`primary_climate_entity_id` and renders backend-owned attributes. It may call
existing backend services for quick override and resume actions, but it shall
not evaluate rules, schedules, fallback state, or degraded-state semantics.

Increment 3.3a adds the first room activation flow to this prototype. The card
loads backend-owned room candidates through WebSocket, renders an `Add room`
section, activates one eligible candidate through a backend-owned operation,
and then waits for Home Assistant state to expose the new room tile.

Increment 3.3b adds minimal editing for the initially supported daily schedule
window. The card renders backend-owned `schedule_home_start` and
`schedule_home_end` room attributes, collects edited start/end values, and
saves through the admin-only backend WebSocket schedule update operation.

Increment 3.3c adds minimal room action capability projection through room
climate entity attributes. The card renders a fixed-duration `Override for 1h`
action only when `can_set_override` is true, renders `Resume schedule` only
when `can_clear_override` is true, and displays active manual override target
and end values from backend-owned attributes. The card still uses the existing
override services; it does not evaluate override lifecycle, schedule state, or
rule priority. For this prototype, `can_set_override` means the backend exposes
the minimal `set_manual_override_duration` action for the room; it is not yet a
complete policy for every supported override termination variant.

### Room overview

The room overview is the primary daily-use surface.

Each room tile shall show:

- room name from Home Assistant area
- current temperature if available
- current target temperature
- active control context
- next scheduled change if applicable
- active override end if applicable
- window state if configured
- humidity if configured
- degraded or fallback indication if applicable

The room tile shall expose quick actions for:

- opening room detail
- setting a temporary manual override
- clearing an active override / resuming schedule

### Room detail

The room detail view shall show:

- current measured state
- effective target
- reason chain for the effective target
- schedule preview
- quick override controls
- room configuration entry point
- sensor/status diagnostics relevant to the room

The reason chain shall explain the current effective target in user-facing
terms, for example:

- schedule active
- manual override active until a local time
- window override active
- global away mode active
- fallback active because required input is unavailable

### Room management

Room management shall allow users to:

- activate an eligible Home Assistant area for Climate Relay
- select the primary `climate` entity when more than one candidate exists
- configure home and away targets
- configure the initially supported schedule model
- select optional window contact
- select optional humidity sensor
- configure window behavior
- disable a room again

Room management belongs to the custom frontend. The Home Assistant options flow
may temporarily provide equivalent configuration only as bootstrap scaffolding.

The Increment 3.3a room-management subset supports only activation of one
eligible primary climate candidate with backend defaults. It intentionally does
not configure optional sensors, window behavior, targets, or schedules.

### Schedule editing

The first frontend slice shall include schedule editing for the initially
supported schedule model.

The schedule editor shall:

- operate per room
- show the current day schedule visually or structurally
- allow editing time boundaries and target temperatures
- validate continuity and non-overlap through backend-owned validation
- save through backend-owned actions or configuration APIs

The frontend shall not evaluate schedule behavior independently. It may render
schedule data and collect user input, but backend-owned logic remains
authoritative.

The Increment 3.3b prototype intentionally supports only one daily home window
with editable start and end time. It does not add weekly schedules, multiple
timeblocks, target-temperature editing, or drag-and-drop editing.

### Manual override

A manual override flow shall allow:

- target temperature selection
- termination by duration
- termination until fixed local time
- termination at next scheduled change
- persistent override until cleared

The frontend shall invoke backend-owned actions for override creation and
clearing.

The Increment 3.3c prototype supports only the minimal duration action exposed
to the card: a fixed one-hour override using the existing set service and a
resume action using the existing clear service. Free duration selection, fixed
end time, next-schedule-change termination, until-cleared UI, richer room
configuration, room update/disable, and persistence/reload acceptance remain
future work even though the backend service can already represent more
termination types.

### Global mode

The global mode control shall be visible from the primary frontend surface and
support:

- `auto`
- `home`
- `away`

The UI shall distinguish selected global mode from effective room context.

## Interaction guardrails

- Normal room operation shall not require Home Assistant service calls.
- Raw entity IDs should not be exposed in daily-use views unless necessary for
  diagnostics.
- Backend-owned terms may appear in developer docs, but user-facing labels shall
  prefer user concepts such as room, schedule, override, window open, and away
  mode.
- Frontend actions shall be idempotent or safely repeatable where feasible.
