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

## Frontend role

The frontend will eventually provide:

- area overview UI
- area detail dialogs
- schedule editing
- global mode controls

The frontend should never become the primary owner of behavioral logic or of
house-structure identity. It should consume Home Assistant area and floor data
for navigation and layer ClimateRelayCore state on top.
