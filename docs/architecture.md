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

## Future multi-profile configuration

Runtime data structures accept more than one regulation profile when
configuration supplies them. Epic 2 / Increment 2.2 adds a bounded runtime
update baseline: profile-local events such as manual area overrides notify only
the affected regulation profile, while global configuration and presence-mode
changes still fan out to all profile entities.

The user-facing config and options flows remain single-profile at this point.
Full multi-profile add, edit, remove, and persistence UX is deferred until the
dedicated multi-profile configuration slice because it requires complete
Home Assistant GUI acceptance coverage for success, validation, cancellation,
and persistence paths.

The future multi-profile model should add:

- stable generated profile IDs that survive display-name and entity changes
- add, edit, and remove operations for regulation profiles
- explicit area/profile target selection for services
- validation for duplicate area targeting and orphaned profiles
- migration rules for existing single-profile entries

## Frontend role

The frontend will eventually provide:

- area overview UI
- area detail dialogs
- schedule editing
- global mode controls

The frontend should never become the primary owner of behavioral logic or of
house-structure identity. It should consume Home Assistant area and floor data
for navigation and layer ClimateRelayCore state on top.

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
