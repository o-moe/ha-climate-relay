# Requirements

## Product goals

ClimateRelayCore must provide a reusable climate-control backend for Home Assistant that:

- works with generic `climate` entities
- supports optional room-level humidity sensors
- supports optional room-level window contacts
- supports presence-aware global modes using Home Assistant `person` entities
- remains independent from any specific frontend implementation

## Core functional requirements

### Room model

Each room must support:

- exactly one primary `climate` entity
- an optional humidity sensor
- an optional window contact
- room-specific home and away targets
- a room schedule
- manual override behavior settings

### Global mode handling

The system must support:

- `auto`
- `home`
- `away`

When global mode is `auto`, at least one configured person at home means `home`; otherwise the effective state is `away`.

### Window behavior

If a room has a configured window contact, the backend must support:

- a delay before activation
- a configurable open-window action
- restoration of the last valid room state when the window closes

Supported open-window actions must include:

- `off`
- `frost_protection` when supported
- `minimum_temperature`
- `custom_temperature`

### Manual room override

Each room must support manual overrides with configurable termination behavior:

- `duration`
- `next_timeblock`
- `never`

### Scheduling

The backend must support at least these schedule layouts:

- one schedule shared across all days
- one shared weekday schedule plus separate Saturday and Sunday schedules
- a fully individual seven-day schedule

## Non-functional requirements

- Public repository content must remain in English.
- Public repository content must avoid external manufacturer references.
- Public backend behavior must be testable without Home Assistant runtime dependencies.
- CI and local development must run the same locked Python workflow.
