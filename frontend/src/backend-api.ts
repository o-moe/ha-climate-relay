import type {
  ActivateRoomResult,
  HomeAssistantLike,
  RoomCandidateDiscoveryResult,
} from "./types";

export const ROOM_CANDIDATES_COMMAND = "climate_relay_core/room_candidates";
export const ACTIVATE_ROOM_COMMAND = "climate_relay_core/activate_room";

export async function fetchRoomCandidates(
  hass: HomeAssistantLike,
): Promise<RoomCandidateDiscoveryResult> {
  return hass.connection.sendMessagePromise<RoomCandidateDiscoveryResult>({
    type: ROOM_CANDIDATES_COMMAND,
  });
}

export async function activateRoom(
  hass: HomeAssistantLike,
  candidateId: string,
): Promise<ActivateRoomResult> {
  return hass.connection.sendMessagePromise<ActivateRoomResult>({
    type: ACTIVATE_ROOM_COMMAND,
    candidate_id: candidateId,
  });
}
