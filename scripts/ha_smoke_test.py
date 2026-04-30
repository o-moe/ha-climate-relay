#!/usr/bin/env python3
"""Run a narrow authenticated smoke test against a Home Assistant instance."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://haos-test.local:8123"
TOKEN_ENV_VAR = "HOME_ASSISTANT_TOKEN"
SERVICE_DOMAIN = "climate_relay_core"
SERVICE_CLEAR_AREA_OVERRIDE = "clear_area_override"
SERVICE_SET_AREA_OVERRIDE = "set_area_override"
SERVICE_SET_GLOBAL_MODE = "set_global_mode"
SERVICE_NAMES = (
    SERVICE_SET_GLOBAL_MODE,
    SERVICE_SET_AREA_OVERRIDE,
    SERVICE_CLEAR_AREA_OVERRIDE,
)
VALID_MODES = ("auto", "home", "away")
VALID_EFFECTIVE_PRESENCE = ("home", "away")
VALID_SIMULATION_MODE = ("on", "off")


class SmokeTestError(RuntimeError):
    """Raised when the smoke test fails."""


@dataclass(frozen=True)
class EntityState:
    """Represent the subset of HA state fields used by the smoke test."""

    entity_id: str
    state: str
    attributes: dict[str, Any]

    @classmethod
    def from_api_payload(cls, payload: dict[str, Any]) -> EntityState:
        return cls(
            entity_id=str(payload["entity_id"]),
            state=str(payload["state"]),
            attributes=dict(payload.get("attributes", {})),
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the Climate Relay integration is reachable in Home Assistant, "
            "exposes its expected service and entity surface, and responds to a "
            "service-driven global-mode transition."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Home Assistant base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--select-entity-id",
        default=None,
        help="Explicit Presence Control entity_id. If omitted, it is discovered from state.",
    )
    parser.add_argument(
        "--expect-room-count",
        type=int,
        default=0,
        help="Minimum number of Climate Relay room climate entities expected.",
    )
    parser.add_argument(
        "--expect-room-next-change",
        action="store_true",
        help="Require at least one room entity to expose next_change_at.",
    )
    parser.add_argument(
        "--expect-area-override-services",
        action="store_true",
        help="Require the manual override services introduced in iteration 1.4.",
    )
    parser.add_argument(
        "--set-room-override-area-id",
        default=None,
        help="Set a manual override for this Climate Relay area/profile during the smoke test.",
    )
    parser.add_argument(
        "--set-room-override-temperature",
        type=float,
        default=22.5,
        help="Manual override target temperature used with --set-room-override-area-id.",
    )
    parser.add_argument(
        "--set-room-override-duration-minutes",
        type=int,
        default=45,
        help="Manual override duration used with --set-room-override-area-id.",
    )
    parser.add_argument(
        "--expect-room-override-ends",
        action="store_true",
        help="Require a room entity to expose override_ends_at after setting an override.",
    )
    parser.add_argument(
        "--expect-select-friendly-name",
        default=None,
        help="Expected friendly_name of the Presence Control select entity.",
    )
    parser.add_argument(
        "--set-initial-mode",
        choices=VALID_MODES,
        default=None,
        help="Set Presence Control to this mode before checking state.",
    )
    parser.add_argument(
        "--expect-effective-presence",
        choices=VALID_EFFECTIVE_PRESENCE,
        default=None,
        help="Expected effective_presence attribute on the Presence Control entity.",
    )
    parser.add_argument(
        "--expect-unknown-state-handling",
        default=None,
        help="Expected unknown_state_handling attribute on the Presence Control entity.",
    )
    parser.add_argument(
        "--expect-simulation-mode",
        choices=VALID_SIMULATION_MODE,
        default=None,
        help="Expected simulation_mode attribute on the Presence Control entity.",
    )
    parser.add_argument(
        "--expect-fallback-temperature",
        type=float,
        default=None,
        help="Expected fallback_temperature attribute on the Presence Control entity.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Maximum time to wait for the select entity state to reflect a service call.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=0.5,
        help="Polling interval while waiting for state transitions.",
    )
    return parser


def _request_json(
    *,
    base_url: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeTestError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SmokeTestError(f"{method} {path} failed: {exc.reason}") from exc


def _get_states(*, base_url: str, token: str) -> list[EntityState]:
    payload = _request_json(base_url=base_url, token=token, path="/api/states")
    if not isinstance(payload, list):
        raise SmokeTestError("Expected /api/states to return a list.")
    return [EntityState.from_api_payload(item) for item in payload]


def _get_services(*, base_url: str, token: str) -> list[dict[str, Any]]:
    payload = _request_json(base_url=base_url, token=token, path="/api/services")
    if not isinstance(payload, list):
        raise SmokeTestError("Expected /api/services to return a list.")
    return payload


def _find_presence_control_entity(
    states: list[EntityState],
    explicit_entity_id: str | None,
) -> EntityState:
    if explicit_entity_id is not None:
        for state in states:
            if state.entity_id == explicit_entity_id:
                return state
        raise SmokeTestError(f"Configured select entity {explicit_entity_id!r} was not found.")

    candidates = [
        state
        for state in states
        if state.entity_id.startswith("select.")
        and tuple(state.attributes.get("options", ())) == VALID_MODES
        and "effective_presence" in state.attributes
    ]
    if not candidates:
        raise SmokeTestError("Could not discover the Climate Relay Presence Control entity.")
    if len(candidates) > 1:
        entity_ids = ", ".join(state.entity_id for state in candidates)
        raise SmokeTestError(
            "Presence Control discovery was ambiguous. "
            f"Use --select-entity-id. Candidates: {entity_ids}"
        )
    return candidates[0]


def _find_room_entities(states: list[EntityState]) -> list[EntityState]:
    return [
        state
        for state in states
        if state.entity_id.startswith("climate.")
        and "primary_climate_entity_id" in state.attributes
        and "active_control_context" in state.attributes
    ]


def _assert_equal(name: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise SmokeTestError(f"Expected {name} to be {expected!r}, got {actual!r}.")


def _assert_select_surface(select_state: EntityState, args: argparse.Namespace) -> list[str]:
    attrs = select_state.attributes

    _assert_equal("Presence Control options", tuple(attrs.get("options", ())), VALID_MODES)

    effective_presence = attrs.get("effective_presence")
    if effective_presence not in VALID_EFFECTIVE_PRESENCE:
        raise SmokeTestError(
            "Presence Control effective_presence must be "
            f"one of {VALID_EFFECTIVE_PRESENCE}, got {effective_presence!r}."
        )

    simulation_mode = attrs.get("simulation_mode")
    if simulation_mode not in VALID_SIMULATION_MODE:
        raise SmokeTestError(
            "Presence Control simulation_mode must be "
            f"one of {VALID_SIMULATION_MODE}, got {simulation_mode!r}."
        )

    if args.expect_select_friendly_name is not None:
        _assert_equal(
            "Presence Control friendly_name",
            attrs.get("friendly_name"),
            args.expect_select_friendly_name,
        )
    if args.expect_effective_presence is not None:
        _assert_equal(
            "Presence Control effective_presence",
            effective_presence,
            args.expect_effective_presence,
        )
    if args.expect_unknown_state_handling is not None:
        _assert_equal(
            "Presence Control unknown_state_handling",
            attrs.get("unknown_state_handling"),
            args.expect_unknown_state_handling,
        )
    if args.expect_simulation_mode is not None:
        _assert_equal(
            "Presence Control simulation_mode",
            simulation_mode,
            args.expect_simulation_mode,
        )
    if args.expect_fallback_temperature is not None:
        try:
            fallback_temperature = float(attrs.get("fallback_temperature"))
        except (TypeError, ValueError) as exc:
            raise SmokeTestError(
                "Presence Control fallback_temperature is missing or not numeric."
            ) from exc
        _assert_equal(
            "Presence Control fallback_temperature",
            fallback_temperature,
            args.expect_fallback_temperature,
        )

    return [
        f"Presence Control mode: {select_state.state}",
        f"Presence Control effective presence: {effective_presence}",
        f"Presence Control simulation mode: {simulation_mode}",
    ]


def _assert_room_surface(
    room_entities: list[EntityState],
    *,
    expect_next_change: bool,
) -> list[str]:
    found_next_change = False
    for room in room_entities:
        attrs = room.attributes
        primary_climate_entity_id = attrs.get("primary_climate_entity_id")
        active_control_context = attrs.get("active_control_context")
        if not isinstance(primary_climate_entity_id, str) or "." not in primary_climate_entity_id:
            raise SmokeTestError(
                f"Room entity {room.entity_id} has invalid primary_climate_entity_id "
                f"{primary_climate_entity_id!r}."
            )
        if active_control_context not in {"manual_override", "schedule", "fallback"}:
            raise SmokeTestError(
                f"Room entity {room.entity_id} has unexpected active_control_context "
                f"{active_control_context!r}."
            )
        next_change_at = attrs.get("next_change_at")
        if next_change_at is not None:
            if not isinstance(next_change_at, str) or "T" not in next_change_at:
                raise SmokeTestError(
                    f"Room entity {room.entity_id} has invalid next_change_at {next_change_at!r}."
                )
            found_next_change = True

    if expect_next_change and not found_next_change:
        raise SmokeTestError("Expected at least one room entity to expose next_change_at.")

    return [f"Room surface verified: {entity.entity_id}" for entity in room_entities]


def _assert_service_registered(
    services: list[dict[str, Any]],
    *,
    expect_area_override_services: bool,
) -> tuple[str, ...]:
    expected_services = (
        SERVICE_NAMES if expect_area_override_services else (SERVICE_SET_GLOBAL_MODE,)
    )
    for domain_entry in services:
        if domain_entry.get("domain") != SERVICE_DOMAIN:
            continue
        service_names = domain_entry.get("services", {})
        if all(service_name in service_names for service_name in expected_services):
            return expected_services
    raise SmokeTestError(
        f"Expected services under {SERVICE_DOMAIN}: {', '.join(expected_services)}."
    )


def _call_set_global_mode(*, base_url: str, token: str, mode: str) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/services/{SERVICE_DOMAIN}/{SERVICE_SET_GLOBAL_MODE}",
        method="POST",
        payload={"mode": mode},
    )


def _call_set_area_override(
    *,
    base_url: str,
    token: str,
    area_id: str,
    target_temperature: float,
    duration_minutes: int,
) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/services/{SERVICE_DOMAIN}/{SERVICE_SET_AREA_OVERRIDE}",
        method="POST",
        payload={
            "area_id": area_id,
            "target_temperature": target_temperature,
            "termination_type": "duration",
            "duration_minutes": duration_minutes,
        },
    )


def _call_clear_area_override(*, base_url: str, token: str, area_id: str) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/services/{SERVICE_DOMAIN}/{SERVICE_CLEAR_AREA_OVERRIDE}",
        method="POST",
        payload={"area_id": area_id},
    )


def _assert_manual_override_surface(
    room_entities: list[EntityState],
    *,
    expect_override_ends: bool,
) -> list[str]:
    override_rooms = [
        room
        for room in room_entities
        if room.attributes.get("active_control_context") == "manual_override"
    ]
    if not override_rooms:
        raise SmokeTestError("Expected one room entity to expose manual_override context.")
    if expect_override_ends:
        override_ends_at = override_rooms[0].attributes.get("override_ends_at")
        if not isinstance(override_ends_at, str) or "T" not in override_ends_at:
            raise SmokeTestError(
                "Expected manual override room entity to expose valid override_ends_at."
            )
    return [f"Manual override verified: {override_rooms[0].entity_id}"]


def _wait_for_select_state(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    expected_state: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> EntityState:
    deadline = time.monotonic() + timeout_seconds
    while True:
        payload = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/states/{entity_id}",
        )
        state = EntityState.from_api_payload(payload)
        if state.state == expected_state:
            return state
        if time.monotonic() >= deadline:
            raise SmokeTestError(
                f"Timed out waiting for {entity_id} to become {expected_state!r}; "
                f"last observed state was {state.state!r}."
            )
        time.sleep(poll_interval_seconds)


def _choose_probe_mode(original_mode: str) -> str:
    if original_mode not in VALID_MODES:
        raise SmokeTestError(
            f"Presence Control reported unexpected mode {original_mode!r}; "
            f"expected one of {VALID_MODES}."
        )
    return "home" if original_mode != "home" else "away"


def _run_smoke_test(args: argparse.Namespace) -> list[str]:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SmokeTestError(
            f"Missing {TOKEN_ENV_VAR}. Export the long-lived Home Assistant token first."
        )

    api_status = _request_json(base_url=args.base_url, token=token, path="/api/")
    if api_status.get("message") != "API running.":
        raise SmokeTestError(f"Unexpected /api/ response: {api_status!r}")

    services = _get_services(base_url=args.base_url, token=token)
    expected_services = _assert_service_registered(
        services,
        expect_area_override_services=args.expect_area_override_services,
    )
    if args.set_initial_mode is not None:
        _call_set_global_mode(base_url=args.base_url, token=token, mode=args.set_initial_mode)

    states = _get_states(base_url=args.base_url, token=token)
    select_state = _find_presence_control_entity(states, args.select_entity_id)
    select_lines = _assert_select_surface(select_state, args)
    room_entities = _find_room_entities(states)
    if len(room_entities) < args.expect_room_count:
        raise SmokeTestError(
            f"Expected at least {args.expect_room_count} Climate Relay room entities, "
            f"found {len(room_entities)}."
        )
    room_lines = _assert_room_surface(
        room_entities,
        expect_next_change=args.expect_room_next_change,
    )
    override_lines: list[str] = []
    if args.set_room_override_area_id is not None:
        _call_set_area_override(
            base_url=args.base_url,
            token=token,
            area_id=args.set_room_override_area_id,
            target_temperature=args.set_room_override_temperature,
            duration_minutes=args.set_room_override_duration_minutes,
        )
        time.sleep(2.0)
        room_entities = _find_room_entities(_get_states(base_url=args.base_url, token=token))
        override_lines = _assert_manual_override_surface(
            room_entities,
            expect_override_ends=args.expect_room_override_ends,
        )
        _call_clear_area_override(
            base_url=args.base_url,
            token=token,
            area_id=args.set_room_override_area_id,
        )

    original_mode = select_state.state
    probe_mode = _choose_probe_mode(original_mode)
    restored = False

    try:
        _call_set_global_mode(base_url=args.base_url, token=token, mode=probe_mode)
        changed_state = _wait_for_select_state(
            base_url=args.base_url,
            token=token,
            entity_id=select_state.entity_id,
            expected_state=probe_mode,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        _call_set_global_mode(base_url=args.base_url, token=token, mode=original_mode)
        restored_state = _wait_for_select_state(
            base_url=args.base_url,
            token=token,
            entity_id=select_state.entity_id,
            expected_state=original_mode,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        restored = True
    finally:
        if not restored:
            with suppress(SmokeTestError):
                _call_set_global_mode(base_url=args.base_url, token=token, mode=original_mode)

    lines = [
        f"API reachable: {args.base_url}",
        f"Services present: {SERVICE_DOMAIN}.{', '.join(expected_services)}",
        f"Presence Control entity: {select_state.entity_id}",
        *select_lines,
        f"Room climate entities: {len(room_entities)}",
        *room_lines,
        *override_lines,
        (
            "Mode transition verified: "
            f"{original_mode} -> {changed_state.state} -> {restored_state.state}"
        ),
    ]
    return lines


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        lines = _run_smoke_test(args)
    except SmokeTestError as exc:
        print(f"HA smoke test failed: {exc}", file=sys.stderr)
        return 1

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
