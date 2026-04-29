#!/usr/bin/env python3
"""Ensure a dedicated no-area Virtual Climate fixture exists in Home Assistant."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import websockets

DEFAULT_BASE_URL = "http://haos-test.local:8123"
TOKEN_ENV_VAR = "HOME_ASSISTANT_TOKEN"
DEFAULT_FIXTURE_TITLE = "No Area Fixture"
DEFAULT_CLIMATE_NAME = "No Area Fixture"
DEFAULT_CURRENT_TEMPERATURE = 20.0
DEFAULT_TARGET_TEMPERATURE = 21.0


class FixtureError(RuntimeError):
    """Raised when the dedicated no-area fixture cannot be prepared."""


@dataclass(frozen=True)
class ConfigEntrySummary:
    """Represent one HA config entry summary."""

    entry_id: str
    domain: str
    title: str
    state: str


@dataclass(frozen=True)
class DeviceEntry:
    """Represent the subset of device-registry fields that we need."""

    id: str
    primary_config_entry: str | None
    name: str | None
    name_by_user: str | None
    area_id: str | None


@dataclass(frozen=True)
class EntityDisplayEntry:
    """Represent the subset of entity-registry display fields that we need."""

    entity_id: str
    platform: str
    device_id: str | None
    name: str | None
    area_id: str | None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create or verify a dedicated Virtual Climate fixture that intentionally "
            "has no Home Assistant area assignment."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Home Assistant base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--fixture-title",
        default=DEFAULT_FIXTURE_TITLE,
        help=f"Virtual Climate config-entry title. Default: {DEFAULT_FIXTURE_TITLE!r}",
    )
    parser.add_argument(
        "--climate-name",
        default=DEFAULT_CLIMATE_NAME,
        help=f"Virtual Climate entity name. Default: {DEFAULT_CLIMATE_NAME!r}",
    )
    parser.add_argument(
        "--initial-current-temperature",
        type=float,
        default=DEFAULT_CURRENT_TEMPERATURE,
        help="Initial current temperature for the dedicated fixture.",
    )
    parser.add_argument(
        "--initial-target-temperature",
        type=float,
        default=DEFAULT_TARGET_TEMPERATURE,
        help="Initial target temperature for the dedicated fixture.",
    )
    parser.add_argument(
        "--wait-timeout-seconds",
        type=float,
        default=20.0,
        help="Maximum wait time for the dedicated fixture climate entity to appear.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=1.0,
        help="Polling interval while waiting for the dedicated fixture entity.",
    )
    return parser


def _build_ws_url(base_url: str) -> str:
    parsed = urlparse(base_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    if not parsed.netloc:
        raise FixtureError(f"Cannot derive websocket URL from {base_url!r}.")
    return f"{scheme}://{parsed.netloc}/api/websocket"


def _request_json(
    *,
    base_url: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise FixtureError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise FixtureError(f"{method} {path} failed: {exc.reason}") from exc


def _get_config_entries(*, base_url: str, token: str) -> list[ConfigEntrySummary]:
    payload = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/entry",
    )
    if not isinstance(payload, list):
        raise FixtureError("Expected config entries endpoint to return a list.")
    return [
        ConfigEntrySummary(
            entry_id=str(item["entry_id"]),
            domain=str(item["domain"]),
            title=str(item["title"]),
            state=str(item["state"]),
        )
        for item in payload
    ]


def _find_existing_fixture_entry(
    entries: list[ConfigEntrySummary],
    fixture_title: str,
) -> ConfigEntrySummary | None:
    matches = [
        entry
        for entry in entries
        if entry.domain == "virtual_climate" and entry.title == fixture_title
    ]
    if len(matches) > 1:
        raise FixtureError(
            f"Found multiple Virtual Climate entries named {fixture_title!r}: "
            + ", ".join(entry.entry_id for entry in matches)
        )
    return matches[0] if matches else None


def _create_fixture_entry(
    *,
    base_url: str,
    token: str,
    fixture_title: str,
    climate_name: str,
    initial_current_temperature: float,
    initial_target_temperature: float,
) -> ConfigEntrySummary:
    flow = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/flow",
        method="POST",
        payload={"handler": "virtual_climate"},
    )
    if not isinstance(flow, dict) or "flow_id" not in flow:
        raise FixtureError("Failed to initialize the Virtual Climate config flow.")

    result = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/flow/{flow['flow_id']}",
        method="POST",
        payload={
            "name": fixture_title,
            "climate_names": climate_name,
            "initial_current_temperature": initial_current_temperature,
            "initial_target_temperature": initial_target_temperature,
        },
    )
    if not isinstance(result, dict) or result.get("type") != "create_entry":
        raise FixtureError(
            "Virtual Climate config flow did not create the dedicated no-area fixture."
        )
    created = result.get("result")
    if not isinstance(created, dict):
        raise FixtureError("Virtual Climate config flow did not return the created entry.")
    return ConfigEntrySummary(
        entry_id=str(created["entry_id"]),
        domain=str(created["domain"]),
        title=str(created["title"]),
        state=str(created["state"]),
    )


async def _ws_command(
    websocket: Any,
    command_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    await websocket.send(json.dumps({"id": command_id, **payload}))
    while True:
        message = json.loads(await websocket.recv())
        if message.get("id") == command_id:
            return message


async def _get_registry_data(
    *,
    base_url: str,
    token: str,
) -> tuple[list[DeviceEntry], list[EntityDisplayEntry]]:
    async with websockets.connect(_build_ws_url(base_url)) as websocket:
        await websocket.recv()
        await websocket.send(json.dumps({"type": "auth", "access_token": token}))
        auth_message = json.loads(await websocket.recv())
        if auth_message.get("type") != "auth_ok":
            raise FixtureError(f"HA websocket auth failed: {auth_message!r}")

        device_result = await _ws_command(
            websocket,
            1,
            {"type": "config/device_registry/list"},
        )
        entity_result = await _ws_command(
            websocket,
            2,
            {"type": "config/entity_registry/list_for_display"},
        )

    if not device_result.get("success"):
        raise FixtureError(f"Device registry query failed: {device_result!r}")
    if not entity_result.get("success"):
        raise FixtureError(f"Entity registry query failed: {entity_result!r}")

    devices = [
        DeviceEntry(
            id=str(item["id"]),
            primary_config_entry=(
                str(item["primary_config_entry"])
                if item.get("primary_config_entry") is not None
                else None
            ),
            name=item.get("name") if isinstance(item.get("name"), str) else None,
            name_by_user=(
                item.get("name_by_user") if isinstance(item.get("name_by_user"), str) else None
            ),
            area_id=item.get("area_id") if isinstance(item.get("area_id"), str) else None,
        )
        for item in device_result.get("result", [])
    ]
    compact_entities = entity_result.get("result", {})
    entity_rows = compact_entities.get("entities", []) if isinstance(compact_entities, dict) else []
    entities = [
        EntityDisplayEntry(
            entity_id=str(item["ei"]),
            platform=str(item["pl"]),
            device_id=item.get("di") if isinstance(item.get("di"), str) else None,
            name=item.get("en") if isinstance(item.get("en"), str) else None,
            area_id=item.get("ai") if isinstance(item.get("ai"), str) else None,
        )
        for item in entity_rows
    ]
    return devices, entities


async def _clear_device_area(
    *,
    base_url: str,
    token: str,
    device_id: str,
) -> None:
    async with websockets.connect(_build_ws_url(base_url)) as websocket:
        await websocket.recv()
        await websocket.send(json.dumps({"type": "auth", "access_token": token}))
        auth_message = json.loads(await websocket.recv())
        if auth_message.get("type") != "auth_ok":
            raise FixtureError(f"HA websocket auth failed: {auth_message!r}")

        result = await _ws_command(
            websocket,
            1,
            {
                "type": "config/device_registry/update",
                "device_id": device_id,
                "area_id": None,
            },
        )

    if not result.get("success"):
        raise FixtureError(f"Failed to clear device area for {device_id}: {result!r}")


def _find_fixture_device(
    devices: list[DeviceEntry],
    *,
    entry_id: str,
    climate_name: str,
) -> DeviceEntry:
    matches = [
        device
        for device in devices
        if device.primary_config_entry == entry_id
        and climate_name in {device.name, device.name_by_user}
    ]
    if len(matches) != 1:
        raise FixtureError(
            f"Expected exactly one dedicated fixture device for {entry_id}, got {len(matches)}."
        )
    return matches[0]


def _find_fixture_climate_entity(
    entities: list[EntityDisplayEntry],
    *,
    device_id: str,
) -> EntityDisplayEntry:
    matches = [
        entity
        for entity in entities
        if entity.device_id == device_id
        and entity.platform == "virtual_climate"
        and entity.entity_id.startswith("climate.")
    ]
    if len(matches) != 1:
        raise FixtureError(
            f"Expected exactly one dedicated fixture climate entity for device {device_id}, "
            f"got {len(matches)}."
        )
    return matches[0]


def _wait_for_fixture_entity(
    *,
    base_url: str,
    token: str,
    entry_id: str,
    climate_name: str,
    wait_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[DeviceEntry, EntityDisplayEntry]:
    deadline = time.monotonic() + wait_timeout_seconds
    while True:
        devices, entities = asyncio.run(_get_registry_data(base_url=base_url, token=token))
        try:
            device = _find_fixture_device(devices, entry_id=entry_id, climate_name=climate_name)
            entity = _find_fixture_climate_entity(entities, device_id=device.id)
            return device, entity
        except FixtureError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(poll_interval_seconds)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        parser.error(f"{TOKEN_ENV_VAR} must be set to a valid HA long-lived token.")

    entries = _get_config_entries(base_url=args.base_url, token=token)
    fixture_entry = _find_existing_fixture_entry(entries, args.fixture_title)

    lines: list[str] = []
    if fixture_entry is None:
        fixture_entry = _create_fixture_entry(
            base_url=args.base_url,
            token=token,
            fixture_title=args.fixture_title,
            climate_name=args.climate_name,
            initial_current_temperature=args.initial_current_temperature,
            initial_target_temperature=args.initial_target_temperature,
        )
        lines.append(
            f"Created dedicated no-area Virtual Climate entry {fixture_entry.entry_id} "
            f"({fixture_entry.title})."
        )
    else:
        lines.append(
            f"Using existing dedicated no-area Virtual Climate entry {fixture_entry.entry_id} "
            f"({fixture_entry.title})."
        )

    device, entity = _wait_for_fixture_entity(
        base_url=args.base_url,
        token=token,
        entry_id=fixture_entry.entry_id,
        climate_name=args.climate_name,
        wait_timeout_seconds=args.wait_timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    lines.append(f"Fixture climate entity: {entity.entity_id}")
    lines.append(f"Fixture device: {device.id}")

    if device.area_id is not None:
        previous_area_id = device.area_id
        asyncio.run(
            _clear_device_area(
                base_url=args.base_url,
                token=token,
                device_id=device.id,
            )
        )
        device, entity = _wait_for_fixture_entity(
            base_url=args.base_url,
            token=token,
            entry_id=fixture_entry.entry_id,
            climate_name=args.climate_name,
            wait_timeout_seconds=args.wait_timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        lines.append(f"Cleared fixture device area assignment {previous_area_id!r}.")

    if device.area_id is not None:
        raise FixtureError(
            f"Dedicated fixture device {device.id} still has area_id={device.area_id!r}."
        )
    if entity.area_id is not None:
        raise FixtureError(
            "Dedicated fixture climate entity "
            f"{entity.entity_id} still has area_id={entity.area_id!r}."
        )

    lines.append("Dedicated no-area fixture is ready.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FixtureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
