# Architecture

## Selected approach

ClimateRelayCore uses a hybrid architecture:

- a Python custom integration for configuration, services, and rule evaluation
- a future frontend that consumes backend-owned interfaces

The backend remains the source of truth for behavior.

## Identity model

Home Assistant remains the source of truth for the house structure.

- Home Assistant `areas` and floors define the physical layout used for
  navigation and presentation.
- ClimateRelayCore defines regulation profiles that are canonically anchored
  to one primary Home Assistant `climate` entity.
- A regulation profile inherits its default Home Assistant area placement from
  that primary `climate` entity or its device context and may validate that
  relationship during configuration.
- The frontend and house navigation continue to use Home Assistant areas and
  floors, so the regulation profile must not become a second proprietary room
  tree.

## Layering

### Domain

Pure Python models and rule logic with no Home Assistant dependencies.

### Application

Use cases and services that orchestrate domain behavior.

### Ports

Abstract interfaces for time, persistence, entity access, and event delivery.

### Infrastructure

Home Assistant-specific adapters such as config flow, entity adapters, and service registration.

## Why backend-first

The project needs deterministic scheduling, override resolution, and area state recovery. Those concerns belong in the backend rather than in dashboards or ad hoc automation definitions.
The backend therefore owns rule evaluation, but it should attach that behavior
to HA-native entities and house structure instead of inventing a second house
model.

Backend-first does not mean options-flow-first. The backend owns behavior, but
room-level daily operation and room-level product configuration are target
frontend interactions. Administrative Home Assistant flows may bootstrap backend
configuration, but they are not the permanent product UI.

## Product UX documents

The target user experience and frontend/backend boundary are governed by:

- [product-ux-vision.md](./product-ux-vision.md)
- [frontend-interaction-model.md](./frontend-interaction-model.md)
- [frontend-backend-contract.md](./frontend-backend-contract.md)

These documents are binding design inputs for future frontend work and for any
backend change that affects room-level configuration, schedule editing, manual
overrides, or daily climate operation.

## Administrative flow versus product UI

Home Assistant config and options flows are administrative setup surfaces. They
are appropriate for integration-global configuration and temporary bootstrap
flows.

Room-level climate management is a product interaction surface and belongs to
the custom frontend. This includes room activation, room configuration,
schedule editing, quick overrides, and room-level diagnostics.

Room-level options-flow configuration is transitional scaffolding only and shall
be removed or reduced once the frontend room-management surface can write to
the backend-owned configuration model.

Until that migration is complete, temporary options-flow room configuration and
future frontend room configuration shall write to the same backend-owned
configuration model. They shall not create competing persistence formats.

## Epic 1 hardening decisions

- Effective target selection is centralized in a pure domain resolver. The Home
  Assistant climate entity consumes the resolver output for target temperature,
  active context, next schedule change, and manual override end time.
- The resolver preserves Epic 1 behavior and reserves an explicit
  `window_priority_pending` placeholder for Epic 2. Window automation is not
  exposed in Epic 1.
- Actuation state is recorded only after a blocking
  `climate.set_temperature` call succeeds. Failed writes are logged with entity,
  target, and source context and remain retryable.
- Global mode and manual override runtime state remain in memory for Epic 1.
  Full durable runtime persistence is deliberately deferred to the persistence
  epic because adding it here would broaden product behavior beyond hardening.

## Epic 2 window automation decisions

- Window override is part of the central pure-Python resolver and has the
  highest rule priority.
- The Home Assistant climate entity owns only framework adaptation: it observes
  the configured binary sensor, manages delayed activation, maps
  primary-climate capabilities, and passes an already resolved window target
  into the domain resolver.
- Window close clears the active window override and runs normal rule
  evaluation at close time instead of restoring a stored pre-window target.
- Window action mapping remains generic and capability-based. Unsupported
  `off` and `frost_protection` actions fall back to the primary climate
  minimum temperature.

## Epic 2 fallback decisions

- Required primary-climate availability is a resolver input, not a Home
  Assistant entity concern. The Home Assistant climate entity only adapts
  `missing`, `unknown`, and `unavailable` source states into that domain input.
- Required-component fallback has higher priority than window, manual, and
  schedule contexts because unavailable required control components make normal
  targets non-actionable. The resolved target is the configured global fallback
  temperature and the area entity exposes `active_control_context = fallback`
  plus `degradation_status = required_component_fallback`.
- Exceptional fallback for invalid runtime target data remains pure domain
  behavior. It reuses the last valid temperature target confirmed by the
  adapter when available and otherwise falls back to 20 C.
- Optional sensor degradation remains explanatory only. Unavailable optional
  humidity or window sources expose `optional_sensor_unavailable` without
  changing the effective target by themselves.

## Multi-profile configuration

Runtime data structures accept more than one regulation profile when
configuration supplies them. Epic 2 / Increment 2.2 adds a bounded runtime
update baseline: profile-local events such as manual area overrides notify only
the affected regulation profile, while global configuration and presence-mode
changes still fan out to all profile entities.

The current user-facing options flow supports adding, editing, removing, and
finishing multiple primary-climate-anchored regulation profiles as temporary
bootstrap scaffolding. Each profile still inherits its Home Assistant area from
the selected primary climate entity. The flow rejects profiles whose primary
climate entity has no HA area and rejects duplicate primary-climate or duplicate
HA-area targeting.

This options-flow room management is not the target UX. Long-term room
activation, room editing, schedule editing, optional sensor selection, and
window-behavior configuration belong to the custom frontend room-management
surface.

Remaining multi-profile hardening should add:

- stable generated profile IDs that survive display-name and entity changes
- migration rules for existing single-profile entries
- migration rules that allow the future frontend to replace room-level
  options-flow management without changing the backend-owned configuration
  model

## Frontend role

The frontend will eventually provide:

- room overview UI
- room detail dialogs
- room activation and configuration
- schedule editing
- quick manual override controls
- global mode controls
- room-level degraded-state and fallback indications

The frontend should never become the primary owner of behavioral logic or of
house-structure identity. It should consume Home Assistant area and floor data
for navigation and layer ClimateRelayCore state on top.

The frontend is the target surface for daily room-level climate operation and
room-level product configuration. The integration options flow remains an
administrative surface for integration-global settings and temporary bootstrap
configuration only.

## Options-flow UX structure

Home Assistant config and options flows are modeled as explicit multi-step data
entry flows. Climate Relay treats fields as always-visible only when an empty
value is a valid saved state. Fields that become required because of a previous
toggle, mode, or action selection are collected in a dedicated follow-up step.

Dedicated conditional steps must:

- name or describe the selection that made the field required
- keep pending values from previous steps until the flow is completed
- return localized integration-owned validation errors
- avoid relying on generic selector/schema errors for expected user mistakes

This pattern is used by the daily manual-override reset time and by the
open-window custom-temperature action. Future conditional fields should follow
the same structure unless Home Assistant introduces a canonical conditional
field mechanism that supersedes it.

This options-flow UX structure applies only when an options-flow surface is the
right Home Assistant surface for the behavior. It must not be used as a reason
to permanently place room-level product UX into integration-global options.
