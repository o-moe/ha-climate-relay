import type {
  ActivateRoomResult,
  DailyScheduleWindow,
  HomeAssistantLike,
  RoomCandidateDiscoveryResult,
  UpdateRoomScheduleResult,
} from "./types";

export const ROOM_CANDIDATES_COMMAND = "climate_relay_core/room_candidates";
export const ACTIVATE_ROOM_COMMAND = "climate_relay_core/activate_room";
export const UPDATE_ROOM_SCHEDULE_COMMAND = "climate_relay_core/update_room_schedule";

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

export async function updateRoomSchedule(
  hass: HomeAssistantLike,
  primaryClimateEntityId: string,
  schedule: DailyScheduleWindow,
): Promise<UpdateRoomScheduleResult> {
  return hass.connection.sendMessagePromise<UpdateRoomScheduleResult>({
    type: UPDATE_ROOM_SCHEDULE_COMMAND,
    primary_climate_entity_id: primaryClimateEntityId,
    schedule_home_start: schedule.schedule_home_start,
    schedule_home_end: schedule.schedule_home_end,
  });
}
