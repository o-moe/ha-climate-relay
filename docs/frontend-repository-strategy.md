# Frontend Repository Strategy

## Decision

Climate Relay keeps the backend Home Assistant integration in this repository.
The target daily-use custom card is a Home Assistant dashboard resource and
shall be distributed long term from a separate HACS dashboard/custom-card
repository.

## Rationale

HACS treats integrations and dashboard/plugin repositories as different
repository categories. Keeping the backend integration and the dashboard card
separable avoids coupling release and installation mechanics that Home
Assistant already models separately.

Early GUI iterations may keep a prototype under `frontend/` in this backend
repository when that shortens acceptance testing and product-owner validation.
That prototype is allowed only while it stays portable:

- it must not depend on backend repository internals beyond backend-owned Home
  Assistant state and actions
- it must not duplicate rule evaluation, schedule evaluation, override
  lifecycle, fallback semantics, degraded-state semantics, or persistence logic
- it must avoid architecture that blocks moving the card into a standalone HACS
  dashboard/custom-card repository later

The current `frontend/` code is therefore an Increment 3.3 validation scaffold,
not the final distribution boundary.
