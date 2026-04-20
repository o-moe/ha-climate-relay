# Requirements Specification

## 1. Document control

- Document type: Software Requirements Specification (reviewed working baseline)
- System of interest: ClimateRelayCore
- Baseline date: 2026-04-20
- Document language: English
- Status: Reviewed working baseline

This specification consolidates the requirements that are currently visible in
the repository discussions, architecture notes, domain rules, and tests. It is
intended to turn previously loose product discussions into a verifiable
requirements baseline.

The structure and wording of this document are aligned with current,
widely-recognized requirements engineering practice:

- ISO/IEC/IEEE 29148:2018 for requirements engineering information items and
  requirement quality criteria
- IREB terminology and distinction between functional requirements, quality
  requirements, and constraints

Requirement statements in this document are written to be:

- necessary
- unambiguous
- verifiable
- implementation-independent where possible
- uniquely identifiable

Status terms used in this document:

- Confirmed by implementation: already evidenced by current code and tests
- Confirmed direction: agreed requirement baseline, not necessarily fully implemented yet
- Draft: intentionally left open and requires later refinement

## 2. Purpose and scope

ClimateRelayCore shall provide a backend-first climate control solution for Home
Assistant that organizes behavior around rooms instead of raw entities.

The initial scope of this specification covers:

- backend configuration and runtime behavior
- domain rules for scheduling, presence, window handling, and manual overrides
- integration-level constraints that shape future frontend work

The initial scope does not yet cover:

- a finalized end-user frontend design
- migration of existing Home Assistant automations
- manufacturer-specific capabilities beyond generic Home Assistant entity
  behavior

## 3. Product vision

Users shall be able to manage climate behavior at room level through one
coherent backend model, with deterministic automation behavior and room-specific
configuration, without coupling the solution to a specific thermostat vendor or
frontend implementation.

## 4. Stakeholders

- Primary user: Home Assistant user operating multiple climate-controlled rooms
- Secondary user: Household member affected by comfort and energy-saving
  behavior
- Administrator: Person configuring entities, schedules, and operating modes
- Developer: Contributor extending backend logic, services, and future frontend
- Future frontend consumer: Dashboard or card that reads and manipulates
  backend-owned state

## 5. System context

ClimateRelayCore operates as a Home Assistant custom integration and interacts
with:

- Home Assistant `climate` entities as the controlled room devices
- optional Home Assistant humidity sensors per room
- optional Home Assistant window contacts per room
- optional Home Assistant `person` entities for presence resolution
- a future frontend that consumes backend-owned configuration and state

The backend is the source of truth for behavior. The frontend shall not own rule
evaluation logic.

## 6. Definitions and glossary

- Room: Logical control unit consisting of one primary climate entity and
  optional supporting sensors
- Global mode: Repository-level operating mode with values `auto`, `home`, or
  `away`
- Effective presence: Presence result resolved from global mode and person
  states, with values `home` or `away`
- Effective target: Resolved commandable target for a climate entity, including
  HVAC mode, preset mode, and/or target temperature
- Room target: User-configurable temperature-based desired room state that is
  used as an input to rule evaluation, for example for `home`, `away`,
  schedule blocks, or manual overrides
- Manual room override: Explicit temporary or persistent deviation from schedule
  behavior for one room
- Window override: Temporary room state activated when a configured window is
  open long enough to pass the configured delay
- Schedule time block: Time interval with a defined target state for a room
- Fallback state: Safe default target used when no higher-priority rule provides
  a target

## 7. Assumptions and dependencies

- A Home Assistant instance is available and provides entity state updates.
- Each configured room has exactly one primary `climate` entity.
- Presence is derived only from explicitly configured `person` entities.
- Open-window behavior is limited to actions that can be expressed through
  generic climate capabilities.
- Public repository content remains English-only.

## 8. Business rules and prioritization

The following rule priority is currently established and shall govern effective
room state resolution:

1. Window override
2. Manual room override
3. Effective global mode
4. Room schedule
5. Fallback state

## 9. Functional requirements

### 9.1 Configuration and setup

#### FR-001 Single integration instance

- Statement: The system shall allow only one active ClimateRelayCore
  configuration entry per Home Assistant instance.
- Source: Existing config flow and tests
- Rationale: The product is modeled as one repository-wide control backend.
- Fit criterion: Attempting to create a second configuration entry is rejected
  by the integration.
- Status: Confirmed by implementation

#### FR-002 Named integration setup

- Statement: The system shall provide a user-configurable display name during
  initial setup and shall use `ClimateRelayCore` as the default value.
- Source: Existing config flow and constants
- Rationale: The integration must remain identifiable in Home Assistant UI.
- Fit criterion: The initial config form shows a `name` field with the default
  value `ClimateRelayCore`.
- Status: Confirmed by implementation

### 9.2 Room model

#### FR-010 Room composition

- Statement: The system shall model climate behavior per room.
- Source: Discovery and product goals
- Rationale: The product is intentionally room-centric.
- Fit criterion: Backend configuration and rule evaluation operate on rooms
  rather than directly on unrelated entity lists.
- Status: Confirmed direction

#### FR-011 Primary climate entity

- Statement: Each room shall reference exactly one primary Home Assistant
  `climate` entity.
- Source: Existing requirements baseline
- Rationale: A room requires one authoritative actuator target.
- Fit criterion: Room configuration is invalid unless exactly one primary
  `climate` entity is assigned.
- Status: Confirmed direction

#### FR-012 Optional humidity sensor

- Statement: Each room may reference one humidity sensor.
- Source: Discovery and product goals
- Rationale: Humidity is optional supporting room context.
- Fit criterion: A room remains valid with or without a configured humidity
  sensor.
- Status: Confirmed direction

#### FR-019 Humidity as optional display context

- Statement: If a room has a configured humidity sensor, the humidity value
  shall be treated as optional display and hint context and shall not affect the
  control rule evaluation.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Humidity can add useful room context without increasing the
  complexity or unpredictability of the climate control logic.
- Fit criterion: The system can expose humidity values for room display, while
  rule evaluation remains unchanged whether the humidity sensor is configured or
  not.
- Status: Confirmed direction

#### FR-013 Optional window contact

- Statement: Each room may reference one window contact.
- Source: Discovery and product goals
- Rationale: Open-window automation is optional per room.
- Fit criterion: A room remains valid with or without a configured window
  contact.
- Status: Confirmed direction

#### FR-020 Optional sensor degradation

- Statement: If an optional room sensor becomes unavailable, the system shall
  continue operating the room as far as possible without that sensor input.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Optional context loss should not unnecessarily block core room
  control.
- Fit criterion: Loss of an optional humidity sensor or optional window contact
  does not prevent continued room control based on the remaining valid inputs.
- Status: Confirmed direction

#### FR-021 Optional sensor availability indication

- Statement: If an optional room sensor becomes unavailable, the system shall
  expose this condition so that the frontend can show a user-visible warning or
  indication.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users should be aware that optional context is currently missing.
- Fit criterion: Optional sensor unavailability is available as room state or
  status information for UI visualization.
- Status: Confirmed direction

#### FR-014 Room-specific targets

- Statement: Each room shall support separate `home` and `away` target
  definitions.
- Source: Existing requirements baseline
- Rationale: Presence-aware automation requires room-specific occupancy targets.
- Fit criterion: For each room, configuration supports distinct target values
  for `home` and `away`.
- Status: Confirmed direction

#### FR-017 Room target structure

- Statement: A room target shall be temperature-based and shall support at
  least an absolute target temperature and may additionally support relative
  temperature adjustment.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users need both explicit temperatures and simple setback or boost
  behavior, while HVAC mode and preset handling remain backend/device concerns.
- Fit criterion: The target model can represent an absolute temperature and a
  relative temperature delta.
- Status: Confirmed direction

#### FR-072 Relative target reference

- Statement: If a room target uses relative temperature adjustment, the
  adjustment shall be applied relative to the room's currently valid target
  temperature at the time of evaluation.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Relative targets should adapt from the room's current intended
  state instead of requiring a separate static reference model.
- Fit criterion: A relative room target is resolved by adding its temperature
  delta to the room's currently applicable target temperature.
- Status: Confirmed direction

#### FR-018 Away target variants

- Statement: A room's `away` target shall support both a fully explicit target
  state and temperature adjustment relative to another baseline target.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Away behavior must be configurable either as a fixed setpoint or
  as a setback/boost relative to normal room behavior.
- Fit criterion: `away` configuration supports both absolute and relative
  target definition forms.
- Status: Confirmed direction

#### FR-015 Room schedule

- Statement: Each room shall support a configurable schedule.
- Source: Existing requirements baseline
- Rationale: Automated target changes must be time-based at room level.
- Fit criterion: Each configured room can store and evaluate a schedule.
- Status: Confirmed direction

#### FR-016 Manual override policy

- Statement: Each room shall support configurable manual override termination
  behavior.
- Source: Existing requirements baseline
- Rationale: Users need predictable handling after manual intervention.
- Fit criterion: Room configuration supports the allowed override termination
  policies defined in this specification.
- Status: Confirmed direction

### 9.3 Global mode and presence

#### FR-022 Supported global modes

- Statement: The system shall support the global modes `auto`, `home`, and
  `away`.
- Source: Rules, requirements, and domain tests
- Rationale: These modes define the core product operating model.
- Fit criterion: The domain model accepts exactly these global mode values.
- Status: Confirmed by implementation

#### FR-023 Presence resolution in auto mode

- Statement: When global mode is `auto`, the system shall resolve effective
  presence to `home` if at least one configured person entity is in state
  `home`; otherwise it shall resolve effective presence to `away`.
- Source: Rules and domain tests
- Rationale: Auto mode is presence-aware rather than manually fixed.
- Fit criterion: Domain evaluation returns `home` for any configured set that
  contains at least one person with state `home`, and `away` otherwise.
- Status: Confirmed by implementation

#### FR-024 Manual home mode

- Statement: When global mode is `home`, the system shall resolve effective
  presence to `home` regardless of configured person states.
- Source: Rules and domain tests
- Rationale: Manual global override must take precedence over live presence.
- Fit criterion: Effective presence is `home` even if every person entity is
  away.
- Status: Confirmed by implementation

#### FR-025 Manual away mode

- Statement: When global mode is `away`, the system shall resolve effective
  presence to `away` regardless of configured person states.
- Source: Rules and domain tests
- Rationale: Manual global override must take precedence over live presence.
- Fit criterion: Effective presence is `away` even if one or more configured
  persons are home.
- Status: Confirmed by implementation

#### FR-026 Non-expiring manual global override

- Statement: Manual global `home` and `away` selections shall not expire
  automatically.
- Source: Rules document
- Rationale: Global mode changes must remain stable until changed explicitly.
- Fit criterion: After manual selection of `home` or `away`, the effective mode
  remains unchanged until a user or service changes it.
- Status: Confirmed direction

#### FR-027 No intermediate effective presence state

- Statement: The system shall not introduce an intermediate effective presence
  state beyond `home` and `away`.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Presence handling must remain deterministic and easy to understand
  in both automation and UI.
- Fit criterion: Effective presence resolution always results in either `home`
  or `away`.
- Status: Confirmed direction

#### FR-028 Configurable handling of unknown presence states

- Statement: The system shall provide a global configuration option that defines
  how `unknown` and `unavailable` configured person states are interpreted
  during automatic presence resolution.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users may prefer conservative or permissive handling of uncertain
  presence information.
- Fit criterion: The global configuration allows selection of the handling rule
  for `unknown` and `unavailable` person states in `auto` mode.
- Status: Confirmed direction

#### FR-029 Default unknown-presence mapping

- Statement: By default, the system shall interpret `unknown` and
  `unavailable` configured person states as `not_home` during automatic
  presence resolution.
- Source: Requirements elicitation on 2026-04-20
- Rationale: A conservative default avoids incorrectly assuming occupancy when
  presence information is missing.
- Fit criterion: Without custom configuration, `unknown` and `unavailable`
  person states do not cause effective presence `home`.
- Status: Confirmed direction

#### FR-101 Global simulation mode option

- Statement: The system shall provide a global configuration option that
  enables or disables simulation mode for backend-controlled device actions.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users should be able to observe the intended control behavior
  before allowing the integration to actuate climate devices.
- Fit criterion: The global configuration surface exposes one simulation mode
  option that can be turned on and off without changing the rule model itself.
- Status: Confirmed direction

#### FR-102 Simulation mode disabled by default

- Statement: Simulation mode shall be disabled by default.
- Source: Requirements elicitation on 2026-04-20
- Rationale: A new installation should apply its configured automation behavior
  normally unless the user explicitly opts into dry-run observation.
- Fit criterion: A newly created integration entry does not suppress device
  writes unless the user explicitly enables simulation mode.
- Status: Confirmed direction

### 9.4 Window behavior

#### FR-030 Delayed window activation

- Statement: If a room has a configured window contact, the system shall start a
  configurable delay when the contact opens and shall activate window override
  only if the contact remains open for the full delay.
- Source: Rules document and requirements baseline
- Rationale: Short contact fluctuations shall not trigger unnecessary HVAC
  changes.
- Fit criterion: A window that closes before the delay expires does not activate
  window override.
- Status: Confirmed direction

#### FR-031 Supported window actions

- Statement: The system shall support the window actions `off`,
  `frost_protection`, `minimum_temperature`, and `custom_temperature`.
- Source: Requirements, domain code, and domain tests
- Rationale: Open-window handling must remain configurable yet generic.
- Fit criterion: Backend configuration and domain mapping accept exactly these
  action types.
- Status: Confirmed by implementation

#### FR-032 Off action mapping

- Statement: If the configured window action is `off` and the climate entity
  supports HVAC mode `off`, the system shall set the effective target HVAC mode
  to `off`.
- Source: Domain code and tests
- Rationale: Native switch-off is the preferred low-energy behavior.
- Fit criterion: Window action resolution returns an effective target with
  `hvac_mode = off`.
- Status: Confirmed by implementation

#### FR-033 Frost protection mapping

- Statement: If the configured window action is `frost_protection` and the
  climate entity supports a frost-protection preset, the system shall set the
  effective target preset mode to `frost_protection`.
- Source: Domain code and tests
- Rationale: Devices with explicit frost protection should use it.
- Fit criterion: Window action resolution returns an effective target with
  `preset_mode = frost_protection`.
- Status: Confirmed by implementation

#### FR-034 Minimum-temperature mapping

- Statement: If the configured window action is `minimum_temperature`, the
  system shall set the effective target temperature to the minimum supported
  temperature of the climate entity.
- Source: Domain code and tests
- Rationale: Generic fallback behavior must remain device-compatible.
- Fit criterion: Window action resolution returns the climate entity minimum
  temperature as target temperature.
- Status: Confirmed by implementation

#### FR-035 Custom-temperature mapping

- Statement: If the configured window action is `custom_temperature`, the
  system shall require a configured custom target temperature and shall apply
  that value.
- Source: Domain code and tests
- Rationale: A custom mode without a value is incomplete and unverifiable.
- Fit criterion: Resolution fails validation when no custom temperature is
  configured and returns the explicit target when it is configured.
- Status: Confirmed by implementation

#### FR-036 Capability fallback for unsupported actions

- Statement: If the requested window action cannot be applied through a climate
  entity capability, the system shall fall back to a device-compatible minimum
  temperature target.
- Source: Domain code and tests
- Rationale: The backend must degrade gracefully on limited devices.
- Fit criterion: Unsupported `off` or `frost_protection` behavior resolves to a
  `heat` target with the device minimum temperature.
- Status: Confirmed by implementation for current action mapping

#### FR-037 Re-evaluate room state after window close

- Statement: When an active window override ends because the window closes, the
  system shall trigger a full reevaluation of the room state using the rules
  that are valid at close time.
- Source: Requirements elicitation on 2026-04-20
- Rationale: The room should return to the currently correct state rather than
  an outdated pre-window snapshot.
- Fit criterion: After window close, the resolved room target matches the
  result of normal rule evaluation at that time.
- Status: Confirmed direction

Examples:

- Given a room with an active window override and a scheduled target of 21 C,
  when the schedule changes to 18 C while the window remains open and the
  window is then closed, then the resolved room target is 18 C.
- Given a room with an active window override while global mode is effectively
  `home`, when the global mode changes so that the effective state at close time
  is `away` and the window is then closed, then the resolved room target is the
  room's `away` target.
- Given a room with an active window override and no active manual override,
  when a manual override to 23 C for 2 hours is created while the window
  remains open and the window is then closed, then the resolved room target is
  the manual override target.

### 9.5 Manual room overrides

#### FR-040 Manual room override support

- Statement: The system shall allow manual override of a room's effective target
  through backend-owned interactions such as integration actions or future UI
  actions.
- Source: Rules document
- Rationale: Users need explicit room-level intervention independent of
  schedules.
- Fit criterion: The backend exposes a way to set a room-specific override
  target.
- Status: Confirmed direction

#### FR-070 Room-scoped override operations

- Statement: Backend operations for creating, changing, or clearing manual
  overrides shall be scoped to one room at a time.
- Source: Requirements elicitation on 2026-04-20
- Rationale: The domain model is room-centric, and room-level operations remain
  clear, composable, and easier to reason about than special bulk semantics.
- Fit criterion: The backend interface supports manual override operations per
  room rather than requiring dedicated multi-room domain commands.
- Status: Confirmed direction

#### FR-073 Minimal runtime command set

- Statement: The backend shall provide a minimal runtime command set that
  supports changing global mode, setting a room-specific manual override, and
  clearing a room-specific manual override.
- Source: Requirements elicitation on 2026-04-20
- Rationale: These commands cover the currently identified runtime control needs
  without exposing unnecessary domain operations.
- Fit criterion: The runtime interface supports commands equivalent to
  `set_global_mode`, `set_room_override`, and `clear_room_override`.
- Status: Confirmed direction

#### FR-091 Global mode action schema

- Statement: The runtime command for changing global mode shall accept exactly
  one mode parameter whose allowed values are `auto`, `home`, and `away`.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: The action should be simple, bounded, and aligned with the global
  mode domain model.
- Fit criterion: The action equivalent to `set_global_mode` requires one mode
  input and rejects values outside `auto`, `home`, and `away`.
- Status: Confirmed direction

#### FR-071 UI-orchestrated batch actions

- Statement: Convenience actions affecting multiple rooms may be implemented by
  the frontend as orchestration of multiple room-scoped backend operations and
  shall not require separate domain-specific backend batch functions.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Batch behaviors such as clearing all overrides or applying the same
  temporary action to many rooms are interaction conveniences rather than core
  domain concepts.
- Fit criterion: The backend remains centered on room-scoped operations, while
  the frontend can compose multiple calls for multi-room actions.
- Status: Confirmed direction

#### FR-045 Manual override input model

- Statement: A manual room override shall be created by setting an absolute
  target temperature for the room.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Manual room interaction should remain simple and directly reflect a
  user changing the room temperature.
- Fit criterion: Manual override creation accepts an absolute target
  temperature, not a relative delta, HVAC mode, or preset mode.
- Status: Confirmed direction

#### FR-092 Room override action schema

- Statement: The runtime command for setting a room override shall accept a room
  identifier, an absolute target temperature, and one termination definition.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: The action schema should capture the full room-level manual intent
  in one bounded command.
- Fit criterion: The action equivalent to `set_room_override` requires a room
  reference, a target temperature, and a termination specification compatible
  with the allowed override termination options.
- Status: Confirmed direction

#### FR-093 Override termination parameter structure

- Statement: The override termination definition shall consist of a termination
  type plus exactly the additional parameter required by that type, if any.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: A typed termination payload is easier to validate and less
  ambiguous than a loose collection of optional fields.
- Fit criterion: `duration` requires a duration value, `until_time` requires a
  fixed time value, `next_timeblock` requires no additional parameter, and
  `never` requires no additional parameter.
- Status: Confirmed direction

#### FR-094 Clear override action schema

- Statement: The runtime command for clearing a room override shall accept only
  the room identifier needed to select the room whose manual override is to be
  cleared.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: Clearing an override should be an unambiguous room-scoped action
  with no additional behavioral options in the baseline.
- Fit criterion: The action equivalent to `clear_room_override` requires a room
  reference and no override-specific payload beyond room selection.
- Status: Confirmed direction

#### FR-074 Replacing an active room override

- Statement: If a room already has an active manual override, creating a new
  manual override for the same room shall replace the existing override.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Room-level manual interaction should remain direct and should not
  require a separate explicit clear step before applying a new intent.
- Fit criterion: A second `set_room_override` operation for the same room leaves
  exactly one active override, representing the newer command.
- Status: Confirmed direction

#### FR-041 Override termination options

- Statement: The system shall support the manual room override termination
  options `duration`, `until_time`, `next_timeblock`, and `never`.
- Source: Rules document, requirements baseline, and elicitation on 2026-04-20
- Rationale: Users need predictable override lifetimes.
- Fit criterion: Override creation and storage accept exactly these termination
  options.
- Status: Confirmed direction

#### FR-042 Duration-based termination

- Statement: If the override termination option is `duration`, the system shall
  end the override after the configured duration elapses.
- Source: Rules document and elicitation on 2026-04-20
- Rationale: Temporary overrides must expire automatically.
- Fit criterion: A duration-based override becomes inactive after its duration
  expires.
- Status: Confirmed direction

#### FR-046 Minute-precise override duration

- Statement: If the override termination option is `duration`, the configured
  duration shall support minute-level precision.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Override duration should match the schedule precision and support
  real household timing needs.
- Fit criterion: A duration-based override can be set for values such as
  15 minutes, 90 minutes, or 135 minutes.
- Status: Confirmed direction

#### FR-047 Fixed-clock-time termination

- Statement: If the override termination option is `until_time`, the system
  shall keep the override active until a specified fixed clock time and end it
  at that time.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users often think in terms of a specific wall-clock end time rather
  than a relative duration.
- Fit criterion: An override can be created with an explicit end time such as
  `22:30`, after which it becomes inactive.
- Status: Confirmed direction

#### FR-066 Next-occurrence semantics for fixed clock times

- Statement: If a manual override is created with termination option
  `until_time` and the specified clock time has already passed on the current
  day, the system shall interpret the end time as the next occurrence of that
  clock time.
- Source: Requirements elicitation on 2026-04-20
- Rationale: A fixed-clock-time override should remain predictable and should
  not expire immediately because the same-day time has already passed.
- Fit criterion: An override created at `22:00` with end time `06:00` remains
  active until `06:00` on the following day.
- Status: Confirmed direction

#### FR-043 Next-timeblock termination

- Statement: If the override termination option is `next_timeblock`, the system
  shall end the override at the next schedule time block boundary for the room.
- Source: Rules document
- Rationale: Users may want manual intervention only until the next planned
  schedule change.
- Fit criterion: The override becomes inactive when the next schedule block
  starts.
- Status: Confirmed direction

#### FR-044 Persistent override

- Statement: If the override termination option is `never`, the system shall
  keep the override active until it is explicitly cleared.
- Source: Rules document
- Rationale: Some rooms require user-controlled persistent exceptions.
- Fit criterion: The override remains active across normal schedule transitions
  until explicit removal.
- Status: Confirmed direction

#### FR-048 Optional global reset time for manual overrides

- Statement: The system shall support an optional configuration that resets all
  active manual room overrides to the current schedule at a specified clock
  time.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Some users want a daily automatic return from ad hoc manual changes
  to normal scheduled behavior across all rooms.
- Fit criterion: When the option is enabled, all active manual overrides are
  cleared at the configured time and rooms return to the schedule-derived state.
- Status: Confirmed direction

#### FR-049 Global reset option disabled by default

- Statement: The optional global reset time for manual overrides shall be
  disabled by default.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Automatic clearing of overrides changes user intent and must be an
  explicit opt-in behavior.
- Fit criterion: A new installation does not automatically clear manual
  overrides at a daily time unless the user enables this feature.
- Status: Confirmed direction

### 9.6 Scheduling

#### FR-050 Supported schedule layouts

- Statement: The system shall support at least the following schedule layouts:
  one schedule shared across all days, one shared weekday schedule with separate
  Saturday and Sunday schedules, and one fully individual seven-day schedule.
- Source: Requirements baseline
- Rationale: These layouts cover the expected complexity range without forcing
  per-day duplication.
- Fit criterion: Schedule configuration supports all three layout models.
- Status: Confirmed direction

#### FR-053 Unlimited non-overlapping schedule blocks

- Statement: Each supported schedule layout shall allow as many schedule blocks
  as needed, provided that the blocks do not overlap and do not leave gaps
  within the covered schedule timeline.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users need flexible daily planning without ambiguous or undefined
  periods.
- Fit criterion: Schedule validation accepts any number of blocks that fully
  partition the applicable time range without overlaps or gaps, and rejects all
  other combinations.
- Status: Confirmed direction

#### FR-054 Schedule continuity

- Statement: For each configured schedule day or day-group, the schedule shall
  define a continuous sequence of blocks with no overlaps and no uncovered
  period.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Rule evaluation requires a defined target for every point in time
  within the schedule model.
- Fit criterion: At every valid schedule time, exactly one schedule block is
  active for the applicable day or day-group.
- Status: Confirmed direction

#### FR-065 Minute-level schedule boundaries

- Statement: Schedule block boundaries shall support minute-level precision.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Users need fine-grained scheduling without being restricted to a
  coarser fixed interval.
- Fit criterion: Schedule blocks can begin and end at arbitrary minute values
  such as `06:30` or `22:15`.
- Status: Confirmed direction

#### FR-051 Schedule evaluation ownership

- Statement: The backend shall own schedule evaluation logic.
- Source: Architecture and discovery
- Rationale: Time-based behavior must remain deterministic and frontend-agnostic.
- Fit criterion: Effective targets can be resolved without requiring frontend
  code execution.
- Status: Confirmed direction

#### FR-052 Schedule as room input

- Statement: A room's schedule shall participate in effective target resolution
  only after window override, manual room override, and effective global mode
  have been considered.
- Source: Rules priority model
- Rationale: The priority model must be consistent across all room decisions.
- Fit criterion: Rule evaluation never applies the schedule when a higher
  priority context is active.
- Status: Confirmed direction

### 9.7 Fallback behavior

#### FR-055 Exceptional fallback state

- Statement: The system shall define a fallback target for exceptional cases in
  which normal rule evaluation cannot produce a valid room target.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Even if such situations should not occur in normal operation, the
  backend requires deterministic behavior for invalid or incomplete runtime
  states.
- Fit criterion: The specification defines one deterministic fallback result for
  rooms without a valid resolved target.
- Status: Confirmed direction

#### FR-056 Fallback target priority

- Statement: If normal rule evaluation cannot produce a valid room target, the
  system shall first reuse the last valid temperature-based room target known
  for the room. If no such target is known, the system shall use a default
  fallback target of 20 C.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Reusing the last valid target preserves continuity, while a fixed
  default provides deterministic recovery when no prior valid state exists.
- Fit criterion: In fallback situations, the resolved target is either the last
  valid room target or 20 C when no last valid target is available.
- Status: Confirmed direction

#### FR-068 Global fallback target for required device failure

- Statement: The system shall support a globally configurable fallback target
  temperature that is used when a required room control component becomes
  unavailable.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Failure of a required actuator or required control input needs a
  deterministic and user-defined safe behavior.
- Fit criterion: The system configuration includes a global fallback
  temperature for required-component failure situations.
- Status: Confirmed direction

#### FR-069 Required-component failure handling

- Statement: If a required room control component becomes unavailable, the
  system shall treat the room as being in fallback handling and use the global
  fallback target temperature.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Required component loss prevents normal rule evaluation and should
  trigger a defined fallback behavior instead of silent undefined operation.
- Fit criterion: When a required climate entity or another required control
  component is unavailable, the room resolves to the configured global fallback
  target temperature.
- Status: Confirmed direction

### 9.8 Persistence and restart recovery

#### FR-057 Persistent configuration recovery

- Statement: All persisted ClimateRelayCore configuration shall survive a Home
  Assistant restart and shall be reloaded during integration startup.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Configuration must remain stable across restarts and must not
  require manual reconstruction.
- Fit criterion: After restart, configured rooms, schedules, targets, window
  behavior settings, and mode-related configuration remain available without
  re-entry.
- Status: Confirmed direction

#### FR-058 Re-read current device state after restart

- Statement: After restart, the system shall read the current states of the
  configured Home Assistant entities before making new rule decisions.
- Source: Requirements elicitation on 2026-04-20
- Rationale: The elapsed time during downtime is unknown, so prior runtime
  assumptions may be stale or wrong.
- Fit criterion: After startup, rule evaluation uses freshly read entity states
  for climate devices, window contacts, presence entities, and other configured
  room inputs.
- Status: Confirmed direction

#### FR-059 Recompute effective room state after restart

- Statement: After persisted configuration and current entity states have been
  loaded, the system shall recompute the effective state of each room according
  to the normal rule model instead of blindly resuming a pre-restart runtime
  action sequence.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Correct post-restart behavior depends on current facts, not on an
  outdated runtime snapshot.
- Fit criterion: Room targets after restart match the result of normal rule
  evaluation based on loaded configuration and current entity states.
- Status: Confirmed direction

#### FR-063 Persist durable control state

- Statement: The system shall persist durable control state needed for correct
  post-restart rule evaluation, including at least global mode, room-specific
  configuration, and any active manual override that has not yet expired.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Restart recovery requires more than static configuration when user
  choices remain semantically active across time.
- Fit criterion: A restart does not lose non-expired override state or the
  selected global mode.
- Status: Confirmed direction

#### FR-064 Do not resume in-flight window delay timers after restart

- Statement: After restart, the system shall not blindly resume a previously
  running window-delay timer. Instead, it shall read the current window state
  and reevaluate window behavior from that current state.
- Source: Requirements elicitation on 2026-04-20
- Rationale: The elapsed downtime is unknown, so a stored timer start point may
  no longer be valid or meaningful.
- Fit criterion: A restart during a window-delay period does not continue the
  old timer; subsequent behavior depends on the current window state and normal
  rule evaluation.
- Status: Confirmed direction

### 9.9 Backend and frontend separation

#### FR-060 Frontend independence

- Statement: The system shall remain usable as a backend without requiring a
  specific frontend implementation.
- Source: Product goals, discovery, architecture
- Rationale: Behavioral logic must not depend on one dashboard technology.
- Fit criterion: Core climate behavior remains configurable and executable
  without the future TypeScript frontend.
- Status: Confirmed direction

#### FR-075 Home Assistant native state exposure

- Statement: Backend state that naturally fits the Home Assistant state model
  shall be exposed through Home Assistant entities rather than only through
  action responses or custom frontend-only APIs.
- Source: Architecture decision based on Home Assistant developer guidance on
  entities and service action response usage, researched on 2026-04-20
- Rationale: Room and global runtime state should remain reusable for
  dashboards, automations, and other Home Assistant clients.
- Fit criterion: Runtime values such as room state, current targets, warnings,
  and other stable status information are available as Home Assistant state.
- Status: Confirmed direction

#### FR-076 Runtime writes via integration actions

- Statement: Runtime commands from the frontend to the backend shall be exposed
  as Home Assistant integration actions under the integration domain.
- Source: Architecture decision based on Home Assistant developer guidance for
  integration-specific actions, researched on 2026-04-20
- Rationale: Integration-specific commands are expected to be modeled as
  actions, which also makes them available to automations and other Home
  Assistant tooling.
- Fit criterion: Commands equivalent to `set_global_mode`,
  `set_room_override`, and `clear_room_override` are callable as integration
  actions.
- Status: Confirmed direction

#### FR-077 Custom frontend as card and optional strategy

- Statement: The TypeScript frontend shall be implemented as a custom dashboard
  card and may additionally provide a custom dashboard or view strategy for
  generating Lovelace configuration.
- Source: Architecture decision based on Home Assistant frontend developer
  guidance, researched on 2026-04-20
- Rationale: This matches the Home Assistant extension model for custom
  dashboards and keeps dashboard generation separate from control logic.
- Fit criterion: The frontend can render as a custom card, and any automatic
  dashboard generation uses a custom strategy rather than backend-owned UI
  logic.
- Status: Confirmed direction

#### FR-099 Integration distribution as HACS custom repository

- Statement: The Home Assistant integration shall be distributable from its
  public GitHub repository as an `Integration`-type HACS custom repository.
- Source: Home Assistant ecosystem distribution decision on 2026-04-20
- Rationale: HACS custom repositories are the expected installation path for
  community integrations and provide a user-friendly update flow.
- Fit criterion: The integration repository contains the metadata, repository
  structure, documentation, and validation support required for HACS to add it
  as a custom repository of type `Integration`.
- Status: Confirmed direction

#### FR-100 Frontend distribution as separate HACS dashboard repository

- Statement: The future custom frontend shall be distributable as a separate
  public GitHub repository of type `Dashboard` in HACS and shall not be
  coupled to installation of the backend integration package.
- Source: Home Assistant ecosystem distribution decision on 2026-04-20
- Rationale: HACS handles integrations and dashboard elements as different
  repository types with different packaging rules, and users should be able to
  install or update the UI independently from the backend.
- Fit criterion: The frontend card or strategy is packaged in a separate
  repository with the distributable dashboard assets expected by HACS for a
  `Dashboard` repository.
- Status: Confirmed direction

#### FR-103 Simulation mode suppresses device writes

- Statement: When simulation mode is enabled, the system shall continue rule
  evaluation, state updates, and diagnostics processing, but it shall not send
  active write commands to climate devices or other controlled devices.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Dry-run operation is useful only if the full decision path still
  executes while external side effects are suppressed.
- Fit criterion: With simulation mode enabled, the backend still computes the
  effective target and exposes the same explanatory state, while device-write
  operations are skipped.
- Status: Confirmed direction

#### FR-104 Simulation mode logs intended actions

- Statement: When simulation mode suppresses a device write, the system shall
  log the intended action clearly enough for an operator to verify what would
  have been sent.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Simulation mode must provide observable evidence of intended
  control behavior or it does not help users validate automation safely.
- Fit criterion: Operator-readable logs identify suppressed actions together
  with the intended target or command that would otherwise have been issued.
- Status: Confirmed direction

#### FR-078 Strategy shall not own business logic

- Statement: A custom dashboard or view strategy shall generate configuration
  only and shall not become the owner of room control rules or state
  derivation.
- Source: Requirements engineering decision derived from the backend-first
  architecture and Home Assistant strategy model, researched on 2026-04-20
- Rationale: Strategies are for generating dashboard configuration, while rule
  evaluation belongs in the backend.
- Fit criterion: Room targets, override resolution, schedule evaluation, and
  fallback logic remain backend-owned even when a custom strategy is used.
- Status: Confirmed direction

#### FR-079 Frontend reads Home Assistant state

- Statement: The custom frontend shall read runtime state through Home
  Assistant's state context and subscriptions instead of using a separate
  frontend-specific backend protocol for ordinary room status.
- Source: Architecture decision based on Home Assistant custom card developer
  guidance, researched on 2026-04-20
- Rationale: Reading the Home Assistant state directly aligns the frontend with
  native platform behavior and avoids redundant transport layers.
- Fit criterion: The frontend obtains ordinary runtime room and global state
  through Home Assistant state access patterns.
- Status: Confirmed direction

#### FR-080 Minimal externally exposed entity set

- Statement: The integration shall expose only the Home Assistant entities that
  are necessary to support the intended room-centric control, visualization, and
  automation use cases.
- Source: Requirements elicitation on 2026-04-20
- Rationale: Exposing too many entities increases maintenance cost, UI noise,
  and interface complexity without adding proportional user value.
- Fit criterion: Every exposed integration-owned entity has a clear user-facing
  purpose for control, visualization, warning, or automation.
- Status: Confirmed direction

#### FR-081 Room-level climate entity as primary room surface

- Statement: Each configured room shall be exposed primarily through one
  integration-owned room-level `climate` entity.
- Source: Architecture decision based on Home Assistant climate entity model,
  researched on 2026-04-20
- Rationale: The room behaves from the user perspective like a temperature
  control endpoint, and the `climate` domain is the closest Home Assistant
  native fit for that responsibility.
- Fit criterion: Each room has one integration-owned `climate` entity that
  represents its room-level control state and target temperature behavior.
- Status: Confirmed direction

#### FR-082 Global mode as select entity

- Statement: The global operating mode shall be exposed through one
  integration-owned `select` entity with the options `auto`, `home`, and
  `away`.
- Source: Architecture decision based on Home Assistant select entity model,
  researched on 2026-04-20
- Rationale: Global mode is a bounded choice among a small set of options and
  does not have a better fitting built-in entity model.
- Fit criterion: Home Assistant exposes one `select` entity whose current option
  reflects the active global mode and whose options are `auto`, `home`, and
  `away`.
- Status: Confirmed direction

#### FR-083 Avoid mirroring optional context sensors by default

- Statement: Optional room context such as humidity and window state shall not
  be duplicated into additional integration-owned entities by default when the
  frontend can use the configured source entities directly.
- Source: Architecture decision derived from the minimal entity exposure
  principle and Home Assistant entity guidance, researched on 2026-04-20
- Rationale: Mirroring existing source entities would add interface surface and
  database churn without clear functional benefit in the baseline scope.
- Fit criterion: The baseline integration does not create separate mirrored
  humidity or window entities solely for frontend convenience.
- Status: Confirmed direction

#### FR-084 Use attributes sparingly for explanatory room context

- Statement: Additional integration-owned room context that explains the state
  of the room-level `climate` entity may be exposed as extra state attributes,
  but only when that context is necessary for frontend explanation or
  automation and does not justify a separate entity.
- Source: Architecture decision based on Home Assistant entity guidance on extra
  state attributes, researched on 2026-04-20
- Rationale: Home Assistant allows explanatory extra attributes, but excessive
  or rapidly changing attributes should be avoided.
- Fit criterion: Extra room attributes are limited to explanatory context and
  are not used as a dumping ground for every internal intermediate value.
- Status: Confirmed direction

#### FR-085 Minimal explanatory room attributes

- Statement: If explanatory room context is exposed as extra attributes of the
  room-level `climate` entity, the baseline attribute set shall be limited to
  the minimum needed to explain current room behavior and upcoming changes.
- Source: Requirements elicitation on 2026-04-20
- Rationale: The room entity should remain understandable and stable without
  exposing all internal rule-engine details.
- Fit criterion: The baseline attribute set is intentionally small and focused
  on user-relevant explanation.
- Status: Confirmed direction

#### FR-086 Active control context attribute

- Statement: The room-level `climate` entity shall expose the currently active
  control context as an explanatory extra state attribute.
- Source: Architecture decision derived from the minimal entity exposure
  principle and Home Assistant entity guidance, researched and refined on
  2026-04-20
- Rationale: The active control context explains why the room currently has its
  resolved target without requiring a separate entity or frontend-specific
  derivation.
- Fit criterion: The room-level `climate` entity exposes an attribute
  equivalent to `active_control_context`.
- Status: Confirmed direction

#### FR-087 Active control context values

- Statement: The `active_control_context` attribute shall use a bounded set of
  values that reflects the rule source currently determining the room target.
- Source: Requirements elicitation on 2026-04-20
- Rationale: A small fixed vocabulary is easier for UI rendering, automation,
  and long-term interface stability than free-form text.
- Fit criterion: The attribute value is one of `schedule`, `override`,
  `window`, or `fallback`.
- Status: Confirmed direction

#### FR-088 Next change timestamp attribute

- Statement: The room-level `climate` entity shall expose the next scheduled or
  rule-driven room target change time as an explanatory extra state attribute
  when such a future change is known.
- Source: Architecture decision derived from the agreed room UI needs and the
  minimal attribute model, refined on 2026-04-20
- Rationale: Showing the next expected change is directly useful in the room UI
  and explains how long the current target is expected to remain active.
- Fit criterion: The room-level `climate` entity exposes an attribute
  equivalent to `next_change_at` whenever the next relevant change time is known.
- Status: Confirmed direction

#### FR-095 Time attribute serialization

- Statement: Time-based explanatory attributes exposed by the integration shall
  use one consistent timestamp serialization format that includes date, time,
  and offset information.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: A single explicit timestamp format reduces ambiguity for frontend
  parsing, logging, and test verification.
- Fit criterion: Attributes such as `next_change_at` and `override_ends_at`
  use the same offset-aware timestamp representation.
- Status: Confirmed direction

#### FR-096 Local-time basis for serialized timestamps

- Statement: Serialized time attributes shall represent the relevant time in the
  configured local time zone rather than as ambiguous naive local strings.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: User-facing schedule and override times are defined in local wall
  time and therefore require explicit local-zone interpretation.
- Fit criterion: Time attributes are serialized with explicit offset
  information corresponding to the configured local time zone.
- Status: Confirmed direction

#### FR-089 Override end timestamp attribute

- Statement: If a manual override is active and has a known end time, the
  room-level `climate` entity shall expose that end time as an explanatory extra
  state attribute.
- Source: Architecture decision derived from the agreed room UI needs and the
  minimal attribute model, refined on 2026-04-20
- Rationale: Users need to see when a temporary override will stop without the
  frontend having to reconstruct the end condition.
- Fit criterion: The room-level `climate` entity exposes an attribute
  equivalent to `override_ends_at` only when an override is active and a
  concrete end time exists.
- Status: Confirmed direction

#### FR-090 Degradation status attribute

- Statement: The room-level `climate` entity shall expose a compact degradation
  or warning status as an explanatory extra state attribute when optional sensor
  loss or required-component fallback affects room operation.
- Source: Architecture decision derived from the agreed failure-handling model
  and the minimal attribute model, refined on 2026-04-20
- Rationale: The frontend should be able to highlight degraded operation
  without requiring many dedicated warning entities.
- Fit criterion: The room-level `climate` entity exposes an attribute
  equivalent to `degradation_status` when degraded or fallback operation is
  relevant to the room.
- Status: Confirmed direction

#### FR-097 Degradation status vocabulary

- Statement: The `degradation_status` attribute shall use a bounded vocabulary
  rather than free-form text.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: A controlled value set is easier to test, document, localize, and
  render consistently in the frontend.
- Fit criterion: The attribute value is selected from a documented bounded set.
- Status: Confirmed direction

#### FR-098 Degradation status values

- Statement: In the baseline scope, the bounded `degradation_status`
  vocabulary shall contain at least `optional_sensor_unavailable` and
  `required_component_fallback`.
- Source: Requirements engineering refinement on 2026-04-20
- Rationale: The baseline must distinguish between degraded operation with
  optional context loss and fallback operation caused by required control
  component failure.
- Fit criterion: UI and tests can distinguish these two degradation cases by
  attribute value without parsing free-form messages.
- Status: Confirmed direction

#### FR-061 Backend-owned behavior

- Statement: The frontend shall not become the primary owner of rule logic for
  scheduling, presence, override resolution, or window behavior.
- Source: Architecture
- Rationale: Business rules must remain deterministic and testable in the
  backend.
- Fit criterion: These behaviors are defined and testable in backend-owned
  services or domain logic.
- Status: Confirmed direction

#### FR-062 Future frontend capabilities

- Statement: The future frontend shall support room overview, room detail
  dialogs, schedule editing, and global mode controls by consuming
  backend-owned interfaces.
- Source: Architecture
- Rationale: Frontend scope should be visible early, even if not yet fully
  specified.
- Fit criterion: Future UI design work traces back to these capability areas.
- Status: Draft, UX details open

#### FR-067 Optional humidity-based UI hints

- Statement: A future frontend may provide humidity-based visual hints such as
  prominent ventilation recommendations, colors, or pictograms, but such hints
  shall not change backend control behavior.
- Source: Requirements elicitation on 2026-04-20
- Rationale: UI hints can help users interpret room conditions without coupling
  humidity display to automatic climate control decisions.
- Fit criterion: Any humidity-based frontend hint remains informational and does
  not modify room targets, overrides, or window logic.
- Status: Confirmed direction

## 10. Quality requirements and constraints

### 10.1 Repository and documentation constraints

#### QR-001 English-only public content

- Statement: Public repository content shall remain in English.
- Source: Engineering standards
- Fit criterion: Public-facing repository files are written in English.
- Status: Confirmed

#### QR-002 No manufacturer references

- Statement: Public repository content shall avoid external manufacturer
  references.
- Source: Engineering standards
- Fit criterion: Documentation and public product language remain vendor-neutral.
- Status: Confirmed

### 10.2 Architecture and maintainability

#### QR-010 Testable pure backend behavior

- Statement: Public backend behavior shall be testable without requiring Home
  Assistant runtime dependencies in the domain layer.
- Source: Requirements baseline and architecture
- Fit criterion: Core rule logic can be exercised through pure Python tests.
- Status: Confirmed

#### QR-011 Separation of concerns

- Statement: Domain logic shall remain separated from Home Assistant-specific
  adapters.
- Source: Architecture and engineering standards
- Fit criterion: Pure rule logic resides outside infrastructure adapters and can
  be tested independently.
- Status: Confirmed

#### QR-012 Minimal public interface complexity

- Statement: The public integration surface shall remain intentionally small and
  expose only the entities, actions, and attributes needed for the agreed
  baseline use cases.
- Source: Requirements baseline and architecture decisions
- Fit criterion: Newly proposed public entities, actions, or attributes require
  explicit requirement justification before being added.
- Status: Confirmed

### 10.3 Performance and responsiveness

#### QR-020 Bounded rule evaluation latency

- Statement: Pure rule evaluation for a single room shall complete quickly
  enough that user-triggered changes and ordinary state updates do not feel
  delayed.
- Source: Requirements engineering refinement on 2026-04-20
- Fit criterion: In automated tests on the supported development baseline,
  single-room domain rule evaluation completes well below 100 ms.
- Status: Confirmed direction

#### QR-021 Efficient room update scaling

- Statement: Room state updates shall scale linearly with the number of affected
  rooms and shall not require full-system reevaluation when one unrelated room
  changes.
- Source: Requirements engineering refinement on 2026-04-20
- Fit criterion: Architecture and tests show that an event affecting one room
  reevaluates only that room and any explicitly dependent global logic.
- Status: Confirmed direction

### 10.4 Reliability and recoverability

#### QR-030 Deterministic degraded behavior

- Statement: Sensor loss, unsupported capabilities, and restart recovery shall
  lead to deterministic behavior rather than undefined intermediate states.
- Source: Requirements baseline and elicitation
- Fit criterion: For each supported degradation case, the system reaches a
  documented effective state or fallback path.
- Status: Confirmed direction

#### QR-031 Restart-safe recomputation

- Statement: After restart, the system shall recompute room state from
  persisted configuration and current entity values without assuming that
  pre-restart timing information is still valid.
- Source: Restart requirements baseline
- Fit criterion: Restart-focused integration tests confirm recomputation from
  current facts instead of blind continuation of stale runtime sequences.
- Status: Confirmed direction

### 10.5 Observability and diagnosability

#### QR-040 User-visible degraded-state indication

- Statement: Degraded or fallback operation that affects user understanding
  shall be visible through exposed room state suitable for UI indication.
- Source: Requirements elicitation on degraded sensor and component handling
- Fit criterion: Room state exposes enough information for the frontend to
  distinguish normal, degraded, and fallback operation.
- Status: Confirmed direction

#### QR-041 Operator-readable logging

- Statement: The integration shall produce logs that allow a developer or
  advanced user to reconstruct major control transitions and failure causes
  without enabling excessively verbose tracing in normal operation.
- Source: Requirements engineering refinement on 2026-04-20
- Fit criterion: Important events such as startup recovery, fallback entry,
  override creation or replacement, window override activation, and
  simulation-mode suppressed writes can be found in structured or consistently
  worded logs.
- Status: Confirmed direction

### 10.6 Usability and configuration quality

#### QR-050 Consistent user mental model

- Statement: Configuration and runtime control shall preserve a room-centric
  user mental model and avoid exposing unnecessary internal rule-engine
  mechanics.
- Source: Product vision and elicitation
- Fit criterion: The primary runtime controls map directly to room temperature
  and global mode concepts rather than low-level device commands.
- Status: Confirmed direction

#### QR-051 Predictable time semantics

- Statement: User-facing time-based behavior shall be interpretable in local
  wall-clock terms and remain predictable across day boundaries.
- Source: Schedule and override elicitation
- Fit criterion: Fixed end times, schedule blocks, and next-change timestamps
  follow documented local-time semantics in tests and examples.
- Status: Confirmed direction

### 10.7 Compatibility and portability

#### QR-060 Home Assistant native integration style

- Statement: The integration shall follow Home Assistant native extension
  patterns for entities, actions, custom cards, and optional strategies instead
  of introducing a parallel proprietary control model.
- Source: Home Assistant architecture research on 2026-04-20
- Fit criterion: Public runtime interaction uses Home Assistant entities and
  actions, frontend integration uses supported custom frontend extension
  points, and distribution follows the expected HACS repository types for
  integrations and dashboard elements.
- Status: Confirmed direction

#### QR-061 Time zone and DST correctness

- Statement: Schedule evaluation, fixed-time overrides, and next-change
  calculation shall use the configured local time zone correctly, including
  daylight-saving transitions.
- Source: Requirements engineering refinement on 2026-04-20
- Fit criterion: Automated tests cover representative local-time and
  day-transition cases, including DST-sensitive behavior where feasible.
- Status: Confirmed direction

### 10.8 Verification and delivery

#### QR-070 Mandatory automated checks

- Statement: Backend changes shall satisfy formatting, linting, tests, coverage,
  and package build checks in local development and CI.
- Source: README and engineering standards
- Fit criterion: Standard commands complete successfully in both local and CI
  workflows.
- Status: Confirmed

#### QR-071 Locked workflow consistency

- Statement: Local development and CI shall use the same locked Python
  dependency workflow.
- Source: Requirements baseline and engineering standards
- Fit criterion: The repository uses `uv`, `pyproject.toml`, and `uv.lock` as
  the authoritative workflow inputs in both environments.
- Status: Confirmed

#### QR-072 Test coverage expectation

- Statement: Public backend behavior shall be covered by unit tests and/or
  integration tests.
- Source: Engineering standards and contributing guidelines
- Fit criterion: New publicly visible backend behavior is not considered done
  until automated tests cover it.
- Status: Confirmed

### 10.9 Verification approach

The following verification methods shall be used for this specification:

- `UT` Unit test: pure domain and rule behavior
- `IT` Integration test: Home Assistant integration behavior, entity exposure,
  config flow, and action wiring
- `AT` Acceptance test or specification by example: user-visible end-to-end
  behavior
- `DR` Design review: architectural and interface conformance review

Verification expectations by requirement class:

- Domain rules and priority behavior shall primarily be verified by `UT` and
  supporting `AT`.
- Home Assistant-facing entities, actions, and restart behavior shall primarily
  be verified by `IT` and supporting `AT`.
- Architecture constraints, minimal entity exposure, and frontend ownership
  boundaries shall primarily be verified by `DR`, with `IT` where feasible.

## 11. Out of scope for this baseline

- Device-specific optimization for individual thermostat vendors
- Final frontend interaction design and visual design system
- Mobile app support outside Home Assistant frontend capabilities
- Energy analytics, reporting, or optimization algorithms beyond rule-based room
  control
- Automatic import of legacy automations from existing Home Assistant setups
- Optional humidity-based dehumidifier control

## 11.1 Future considerations

The following ideas are intentionally not part of the current binding baseline,
but may become future epics after the core climate-control scope is stable.

### FC-001 Optional dehumidifier control

The product may later support an optional room-level dehumidifier entity that is
switched on or off based on measured humidity, configurable thresholds, and
hysteresis.

Possible future requirement themes:

- one optional dehumidifier actuator per room
- configurable humidity target or upper and lower thresholds
- hysteresis to avoid rapid toggling
- purely humidity-driven control that remains separate from heating control
- clear room-level visibility of current dehumidifier state and thresholds

## 12. Review results and remaining gaps

This document has been reviewed for requirement quality with focus on:

- unambiguous wording
- testability and fit criteria
- internal consistency
- explicit handling of out-of-scope topics
- traceability to sources and implementation evidence

The current reviewed baseline is considered strong enough to drive
implementation planning. Remaining gaps are bounded and primarily technical:

- The exact Home Assistant action registration shape is not yet fixed,
  especially entity-service vs integration-action targeting details.
- Future frontend UX details remain intentionally open.

## 13. Key decisions baseline

The following elicitation results are now considered part of the reviewed
baseline:

- Room targets are temperature-based only.
- Relative targets are applied to the room's currently valid target
  temperature.
- `away` supports both absolute and relative target definition.
- Window close triggers full reevaluation using rules valid at close time.
- Manual overrides are room-scoped, absolute-temperature based, and replacing.
- Override termination supports `duration`, `until_time`, `next_timeblock`, and
  `never`.
- Schedule layouts are `Mo-So`, `Mo-Fr + Sa + So`, and individual daily
  schedules.
- Schedule blocks are minute-precise, non-overlapping, and gap-free.
- Optional sensors degrade gracefully with UI-visible indication.
- Required component failure uses a globally configurable fallback temperature.
- Restart reloads persisted configuration, rereads live entity state, and
  recomputes room state.
- The frontend reads Home Assistant state and writes via integration actions.
- The minimal exposed entity model is room-level `climate` plus global `select`
  with sparse explanatory attributes.
- Humidity is informational context only in the baseline.

## 14. Traceability and verification

The detailed requirement-to-verification mapping is maintained in the companion
document [verification-matrix.md](./verification-matrix.md).

### 14.1 Source traceability

- Existing implementation and tests:
  `FR-001`, `FR-002`, `FR-022` to `FR-025`, `FR-031` to `FR-036`
- Existing repository design documents:
  `FR-010` to `FR-016`, `FR-030`, `FR-040` to `FR-044`, `FR-050` to `FR-052`,
  `FR-060` to `FR-062`, `QR-001` to `QR-012`, `QR-070` to `QR-072`
- Requirements elicitation on 2026-04-20:
  `FR-017` to `FR-021`, `FR-026` to `FR-029`, `FR-037`, `FR-045` to `FR-049`,
  `FR-053` to `FR-104`, `QR-020` to `QR-061`
- Home Assistant architecture research on 2026-04-20:
  `FR-075` to `FR-090`, `FR-099`, `FR-100`

### 14.2 Verification traceability

- `UT` priority:
  global mode resolution, window action mapping, override resolution, fallback
  logic, schedule evaluation, restart reevaluation logic
- `IT` priority:
  config flow, entity exposure, action registration and handling, restart
  recovery behavior, attribute exposure, degradation handling
- `AT` priority:
  room scenarios around schedule change, window close, override replacement,
  fallback behavior, and UI-visible explanatory context
- `DR` priority:
  minimal entity surface, backend/frontend ownership boundary, Home Assistant
  idiomatic integration design

### 14.3 Coverage expectations

- Every functional requirement shall trace to at least one planned verification
  method.
- Every implemented public backend behavior shall trace back to at least one
  requirement identifier.
- User-visible behavior added without an identifier in this document shall be
  treated as scope creep until the specification is updated.

## 15. Recommended next steps

1. Derive an implementation backlog grouped into backend domain, Home
   Assistant integration, and frontend work.
2. Define the exact technical action schemas and room attribute serialization
   formats.
3. Create a verification matrix that maps each `FR` and `QR` identifier to
   planned `UT`, `IT`, `AT`, or `DR` activities.
4. Split the reviewed baseline into delivery increments and implementation
   epics.
