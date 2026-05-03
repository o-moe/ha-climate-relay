# Frontend Interaction Model

## Purpose

This document defines the target interaction model for the Climate Relay
frontend. It constrains future frontend and backend work so that room-level
climate behavior is designed from user tasks rather than from backend
implementation artifacts.

## UI surfaces

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
