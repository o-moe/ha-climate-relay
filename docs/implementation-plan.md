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
- GUI/UX acceptance for each increment must be complete for the user flows it
  touches. It must automate successful flows and validation/error paths in the
  real Home Assistant UI, including selector behavior, step transitions,
  persistence, and any affected cancel or close behavior. A happy-path-only GUI
  smoke test is not sufficient for an increment that changes UI/UX behavior.
- When UI configuration controls backend runtime behavior, the increment
  acceptance runner must configure the feature through the UI and then verify
  the resulting backend state or action through Home Assistant state, services,
  or another executable runtime observation.

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

1. `M1 Foundation complete`: Epic 1
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
