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
- Quick override and resume buttons call the existing
  `climate_relay_core.set_area_override` and
  `climate_relay_core.clear_area_override` services.
- The quick override button is explicitly labeled as `Override 1h` because the
  current card uses a temporary fixed one-hour duration scaffold instead of a
  complete override flow.
- Candidate discovery uses the `climate_relay_core/room_candidates` WebSocket
  command and returns area/climate candidates with backend-owned availability
  reasons.
- Room activation uses the `climate_relay_core/activate_room` WebSocket command
  and persists exactly one activated room through the existing `rooms` options
  shape.

## Remaining backend-facing gaps

### Room activation

Increment 3.3a implements the first activation path. The backend lists climate
candidates from Home Assistant state/entity registry context, marks missing
areas, duplicate primary climates, and duplicate HA areas as unavailable, and
activates one eligible primary climate through `room_management.activate_room`.

Still open: richer room configuration after activation, optional humidity/window
selection, target-temperature configuration, room disable/update operations, and
stable profile-ID migration.

### Schedule editing

The frontend still lacks backend-owned schedule validation and schedule update
operations. The card therefore documents the gap instead of implementing a fake
schedule editor or duplicating schedule validation in TypeScript.

### Quick override

The card can set a one-hour duration override through the existing service. The
backend does not yet expose per-room supported override capabilities or a
structured active override object for frontend rendering.

The existing override services currently accept an area ID, profile ID, or
primary climate entity ID through the `area_id` service field. The card uses the
room primary climate entity ID as a transitional room reference until a
dedicated frontend-facing room action contract exists.

### Clear override / resume schedule

The card can call the existing clear service using the room primary climate
entity ID. The backend does not yet expose whether clearing is currently
relevant as a room capability or action state.

## Follow-up boundary

The next backend work should implement only the missing frontend-facing
operations discovered by this slice: schedule validation/update, minimal
schedule editing, action capability projection, room update, and room disable.
It should not return to broad backend-only room-management abstraction.

Real Home Assistant / Playwright end-to-end acceptance for the custom card is
still missing. Current evidence is Python backend tests plus Vitest/jsdom
frontend tests against mocked Home Assistant objects.
