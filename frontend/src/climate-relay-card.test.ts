import { describe, expect, it, vi } from "vitest";

import "./climate-relay-card";
import type { ClimateRelayCard } from "./climate-relay-card";
import type { HomeAssistantLike } from "./types";

describe("climate-relay-card", () => {
  it("renders loading state without hass", async () => {
    const element = createCard();

    await element.updateComplete;

    expect(textContent(element)).toContain("Loading Climate Relay");
  });

  it("renders empty state with a mocked Home Assistant object", async () => {
    const element = createCard();
    element.hass = { states: {} };

    await element.updateComplete;

    expect(textContent(element)).toContain("No Climate Relay entities found");
  });

  it("renders one room tile from backend-owned Home Assistant state", async () => {
    const element = createCard();
    element.hass = mockHass();

    await element.updateComplete;

    const rendered = textContent(element);
    expect(rendered).toContain("Office");
    expect(rendered).toContain("20.4 °C");
    expect(rendered).toContain("21.5 °C");
    expect(rendered).toContain("manual_override");
    expect(rendered).toContain("optional_sensor_unavailable");
    expect(rendered).toContain("2026-05-10T22:00:00+02:00");
    expect(rendered).toContain("2026-05-10T19:30:00+02:00");
  });

  it("orchestrates existing backend override services without owning rule logic", async () => {
    const callService = vi.fn();
    const element = createCard();
    element.hass = mockHass(callService);

    await element.updateComplete;
    const buttons = element.shadowRoot?.querySelectorAll("button");
    buttons?.[0]?.dispatchEvent(new MouseEvent("click"));
    buttons?.[1]?.dispatchEvent(new MouseEvent("click"));

    expect(callService).toHaveBeenCalledWith("climate_relay_core", "set_area_override", {
      area_id: "climate.office",
      target_temperature: 21.5,
      termination_type: "duration",
      duration_minutes: 60,
    });
    expect(callService).toHaveBeenCalledWith("climate_relay_core", "clear_area_override", {
      area_id: "climate.office",
    });
  });
});

function createCard(): ClimateRelayCard {
  const element = document.createElement("climate-relay-card") as ClimateRelayCard;
  element.setConfig({ title: "Climate Relay" });
  document.body.append(element);
  return element;
}

function mockHass(callService = vi.fn()): HomeAssistantLike {
  return {
    callService,
    states: {
      "climate.climate_relay_office": {
        entity_id: "climate.climate_relay_office",
        state: "heat",
        attributes: {
          friendly_name: "Office",
          primary_climate_entity_id: "climate.office",
          current_temperature: 20.4,
          temperature: 21.5,
          active_control_context: "manual_override",
          degradation_status: "optional_sensor_unavailable",
          next_change_at: "2026-05-10T22:00:00+02:00",
          override_ends_at: "2026-05-10T19:30:00+02:00",
        },
      },
    },
  };
}

function textContent(element: Element): string {
  return element.shadowRoot?.textContent?.replace(/\s+/g, " ").trim() ?? "";
}
