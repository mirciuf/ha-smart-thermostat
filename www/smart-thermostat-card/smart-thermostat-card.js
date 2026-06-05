/**
 * Smart Thermostat Card
 * Custom Lovelace card for Smart Thermostat integration
 */

class SmartThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  static getConfigElement() {
    return document.createElement("smart-thermostat-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }

  setConfig(config) {
    if (!config.entity) throw new Error("Trebuie să specificați o entitate");
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  // ── Helpers ──────────────────────────────────────────────────────────

  _state(entityId, fallback = "unavailable") {
    if (!entityId || !this._hass) return fallback;
    return this._hass.states[entityId]?.state ?? fallback;
  }

  _attr(entityId, key, fallback = null) {
    if (!entityId || !this._hass) return fallback;
    return this._hass.states[entityId]?.attributes?.[key] ?? fallback;
  }

  _callService(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  // ── Mode colors & icons ───────────────────────────────────────────────

  _modeColor(mode, action) {
    if (mode === "off") return "#6b7280";
    if (action === "heating") return "#ef4444";
    if (action === "cooling") return "#3b82f6";
    if (mode === "heat") return "#f97316";
    if (mode === "cool") return "#60a5fa";
    return "#6b7280";
  }

  _modeIcon(mode, action) {
    if (action === "heating") return "🔥";
    if (action === "cooling") return "❄️";
    if (mode === "heat") return "🔥";
    if (mode === "cool") return "❄️";
    return "⏸️";
  }

  // ── Render ─────────────────────────────────────────────────────────────

  render() {
    if (!this._config || !this._hass) return;

    const entityId = this._config.entity;
    const state = this._hass.states[entityId];

    if (!state) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--error-color)">Entitatea "${entityId}" nu a fost găsită.</div></ha-card>`;
      return;
    }

    const attrs = state.attributes;
    const hvacMode = state.state;
    const hvacActionRaw = attrs.hvac_action || "idle";
    
    // Read switch states directly for accurate color/status
    const heatSwitchId = attrs.heat_switch;
    const coolSwitchId = attrs.cool_switch;
    const heatSwitchOn = heatSwitchId && this._hass.states[heatSwitchId]?.state === "on";
    const coolSwitchOn = coolSwitchId && this._hass.states[coolSwitchId]?.state === "on";
    
    // Determine actual action from switch states
    let hvacAction = hvacActionRaw;
    if (hvacMode !== "off") {
      if (heatSwitchOn) hvacAction = "heating";
      else if (coolSwitchOn) hvacAction = "cooling";
      else hvacAction = "idle";
    }
    
    const currentTemp = attrs.current_temperature;
    const targetTemp = attrs.temperature;
    const presetMode = attrs.preset_mode || "none";
    const presets = attrs.presets || {};
    const windowOpen = attrs.window_open || false;
    const outdoorTemp = attrs.outdoor_temperature;
    const outdoorThreshold = attrs.outdoor_temp_threshold || 20;
    const hysteresis = attrs.hysteresis || 0.5;
    const name = attrs.friendly_name || entityId;
    const hvacModes = attrs.hvac_modes || ["off", "heat"];
    const presetModes = attrs.preset_modes || ["none"];

    const color = this._modeColor(hvacMode, hvacAction);
    const icon = this._modeIcon(hvacMode, hvacAction);

    // Check blocking conditions
    const outdoorBlocking = outdoorTemp !== null && outdoorTemp !== undefined
      && outdoorTemp > outdoorThreshold && hvacMode === "heat";

    // Status message
    let statusMsg = "";
    let statusIcon = "";
    let statusColor = "";
    if (windowOpen) {
      statusMsg = "Geam deschis";
      statusIcon = "🪟";
      statusColor = "#3b82f6";
    } else if (outdoorBlocking) {
      statusMsg = `Exterior ${outdoorTemp}°C`;
      statusIcon = "☀️";
      statusColor = "#ef4444";
    }

    // Temperature arc
    const minTemp = attrs.min_temp || 5;
    const maxTemp = attrs.max_temp || 35;
    const arcPercent = targetTemp ? (targetTemp - minTemp) / (maxTemp - minTemp) : 0.5;
    const arcDeg = arcPercent * 240 - 120; // -120 to +120 degrees

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          border-radius: 16px;
          overflow: hidden;
          background: var(--ha-card-background, var(--card-background-color, white));
          box-shadow: var(--ha-card-box-shadow, none);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }

        /* ── Header ── */
        .header {
          padding: 14px 16px 8px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .header-left { display: flex; align-items: center; gap: 10px; }
        .header-icon {
          width: 36px; height: 36px; border-radius: 50%;
          background: ${color}22;
          display: flex; align-items: center; justify-content: center;
          font-size: 18px;
        }
        .header-name {
          font-size: 15px; font-weight: 700;
          color: var(--primary-text-color);
        }
        .header-action {
          font-size: 11px; color: var(--secondary-text-color);
          text-transform: uppercase; letter-spacing: 0.5px;
        }

        /* ── Status badge ── */
        .status-badge {
          display: ${statusMsg ? "flex" : "none"};
          align-items: center; gap: 5px;
          background: ${statusColor}22;
          border: 1px solid ${statusColor}55;
          border-radius: 20px;
          padding: 4px 10px;
          font-size: 12px; font-weight: 600;
          color: ${statusColor};
        }

        /* ── Thermostat dial ── */
        .dial-section {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 8px 16px 16px;
          position: relative;
        }
        .dial-wrapper {
          position: relative;
          width: 180px; height: 180px;
        }
        .dial-svg { width: 180px; height: 180px; }
        .dial-center {
          position: absolute;
          top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          text-align: center;
        }
        .dial-current {
          font-size: 36px; font-weight: 800;
          color: ${color};
          line-height: 1;
        }
        .dial-current-unit {
          font-size: 14px; color: var(--secondary-text-color);
        }
        .dial-target {
          font-size: 13px; color: var(--secondary-text-color);
          margin-top: 2px;
        }

        /* ── Temp controls ── */
        .temp-controls {
          display: flex; align-items: center; gap: 20px;
          margin-top: 8px;
        }
        .temp-btn {
          width: 40px; height: 40px; border-radius: 50%;
          border: 2px solid ${color}55;
          background: ${color}11;
          color: ${color};
          font-size: 22px; font-weight: 700;
          cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          transition: all 0.15s;
        }
        .temp-btn:hover { background: ${color}33; }
        .temp-value {
          font-size: 28px; font-weight: 800;
          color: var(--primary-text-color);
          min-width: 70px; text-align: center;
        }
        .temp-unit { font-size: 14px; color: var(--secondary-text-color); }

        /* ── HVAC mode buttons ── */
        .mode-section {
          padding: 0 16px 12px;
          display: flex; gap: 8px;
        }
        .mode-btn {
          flex: 1; padding: 8px 4px;
          border-radius: 10px;
          border: 2px solid transparent;
          cursor: pointer;
          font-size: 11px; font-weight: 600;
          text-align: center;
          transition: all 0.15s;
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
        }
        .mode-btn.active-off {
          border-color: #6b728055;
          background: #6b728022;
          color: #6b7280;
        }
        .mode-btn.active-heat {
          border-color: #f9731655;
          background: #f9731622;
          color: #f97316;
        }
        .mode-btn.active-cool {
          border-color: #60a5fa55;
          background: #60a5fa22;
          color: #60a5fa;
        }
        .mode-btn-icon { font-size: 18px; display: block; margin-bottom: 2px; }

        /* ── Preset section ── */
        .preset-section {
          padding: 0 16px 14px;
          display: ${presetModes.length > 1 ? "block" : "none"};
        }
        .preset-label {
          font-size: 11px; font-weight: 600;
          color: var(--secondary-text-color);
          text-transform: uppercase; letter-spacing: 0.5px;
          margin-bottom: 6px;
        }
        .preset-buttons {
          display: flex; flex-wrap: wrap; gap: 6px;
        }
        .preset-btn {
          padding: 5px 12px;
          border-radius: 20px;
          border: 1.5px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          font-size: 12px; font-weight: 600;
          cursor: pointer;
          transition: all 0.15s;
        }
        .preset-btn.active {
          border-color: ${color};
          background: ${color}22;
          color: ${color};
        }

        /* ── Info row ── */
        .info-row {
          padding: 8px 16px 14px;
          display: flex; gap: 8px;
          border-top: 1px solid var(--divider-color);
        }
        .info-item {
          flex: 1;
          background: var(--secondary-background-color);
          border-radius: 8px; padding: 8px 10px;
        }
        .info-item-label {
          font-size: 10px; font-weight: 600;
          color: var(--secondary-text-color);
          text-transform: uppercase; letter-spacing: 0.5px;
        }
        .info-item-value {
          font-size: 14px; font-weight: 700;
          color: var(--primary-text-color);
          margin-top: 2px;
        }
      </style>

      <ha-card>

        <!-- Header -->
        <div class="header">
          <div class="header-left">
            <div class="header-icon">${icon}</div>
            <div>
              <div class="header-name">${name}</div>
              <div class="header-action">${this._actionLabel(hvacAction, hvacMode)}</div>
            </div>
          </div>
          <div class="status-badge">
            <span>${statusIcon}</span>
            <span>${statusMsg}</span>
          </div>
        </div>

        <!-- Dial -->
        <div class="dial-section">
          <div class="dial-wrapper">
            <svg class="dial-svg" viewBox="0 0 180 180">
              <!-- Track arc -->
              <path d="${this._arcPath(90, 90, 75, -210, 30)}"
                fill="none" stroke="var(--divider-color)" stroke-width="6"
                stroke-linecap="round"/>
              <!-- Active arc -->
              <path d="${this._arcPath(90, 90, 75, -210, -210 + (arcPercent * 240))}"
                fill="none" stroke="${color}" stroke-width="6"
                stroke-linecap="round" opacity="${hvacMode === 'off' ? 0.3 : 1}"/>
            </svg>
            <div class="dial-center">
              <div class="dial-current">
                ${currentTemp !== null && currentTemp !== undefined ? currentTemp.toFixed(1) : "—"}
              </div>
              <div class="dial-current-unit">°C interior</div>
              <div class="dial-target">țintă: ${targetTemp || "—"}°C</div>
            </div>
          </div>

          <!-- Temperature controls -->
          <div class="temp-controls">
            <button class="temp-btn" id="btn-minus">−</button>
            <div>
              <span class="temp-value">${targetTemp || "—"}</span>
              <span class="temp-unit">°C</span>
            </div>
            <button class="temp-btn" id="btn-plus">+</button>
          </div>
        </div>

        <!-- HVAC Mode buttons -->
        <div class="mode-section">
          <button class="mode-btn ${hvacMode === 'off' ? 'active-off' : ''}" data-mode="off">
            <span class="mode-btn-icon">⏸️</span>Off
          </button>
          <button class="mode-btn ${hvacMode === 'heat' ? 'active-heat' : ''}" data-mode="heat">
            <span class="mode-btn-icon">🔥</span>Caldura
          </button>
          ${hvacModes.includes("cool") ? `
          <button class="mode-btn ${hvacMode === 'cool' ? 'active-cool' : ''}" data-mode="cool">
            <span class="mode-btn-icon">❄️</span>Racire
          </button>` : ""}
        </div>

        <!-- Preset buttons -->
        <div class="preset-section">
          <div class="preset-label">Preseturi</div>
          <div class="preset-buttons">
            ${presetModes.map(p => `
              <button class="preset-btn ${presetMode === p ? 'active' : ''}" data-preset="${p}">
                ${p === "none" ? "Manual" : p}
              </button>
            `).join("")}
          </div>
        </div>

        <!-- Info row -->
        <div class="info-row">
          <div class="info-item">
            <div class="info-item-label">Histereza</div>
            <div class="info-item-value">±${hysteresis}°C</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Exterior</div>
            <div class="info-item-value">${outdoorTemp !== null && outdoorTemp !== undefined ? outdoorTemp + "°C" : "—"}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Prag ext.</div>
            <div class="info-item-value">${outdoorThreshold}°C</div>
          </div>
        </div>

      </ha-card>
    `;

    // Event listeners
    this.shadowRoot.querySelector("#btn-minus")?.addEventListener("click", () => {
      const newTemp = Math.max((targetTemp || 21) - 0.5, minTemp);
      this._callService("climate", "set_temperature", { entity_id: entityId, temperature: newTemp });
    });

    this.shadowRoot.querySelector("#btn-plus")?.addEventListener("click", () => {
      const newTemp = Math.min((targetTemp || 21) + 0.5, maxTemp);
      this._callService("climate", "set_temperature", { entity_id: entityId, temperature: newTemp });
    });

    this.shadowRoot.querySelectorAll(".mode-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        this._callService("climate", "set_hvac_mode", {
          entity_id: entityId,
          hvac_mode: btn.dataset.mode
        });
      });
    });

    this.shadowRoot.querySelectorAll(".preset-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        this._callService("climate", "set_preset_mode", {
          entity_id: entityId,
          preset_mode: btn.dataset.preset
        });
      });
    });
  }

  _actionLabel(action, mode) {
    if (mode === "off") return "Oprit";
    if (action === "heating") return "Încălzire activă";
    if (action === "cooling") return "Răcire activă";
    if (action === "idle") return "Inactiv — în așteptare";
    return "—";
  }

  _arcPath(cx, cy, r, startDeg, endDeg) {
    const toRad = d => (d * Math.PI) / 180;
    const x1 = cx + r * Math.cos(toRad(startDeg));
    const y1 = cy + r * Math.sin(toRad(startDeg));
    const x2 = cx + r * Math.cos(toRad(endDeg));
    const y2 = cy + r * Math.sin(toRad(endDeg));
    const diff = endDeg - startDeg;
    const large = Math.abs(diff) > 180 ? 1 : 0;
    const sweep = diff > 0 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} ${sweep} ${x2} ${y2}`;
  }

  getCardSize() { return 5; }
}

customElements.define("smart-thermostat-card", SmartThermostatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "smart-thermostat-card",
  name: "Smart Thermostat Card",
  description: "Card pentru Smart Thermostat cu indicatori vizuali pentru geam deschis și temperatură exterioară",
  preview: false,
});

console.info(
  `%c SMART-THERMOSTAT-CARD %c v1.1.0 `,
  "color: white; background: #10b981; font-weight: 700;",
  "color: #10b981; background: white; font-weight: 700;"
);
