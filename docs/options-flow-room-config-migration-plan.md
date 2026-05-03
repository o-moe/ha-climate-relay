# Options-Flow Room Configuration Migration Plan

## Purpose

This document classifies the current room-level configuration that is still
implemented in the Home Assistant integration options flow and defines how that
configuration shall move toward the target custom frontend room-management UI.

The current options-flow room management exists only as temporary bootstrap
scaffolding. It allows the backend and Home Assistant runtime surface to be
validated before the custom frontend exists. It is not the target product UX.

## Scope

This migration plan covers the options-flow room and regulation-profile
configuration implemented in `custom_components/climate_relay_core/config_flow.py`
and localized in `custom_components/climate_relay_core/strings.json`.

It does not change Python behavior. It does not remove existing options-flow
steps. It defines the migration target and the evidence required before the
options-flow room management can be reduced or removed.

## Target state

The long-term target state is:

- the integration options flow remains focused on integration-global
  administrative settings
- room activation and room configuration move to the custom frontend
- schedule editing moves to the custom frontend in the first frontend slice
- quick overrides and resume-schedule actions are daily-use frontend flows
- backend-owned state and actions remain authoritative for all climate behavior
- the frontend does not own rule evaluation, schedule evaluation, fallback
  behavior, degraded-state semantics, or persistence semantics

## Classification summary

### Integration-global settings

These settings may remain in the integration options flow because they affect
the integration as a whole rather than one room:

- `person_entity_ids`
- `unknown_state_handling`
- `fallback_temperature`
- `manual_override_reset_enabled`
- `manual_override_reset_time`
- `simulation_mode`
- `verbose_logging`

These settings are collected in the options-flow `init` step, with the reset
time collected in the dedicated `reset_time` step when daily reset is enabled.
They remain administrative configuration.

### Temporary room bootstrap settings

The following settings are currently allowed to remain in the options flow only
as bootstrap scaffolding:

- `rooms`
- `primary_climate_entity_id`
- `humidity_entity_id`
- `window_entity_id`
- `window_action_type`
- `window_custom_temperature`
- `window_open_delay_seconds`
- `home_target_temperature`
- `away_target_type`
- `away_target_temperature`
- `schedule_home_start`
- `schedule_home_end`

These settings are currently collected through the `profiles`,
`profile_select_edit`, `profile_select_remove`, `room`, and
`window_custom_temperature` steps.

They shall not be expanded into richer room-level product UX in the integration
options flow. Any additional room-level product requirement must be specified
against the custom frontend room-management model.

### Future frontend room-management settings

The following settings shall move to the custom frontend room-management UI:

- room activation backed by `rooms`
- primary climate selection backed by `primary_climate_entity_id`
- optional humidity source selection backed by `humidity_entity_id`
- optional window-contact selection backed by `window_entity_id`
- open-window behavior backed by `window_action_type`,
  `window_custom_temperature`, and `window_open_delay_seconds`
- comfort and setback targets backed by `home_target_temperature`,
  `away_target_type`, and `away_target_temperature`
- schedule editing backed by `schedule_home_start`, `schedule_home_end`, and
  the future richer schedule model

The frontend shall write through backend-owned actions or configuration APIs.
It shall not mutate Home Assistant config entries directly and shall not create
a second persistence format.

### Remove after frontend migration

The following options-flow surfaces shall be reduced or removed once the custom
frontend can manage the equivalent room configuration:

- the `profiles` management step
- the `profile_select_edit` step
- the `profile_select_remove` step
- the `room` configuration step
- the `window_custom_temperature` step as a room-management step
- selector labels and descriptions that present regulation-profile management
  as a permanent options-flow experience

Removal must not happen before the backend exposes stable frontend-callable room
configuration operations and the frontend has acceptance evidence for room
activation, schedule editing, and room update persistence.

## Field migration details

### `rooms`

Current location: options-flow persistence payload created by
`_create_options_entry()`.

Current purpose: stores the configured regulation-profile list.

Target surface: custom frontend room-management UI.

Target backend contract: activated room/profile list exposed as backend-owned
state and updated through backend-owned room activation, room update, and room
disable operations.

Migration trigger: the frontend can create, update, and disable rooms without
using the options flow.

Required evidence before options-flow removal:

- room activation frontend acceptance path
- room update frontend acceptance path
- room disable frontend acceptance path
- persisted configuration reload test
- migration test proving existing `rooms` options are preserved or migrated

### `primary_climate_entity_id`

Current location: `room` step.

Current purpose: anchors one regulation profile to exactly one Home Assistant
`climate` entity and derives the Home Assistant area.

Target surface: room activation and room configuration in the custom frontend.

Target backend contract: room activation/update operation validates exactly one
primary climate entity, derives exactly one Home Assistant area, rejects missing
areas, rejects duplicate primary climates, and rejects duplicate target areas.

Migration trigger: the frontend can activate an eligible Home Assistant area and
select or confirm the primary climate entity.

Required evidence before options-flow removal:

- frontend room activation acceptance path
- duplicate primary-climate validation
- duplicate area validation
- missing-area validation
- backend validation tests independent of the options flow

### `humidity_entity_id`

Current location: `room` step.

Current purpose: optional display-only humidity source for a regulation profile.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation accepts optional humidity source,
exposes humidity as display context, and marks optional sensor degradation
without affecting target resolution.

Migration trigger: the frontend room detail or room settings UI can select,
clear, and display the optional humidity source.

Required evidence before options-flow removal:

- frontend room settings acceptance path for selecting and clearing humidity
- backend optional-sensor degradation test
- frontend degraded-state indication for unavailable humidity source

### `window_entity_id`

Current location: `room` step.

Current purpose: optional window-contact source for one room.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation accepts optional window contact,
subscribes to its state, applies delayed open-window behavior, and exposes
window state and degradation information.

Migration trigger: the frontend can select and clear the window contact as part
of room configuration.

Required evidence before options-flow removal:

- frontend room settings acceptance path for selecting and clearing window
  contact
- delayed open-window runtime acceptance
- unavailable optional window-contact degradation acceptance

### `window_action_type`

Current location: `room` step.

Current purpose: selects the action used while a configured window is open.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation validates the supported action
values and keeps action mapping in backend-owned rule logic.

Migration trigger: the frontend can configure the open-window behavior without
using options-flow profile management.

Required evidence before options-flow removal:

- frontend room settings acceptance path for each supported action category
- backend tests for action validation and capability fallback
- no duplicated action mapping in TypeScript

### `window_custom_temperature`

Current location: dedicated `window_custom_temperature` options-flow step.

Current purpose: collects the required custom target when `window_action_type`
is `custom_temperature`.

Target surface: room configuration in the custom frontend.

Target backend contract: backend validation rejects custom-temperature action
without a valid custom temperature and returns localized or frontend-renderable
validation feedback.

Migration trigger: the frontend can collect and validate the custom temperature
as part of the open-window settings flow.

Required evidence before options-flow removal:

- frontend validation path for missing custom temperature
- frontend validation path for invalid range
- backend validation test that does not depend on options-flow selectors

### `window_open_delay_seconds`

Current location: `room` step.

Current purpose: defines how long a window must remain open before window
override activates.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation validates non-negative delay
values and persists the selected delay.

Migration trigger: the frontend can edit the delay and runtime behavior uses the
updated backend-owned value.

Required evidence before options-flow removal:

- frontend room settings acceptance path for delay edit
- delayed window activation runtime acceptance using the frontend-configured
  value
- backend validation test for invalid delay values

### `home_target_temperature`

Current location: `room` step.

Current purpose: defines the room target used when the effective presence is
home and schedule context selects the home target.

Target surface: room configuration and schedule editing in the custom frontend.

Target backend contract: room update and schedule update operations validate and
persist temperature values. Rule evaluation remains backend-owned.

Migration trigger: the frontend can edit the home target and the room overview
shows the resulting target when active.

Required evidence before options-flow removal:

- frontend room settings or schedule editor acceptance path
- backend target validation test
- room overview reflects the updated target without raw attribute inspection

### `away_target_type`

Current location: `room` step.

Current purpose: defines whether the away target is absolute or relative.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation validates the allowed target
strategy values and backend rule evaluation applies the strategy.

Migration trigger: the frontend can edit the away target mode and render the
configured strategy clearly.

Required evidence before options-flow removal:

- frontend room settings acceptance path for absolute and relative modes
- backend validation tests for allowed values
- backend rule tests for absolute and relative target behavior

### `away_target_temperature`

Current location: `room` step.

Current purpose: stores either the absolute away target or relative away delta,
depending on `away_target_type`.

Target surface: room configuration in the custom frontend.

Target backend contract: room update operation validates the value according to
the selected target strategy and keeps resolution backend-owned.

Migration trigger: the frontend can edit the away value and render whether it is
an absolute temperature or a relative delta.

Required evidence before options-flow removal:

- frontend room settings acceptance path for both value semantics
- backend validation tests
- room detail reason chain shows away influence when active

### `schedule_home_start`

Current location: `room` step.

Current purpose: defines the beginning of the initially supported daily home
window.

Target surface: schedule editor in the first custom frontend slice.

Target backend contract: schedule update operation validates continuity,
non-overlap, and minute-level boundaries. Backend schedule evaluation remains
authoritative.

Migration trigger: the frontend schedule editor can edit and persist the daily
home window start time.

Required evidence before options-flow removal:

- frontend schedule editing acceptance path
- invalid schedule validation path
- backend schedule validation test independent of options-flow forms
- room tile or room detail shows the next scheduled change

### `schedule_home_end`

Current location: `room` step.

Current purpose: defines the end of the initially supported daily home window.

Target surface: schedule editor in the first custom frontend slice.

Target backend contract: schedule update operation validates that start and end
form a meaningful window and that future richer schedules remain continuous and
non-overlapping.

Migration trigger: the frontend schedule editor can edit and persist the daily
home window end time.

Required evidence before options-flow removal:

- frontend schedule editing acceptance path
- validation for identical start and end times
- backend schedule validation test independent of options-flow forms
- runtime acceptance showing schedule-derived target changes

## Backend capabilities required before migration

The backend must expose or support the following capabilities before the
options-flow room-management surface can be reduced:

- stable generated room/profile identifiers
- room activation operation
- room update operation
- room disable operation
- schedule update operation
- backend validation that is independent of options-flow schemas
- frontend-facing room state with enough data for overview, detail, schedule,
  override, window, humidity, and degradation rendering
- persistence migration for existing `rooms` options
- acceptance tests that configure room behavior through the target frontend
  rather than through the integration options flow

## Config subentries evaluation checkpoint

Home Assistant config subentries may be a better administrative representation
for repeated room/profile configuration than a single global options-flow list.
However, config subentries are still Home Assistant administrative
configuration flows. They are not the target daily-use room-management UI.

Before adopting config subentries, the project must complete the evaluation in
[config-subentries-evaluation.md](./config-subentries-evaluation.md).

Subentries shall not be adopted only to make the current options-flow UX more
structured. They are acceptable only if they reduce backend persistence and
migration risk without delaying or replacing the custom frontend room-management
surface.

## Migration phases

### Phase 1: Freeze options-flow room UX growth

No new room-level product behavior is added to the options flow unless the
change documents why it is temporary and which frontend interaction will replace
it.

### Phase 2: Extract backend-owned room configuration operations

Move validation and persistence rules behind backend-owned operations that can
be called by both temporary options-flow scaffolding and future frontend flows.

### Phase 3: Build first frontend slice

Implement room overview, room detail, room activation/configuration, schedule
editing, quick override, clear override / resume schedule, global mode control,
and basic degraded-state indication in the separate frontend repository.

### Phase 4: Migrate existing options data

Preserve or migrate existing `rooms` data into the backend-owned configuration
model used by the frontend.

### Phase 5: Reduce or remove room-level options-flow surfaces

After frontend acceptance and migration evidence exists, remove or reduce the
options-flow room-management steps. Keep only integration-global administrative
settings in the options flow.

## Non-goals

- This plan does not require immediate removal of existing room options-flow
  behavior.
- This plan does not introduce frontend-owned rule evaluation.
- This plan does not introduce a second room tree outside Home Assistant areas.
- This plan does not require config subentries unless the separate evaluation
  proves they are beneficial.
- This plan does not permit daily-use room operation through Home Assistant
  Developer Tools or manual service calls as the target UX.
