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
EPIC_2_ACCEPTANCE_VERSION = "v0.2.0-alpha.7"
LOCAL_ENV_FILE = Path(".env.local")
DEFAULT_ARTIFACT_DIR = Path("artifacts") / "acceptance"


class AcceptanceError(RuntimeError):
    """Raised when one acceptance step fails."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the repository-local HA acceptance workflow for one documented epic."
    )
    parser.add_argument(
        "--epic",
        required=True,
        choices=("1", "2"),
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


def _run_command(command: list[str], *, env: dict[str, str], description: str) -> None:
    print(f"[acceptance] {description}")
    print(f"[acceptance] $ {' '.join(shlex.quote(part) for part in command)}")
    result = subprocess.run(
        command,
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
    states = _request_json(base_url=base_url, token=token, path="/api/states")
    if not isinstance(states, list):
        raise AcceptanceError("Expected /api/states to return a list.")
    candidates = [
        state
        for state in states
        if isinstance(state, dict)
        and str(state.get("entity_id", "")).startswith("climate.")
        and state.get("attributes", {}).get("primary_climate_entity_id")
        == "climate.virtual_climate_office"
    ]
    if len(candidates) != 1:
        raise AcceptanceError(
            "Expected exactly one Epic 2 room climate entity for "
            f"climate.virtual_climate_office, found {len(candidates)}."
        )
    return str(candidates[0]["entity_id"])


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
    if flow.get("step_id") != "room":
        raise AcceptanceError(f"Expected room options step, got {flow!r}.")
    result = _request_json(
        base_url=base_url,
        token=token,
        path=f"/api/config/config_entries/options/flow/{flow_id}",
        method="POST",
        payload={
            "primary_climate_entity_id": "climate.virtual_climate_office",
            "window_entity_id": "binary_sensor.virtual_window_office",
            "window_action_type": "minimum_temperature",
            "window_custom_temperature": None,
            "window_open_delay_seconds": 0,
            "home_target_temperature": 20.0,
            "away_target_type": "absolute",
            "away_target_temperature": 17.0,
            "schedule_home_start": "06:00:00",
            "schedule_home_end": "22:00:00",
        },
    )
    if result.get("type") != "create_entry":
        raise AcceptanceError(f"Expected profile options to save, got {result!r}.")
    time.sleep(5.0)


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
  await page.getByText("Regulation Profile", {{ exact: true }}).waitFor({{ timeout: 10000 }});
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

await ensureLoggedIn();
await openRegulationProfile();
await clearPrimaryClimate();
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Select exactly one primary climate entity.");
await selectPrimaryClimate("No Area Fixture");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await expectText("Assign the primary climate entity to a Home Assistant area first.");
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
  await page.getByText("Regulation Profile", {{ exact: true }}).waitFor({{ timeout: 10000 }});
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

await ensureLoggedIn();
await openRegulationProfile();
await selectPrimaryClimate("Office");
const timeSelectors = page.locator("ha-selector-time");
await timeSelectors.nth(0).waitFor({{ timeout: 10000 }});
await timeSelectors.nth(1).waitFor({{ timeout: 10000 }});
await setTimeInput(0, "06", "00");
await setTimeInput(1, "22", "00");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
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
  await page.getByText("Regulation Profile", {{ exact: true }}).waitFor({{ timeout: 10000 }});
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
  const selector = page.locator("ha-selector-select").nth(selectorIndex);
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
  await selector.locator("mwc-select, ha-select").first().click();
  await page.getByText(optionLabel, {{ exact: true }}).click();
}}

async function setNumberInput(selectorIndex, value) {{
  const selector = page.locator("ha-selector-number").nth(selectorIndex);
  const input = selector.locator("input").first();
  await input.fill(String(value));
  await input.dispatchEvent("input");
  await input.dispatchEvent("change");
  await selector.evaluate((element, value) => {{
    const numericValue = Number(value);
    const finalValue = Number.isNaN(numericValue) ? value : numericValue;
    const targets = [element];
    if (element.getRootNode().host) {{
      targets.push(element.getRootNode().host);
    }}
    for (const target of targets) {{
      target.value = finalValue;
      target.dispatchEvent(new CustomEvent("value-changed", {{
        bubbles: true,
        composed: true,
        detail: {{ value: finalValue }},
      }}));
    }}
  }}, String(value));
}}

async function clearNumberInput(selectorIndex) {{
  const selector = page.locator("ha-selector-number").nth(selectorIndex);
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

await ensureLoggedIn();
await openRegulationProfile();

for (const text of [
  "Window contact",
  "Open-window action",
  "Open-window custom temperature",
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
await selectEntity(0, "Primary climate entity", "Office");
await setTimeInput(0, "06", "00");
await setTimeInput(1, "06", "00");
await submitAndStay();
await expectText("Choose different start and end times for the daily home schedule.");

await setTimeInput(1, "22", "00");
await selectNativeOption(0, "custom_temperature", "Use custom temperature");
await clearNumberInput(0);
await submitAndStay();
await expectAnyText([
  "Set a custom temperature or choose a different open-window action.",
  "expected float",
]);

await selectEntity(2, "Window contact", "Virtual Window Office");
await setNumberInput(0, "12");
await setNumberInput(1, "0");
await setNumberInput(2, "20");
await selectNativeOption(1, "absolute", "Absolute temperature");
await setNumberInput(3, "17");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
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

    _set_entity_state(
        base_url=base_url,
        token=token,
        entity_id="binary_sensor.virtual_window_office",
        state="off",
        attributes={"device_class": "window", "friendly_name": "Virtual Window Office"},
    )
    if skip_gui:
        print("[acceptance] Prepare Epic 2 window automation profile through API")
        _prepare_epic_2_profile(base_url=base_url, token=token)
    else:
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

    room_entity_id = _find_epic_2_room_entity(base_url=base_url, token=token)

    print("[acceptance] Open configured window contact and expect window override")
    _set_entity_state(
        base_url=base_url,
        token=token,
        entity_id="binary_sensor.virtual_window_office",
        state="on",
        attributes={"device_class": "window", "friendly_name": "Virtual Window Office"},
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=room_entity_id,
        expected_context="window_override",
    )

    print("[acceptance] Close configured window contact and expect normal reevaluation")
    _set_entity_state(
        base_url=base_url,
        token=token,
        entity_id="binary_sensor.virtual_window_office",
        state="off",
        attributes={"device_class": "window", "friendly_name": "Virtual Window Office"},
    )
    _wait_for_room_context(
        base_url=base_url,
        token=token,
        entity_id=room_entity_id,
        expected_context="schedule",
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
    print(f"[acceptance] Epic {args.epic} completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
