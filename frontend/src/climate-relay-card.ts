import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { activateRoom, fetchRoomCandidates } from "./backend-api";
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
      grid-template-columns: minmax(90px, 1fr) auto auto;
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
          ${this._renderMetric("Degradation", room.degradationStatus)}
          ${this._renderMetric("Next change", room.nextChangeAt)}
          ${this._renderMetric("Override ends", room.overrideEndsAt)}
        </dl>
        <div class="actions">
          <input
            aria-label=${`${room.displayName} override target`}
            inputmode="decimal"
            .value=${this._overrideTargets[room.entityId] ??
            formatNumber(room.targetTemperature) ??
            ""}
            @input=${(event: InputEvent) => this._updateOverrideTarget(room, event)}
          />
          <button @click=${() => this._setOverride(room)}>Override 1h</button>
          <button class="secondary" @click=${() => this._clearOverride(room)}>Resume</button>
        </div>
      </article>
    `;
  }

  private _renderMetric(label: string, value: string | undefined) {
    if (!value) {
      return nothing;
    }
    return html`<dt>${label}</dt><dd>${value}</dd>`;
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
        <div>Room activation needs backend candidate discovery and a frontend-callable activation operation.</div>
        <div>Schedule editing needs backend-owned schedule validation and update operations.</div>
        <div>Override 1h is a temporary fixed-duration scaffold that uses existing backend services; supported action capabilities are not yet exposed as room state.</div>
      </section>
    `;
  }

  private _updateOverrideTarget(room: ClimateRelayRoomTile, event: InputEvent): void {
    const input = event.target as HTMLInputElement;
    this._overrideTargets = {
      ...this._overrideTargets,
      [room.entityId]: input.value,
    };
  }

  private async _setOverride(room: ClimateRelayRoomTile): Promise<void> {
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
    if (!this.hass?.callService) {
      return;
    }
    const roomReference = room.primaryClimateEntityId;
    await this.hass.callService("climate_relay_core", "clear_area_override", {
      area_id: roomReference,
    });
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
