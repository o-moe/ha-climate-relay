# Rules

## Goal

This document describes the rule model used to determine the effective room state.

## Core concepts

### Global mode

Supported values:

- `auto`
- `home`
- `away`

In `auto`, the effective global state is derived from configured Home Assistant `person` entities.

### Room-level contexts

The backend distinguishes these room-level contexts:

- scheduled behavior
- manual override
- window override

### Effective target

The effective target is the resolved state that will be applied to the room's climate entity. It may contain:

- an HVAC mode
- a preset mode
- a target temperature

## Rule priority

Priority order:

1. window override
2. manual room override
3. effective global mode
4. room schedule
5. fallback state

## Window override

When a configured window contact opens:

1. start the configured delay
2. if the contact is still open after the delay, activate window override
3. store the last valid room state

When the window closes:

1. clear window override
2. restore the last valid room state

## Manual room override

Manual room overrides are created through backend services or future UI actions.

Termination options:

- after a configured duration
- at the next schedule time block
- never, until cleared explicitly

## Presence handling

If global mode is `auto`:

- effective mode is `home` if any configured person is home
- effective mode is `away` otherwise

Manual global `home` and `away` overrides do not expire automatically.
