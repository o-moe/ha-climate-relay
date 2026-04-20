# ClimateRelayCore

ClimateRelayCore is a Home Assistant custom integration for room-centric
climate control.

## Available Features

- one installable integration instance per Home Assistant installation
- one global mode control with the options `auto`, `home`, and `away`
- automatic presence resolution from configured `person` entities
- configurable handling for `unknown` and `unavailable` person states
- a configurable fallback target temperature for required-component failure
- optional simulation mode for dry-run observation without device actuation
- optional verbose diagnostic logging

## Installation

The recommended installation path is through HACS as a custom repository.

### Install with HACS

1. Open HACS in Home Assistant.
2. Open the menu in the top right corner.
3. Select `Custom repositories`.
4. Add `https://github.com/o-moe/ha-climate-relay` as repository URL.
5. Select the repository type `Integration`.
6. Download `ClimateRelayCore` through HACS.
7. Restart Home Assistant.
8. Open `Settings > Devices & Services`.
9. Select `Add Integration`.
10. Search for `ClimateRelayCore`.
11. Create the integration entry.

If both stable and early-access builds are published, ordinary users should
prefer the latest stable GitHub release. Alpha or dev builds are intended only
for directed testing.

### Manual Installation

1. Copy `custom_components/climate_relay_core` into your Home Assistant
   configuration directory under `custom_components/`.
2. Restart Home Assistant.
3. Open `Settings > Devices & Services`.
4. Select `Add Integration`.
5. Search for `ClimateRelayCore`.
6. Create the integration entry.

## First Setup

The initial setup flow currently asks only for the display name of the
integration. After setup, open the integration options to configure:

- tracked `person` entities for automatic presence resolution
- handling of `unknown` and `unavailable` person states
- fallback temperature
- optional daily manual-override reset time
- simulation mode
- verbose logging

## How To Use It

After setup, Home Assistant exposes one integration-owned `select` entity named
`Global Mode`.

- `auto`: resolves presence from the configured `person` entities
- `home`: forces effective presence to `home`
- `away`: forces effective presence to `away`

You can change the mode either through the `Global Mode` select entity or via
the service `climate_relay_core.set_global_mode`.

## Diagnostics

The integration writes logs for global mode transitions and configuration
updates. If you enable verbose logging in the options flow, it also logs the
resolved effective presence context.

If simulation mode is enabled, the integration still evaluates its control
logic and records the resulting decisions, but it is intended to suppress
actual device writes once room-level actuation paths are in use.

## Current Limitations

- room entities are not exposed yet
- schedules are not available yet
- room-level manual overrides are not available yet
- window automation is not available yet
- a dedicated dashboard UI is not available yet

## Additional Documentation

Developer and project-internal documentation is maintained in [docs/](./docs/)
and [CONTRIBUTING.md](./CONTRIBUTING.md).
