# Rules

## Goal

This document describes the rule model used to determine the effective area
state.

## Core concepts

### Global mode

Supported values:

- `auto`
- `home`
- `away`

In `auto`, the effective global state is derived from configured Home Assistant `person` entities.

### Area-level contexts

The backend distinguishes these area-level contexts:

- scheduled behavior
- manual override
- window override

### Effective target

The effective target is the resolved state that will be applied to the area's
climate entity. It may contain:

- an HVAC mode
- a preset mode
- a target temperature

## Schedule baseline

The first schedule slice supports one daily home window per configured
regulation profile. Outside that window the profile uses its configured away
target. The backend expands the window into a continuous all-days schedule with
no gaps, evaluates it in local time, and exposes the next scheduled target
change when effective presence is home.

The schedule domain model also validates the planned broader layouts:

- one schedule shared across all days
- one weekday schedule plus one weekend schedule
- one independent schedule for each weekday

## Rule priority

Priority order:

1. required-component fallback
2. window override
3. manual area override
4. effective global mode and area schedule
5. exceptional fallback state

Epic 2 enables the window-priority branch for configured window contacts. Window
override is evaluated before manual override so open-window protection remains
deterministic while the contact is active.

Required-component fallback is evaluated first because a missing, `unknown`, or
`unavailable` primary climate entity prevents normal control from being
applied safely. In that case the area resolves to the configured global
fallback temperature and exposes fallback context instead of pretending that a
higher-level rule can be acted on.

Exceptional fallback is reserved for invalid or incomplete runtime state where
normal rule evaluation cannot produce a valid temperature target even though
the required climate component is available. It reuses the last valid
temperature-based target known for the profile when one exists; otherwise it
uses 20 C.

## Window override

When a configured window contact opens:

1. start the configured delay
2. if the contact is still open after the delay, activate window override
3. store the last valid room state

When the window closes:

1. clear window override
2. reevaluate the full rule stack using the state that is valid at close time

Close-time reevaluation intentionally does not restore a stale pre-window
snapshot. If the schedule, global mode, or manual override changed while the
window was open, the area resolves to that current state after the window
closes.

## Manual area override

Manual area overrides are created through backend services or future UI actions.

Termination options:

- after a configured duration
- at the next schedule time block
- never, until cleared explicitly

## Presence handling

If global mode is `auto`:

- effective mode is `home` if any configured person is home
- effective mode is `away` otherwise

Manual global `home` and `away` overrides do not expire automatically.
