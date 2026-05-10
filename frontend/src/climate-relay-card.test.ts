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
    element.hass = { ...mockHass(), states: {} };

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
    expect(rendered).toContain("Override 1h");
  });

  it("renders candidate section when backend returns candidates", async () => {
    const sendMessagePromise = vi.fn().mockResolvedValue({
      candidates: [
        {
          candidate_id: "climate.bedroom",
          area_id: "bedroom",
          area_name: "Bedroom",
          primary_climate_entity_id: "climate.bedroom",
          primary_climate_display_name: "Bedroom Thermostat",
          already_active: false,
          unavailable_reason: null,
        },
      ],
    });
    const element = createCard();
    element.hass = mockHass(undefined, sendMessagePromise);

    await waitForUpdates(element);

    const rendered = textContent(element);
    expect(rendered).toContain("Add room");
    expect(rendered).toContain("Bedroom");
    expect(rendered).toContain("Bedroom Thermostat");
    expect(rendered).toContain("Activate");
  });

  it("shows unavailable reason for non-activatable candidate", async () => {
    const sendMessagePromise = vi.fn().mockResolvedValue({
      candidates: [
        {
          candidate_id: "climate.no_area",
          area_id: null,
          area_name: null,
          primary_climate_entity_id: "climate.no_area",
          primary_climate_display_name: "Loose Thermostat",
          already_active: false,
          unavailable_reason: "missing_area",
        },
      ],
    });
    const element = createCard();
    element.hass = { ...mockHass(undefined, sendMessagePromise), states: {} };

    await waitForUpdates(element);

    expect(textContent(element)).toContain("Climate entity has no Home Assistant area.");
  });

  it("calls backend activation operation when user clicks Activate", async () => {
    const sendMessagePromise = vi
      .fn()
      .mockResolvedValueOnce({
        candidates: [
          {
            candidate_id: "climate.bedroom",
            area_id: "bedroom",
            area_name: "Bedroom",
            primary_climate_entity_id: "climate.bedroom",
            primary_climate_display_name: "Bedroom Thermostat",
            already_active: false,
            unavailable_reason: null,
          },
        ],
      })
      .mockResolvedValueOnce({ activated: true })
      .mockResolvedValueOnce({ candidates: [] });
    const element = createCard();
    element.hass = { ...mockHass(undefined, sendMessagePromise), states: {} };

    await waitForUpdates(element);
    const activateButton = Array.from(element.shadowRoot?.querySelectorAll("button") ?? []).find(
      (button) => button.textContent?.includes("Activate"),
    );
    activateButton?.dispatchEvent(new MouseEvent("click"));
    await waitForUpdates(element);

    expect(sendMessagePromise).toHaveBeenCalledWith({
      type: "climate_relay_core/activate_room",
      candidate_id: "climate.bedroom",
    });
    expect(textContent(element)).toContain("Waiting for Home Assistant state to update.");
  });

  it("shows activation error if backend rejects the command", async () => {
    const sendMessagePromise = vi
      .fn()
      .mockResolvedValueOnce({
        candidates: [
          {
            candidate_id: "climate.bedroom",
            area_id: "bedroom",
            area_name: "Bedroom",
            primary_climate_entity_id: "climate.bedroom",
            primary_climate_display_name: "Bedroom Thermostat",
            already_active: false,
            unavailable_reason: null,
          },
        ],
      })
      .mockRejectedValueOnce(new Error("Home Assistant area is already activated."));
    const element = createCard();
    element.hass = { ...mockHass(undefined, sendMessagePromise), states: {} };

    await waitForUpdates(element);
    const activateButton = Array.from(element.shadowRoot?.querySelectorAll("button") ?? []).find(
      (button) => button.textContent?.includes("Activate"),
    );
    activateButton?.dispatchEvent(new MouseEvent("click"));
    await waitForUpdates(element);

    expect(textContent(element)).toContain("Home Assistant area is already activated.");
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

  it("documents that schedule validation stays backend-owned and unimplemented here", async () => {
    const element = createCard();
    element.hass = mockHass();

    await waitForUpdates(element);

    const rendered = textContent(element);
    expect(rendered).toContain("Room activation is available for eligible primary climate candidates");
    expect(rendered).toContain("Schedule editing needs backend-owned schedule validation");
    expect(rendered).toContain("Override 1h remains a temporary fixed-duration scaffold");
  });
});

function createCard(): ClimateRelayCard {
  const element = document.createElement("climate-relay-card") as ClimateRelayCard;
  element.setConfig({ title: "Climate Relay" });
  document.body.append(element);
  return element;
}

function mockHass(
  callService = vi.fn(),
  sendMessagePromise = vi.fn().mockResolvedValue({ candidates: [] }),
): HomeAssistantLike {
  return {
    callService,
    connection: {
      sendMessagePromise,
    },
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

async function waitForUpdates(element: ClimateRelayCard): Promise<void> {
  await element.updateComplete;
  await Promise.resolve();
  await element.updateComplete;
}
