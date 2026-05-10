export type ClimateRelayCardConfig = {
  title?: string;
};

export type HomeAssistantState = {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
};

export type HomeAssistantLike = {
  states: Record<string, HomeAssistantState>;
  connection: {
    sendMessagePromise<T>(message: Record<string, unknown>): Promise<T>;
  };
  callService?: (
    domain: string,
    service: string,
    data?: Record<string, unknown>,
  ) => Promise<unknown> | void;
};

export type ClimateRelayRoomTile = {
  entityId: string;
  displayName: string;
  primaryClimateEntityId: string;
  currentTemperature?: number;
  targetTemperature?: number;
  activeControlContext?: string;
  degradationStatus?: string;
  nextChangeAt?: string;
  overrideEndsAt?: string;
};

export type RoomCandidate = {
  candidate_id: string;
  area_id: string | null;
  area_name: string | null;
  primary_climate_entity_id: string;
  primary_climate_display_name: string | null;
  already_active: boolean;
  unavailable_reason: string | null;
};

export type RoomCandidateDiscoveryResult = {
  candidates: RoomCandidate[];
};

export type ActivateRoomResult = {
  activated: boolean;
  candidate: RoomCandidate;
  primary_climate_entity_id: string;
  rooms_count: number;
};
