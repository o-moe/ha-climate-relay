# Product UX Verification Addendum

## Purpose

This addendum defines verification expectations for the product UX requirements
introduced during the Epic 2 UX correction.

The addendum is intentionally separate from the main verification matrix until
the next full verification-matrix consolidation.

## Source documents

Verification in this file traces to:

- [product-ux-requirements-addendum.md](./product-ux-requirements-addendum.md)
- [product-ux-vision.md](./product-ux-vision.md)
- [frontend-interaction-model.md](./frontend-interaction-model.md)
- [frontend-backend-contract.md](./frontend-backend-contract.md)
- [options-flow-room-config-migration-plan.md](./options-flow-room-config-migration-plan.md)
- [config-subentries-evaluation.md](./config-subentries-evaluation.md)

## Verification method legend

- `UX-DR`: Product UX design review
- `UX-AT`: Frontend acceptance test or executable specification
- `UX-IT`: Backend/frontend integration test
- `UX-MIG`: Migration or compatibility test

## Verification artifacts

### UX-DR-001 Product UI boundary review

Confirms that the integration options flow remains an administrative surface and
that room-level product UX targets the custom frontend.

Evidence may include:

- review of `docs/product-ux-vision.md`
- review of `docs/frontend-interaction-model.md`
- review of `docs/options-flow-room-config-migration-plan.md`
- review of PRs that touch room-level options-flow behavior

### UX-DR-002 Frontend/backend boundary review

Confirms that the frontend renders and orchestrates backend-owned state and
actions without owning rule evaluation, schedule evaluation, fallback semantics,
degraded-state semantics, or persistence semantics.

Evidence may include:

- review of `docs/frontend-backend-contract.md`
- frontend implementation review
- backend state/action contract review
- TypeScript review proving no duplicated business-rule resolver exists

### UX-DR-003 Config subentries decision review

Confirms that config subentries are not adopted without satisfying the criteria
in `docs/config-subentries-evaluation.md`.

Evidence may include:

- explicit architecture decision in a future PR
- migration-risk analysis
- proof that subentries do not delay the custom frontend
- proof that subentries do not create a competing persistence model

### UX-AT-001 Room overview acceptance

Verifies that the frontend room overview renders all activated rooms and shows
core room state.

Expected coverage:

- all activated rooms appear once
- room name follows Home Assistant area naming
- current target is visible
- active control context is visible
- next scheduled change is visible when applicable
- active override end is visible when applicable
- window, humidity, and degradation indicators are visible when applicable

Increment 3.3 adds an executable frontend scaffold for the first part of this
acceptance target: `npm run test` in `frontend/` renders
`climate-relay-card` with a mocked Home Assistant `hass` object, verifies the
empty state, verifies one activated room tile, and verifies that room name,
target temperature, active control context, and degradation status are visible
without raw entity attribute inspection.

### UX-AT-002 Room detail reason-chain acceptance

Verifies that the frontend room detail explains why the current room target is
active.

Expected coverage:

- schedule-controlled room
- manual override room
- open-window override room
- global away influence
- required-component fallback
- optional sensor degradation

### UX-AT-003 Room activation and configuration acceptance

Verifies that users can activate and configure one eligible Home Assistant area
through the frontend.

Expected coverage:

- eligible room activation
- primary climate selection or confirmation
- missing-area validation
- duplicate primary-climate validation
- duplicate Home Assistant area validation
- optional humidity selection and clearing
- optional window contact selection and clearing
- room disable flow
- persistence after reload

Increment 3.3a adds executable partial coverage for this target. Python backend
tests cover candidate discovery, missing-area rejection, duplicate primary
climate rejection, duplicate HA-area rejection, one-room activation, use of
`room_management.activate_room(...)`, and config-entry options persistence.
Vitest/jsdom tests cover rendering the candidate section, unavailable reasons,
activation WebSocket orchestration, activation errors, and preservation of room
tile rendering.

Still missing: real Home Assistant / Playwright end-to-end acceptance,
optional sensor configuration, room update/disable, target configuration,
schedule editing, and persistence verification through a running HA instance.

### UX-AT-004 Schedule editor acceptance

Verifies that the first frontend slice includes room schedule editing for the
initially supported schedule model.

Expected coverage:

- edit start time
- edit end time
- save schedule through backend-owned operation
- reject identical start and end times
- reject invalid schedule shape
- room overview or room detail shows the resulting next scheduled change
- runtime behavior follows backend-owned schedule evaluation

Increment 3.3 documents this as a backend-facing gap because the frontend does
not yet have backend-owned schedule validation or schedule update operations.
Increment 3.3a keeps this gap open and does not add frontend-owned schedule
validation.

### UX-AT-005 Quick override acceptance

Verifies frontend creation and clearing of manual room overrides.

Expected coverage:

- set absolute target temperature
- duration termination
- fixed local time termination
- next scheduled change termination
- persistent override until cleared
- clear override / resume schedule
- room tile reflects active override without raw attribute inspection

Increment 3.3 covers only the initial executable scaffold: the card can call
the existing backend set/clear override services and the frontend test verifies
that orchestration. Full capability discovery and runtime effect coverage remain
open.
Increment 3.3a does not change this: `Override 1h` remains a temporary fixed
duration scaffold, and action capability projection remains open.

### UX-AT-006 Global mode acceptance

Verifies global mode control from the frontend.

Expected coverage:

- set `auto`
- set `home`
- set `away`
- room state reflects backend-owned effective context
- selected global mode is distinguishable from each room's active context

### UX-AT-007 Degraded-state indication acceptance

Verifies that degraded and fallback states are visible in the frontend.

Expected coverage:

- required primary climate unavailable
- optional humidity unavailable
- optional window contact unavailable
- degraded state shown in overview where relevant
- detailed explanation shown in room detail

### UX-IT-001 Frontend state contract integration

Verifies that the backend exposes enough frontend-facing state for the first
frontend slice.

Expected coverage:

- stable room/profile identifier
- Home Assistant area identifier
- display name
- primary climate entity identifier
- current temperature
- target temperature
- active control context
- next scheduled change
- override end time
- degradation status
- optional window state
- optional humidity value
- schedule summary
- frontend capabilities

### UX-IT-002 Frontend action contract integration

Verifies that frontend-callable operations exist for the first frontend slice.

Expected coverage:

- activate room
- update room configuration
- disable room
- set global mode
- set room override
- clear room override
- update room schedule
- validate room schedule where needed

### UX-MIG-001 Options-flow room migration compatibility

Verifies that existing options-flow `rooms` data can be consumed by or migrated
to the backend-owned room configuration model used by the frontend.

Expected coverage:

- existing room list survives upgrade
- existing primary climate anchors survive upgrade
- existing optional sensors survive upgrade
- existing window behavior survives upgrade
- existing targets survive upgrade
- existing schedule window survives upgrade
- runtime behavior remains equivalent after migration

### UX-MIG-002 Options-flow removal readiness

Verifies that options-flow room-management surfaces can be reduced or removed
without losing user-facing capability.

Expected coverage:

- frontend can perform all room-management tasks previously available through
  the temporary options-flow profile manager
- backend validation does not depend on options-flow schemas
- tests cover frontend room activation, update, disable, and schedule editing
- documentation no longer presents options-flow room management as target UX

## Traceability matrix

| Requirement | Methods | Artifacts |
| --- | --- | --- |
| `UX-FR-001` | `UX-AT`, `UX-DR` | `UX-AT-001`, `UX-AT-005`, `UX-DR-001` |
| `UX-FR-002` | `UX-DR` | `UX-DR-001` |
| `UX-FR-003` | `UX-DR`, `UX-MIG` | `UX-DR-001`, `UX-MIG-001`, `UX-MIG-002` |
| `UX-FR-004` | `UX-AT`, `UX-IT` | `UX-AT-001`, `UX-IT-001` |
| `UX-FR-005` | `UX-AT`, `UX-IT` | `UX-AT-002`, `UX-IT-001` |
| `UX-FR-006` | `UX-AT`, `UX-IT`, `UX-MIG` | `UX-AT-003`, `UX-IT-002`, `UX-MIG-001` |
| `UX-FR-007` | `UX-AT`, `UX-IT` | `UX-AT-004`, `UX-IT-002` |
| `UX-FR-008` | `UX-AT`, `UX-IT` | `UX-AT-005`, `UX-IT-002` |
| `UX-FR-009` | `UX-AT`, `UX-IT` | `UX-AT-006`, `UX-IT-002` |
| `UX-FR-010` | `UX-DR`, `UX-IT` | `UX-DR-002`, `UX-IT-001`, `UX-IT-002` |
| `UX-FR-011` | `UX-IT`, `UX-MIG` | `UX-IT-002`, `UX-MIG-001` |
| `UX-FR-012` | `UX-DR` | `UX-DR-003` |
| `UX-QR-001` | `UX-AT`, `UX-DR` | `UX-AT-001`, `UX-DR-001` |
| `UX-QR-002` | `UX-AT`, `UX-DR` | `UX-AT-001`, `UX-AT-005`, `UX-DR-001` |
| `UX-QR-003` | `UX-AT` | `UX-AT-001` to `UX-AT-007` |
| `UX-QR-004` | `UX-MIG`, `UX-DR` | `UX-MIG-001`, `UX-MIG-002`, `UX-DR-002` |

## Completion rule

The first frontend slice is not complete until all `UX-AT-001` to `UX-AT-007`,
`UX-IT-001`, `UX-IT-002`, and relevant migration evidence pass for the target
build.

Options-flow room-management reduction is not allowed until `UX-MIG-001` and
`UX-MIG-002` pass.
