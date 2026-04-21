# Climate Relay

Climate Relay is a Home Assistant custom integration for room-centric
climate control.

[![Open your Home Assistant instance and show the Climate Relay repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=ha-climate-relay&owner=o-moe)

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

1. Open the badge above from the Home Assistant instance where you want to install the integration.
2. Confirm the HACS repository link for `ClimateRelayCore`.
3. Download `Climate Relay` through HACS.
4. Restart Home Assistant.
5. Open `Settings > Devices & Services`.
6. Select `Add Integration`.
7. Search for `Climate Relay`.
8. Create the integration entry.

If you prefer the manual HACS path:

1. Open HACS in Home Assistant.
2. Open the menu in the top right corner.
3. Select `Custom repositories`.
4. Add `https://github.com/o-moe/ha-climate-relay` as repository URL.
5. Select the repository type `Integration`.
6. Download `Climate Relay` through HACS.
7. Restart Home Assistant.
8. Open `Settings > Devices & Services`.
9. Select `Add Integration`.
10. Search for `Climate Relay`.
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
5. Search for `Climate Relay`.
6. Create the integration entry.

## First Setup

The initial setup flow currently asks only for the display name of the
integration. After setup, open the integration card menu in
`Settings > Devices & Services` and choose `Configure` to adjust:

- tracked `person` entities for automatic presence resolution
- handling of `unknown` and `unavailable` person states
- fallback temperature
- optional daily manual-override reset time
- simulation mode
- verbose logging

The options dialog includes short inline explanations. At a high level:

- tracked presence entities drive `Automatic` presence resolution
- unknown-state handling defines how missing person state is interpreted
- fallback temperature is reserved for later room/failure handling
- daily override reset is preparation for later room-level manual overrides
- simulation mode keeps future actuator writes suppressed while still logging intended behavior
- verbose logging expands diagnostic output for troubleshooting

After a successful installation and setup, Home Assistant currently exposes:

- one `select` entity named `Presence Control`
- one service named `climate_relay_core.set_global_mode`

## How To Use It

After setup, use the `Presence Control` select entity to control the current
integration-wide behavior.

- `Automatic`: resolves presence from the configured `person` entities
- `Home`: forces effective presence to `home`
- `Away`: forces effective presence to `away`

You can change the mode either through the `Presence Control` select entity or via
the service `climate_relay_core.set_global_mode`.

## Diagnostics

The integration writes logs for global mode transitions and configuration
updates. If you enable verbose logging in the options flow, it also logs the
resolved effective presence context.

If simulation mode is enabled, the integration still evaluates its control
logic and logs the resulting decisions. In the current feature scope, there
are no active thermostat or other device writes yet, so the option is
primarily a preparation and observation mode for later room-level actuation.

## Current Limitations

- room entities are not exposed yet
- schedules are not available yet
- room-level manual overrides are not available yet
- window automation is not available yet
- a dedicated dashboard UI is not available yet

## Additional Documentation

Developer and project-internal documentation is maintained in [docs/](./docs/)
and [CONTRIBUTING.md](./CONTRIBUTING.md).
