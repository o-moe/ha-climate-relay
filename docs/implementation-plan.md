# Implementation Plan

## Purpose

This document derives a prioritized implementation plan from the reviewed SRS in
[requirements.md](./requirements.md), the
[verification matrix](./verification-matrix.md), and the repository baseline in
[README.md](../README.md), [developer-guide.md](./developer-guide.md),
[README.md](../README.md), [architecture.md](./architecture.md),
[architecture.md](./architecture.md),
[discovery.md](./discovery.md), [rules.md](./rules.md),
[engineering-standards.md](./engineering-standards.md),
[product-ux-vision.md](./product-ux-vision.md),
[frontend-interaction-model.md](./frontend-interaction-model.md),
[frontend-backend-contract.md](./frontend-backend-contract.md),
[frontend-repository-strategy.md](./frontend-repository-strategy.md), and
[CONTRIBUTING.md](../CONTRIBUTING.md).

The plan is intentionally backend-first and uses the current implementation
state as the starting point. Backend-first means the backend remains the source
of truth for behavior; it does not mean delaying the first GUI vertical slice
until every backend or Home Assistant surface is complete.

## Plan status

- Status: Approved implementation baseline with Epic 2 UX correction
- Approval date: 2026-04-20
- UX correction date: 2026-05-03
- Decision: proceed with implementation in the defined epic and increment order,
  while preventing permanent room-level product UX from moving into the
  integration-global options flow
- Governance: every increment remains subject to the delivery contract in
  [engineering-standards.md](./engineering-standards.md)

## Current baseline

The repository currently provides only a thin implementation baseline:

- single-instance setup and naming config flow
- integration scaffold and unload lifecycle
- global mode presence resolution for `auto`, `home`, and `away`
- window action mapping with capability fallback
- a frontend scaffold without backend integration

This means the highest-value gaps are still the global configuration model, the
area-bound regulation model, logging and diagnostics, the rule engine, override lifecycle,
persistence, Home Assistant runtime surface, and frontend/backend integration.

## UX correction decision

As of Epic 2 / Increment 2.3, the project distinguishes administrative Home
Assistant setup flows from the target room-level product UI.

The integration options flow may temporarily host room-level configuration
during backend bootstrap work, but this is not the target user experience. New
room-level product behavior shall be specified against the frontend
room-management UI and the frontend/backend contract.

Before adding further room-level options-flow complexity, the project shall
preserve the daily-use frontend interaction model and document how any temporary
options-flow behavior will migrate to the frontend or be removed.

The first frontend slice shall include room overview, room detail, room
activation/configuration, schedule editing for the initially supported schedule
model, quick manual override, clear override / resume schedule, global mode
control, and basic degraded-state indication.

## Global delivery contract

Every increment in this plan is governed by the following mandatory delivery
contract:

- Development is test-first. The first implementation step for each behavior is
  an executable failing test or specification.
- An increment is not done when code exists; it is done only when the behavior
  required by the increment is specified as tests at the required verification
  levels and those tests pass.
- All quality gates must be green before an increment is considered complete:
  formatting, linting, automated tests, required coverage, and package build.
- Documentation must be created or updated within the same increment so that
  requirements, behavior, interfaces, and operating assumptions remain current.
- User-visible changes must update the user-facing `README.md` in the same
  increment.
- Requirements assigned to an increment must be traceable to tests and, where
  applicable, to design-review evidence.
- User-visible Home Assistant GUI/UX changes must include or extend an
  executable iteration acceptance runner in the same increment. The runner is
  part of the delivery artifact and must be usable as regression evidence for
  later iterations.
- GUI/UX acceptance for each increment must be complete for the user flows it
  touches. It must automate successful flows and validation/error paths in the
  real Home Assistant UI, including selector behavior, step transitions,
  persistence, and any affected cancel or close behavior. A happy-path-only GUI
  smoke test is not sufficient for an increment that changes UI/UX behavior.
- When UI configuration controls backend runtime behavior, the increment
  acceptance runner must configure the feature through the UI and then verify
  the resulting backend state or action through Home Assistant state, services,
  or another executable runtime observation.
- Home Assistant option fields that are conditionally required by a selected
  mode, toggle, or action must follow the established dedicated-step pattern
  instead of remaining as always-visible optional fields. The dedicated step
  must explicitly identify the selection that made the field required and must
  expose integration-owned localized validation errors.

## Increment slicing policy

Increments are not sliced only by technical layering. They must also be sliced
so they can be deployed to a Home Assistant instance and evaluated by a product
owner in a meaningful manual acceptance step.

Every increment must therefore satisfy all of the following:

- deliver a user-observable outcome in Home Assistant
- be executable as a bounded acceptance run in the dedicated Home Assistant
  test instance whenever the behavior is automatable
- provide bounded acceptance scope for product-owner sign-off
- still preserve the engineering contract for TDD, quality gates, and
  documentation

Foundational work that has no standalone user value must be bundled into the
smallest vertical slice that does produce observable value in Home Assistant.

## Prioritization logic

The plan is prioritized by dependency and risk:

1. Establish domain contracts before infrastructure.
2. Establish shared configuration and diagnostics foundations before features
   that depend on them.
3. Implement deterministic rule evaluation before Home Assistant exposure.
4. Define frontend interaction contracts before adding further room-level
   options-flow complexity.
5. Implement persistence and degraded behavior before broad release-capable
   user-facing controls.
6. Expose only the backend-owned room-management entry points required by the
   first GUI vertical slice before implementing that slice.
7. Use the first GUI vertical slice as an early validation driver for the
   room-first product model.
8. Keep frontend work strictly dependent on backend-owned state and actions.

## Epic 1: Foundation complete

Goal: establish the product foundation through a tested, installable Home
Assistant baseline with one area-bound regulation profile.

Scope:

- installable integration and HACS-compatible repository layout
- global configuration, global mode handling, diagnostics, and simulation mode
- one primary-climate-anchored regulation profile with HA area semantics
- one integration-owned area climate entity with sparse explanatory attributes
- home and away targets, daily local schedule window, next-change explanation,
  and fallback behavior
- central effective-regulation resolver for manual override, schedule/global
  mode, and fallback priority
- manual area override creation, replacement, clearing, and termination
  semantics through Home Assistant services
- hardened actuation retry behavior, service-boundary validation, timer
  cleanup, and time-semantics coverage

User value: the product can be installed, configured, operated, diagnosed, and
accepted in a real Home Assistant instance for one area-bound regulation
profile.

Product-owner acceptance: one configured area can be controlled by global mode,
schedule, and manual override services; the area climate entity explains active
context, next schedule change, override end time, and degradation state; and
simulation mode allows safe observation without real device writes.

Requirements: `FR-001`, `FR-002`, `FR-010` to `FR-029`, `FR-040` to `FR-056`,
`FR-065`, `FR-066`, `FR-068` to `FR-076`, `FR-080` to `FR-104`, `QR-010` to
`QR-012`, `QR-020`, `QR-021`, `QR-030`, `QR-040`, `QR-041`, `QR-050`, `QR-051`,
`QR-060`, `QR-061`, `QR-070`, and `QR-071`.

Verification focus: `V-UT-001` to `V-UT-008`, `V-IT-001` to `V-IT-007`,
`V-AT-002` to `V-AT-006`, and `V-DR-001` to `V-DR-004`.

Exit criteria: the Epic 1 stable release candidate passes local quality gates,
the Home Assistant API and GUI acceptance suite, and the stable release
boundary documented in [epic-1.md](./epic-1.md).

## Epic 2: Core automation completion

Goal: extend the single-area baseline into the complete deterministic rule
resolver expected from the product.

### Increment 2.1: Window automation and full rule priority

- Scope: add delayed window handling, supported window actions, capability
  fallback, and full rule-priority integration with existing schedule and
  manual behavior.
- User value: window state now influences area control automatically in a way
  that is visible and testable in HA.
- Product-owner acceptance: opening and closing a configured window changes area
  behavior according to the configured delay and action rules, and close-time
  reevaluation behaves correctly.
- Requirements: `FR-030` to `FR-037`, `FR-052`, `QR-030`.
- Verification focus: `V-UT-003`, `V-UT-004`, `V-AT-001`, `V-DR-001`.
- Exit criteria: window automation works end-to-end for one area and completes
  the published rule-priority model.

### Increment 2.2: Multi-area scaling baseline

- Scope: extend the area-centric model from one regulation profile to multiple
  independently controlled primary-climate-anchored profiles across HA areas
  without breaking bounded update behavior.
- User value: the integration becomes useful for a realistic multi-area home
  instead of only a single demonstration area.
- Product-owner acceptance: multiple areas can be configured and operated in HA
  without unrelated area changes forcing full-system behavior changes.
- Requirements: `QR-021`, `QR-050`, `FR-070`, `FR-071`.
- Verification focus: `V-UT-004`, `V-IT-002`, `V-IT-003`, `V-DR-001`.
- Exit criteria: multiple primary-climate-anchored regulation profiles work
  predictably and
  preserve the area-centric
  mental model.

### Increment 2.3: Effective target resolution completion

- Scope: complete remaining fallback and required-component failure behavior so
  the runtime model stays deterministic under unsupported or broken conditions.
- User value: the automation remains usable and understandable even when
  required components fail.
- Product-owner acceptance: failure scenarios in HA lead to documented fallback
  behavior instead of undefined or opaque area state.
- Requirements: `FR-055`, `FR-056`, `FR-069`, `QR-030`, `QR-040`.
- Verification focus: `V-UT-007`, `V-IT-005`, `V-AT-005`, `V-DR-003`.
- Exit criteria: fallback and failure handling are product-owner testable as
  stable user-visible behavior.

## Epic 3: Frontend contract correction and early GUI vertical slice

Goal: prevent room-level product UX from becoming permanent options-flow UX and
validate the room-first GUI early, while adding only the smallest backend-owned
room-management operations required by that GUI slice.

### Increment 3.0: Frontend contract and room-management UX skeleton

- Scope: define the product UX vision, frontend interaction model, and
  frontend/backend contract; introduce the first room-management UI skeleton
  target before further room-level options-flow expansion.
- User value: room-level climate behavior is no longer designed as
  integration-global options-flow configuration.
- Product-owner acceptance: room activation, room schedule editing, and quick
  override are specified as frontend room-management flows, while the existing
  options-flow room configuration is documented as temporary bootstrap
  scaffolding.
- Requirements: `FR-060` to `FR-062`, `FR-071`, `FR-077` to `FR-079`,
  `FR-100`, `QR-050`, `QR-060`.
- Verification focus: `V-DR-001`, `V-DR-002`, `V-DR-003`, `V-AT-004`.
- Exit criteria: product UX docs, frontend interaction model,
  frontend/backend contract, and verification criteria exist and are linked
  from the implementation plan.

### Increment 3.1: Room configuration validation extraction

- Status: completed by the current branch work.
- Scope: behavior-neutral extraction of reusable room/profile normalization and
  pure validation from `config_flow.py` into `room_config.py`.
- Non-scope: no new API, no frontend, no config subentries, no persistence
  change, and no room-level options-flow UX expansion.
- Verification focus: pure helper unit tests plus unchanged options-flow
  behavior coverage.
- Exit criteria: existing `rooms` persistence shape and user-visible Options
  Flow behavior remain unchanged while room/profile normalization can be reused
  by later backend-owned room-management operations.

### Increment 3.2: Minimal backend-owned room-management entry point

- Scope: provide the smallest backend-owned operations required by the first
  GUI vertical slice. The operations shall support activating, updating, and
  disabling one room/profile while preserving the existing `rooms` persistence
  format.
- Non-scope: no broad backend API, no Options Flow UX expansion, no config
  subentries, and no new persistence format.
- Guardrail: no additional room-management backend abstraction may be added
  before the first GUI vertical slice unless it is directly required by that
  vertical slice.
- Verification focus: backend validation and persistence/reload tests for one
  activated, updated, and disabled room/profile using the existing `rooms`
  shape.
- Exit criteria: the first GUI slice has enough backend-owned operations to
  manage one room without mutating Home Assistant config entries directly and
  without expanding the temporary options-flow room manager.

### Increment 3.3: First GUI vertical slice

- Status: completed as the first room-tile rendering slice; extended by
  Increment 3.3a for GUI room activation.
- Scope: deliver the first custom card / dashboard frontend slice that validates
  the room-first UX early. This slice validates daily-use behavior; it is not
  the final frontend.
- Current slice: render activated rooms as room tiles from backend-owned Home
  Assistant climate entity state; show effective target, active control
  context, degradation, next change, and override end; expose quick override
  and resume actions through existing backend services; document missing
  backend-facing activation and schedule-editing operations.
- Full target flow: list eligible Home Assistant areas and climate candidates;
  activate one room through a backend-owned operation; show the activated room
  as a room tile; edit the initially supported daily schedule model; set a
  quick manual override; clear override / resume schedule.
- Constraints: backend remains the source of truth; the frontend does not own
  rule evaluation, schedule evaluation, fallback semantics, degraded-state
  semantics, or persistence semantics.
- Verification focus: executable frontend acceptance for room tile rendering
  and action orchestration; backend/frontend integration evidence for state,
  schedule update, override, clear override, and persistence remains required
  before the full target flow is complete.
- Exit criteria: a product owner can validate the room-first tile experience
  from the GUI without Developer Tools or raw attribute inspection, with
  remaining backend-facing gaps explicitly documented.

### Increment 3.3a: Candidate discovery and GUI room activation

- Scope: add narrow frontend-facing WebSocket commands for room candidate
  discovery and activation of exactly one room from the custom card.
- Implemented flow: the backend lists climate candidates with HA area metadata,
  marks already-active, missing-area, duplicate-primary, and duplicate-area
  candidates as unavailable, and activates one eligible candidate through the
  existing `rooms` options format and `room_management.activate_room(...)`.
  Candidate discovery excludes Climate Relay's own virtual room climate
  entities. Candidate discovery and activation WebSocket commands are
  admin-only.
- Persistence/reload behavior: activation updates config entry options through
  Home Assistant's update mechanism and relies on the existing config-entry
  update listener to reload runtime/entities.
- Frontend behavior: the card renders an `Add room` section, shows unavailable
  reasons, calls the activation command, and shows a waiting-for-state-update
  success message until Home Assistant exposes the new room entity.
- Non-scope: no schedule editor, no schedule update operation, no optional
  sensor setup, no target-temperature setup, no config subentries, no stable
  profile-ID migration, no Options Flow UX expansion, and no frontend-owned
  rule or schedule evaluation.
- Verification focus: backend unit tests for candidate discovery, own-entity
  exclusion, admin-only WebSocket commands, activation, duplicate rejection,
  config-entry update, listener-owned reload behavior, and room-management
  reuse; Vitest/jsdom tests for candidate rendering, activation orchestration,
  activation errors, and preservation of existing room tile rendering.
- Remaining acceptance gap: real Home Assistant / Playwright end-to-end
  acceptance for the custom card is still not present.

## Epic 4: Reliability, recovery, and Home Assistant surface completion

Goal: make the backend reliable under restart and component failure while
keeping native Home Assistant surfaces intentionally small and downstream of
the backend-owned room model.

### Increment 4.1: Durable state persistence and startup recomputation

- Scope: persist global mode, primary-climate-anchored regulation-profile
  configuration, inherited area placement, and active overrides; reload state
  on startup; reread live entity state; recompute area targets.
- Requirements: `FR-057` to `FR-064`, `QR-031`, `QR-061`.
- Verification focus: `V-UT-008`, `V-IT-004`, `V-AT-005`.
- Exit criteria: restart scenarios are covered by integration tests and
  specification-by-example cases, including the rule that window-delay timers
  are not blindly resumed.

### Increment 4.2: Degradation exposure and operator diagnostics

- Scope: surface optional-sensor degradation and required-component fallback in
  runtime state and logs, including an explicit user-facing status or diagnosis
  sensor if the final HA surface still needs one beyond explanatory entity
  attributes.
- Requirements: `FR-020`, `FR-021`, `FR-090`, `FR-097`, `FR-098`, `QR-040`,
  `QR-041`.
- Verification focus: `V-UT-007`, `V-IT-005`, `V-AT-004`, `V-AT-005`,
  `V-DR-003`.
- Exit criteria: degraded and fallback states are visible to both UI consumers
  and operators, with bounded vocabulary, a deliberately chosen HA-facing
  status surface, and test evidence.

### Increment 4.3: Runtime actions and integration orchestration

- Scope: register integration actions for global mode changes and area override
  operations; map validated runtime commands to application services.
- Requirements: `FR-073`, `FR-076`, `FR-091` to `FR-094`, `QR-060`.
- Verification focus: `V-IT-003`, `V-DR-002`, `V-DR-003`.
- Exit criteria: integration actions are fully validated, area-scoped, and
  tested through Home Assistant integration tests.

### Increment 4.4: Entity model and explanatory attributes

- Scope: expose one regulation `climate` entity per configured profile, grouped
  into the inherited HA area, plus one global `select` entity and the minimal
  explanatory attributes.
- Requirements: `FR-075`, `FR-079` to `FR-090`, `FR-095`, `FR-096`,
  `QR-012`, `QR-040`, `QR-060`.
- Verification focus: `V-IT-002`, `V-IT-005`, `V-IT-006`, `V-AT-004`,
  `V-DR-002`, `V-DR-003`.
- Exit criteria: the public entity surface stays intentionally minimal, all
  timestamps serialize consistently in local time with offset, and attribute
  semantics are documented.

## Epic 5: Frontend hardening on top of backend-owned state

Goal: harden and extend the frontend after the first GUI vertical slice without
moving behavioral ownership out of the backend.

Distribution rule for Epic 5:

- the backend integration continues to ship from this repository as an
  `Integration`-type HACS custom repository
- the frontend card/strategy UI shall be packaged for HACS as a separate
  `Dashboard`-type custom repository with its distributable `.js` assets

### Increment 5.1: Frontend state breadth and distribution hardening

- Scope: extend the first GUI vertical slice into a broader custom card reading
  real Home Assistant area/floor structure, backend-owned state, and
  explanatory area attributes.
- Requirements: `FR-060` to `FR-062`, `FR-067`, `FR-077` to `FR-079`,
  `QR-050`, `QR-060`.
- Verification focus: `V-IT-006`, `V-AT-004`, `V-DR-001`, `V-DR-002`.
- Exit criteria: the card renders backend-owned area/global state on top of
  Home Assistant's existing house structure without duplicating rule logic in
  TypeScript.

### Increment 5.2: Frontend control flows and optional strategy

- Scope: add global mode controls, area override flows, and optionally a view
  or dashboard strategy that generates configuration only from the existing HA
  structure.
- Requirements: `FR-062`, `FR-071`, `FR-076`, `FR-077`, `FR-078`.
- Verification focus: `V-AT-004`, `V-DR-001`, `V-DR-002`.
- Exit criteria: frontend writes go through backend actions only, and any
  strategy remains configuration-generation logic rather than business logic.

## Recommended release path

The recommended release path is:

1. `M1 Foundation complete`: Epic 1
2. `M2 Core automation complete`: Increment 2.1, 2.2, 2.3
3. `M3 Frontend contract corrected`: Increment 3.0, 3.1
4. `M4 First GUI vertical slice`: Increment 3.2, 3.3
5. `M5 Reliable Home Assistant baseline`: Increment 4.1 to 4.4
6. `M6 Frontend hardening`: Increment 5.1
7. `M7 Frontend convenience`: Increment 5.2

This sequencing keeps the first GUI slice downstream of the smallest tested
backend-owned room-management contract while preventing room-level product UX
from being permanently shaped by the integration-global options flow.

## Finalization decisions

The plan is finalized with the following binding decisions:

- Backend-first sequencing remains mandatory.
- Backend-first does not mean options-flow-first for room-level product UX.
- No frontend feature may become the owner of behavioral logic.
- Room-level options-flow configuration is temporary bootstrap scaffolding and
  shall be reduced or removed once frontend room management can write to the
  backend-owned configuration model.
- No increment may skip TDD, required verification artifacts, quality gates, or
  documentation updates.
- The first GUI vertical slice is planned before the full reliable Home
  Assistant baseline to validate the product UX early.
- `M6` and `M7` harden and extend frontend work after the first GUI vertical
  slice instead of introducing the first coherent frontend.

## Definition of done per increment

An increment is complete only when all of the following are true:

- linked requirements are implemented
- required `UT`, `IT`, `AT`, and `DR` artifacts for that increment exist or
  are updated
- the increment was developed test-first
- formatting, linting, tests, coverage, and package build are green
- user-facing and engineering documentation are updated
- traceability from requirements to verification remains intact
