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

1. manual area override
2. effective global mode and area schedule
3. fallback state

The domain resolver contains an explicit window-priority placeholder for Epic 2,
but Epic 1 does not enable window automation as user-facing behavior.

## Window override

When a configured window contact opens:

1. start the configured delay
2. if the contact is still open after the delay, activate window override
3. store the last valid room state

When the window closes:

1. clear window override
2. restore the last valid room state

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
