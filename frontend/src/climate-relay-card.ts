import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { activateRoom, fetchRoomCandidates, updateRoomSchedule } from "./backend-api";
import { extractClimateRelayRooms } from "./room-state";
import type {
  ClimateRelayCardConfig,
  ClimateRelayRoomTile,
  HomeAssistantLike,
  RoomCandidate,
} from "./types";

@customElement("climate-relay-card")
export class ClimateRelayCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistantLike;
  @state() private _config: ClimateRelayCardConfig = {};
  @state() private _overrideTargets: Record<string, string> = {};
  @state() private _candidates: RoomCandidate[] = [];
  @state() private _candidateError?: string;
  @state() private _candidateLoading = false;
  @state() private _activatingCandidateId?: string;
  @state() private _activationMessage?: string;
  @state() private _scheduleEdits: Record<string, { start: string; end: string }> = {};
  @state() private _scheduleErrors: Record<string, string> = {};
  @state() private _scheduleMessages: Record<string, string> = {};
  @state() private _savingScheduleEntityId?: string;
  private _candidateHass?: HomeAssistantLike;

  public setConfig(config: ClimateRelayCardConfig): void {
    this._config = config ?? {};
  }

  static styles = css`
    :host {
      display: block;
      color: var(--primary-text-color, #1f2933);
      font-family: var(--paper-font-body1_-_font-family, "Segoe UI", sans-serif);
    }

    ha-card {
      background: var(--ha-card-background, #ffffff);
      border: 1px solid var(--divider-color, #d8dee4);
      border-radius: var(--ha-card-border-radius, 8px);
      box-shadow: var(--ha-card-box-shadow, none);
      display: block;
      overflow: hidden;
    }

    .content {
      display: grid;
      gap: 16px;
      padding: 16px;
    }

    h2 {
      font-size: 18px;
      line-height: 1.3;
      margin: 0;
    }

    .status {
      background: var(--secondary-background-color, #f5f7fa);
      border: 1px solid var(--divider-color, #d8dee4);
      border-radius: 6px;
      padding: 12px;
    }

    .rooms {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }

    .room-tile,
    .candidate {
      border: 1px solid var(--divider-color, #d8dee4);
      border-radius: 8px;
      display: grid;
      gap: 12px;
      min-width: 0;
      padding: 14px;
    }

    .tile-header,
    .candidate-header {
      align-items: start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      min-width: 0;
    }

    .room-name {
      font-size: 16px;
      font-weight: 700;
      line-height: 1.3;
      overflow-wrap: anywhere;
    }

    .context {
      background: var(--secondary-background-color, #eef2f7);
      border-radius: 999px;
      color: var(--secondary-text-color, #52616f);
      flex: 0 0 auto;
      font-size: 12px;
      line-height: 1.2;
      max-width: 46%;
      overflow-wrap: anywhere;
      padding: 5px 8px;
    }

    .candidate-list {
      display: grid;
      gap: 10px;
    }

    .section-title {
      font-size: 14px;
      font-weight: 700;
      margin: 0;
    }

    .candidate-name {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.3;
      overflow-wrap: anywhere;
    }

    .candidate-meta,
    .message {
      color: var(--secondary-text-color, #52616f);
      font-size: 13px;
      line-height: 1.4;
      overflow-wrap: anywhere;
    }

    .message.error {
      color: var(--error-color, #b00020);
    }

    dl {
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(108px, max-content) minmax(0, 1fr);
      margin: 0;
    }

    dt {
      color: var(--secondary-text-color, #52616f);
      font-size: 12px;
    }

    dd {
      font-size: 13px;
      margin: 0;
      min-width: 0;
      overflow-wrap: anywhere;
    }

    .actions {
      align-items: end;
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(90px, 1fr) auto;
    }

    .override-status {
      color: var(--secondary-text-color, #52616f);
      display: grid;
      font-size: 13px;
      gap: 4px;
      line-height: 1.4;
    }

    .schedule-editor {
      align-items: end;
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(88px, 1fr)) auto;
    }

    label {
      color: var(--secondary-text-color, #52616f);
      display: grid;
      font-size: 12px;
      gap: 4px;
      min-width: 0;
    }

    input {
      background: var(--card-background-color, #ffffff);
      border: 1px solid var(--divider-color, #d8dee4);
      border-radius: 6px;
      color: inherit;
      font: inherit;
      min-width: 0;
      padding: 8px;
    }

    button {
      background: var(--primary-color, #0b6bcb);
      border: 0;
      border-radius: 6px;
      color: var(--text-primary-color, #ffffff);
      cursor: pointer;
      font: inherit;
      min-height: 36px;
      padding: 8px 10px;
      white-space: nowrap;
    }

    button.secondary {
      background: transparent;
      border: 1px solid var(--divider-color, #d8dee4);
      color: var(--primary-text-color, #1f2933);
    }

    button:disabled {
      cursor: default;
      opacity: 0.55;
    }

    .gaps {
      color: var(--secondary-text-color, #52616f);
      display: grid;
      font-size: 13px;
      gap: 6px;
      line-height: 1.4;
    }
  `;

  protected render() {
    if (!this.hass) {
      return this._renderShell(html`<div class="status">Loading Climate Relay</div>`);
    }

    const rooms = extractClimateRelayRooms(this.hass.states);
    return this._renderShell(html`
      ${rooms.length === 0
        ? html`<div class="status">No Climate Relay entities found</div>`
        : html`<section class="rooms">${rooms.map((room) => this._renderRoom(room))}</section>`}
      ${this._renderCandidateSection()}
      ${this._renderGaps()}
    `);
  }

  protected willUpdate(changedProperties: Map<string, unknown>): void {
    if (changedProperties.has("hass") && this.hass && this.hass !== this._candidateHass) {
      this._candidateHass = this.hass;
      void this._loadCandidates();
    }
  }

  private _renderShell(content: unknown) {
    return html`
      <ha-card>
        <div class="content">
          <h2>${this._config.title ?? "Climate Relay"}</h2>
          ${content}
        </div>
      </ha-card>
    `;
  }

  private _renderRoom(room: ClimateRelayRoomTile) {
    return html`
      <article class="room-tile">
        <div class="tile-header">
          <div class="room-name">${room.displayName}</div>
          ${room.activeControlContext
            ? html`<div class="context">${room.activeControlContext}</div>`
            : nothing}
        </div>
        <dl>
          ${this._renderMetric("Current", formatTemperature(room.currentTemperature))}
          ${this._renderMetric("Target", formatTemperature(room.targetTemperature))}
          ${this._renderMetric("Context", room.activeControlContext)}
          ${this._renderMetric("Override target", formatTemperature(room.manualOverrideTargetTemperature))}
          ${this._renderMetric("Override ends", room.manualOverrideEndsAt)}
          ${this._renderMetric("Degradation", room.degradationStatus)}
          ${this._renderMetric("Next change", room.nextChangeAt)}
          ${this._renderMetric("Override ends", room.manualOverrideEndsAt ? undefined : room.overrideEndsAt)}
          ${this._renderMetric("Schedule start", room.scheduleHomeStart)}
          ${this._renderMetric("Schedule end", room.scheduleHomeEnd)}
        </dl>
        ${this._renderScheduleEditor(room)}
        ${this._renderOverrideControls(room)}
      </article>
    `;
  }

  private _renderMetric(label: string, value: string | undefined) {
    if (!value) {
      return nothing;
    }
    return html`<dt>${label}</dt><dd>${value}</dd>`;
  }

  private _renderScheduleEditor(room: ClimateRelayRoomTile) {
    const edit = this._scheduleValue(room);
    const disabled = this._savingScheduleEntityId === room.entityId;
    return html`
      <div class="schedule-editor">
        <label>
          Start
          <input
            aria-label=${`${room.displayName} schedule start`}
            type="time"
            step="60"
            .value=${toTimeInputValue(edit.start)}
            @input=${(event: InputEvent) => this._updateScheduleEdit(room, "start", event)}
          />
        </label>
        <label>
          End
          <input
            aria-label=${`${room.displayName} schedule end`}
            type="time"
            step="60"
            .value=${toTimeInputValue(edit.end)}
            @input=${(event: InputEvent) => this._updateScheduleEdit(room, "end", event)}
          />
        </label>
        <button ?disabled=${disabled} @click=${() => this._saveSchedule(room)}>
          ${disabled ? "Saving" : "Save"}
        </button>
      </div>
      ${this._scheduleErrors[room.entityId]
        ? html`<div class="message error">${this._scheduleErrors[room.entityId]}</div>`
        : nothing}
      ${this._scheduleMessages[room.entityId]
        ? html`<div class="message">${this._scheduleMessages[room.entityId]}</div>`
        : nothing}
    `;
  }

  private _renderOverrideControls(room: ClimateRelayRoomTile) {
    if (room.manualOverrideActive) {
      return html`
        <div class="override-status">
          <div>Manual override active</div>
          ${room.manualOverrideTargetTemperature !== undefined
            ? html`<div>Target ${formatTemperature(room.manualOverrideTargetTemperature)}</div>`
            : nothing}
          ${room.manualOverrideEndsAt ? html`<div>Ends ${room.manualOverrideEndsAt}</div>` : nothing}
        </div>
        ${room.canClearOverride
          ? html`
              <div class="actions">
                <span></span>
                <button class="secondary" @click=${() => this._clearOverride(room)}>
                  Resume schedule
                </button>
              </div>
            `
          : nothing}
      `;
    }

    if (!room.canSetOverride) {
      return nothing;
    }

    return html`
      <div class="actions">
        <input
          aria-label=${`${room.displayName} override target`}
          inputmode="decimal"
          .value=${this._overrideTargets[room.entityId] ??
          formatNumber(room.targetTemperature) ??
          ""}
          @input=${(event: InputEvent) => this._updateOverrideTarget(room, event)}
        />
        <button @click=${() => this._setOverride(room)}>Override for 1h</button>
      </div>
    `;
  }

  private _renderCandidateSection() {
    const activatableCandidates = this._candidates.filter(
      (candidate) => !candidate.already_active,
    );
    if (!this._candidateLoading && activatableCandidates.length === 0 && !this._candidateError) {
      return nothing;
    }

    return html`
      <section class="candidate-list" aria-label="Add room">
        <h3 class="section-title">Add room</h3>
        ${this._candidateLoading ? html`<div class="message">Loading room candidates</div>` : nothing}
        ${this._candidateError ? html`<div class="message error">${this._candidateError}</div>` : nothing}
        ${this._activationMessage ? html`<div class="message">${this._activationMessage}</div>` : nothing}
        ${activatableCandidates.map((candidate) => this._renderCandidate(candidate))}
      </section>
    `;
  }

  private _renderCandidate(candidate: RoomCandidate) {
    const disabled = Boolean(candidate.unavailable_reason) || Boolean(this._activatingCandidateId);
    return html`
      <article class="candidate">
        <div class="candidate-header">
          <div>
            <div class="candidate-name">${candidate.area_name ?? candidate.primary_climate_display_name ?? candidate.primary_climate_entity_id}</div>
            <div class="candidate-meta">${candidate.primary_climate_display_name ?? candidate.primary_climate_entity_id}</div>
          </div>
          <button
            ?disabled=${disabled}
            @click=${() => this._activateCandidate(candidate)}
          >
            ${this._activatingCandidateId === candidate.candidate_id ? "Activating" : "Activate"}
          </button>
        </div>
        ${candidate.unavailable_reason
          ? html`<div class="message error">${formatUnavailableReason(candidate.unavailable_reason)}</div>`
          : nothing}
      </article>
    `;
  }

  private _renderGaps() {
    return html`
      <section class="gaps" aria-label="Climate Relay frontend contract gaps">
        <div>Room activation is available for eligible primary climate candidates; rich room configuration still needs optional sensor, target, and window support.</div>
        <div>Daily schedule start/end editing is available through backend-owned validation and update operations.</div>
        <div>Override controls are rendered from backend-projected room action capabilities.</div>
      </section>
    `;
  }

  private _scheduleValue(room: ClimateRelayRoomTile): { start: string; end: string } {
    return (
      this._scheduleEdits[room.entityId] ?? {
        start: room.scheduleHomeStart ?? "",
        end: room.scheduleHomeEnd ?? "",
      }
    );
  }

  private _updateScheduleEdit(
    room: ClimateRelayRoomTile,
    field: "start" | "end",
    event: InputEvent,
  ): void {
    const input = event.target as HTMLInputElement;
    const current = this._scheduleValue(room);
    this._scheduleEdits = {
      ...this._scheduleEdits,
      [room.entityId]: {
        ...current,
        [field]: input.value,
      },
    };
  }

  private _updateOverrideTarget(room: ClimateRelayRoomTile, event: InputEvent): void {
    const input = event.target as HTMLInputElement;
    this._overrideTargets = {
      ...this._overrideTargets,
      [room.entityId]: input.value,
    };
  }

  private async _setOverride(room: ClimateRelayRoomTile): Promise<void> {
    if (!room.canSetOverride) {
      return;
    }
    const rawValue = this._overrideTargets[room.entityId] ?? formatNumber(room.targetTemperature);
    const targetTemperature = Number(rawValue);
    if (!this.hass?.callService || !Number.isFinite(targetTemperature)) {
      return;
    }
    const roomReference = room.primaryClimateEntityId;
    await this.hass.callService("climate_relay_core", "set_area_override", {
      area_id: roomReference,
      target_temperature: targetTemperature,
      termination_type: "duration",
      duration_minutes: 60,
    });
  }

  private async _clearOverride(room: ClimateRelayRoomTile): Promise<void> {
    if (!this.hass?.callService || !room.canClearOverride) {
      return;
    }
    const roomReference = room.primaryClimateEntityId;
    await this.hass.callService("climate_relay_core", "clear_area_override", {
      area_id: roomReference,
    });
  }

  private async _saveSchedule(room: ClimateRelayRoomTile): Promise<void> {
    if (!this.hass?.connection) {
      return;
    }
    const edit = this._scheduleValue(room);
    this._savingScheduleEntityId = room.entityId;
    this._scheduleErrors = { ...this._scheduleErrors, [room.entityId]: "" };
    this._scheduleMessages = { ...this._scheduleMessages, [room.entityId]: "" };
    try {
      const result = await updateRoomSchedule(this.hass, room.primaryClimateEntityId, {
        schedule_home_start: edit.start,
        schedule_home_end: edit.end,
      });
      this._scheduleEdits = {
        ...this._scheduleEdits,
        [room.entityId]: {
          start: result.schedule_home_start,
          end: result.schedule_home_end,
        },
      };
      this._scheduleMessages = {
        ...this._scheduleMessages,
        [room.entityId]: "Schedule saved. Waiting for Home Assistant state to update.",
      };
    } catch (error) {
      this._scheduleErrors = {
        ...this._scheduleErrors,
        [room.entityId]: errorMessage(error),
      };
    } finally {
      this._savingScheduleEntityId = undefined;
    }
  }

  private async _loadCandidates(): Promise<void> {
    if (!this.hass?.connection) {
      return;
    }
    this._candidateLoading = true;
    this._candidateError = undefined;
    try {
      const result = await fetchRoomCandidates(this.hass);
      this._candidates = result.candidates;
    } catch (error) {
      this._candidateError = errorMessage(error);
    } finally {
      this._candidateLoading = false;
    }
  }

  private async _activateCandidate(candidate: RoomCandidate): Promise<void> {
    if (!this.hass?.connection || candidate.unavailable_reason) {
      return;
    }
    this._activatingCandidateId = candidate.candidate_id;
    this._activationMessage = undefined;
    this._candidateError = undefined;
    try {
      await activateRoom(this.hass, candidate.candidate_id);
      this._activationMessage = "Room activated. Waiting for Home Assistant state to update.";
      await this._loadCandidates();
    } catch (error) {
      this._candidateError = errorMessage(error);
    } finally {
      this._activatingCandidateId = undefined;
    }
  }
}

function formatTemperature(value: number | undefined): string | undefined {
  return value === undefined ? undefined : `${value.toFixed(1)} °C`;
}

function formatNumber(value: number | undefined): string | undefined {
  return value === undefined ? undefined : value.toFixed(1);
}

function toTimeInputValue(value: string | undefined): string {
  if (!value) {
    return "";
  }
  return value.length >= 5 ? value.slice(0, 5) : value;
}

function formatUnavailableReason(reason: string): string {
  const labels: Record<string, string> = {
    duplicate_area: "Area is already active.",
    duplicate_primary_climate: "Climate entity is already active.",
    missing_area: "Climate entity has no Home Assistant area.",
  };
  return labels[reason] ?? reason;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }
  return "Climate Relay backend request failed.";
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-relay-card": ClimateRelayCard;
  }
}
