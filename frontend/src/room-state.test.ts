import { describe, expect, it } from "vitest";

import { extractClimateRelayRooms } from "./room-state";
import type { HomeAssistantState } from "./types";

describe("extractClimateRelayRooms", () => {
  it("returns an empty list when no Climate Relay room entity is present", () => {
    const states: Record<string, HomeAssistantState> = {
      "climate.raw_thermostat": {
        entity_id: "climate.raw_thermostat",
        state: "heat",
        attributes: {
          friendly_name: "Raw Thermostat",
          temperature: 21,
        },
      },
    };

    expect(extractClimateRelayRooms(states)).toEqual([]);
  });

  it("extracts visible room tile state from backend-owned climate attributes", () => {
    const states: Record<string, HomeAssistantState> = {
      "climate.climate_relay_office": {
        entity_id: "climate.climate_relay_office",
        state: "heat",
        attributes: {
          friendly_name: "Office",
          primary_climate_entity_id: "climate.office",
          current_temperature: 20.2,
          temperature: 21,
          active_control_context: "schedule",
          degradation_status: "optional_sensor_unavailable",
          next_change_at: "2026-05-10T22:00:00+02:00",
          override_ends_at: "2026-05-10T18:00:00+02:00",
          schedule_home_start: "06:00:00",
          schedule_home_end: "22:00:00",
        },
      },
    };

    expect(extractClimateRelayRooms(states)).toEqual([
      {
        entityId: "climate.climate_relay_office",
        displayName: "Office",
        primaryClimateEntityId: "climate.office",
        currentTemperature: 20.2,
        targetTemperature: 21,
        activeControlContext: "schedule",
        degradationStatus: "optional_sensor_unavailable",
        nextChangeAt: "2026-05-10T22:00:00+02:00",
        overrideEndsAt: "2026-05-10T18:00:00+02:00",
        scheduleHomeStart: "06:00:00",
        scheduleHomeEnd: "22:00:00",
      },
    ]);
  });
});
