import { describe, expect, it, vi } from "vitest";

import {
  ACTIVATE_ROOM_COMMAND,
  ROOM_CANDIDATES_COMMAND,
  activateRoom,
  fetchRoomCandidates,
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
});

function mockHass(result: unknown): HomeAssistantLike {
  return {
    states: {},
    connection: {
      sendMessagePromise: vi.fn().mockResolvedValue(result),
    },
  };
}
