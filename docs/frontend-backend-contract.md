# Frontend Backend Contract

## Purpose

This document defines the target contract between the Climate Relay backend
integration and the future custom frontend.

The backend owns behavior. The frontend owns presentation and user interaction.

## Backend ownership

The backend shall own:

- room activation state
- mapping from activated room to Home Assistant area
- primary climate anchoring
- optional sensor references
- schedule storage and validation
- schedule evaluation
- presence resolution
- manual override lifecycle
- window override lifecycle
- fallback and degradation behavior
- persistence and restart recovery
- Home Assistant service/action execution

## Frontend ownership

The frontend shall own:

- room overview rendering
- room detail rendering
- schedule editing interaction
- quick override interaction
- room-management interaction
- orchestration of backend-owned actions
- visualization of backend-owned state

The frontend shall not own:

- rule priority
- target resolution
- schedule evaluation
- fallback semantics
- degraded-state semantics
- restart recovery semantics

## Required state shape

The backend shall expose enough frontend-facing state for each activated room to
render:

- stable room/profile identifier
- Home Assistant area identifier
- display name
- primary climate entity identifier
- current temperature
- target temperature
- active control context
- effective presence or global mode influence where relevant
- next scheduled change
- override end time
- degradation status
- optional window state
- optional humidity value
- schedule summary
- capabilities required by the frontend

## Required frontend actions

The backend shall provide frontend-callable operations for:

- activate room
- update room configuration
- disable room
- set global mode
- set room override
- clear room override
- update room schedule
- validate room schedule before saving, if validation cannot be fully
  represented as part of save failure feedback

All operations shall validate input at the backend boundary.

## Options-flow migration rule

Room-level configuration currently implemented in the integration options flow
is transitional bootstrap scaffolding.

Once the frontend room-management surface can create and update room
configuration, the room-level options-flow configuration shall be reduced or
removed. The options flow shall remain focused on integration-global
administrative settings.

## Compatibility rule

Until migration is complete, both temporary options-flow configuration and
future frontend configuration shall write to the same backend-owned
configuration model. They shall not create competing persistence formats.
