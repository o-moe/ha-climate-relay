#!/usr/bin/env python3
"""Run the documented Home Assistant acceptance workflow for one iteration."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE_URL = "http://haos-test.local:8123"
TOKEN_ENV_VAR = "HOME_ASSISTANT_TOKEN"
ITERATION_1_2_VERSION = "v0.1.0-alpha.8"
ITERATION_1_3_VERSION = "v0.1.0-beta.3"
LOCAL_ENV_FILE = Path(".env.local")


class AcceptanceError(RuntimeError):
    """Raised when one acceptance step fails."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the repository-local HA acceptance workflow for one documented iteration."
        )
    )
    parser.add_argument(
        "--iteration",
        required=True,
        choices=("1.2", "1.3"),
        help="Iteration acceptance workflow to run.",
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


def _gui_regression_code(base_url: str) -> str:
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
  await page.getByText(text, {{ exact: true }}).waitFor({{ timeout: 10000 }});
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


def _gui_iteration_1_3_code(base_url: str) -> str:
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

await ensureLoggedIn();
await openRegulationProfile();
await page.getByText("Home schedule start", {{ exact: true }}).waitFor({{ timeout: 10000 }});
await page.getByText("Home schedule end", {{ exact: true }}).waitFor({{ timeout: 10000 }});
const timeInputs = page.locator("ha-selector-time input");
await timeInputs.nth(0).fill("06:00");
await timeInputs.nth(1).fill("06:00");
await page.getByRole("button", {{ name: "OK", exact: true }}).click();
await page.getByText(
  "Choose different start and end times for the daily home schedule.",
  {{ exact: true }}
).waitFor({{ timeout: 10000 }});
}}""".strip()


def _run_iteration_1_2(*, base_url: str, skip_gui: bool) -> None:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AcceptanceError(f"{TOKEN_ENV_VAR} must be set.")

    env = os.environ.copy()
    strict_smoke = [
        sys.executable,
        "scripts/ha_smoke_test.py",
        "--expect-select-friendly-name",
        "Climate Relay Presence Control",
        "--expect-effective-presence",
        "away",
        "--expect-unknown-state-handling",
        "away",
        "--expect-simulation-mode",
        "on",
        "--expect-fallback-temperature",
        "20.0",
        "--base-url",
        base_url,
    ]

    steps = [
        (
            [
                sys.executable,
                "scripts/ha_prepare_test_instance.py",
                "--base-url",
                base_url,
                "--install-version",
                f"update.climaterelaycore_update={ITERATION_1_2_VERSION}",
            ],
            "Prepare HA test instance",
        ),
        (strict_smoke, "Run authenticated HA smoke test"),
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

    if skip_gui:
        return

    pw_env = _playwright_env()
    pwcli = pw_env["PWCLI"]
    session = f"i12{os.getpid()}"
    try:
        _run_command(
            [pwcli, f"-s={session}", "open", base_url],
            env=pw_env,
            description="Open Playwright browser session",
        )
        _run_command(
            [pwcli, f"-s={session}", "run-code", _gui_regression_code(base_url)],
            env=pw_env,
            description="Run iteration 1.2 GUI regression",
        )
    finally:
        subprocess.run(
            [pwcli, f"-s={session}", "close"],
            env=pw_env,
            check=False,
        )


def _run_iteration_1_3(*, base_url: str, skip_gui: bool) -> None:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise AcceptanceError(f"{TOKEN_ENV_VAR} must be set.")

    env = os.environ.copy()
    strict_smoke = [
        sys.executable,
        "scripts/ha_smoke_test.py",
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
        "--expect-room-count",
        "1",
        "--expect-room-next-change",
        "--base-url",
        base_url,
    ]

    steps = [
        (
            [
                sys.executable,
                "scripts/ha_prepare_test_instance.py",
                "--base-url",
                base_url,
                "--install-version",
                f"update.climaterelaycore_update={ITERATION_1_3_VERSION}",
            ],
            "Prepare HA test instance",
        ),
        (strict_smoke, "Run authenticated HA schedule smoke test"),
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

    if skip_gui:
        return

    pw_env = _playwright_env()
    pwcli = pw_env["PWCLI"]
    session = f"i13{os.getpid()}"
    try:
        _run_command(
            [pwcli, f"-s={session}", "open", base_url],
            env=pw_env,
            description="Open Playwright browser session",
        )
        _run_command(
            [pwcli, f"-s={session}", "run-code", _gui_iteration_1_3_code(base_url)],
            env=pw_env,
            description="Run iteration 1.3 GUI regression",
        )
    finally:
        subprocess.run(
            [pwcli, f"-s={session}", "close"],
            env=pw_env,
            check=False,
        )


def main() -> int:
    _load_local_env_file()
    args = _build_parser().parse_args()
    if args.iteration == "1.2":
        _run_iteration_1_2(base_url=args.base_url, skip_gui=args.skip_gui)
    elif args.iteration == "1.3":
        _run_iteration_1_3(base_url=args.base_url, skip_gui=args.skip_gui)
    else:
        raise AcceptanceError(f"Unsupported iteration {args.iteration!r}.")
    print(f"[acceptance] Iteration {args.iteration} completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
