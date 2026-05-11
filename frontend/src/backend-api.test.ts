import { describe, expect, it, vi } from "vitest";

import {
  ACTIVATE_ROOM_COMMAND,
  ROOM_CANDIDATES_COMMAND,
  UPDATE_ROOM_SCHEDULE_COMMAND,
  activateRoom,
  fetchRoomCandidates,
  updateRoomSchedule,
} from "./backend-api";
import type { HomeAssistantLike } from "./types";

describe("backend-api", () => {
  it("requests room candidates over the Home Assistant WebSocket connection", async () => {
    const hass = mockHass({ candidates: [] });

    await fetchRoomCandidates(hass);

    expect(hass.connection.sendMessagePromise).toHaveBeenCalledWith({
      type: ROOM_CANDIDATES_COMMAND,
    });
  });

  it("requests one room activation over the Home Assistant WebSocket connection", async () => {
    const hass = mockHass({ activated: true });

    await activateRoom(hass, "climate.office");

    expect(hass.connection.sendMessagePromise).toHaveBeenCalledWith({
      type: ACTIVATE_ROOM_COMMAND,
      candidate_id: "climate.office",
    });
  });

  it("requests one room schedule update over the Home Assistant WebSocket connection", async () => {
    const hass = mockHass({ updated: true });

    await updateRoomSchedule(hass, "climate.office", {
      schedule_home_start: "07:00",
      schedule_home_end: "21:30",
    });

    expect(hass.connection.sendMessagePromise).toHaveBeenCalledWith({
      type: UPDATE_ROOM_SCHEDULE_COMMAND,
      primary_climate_entity_id: "climate.office",
      schedule_home_start: "07:00",
      schedule_home_end: "21:30",
    });
  });
});

function mockHass(result: unknown): HomeAssistantLike {
  return {
    states: {},
    connection: {
      sendMessagePromise: vi.fn().mockResolvedValue(result),
    },
  };
}
