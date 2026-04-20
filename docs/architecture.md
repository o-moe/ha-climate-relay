# Architecture

## Selected approach

ClimateRelayCore uses a hybrid architecture:

- a Python custom integration for configuration, services, and rule evaluation
- a future frontend that consumes backend-owned interfaces

The backend remains the source of truth for behavior.

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

The project needs deterministic scheduling, override resolution, and room state recovery. Those concerns belong in the backend rather than in dashboards or ad hoc automation definitions.

## Frontend role

The frontend will eventually provide:

- room overview UI
- room detail dialogs
- schedule editing
- global mode controls

The frontend should never become the primary owner of behavioral logic.
