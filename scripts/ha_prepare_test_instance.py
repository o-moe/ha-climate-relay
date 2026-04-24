#!/usr/bin/env python3
"""Prepare the Home Assistant test instance for GUI or smoke tests."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://haos-test.local:8123"
TOKEN_ENV_VAR = "HOME_ASSISTANT_TOKEN"
DEFAULT_UPDATE_ENTITIES = (
    "update.virtual_climate_update",
    "update.climaterelaycore_update",
)


class PrepareError(RuntimeError):
    """Raised when preparing the HA test instance fails."""


@dataclass(frozen=True)
class UpdateState:
    """Represent an HA update entity."""

    entity_id: str
    state: str
    installed_version: str | None
    latest_version: str | None
    in_progress: bool
    skipped_version: str | None

    @classmethod
    def from_api_payload(cls, payload: dict[str, Any]) -> UpdateState:
        attrs = dict(payload.get("attributes", {}))
        return cls(
            entity_id=str(payload["entity_id"]),
            state=str(payload["state"]),
            installed_version=_as_optional_str(attrs.get("installed_version")),
            latest_version=_as_optional_str(attrs.get("latest_version")),
            in_progress=bool(attrs.get("in_progress", False)),
            skipped_version=_as_optional_str(attrs.get("skipped_version")),
        )


def _as_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Update the required HACS-backed integrations in the HA test instance "
            "and restart Home Assistant afterwards."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Home Assistant base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--restart-timeout-seconds",
        type=float,
        default=180.0,
        help="Maximum wait time for Home Assistant to come back after restart.",
    )
    parser.add_argument(
        "--update-timeout-seconds",
        type=float,
        default=240.0,
        help="Maximum wait time per update entity to finish installation.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval for update and restart status checks.",
    )
    parser.add_argument(
        "--entity-id",
        action="append",
        dest="entity_ids",
        default=None,
        help=(
            "Update entity to process. Can be passed multiple times. "
            f"Defaults: {', '.join(DEFAULT_UPDATE_ENTITIES)}"
        ),
    )
    return parser


def _request_json(
    *,
    base_url: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
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
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise PrepareError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise PrepareError(f"{method} {path} failed: {exc.reason}") from exc


def _get_update_state(*, base_url: str, token: str, entity_id: str) -> UpdateState:
    payload = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/states/{entity_id}",
    )
    if not isinstance(payload, dict):
        raise PrepareError(f"Expected state payload for {entity_id}.")
    return UpdateState.from_api_payload(payload)


def _call_service(
    *,
    base_url: str,
    token: str,
    domain: str,
    service: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    return _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/services/{domain}/{service}",
        method="POST",
        payload=payload or {},
    )


def _request_restart(*, base_url: str, token: str) -> str:
    try:
        _call_service(
            base_url=base_url,
            token=token,
            domain="homeassistant",
            service="restart",
        )
        return "accepted"
    except PrepareError as exc:
        message = str(exc)
        if "HTTP 504" in message:
            return "accepted_via_504"
        raise


def _wait_for_update_completion(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    expected_version: str | None,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> UpdateState:
    deadline = time.monotonic() + timeout_seconds
    while True:
        state = _get_update_state(base_url=base_url, token=token, entity_id=entity_id)
        if not state.in_progress and (
            expected_version is None or state.installed_version == expected_version
        ):
            return state
        if time.monotonic() >= deadline:
            raise PrepareError(
                f"Timed out waiting for {entity_id} update completion. "
                f"Installed={state.installed_version!r}, latest={state.latest_version!r}, "
                f"in_progress={state.in_progress}."
            )
        time.sleep(poll_interval_seconds)


def _wait_for_api_recovery(
    *,
    base_url: str,
    token: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    saw_shutdown = False
    while True:
        try:
            payload = _request_json(
                base_url=base_url,
                token=token,
                path="/api/",
                timeout=10.0,
            )
            if (
                saw_shutdown
                and isinstance(payload, dict)
                and payload.get("message") == "API running."
            ):
                return
        except PrepareError:
            saw_shutdown = True
        if time.monotonic() >= deadline:
            raise PrepareError("Timed out waiting for Home Assistant restart recovery.")
        time.sleep(poll_interval_seconds)


def _process_update_entity(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    update_timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[str]:
    before = _get_update_state(base_url=base_url, token=token, entity_id=entity_id)
    lines = [
        (
            f"{entity_id}: installed={before.installed_version!r}, "
            f"latest={before.latest_version!r}, skipped={before.skipped_version!r}"
        )
    ]

    needs_install = before.installed_version != before.latest_version
    if not needs_install:
        lines.append(f"{entity_id}: already up to date.")
        return lines

    if before.skipped_version is not None:
        _call_service(
            base_url=base_url,
            token=token,
            domain="update",
            service="clear_skipped",
            payload={"entity_id": entity_id},
        )
        lines.append(f"{entity_id}: cleared skipped version {before.skipped_version!r}.")

    _call_service(
        base_url=base_url,
        token=token,
        domain="update",
        service="install",
        payload={"entity_id": entity_id},
    )
    after = _wait_for_update_completion(
        base_url=base_url,
        token=token,
        entity_id=entity_id,
        expected_version=before.latest_version,
        timeout_seconds=update_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    lines.append(
        f"{entity_id}: updated to {after.installed_version!r}."
    )
    return lines


def _run_prepare(args: argparse.Namespace) -> list[str]:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise PrepareError(
            f"Missing {TOKEN_ENV_VAR}. Export the long-lived Home Assistant token first."
        )

    entity_ids = tuple(args.entity_ids or DEFAULT_UPDATE_ENTITIES)
    lines = [f"Preparing HA test instance: {args.base_url}"]

    for entity_id in entity_ids:
        lines.extend(
            _process_update_entity(
                base_url=args.base_url,
                token=token,
                entity_id=entity_id,
                update_timeout_seconds=args.update_timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        )

    restart_result = _request_restart(base_url=args.base_url, token=token)
    lines.append(f"homeassistant.restart: {restart_result}.")

    _wait_for_api_recovery(
        base_url=args.base_url,
        token=token,
        timeout_seconds=args.restart_timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    lines.append("Home Assistant restart: recovered.")
    return lines


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        lines = _run_prepare(args)
    except PrepareError as exc:
        print(f"HA prepare failed: {exc}", file=sys.stderr)
        return 1

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
