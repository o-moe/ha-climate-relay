import type { ClimateRelayRoomTile, HomeAssistantState } from "./types";

const PRIMARY_CLIMATE_ATTRIBUTE = "primary_climate_entity_id";

export function extractClimateRelayRooms(
  states: Record<string, HomeAssistantState>,
): ClimateRelayRoomTile[] {
  return Object.values(states)
    .filter(isClimateRelayRoomState)
    .map(toRoomTile)
    .sort((left, right) => left.displayName.localeCompare(right.displayName));
}

function isClimateRelayRoomState(state: HomeAssistantState): boolean {
  return (
    state.entity_id.startsWith("climate.") &&
    typeof state.attributes[PRIMARY_CLIMATE_ATTRIBUTE] === "string"
  );
}

function toRoomTile(state: HomeAssistantState): ClimateRelayRoomTile {
  return {
    entityId: state.entity_id,
    displayName: stringAttribute(state, "friendly_name") ?? state.entity_id,
    primaryClimateEntityId: stringAttribute(state, PRIMARY_CLIMATE_ATTRIBUTE) ?? "",
    currentTemperature: numberAttribute(state, "current_temperature"),
    targetTemperature: numberAttribute(state, "temperature"),
    activeControlContext: stringAttribute(state, "active_control_context"),
    degradationStatus: stringAttribute(state, "degradation_status"),
    nextChangeAt: stringAttribute(state, "next_change_at"),
    overrideEndsAt: stringAttribute(state, "override_ends_at"),
  };
}

function stringAttribute(state: HomeAssistantState, key: string): string | undefined {
  const value = state.attributes[key];
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function numberAttribute(state: HomeAssistantState, key: string): number | undefined {
  const value = state.attributes[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}
