# Iteration X.Y GUI Smoke Suite

## Purpose

Describe the narrow Home Assistant GUI/UX acceptance checks for iteration
`X.Y`.

## Preconditions

1. Run `scripts/ha_prepare_test_instance.py`.
2. Run `scripts/ha_smoke_test.py` with the iteration-specific API assertions.
3. Open the HA test instance in the Codex in-app browser.
4. Log in with the dedicated HA test user if the session is not already
   authenticated.

## Scope

- Describe only the HA surfaces changed in this iteration.

## Cases

### Case 1: App shell reachable

- Open `http://haos-test.local:8123/`.
- Wait until HA finishes loading.
- Expect the HA overview or another expected landing page for the test flow.
- Fail if the session remains stuck on the login form, a loader, or an empty
  shell.

### Case 2: Primary iteration surface

- Describe the exact navigation path.
- List the expected visible labels, controls, and persisted values.
- List the expected save/cancel or open/close behavior.
- List explicit failure signals.

## Notes

- Keep selectors and labels aligned with the current HA UI language used in the
  test instance.
- Record only what the iteration actually changed.
