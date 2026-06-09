/**
 * Smart Thermostat Card v5.0
 * - Icons moved up (no overlap with arc)
 * - Rectangular mode buttons, dynamic width
 * - Fixed +/- button positions (min-width on temp display)
 * - Draggable thumb on arc
 * - Gray arc when blocked (window/outdoor)
 */

class SmartThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._dragging = false;
  }

  static getStubConfig() { return { entity: "" }; }

  setConfig(config) {
    if (!config.entity) throw new Error("Trebuie să specificați o entitate");
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _arc(cx, cy, r, startDeg, endDeg) {
    const r2d = d => d * Math.PI / 180;
    const x1 = cx + r * Math.cos(r2d(startDeg));
    const y1 = cy + r * Math.sin(r2d(startDeg));
    const x2 = cx + r * Math.cos(r2d(endDeg));
    const y2 = cy + r * Math.sin(r2d(endDeg));
    const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
    const sweep = endDeg > startDeg ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} ${sweep} ${x2} ${y2}`;
  }

  _degToTemp(deg, minTemp, maxTemp) {
    const ARC_START = -216, ARC_END = 36;
    const pct = (deg - ARC_START) / (ARC_END - ARC_START);
    return Math.round((minTemp + pct * (maxTemp - minTemp)) * 2) / 2;
  }

  _setupDrag(svg, entityId, minTemp, maxTemp, currentTarget) {
    const CX = 100, CY = 100, R = 80;
    const ARC_START = -216, ARC_END = 36;

    const getAngle = (clientX, clientY) => {
      const rect = svg.getBoundingClientRect();
      const scaleX = 200 / rect.width;
      const scaleY = 185 / rect.height;
      const x = (clientX - rect.left) * scaleX - CX;
      const y = (clientY - rect.top) * scaleY - CY;
      let deg = Math.atan2(y, x) * 180 / Math.PI;
      return deg;
    };

    const clampDeg = (deg) => {
      // Normalize to arc range
      while (deg < ARC_START) deg += 360;
      while (deg > ARC_START + 360) deg -= 360;
      if (deg > ARC_END && deg < ARC_START + 360) {
        // Outside arc — snap to nearest end
        const distStart = Math.abs(deg - (ARC_START + 360));
        const distEnd = Math.abs(deg - ARC_END);
        deg = distEnd < distStart ? ARC_END : ARC_START;
      }
      return Math.min(Math.max(deg, ARC_START), ARC_END);
    };

    const onMove = (e) => {
      if (!this._dragging) return;
      e.preventDefault();
      const client = e.touches ? e.touches[0] : e;
      let deg = getAngle(client.clientX, client.clientY);
      deg = clampDeg(deg);
      const newTemp = this._degToTemp(deg, minTemp, maxTemp);
      if (newTemp !== currentTarget && newTemp >= minTemp && newTemp <= maxTemp) {
        currentTarget = newTemp;
        this._call("climate", "set_temperature", { entity_id: entityId, temperature: newTemp });
      }
    };

    const onUp = () => { this._dragging = false; };

    const thumb = svg.querySelector("#drag-thumb");
    if (thumb) {
      thumb.addEventListener("mousedown", (e) => { this._dragging = true; e.preventDefault(); });
      thumb.addEventListener("touchstart", (e) => { this._dragging = true; e.preventDefault(); }, { passive: false });
    }

    svg.addEventListener("mousemove", onMove);
    svg.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
  }

  render() {
    if (!this._config || !this._hass) return;

    const entityId = this._config.entity;
    const state = this._hass.states[entityId];
    if (!state) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--error-color)">Entitatea "${entityId}" nu a fost găsită.</div></ha-card>`;
      return;
    }

    const attrs       = state.attributes;
    const hvacMode    = state.state;
    const currentTemp = attrs.current_temperature;
    const targetTemp  = attrs.temperature;
    const presetMode  = attrs.preset_mode || "none";
    const windowOpen  = attrs.window_open || false;
    const outdoorTemp = attrs.outdoor_temperature;
    const outdoorThr  = attrs.outdoor_temp_threshold || 20;
    const hysteresis  = attrs.hysteresis || 0.5;
    const name        = attrs.friendly_name || entityId;
    const hvacModes   = attrs.hvac_modes || ["off", "heat"];
    const presetModes = attrs.preset_modes || ["none"];
    const minTemp     = attrs.min_temp || 5;
    const maxTemp     = attrs.max_temp || 35;

    const heatSwitchId = attrs.heat_switch;
    const coolSwitchId = attrs.cool_switch;
    const heatOn = heatSwitchId && this._hass.states[heatSwitchId]?.state === "on";

    const outdoorBlocking = outdoorTemp != null && outdoorTemp > outdoorThr && hvacMode === "heat";
    const isBlocked = windowOpen || outdoorBlocking;
    const isOff     = hvacMode === "off" || isBlocked;
    const isHeating = heatOn && hvacMode === "heat" && !isBlocked;
    const isCooling = hvacMode === "cool" && !isBlocked;

    // Arc color — gray when blocked or off
    let arcColorHex = "#666";
    if (!isBlocked) {
      if (isHeating)             arcColorHex = "#e74c3c";
      else if (isCooling)        arcColorHex = "#3498db";
      else if (hvacMode === "heat") arcColorHex = "#e67e22";
      else if (hvacMode === "cool") arcColorHex = "#2980b9";
    }

    const ARC_START = -216, ARC_END = 36;
    const CX = 100, CY = 100, R = 80;
    const pct = targetTemp
      ? Math.min(Math.max((targetTemp - minTemp) / (maxTemp - minTemp), 0), 1)
      : 0.5;
    const arcFill = ARC_START + pct * (ARC_END - ARC_START);
    const tRad = arcFill * Math.PI / 180;
    const thumbX = CX + R * Math.cos(tRad);
    const thumbY = CY + R * Math.sin(tRad);

    const windowColor = windowOpen ? "#3498db" : "var(--secondary-text-color)";
    const sunColor = outdoorBlocking ? "#e67e22" : "var(--secondary-text-color)";

    // Center icon
    let centerIcon = "";
    if (isCooling) {
      centerIcon = `<svg viewBox="0 0 24 24" class="center-icon" fill="#3498db">
        <path d="M20 11h-2.5l1.8-1.8-1.4-1.4L15 10.7V8h-2v5h-2V8H9v2.7L6.1 7.8 4.7 9.2 6.5 11H4v2h2.5l-1.8 1.8 1.4 1.4L9 13.3V16h2v-5h2v5h2v-2.7l2.9 2.9 1.4-1.4L17.5 13H20v-2z"/>
      </svg>`;
    } else {
      const rc = isHeating ? "#e74c3c" : (hvacMode === "heat" && !isBlocked ? "#e67e2299" : "var(--disabled-color,#999)");
      centerIcon = `<svg viewBox="0 0 24 24" class="center-icon" fill="${rc}">
        <path d="M19 8H5a3 3 0 0 0 0 6h1v2h2v-2h8v2h2v-2h1a3 3 0 0 0 0-6zm0 4H5a1 1 0 0 1 0-2h14a1 1 0 0 1 0 2z"/>
      </svg>`;
    }

    // Mode buttons — only configured ones
    const modeButtons = [
      { mode: "off",  icon: "⏸️", label: "Off",     cls: "mode-off"  },
      { mode: "heat", icon: "🔥", label: "Căldură", cls: "mode-heat" },
      ...(hvacModes.includes("cool") ? [{ mode: "cool", icon: "❄️", label: "Răcire", cls: "mode-cool" }] : []),
    ];

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          border-radius: 20px;
          background: var(--ha-card-background, var(--card-background-color, #fff));
          overflow: hidden;
          box-shadow: var(--ha-card-box-shadow, 0 2px 12px rgba(0,0,0,0.15));
          padding-bottom: 12px;
          container-type: inline-size;
        }

        .name-bar {
          text-align: center;
          padding: 14px 12px 0;
          font-size: clamp(13px, 4cqi, 17px);
          font-weight: 700;
          color: var(--primary-text-color);
        }

        .dial-wrap {
          position: relative;
          width: 100%;
          aspect-ratio: 1 / 0.82;
          max-width: 320px;
          margin: 0 auto;
        }
        .dial-svg {
          width: 100%; height: 100%;
          overflow: visible;
          cursor: default;
        }
        #drag-thumb { cursor: grab; }
        #drag-thumb:active { cursor: grabbing; }

        .dial-overlay {
          position: absolute;
          top: 46%; left: 50%;
          transform: translate(-50%, -50%);
          text-align: center;
          pointer-events: none;
          width: 55%;
        }
        .current-temp-wrap {
          display: flex;
          align-items: flex-start;
          justify-content: center;
          line-height: 1;
        }
        .current-temp {
          font-size: clamp(28px, 12cqi, 52px);
          font-weight: 800;
          color: var(--primary-text-color);
        }
        .current-unit {
          font-size: clamp(12px, 4cqi, 18px);
          color: var(--secondary-text-color);
          margin-top: 4px; margin-left: 2px;
        }
        .center-icon {
          width: clamp(20px, 6cqi, 30px);
          height: clamp(20px, 6cqi, 30px);
          margin-top: 4px;
        }
        .target-label {
          font-size: clamp(10px, 3cqi, 13px);
          color: var(--secondary-text-color);
          margin-top: 2px;
        }

        /* +/- controls — fixed layout so buttons don't jump */
        .temp-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: clamp(10px, 4cqi, 20px);
          margin: clamp(-14px, -3cqi, -4px) 0 10px;
          padding: 0 16px;
        }
        .temp-btn {
          flex-shrink: 0;
          width: clamp(36px, 10cqi, 50px);
          height: clamp(36px, 10cqi, 50px);
          border-radius: 50%;
          border: none;
          background: var(--secondary-background-color);
          color: ${arcColorHex};
          font-size: clamp(20px, 6cqi, 28px);
          font-weight: 300;
          cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 2px 6px rgba(0,0,0,0.12);
          transition: filter 0.1s;
        }
        .temp-btn:hover { filter: brightness(1.1); }
        .temp-value-wrap {
          /* Fixed width so decimal doesn't shift buttons */
          width: clamp(90px, 26cqi, 130px);
          text-align: center;
          flex-shrink: 0;
        }
        .temp-value {
          font-size: clamp(24px, 9cqi, 36px);
          font-weight: 800;
          color: var(--primary-text-color);
        }
        .temp-unit-s {
          font-size: clamp(11px, 3cqi, 15px);
          color: var(--secondary-text-color);
        }

        /* Mode buttons — rectangular, fill full width */
        .mode-row {
          display: flex;
          gap: 6px;
          padding: 2px 12px 10px;
        }
        .mode-btn {
          flex: 1;
          padding: clamp(8px, 2.5cqi, 12px) 4px;
          border-radius: 12px;
          border: 2px solid var(--divider-color);
          background: var(--secondary-background-color);
          cursor: pointer;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          transition: all 0.15s;
        }
        .mode-btn:hover { filter: brightness(1.08); }
        .mode-btn-icon { font-size: clamp(16px, 5cqi, 22px); line-height: 1; }
        .mode-btn-label {
          font-size: clamp(9px, 2.5cqi, 12px);
          font-weight: 700;
          color: var(--secondary-text-color);
        }
        .mode-off.active  { border-color: #9ca3af; background: #9ca3af18; }
        .mode-off.active .mode-btn-label { color: #9ca3af; }
        .mode-heat.active { border-color: #e74c3c; background: #e74c3c18; }
        .mode-heat.active .mode-btn-label { color: #e74c3c; }
        .mode-cool.active { border-color: #3498db; background: #3498db18; }
        .mode-cool.active .mode-btn-label { color: #3498db; }

        /* Presets */
        .preset-section {
          display: ${presetModes.length > 1 ? "block" : "none"};
          padding: 0 12px 6px;
          text-align: center;
        }
        .preset-label {
          font-size: clamp(9px, 2.5cqi, 11px);
          font-weight: 700;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 5px;
        }
        .preset-btns {
          display: flex; flex-wrap: wrap;
          gap: 5px; justify-content: center;
        }
        .preset-btn {
          padding: clamp(3px,1cqi,6px) clamp(8px,3cqi,14px);
          border-radius: 20px;
          border: 1.5px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          font-size: clamp(10px, 3cqi, 13px);
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s;
        }
        .preset-btn.active {
          border-color: ${arcColorHex};
          background: ${arcColorHex}22;
          color: ${arcColorHex};
        }

        /* Info bar */
        .info-bar {
          display: flex;
          gap: 5px;
          padding: 8px 12px 0;
          border-top: 1px solid var(--divider-color);
          margin-top: 6px;
        }
        .info-chip {
          flex: 1;
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: clamp(5px,2cqi,8px) 4px;
          text-align: center;
        }
        .info-chip-lbl {
          font-size: clamp(8px, 2cqi, 10px);
          font-weight: 700;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .info-chip-val {
          font-size: clamp(11px, 3.5cqi, 14px);
          font-weight: 800;
          color: var(--primary-text-color);
          margin-top: 1px;
        }
      </style>

      <ha-card>
        <div class="name-bar">${name}</div>

        <div class="dial-wrap">
          <svg id="dial-svg" class="dial-svg" viewBox="0 0 200 185" preserveAspectRatio="xMidYMid meet">

            <!-- Track -->
            <path d="${this._arc(CX,CY,R,-216,36)}"
              fill="none" stroke="var(--divider-color,#ddd)" stroke-width="8" stroke-linecap="round"/>

            <!-- Active arc — gray when blocked -->
            <path d="${this._arc(CX,CY,R,-216,arcFill)}"
              fill="none" stroke="${arcColorHex}" stroke-width="8"
              stroke-linecap="round" opacity="${isOff ? 0.35 : 1}"/>

            <!-- Draggable thumb -->
            <g id="drag-thumb">
              <circle cx="${thumbX}" cy="${thumbY}" r="10"
                fill="${arcColorHex}" opacity="${isOff ? 0.35 : 1}"/>
              <circle cx="${thumbX}" cy="${thumbY}" r="5"
                fill="white" opacity="${isOff ? 0.35 : 1}"/>
            </g>

            <!-- Window icon — positioned ABOVE the arc start (top-left) -->
            <g transform="translate(22,22)" opacity="${windowOpen ? 1 : 0.3}">
              <rect x="-13" y="-13" width="26" height="26" rx="6"
                fill="${windowOpen ? '#3498db18' : 'transparent'}"
                stroke="${windowOpen ? '#3498db' : 'var(--secondary-text-color)'}" stroke-width="1.5"/>
              <line x1="-5" y1="-8" x2="-5" y2="8" stroke="${windowColor}" stroke-width="1.5"/>
              <line x1="5" y1="-8" x2="5" y2="8" stroke="${windowColor}" stroke-width="1.5"/>
              <line x1="-8" y1="0" x2="8" y2="0" stroke="${windowColor}" stroke-width="1.2"/>
              <rect x="-9" y="-10" width="18" height="20" rx="2"
                fill="none" stroke="${windowColor}" stroke-width="1.5"/>
            </g>

            <!-- Sun icon — positioned ABOVE the arc end (top-right) -->
            <g transform="translate(178,22)" opacity="${outdoorBlocking ? 1 : 0.3}">
              <rect x="-13" y="-13" width="26" height="26" rx="6"
                fill="${outdoorBlocking ? '#e67e2218' : 'transparent'}"
                stroke="${outdoorBlocking ? '#e67e22' : 'var(--secondary-text-color)'}" stroke-width="1.5"/>
              <circle cx="0" cy="0" r="5" fill="none" stroke="${sunColor}" stroke-width="1.5"/>
              <line x1="0" y1="-9" x2="0" y2="-7" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="0" y1="7" x2="0" y2="9" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="-9" y1="0" x2="-7" y2="0" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="7" y1="0" x2="9" y2="0" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="-6.4" y1="-6.4" x2="-4.9" y2="-4.9" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="4.9" y1="4.9" x2="6.4" y2="6.4" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="6.4" y1="-6.4" x2="4.9" y2="-4.9" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
              <line x1="-4.9" y1="4.9" x2="-6.4" y2="6.4" stroke="${sunColor}" stroke-width="1.5" stroke-linecap="round"/>
            </g>

          </svg>

          <div class="dial-overlay">
            <div class="current-temp-wrap">
              <span class="current-temp">
                ${currentTemp != null ? currentTemp.toFixed(1) : "—"}
              </span>
              <span class="current-unit">°C</span>
            </div>
            <div style="display:flex;justify-content:center;margin-top:4px">
              ${centerIcon}
            </div>
            <div class="target-label">țintă: ${targetTemp || "—"}°C</div>
          </div>
        </div>

        <!-- Temp controls with fixed-width center -->
        <div class="temp-controls">
          <button class="temp-btn" id="btn-minus">−</button>
          <div class="temp-value-wrap">
            <span class="temp-value">${targetTemp != null ? targetTemp : "—"}</span>
            <span class="temp-unit-s">°C</span>
          </div>
          <button class="temp-btn" id="btn-plus">+</button>
        </div>

        <!-- Mode buttons — rectangular, full width -->
        <div class="mode-row">
          ${modeButtons.map(b => `
            <button class="mode-btn ${b.cls} ${hvacMode === b.mode || (isBlocked && b.mode === 'off') ? 'active' : ''}"
              data-mode="${b.mode}">
              <span class="mode-btn-icon">${b.icon}</span>
              <span class="mode-btn-label">${b.label}</span>
            </button>
          `).join("")}
        </div>

        <!-- Presets -->
        <div class="preset-section">
          <div class="preset-label">Preseturi</div>
          <div class="preset-btns">
            ${presetModes.map(p => `
              <button class="preset-btn ${presetMode === p ? 'active' : ''}" data-preset="${p}">
                ${p === "none" ? "Manual" : p}
              </button>
            `).join("")}
          </div>
        </div>

        <!-- Info bar -->
        <div class="info-bar">
          <div class="info-chip">
            <div class="info-chip-lbl">Histereza</div>
            <div class="info-chip-val">±${hysteresis}°C</div>
          </div>
          <div class="info-chip">
            <div class="info-chip-lbl">Exterior</div>
            <div class="info-chip-val" style="color:${outdoorBlocking ? '#e67e22' : 'var(--primary-text-color)'}">
              ${outdoorTemp != null ? outdoorTemp + "°C" : "—"}
            </div>
          </div>
          <div class="info-chip">
            <div class="info-chip-lbl">Prag ext.</div>
            <div class="info-chip-val">${outdoorThr}°C</div>
          </div>
        </div>

      </ha-card>
    `;

    // +/- buttons
    this.shadowRoot.querySelector("#btn-minus")?.addEventListener("click", () => {
      const n = Math.max((targetTemp || 21) - 0.5, minTemp);
      this._call("climate", "set_temperature", { entity_id: entityId, temperature: n });
    });
    this.shadowRoot.querySelector("#btn-plus")?.addEventListener("click", () => {
      const n = Math.min((targetTemp || 21) + 0.5, maxTemp);
      this._call("climate", "set_temperature", { entity_id: entityId, temperature: n });
    });

    // Mode buttons
    this.shadowRoot.querySelectorAll(".mode-btn").forEach(b => {
      b.addEventListener("click", () =>
        this._call("climate", "set_hvac_mode", { entity_id: entityId, hvac_mode: b.dataset.mode }));
    });

    // Preset buttons
    this.shadowRoot.querySelectorAll(".preset-btn").forEach(b => {
      b.addEventListener("click", () =>
        this._call("climate", "set_preset_mode", { entity_id: entityId, preset_mode: b.dataset.preset }));
    });

    // Draggable arc thumb
    const svg = this.shadowRoot.querySelector("#dial-svg");
    if (svg) {
      this._setupDrag(svg, entityId, minTemp, maxTemp, targetTemp);
    }
  }

  getCardSize() { return 6; }
}

customElements.define("smart-thermostat-card", SmartThermostatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "smart-thermostat-card",
  name: "Smart Thermostat Card",
  description: "Card responsive pentru Smart Thermostat",
  preview: false,
});

console.info(
  `%c SMART-THERMOSTAT-CARD %c v5.0.0 `,
  "color: white; background: #10b981; font-weight: 700;",
  "color: #10b981; background: white; font-weight: 700;"
);
