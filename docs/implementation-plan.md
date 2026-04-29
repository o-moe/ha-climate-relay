# Implementation Plan

## Purpose

This document derives a prioritized implementation plan from the reviewed SRS in
[requirements.md](./requirements.md), the
[verification matrix](./verification-matrix.md), and the repository baseline in
[README.md](../README.md), [developer-guide.md](./developer-guide.md),
[README.md](../README.md), [architecture.md](./architecture.md),
[architecture.md](./architecture.md),
[discovery.md](./discovery.md), [rules.md](./rules.md),
[engineering-standards.md](./engineering-standards.md), and
[CONTRIBUTING.md](../CONTRIBUTING.md).

The plan is intentionally backend-first and uses the current implementation
state as the starting point.

## Plan status

- Status: Approved implementation baseline
- Approval date: 2026-04-20
- Decision: proceed with implementation in the defined epic and increment order
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
4. Implement persistence and degraded behavior before user-facing controls.
5. Expose the smallest stable Home Assistant surface before richer frontend
   work.
6. Keep frontend work strictly dependent on backend-owned state and actions.

## Epic 1: Vertical foundation slices

Goal: establish the product foundation through increments that already create
observable value in Home Assistant, instead of delivering technical groundwork
in isolation.

### Increment 1.1: Installable integration with global controls and diagnostics

- Scope: deliver an installable integration baseline with global configuration,
  global mode handling, Home Assistant logging, optional verbose/debug mode,
  a global simulation-mode option, one user-visible global control surface in
  HA, and a repository layout that can be installed as an `Integration`-type
  HACS custom repository.
- User value: the product can be installed, configured, operated at global
  level, and diagnosed in a real HA instance.
- Product-owner acceptance: the integration can be added once, exposes the
  agreed global mode control, honors configured global defaults, produces
  readable logs during normal and debug operation, exposes the simulation-mode
  switch with the documented default, and can be installed via HACS as a custom
  repository.
- Requirements: `FR-001`, `FR-002`, `FR-022` to `FR-029`, `FR-048`, `FR-049`,
  `FR-068`, `FR-082`, `FR-101`, `FR-102`, `QR-011`, `QR-012`, `QR-041`,
  `QR-050`, `QR-060`, `QR-070`, `QR-071`.
- Verification focus: `V-UT-001`, `V-UT-002`, `V-IT-001`, `V-IT-002`,
  `V-IT-003`, `V-AT-005`, `V-AT-006`, `V-DR-002`, `V-DR-004`.
- Exit criteria: the integration delivers a manually testable HA baseline with
  global configuration, global mode control, simulation-mode configuration, and
  operator diagnostics.

### Increment 1.2: Single-area regulation foundation with climate entity and target model

- Scope: deliver the first area-centric slice with one regulation profile
  anchored to one primary Home Assistant `climate` entity, one area-level
  `climate` entity, inherited area placement, area home and away targets, and
  minimal explanatory attributes.
- User value: one real Home Assistant area can be represented and inspected in
  HA through the intended regulation model without inventing a parallel house
  structure.
- Product-owner acceptance: a configured area appears as one integration-owned
  climate entity with understandable target behavior, sparse explanatory
  context, and an explicit relationship to the existing HA area model.
- Requirements: `FR-010` to `FR-014`, `FR-017` to `FR-021`, `FR-072`,
  `FR-075`, `FR-080`, `FR-081`, `FR-084` to `FR-087`, `FR-090`, `FR-097`,
  `FR-098`, `QR-010`, `QR-011`, `QR-012`, `QR-040`, `QR-050`.
- Verification focus: `V-UT-004`, `V-UT-007`, `V-IT-002`, `V-IT-005`,
  `V-IT-006`, `V-AT-004`, `V-DR-001`, `V-DR-003`.
- Exit criteria: one primary-climate-anchored regulation profile can be
  configured and
  observed end-to-end in HA with clear area semantics and visible degradation
  signaling.

### Increment 1.3: Single-area schedule and effective target baseline

- Scope: add schedule modeling, next-change calculation, and effective target
  resolution for one primary-climate-anchored regulation profile using global
  mode, schedule, and fallback, together
  with simulation-mode suppression of actual device writes.
- User value: one area now behaves automatically over time and exposes why its
  target is currently active, while users can verify the intended control
  behavior safely before allowing device actuation.
- Product-owner acceptance: the area target changes predictably according to
  schedule and global mode, HA shows the active control context plus next
  change, and simulation mode allows observing intended actions without sending
  writes to real devices.
- Requirements: `FR-015`, `FR-050` to `FR-056`, `FR-065`, `FR-086` to
  `FR-089`, `FR-095`, `FR-096`, `FR-103`, `FR-104`, `QR-020`, `QR-021`,
  `QR-030`, `QR-041`, `QR-051`, `QR-061`.
- Verification focus: `V-UT-004`, `V-UT-006`, `V-UT-007`, `V-IT-006`,
  `V-IT-007`, `V-AT-003`, `V-AT-004`, `V-AT-005`, `V-AT-006`, `V-DR-001`,
  `V-DR-003`.
- Exit criteria: one area delivers predictable scheduled behavior and
  explanatory timing data in HA, and simulation mode suppresses real actuation
  while logging intended control actions.

### Increment 1.4: Single-area manual control baseline

- Scope: add manual area override creation, replacement, clearing, termination
  semantics, and area-scoped runtime actions for one regulation profile.
- User value: the user can override one area manually in HA and understand when
  the override will end.
- Product-owner acceptance: one area override can be set, replaced, and cleared
  through HA-facing controls, and temporary overrides display their end time.
- Requirements: `FR-016`, `FR-040` to `FR-049`, `FR-066`, `FR-070`, `FR-071`,
  `FR-073`, `FR-074`, `FR-076`, `FR-089`, `FR-091` to `FR-094`, `QR-050`,
  `QR-051`, `QR-060`.
- Verification focus: `V-UT-005`, `V-UT-008`, `V-IT-003`, `V-IT-006`,
  `V-AT-002`, `V-AT-004`, `V-DR-002`, `V-DR-003`.
- Exit criteria: one-area manual intervention works end-to-end in HA and is
  product-owner testable as a useful standalone capability.

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

## Epic 3: Reliability and recovery

Goal: make the backend reliable under restart and component failure.

### Increment 3.1: Durable state persistence and startup recomputation

- Scope: persist global mode, primary-climate-anchored regulation-profile
  configuration, inherited area placement, and active overrides; reload state
  on startup; reread live entity state; recompute area targets.
- Requirements: `FR-057` to `FR-064`, `QR-031`, `QR-061`.
- Verification focus: `V-UT-008`, `V-IT-004`, `V-AT-005`.
- Exit criteria: restart scenarios are covered by integration tests and
  specification-by-example cases, including the rule that window-delay timers
  are not blindly resumed.

### Increment 3.2: Degradation exposure and operator diagnostics

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

## Epic 4: Home Assistant surface completion

Goal: expose the smallest correct runtime interface through native Home
Assistant patterns.

### Increment 4.1: Runtime actions and integration orchestration

- Scope: register integration actions for global mode changes and area override
  operations; map validated runtime commands to application services.
- Requirements: `FR-073`, `FR-076`, `FR-091` to `FR-094`, `QR-060`.
- Verification focus: `V-IT-003`, `V-DR-002`, `V-DR-003`.
- Exit criteria: integration actions are fully validated, area-scoped, and
  tested through Home Assistant integration tests.

### Increment 4.2: Entity model and explanatory attributes

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

## Epic 5: Frontend integration on top of backend-owned state

Goal: deliver the first real user-facing frontend without moving behavioral
ownership out of the backend.

Distribution rule for Epic 5:

- the backend integration continues to ship from this repository as an
  `Integration`-type HACS custom repository
- the frontend card/strategy UI shall be packaged for HACS as a separate
  `Dashboard`-type custom repository with its distributable `.js` assets
### Increment 5.1: Dashboard card wired to Home Assistant state

- Scope: replace the static frontend scaffold with a custom card reading real
  Home Assistant area/floor structure, backend-owned state, and explanatory
  area attributes.
- Requirements: `FR-060` to `FR-062`, `FR-067`, `FR-077` to `FR-079`,
  `QR-050`, `QR-060`.
- Verification focus: `V-IT-006`, `V-AT-004`, `V-DR-001`, `V-DR-002`.
- Exit criteria: the card renders backend-owned area/global state on top of
  Home Assistant's existing house structure without
  duplicating rule logic in TypeScript.

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

1. `M1 Foundation complete`: Increment 1.1, 1.2, 1.3, 1.4
2. `M2 Core automation complete`: Increment 2.1, 2.2, 2.3
3. `M3 Reliable runtime`: Increment 3.1, 3.2
4. `M4 Home Assistant usable baseline`: Increment 4.1, 4.2
5. `M5 First coherent frontend`: Increment 5.1
6. `M6 Frontend convenience`: Increment 5.2

This sequencing keeps all user-visible surfaces downstream of a tested and
restart-safe backend.

## Finalization decisions

The plan is finalized with the following binding decisions:

- Backend-first sequencing remains mandatory.
- No frontend feature may become the owner of behavioral logic.
- No increment may skip TDD, required verification artifacts, quality gates, or
  documentation updates.
- The first release-capable implementation target is `M4 Home Assistant usable
  baseline`.
- `M5` and `M6` remain downstream of the stable backend and Home Assistant
  runtime surface.

## Definition of done per increment

An increment is complete only when all of the following are true:

- linked requirements are implemented
- required `UT`, `IT`, `AT`, and `DR` artifacts for that increment exist or
  are updated
- the increment was developed test-first
- formatting, linting, tests, coverage, and package build are green
- user-facing and engineering documentation are updated
- traceability from requirements to verification remains intact
