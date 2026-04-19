# Discovery

## Product intent

ClimateRelayCore aims to provide a clearer and more coherent climate control experience for Home Assistant users who want a room-centric interface and reliable automation behavior on top of generic thermostat entities.

The project is intentionally backend-first. The initial value comes from a stable rule engine, a clear configuration model, and reusable services. Frontend work can evolve later on top of those interfaces.

## Problem statement

Home Assistant exposes many climate entities and helper tools, but building a consistent climate control experience across rooms often requires fragmented dashboards, ad hoc automations, and duplicated logic.

The product direction for ClimateRelayCore is to:

- organize climate control around rooms rather than raw entities
- model scheduling, manual overrides, and presence handling explicitly
- support optional room sensors without coupling the backend to a specific device family

## Functional themes

- room overview and room-level control
- optional humidity display
- optional window-contact automation per room
- presence-aware global operating mode
- room schedules and manual overrides
- frontend-independent backend services

## Architecture options considered

### Dashboard only

A dashboard-only solution would be fast to prototype but would push too much logic into the frontend and into user-managed Home Assistant helpers.

### Strategy-driven UI generation

This can become useful later, but it does not solve the core backend rule and configuration problems.

### Custom integration only

A backend-only solution would provide strong logic, but it would not deliver a coherent user experience on its own.

### Hybrid approach

The selected direction is a hybrid architecture:

- a Python custom integration for configuration, services, and rule evaluation
- a future TypeScript frontend for user experience

This gives the backend stable ownership of behavior while keeping UI choices open.
