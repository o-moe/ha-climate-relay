# Frontend Backend Contract Spike

## 1. Purpose

This spike prepares the backend contract for the future custom frontend room
management experience. The goal is to identify the backend-owned state shapes
and backend-owned operations required by the first frontend slice before any
frontend implementation starts.

The current Options Flow room/profile manager remains administrative bootstrap
scaffolding. It must not drift into the long-term daily-use room management UI.
The custom frontend may render state and orchestrate backend-owned actions, but
it must not duplicate climate-control business rules, schedule evaluation,
override lifecycle behavior, fallback behavior, or degraded-state semantics.

This document is intentionally a contract and gap analysis. It does not introduce
a frontend, a new Options Flow surface, config subentries, or a new persistence
format.

Increment 3.1 extracted behavior-neutral room/profile validation and
normalization from `custom_components/climate_relay_core/config_flow.py`.
Increment 3.2 adds the minimal backend-owned room-management entry point in
`custom_components/climate_relay_core/room_management.py`. That entry point
still works on the existing `rooms` options shape and only supports activating,
updating, or disabling one room/profile at a time. It does not add Home
Assistant services, WebSocket APIs, config subentries, frontend APIs, or a new
persistence format.

Increment 3.3 starts the first GUI vertical slice with a minimal
`climate-relay-card` prototype in `frontend/`. The card reads activated room
climate entities from existing Home Assistant state and calls existing override
services where available. It does not add a new backend API. The remaining
backend-facing gaps discovered by the slice are tracked in
[increment-3-3-gui-gaps.md](./increment-3-3-gui-gaps.md).

Increment 3.3a adds the first narrow frontend-facing backend operations:
`climate_relay_core/room_candidates` and `climate_relay_core/activate_room`
WebSocket commands. These commands are scoped to candidate discovery and
activating exactly one room from the custom card. They keep the existing
`rooms` persistence format and do not introduce config subentries or a broad
backend API. Both commands require a Home Assistant admin user because they
support room configuration; activation also mutates persistent config entry
options.

Increment 3.3b adds `climate_relay_core/update_room_schedule` for the existing
daily-window schedule model. The command accepts a transitional
`primary_climate_entity_id` room reference plus `schedule_home_start` and
`schedule_home_end`, requires an admin user, validates the schedule in backend
code, updates only those two fields on the matching room in the existing
`rooms` options list, and relies on the existing config-entry update listener
for reload. The command accepts only minute-level schedule values; `HH:MM` and
`HH:MM:00` normalize to `HH:MM:00`, while non-zero seconds or microseconds are
rejected as invalid schedule times.

A later frontend-facing state provider or API should only be introduced after
the concrete frontend consumption model has been explicitly chosen.

Increment 3.3c adds minimal room action capability projection to existing room
climate entity attributes instead of introducing a new state provider. The card
uses those projected attributes to decide whether to render fixed-duration
override and resume actions, while continuing to call the existing override
services. The only set-override action projected in this increment is
`set_manual_override_duration`; `can_set_override` means that this minimal
duration action is available, not that all override termination variants have a
complete frontend capability policy.

This spike refines the target direction already documented in
[product-ux-vision.md](./product-ux-vision.md),
[frontend-interaction-model.md](./frontend-interaction-model.md),
[frontend-backend-contract.md](./frontend-backend-contract.md),
[options-flow-room-config-migration-plan.md](./options-flow-room-config-migration-plan.md),
[config-subentries-evaluation.md](./config-subentries-evaluation.md),
[product-ux-requirements-addendum.md](./product-ux-requirements-addendum.md),
and
[product-ux-verification-addendum.md](./product-ux-verification-addendum.md).
It is not a replacement for those documents.

## 2. Current backend surfaces

### Persisted room/profile data

Room/profile configuration is currently persisted in config entry options under
the `rooms` key (`CONF_ROOMS` in
`custom_components/climate_relay_core/const.py`). The current Options Flow owns
creation and mutation of those values in
`custom_components/climate_relay_core/config_flow.py`.

Each persisted room/profile entry currently stores these fields:

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

Runtime normalization happens in
`custom_components/climate_relay_core/runtime.py`:

- `build_room_configs(...)` reads `rooms` from merged config entry data/options.
- `_normalize_room_config(...)` normalizes the persisted flat room shape.
- `_normalize_schedule(...)` also accepts a nested `schedule` shape, but the
  current Options Flow still persists the flat daily schedule fields.
- `_resolve_area_reference(...)` derives the Home Assistant area from the
  primary climate entity or its device.
- `_resolve_profile_display_name(...)` prefers the HA area name, then legacy
  `name`, then the primary climate entity ID.

After the room/profile normalization extraction,
`custom_components/climate_relay_core/room_config.py` owns persisted or
config-like room/profile normalization and pure validation. It must remain a
framework-independent helper layer and must not import Home Assistant UI
dependencies such as selectors, config entries, `voluptuous`, or Options Flow
step logic.

`custom_components/climate_relay_core/runtime.py` owns runtime object
construction, active room configs, manual overrides, schedule-evaluation inputs,
target-resolution support, and subscriber notification. These responsibilities
must not be merged back into `room_config.py` during later refactoring.

There is no durable, user-editable stable profile identifier in the persisted
room options. `build_room_configs(...)` currently derives
`RegulationProfileConfig.profile_id` from `slugify(primary_climate_entity_id)`.
That identifier is stable only while the primary climate entity ID remains
unchanged.

The Increment 3.2 room-management entry point therefore uses
`primary_climate_entity_id` as the temporary room reference for activation,
update, and disable operations. This is a transitional reference strategy only.
It must be replaced or wrapped by a stable profile-ID contract before the
frontend depends on durable room identities. Increment 3.2 deliberately does
not introduce that profile-ID migration.

### Current regulation-profile fields

`RegulationProfileConfig` in
`custom_components/climate_relay_core/runtime.py` is the current runtime profile
shape. It contains:

- `profile_id`
- `display_name`
- `primary_climate_entity_id`
- `area_id`
- `area_name`
- `humidity_entity_id`
- `window_entity_id`
- `window_action_type`
- `window_custom_temperature`
- `window_open_delay_seconds`
- `home_target`
- `away_target`
- `schedule`

This is close to the backend-owned room configuration shape required by the
frontend, but it is runtime-internal and does not yet provide a frontend-facing
state adapter, mutation API, or migration-safe profile identity contract.

### Current climate entities per profile

`custom_components/climate_relay_core/climate.py` creates one
`ClimateRelayCoreRoomClimateEntity` per `RegulationProfileConfig` in
`async_setup_entry(...)`. The entity:

- Represents one configured room/profile.
- Uses the runtime profile display name for the entity name.
- Suggests the resolved HA area in `device_info` when available.
- Reads source state from the primary climate entity and optional humidity/window
  entities.
- Applies backend-owned target resolution through the domain resolver.
- Exposes HA climate properties such as current temperature, target temperature,
  and optionally current humidity.

The climate entity currently exposes these frontend-relevant attributes:

- `active_control_context`
- `supported_room_actions`
- `can_set_override`
- `can_clear_override`
- `manual_override_active`
- `manual_override_target_temperature`
- `manual_override_ends_at`
- `manual_override_termination_type`
- `primary_climate_entity_id`
- `humidity_entity_id`
- `window_entity_id`
- `next_change_at`
- `override_ends_at`
- `degradation_status`
- `schedule_home_start`
- `schedule_home_end`

The climate entity does not currently expose a complete room state object with
`profile_id`, `area_id`, capabilities, optional source entity states, or
global-mode influence. Schedule projection is intentionally limited to the
current daily-window start/end fields.

### Current select entity for global mode

`custom_components/climate_relay_core/select.py` creates the integration-wide
presence control select entity. It maps user selection to
`GlobalRuntime.async_set_global_mode(...)`.

The select entity exposes:

- selectable global mode options: `auto`, `home`, `away`
- `effective_presence`
- `unknown_state_handling`
- `fallback_temperature`
- `manual_override_reset_time`
- `simulation_mode`

This is the current global mode/status surface. There is not yet a consolidated
frontend-facing global state provider or room-overview provider.

### Current services/actions

`custom_components/climate_relay_core/services.yaml` and
`custom_components/climate_relay_core/__init__.py` expose these current backend
actions:

- `climate_relay_core.set_global_mode`
  - Input: `mode`
  - Handler: `_async_handle_set_global_mode(...)`
  - Runtime operation: `GlobalRuntime.async_set_global_mode(...)`

- `climate_relay_core.set_area_override`
  - Input: `area_id`, `target_temperature`, `termination_type`, optional
    `duration_minutes`, optional `until_time`
  - Handler: `_async_handle_set_area_override(...)`
  - Service-level termination validation:
    `_validate_override_termination(...)`
  - Runtime operation: `GlobalRuntime.async_set_area_override(...)`
  - The runtime accepts a HA area ID, profile ID, or primary climate entity ID
    through `_find_room_config(...)`.

- `climate_relay_core.clear_area_override`
  - Input: `area_id`
  - Handler: `_async_handle_clear_area_override(...)`
  - Runtime operation: `GlobalRuntime.async_clear_area_override(...)`
  - The runtime accepts a HA area ID, profile ID, or primary climate entity ID
    through `_find_room_config(...)`.

These services are suitable backend-owned actions for override and global mode
control. They are not sufficient as the complete daily-use custom frontend
contract because they do not cover room activation, room configuration, schedule
validation/update, candidate discovery, or room state listing.

### Current explanatory attributes

Current explanatory attributes are split across room climate entities and the
global select entity.

Room climate entity attributes in
`custom_components/climate_relay_core/climate.py`:

- `active_control_context`
- `degradation_status`
- `next_change_at`
- `override_ends_at`
- `primary_climate_entity_id`
- `humidity_entity_id`
- `window_entity_id`

Global select entity attributes in
`custom_components/climate_relay_core/select.py`:

- `effective_presence`
- `fallback_temperature`
- `simulation_mode`
- `unknown_state_handling`
- `manual_override_reset_time`

The first frontend slice can read some of these from HA entity state, but the
current surfaces do not yet provide one complete, backend-owned room overview or
room detail shape.

## 3. Frontend state requirements

The first frontend slice needs a minimal frontend-facing room state for every
activated room. The backend should own the shape and semantics. The frontend may
render it and call backend actions, but must not infer climate-control business
rules from raw HA state.

Required room state:

- `profile_id`
  - Purpose: stable room/profile identifier for state updates and actions.
  - Current status: partially exists as runtime-derived
    `RegulationProfileConfig.profile_id`.
  - Gap: derived from `primary_climate_entity_id`, not persisted as a durable ID.

- `area_id`
  - Purpose: HA area identifier for room identity and service targeting.
  - Current status: runtime derives it from the primary climate entity when HA
    registries are available.
  - Gap: not persisted and not exposed on the room climate entity.

- `display_name`
  - Purpose: room label for overview/detail.
  - Current status: exists in `RegulationProfileConfig.display_name` and entity
    name.
  - Gap: no explicit state field in a room state adapter.

- `primary_climate_entity_id`
  - Purpose: primary control anchor.
  - Current status: persisted and exposed as a climate entity attribute.
  - Gap: no candidate/eligibility metadata for frontend activation flows.

- `current_temperature`
  - Purpose: room detail and overview status.
  - Current status: exposed through the room climate entity's HA climate state.
  - Gap: no consolidated room state adapter.

- `target_temperature`
  - Purpose: effective backend-owned target.
  - Current status: exposed through the room climate entity's HA climate state.
  - Gap: no explicit target source summary beyond `active_control_context`.

- `active_control_context`
  - Purpose: explain whether schedule, global presence, manual override, window
    override, or fallback is currently controlling the target.
  - Current status: exposed as a climate entity attribute.
  - Gap: frontend should consume a bounded backend-owned vocabulary; the current
    attribute exists but is not packaged with action capabilities.

- `effective_presence` or relevant global mode influence
  - Purpose: explain global mode influence on the room.
  - Current status: exposed on the global select entity.
  - Gap: not included in per-room state.

- `next_scheduled_change`
  - Purpose: show the next schedule-driven change when known.
  - Current status: `next_change_at` is exposed on room climate entities when
    known.
  - Gap: name and semantics should be made explicit in the frontend contract.

- `active_override_end_time`
  - Purpose: show active manual override expiry.
  - Current status: `override_ends_at` is exposed when a bounded override is
    active.
  - Gap: no explicit override object with termination type/capabilities.

- `degradation_status`
  - Purpose: basic degraded-state indication.
  - Current status: exposed on room climate entities when degraded/fallback is
    active.
  - Gap: no aggregate degraded-state summary.

- `humidity_entity_id`
  - Purpose: optional sensor configuration display/edit.
  - Current status: persisted and exposed when configured.
  - Gap: no frontend-facing configuration shape or candidate list.

- `humidity_value`
  - Purpose: optional live room humidity display.
  - Current status: room climate entity may expose current humidity through HA
    climate properties when available.
  - Gap: no explicit optional field tied to the configured humidity source.

- `window_entity_id`
  - Purpose: optional window sensor configuration display/edit.
  - Current status: persisted and exposed when configured.
  - Gap: no frontend-facing configuration shape or candidate list.

- `window_state`
  - Purpose: live window status and degraded-state explanation.
  - Current status: internal climate entity tracking reads the optional window
    state.
  - Gap: not exposed as a room state field.

- `schedule_summary`
  - Purpose: show the configured daily schedule without frontend rule
    evaluation.
  - Current status: runtime has `ScheduleDefinition` on the room config.
  - Gap: not exposed as frontend-facing state.

- `supported_override_termination_capabilities`
  - Purpose: drive quick manual override controls.
  - Current status: service supports `duration`, `until_time`, `next_timeblock`,
    and `never`.
  - Gap: not exposed as discoverable room/global capabilities.

- `supported_schedule_editing_capabilities`
  - Purpose: constrain the frontend editor to the backend-supported model.
  - Current status: current model is one all-days home window with start/end.
  - Gap: not exposed as backend-owned capabilities.

- `supported_window_behavior_capabilities`
  - Purpose: constrain window behavior editing.
  - Current status: window behavior options exist in Options Flow and runtime.
  - Gap: not exposed outside Options Flow.

- `simulation_mode`
  - Purpose: indicate whether service/action execution is simulated.
  - Current status: exposed on the global select entity.
  - Gap: not included in per-room state or a room overview payload.

## 4. Frontend action requirements

### List activated rooms

- Purpose: power the room overview and route to room detail.
- Input: none, or config entry identifier if multiple entries are supported.
- Validation responsibility: backend filters to configured/activated rooms.
- Output or state effect: list of frontend-facing room state objects.
- Existing implementation support: `GlobalRuntime.room_configs` and room climate
  entities contain most source data.
- Missing implementation work: add a frontend-facing state adapter/provider or
  diagnostic/state service that assembles complete room state without requiring
  frontend rule inference.
- Required tests: room state shape generation, empty room list, multi-room order
  stability, degraded room state, optional humidity/window state inclusion.

### List eligible Home Assistant areas/climate candidates

- Purpose: support room activation/configuration without embedding HA registry
  logic in the frontend.
- Input: none, or optional current profile ID when editing.
- Validation responsibility: backend reads HA area, device, and entity registries;
  backend marks invalid or already-used candidates.
- Output or state effect: candidate list with area ID/name, climate entity ID,
  display labels, duplicate/eligibility metadata, and optional humidity/window
  candidates if included in the first backend operation.
- Existing implementation support: Options Flow selectors and
  `_resolve_area_reference(...)` derive area context.
- Increment 3.3a implementation: `climate_relay_core/room_candidates` returns
  `candidate_id`, `area_id`, `area_name`, `primary_climate_entity_id`,
  `primary_climate_display_name`, `already_active`, and
  `unavailable_reason`. The command excludes Climate Relay's own virtual room
  climate entities from candidates by ignoring state-machine climate entities
  that expose `primary_climate_entity_id` and registry entries owned by the
  `climate_relay_core` platform.
- Remaining implementation work: optional humidity/window candidates, editing
  context, and a complete room-state provider remain open.
- Required tests: primary climate missing area, duplicate primary climate,
  duplicate HA area, candidate exclusion/inclusion while editing an existing
  room, optional sensor/window candidates.

### Activate room

- Purpose: create a room/profile from an eligible HA area and primary climate.
- Input: primary climate entity ID or candidate ID for Increment 3.3a. Optional
  humidity entity ID, optional window entity ID, window behavior, target
  temperatures, and daily schedule remain future room-configuration inputs.
- Validation responsibility: backend validates required primary climate, HA area
  resolution, duplicates, targets, schedule, optional sensors, and window
  behavior.
- Output or state effect: updates existing `rooms` options and reloads runtime
  using the same persistence format.
- Existing implementation support: Options Flow add-profile path persists this
  data.
- Increment 3.3a implementation: `climate_relay_core/activate_room` validates
  the selected candidate, builds a default room payload, calls
  `room_management.activate_room(...)`, persists updated config entry options
  through Home Assistant's config-entry update path, and relies on the existing
  config-entry update listener to reload runtime/entities.
- Required tests: activation validation, primary climate missing area, duplicate
  primary climate, duplicate HA area, defaults, persistence, and update-listener
  reload behavior.

### Update room configuration

- Purpose: edit primary/optional sensors, targets, and window behavior for an
  activated room.
- Input: stable profile ID or area ID plus replacement configuration fields.
- Validation responsibility: backend validates all room fields and protects
  against duplicate anchors.
- Output or state effect: updates one `rooms` entry, drops stale overrides only
  when the target profile is no longer present, and reloads runtime.
- Existing implementation support: Options Flow edit-profile path and
  `GlobalRuntime.update_room_configs(...)` support reload behavior.
- Missing implementation work: reusable validation, stable mutation target, and
  backend-owned update operation.
- Required tests: optional humidity selection/clearing, optional window
  selection/clearing, window action validation, custom window temperature
  validation, window delay validation, home/away target validation, duplicate
  protection while editing.

### Disable room

- Purpose: deactivate a configured room/profile while preserving safe runtime
  behavior.
- Input: stable profile ID or area ID.
- Validation responsibility: backend validates the room exists.
- Output or state effect: removes the room from existing `rooms` options,
  reloads runtime, and clears stale overrides for removed profiles.
- Existing implementation support: Options Flow remove-profile path and runtime
  stale override cleanup.
- Missing implementation work: backend-owned disable operation and stable target
  identity.
- Required tests: disable existing room, reject unknown room, stale override
  cleanup, unrelated rooms unaffected, existing `rooms` compatibility.

### Update room schedule

- Purpose: edit the backend-owned schedule for the initial schedule model.
- Input: stable profile ID or area ID plus schedule payload.
- Validation responsibility: backend validates supported schedule layout, time
  format, daily start/end bounds, and non-identical start/end.
- Output or state effect: updates schedule fields in the existing room options
  persistence and reloads runtime.
- Existing implementation support: Options Flow schedule fields and runtime
  `_normalize_schedule(...)`.
- Current extraction note: `validate_room_schedule_window(...)` preserves only
  the existing Options Flow invariant that start and end must not be identical.
  It is not a complete schedule validator.
- Missing implementation work: reusable schedule validation and backend-owned
  schedule update operation independent of Options Flow.
- Required tests: daily schedule start/end validation, identical schedule
  start/end rejection, schedule persistence and reload, existing flat `rooms`
  compatibility.

### Validate room schedule

- Purpose: let the frontend validate edits before persisting without duplicating
  schedule rules.
- Input: schedule payload and optional room/profile context.
- Validation responsibility: backend owns all validation.
- Output or state effect: validation success with normalized schedule summary or
  structured validation errors; no persistence side effect.
- Existing implementation support: partial normalization in runtime and UI schema
  constraints in Options Flow.
- Missing implementation work: backend-owned validation function/action with
  structured errors for valid time values, supported schedule layout,
  continuity, non-overlap, minute-level boundaries, and future richer schedule
  models.
- Required tests: valid schedule normalization, invalid time values, identical
  schedule start/end rejection, unsupported schedule layout rejection.

### Set global mode

- Purpose: switch integration-wide presence control.
- Input: `mode` (`auto`, `home`, `away`).
- Validation responsibility: service/runtime validate bounded enum.
- Output or state effect: updates `GlobalRuntime.global_mode` and notifies
  subscribers.
- Existing implementation support: `set_global_mode` service and select entity.
- Missing implementation work: include current global mode and effective
  presence in the frontend state provider.
- Required tests: existing service/select tests plus frontend state projection of
  global mode.

### Set room override

- Purpose: set a quick manual override for one room.
- Input: area ID, profile ID, or primary climate entity ID; target temperature;
  termination type; optional duration or until time.
- Validation responsibility: backend validates target room and termination
  payload. Temperature range should be part of the backend-owned contract, not
  only service selector metadata.
- Output or state effect: creates/replaces manual override and notifies only the
  targeted profile.
- Existing implementation support: `set_area_override` service and
  `GlobalRuntime.async_set_area_override(...)`.
- Increment 3.3c implementation support: room climate entity attributes expose
  the minimal supported card action (`set_manual_override_duration`) and
  whether that duration-based action is currently available. The card maps this
  minimal action to a fixed one-hour override.
- Missing implementation work: expose richer termination capabilities, define a
  fuller capability policy, and consider structured frontend errors.
- Required tests: override set behavior through backend action, invalid
  termination combinations, unknown room, targeted notification only,
  frontend-facing state after override.

### Clear room override / resume schedule

- Purpose: clear the room override and resume backend schedule/global control.
- Input: area ID, profile ID, or primary climate entity ID.
- Validation responsibility: backend validates target room.
- Output or state effect: clears manual override and notifies only the targeted
  profile.
- Existing implementation support: `clear_area_override` service and
  `GlobalRuntime.async_clear_area_override(...)`.
- Increment 3.3c implementation support: room climate entity attributes expose
  `can_clear_override` and active manual override details so the frontend does
  not infer lifecycle state from rules or timestamps.
- Missing implementation work: stable room action identity and richer
  frontend-facing error handling.
- Required tests: override clear behavior through backend action, unknown room,
  idempotence or explicit error policy, frontend-facing state after clear.

### Read degraded-state summary

- Purpose: show basic degraded-state indication in overview without scanning and
  interpreting every entity in the frontend.
- Input: none, or config entry identifier if multiple entries are supported.
- Validation responsibility: backend owns degraded-state vocabulary and summary
  semantics.
- Output or state effect: aggregate summary plus per-room degraded status.
- Existing implementation support: room climate entities expose
  `degradation_status` when degraded/fallback is active.
- Missing implementation work: no aggregate degraded-state provider.
- Required tests: no degraded rooms, required-component fallback, unavailable
  optional source behavior, multi-room mixed status.

## 5. Gap analysis

### Already implemented

- Existing room/profile persistence under `rooms`.
- Runtime `RegulationProfileConfig` for activated profiles.
- One HA climate entity per activated profile.
- Increment 3.3 custom card rendering of activated room climate entities from
  existing backend-owned Home Assistant state.
- Increment 3.3a WebSocket candidate discovery and one-room activation from the
  custom card.
- Integration-wide global mode select entity.
- Backend-owned rule priority, target resolution, schedule evaluation, manual
  override lifecycle, window override lifecycle, fallback behavior, and service
  execution.
- Area-scoped `set_area_override` and `clear_area_override` services.
- Current explanatory attributes for active context, next change, override end,
  required-component degradation, and global select settings.

### Implemented but Options-Flow-coupled

- Room activation through the Options Flow and the Increment 3.3a WebSocket
  command.
- Room configuration update.
- Room removal/disable.
- Candidate selection through HA selectors.
- Duplicate HA area validation.
- Primary climate area requirement validation.
- Schedule start/end entry and identical start/end rejection.
- Window custom temperature follow-up validation.
- Most room configuration normalization from selector-shaped payloads.

The minimal Increment 3.2 room-management entry point moves duplicate primary
climate validation into a pure backend-owned operation that can be reused by the
current Options Flow and a future frontend-facing entry point. Duplicate
Home Assistant area validation remains HA-registry-/adapter-near because it
requires resolving entity and device registry context. The current Options Flow
continues to own that validation until a candidate or registry adapter exists.

### Layer boundaries for extraction

Domain/application-owned logic includes room/profile value normalization,
room/profile invariant validation, schedule validation, and target/window
configuration validation.

Home Assistant adapter logic includes selector payload handling, entity registry
lookup, area/device registry lookup, Options Flow form schema construction, and
strings/localization keys.

Runtime logic includes active room configs, overrides, schedule evaluation,
target resolution, and subscriber notification.

Reusable validation modules should keep Home Assistant-specific Options Flow and
registry details out of backend-owned validation. Adapter-specific helpers may
exist when needed, but they should be named and scoped as adapter helpers.

### Partially implemented

- Stable room/profile identity: runtime has `profile_id`, but it is derived from
  `primary_climate_entity_id` and is not persisted.
- Area identity: runtime resolves `area_id`, but room options do not persist it
  and room climate entities do not expose it.
- Room overview state: HA entities expose fragments, but no backend-owned room
  overview shape exists.
- Room detail state: runtime and entity state contain most raw inputs, but
  schedule summary, capabilities, optional source states, and global mode
  influence are missing.
- Global mode control: backend action exists, but global state is not included in
  a room/frontend state provider.
- Override control: services exist, but room state does not expose capability
  metadata or an explicit active override object.
- Degraded-state indication: per-room attribute exists, aggregate summary does
  not.

### Missing backend operation

- List activated rooms.
- Update room configuration outside Options Flow.
- Disable room outside Options Flow.
- Update room schedule outside Options Flow.
- Validate room schedule outside Options Flow.
- Read aggregate degraded-state summary.

### Missing frontend-facing state

- Complete room state object.
- Durable `profile_id` contract.
- `area_id` in exposed room state.
- Schedule summary.
- Supported override termination capabilities.
- Supported schedule-editing capabilities.
- Supported window behavior capabilities.
- Optional source entity current states for humidity/window.
- Per-room simulation/global-mode influence.
- Aggregate degraded-state summary.

### Missing validation outside Options Flow

- Room activation validation.
- Primary climate missing-area validation.
- Duplicate primary climate validation.
- Duplicate HA area validation.
- Optional humidity/window selection and clearing validation.
- Window action validation.
- Custom window temperature validation.
- Window delay validation.
- Home/away target validation.
- Daily schedule start/end validation.
- Identical schedule start/end rejection.
- Temperature range validation for room overrides beyond service selector
  metadata.

### Missing migration/persistence support

- Migration-safe durable profile IDs for existing `rooms` entries.
- Compatibility tests for existing flat `rooms` options once stable IDs are
  introduced.
- A backend-owned mutation layer that updates the existing `rooms` persistence
  without introducing a competing storage format.
- Explicit migration policy for preserving existing primary-climate-derived
  profiles while adding durable identifiers.

## 6. Proposed implementation sequence

1. Extract reusable room/profile normalization and pure validation out of
   `custom_components/climate_relay_core/config_flow.py` without changing
   behavior. Do not add services, WebSocket APIs, config subentries, frontend
   APIs, or a new persistence shape in this step.
2. Introduce backend-owned room configuration service/application functions that
   update the existing `rooms` options format.
3. Add stable room/profile identifiers if missing, including migration tests for
   existing primary-climate-derived profiles.
4. Add a frontend-facing room state adapter or diagnostic/state provider that
   assembles overview/detail state from runtime and HA entity state.
5. Add schedule validation/update operations independent of Options Flow for the
   initial all-days schedule model.
6. Add migration tests for existing `rooms` options, including flat schedule
   fields and optional humidity/window fields.
7. Only then build or wire the frontend against the backend-owned contract.
8. Only after frontend acceptance, reduce or remove room-level Options Flow
   surfaces.

## 7. Tests required before frontend work

The following tests are required before frontend work depends on the backend
contract:

- Room activation validation.
- Primary climate missing area.
- Duplicate primary climate.
- Duplicate Home Assistant area.
- Optional humidity selection and clearing.
- Optional window selection and clearing.
- Window action validation.
- Custom window temperature validation.
- Window delay validation.
- Home target validation.
- Away target type and temperature validation.
- Daily schedule start/end validation.
- Identical schedule start/end rejection.
- Schedule persistence and reload.
- Existing `rooms` compatibility.
- Existing flat schedule field compatibility.
- Stable profile ID migration and reload.
- Override set behavior through backend action.
- Override clear/resume behavior through backend action.
- Override termination validation.
- Unrelated room unaffected by targeted override.
- Frontend-facing room state shape generation.
- Frontend-facing state for optional humidity/window values.
- Frontend-facing state for degradation/fallback.
- Frontend-facing global mode and effective presence projection.
- Aggregate degraded-state summary generation.

## 8. Non-goals

- No frontend implementation in this task.
- No Options Flow extension.
- No config subentries introduction.
- No deletion of the current Options Flow room/profile manager.
- No new persistence format.
- No TypeScript rule evaluation.
- No service-call-only daily-use UX as the target state.
- No duplication of backend rule logic in frontend-oriented code.
- No room-level product UX expansion in Home Assistant Options Flow.

## 9. Recommended next Codex task

Extract reusable room/profile normalization and pure validation from
`custom_components/climate_relay_core/config_flow.py` into a backend-owned module
without changing behavior. Keep Options-Flow-specific selector unwrapping,
schema construction, localized error mapping, and Home Assistant registry lookup
in the adapter layer unless a helper is explicitly designed as an adapter
helper.
