# Increment 3.3 GUI Gaps

## Scope

Increment 3.3 starts the first GUI vertical slice with a minimal
`climate-relay-card` custom card. The card renders activated Climate Relay room
climate entities from backend-owned Home Assistant state and can call the
existing backend override services.

The slice deliberately does not add a broad backend API, a WebSocket API, config
subentries, a new persistence format, or an Options Flow UX expansion.

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

## Remaining backend-facing gaps

### Room activation

The frontend still lacks backend-owned candidate discovery and a
frontend-callable activation operation. The existing `room_management.py`
helpers operate on the existing `rooms` option shape, but no Home Assistant
frontend-facing operation lists eligible areas/climate candidates or persists an
activated room from the custom card.

### Schedule editing

The frontend still lacks backend-owned schedule validation and schedule update
operations. The card therefore documents the gap instead of implementing a fake
schedule editor or duplicating schedule validation in TypeScript.

### Quick override

The card can set a one-hour duration override through the existing service. The
backend does not yet expose per-room supported override capabilities or a
structured active override object for frontend rendering.

### Clear override / resume schedule

The card can call the existing clear service using the room primary climate
entity ID. The backend does not yet expose whether clearing is currently
relevant as a room capability or action state.

## Follow-up boundary

The next backend work should implement only the missing frontend-facing
operations discovered by this slice: candidate discovery, room activation,
schedule validation/update, and action capability projection. It should not
return to broad backend-only room-management abstraction.
