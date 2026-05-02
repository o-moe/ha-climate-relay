# Verification Matrix

## Purpose

This matrix maps the current reviewed requirements baseline to planned
verification methods and verification artifacts.

It complements the Software Requirements Specification in
[requirements.md](./requirements.md) and is intended to support:

- test planning
- coverage tracking
- change impact analysis
- release readiness review

## Current implementation evidence

Epic 1 contributes the following executable evidence:

- `V-UT-001`: `tests/components/climate_relay_core/test_config_flow.py`
- `V-UT-002`: `tests/components/climate_relay_core/test_rules.py`,
  `tests/components/climate_relay_core/test_runtime.py`
- `V-UT-004`: central resolver and area target priority coverage in
  `tests/components/climate_relay_core/test_rules.py`
- `V-UT-005`: `tests/components/climate_relay_core/test_overrides.py`,
  `tests/components/climate_relay_core/test_runtime.py`
- `V-UT-006`: schedule validation, overnight/day-boundary behavior, and
  representative DST coverage in
  `tests/components/climate_relay_core/test_schedules.py`
- `V-UT-007`: fallback and degradation coverage in
  `tests/components/climate_relay_core/test_climate.py`,
  `tests/components/climate_relay_core/test_runtime.py`
- `V-UT-008`: fixed-time next-occurrence, next-timeblock boundary behavior, and
  time semantics in `tests/components/climate_relay_core/test_overrides.py`,
  `tests/components/climate_relay_core/test_runtime.py`
- `V-IT-001`: `tests/components/climate_relay_core/test_init.py`
- `V-IT-002`: `tests/components/climate_relay_core/test_select.py`,
  `tests/components/climate_relay_core/test_init.py`
- `V-IT-003`: Home Assistant service registration, runtime command handling,
  service-boundary error conversion, and override termination validation in
  `tests/components/climate_relay_core/test_init.py`,
  `tests/components/climate_relay_core/test_runtime.py`, and
  `scripts/ha_smoke_test.py`
- `V-IT-006`: `tests/components/climate_relay_core/test_climate.py`,
  `scripts/ha_smoke_test.py`
- `V-IT-006`, `V-IT-007`: actuation retry, blocking service-call success
  boundary, simulation-mode suppression, and timer cleanup coverage in
  `tests/components/climate_relay_core/test_climate.py`
- `V-DR-001`, `V-DR-003`: documented in-memory runtime-state limitation and
  future multi-profile configuration model in `docs/architecture.md` and
  `docs/epic-1.md`
- `V-AT-002`, `V-AT-003`, `V-AT-004`, `V-AT-005`, `V-AT-006`:
  `docs/gui-smoke-suites/epic-1.md`,
  `scripts/run_epic_acceptance.py --epic 1`; rerun on 2026-04-30 with
  both `--skip-gui` and full GUI runner against
  `http://haos-test.local:8123`

Epic 2 contributes the following executable evidence:

- `V-UT-003`: window action mapping and capability fallback coverage in
  `tests/components/climate_relay_core/test_rules.py`
- `V-UT-004`, `V-AT-001`: window-priority resolution, delayed activation, and
  close-time reevaluation coverage in
  `tests/components/climate_relay_core/test_rules.py` and
  `tests/components/climate_relay_core/test_climate.py`; full Epic 2
  options-flow GUI regression with deterministic baseline preparation and API
  open/close acceptance path prepared in
  `scripts/run_epic_acceptance.py --epic 2`; release acceptance passed on
  2026-05-02 against `v0.2.0-alpha.11` on
  `http://haos-test.local:8123`
- `V-DR-002`: Home Assistant options-flow UX structure documented in
  `docs/architecture.md` and `docs/engineering-standards.md`; conditionally
  required selector values use dedicated follow-up steps with localized
  integration-owned validation errors.

## Verification method legend

- `UT`: Unit test
- `IT`: Integration test
- `AT`: Acceptance test / specification by example
- `DR`: Design review

## Verification artifact catalog

### Unit tests

- `V-UT-001`: Config flow and singleton setup behavior
- `V-UT-002`: Presence resolution and global mode behavior
- `V-UT-003`: Window action mapping and capability fallback
- `V-UT-004`: Room target resolution priority and active control context
- `V-UT-005`: Manual override lifecycle and replacement semantics
- `V-UT-006`: Schedule model validation and next-change calculation
- `V-UT-007`: Fallback and degradation rule behavior
- `V-UT-008`: Restart recomputation, persisted-state interpretation, and time semantics

### Integration tests

- `V-IT-001`: Integration setup, config entry lifecycle, and singleton enforcement
- `V-IT-002`: Entity exposure for rooms, global mode, and sparse explanatory attributes
- `V-IT-003`: Integration action registration and runtime command handling
- `V-IT-004`: Restart recovery with persisted configuration and durable control state
- `V-IT-005`: Degraded operation and fallback exposure to Home Assistant state
- `V-IT-006`: Frontend-facing state shape, minimal entity surface, and attribute serialization
- `V-IT-007`: Simulation mode behavior, suppressed writes, and intended-action logging

### Acceptance tests

- `V-AT-001`: Specification-by-example scenarios for window close reevaluation
- `V-AT-002`: Specification-by-example scenarios for manual override behavior
- `V-AT-003`: Specification-by-example scenarios for schedule layouts and next changes
- `V-AT-004`: Room UI explanation scenarios for context, next change, override end, and degradation
- `V-AT-005`: Restart and degradation user-visible behavior scenarios
- `V-AT-006`: Simulation mode dry-run scenarios for safe behavior observation

All acceptance artifacts that cover Home Assistant GUI/UX changes must include
the complete affected UI flow, successful persistence, and introduced or
affected validation/error paths. For UI-configured runtime behavior, the
acceptance artifact must also verify the backend state or action produced by
the saved UI configuration.

### Design reviews

- `V-DR-001`: Layering, backend ownership, and testability review
- `V-DR-002`: Home Assistant idiomatic integration design review
- `V-DR-003`: Public interface minimization and traceability review
- `V-DR-004`: Repository policy and documentation conformance review

## Functional requirement matrix

### Configuration and room model

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-001` | Single integration instance | `UT`, `IT` | `V-UT-001`, `V-IT-001` |
| `FR-002` | Named integration setup | `UT`, `IT` | `V-UT-001`, `V-IT-001` |
| `FR-010` | Room composition | `DR`, `IT` | `V-DR-001`, `V-IT-002` |
| `FR-011` | Primary climate entity | `IT`, `DR` | `V-IT-002`, `V-DR-002` |
| `FR-012` | Optional humidity sensor | `IT`, `AT` | `V-IT-002`, `V-AT-004` |
| `FR-013` | Optional window contact | `IT`, `AT` | `V-IT-002`, `V-AT-001` |
| `FR-014` | Room-specific targets | `UT`, `AT` | `V-UT-004`, `V-AT-002` |
| `FR-015` | Room schedule | `UT`, `AT` | `V-UT-006`, `V-AT-003` |
| `FR-016` | Manual override policy | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-017` | Room target structure | `UT`, `DR` | `V-UT-004`, `V-DR-003` |
| `FR-018` | Away target variants | `UT`, `AT` | `V-UT-004`, `V-AT-003` |
| `FR-019` | Humidity as optional display context | `IT`, `DR` | `V-IT-006`, `V-DR-002` |
| `FR-020` | Optional sensor degradation | `UT`, `IT`, `AT` | `V-UT-007`, `V-IT-005`, `V-AT-005` |
| `FR-021` | Optional sensor availability indication | `IT`, `AT` | `V-IT-005`, `V-AT-004` |
| `FR-072` | Relative target reference | `UT`, `AT` | `V-UT-004`, `V-AT-003` |

### Global mode and presence

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-022` | Supported global modes | `UT`, `IT` | `V-UT-002`, `V-IT-002` |
| `FR-023` | Presence resolution in auto mode | `UT` | `V-UT-002` |
| `FR-024` | Manual home mode | `UT` | `V-UT-002` |
| `FR-025` | Manual away mode | `UT` | `V-UT-002` |
| `FR-026` | Non-expiring manual global override | `UT`, `IT` | `V-UT-002`, `V-IT-003` |
| `FR-027` | No intermediate effective presence state | `UT`, `AT` | `V-UT-002`, `V-AT-005` |
| `FR-028` | Configurable handling of unknown presence states | `UT`, `IT` | `V-UT-002`, `V-IT-003` |
| `FR-029` | Default unknown-presence mapping | `UT`, `IT` | `V-UT-002`, `V-IT-003` |
| `FR-101` | Global simulation mode option | `IT`, `DR` | `V-IT-003`, `V-DR-003` |
| `FR-102` | Simulation mode disabled by default | `IT`, `AT` | `V-IT-003`, `V-AT-006` |

### Window behavior

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-030` | Delayed window activation | `UT`, `AT` | `V-UT-004`, `V-AT-001` |
| `FR-031` | Supported window actions | `UT` | `V-UT-003` |
| `FR-032` | Off action mapping | `UT` | `V-UT-003` |
| `FR-033` | Frost protection mapping | `UT` | `V-UT-003` |
| `FR-034` | Minimum-temperature mapping | `UT` | `V-UT-003` |
| `FR-035` | Custom-temperature mapping | `UT` | `V-UT-003` |
| `FR-036` | Capability fallback for unsupported actions | `UT` | `V-UT-003` |
| `FR-037` | Re-evaluate room state after window close | `UT`, `AT` | `V-UT-004`, `V-AT-001` |

### Manual overrides and runtime commands

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-040` | Manual room override support | `IT`, `AT` | `V-IT-003`, `V-AT-002` |
| `FR-041` | Override termination options | `UT`, `IT` | `V-UT-005`, `V-IT-003` |
| `FR-042` | Duration-based termination | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-043` | Next-timeblock termination | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-044` | Persistent override | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-045` | Manual override input model | `IT`, `AT` | `V-IT-003`, `V-AT-002` |
| `FR-046` | Minute-precise override duration | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-047` | Fixed-clock-time termination | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-048` | Optional global reset time for manual overrides | `UT`, `IT` | `V-UT-005`, `V-IT-003` |
| `FR-049` | Global reset option disabled by default | `IT`, `DR` | `V-IT-001`, `V-DR-003` |
| `FR-066` | Next-occurrence semantics for fixed clock times | `UT`, `AT` | `V-UT-008`, `V-AT-002` |
| `FR-070` | Room-scoped override operations | `IT`, `DR` | `V-IT-003`, `V-DR-002` |
| `FR-071` | UI-orchestrated batch actions | `DR`, `AT` | `V-DR-002`, `V-AT-004` |
| `FR-073` | Minimal runtime command set | `IT`, `DR` | `V-IT-003`, `V-DR-003` |
| `FR-074` | Replacing an active room override | `UT`, `AT` | `V-UT-005`, `V-AT-002` |
| `FR-091` | Global mode action schema | `IT`, `DR` | `V-IT-003`, `V-DR-002` |
| `FR-092` | Room override action schema | `IT`, `DR` | `V-IT-003`, `V-DR-002` |
| `FR-093` | Override termination parameter structure | `UT`, `IT` | `V-UT-005`, `V-IT-003` |
| `FR-094` | Clear override action schema | `IT`, `DR` | `V-IT-003`, `V-DR-002` |

### Scheduling and fallback

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-050` | Supported schedule layouts | `UT`, `AT` | `V-UT-006`, `V-AT-003` |
| `FR-051` | Schedule evaluation ownership | `DR`, `UT` | `V-DR-001`, `V-UT-006` |
| `FR-052` | Schedule as room input | `UT`, `AT` | `V-UT-004`, `V-AT-003` |
| `FR-053` | Unlimited non-overlapping schedule blocks | `UT` | `V-UT-006` |
| `FR-054` | Schedule continuity | `UT`, `AT` | `V-UT-006`, `V-AT-003` |
| `FR-055` | Exceptional fallback state | `UT`, `AT` | `V-UT-007`, `V-AT-005` |
| `FR-056` | Fallback target priority | `UT`, `AT` | `V-UT-007`, `V-AT-005` |
| `FR-065` | Minute-level schedule boundaries | `UT`, `AT` | `V-UT-006`, `V-AT-003` |
| `FR-068` | Global fallback target for required device failure | `IT`, `AT` | `V-IT-005`, `V-AT-005` |
| `FR-069` | Required-component failure handling | `UT`, `IT`, `AT` | `V-UT-007`, `V-IT-005`, `V-AT-005` |

### Persistence and restart recovery

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-057` | Persistent configuration recovery | `IT` | `V-IT-004` |
| `FR-058` | Re-read current device state after restart | `IT`, `AT` | `V-IT-004`, `V-AT-005` |
| `FR-059` | Recompute effective room state after restart | `UT`, `IT`, `AT` | `V-UT-008`, `V-IT-004`, `V-AT-005` |
| `FR-063` | Persist durable control state | `IT` | `V-IT-004` |
| `FR-064` | Do not resume in-flight window delay timers after restart | `UT`, `IT`, `AT` | `V-UT-008`, `V-IT-004`, `V-AT-005` |

### Backend/frontend separation and Home Assistant integration

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `FR-060` | Frontend independence | `DR` | `V-DR-001` |
| `FR-061` | Backend-owned behavior | `DR` | `V-DR-001` |
| `FR-062` | Future frontend capabilities | `DR` | `V-DR-002` |
| `FR-067` | Optional humidity-based UI hints | `DR`, `AT` | `V-DR-002`, `V-AT-004` |
| `FR-075` | Home Assistant native state exposure | `IT`, `DR` | `V-IT-002`, `V-DR-002` |
| `FR-076` | Runtime writes via integration actions | `IT`, `DR` | `V-IT-003`, `V-DR-002` |
| `FR-077` | Custom frontend as card and optional strategy | `DR` | `V-DR-002` |
| `FR-099` | Integration distribution as HACS custom repository | `IT`, `DR` | `V-IT-001`, `V-DR-004` |
| `FR-100` | Frontend distribution as separate HACS dashboard repository | `DR` | `V-DR-002`, `V-DR-004` |
| `FR-103` | Simulation mode suppresses device writes | `IT`, `AT`, `DR` | `V-IT-007`, `V-AT-006`, `V-DR-002` |
| `FR-104` | Simulation mode logs intended actions | `IT`, `AT`, `DR` | `V-IT-007`, `V-AT-006`, `V-DR-003` |
| `FR-078` | Strategy shall not own business logic | `DR` | `V-DR-001`, `V-DR-002` |
| `FR-079` | Frontend reads Home Assistant state | `IT`, `DR` | `V-IT-006`, `V-DR-002` |
| `FR-080` | Minimal externally exposed entity set | `IT`, `DR` | `V-IT-006`, `V-DR-003` |
| `FR-081` | Room-level climate entity as primary room surface | `IT`, `DR` | `V-IT-002`, `V-DR-002` |
| `FR-082` | Global mode as select entity | `IT`, `DR` | `V-IT-002`, `V-DR-002` |
| `FR-083` | Avoid mirroring optional context sensors by default | `IT`, `DR` | `V-IT-006`, `V-DR-003` |
| `FR-084` | Use attributes sparingly for explanatory room context | `IT`, `DR` | `V-IT-006`, `V-DR-003` |
| `FR-085` | Minimal explanatory room attributes | `IT`, `DR` | `V-IT-006`, `V-DR-003` |
| `FR-086` | Active control context attribute | `IT`, `AT` | `V-IT-006`, `V-AT-004` |
| `FR-087` | Active control context values | `IT`, `AT` | `V-IT-006`, `V-AT-004` |
| `FR-088` | Next change timestamp attribute | `UT`, `IT`, `AT` | `V-UT-006`, `V-IT-006`, `V-AT-004` |
| `FR-089` | Override end timestamp attribute | `UT`, `IT`, `AT` | `V-UT-005`, `V-IT-006`, `V-AT-004` |
| `FR-090` | Degradation status attribute | `IT`, `AT` | `V-IT-005`, `V-AT-004` |
| `FR-095` | Time attribute serialization | `IT`, `AT`, `DR` | `V-IT-006`, `V-AT-004`, `V-DR-003` |
| `FR-096` | Local-time basis for serialized timestamps | `UT`, `IT`, `AT` | `V-UT-008`, `V-IT-006`, `V-AT-004` |
| `FR-097` | Degradation status vocabulary | `IT`, `DR` | `V-IT-006`, `V-DR-003` |
| `FR-098` | Degradation status values | `IT`, `AT` | `V-IT-005`, `V-AT-004` |

## Quality requirement matrix

| ID | Requirement | Methods | Planned verification artifacts |
| --- | --- | --- | --- |
| `QR-001` | English-only public content | `DR` | `V-DR-004` |
| `QR-002` | No manufacturer references | `DR` | `V-DR-004` |
| `QR-010` | Testable pure backend behavior | `DR`, `UT` | `V-DR-001`, `V-UT-004` |
| `QR-011` | Separation of concerns | `DR` | `V-DR-001` |
| `QR-012` | Minimal public interface complexity | `DR`, `IT` | `V-DR-003`, `V-IT-006` |
| `QR-020` | Bounded rule evaluation latency | `UT`, `DR` | `V-UT-004`, `V-DR-001` |
| `QR-021` | Efficient room update scaling | `UT`, `IT`, `DR` | `V-UT-004`, `V-IT-005`, `V-DR-001` |
| `QR-030` | Deterministic degraded behavior | `UT`, `IT`, `AT` | `V-UT-007`, `V-IT-005`, `V-AT-005` |
| `QR-031` | Restart-safe recomputation | `UT`, `IT`, `AT` | `V-UT-008`, `V-IT-004`, `V-AT-005` |
| `QR-040` | User-visible degraded-state indication | `IT`, `AT` | `V-IT-005`, `V-AT-004` |
| `QR-041` | Operator-readable logging | `IT`, `DR` | `V-IT-005`, `V-IT-007`, `V-DR-003` |
| `QR-050` | Consistent user mental model | `DR`, `AT` | `V-DR-003`, `V-AT-004` |
| `QR-051` | Predictable time semantics | `UT`, `AT` | `V-UT-006`, `V-AT-003` |
| `QR-060` | Home Assistant native integration style | `DR`, `IT` | `V-DR-002`, `V-IT-001`, `V-IT-002` |
| `QR-061` | Time zone and DST correctness | `UT`, `IT`, `AT` | `V-UT-008`, `V-IT-004`, `V-AT-003` |
| `QR-070` | Mandatory automated checks | `IT`, `DR` | `V-IT-001`, `V-DR-004` |
| `QR-071` | Locked workflow consistency | `DR` | `V-DR-004` |
| `QR-072` | Test coverage expectation | `DR` | `V-DR-003` |

## Matrix review notes

- Every current `FR` and `QR` identifier is mapped to at least one planned
  verification method.
- Many requirements intentionally share verification artifacts; this is
  expected because one good scenario often verifies several related
  requirements.
- `FR-062` remains intentionally broad and is therefore assigned to design
  review rather than to detailed executable tests in the current baseline.
- The matrix defines planned verification only. It does not claim that all
  listed artifacts already exist.
