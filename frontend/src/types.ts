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
