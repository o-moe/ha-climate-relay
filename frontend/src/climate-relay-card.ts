import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { extractClimateRelayRooms } from "./room-state";
import type {
  ClimateRelayCardConfig,
  ClimateRelayRoomTile,
  HomeAssistantLike,
} from "./types";

@customElement("climate-relay-card")
export class ClimateRelayCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistantLike;
  @state() private _config: ClimateRelayCardConfig = {};
  @state() private _overrideTargets: Record<string, string> = {};

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

    .room-tile {
      border: 1px solid var(--divider-color, #d8dee4);
      border-radius: 8px;
      display: grid;
      gap: 12px;
      min-width: 0;
      padding: 14px;
    }

    .tile-header {
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
      ${this._renderGaps()}
    `);
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
          <button @click=${() => this._setOverride(room)}>Override</button>
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

  private _renderGaps() {
    return html`
      <section class="gaps" aria-label="Climate Relay frontend contract gaps">
        <div>Room activation needs backend candidate discovery and a frontend-callable activation operation.</div>
        <div>Schedule editing needs backend-owned schedule validation and update operations.</div>
        <div>Override controls use existing backend services; supported action capabilities are not yet exposed as room state.</div>
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
    await this.hass.callService("climate_relay_core", "set_area_override", {
      area_id: room.primaryClimateEntityId,
      target_temperature: targetTemperature,
      termination_type: "duration",
      duration_minutes: 60,
    });
  }

  private async _clearOverride(room: ClimateRelayRoomTile): Promise<void> {
    if (!this.hass?.callService) {
      return;
    }
    await this.hass.callService("climate_relay_core", "clear_area_override", {
      area_id: room.primaryClimateEntityId,
    });
  }
}

function formatTemperature(value: number | undefined): string | undefined {
  return value === undefined ? undefined : `${value.toFixed(1)} °C`;
}

function formatNumber(value: number | undefined): string | undefined {
  return value === undefined ? undefined : value.toFixed(1);
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-relay-card": ClimateRelayCard;
  }
}
