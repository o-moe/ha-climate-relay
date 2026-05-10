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

Schedule editing remains a visible gap until backend-owned schedule validation
and schedule update operations exist. Action capability projection also remains
open; the quick override control is still a fixed one-hour scaffold over the
existing services.

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

### Manual override

A manual override flow shall allow:

- target temperature selection
- termination by duration
- termination until fixed local time
- termination at next scheduled change
- persistent override until cleared

The frontend shall invoke backend-owned actions for override creation and
clearing.

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
