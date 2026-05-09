# Product UX Requirements Addendum

## Purpose

This addendum extends the reviewed requirements baseline with product UX
requirements that were clarified during the Epic 2 UX correction.

The addendum is intentionally separate from the main requirements document until
the next full requirements consolidation. Requirements in this file are binding
for future frontend and room-configuration work.

## Source documents

These requirements derive from:

- [product-ux-vision.md](./product-ux-vision.md)
- [frontend-interaction-model.md](./frontend-interaction-model.md)
- [frontend-backend-contract.md](./frontend-backend-contract.md)
- [options-flow-room-config-migration-plan.md](./options-flow-room-config-migration-plan.md)
- [config-subentries-evaluation.md](./config-subentries-evaluation.md)

## Functional requirements

### UX-FR-001 Daily-use frontend as primary room UI

- Statement: The system shall provide a custom frontend as the primary user
  surface for daily room-level climate operation.
- Rationale: Daily room operation must not depend on Home Assistant Developer
  Tools, manual service calls, or raw entity attribute inspection.
- Fit criterion: A user can view room state, set a quick override, clear an
  override, and inspect the reason for the current target from the custom
  frontend.
- Status: Confirmed direction

### UX-FR-002 Options flow as administrative surface

- Statement: The Home Assistant integration options flow shall remain an
  administrative setup surface and shall not become the permanent primary UI for
  daily room-level climate control or room-level product configuration.
- Rationale: Room management and daily operation are product interactions, not
  integration-global administrative options.
- Fit criterion: New room-level product behavior is specified against the
  custom frontend room-management model unless explicitly documented as
  temporary bootstrap scaffolding.
- Status: Confirmed direction

### UX-FR-003 Temporary room bootstrap classification

- Statement: Existing options-flow regulation-profile configuration shall be
  treated as temporary bootstrap scaffolding until the custom frontend can
  manage equivalent room configuration.
- Rationale: The current options-flow profile manager is useful for backend
  validation, but it must not shape the final product UX.
- Fit criterion: Every room-level options-flow field is classified in
  [options-flow-room-config-migration-plan.md](./options-flow-room-config-migration-plan.md).
- Status: Confirmed direction

### UX-FR-004 Room overview

- Statement: The frontend shall provide a room overview showing all activated
  Climate Relay rooms.
- Rationale: The primary mental model is room-first, not entity-first.
- Fit criterion: Each activated room appears once and shows room name, current
  target, active control context, and relevant schedule, override, window,
  humidity, and degradation indicators when available.
- Status: Confirmed direction

### UX-FR-005 Room detail reason chain

- Statement: The frontend shall provide a room detail surface that explains why
  the current target is active.
- Rationale: Users need to understand whether schedule, manual override, window
  override, global away behavior, fallback, or degradation currently controls a
  room.
- Fit criterion: The room detail view renders a reason chain derived from
  backend-owned state without duplicating rule evaluation in the frontend.
- Status: Confirmed direction

### UX-FR-006 Room activation and configuration

- Statement: The frontend shall allow users to activate and configure eligible
  Home Assistant areas as Climate Relay rooms.
- Rationale: Room activation is part of product room management and shall not
  remain centered in the integration-global options flow.
- Fit criterion: A user can activate an eligible Home Assistant area, select or
  confirm the primary climate entity, configure optional sensors, and disable
  the room again through the frontend.
- Status: Confirmed direction

### UX-FR-007 Schedule editing in first frontend slice

- Statement: The first frontend slice shall include schedule editing for the
  initially supported schedule model.
- Rationale: A climate-control product without room schedule editing would not
  validate the intended daily-use experience.
- Fit criterion: A user can edit the supported room schedule through the custom
  frontend, persist it through backend-owned operations, and see the resulting
  next scheduled change in room state.
- Status: Confirmed direction

### UX-FR-008 Quick manual override

- Statement: The frontend shall provide quick manual override creation and
  clearing for one room at a time.
- Rationale: Manual room intervention is a primary daily-use task.
- Fit criterion: A user can set a target temperature with a supported
  termination option and later clear the override or resume schedule from the
  frontend.
- Status: Confirmed direction

### UX-FR-009 Global mode control in frontend

- Statement: The frontend shall expose global mode control for `auto`, `home`,
  and `away`.
- Rationale: Global mode is a daily-use product control, not only an entity or
  service surface.
- Fit criterion: A user can change global mode from the custom frontend and room
  views distinguish selected global mode from each room's active context.
- Status: Confirmed direction

### UX-FR-010 Frontend/backend responsibility boundary

- Statement: The frontend shall render and orchestrate backend-owned state and
  actions but shall not own rule evaluation, schedule evaluation, fallback
  semantics, degraded-state semantics, or persistence semantics.
- Rationale: Climate behavior must remain deterministic and independent of
  frontend execution.
- Fit criterion: Rule priority, schedule resolution, fallback decisions, and
  degradation vocabulary are tested in backend code and are not reimplemented in
  TypeScript.
- Status: Confirmed direction

### UX-FR-011 Backend-owned room configuration operations

- Statement: The backend shall expose operations sufficient for the frontend to
  activate, update, disable, and validate rooms and room schedules.
- Rationale: The frontend needs a stable contract that does not depend on Home
  Assistant options-flow screens.
- Fit criterion: Frontend room-management flows call backend-owned operations or
  APIs rather than mutating Home Assistant config entries directly.
- Status: Confirmed direction

### UX-FR-012 Config subentries evaluation before adoption

- Statement: Home Assistant config subentries shall not be adopted for room
  profiles until the documented evaluation criteria are satisfied.
- Rationale: Config subentries may improve administrative structure, but they do
  not solve the target daily-use GUI problem.
- Fit criterion: Any future subentry adoption references
  [config-subentries-evaluation.md](./config-subentries-evaluation.md) and
  satisfies its adoption criteria.
- Status: Confirmed direction

## Quality requirements

### UX-QR-001 Room-first mental model

- Statement: The product UI shall present climate control by rooms and Home
  Assistant areas rather than by raw entity lists.
- Fit criterion: Primary frontend navigation is room-based and uses Home
  Assistant area names as user-facing room labels.
- Status: Confirmed direction

### UX-QR-002 No permanent daily-use service workflow

- Statement: Normal daily climate operation shall not require Home Assistant
  Developer Tools or manual service calls.
- Fit criterion: All primary daily-use tasks in the first frontend slice are
  available through the custom frontend.
- Status: Confirmed direction

### UX-QR-003 Frontend acceptance coverage

- Statement: New frontend user flows shall have executable acceptance evidence
  covering success paths, validation paths, persistence, and runtime effect.
- Fit criterion: The first frontend slice has acceptance evidence for overview,
  room detail, activation/configuration, schedule editing, quick override,
  override clearing, global mode, and degraded-state indication.
- Status: Confirmed direction

### UX-QR-004 Migration-safe configuration model

- Statement: Temporary options-flow room configuration and future frontend room
  configuration shall write to one backend-owned configuration model.
- Fit criterion: There is no competing persistence format for the same room
  state during migration.
- Status: Confirmed direction
