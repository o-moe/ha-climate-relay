# Product UX Vision

## Purpose

Climate Relay shall provide a room-first climate control experience for Home
Assistant users. The product shall feel like a coherent climate-control
application inside Home Assistant, not like a collection of entities, services,
and integration options.

The Home Assistant config flow and options flow are administrative setup
surfaces. They are not the target interface for daily room-level climate
operation or room-level climate configuration.

## UX target

Users shall be able to:

- see all climate-controlled rooms at a glance
- understand the active reason for each room target
- change a room temperature temporarily
- resume the schedule
- edit the room schedule
- configure room-level climate behavior from the room UI
- recognize window, presence, schedule, override, and degraded states without
  reading raw entity attributes or logs

## Room-first model

A Climate Relay room corresponds to one Home Assistant area that has been
explicitly activated for Climate Relay. The room is anchored by one primary Home
Assistant `climate` entity.

Home Assistant remains the source of truth for area and floor structure. Climate
Relay must not create a parallel proprietary room tree.

## Administrative UI boundary

The integration options flow may temporarily contain room-level configuration
during backend bootstrap work. This is transitional scaffolding only.

Long term, room activation, room configuration, schedule editing,
window-contact selection, target temperatures, and room-level behavior shall
move to the custom frontend.

New room-level product behavior shall be specified against the frontend
room-management UI, not against the integration options flow.

## Daily-use UI

The primary daily-use UI shall be a custom dashboard/card frontend distributed
separately from the backend integration as a HACS dashboard repository.

The frontend shall consume backend-owned state and invoke backend-owned actions.
It shall not duplicate rule evaluation, schedule evaluation, fallback behavior,
or persistence semantics.

## First frontend slice

The first frontend slice shall include:

- room overview
- room detail
- room activation/configuration
- schedule editing for the initially supported schedule model
- quick manual override
- resume schedule / clear override
- global mode control
- basic degraded-state indication

## Non-goals

- No daily-use workflow shall require Home Assistant Developer Tools.
- No normal user workflow shall require manual service calls.
- No product UI shall require users to inspect raw entity attributes.
- No frontend code shall own climate-control business rules.
- No room configuration shall be permanently centered in the integration-global
  options flow.
- No manufacturer names, branding, or proprietary UI references shall appear in
  public repository content.
