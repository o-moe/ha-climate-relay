#!/usr/bin/env python3
"""Run the documented Home Assistant acceptance workflow for an epic."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://haos-test.local:8123"
TOKEN_ENV_VAR = "HOME_ASSISTANT_TOKEN"
EPIC_1_ACCEPTANCE_VERSION = "v0.1.0-alpha.21"
EPIC_2_ACCEPTANCE_VERSION = "v0.2.0-alpha.30"
LOCAL_ENV_FILE = Path(".env.local")
DEFAULT_ARTIFACT_DIR = Path("artifacts") / "acceptance"
EPIC_2_PRIMARY_CLIMATES = (
    "climate.virtual_climate_office",
    "climate.virtual_climate_living_room",
)
EPIC_2_WINDOW_ENTITIES = (
    "binary_sensor.virtual_window_office",
    "binary_sensor.virtual_window_living_room",
)


class AcceptanceError(RuntimeError):
    """Raised when one acceptance step fails."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the repository-local HA acceptance workflow for one documented epic."
    )
    parser.add_argument(
        "--epic",
        required=True,
        choices=("1", "2", "3"),
        help="Epic acceptance workflow to run.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Home Assistant base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--skip-gui",
        action="store_true",
        help="Run backend/API preparation only and skip the Playwright GUI step.",
    )
    parser.add_argument(
        "--install-version",
        default=None,
        help=(
            "Explicit Climate Relay version to install in Home Assistant. "
            "Defaults to the documented acceptance version for the selected epic."
        ),
    )
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Directory for GUI failure screenshots and browser diagnostics.",
    )
    return parser


def _run_command(
    command: list[str],
    *,
    env: dict[str, str],
    description: str,
    cwd: Path | None = None,
) -> None:
    print(f"[acceptance] {description}")
    print(f"[acceptance] $ {' '.join(shlex.quote(part) for part in command)}")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0 or "### Error" in result.stdout or "### Error" in result.stderr:
        raise AcceptanceError(f"{description} failed with exit code {result.returncode}.")


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
        with urlopen(request, timeout=30.0) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AcceptanceError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise AcceptanceError(f"{method} {path} failed: {exc.reason}") from exc


def _set_entity_state(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    state: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/states/{entity_id}",
        method="POST",
        payload={"state": state, "attributes": attributes or {}},
    )


def _find_epic_2_room_entity(*, base_url: str, token: str) -> str:
    room_entities = _find_epic_2_room_entities(base_url=base_url, token=token)
    return room_entities["climate.virtual_climate_office"]


def _find_room_entity_for_primary(
    *,
    base_url: str,
    token: str,
    primary_climate_entity_id: str,
    timeout_seconds: float = 20.0,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while True:
        states = _request_json(base_url=base_url, token=token, path="/api/states")
        if not isinstance(states, list):
            raise AcceptanceError("Expected /api/states to return a list.")
        candidates = [
            state
            for state in states
            if isinstance(state, dict)
            and str(state.get("entity_id", "")).startswith("climate.")
            and state.get("attributes", {}).get("primary_climate_entity_id")
            == primary_climate_entity_id
        ]
        if len(candidates) == 1:
            return str(candidates[0]["entity_id"])
        if len(candidates) > 1:
            raise AcceptanceError(
                "Expected exactly one room climate entity for "
                f"{primary_climate_entity_id}, found {len(candidates)}."
            )
        if time.monotonic() >= deadline:
            raise AcceptanceError(
                f"Timed out waiting for room climate entity for {primary_climate_entity_id}."
            )
        time.sleep(0.5)


def _find_epic_2_room_entities(*, base_url: str, token: str) -> dict[str, str]:
    states = _request_json(base_url=base_url, token=token, path="/api/states")
    if not isinstance(states, list):
        raise AcceptanceError("Expected /api/states to return a list.")
    room_entities: dict[str, str] = {}
    for primary_climate_entity_id in EPIC_2_PRIMARY_CLIMATES:
        candidates = [
            state
            for state in states
            if isinstance(state, dict)
            and str(state.get("entity_id", "")).startswith("climate.")
            and state.get("attributes", {}).get("primary_climate_entity_id")
            == primary_climate_entity_id
        ]
        if len(candidates) != 1:
            raise AcceptanceError(
                "Expected exactly one Epic 2 room climate entity for "
                f"{primary_climate_entity_id}, found {len(candidates)}."
            )
        room_entities[primary_climate_entity_id] = str(candidates[0]["entity_id"])
    return room_entities


def _wait_for_room_context(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    expected_context: str,
    timeout_seconds: float = 20.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        payload = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/states/{entity_id}",
        )
        if isinstance(payload, dict):
            context = payload.get("attributes", {}).get("active_control_context")
            if context == expected_context:
                return
        if time.monotonic() >= deadline:
            raise AcceptanceError(
                f"Timed out waiting for {entity_id} active_control_context="
                f"{expected_context!r}; last payload={payload!r}."
            )
        time.sleep(0.5)


def _wait_for_room_attributes(
    *,
    base_url: str,
    token: str,
    entity_id: str,
    expected_attributes: dict[str, Any],
    timeout_seconds: float = 20.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        payload = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/states/{entity_id}",
        )
        if isinstance(payload, dict):
            attributes = payload.get("attributes", {})
            if all(attributes.get(key) == value for key, value in expected_attributes.items()):
                return
        if time.monotonic() >= deadline:
            raise AcceptanceError(
                f"Timed out waiting for {entity_id} attributes "
                f"{expected_attributes!r}; last payload={payload!r}."
            )
        time.sleep(0.5)


def _call_area_override(
    *,
    base_url: str,
    token: str,
    area_id: str,
    target_temperature: float,
) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path="/api/services/climate_relay_core/set_area_override",
        method="POST",
        payload={
            "area_id": area_id,
            "target_temperature": target_temperature,
            "termination_type": "duration",
            "duration_minutes": 30,
        },
    )


def _clear_area_override(*, base_url: str, token: str, area_id: str) -> None:
    _request_json(
        base_url=base_url,
        token=token,
        path="/api/services/climate_relay_core/clear_area_override",
        method="POST",
        payload={"area_id": area_id},
    )


def _find_config_entry_id(*, base_url: str, token: str, domain: str) -> str:
    entries = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/entry",
    )
    if not isinstance(entries, list):
        raise AcceptanceError("Expected config entry list from Home Assistant.")
    candidates = [entry for entry in entries if entry.get("domain") == domain]
    if len(candidates) != 1:
        raise AcceptanceError(
            f"Expected exactly one {domain} config entry, found {len(candidates)}."
        )
    return str(candidates[0]["entry_id"])


def _prepare_epic_1_profile(*, base_url: str, token: str) -> None:
    entry_id = _find_config_entry_id(
        base_url=base_url,
        token=token,
        domain="climate_relay_core",
    )
    flow = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/options/flow",
        method="POST",
        payload={"handler": entry_id},
    )
    flow_id = str(flow["flow_id"])
    flow = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "person_entity_ids": ["person.bjorn"],
            "unknown_state_handling": "away",
            "fallback_temperature": 20.0,
            "manual_override_reset_enabled": False,
            "simulation_mode": True,
            "verbose_logging": False,
        },
    )
    if flow.get("step_id") != "room":
        if flow.get("step_id") != "profiles":
            raise AcceptanceError(f"Expected profiles options step, got {flow!r}.")
        flow = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/config/config_entries/options/flow/{flow_id}",
            method="POST",
            payload={"profile_action": "add"},
        )
    if flow.get("step_id") != "room":
        raise AcceptanceError(f"Expected room options step, got {flow!r}.")
    result = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "primary_climate_entity_id": "climate.virtual_climate_office",
            "home_target_temperature": 20.0,
            "away_target_type": "absolute",
            "away_target_temperature": 17.0,
            "schedule_home_start": "06:00:00",
            "schedule_home_end": "22:00:00",
        },
    )
    if result.get("step_id") == "profiles":
        result = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/config/config_entries/options/flow/{flow_id}",
            method="POST",
            payload={"profile_action": "finish"},
        )
    if result.get("type") != "create_entry":
        raise AcceptanceError(f"Expected profile options to save, got {result!r}.")
    time.sleep(5.0)


def _prepare_epic_2_profile(*, base_url: str, token: str) -> None:
    entry_id = _find_config_entry_id(
        base_url=base_url,
        token=token,
        domain="climate_relay_core",
    )
    flow = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/options/flow",
        method="POST",
        payload={"handler": entry_id},
    )
    flow_id = str(flow["flow_id"])
    flow = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "person_entity_ids": ["person.bjorn"],
            "unknown_state_handling": "away",
            "fallback_temperature": 20.0,
            "manual_override_reset_enabled": False,
            "simulation_mode": True,
            "verbose_logging": False,
        },
    )
    if flow.get("step_id") != "profiles":
        raise AcceptanceError(f"Expected profiles options step, got {flow!r}.")

    _clear_profiles_in_flow(base_url=base_url, token=token, flow_id=flow_id)
    _add_epic_2_profile(
        base_url=base_url,
        token=token,
        flow_id=flow_id,
        primary_climate_entity_id=EPIC_2_PRIMARY_CLIMATES[0],
        window_entity_id=EPIC_2_WINDOW_ENTITIES[0],
        home_target_temperature=20.0,
        away_target_temperature=17.0,
    )
    _add_epic_2_profile(
        base_url=base_url,
        token=token,
        flow_id=flow_id,
        primary_climate_entity_id=EPIC_2_PRIMARY_CLIMATES[1],
        window_entity_id=EPIC_2_WINDOW_ENTITIES[1],
        home_target_temperature=19.0,
        away_target_temperature=16.0,
    )
    result = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={"profile_action": "finish"},
    )
    if result.get("type") != "create_entry":
        raise AcceptanceError(f"Expected profile options to save, got {result!r}.")
    time.sleep(5.0)


def _prepare_epic_3_profile(*, base_url: str, token: str) -> None:
    entry_id = _find_config_entry_id(
        base_url=base_url,
        token=token,
        domain="climate_relay_core",
    )
    flow = _request_json(
        base_url=base_url,
        token=token,
        path="/api/config/config_entries/options/flow",
        method="POST",
        payload={"handler": entry_id},
    )
    flow_id = str(flow["flow_id"])
    flow = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "person_entity_ids": ["person.bjorn"],
            "unknown_state_handling": "away",
            "fallback_temperature": 20.0,
            "manual_override_reset_enabled": False,
            "simulation_mode": True,
            "verbose_logging": False,
        },
    )
    if flow.get("step_id") != "profiles":
        raise AcceptanceError(f"Expected profiles options step, got {flow!r}.")

    _clear_profiles_in_flow(base_url=base_url, token=token, flow_id=flow_id)
    _add_epic_2_profile(
        base_url=base_url,
        token=token,
        flow_id=flow_id,
        primary_climate_entity_id=EPIC_2_PRIMARY_CLIMATES[0],
        window_entity_id=EPIC_2_WINDOW_ENTITIES[0],
        home_target_temperature=20.0,
        away_target_temperature=17.0,
    )
    result = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={"profile_action": "finish"},
    )
    if result.get("type") != "create_entry":
        raise AcceptanceError(f"Expected profile options to save, got {result!r}.")
    time.sleep(5.0)


def _add_epic_2_profile(
    *,
    base_url: str,
    token: str,
    flow_id: str,
    primary_climate_entity_id: str,
    window_entity_id: str,
    home_target_temperature: float,
    away_target_temperature: float,
) -> None:
    flow = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={"profile_action": "add"},
    )
    if flow.get("step_id") != "room":
        raise AcceptanceError(f"Expected room options step, got {flow!r}.")
    flow = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "primary_climate_entity_id": primary_climate_entity_id,
            "window_entity_id": window_entity_id,
            "window_action_type": "minimum_temperature",
            "window_open_delay_seconds": 0,
            "home_target_temperature": home_target_temperature,
            "away_target_type": "absolute",
            "away_target_temperature": away_target_temperature,
            "schedule_home_start": "06:00:00",
            "schedule_home_end": "22:00:00",
        },
    )
    if flow.get("step_id") != "profiles":
        raise AcceptanceError(f"Expected profiles step after adding profile, got {flow!r}.")


def _clear_profiles_in_flow(*, base_url: str, token: str, flow_id: str) -> None:
    """Remove existing profiles from an options flow for deterministic acceptance setup."""
    for _attempt in range(8):
        flow = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/config/config_entries/options/flow/{flow_id}",
            method="POST",
            payload={"profile_action": "remove"},
        )
        if flow.get("errors", {}).get("profile_action") == "profile_required":
            return
        if flow.get("step_id") != "profile_select_remove":
            raise AcceptanceError(f"Expected profile removal selection step, got {flow!r}.")
        flow = _request_json(
            base_url=base_url,
            token=token,
            path=f"/api/config/config_entries/options/flow/{flow_id}",
            method="POST",
            payload={"profile_index": "0"},
        )
        if flow.get("step_id") != "profiles":
            raise AcceptanceError(f"Expected profiles step after removing profile, got {flow!r}.")
    raise AcceptanceError("Could not clear existing regulation profiles for acceptance setup.")


def _load_local_env_file() -> None:
    """Load ignored local environment values when the shell did not export them."""
    if os.environ.get(TOKEN_ENV_VAR) or not LOCAL_ENV_FILE.exists():
        return

    for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == TOKEN_ENV_VAR and value:
            os.environ[TOKEN_ENV_VAR] = value
            return


def _playwright_env() -> dict[str, str]:
    env = os.environ.copy()
    codex_home = env.get("CODEX_HOME", str(Path.home() / ".codex"))
    env.setdefault("CODEX_HOME", codex_home)
    env.setdefault(
        "PWCLI",
        str(Path(codex_home) / "skills" / "playwright" / "scripts" / "playwright_cli.sh"),
    )
    env.setdefault("NPM_CONFIG_CACHE", "/tmp/codex-npm-cache")
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/tmp/codex-playwright-browsers")
    return env


def _capture_gui_artifact(
    *,
    pwcli: str,
    session: str,
    env: dict[str, str],
    artifact_dir: Path,
    name: str,
) -> None:
    """Best-effort screenshot capture for a failed GUI acceptance step."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifact_dir / f"{name}-{session}.png"
    code = (
        "async () => {"
        f"await page.screenshot({{path: {str(screenshot_path)!r}, fullPage: true}});"
        f"console.log('Saved GUI failure screenshot: {screenshot_path}');"
        "}"
    )
    subprocess.run(
        [pwcli, f"-s={session}", "run-code", code],
        env=env,
        check=False,
        text=True,
    )


def _gui_epic_1_validation_code(base_url: str) -> str:
    return f"""async () => {{
const baseUrl = {base_url!r};

async function ensureLoggedIn() {{
  await page.goto(baseUrl);
  await page.waitForLoadState("domcontentloaded");
  if (page.url().includes("/auth/authorize")) {{
    await page.getByRole("textbox", {{ name: "Benutzername" }}).waitFor({{ timeout: 20000 }});
    await page.getByRole("textbox", {{ name: "Benutzername" }}).fill("codex");
    await page.getByRole("textbox", {{ name: "Passwort" }}).fill("codex");
    await page.getByRole("button", {{ name: "Anmelden" }}).click();
  }}
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {{
    await page.waitForTimeout(1000);
    if (!page.url().includes("/auth/authorize")) {{
      return;
    }}
  }}
  throw new Error("HA login did not complete.");
}}

async function openRegulationProfile() {{
  await page.goto(baseUrl + "/config/integrations/integration/climate_relay_core");
  await page.getByRole("button", {{ name: "Konfigurieren" }}).click();
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
  await page.getByText("Regulation Profiles", {{ exact: true }}).waitFor({{ timeout: 10000 }});
}}

async function clearPrimaryClimate() {{
  const primarySelector = page.locator("ha-selector").first();
  const clearButton = primarySelector.locator(".clear ha-button, .clear button").first();
  if (await clearButton.count()) {{
    await clearButton.click();
  }}
}}

async function expectText(text) {{
  await page.waitForFunction(
    (expected) => document.body && document.body.innerText.includes(expected),
    text,
    {{ timeout: 10000 }},
  );
}}

async function selectPrimaryClimate(name) {{
  const primarySelector = page.locator("ha-selector").first();
  await primarySelector.locator("#item").click();
  const dialog = page.getByRole("dialog", {{ name: "Primary climate entity" }});
  await dialog.getByText(name, {{ exact: true }}).click();
}}

async function chooseProfileAction(action) {{
  const selector = page.locator("ha-selector-select").first();
  await selector.locator("select").first().selectOption(action);
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
}}

await ensureLoggedIn();
await openRegulationProfile();
await chooseProfileAction("add");
await clearPrimaryClimate();
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Select exactly one primary climate entity.");
await selectPrimaryClimate("No Area Fixture");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Assign the primary climate entity to a Home Assistant area first.");
}}""".strip()


def _gui_epic_3_schedule_card_code(base_url: str, card_bundle_path: Path) -> str:
    return f"""async () => {{
const baseUrl = {base_url!r};
const cardBundlePath = {str(card_bundle_path)!r};

async function ensureLoggedIn() {{
  await page.goto(baseUrl);
  await page.waitForLoadState("domcontentloaded");
  if (page.url().includes("/auth/authorize")) {{
    await page.getByRole("textbox", {{ name: "Benutzername" }}).waitFor({{ timeout: 20000 }});
    await page.getByRole("textbox", {{ name: "Benutzername" }}).fill("codex");
    await page.getByRole("textbox", {{ name: "Passwort" }}).fill("codex");
    await page.getByRole("button", {{ name: "Anmelden" }}).click();
  }}
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {{
    await page.waitForTimeout(1000);
    if (!page.url().includes("/auth/authorize")) {{
      return;
    }}
  }}
  throw new Error("HA login did not complete.");
}}

async function mountCard() {{
  await page.addScriptTag({{ path: cardBundlePath, type: "module" }});
  await page.evaluate(() => {{
    const existing = document.querySelector("#climate-relay-acceptance-root");
    existing?.remove();
    const root = document.createElement("div");
    root.id = "climate-relay-acceptance-root";
    root.style.position = "fixed";
    root.style.inset = "24px";
    root.style.zIndex = "10000";
    root.style.overflow = "auto";
    root.style.background = "var(--primary-background-color, white)";
    document.body.append(root);

    const card = document.createElement("climate-relay-card");
    card.setConfig({{ title: "Climate Relay Acceptance" }});
    root.append(card);

    const updateHass = () => {{
      const homeAssistant = document.querySelector("home-assistant");
      if (homeAssistant?.hass) {{
        card.hass = homeAssistant.hass;
      }}
    }};
    updateHass();
    window.__climateRelayAcceptanceInterval = window.setInterval(updateHass, 500);
  }});
}}

async function waitForText(text) {{
  await page.waitForFunction(
    (expected) => document.body && document.body.innerText.includes(expected),
    text,
    {{ timeout: 20000 }},
  );
}}

async function waitForCardText(text) {{
  await page.waitForFunction(
    (expected) => {{
      const card = document.querySelector("climate-relay-card");
      return card?.shadowRoot?.innerText.includes(expected);
    }},
    text,
    {{ timeout: 20000 }},
  );
}}

async function setSchedule(labelSuffix, value) {{
  await page.evaluate(
    ([inputLabelSuffix, inputValue]) => {{
      const card = document.querySelector("climate-relay-card");
      const input = Array.from(card.shadowRoot.querySelectorAll("input")).find(
        (candidate) => candidate.getAttribute("aria-label")?.endsWith(inputLabelSuffix),
      );
      if (!input) {{
        throw new Error(`Missing schedule input ending with ${{inputLabelSuffix}}`);
      }}
      input.value = inputValue;
      input.dispatchEvent(new InputEvent("input", {{ bubbles: true, composed: true }}));
    }},
    [label, value],
  );
}}

async function clickSave() {{
  await page.evaluate(() => {{
    const card = document.querySelector("climate-relay-card");
    const button = Array.from(card.shadowRoot.querySelectorAll("button")).find(
      (candidate) => candidate.textContent.includes("Save"),
    );
    if (!button) {{
      throw new Error("Missing schedule Save button.");
    }}
    button.click();
  }});
}}

await ensureLoggedIn();
await mountCard();
await waitForCardText("Climate Relay Acceptance");
await waitForCardText("Schedule start");
await waitForCardText("06:00:00");
await setSchedule(" schedule start", "07:15");
await setSchedule(" schedule end", "21:45");
await clickSave();
await waitForCardText("Schedule saved. Waiting for Home Assistant state to update.");
}}""".strip()


def _gui_epic_1_profile_save_code(base_url: str) -> str:
    return f"""async () => {{
const baseUrl = {base_url!r};

async function ensureLoggedIn() {{
  await page.goto(baseUrl);
  await page.waitForLoadState("domcontentloaded");
  if (page.url().includes("/auth/authorize")) {{
    await page.getByRole("textbox", {{ name: "Benutzername" }}).waitFor({{ timeout: 20000 }});
    await page.getByRole("textbox", {{ name: "Benutzername" }}).fill("codex");
    await page.getByRole("textbox", {{ name: "Passwort" }}).fill("codex");
    await page.getByRole("button", {{ name: "Anmelden" }}).click();
  }}
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {{
    await page.waitForTimeout(1000);
    if (!page.url().includes("/auth/authorize")) {{
      return;
    }}
  }}
  throw new Error("HA login did not complete.");
}}

async function openRegulationProfile() {{
  await page.goto(baseUrl + "/config/integrations/integration/climate_relay_core");
  await page.getByRole("button", {{ name: "Konfigurieren" }}).click();
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
  await page.getByText("Regulation Profiles", {{ exact: true }}).waitFor({{ timeout: 10000 }});
}}

async function selectPrimaryClimate(name) {{
  const primarySelector = page.locator("ha-selector").first();
  await primarySelector.locator("#item").click();
  const dialog = page.getByRole("dialog", {{ name: "Primary climate entity" }});
  await dialog.getByText(name, {{ exact: true }}).click();
}}

async function setTimeInput(selectorIndex, hours, minutes) {{
  const selector = page.locator("ha-selector-time").nth(selectorIndex);
  for (const [name, value] of [["hours", hours], ["minutes", minutes]]) {{
    const input = selector.locator(`input[name='${{name}}']`);
    await input.fill(value);
    await input.dispatchEvent("input");
    await input.dispatchEvent("change");
  }}
  await selector.evaluate((element, value) => {{
    element.value = value;
    element.dispatchEvent(new CustomEvent("value-changed", {{
      bubbles: true,
      composed: true,
      detail: {{ value }},
    }}));
  }}, `${{hours}}:${{minutes}}:00`);
}}

async function chooseProfileAction(action) {{
  const selector = page.locator("ha-selector-select").first();
  await selector.locator("select").first().selectOption(action);
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
}}

await ensureLoggedIn();
await openRegulationProfile();
await chooseProfileAction("add");
await selectPrimaryClimate("Office");
const timeSelectors = page.locator("ha-selector-time");
await timeSelectors.nth(0).waitFor({{ timeout: 10000 }});
await timeSelectors.nth(1).waitFor({{ timeout: 10000 }});
await setTimeInput(0, "06", "00");
await setTimeInput(1, "22", "00");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await page.getByText("Regulation Profiles", {{ exact: true }}).waitFor({{ timeout: 10000 }});
await chooseProfileAction("finish");
await page.getByText("Regulation Profile", {{ exact: true }}).waitFor({{
  timeout: 10000,
  state: "detached",
}});
}}""".strip()


def _gui_epic_2_options_flow_code(base_url: str) -> str:
    return f"""async () => {{
const baseUrl = {base_url!r};

async function ensureLoggedIn() {{
  await page.goto(baseUrl);
  await page.waitForLoadState("domcontentloaded");
  if (page.url().includes("/auth/authorize")) {{
    await page.getByRole("textbox", {{ name: "Benutzername" }}).waitFor({{ timeout: 20000 }});
    await page.getByRole("textbox", {{ name: "Benutzername" }}).fill("codex");
    await page.getByRole("textbox", {{ name: "Passwort" }}).fill("codex");
    await page.getByRole("button", {{ name: "Anmelden" }}).click();
  }}
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {{
    await page.waitForTimeout(1000);
    if (!page.url().includes("/auth/authorize")) {{
      return;
    }}
  }}
  throw new Error("HA login did not complete.");
}}

async function openRegulationProfile() {{
  await page.goto(baseUrl + "/config/integrations/integration/climate_relay_core");
  await page.getByRole("button", {{ name: "Konfigurieren" }}).click();
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
  await page.getByText("Regulation Profiles", {{ exact: true }}).waitFor({{ timeout: 10000 }});
}}

async function expectText(text) {{
  await installBrowserHelpers();
  const found = await page.waitForFunction(
    (expected) => window.__climateRelayAcceptance.readText(document).includes(expected),
    text,
    {{ timeout: 10000 }},
  ).catch(() => null);
  if (!found) {{
    const visibleText = await page.evaluate(() =>
      window.__climateRelayAcceptance.readText(document).replace(/\\s+/g, " ").slice(0, 1600),
    );
    throw new Error(
      `Timed out waiting for text: ${{text}}. Visible text excerpt: ${{visibleText}}`,
    );
  }}
}}

async function expectAnyText(texts) {{
  await installBrowserHelpers();
  const found = await page.waitForFunction(
    (expectedTexts) => {{
      const pageText = window.__climateRelayAcceptance.readText(document);
      return expectedTexts.some((text) => pageText.includes(text));
    }},
    texts,
    {{ timeout: 10000 }},
  ).catch(() => null);
  if (!found) {{
    const visibleText = await page.evaluate(() =>
      window.__climateRelayAcceptance.readText(document).replace(/\\s+/g, " ").slice(0, 1600),
    );
    throw new Error(
      `Timed out waiting for any text: ${{texts.join(", ")}}. `
        + `Visible text excerpt: ${{visibleText}}`,
    );
  }}
}}

async function scrollDialog(deltaY, steps = 1) {{
  await installBrowserHelpers();
  await page.evaluate((delta) => {{
    window.__climateRelayAcceptance.scrollAll(delta);
  }}, deltaY);
  for (let index = 0; index < steps; index += 1) {{
    await page.mouse.wheel(0, deltaY);
    await page.keyboard.press(deltaY > 0 ? "PageDown" : "PageUp");
    await page.waitForTimeout(200);
  }}
  await page.evaluate((delta) => {{
    window.__climateRelayAcceptance.scrollAll(delta);
  }}, deltaY);
  await page.waitForTimeout(500);
}}

async function revealText(text) {{
  await installBrowserHelpers();
  for (let attempt = 0; attempt < 8; attempt += 1) {{
    if (await page.getByText(text, {{ exact: false }}).first().isVisible().catch(() => false)) {{
      return;
    }}
    if (await page.evaluate((expected) =>
      window.__climateRelayAcceptance.readText(document).includes(expected),
      text,
    )) {{
      await scrollDialog(500, 1);
    }} else {{
      await page.waitForTimeout(250);
    }}
  }}
  await expectText(text);
  throw new Error(`Text exists but was not visibly reachable in the options dialog: ${{text}}`);
}}

async function installBrowserHelpers() {{
  await page.evaluate(() => {{
    window.__climateRelayAcceptance = {{
      readText(root) {{
        let text = root.innerText || root.textContent || "";
        for (const element of root.querySelectorAll("*")) {{
          if (element.shadowRoot) {{
            text += "\\n" + this.readText(element.shadowRoot);
          }}
        }}
        return text;
      }},
      scrollAll(delta) {{
        function scroll(root) {{
          for (const element of root.querySelectorAll("*")) {{
            if (element.scrollHeight > element.clientHeight) {{
              element.scrollTop += delta;
            }}
            const style = getComputedStyle(element);
            const isScrollable = style.overflowY === "auto" || style.overflowY === "scroll";
            if (isScrollable && element.clientHeight) {{
              element.scrollTop += delta;
            }}
            if (element.shadowRoot) {{
              scroll(element.shadowRoot);
            }}
          }}
        }}
        scroll(document);
      }},
      setSelectorValue(localName, selectorIndex, optionLabel, value) {{
        const matches = [];
        function walk(root) {{
          for (const element of root.querySelectorAll("*")) {{
            if (element.localName === localName) {{
              matches.push(element);
            }}
            if (element.shadowRoot) {{
              walk(element.shadowRoot);
            }}
          }}
        }}
        walk(document);
        const element = matches.find((match) => this.readText(match).includes(optionLabel))
          || matches[selectorIndex];
        if (!element) {{
          throw new Error(`Missing selector host ${{localName}}[${{selectorIndex}}]`);
        }}
        const targets = [element];
        if (element.getRootNode().host) {{
          targets.push(element.getRootNode().host);
        }}
        for (const target of targets) {{
          target.value = value;
          target.dispatchEvent(new CustomEvent("value-changed", {{
            bubbles: true,
            composed: true,
            detail: {{ value }},
          }}));
        }}
      }},
    }};
  }});
}}

async function clearEntitySelector(selectorIndex) {{
  const entitySelector = page.locator("ha-selector").nth(selectorIndex);
  const clearButton = entitySelector.locator(".clear ha-button, .clear button").first();
  if (await clearButton.count()) {{
    await clearButton.click();
  }}
}}

async function selectEntity(selectorIndex, dialogName, optionText) {{
  const entitySelector = page.locator("ha-selector").nth(selectorIndex);
  await entitySelector.locator("#item").click();
  const dialog = page.getByRole("dialog", {{ name: dialogName }});
  await dialog.getByText(optionText, {{ exact: true }}).click();
}}

async function selectNativeOption(selectorIndex, optionValue, optionLabel) {{
  await installBrowserHelpers();
  const selectors = page.locator("ha-selector-select");
  const visibleSelectors = [];
  for (let index = 0; index < await selectors.count(); index += 1) {{
    const selector = selectors.nth(index);
    if (await selector.isVisible().catch(() => false)) {{
      visibleSelectors.push(selector);
    }}
  }}
  const selector = visibleSelectors.length
    ? visibleSelectors[Math.min(selectorIndex, visibleSelectors.length - 1)]
    : selectors.nth(selectorIndex);
  const nativeSelect = selector.locator("select").first();
  if (await nativeSelect.count()) {{
    await nativeSelect.selectOption(optionValue);
    return;
  }}
  const visibleOption = page.getByText(optionLabel, {{ exact: true }}).first();
  if (await visibleOption.isVisible().catch(() => false)) {{
    await visibleOption.click({{ timeout: 5000 }}).catch(async () => {{
      await visibleOption.evaluate((element) => element.click());
    }});
    await page.evaluate(
      ([index, label, value]) => window.__climateRelayAcceptance.setSelectorValue(
        "ha-selector-select",
        index,
        label,
        value,
      ),
      [selectorIndex, optionLabel, optionValue],
    );
    return;
  }}
  const menuSelect = selector.locator("mwc-select, ha-select").first();
  if (await menuSelect.isVisible().catch(() => false)) {{
    await menuSelect.click();
    await page.getByText(optionLabel, {{ exact: true }}).click();
    return;
  }}
  await page.evaluate(
    ([index, label, value]) => window.__climateRelayAcceptance.setSelectorValue(
      "ha-selector-select",
      index,
      label,
      value,
    ),
    [selectorIndex, optionLabel, optionValue],
  );
}}

async function resolveNumberSelector(selectorIndex) {{
  const selectors = page.locator("ha-selector-number");
  const visibleSelectors = [];
  for (let index = 0; index < await selectors.count(); index += 1) {{
    const selector = selectors.nth(index);
    const input = selector.locator("input").first();
    if (await input.isVisible().catch(() => false)) {{
      visibleSelectors.push(selector);
    }}
  }}
  if (visibleSelectors.length) {{
    return visibleSelectors[Math.min(selectorIndex, visibleSelectors.length - 1)];
  }}
  return selectors.nth(selectorIndex);
}}

async function setNumberInput(selectorIndex, value) {{
  const selector = await resolveNumberSelector(selectorIndex);
  const input = selector.locator("input").first();
  await input.fill(String(value));
  await input.dispatchEvent("input");
  await input.dispatchEvent("change");
  await selector.evaluate((element, value) => {{
    const targets = [element];
    if (element.getRootNode().host) {{
      targets.push(element.getRootNode().host);
    }}
    for (const target of targets) {{
      target.value = value;
      target.dispatchEvent(new CustomEvent("value-changed", {{
        bubbles: true,
        composed: true,
        detail: {{ value }},
      }}));
    }}
  }}, String(value));
  await page.keyboard.press("Tab");
  await page.waitForTimeout(500);
}}

async function clearNumberInput(selectorIndex) {{
  const selector = await resolveNumberSelector(selectorIndex);
  const input = selector.locator("input").first();
  await input.fill("");
  await input.dispatchEvent("input");
  await input.dispatchEvent("change");
  await selector.evaluate((element) => {{
    const targets = [element];
    if (element.getRootNode().host) {{
      targets.push(element.getRootNode().host);
    }}
    for (const target of targets) {{
      target.value = null;
      target.dispatchEvent(new CustomEvent("value-changed", {{
        bubbles: true,
        composed: true,
        detail: {{ value: null }},
      }}));
    }}
  }});
}}

async function setTextInput(selectorIndex, value) {{
  const selector = page.locator("ha-selector-text").nth(selectorIndex);
  const input = selector.locator("input").first();
  await input.fill(String(value));
  await input.dispatchEvent("input");
  await input.dispatchEvent("change");
  await page.evaluate(([index, value]) => {{
    const matches = [];
    function walk(root) {{
      for (const element of root.querySelectorAll("*")) {{
        if (element.localName === "ha-selector-text") {{
          matches.push(element);
        }}
        if (element.shadowRoot) {{
          walk(element.shadowRoot);
        }}
      }}
    }}
    walk(document);
    const element = matches[index];
    if (!element) {{
      throw new Error(`Missing text selector host ${{index}}`);
    }}
    const targets = [element];
    if (element.getRootNode().host) {{
      targets.push(element.getRootNode().host);
    }}
    for (const target of targets) {{
      target.value = value;
      target.dispatchEvent(new CustomEvent("value-changed", {{
        bubbles: true,
        composed: true,
        detail: {{ value }},
      }}));
    }}
  }}, [selectorIndex, String(value)]);
  await page.keyboard.press("Tab");
  await page.waitForTimeout(500);
}}

async function clickDialogOk() {{
  const dialogs = page.getByRole("dialog");
  for (let index = await dialogs.count() - 1; index >= 0; index -= 1) {{
    const dialog = dialogs.nth(index);
    if (await dialog.isVisible().catch(() => false)) {{
      const okButton = dialog.getByRole("button", {{ name: "OK", exact: true }});
      if (await okButton.count()) {{
        const button = okButton.first();
        if (await button.isVisible().catch(() => false)) {{
          await button.click();
          return;
        }}
      }}
    }}
  }}
  const buttons = page.getByRole("button", {{ name: "OK", exact: true }});
  for (let index = await buttons.count() - 1; index >= 0; index -= 1) {{
    const button = buttons.nth(index);
    if (await button.isVisible().catch(() => false)) {{
      await button.click();
      return;
    }}
  }}
  throw new Error("No visible OK button found.");
}}

async function setTimeInput(selectorIndex, hours, minutes) {{
  const selector = page.locator("ha-selector-time").nth(selectorIndex);
  for (const [name, value] of [["hours", hours], ["minutes", minutes]]) {{
    const input = selector.locator(`input[name='${{name}}']`);
    await input.fill(value);
    await input.dispatchEvent("input");
    await input.dispatchEvent("change");
  }}
  await selector.evaluate((element, value) => {{
    const targets = [element];
    if (element.getRootNode().host) {{
      targets.push(element.getRootNode().host);
    }}
    for (const target of targets) {{
      target.value = value;
      target.dispatchEvent(new CustomEvent("value-changed", {{
        bubbles: true,
        composed: true,
        detail: {{ value }},
      }}));
    }}
  }}, `${{hours}}:${{minutes}}:00`);
}}

async function submitAndStay() {{
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
  await page.getByText("Regulation Profile", {{ exact: true }}).waitFor({{ timeout: 10000 }});
}}

async function chooseProfileAction(action, label) {{
  await selectNativeOption(0, action, label);
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
}}

async function chooseProfileIndex(index) {{
  const profileLabels = [
    "climate.virtual_climate_office",
    "climate.virtual_climate_living_room",
  ];
  await page.getByText(profileLabels[index], {{ exact: true }}).click();
  await page.getByRole("button", {{ name: "OK", exact: true }}).click();
}}

await ensureLoggedIn();
await openRegulationProfile();
await chooseProfileAction("remove", "Remove profile");
await chooseProfileIndex(1);
await expectText("Regulation Profiles");
await chooseProfileAction("add", "Add profile");

for (const text of [
  "Window contact",
  "Open-window action",
]) {{
  await expectText(text);
}}
await revealText("Open-window delay");
await scrollDialog(-900, 2);

await clearEntitySelector(0);
await submitAndStay();
await expectText("Select exactly one primary climate entity.");

await selectEntity(0, "Primary climate entity", "No Area Fixture");
await submitAndStay();
await expectText("Assign the primary climate entity to a Home Assistant area first.");

await clearEntitySelector(0);
await selectEntity(0, "Primary climate entity", "Living Room");
await setTimeInput(0, "06", "00");
await setTimeInput(1, "06", "00");
await submitAndStay();
await expectText("Choose different start and end times for the daily home schedule.");

await setTimeInput(1, "22", "00");
await selectEntity(2, "Window contact", "Virtual Window Living Room");
await setNumberInput(0, "0");
await setNumberInput(1, "20");
await selectNativeOption(1, "absolute", "Absolute temperature");
await setNumberInput(2, "17");
await selectNativeOption(0, "minimum_temperature", "Use minimum temperature");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Regulation Profiles");

await chooseProfileAction("edit", "Edit profile");
await chooseProfileIndex(1);
await expectText("Regulation Profile");
await setNumberInput(1, "18.5");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Regulation Profiles");

await chooseProfileAction("remove", "Remove profile");
await chooseProfileIndex(1);
await expectText("Regulation Profiles");

await chooseProfileAction("add", "Add profile");
await selectEntity(0, "Primary climate entity", "Living Room");
await setNumberInput(0, "0");
await setNumberInput(1, "19");
await selectNativeOption(1, "absolute", "Absolute temperature");
await setNumberInput(2, "16");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Regulation Profiles");

await chooseProfileAction("finish", "Finish");
await expectText("Optionen wurden erfolgreich gespeichert.");
await page.getByRole("button", {{ name: /Fertig|Done|Finish/ }}).click();
await page.getByRole("button", {{ name: /Fertig|Done|Finish/ }}).waitFor({{
  timeout: 10000,
  state: "detached",
}});
}}""".strip()


def _run_epic_1(
    *,
    base_url: str,
    skip_gui: bool,
    artifact_dir: Path,
    install_version: str | None,
) -> None:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AcceptanceError(f"{TOKEN_ENV_VAR} must be set.")

    env = os.environ.copy()
    base_smoke = [
        sys.executable,
        "scripts/ha_smoke_test.py",
        "--expect-area-override-services",
        "--set-initial-mode",
        "home",
        "--expect-select-friendly-name",
        "Climate Relay Presence Control",
        "--expect-effective-presence",
        "home",
        "--expect-unknown-state-handling",
        "away",
        "--expect-simulation-mode",
        "on",
        "--expect-fallback-temperature",
        "20.0",
        "--base-url",
        base_url,
    ]
    override_smoke = [
        *base_smoke,
        "--expect-room-count",
        "1",
        "--set-room-override-area-id",
        "auto",
        "--set-room-override-temperature",
        "22.5",
        "--set-room-override-duration-minutes",
        "45",
        "--expect-room-override-ends",
    ]

    steps = [
        (
            [
                sys.executable,
                "scripts/ha_prepare_test_instance.py",
                "--base-url",
                base_url,
                "--install-version",
                f"update.climaterelaycore_update={install_version or EPIC_1_ACCEPTANCE_VERSION}",
            ],
            "Prepare HA test instance",
        ),
        (base_smoke, "Run authenticated HA base smoke test"),
        (
            [
                sys.executable,
                "scripts/ha_prepare_no_area_fixture.py",
                "--base-url",
                base_url,
            ],
            "Prepare dedicated no-area fixture",
        ),
    ]
    for command, description in steps:
        _run_command(command, env=env, description=description)

    print("[acceptance] Prepare Epic 1 regulation profile")
    _prepare_epic_1_profile(base_url=base_url, token=token)

    if skip_gui:
        _run_command(
            override_smoke,
            env=env,
            description="Run authenticated HA manual override smoke test",
        )
        return

    pw_env = _playwright_env()
    pwcli = pw_env["PWCLI"]
    session = f"e1{os.getpid()}"
    try:
        _run_command(
            [pwcli, f"-s={session}", "open", base_url],
            env=pw_env,
            description="Open Playwright browser session",
        )
        _run_command(
            [pwcli, f"-s={session}", "run-code", _gui_epic_1_validation_code(base_url)],
            env=pw_env,
            description="Run Epic 1 validation GUI regression",
        )
        _run_command(
            [pwcli, f"-s={session}", "run-code", _gui_epic_1_profile_save_code(base_url)],
            env=pw_env,
            description="Run Epic 1 profile-save GUI regression",
        )
        _run_command(
            override_smoke,
            env=env,
            description="Run authenticated HA manual override smoke test",
        )
    except AcceptanceError:
        _capture_gui_artifact(
            pwcli=pwcli,
            session=session,
            env=pw_env,
            artifact_dir=artifact_dir,
            name="epic-1",
        )
        raise
    finally:
        subprocess.run(
            [pwcli, f"-s={session}", "close"],
            env=pw_env,
            check=False,
        )


def _run_epic_2(
    *,
    base_url: str,
    skip_gui: bool,
    artifact_dir: Path,
    install_version: str | None,
) -> None:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AcceptanceError(f"{TOKEN_ENV_VAR} must be set.")

    env = os.environ.copy()
    steps = [
        (
            [
                sys.executable,
                "scripts/ha_prepare_test_instance.py",
                "--base-url",
                base_url,
                "--install-version",
                f"update.climaterelaycore_update={install_version or EPIC_2_ACCEPTANCE_VERSION}",
            ],
            "Prepare HA test instance",
        ),
        (
            [
                sys.executable,
                "scripts/ha_smoke_test.py",
                "--expect-area-override-services",
                "--set-initial-mode",
                "home",
                "--expect-select-friendly-name",
                "Climate Relay Presence Control",
                "--expect-effective-presence",
                "home",
                "--expect-unknown-state-handling",
                "away",
                "--expect-simulation-mode",
                "on",
                "--expect-fallback-temperature",
                "20.0",
                "--base-url",
                base_url,
            ],
            "Run authenticated HA base smoke test",
        ),
        (
            [
                sys.executable,
                "scripts/ha_prepare_no_area_fixture.py",
                "--base-url",
                base_url,
            ],
            "Prepare dedicated no-area fixture",
        ),
    ]
    for command, description in steps:
        _run_command(command, env=env, description=description)

    window_friendly_names = {
        "binary_sensor.virtual_window_office": "Virtual Window Office",
        "binary_sensor.virtual_window_living_room": "Virtual Window Living Room",
    }
    for window_entity_id in EPIC_2_WINDOW_ENTITIES:
        _set_entity_state(
            base_url=base_url,
            token=token,
            entity_id=window_entity_id,
            state="off",
            attributes={
                "device_class": "window",
                "friendly_name": window_friendly_names[window_entity_id],
            },
        )
    print("[acceptance] Prepare Epic 2 window automation profile through API")
    _prepare_epic_2_profile(base_url=base_url, token=token)
    if not skip_gui:
        pw_env = _playwright_env()
        pwcli = pw_env["PWCLI"]
        session = f"e2{os.getpid()}"
        try:
            _run_command(
                [pwcli, f"-s={session}", "open", base_url],
                env=pw_env,
                description="Open Playwright browser session",
            )
            _run_command(
                [pwcli, f"-s={session}", "run-code", _gui_epic_2_options_flow_code(base_url)],
                env=pw_env,
                description="Run Epic 2 full options-flow GUI regression",
            )
        except AcceptanceError:
            _capture_gui_artifact(
                pwcli=pwcli,
                session=session,
                env=pw_env,
                artifact_dir=artifact_dir,
                name="epic-2",
            )
            raise
        finally:
            subprocess.run(
                [pwcli, f"-s={session}", "close"],
                env=pw_env,
                check=False,
            )

    room_entities = _find_epic_2_room_entities(base_url=base_url, token=token)
    office_room_entity_id = room_entities[EPIC_2_PRIMARY_CLIMATES[0]]
    living_room_entity_id = room_entities[EPIC_2_PRIMARY_CLIMATES[1]]

    print("[acceptance] Set area override for one configured profile only")
    _call_area_override(
        base_url=base_url,
        token=token,
        area_id=EPIC_2_PRIMARY_CLIMATES[0],
        target_temperature=22.0,
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=office_room_entity_id,
        expected_context="manual_override",
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=living_room_entity_id,
        expected_context="schedule",
    )

    print("[acceptance] Clear area override for one configured profile only")
    _clear_area_override(
        base_url=base_url,
        token=token,
        area_id=EPIC_2_PRIMARY_CLIMATES[0],
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=office_room_entity_id,
        expected_context="schedule",
    )

    print("[acceptance] Mark required primary climate unavailable and expect fallback")
    office_primary_available_state = {
        "friendly_name": "Virtual Climate Office",
        "hvac_modes": ["off", "heat"],
        "temperature": 20.0,
        "current_temperature": 19.5,
        "min_temp": 5.0,
    }
    try:
        _set_entity_state(
            base_url=base_url,
            token=token,
            entity_id=EPIC_2_PRIMARY_CLIMATES[0],
            state="unavailable",
            attributes=office_primary_available_state,
        )
        _wait_for_room_attributes(
            base_url=base_url,
            token=token,
            entity_id=office_room_entity_id,
            expected_attributes={
                "active_control_context": "fallback",
                "degradation_status": "required_component_fallback",
                "temperature": 20.0,
            },
        )
        _wait_for_room_context(
            base_url=base_url,
            token=token,
            entity_id=living_room_entity_id,
            expected_context="schedule",
        )
    finally:
        print("[acceptance] Restore required primary climate")
        _set_entity_state(
            base_url=base_url,
            token=token,
            entity_id=EPIC_2_PRIMARY_CLIMATES[0],
            state="heat",
            attributes=office_primary_available_state,
        )

    print("[acceptance] Expect normal reevaluation after required primary climate restore")
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=office_room_entity_id,
        expected_context="schedule",
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=living_room_entity_id,
        expected_context="schedule",
    )

    print("[acceptance] Open configured window contact and expect window override")
    _set_entity_state(
        base_url=base_url,
        token=token,
        entity_id=EPIC_2_WINDOW_ENTITIES[0],
        state="on",
        attributes={"device_class": "window", "friendly_name": "Virtual Window Office"},
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=office_room_entity_id,
        expected_context="window_override",
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=living_room_entity_id,
        expected_context="schedule",
    )

    print("[acceptance] Close configured window contact and expect normal reevaluation")
    _set_entity_state(
        base_url=base_url,
        token=token,
        entity_id=EPIC_2_WINDOW_ENTITIES[0],
        state="off",
        attributes={"device_class": "window", "friendly_name": "Virtual Window Office"},
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=office_room_entity_id,
        expected_context="schedule",
    )


def _run_epic_3(
    *,
    base_url: str,
    skip_gui: bool,
    artifact_dir: Path,
    install_version: str | None,
) -> None:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AcceptanceError(f"{TOKEN_ENV_VAR} must be set.")

    env = os.environ.copy()
    prepare_command = [
        sys.executable,
        "scripts/ha_prepare_test_instance.py",
        "--base-url",
        base_url,
    ]
    if install_version is not None:
        prepare_command.extend(
            [
                "--install-version",
                f"update.climaterelaycore_update={install_version}",
            ]
        )
    steps = [
        (prepare_command, "Prepare HA test instance"),
        (
            [
                sys.executable,
                "scripts/ha_smoke_test.py",
                "--expect-area-override-services",
                "--set-initial-mode",
                "home",
                "--expect-select-friendly-name",
                "Climate Relay Presence Control",
                "--expect-effective-presence",
                "home",
                "--expect-unknown-state-handling",
                "away",
                "--expect-simulation-mode",
                "on",
                "--expect-fallback-temperature",
                "20.0",
                "--base-url",
                base_url,
            ],
            "Run authenticated HA base smoke test",
        ),
    ]
    for command, description in steps:
        _run_command(command, env=env, description=description)

    print("[acceptance] Prepare Increment 3 schedule-editing profile through API")
    _prepare_epic_3_profile(base_url=base_url, token=token)
    room_entity_id = _find_room_entity_for_primary(
        base_url=base_url,
        token=token,
        primary_climate_entity_id=EPIC_2_PRIMARY_CLIMATES[0],
    )
    _wait_for_room_attributes(
        base_url=base_url,
        token=token,
        entity_id=room_entity_id,
        expected_attributes={
            "schedule_home_start": "06:00:00",
            "schedule_home_end": "22:00:00",
        },
    )

    if skip_gui:
        return

    _run_command(
        ["npm", "run", "build"],
        env=env,
        description="Build custom card bundle for GUI acceptance",
        cwd=Path("frontend"),
    )
    card_bundle_path = (Path.cwd() / "frontend" / "dist" / "climate-relay-card.js").resolve()
    pw_env = _playwright_env()
    pwcli = pw_env["PWCLI"]
    session = f"e3{os.getpid()}"
    try:
        _run_command(
            [pwcli, f"-s={session}", "open", base_url],
            env=pw_env,
            description="Open Playwright browser session",
        )
        _run_command(
            [
                pwcli,
                f"-s={session}",
                "run-code",
                _gui_epic_3_schedule_card_code(base_url, card_bundle_path),
            ],
            env=pw_env,
            description="Run Increment 3 schedule-editing custom-card GUI regression",
        )
    except AcceptanceError:
        _capture_gui_artifact(
            pwcli=pwcli,
            session=session,
            env=pw_env,
            artifact_dir=artifact_dir,
            name="epic-3-schedule",
        )
        raise
    finally:
        subprocess.run(
            [pwcli, f"-s={session}", "close"],
            env=pw_env,
            check=False,
        )

    _wait_for_room_attributes(
        base_url=base_url,
        token=token,
        entity_id=room_entity_id,
        expected_attributes={
            "schedule_home_start": "07:15:00",
            "schedule_home_end": "21:45:00",
        },
    )


def main() -> int:
    _load_local_env_file()
    args = _build_parser().parse_args()
    artifact_dir = Path(args.artifact_dir)
    if args.epic == "1":
        _run_epic_1(
            base_url=args.base_url,
            skip_gui=args.skip_gui,
            artifact_dir=artifact_dir,
            install_version=args.install_version,
        )
    if args.epic == "2":
        _run_epic_2(
            base_url=args.base_url,
            skip_gui=args.skip_gui,
            artifact_dir=artifact_dir,
            install_version=args.install_version,
        )
    if args.epic == "3":
        _run_epic_3(
            base_url=args.base_url,
            skip_gui=args.skip_gui,
            artifact_dir=artifact_dir,
            install_version=args.install_version,
        )
    print(f"[acceptance] Epic {args.epic} completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
