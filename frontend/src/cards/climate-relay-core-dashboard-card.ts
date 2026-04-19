import { LitElement, css, html } from "lit";
import { customElement, property } from "lit/decorators.js";

import type { RoomCardViewModel } from "../types";

@customElement("climate-relay-core-dashboard-card")
export class ClimateRelayCoreDashboardCard extends LitElement {
  @property({ attribute: false }) public rooms: RoomCardViewModel[] = [];

  static styles = css`
    :host {
      display: block;
      color: #ffc04a;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }

    .grid {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }

    .card {
      background: linear-gradient(180deg, #684008 0%, #5a3404 100%);
      border-radius: 28px;
      min-height: 240px;
      padding: 24px;
    }

    .humidity {
      background: rgba(255, 196, 77, 0.12);
      border-radius: 999px;
      display: inline-flex;
      font-size: 28px;
      font-weight: 700;
      padding: 10px 18px;
    }

    .temperature {
      font-size: 96px;
      font-weight: 700;
      letter-spacing: -0.06em;
      line-height: 1;
      margin: 40px 0 12px;
    }

    .name {
      font-size: 28px;
      font-weight: 700;
    }

    .target {
      font-size: 22px;
      margin-top: 8px;
      opacity: 0.92;
    }
  `;

  protected render() {
    return html`
      <div class="grid">
        ${this.rooms.map(
          (room) => html`
            <article class="card">
              ${room.humidity !== undefined
                ? html`<div class="humidity">${room.humidity}%</div>`
                : null}
              <div class="temperature">${room.temperature.toFixed(1)}°</div>
              <div class="name">${room.name}</div>
              <div class="target">Set to ${room.targetTemperature.toFixed(1)}°</div>
            </article>
          `,
        )}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "climate-relay-core-dashboard-card": ClimateRelayCoreDashboardCard;
  }
}
