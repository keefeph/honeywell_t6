/*
 * Honeywell T6 Hysteresis card
 * type: custom:t6-hysteresis-card
 * entity: climate.<your_t6>_hysteresis
 * show_settings: true        # optional \u2013 installer parameter panel
 * range: [55, 85]            # optional \u2013 slider range (default: band \u00b18\u00b0)
 */
const CARD_VERSION = "1.1.0";

const CATEGORY_ORDER = [
  "Equipment",
  "Staging & limits",
  "Cycle rates",
  "Maintenance reminders",
  "Display & schedule",
];

const css = `
  :host { --t6-heat: var(--state-climate-heat-color, #ff8100);
          --t6-cool: var(--state-climate-cool-color, #2b9af9);
          --t6-off: var(--state-climate-off-color, #8a8a8a); }
  ha-card { padding: 16px; }
  .head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
  .name { font-size: 1.1em; font-weight: 500; color: var(--primary-text-color); }
  .status { color: var(--secondary-text-color); margin-top: 2px; font-size: .95em; }
  .now { text-align:right; }
  .now .t { font-size: 2.4em; font-weight: 300; line-height: 1; color: var(--primary-text-color); }
  .now .h { color: var(--secondary-text-color); font-size: .85em; margin-top: 4px; }
  .chip { display:inline-block; padding:2px 10px; border-radius: 12px; font-size:.8em;
          font-weight:500; margin-top:6px; color:#fff; background: var(--t6-off); }
  .chip.heating { background: var(--t6-heat); } .chip.cooling { background: var(--t6-cool); }

  .band { position: relative; height: 56px; margin: 26px 6px 4px; }
  .track { position:absolute; left:0; right:0; top: 24px; height: 8px; border-radius: 4px;
           background: var(--divider-color, #e0e0e0); }
  .fill { position:absolute; top: 24px; height: 8px; border-radius: 4px; background: var(--accent); opacity:.85; }
  .marker { position:absolute; top: 14px; width: 2px; height: 28px; background: var(--primary-text-color);
            transform: translateX(-1px); }
  .marker span { position:absolute; top: -18px; left: 50%; transform: translateX(-50%);
                 font-size:.75em; white-space:nowrap; color: var(--primary-text-color); }
  input[type=range] { position:absolute; left:-11px; width: calc(100% + 22px); top: 16px; margin:0;
                      background: none; pointer-events: none; -webkit-appearance: none; appearance: none; height: 24px; }
  input[type=range]::-webkit-slider-thumb { pointer-events: all; -webkit-appearance: none; width: 22px; height: 22px;
      border-radius: 50%; background: var(--card-background-color, #fff); border: 3px solid var(--accent); cursor: grab; }
  input[type=range]::-moz-range-thumb { pointer-events: all; width: 16px; height: 16px; border-radius: 50%;
      background: var(--card-background-color, #fff); border: 3px solid var(--accent); cursor: grab; }
  input[type=range]::-webkit-slider-runnable-track { background: none; }
  input[type=range]::-moz-range-track { background: none; }
  .scale { display:flex; justify-content:space-between; font-size:.75em; color: var(--secondary-text-color); margin: 0 6px; }

  .setpoints { display:flex; justify-content: space-between; margin-top: 14px; gap: 12px; }
  .sp { flex:1; border:1px solid var(--divider-color,#e0e0e0); border-radius: 12px; padding: 8px 10px; }
  .sp .lbl { font-size:.75em; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing:.04em; }
  .sp .row { display:flex; align-items:center; justify-content: space-between; }
  .sp .val { font-size: 1.6em; font-weight: 400; color: var(--primary-text-color); }
  .sp .rule { font-size:.78em; color: var(--secondary-text-color); margin-top: 2px; min-height: 2.4em; }
  .sp button { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--divider-color,#ccc);
               background: none; color: var(--primary-text-color); font-size: 1.2em; cursor: pointer; }
  .sp.active { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent) inset; }

  .modes, .fans { display:flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
  .modes button, .fans button { flex:1; min-width: 70px; padding: 8px; border-radius: 10px; cursor:pointer;
      border: 1px solid var(--divider-color,#ccc); background: none; color: var(--primary-text-color); font: inherit; }
  .modes button.on { color:#fff; border-color: transparent; }
  .modes button.on.heat { background: var(--t6-heat); } .modes button.on.cool { background: var(--t6-cool); }
  .modes button.on.off { background: var(--t6-off); }
  .fans button.on { border-color: var(--primary-color); color: var(--primary-color); font-weight: 500; }
  .fanlbl { font-size:.75em; color: var(--secondary-text-color); margin-top: 12px; }

  svg.loop { width: 100%; height: 86px; margin-top: 10px; }
  svg.loop text { font-size: 10px; fill: var(--secondary-text-color); }

  details { margin-top: 16px; border-top: 1px solid var(--divider-color,#e0e0e0); padding-top: 8px; }
  summary { cursor:pointer; color: var(--primary-text-color); font-weight: 500; padding: 4px 0; }
  .warn { font-size:.8em; color: var(--warning-color, #c77700); margin: 6px 0 10px; }
  .cat { margin-top: 10px; font-size:.8em; text-transform: uppercase; letter-spacing:.05em; color: var(--secondary-text-color); }
  .param { display:grid; grid-template-columns: 1fr 170px; align-items:center; gap: 8px; padding: 5px 0;
           border-bottom: 1px dashed var(--divider-color,#eee); }
  .param label { font-size: .9em; color: var(--primary-text-color); }
  .param label small { display:block; color: var(--secondary-text-color); font-size:.8em; }
  .param select, .param input { width: 100%; box-sizing: border-box; padding: 5px; border-radius: 6px;
      border: 1px solid var(--divider-color,#ccc); background: var(--card-background-color,#fff); color: var(--primary-text-color); font: inherit; }
  .param.unavail { opacity: .5; }
  .actions { display:flex; gap:8px; margin-top: 10px; }
  .actions button { padding: 6px 12px; border-radius: 8px; border:1px solid var(--divider-color,#ccc);
      background:none; color: var(--primary-text-color); cursor:pointer; font: inherit; }
  .err { color: var(--error-color, #db4437); padding: 8px; }

  .schedbar { display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;
      margin-top: 12px; padding: 8px 10px; border-radius: 10px; background: var(--secondary-background-color, #f5f5f5); }
  .schedbar .txt { font-size:.9em; color: var(--primary-text-color); }
  .schedbar .txt.held { color: var(--warning-color, #c77700); font-weight: 500; }
  .schedbar .btns { display:flex; gap:6px; }
  .pill { padding: 5px 12px; border-radius: 14px; border: 1px solid var(--divider-color,#ccc); background: var(--card-background-color,#fff);
      color: var(--primary-text-color); cursor:pointer; font: inherit; font-size:.85em; }
  .pill.primary { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); border-color: transparent; }
  .pill:disabled { opacity: .45; cursor: default; }
  .sedit .top { display:flex; align-items:center; gap: 10px; flex-wrap: wrap; margin: 6px 0 10px; }
  .sedit select { padding: 5px; border-radius: 6px; border:1px solid var(--divider-color,#ccc);
      background: var(--card-background-color,#fff); color: var(--primary-text-color); font: inherit; }
  .tabs { display:flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
  .tab { padding: 5px 10px; border-radius: 8px; border: 1px solid var(--divider-color,#ccc); background:none;
      color: var(--primary-text-color); cursor:pointer; font: inherit; font-size:.85em; }
  .tab.on { border-color: var(--primary-color, #03a9f4); color: var(--primary-color, #03a9f4); font-weight: 500; }
  .tab.heat.on { border-color: var(--t6-heat); color: var(--t6-heat); }
  .tab.cool.on { border-color: var(--t6-cool); color: var(--t6-cool); }
  .ptable { width:100%; border-collapse: collapse; font-size:.9em; }
  .ptable th { text-align:left; font-weight: 400; font-size:.8em; color: var(--secondary-text-color); padding: 2px 4px; }
  .ptable td { padding: 3px 4px; }
  .ptable input { width: 100%; box-sizing: border-box; padding: 5px; border-radius: 6px; border: 1px solid var(--divider-color,#ccc);
      background: var(--card-background-color,#fff); color: var(--primary-text-color); font: inherit; }
  .ptable td.num { width: 64px; } .ptable td.time { width: 104px; } .ptable td.del { width: 30px; text-align:center; }
  .ptable tr.now td:first-child input { border-color: var(--accent); }
  .del button { border:none; background:none; color: var(--secondary-text-color); font-size: 1.2em; cursor:pointer; }
  .del button:disabled { opacity:.3; cursor: default; }
  .sactions { display:flex; gap:8px; align-items:center; margin-top: 10px; flex-wrap: wrap; }
  .smsg { font-size:.85em; color: var(--secondary-text-color); }
  .smsg.bad { color: var(--error-color, #db4437); }
`;

class T6HysteresisCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("Set 'entity' to the T6 hysteresis climate entity");
    this._config = { show_settings: true, show_schedule: true, ...config };
    this._dragging = false;
    this._pending = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._built = false;
  }

  static getStubConfig(hass) {
    const e = Object.keys(hass.states).find(
      (id) => id.startsWith("climate.") && hass.states[id].attributes.parameter_entities !== undefined
    );
    return { entity: e || "climate.t6_hysteresis", show_settings: true };
  }

  getCardSize() { return this._config && this._config.show_settings ? 10 : 7; }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    if (!st) {
      this.shadowRoot.innerHTML = `<style>${css}</style><ha-card><div class="err">Entity ${this._config.entity} not found</div></ha-card>`;
      this._built = false;
      return;
    }
    if (!this._built) this._build();
    this._update(st);
  }

  // ---------------------------------------------------------------- build
  _build() {
    const r = this.shadowRoot;
    r.innerHTML = `<style>${css}</style>
      <ha-card>
        <div class="head">
          <div><div class="name"></div><div class="status"></div><span class="chip"></span></div>
          <div class="now"><div class="t"></div><div class="h"></div></div>
        </div>
        <div class="schedbar"><span class="txt"></span><span class="btns"></span></div>
        <div class="band">
          <div class="track"></div><div class="fill"></div>
          <div class="marker"><span></span></div>
          <input type="range" class="lo" aria-label="Low set point">
          <input type="range" class="hi" aria-label="High set point">
        </div>
        <div class="scale"><span class="smin"></span><span class="smax"></span></div>
        <div class="setpoints">
          <div class="sp lo-box"><div class="lbl">Low set point</div>
            <div class="row"><button data-adj="lo,-1">\u2212</button><span class="val lo-val"></span><button data-adj="lo,1">+</button></div>
            <div class="rule lo-rule"></div></div>
          <div class="sp hi-box"><div class="lbl">High set point</div>
            <div class="row"><button data-adj="hi,-1">\u2212</button><span class="val hi-val"></span><button data-adj="hi,1">+</button></div>
            <div class="rule hi-rule"></div></div>
        </div>
        <svg class="loop" viewBox="0 0 300 86" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="modes">
          <button class="off" data-mode="off">Off</button>
          <button class="heat" data-mode="heat">Heat</button>
          <button class="cool" data-mode="cool">Cool</button>
        </div>
        <div class="fanlbl">Fan</div><div class="fans"></div>
        <details class="sched"><summary>Schedule</summary><div class="sedit"></div></details>
        <details class="settings"><summary>Thermostat settings (installer parameters)</summary>
          <div class="warn">These are the T6's Z-Wave configuration parameters. Equipment-type and staging
          parameters must match your wiring \u2014 wrong values can damage HVAC equipment. Some are disabled by
          default; enable them under Settings \u2192 Devices if you need them. A battery-powered T6 applies changes
          when it next wakes up.</div>
          <div class="plist"></div>
          <div class="actions"><button class="refresh">Re-read from thermostat</button></div>
        </details>
      </ha-card>`;

    const lo = r.querySelector("input.lo"), hi = r.querySelector("input.hi");
    const onInput = (which) => () => {
      this._dragging = true;
      let l = parseFloat(lo.value), h = parseFloat(hi.value);
      const gap = this._gap();
      if (h - l < gap) { if (which === "lo") l = h - gap; else h = l + gap; }
      lo.value = l; hi.value = h;
      this._pending = [l, h];
      this._drawBand(l, h);
    };
    const onChange = () => { this._dragging = false; if (this._pending) this._sendBand(...this._pending); };
    lo.addEventListener("input", onInput("lo")); hi.addEventListener("input", onInput("hi"));
    lo.addEventListener("change", onChange); hi.addEventListener("change", onChange);

    r.querySelectorAll("[data-adj]").forEach((b) => b.addEventListener("click", () => {
      const [which, dir] = b.dataset.adj.split(",");
      const st = this._hass.states[this._config.entity];
      const step = st.attributes.target_temp_step || 1;
      let [l, h] = this._pending || [st.attributes.target_temp_low, st.attributes.target_temp_high];
      if (which === "lo") l = Math.min(l + dir * step, h - this._gap());
      else h = Math.max(h + dir * step, l + this._gap());
      this._pending = [l, h];
      this._drawBand(l, h);
      clearTimeout(this._adjTimer);
      this._adjTimer = setTimeout(() => this._sendBand(l, h), 800);
    }));

    r.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () =>
      this._hass.callService("climate", "set_hvac_mode", { entity_id: this._config.entity, hvac_mode: b.dataset.mode })));

    r.querySelector(".refresh").addEventListener("click", () =>
      this._hass.callService("honeywell_t6", "refresh_parameters", { entity_id: this._config.entity }));
    r.querySelector(".settings").style.display = this._config.show_settings ? "" : "none";
    this._built = true;
    this._paramKey = null;
    this._fanKey = null;
    this._barKey = null;
    this._schedKey = null;
    this._draft = null;
    this._dirty = false;
    this._sSeason = null;
    this._sGroup = 0;
    this._sMsg = "";
    const showSched = this._config.show_schedule;
    r.querySelector(".sched").style.display = showSched ? "" : "none";
    r.querySelector(".schedbar").style.display = showSched ? "" : "none";
  }

  _gap() {
    const st = this._hass.states[this._config.entity];
    return st && st.attributes.target_temp_step ? st.attributes.target_temp_step : 1;
  }

  _sendBand(l, h) {
    this._hass.callService("honeywell_t6", "set_band", { entity_id: this._config.entity, low: l, high: h })
      .finally(() => { setTimeout(() => { this._pending = null; }, 1500); });
  }

  _unit() { return (this._hass.config.unit_system && this._hass.config.unit_system.temperature) || "\u00b0"; }

  _range(st) {
    if (this._config.range) return this._config.range;
    const a = st.attributes;
    const pad = this._unit().includes("C") ? 4 : 8;
    let lo = Math.floor(Math.min(a.target_temp_low, a.current_temperature ?? a.target_temp_low) - pad);
    let hi = Math.ceil(Math.max(a.target_temp_high, a.current_temperature ?? a.target_temp_high) + pad);
    return [Math.max(lo, a.min_temp ?? lo), Math.min(hi, a.max_temp ?? hi)];
  }

  // --------------------------------------------------------------- update
  _update(st) {
    const r = this.shadowRoot, a = st.attributes, u = this._unit();
    const mode = st.state;
    const accent = mode === "heat" ? "var(--t6-heat)" : mode === "cool" ? "var(--t6-cool)" : "var(--t6-off)";
    r.host.style.setProperty("--accent", accent);

    r.querySelector(".name").textContent = this._config.name || a.friendly_name || "Thermostat";
    r.querySelector(".status").textContent = a.status || "";
    const chip = r.querySelector(".chip");
    chip.textContent = (a.hvac_action || st.state).replace(/_/g, " ");
    chip.className = "chip " + (a.hvac_action || "");
    r.querySelector(".now .t").textContent = a.current_temperature != null ? `${a.current_temperature}${u}` : "\u2014";
    r.querySelector(".now .h").textContent = a.current_humidity != null ? `${a.current_humidity}% RH` : "";

    r.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));

    const [min, max] = this._range(st);
    this._min = min; this._max = max;
    r.querySelector(".smin").textContent = `${min}${u}`;
    r.querySelector(".smax").textContent = `${max}${u}`;
    const lo = r.querySelector("input.lo"), hi = r.querySelector("input.hi");
    const step = a.target_temp_step || 1;
    for (const el of [lo, hi]) { el.min = min; el.max = max; el.step = step; }
    if (!this._dragging && !this._pending) {
      lo.value = a.target_temp_low; hi.value = a.target_temp_high;
      this._drawBand(a.target_temp_low, a.target_temp_high);
    } else if (this._pending) {
      this._drawBand(...this._pending);
    }

    // fans
    const fans = a.fan_modes || [];
    const fanKey = fans.join("|");
    const fbox = r.querySelector(".fans");
    r.querySelector(".fanlbl").style.display = fans.length ? "" : "none";
    if (fanKey !== this._fanKey) {
      this._fanKey = fanKey;
      fbox.innerHTML = "";
      fans.forEach((f) => {
        const b = document.createElement("button");
        b.textContent = f; b.dataset.fan = f;
        b.addEventListener("click", () =>
          this._hass.callService("climate", "set_fan_mode", { entity_id: this._config.entity, fan_mode: f }));
        fbox.appendChild(b);
      });
    }
    fbox.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.fan === a.fan_mode));

    if (this._config.show_settings) this._updateParams(a.parameter_entities || []);
    if (this._config.show_schedule) { this._updateSchedBar(a); this._updateSchedEditor(st); }
  }

  // -------------------------------------------------------------- schedule
  _svc(service, data = {}) {
    return this._hass.callService("honeywell_t6", service, { entity_id: this._config.entity, ...data });
  }

  _updateSchedBar(a) {
    if (a.schedule_enabled === undefined) {  // integration older than 1.1
      this.shadowRoot.querySelector(".schedbar").style.display = "none";
      return;
    }
    const key = [a.schedule_status, a.hold, a.schedule_enabled].join("|");
    if (key === this._barKey) return;
    this._barKey = key;
    const bar = this.shadowRoot.querySelector(".schedbar");
    const txt = bar.querySelector(".txt");
    txt.textContent = a.schedule_status || "";
    txt.classList.toggle("held", !!a.hold);
    const btns = bar.querySelector(".btns");
    btns.innerHTML = "";
    const add = (label, fn, primary) => {
      const b = document.createElement("button");
      b.className = "pill" + (primary ? " primary" : "");
      b.textContent = label;
      b.addEventListener("click", fn);
      btns.appendChild(b);
    };
    if (!a.schedule_enabled) {
      add("Turn schedule on", () => this._svc("set_schedule_enabled", { enabled: true }), true);
    } else if (a.hold === "next") {
      add("Resume schedule", () => this._svc("resume_schedule"), true);
      add("Hold permanently", () => this._svc("set_hold", { type: "permanent" }));
    } else if (a.hold === "permanent") {
      add("Resume schedule", () => this._svc("resume_schedule"), true);
    } else {
      add("Hold", () => this._svc("set_hold", { type: "permanent" }));
      add("Schedule off", () => this._svc("set_schedule_enabled", { enabled: false }));
    }
  }

  static get LAYOUTS() {
    return {
      same: { label: "Every day", groups: [["Every day", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]] },
      weekday_weekend: { label: "Weekdays + weekend",
        groups: [["Mon\u2013Fri", ["mon", "tue", "wed", "thu", "fri"]], ["Sat\u2013Sun", ["sat", "sun"]]] },
      each_day: { label: "Each day separately",
        groups: [["Mon", ["mon"]], ["Tue", ["tue"]], ["Wed", ["wed"]], ["Thu", ["thu"]], ["Fri", ["fri"]],
                 ["Sat", ["sat"]], ["Sun", ["sun"]]] },
    };
  }

  _groups() { return T6HysteresisCard.LAYOUTS[this._draft.layout].groups; }

  _propagate() {  // make every day in a group match the group's first day
    for (const [, days] of this._groups()) {
      for (const d of days.slice(1)) this._draft.days[d] = JSON.parse(JSON.stringify(this._draft.days[days[0]]));
    }
  }

  _updateSchedEditor(st) {
    const a = st.attributes;
    const sched = a.schedule;
    if (!sched) { this.shadowRoot.querySelector(".sched").style.display = "none"; return; }
    if (this._sSeason === null) this._sSeason = st.state === "cool" ? "cool" : "heat";
    const key = JSON.stringify(sched);
    if (!this._dirty && key !== this._schedKey) {
      this._schedKey = key;
      this._draft = JSON.parse(key);
      if (this._sGroup >= this._groups().length) this._sGroup = 0;
      this._renderSchedEditor();
    } else if (!this._dirty) {
      this._markCurrentRow();
    }
  }

  _markCurrentRow() {
    const st = this._hass.states[this._config.entity], a = st.attributes;
    const today = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][new Date().getDay()];
    const season = st.state === "cool" ? "cool" : "heat";
    const showing = this._draft && this._groups()[this._sGroup][1].includes(today) && this._sSeason === season;
    this.shadowRoot.querySelectorAll(".ptable tr[data-name]").forEach((tr) =>
      tr.classList.toggle("now", !!a.schedule_enabled && showing && tr.dataset.name === a.schedule_period));
  }

  _renderSchedEditor() {
    const box = this.shadowRoot.querySelector(".sedit");
    const st = this._hass.states[this._config.entity];
    const step = st.attributes.target_temp_step || 1;
    const u = this._unit();
    const L = T6HysteresisCard.LAYOUTS;
    const groups = this._groups();
    const [, gdays] = groups[this._sGroup];
    const list = this._draft.days[gdays[0]][this._sSeason];
    box.innerHTML = "";

    const top = document.createElement("div");
    top.className = "top";
    const lbl = document.createElement("span");
    lbl.className = "smsg"; lbl.textContent = "Days:";
    const sel = document.createElement("select");
    for (const [k, v] of Object.entries(L)) {
      const o = document.createElement("option"); o.value = k; o.textContent = v.label; sel.appendChild(o);
    }
    sel.value = this._draft.layout;
    sel.addEventListener("change", () => {
      this._draft.layout = sel.value; this._sGroup = 0; this._propagate(); this._setDirty(); this._renderSchedEditor();
    });
    top.append(lbl, sel);
    box.appendChild(top);

    const mkTabs = (items, current, onPick, extraClass) => {
      const t = document.createElement("div"); t.className = "tabs";
      items.forEach(([label, val]) => {
        const b = document.createElement("button");
        b.className = "tab " + (extraClass ? val : "") + (val === current ? " on" : "");
        b.textContent = label;
        b.addEventListener("click", () => { onPick(val); this._renderSchedEditor(); });
        t.appendChild(b);
      });
      return t;
    };
    box.appendChild(mkTabs([["Heating bands", "heat"], ["Cooling bands", "cool"]], this._sSeason,
      (v) => { this._sSeason = v; }, true));
    if (groups.length > 1) {
      box.appendChild(mkTabs(groups.map(([label], i) => [label, i]), this._sGroup, (v) => { this._sGroup = v; }));
    }

    const tbl = document.createElement("table");
    tbl.className = "ptable";
    tbl.innerHTML = `<tr><th>Period</th><th>Starts</th><th>Low ${u}</th><th>High ${u}</th><th></th></tr>`;
    list.forEach((p, i) => {
      const tr = document.createElement("tr");
      tr.dataset.name = p.name;
      const cell = (cls, el) => { const td = document.createElement("td"); td.className = cls; td.appendChild(el); tr.appendChild(td); };
      const input = (type, value, onChange, extra = {}) => {
        const el = document.createElement("input");
        el.type = type; el.value = value; Object.assign(el, extra);
        el.addEventListener("change", () => { onChange(el.value); this._propagate(); this._setDirty(); });
        return el;
      };
      cell("name", input("text", p.name, (v) => { p.name = v; tr.dataset.name = v; }, { maxLength: 20 }));
      cell("time", input("time", p.start, (v) => {
        p.start = v;
        list.sort((x, y) => (x.start < y.start ? -1 : 1));
        setTimeout(() => this._renderSchedEditor(), 0);  // show the new order
      }));
      cell("num", input("number", p.low, (v) => { p.low = parseFloat(v); }, { step }));
      cell("num", input("number", p.high, (v) => { p.high = parseFloat(v); }, { step }));
      const del = document.createElement("button");
      del.textContent = "\u00d7"; del.title = "Remove period"; del.disabled = list.length <= 1;
      del.addEventListener("click", () => { list.splice(i, 1); this._propagate(); this._setDirty(); this._renderSchedEditor(); });
      cell("del", del);
      tbl.appendChild(tr);
    });
    box.appendChild(tbl);

    const actions = document.createElement("div");
    actions.className = "sactions";
    const addBtn = document.createElement("button");
    addBtn.className = "pill"; addBtn.textContent = "+ Add period"; addBtn.disabled = list.length >= 8;
    addBtn.addEventListener("click", () => {
      const last = list[list.length - 1];
      const [h, m] = last.start.split(":").map(Number);
      const next = `${String(Math.min(h + 1, 23)).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
      list.push({ name: "New", start: next, low: last.low, high: last.high });
      this._propagate(); this._setDirty(); this._renderSchedEditor();
    });
    const save = document.createElement("button");
    save.className = "pill primary"; save.textContent = "Save schedule"; save.disabled = !this._dirty;
    save.addEventListener("click", () => this._saveSchedule());
    const revert = document.createElement("button");
    revert.className = "pill"; revert.textContent = "Revert"; revert.disabled = !this._dirty;
    revert.addEventListener("click", () => {
      this._dirty = false; this._schedKey = null; this._sMsg = "";
      this._updateSchedEditor(this._hass.states[this._config.entity]);
    });
    const msg = document.createElement("span");
    msg.className = "smsg" + (this._sMsgBad ? " bad" : "");
    msg.textContent = this._sMsg || (this._dirty ? "Unsaved changes" : "");
    actions.append(addBtn, save, revert, msg);
    box.appendChild(actions);
    this._markCurrentRow();
  }

  _setDirty() {
    this._dirty = true; this._sMsg = ""; this._sMsgBad = false;
    const r = this.shadowRoot;
    r.querySelectorAll(".sactions .pill").forEach((b) => {
      if (b.textContent !== "+ Add period") b.disabled = false;
    });
    const m = r.querySelector(".sactions .smsg");
    if (m) { m.textContent = "Unsaved changes"; m.classList.remove("bad"); }
  }

  _saveSchedule() {
    const fail = (text) => { this._sMsg = text; this._sMsgBad = true; this._renderSchedEditor(); };
    for (const [d, seasons] of Object.entries(this._draft.days)) {
      for (const [season, list] of Object.entries(seasons)) {
        for (const p of list) {
          if (!/^\d{1,2}:\d{2}$/.test(p.start || "")) return fail(`${d} ${season}: every period needs a start time`);
          if (!(p.high > p.low)) return fail(`${d} ${season} ${p.name}: high must be above low`);
        }
        list.sort((x, y) => (x.start < y.start ? -1 : 1));
      }
    }
    this._svc("set_schedule", { layout: this._draft.layout, days: this._draft.days })
      .then(() => {
        // Keep showing the draft; the editor refreshes when the new state arrives.
        this._dirty = false; this._sMsg = "Saved"; this._sMsgBad = false;
        this._schedKey = JSON.stringify(this._hass.states[this._config.entity].attributes.schedule);
        this._renderSchedEditor();
      })
      .catch((err) => fail((err && err.message) || "Could not save"));
  }

  _pct(v) { return ((v - this._min) / (this._max - this._min)) * 100; }

  _drawBand(l, h) {
    const r = this.shadowRoot, st = this._hass.states[this._config.entity], a = st.attributes, u = this._unit();
    const mode = st.state, phase = a.phase;
    if (!this._dragging) {
      r.querySelector("input.lo").value = l;
      r.querySelector("input.hi").value = h;
    }
    const fill = r.querySelector(".fill");
    fill.style.left = `${this._pct(l)}%`;
    fill.style.width = `${this._pct(h) - this._pct(l)}%`;
    const m = r.querySelector(".marker");
    if (a.current_temperature != null) {
      m.style.display = "";
      m.style.left = `${Math.min(100, Math.max(0, this._pct(a.current_temperature)))}%`;
      m.querySelector("span").textContent = `now ${a.current_temperature}${u}`;
    } else m.style.display = "none";
    r.querySelector(".lo-val").textContent = `${l}${u}`;
    r.querySelector(".hi-val").textContent = `${h}${u}`;

    const loRule = r.querySelector(".lo-rule"), hiRule = r.querySelector(".hi-rule");
    const loBox = r.querySelector(".lo-box"), hiBox = r.querySelector(".hi-box");
    loBox.classList.remove("active"); hiBox.classList.remove("active");
    if (mode === "heat") {
      loRule.textContent = "Heat turns ON when it falls to here";
      hiRule.textContent = "Heat turns OFF when it rises to here";
      (phase === "running" ? hiBox : loBox).classList.add("active");
    } else if (mode === "cool") {
      loRule.textContent = "Cooling turns OFF when it falls to here";
      hiRule.textContent = "Cooling turns ON when it rises to here";
      (phase === "running" ? loBox : hiBox).classList.add("active");
    } else {
      loRule.textContent = "Heat: on here \u00b7 Cool: off here";
      hiRule.textContent = "Heat: off here \u00b7 Cool: on here";
    }
    this._drawLoop(l, h, mode, phase);
  }

  /* Hysteresis loop diagram: x = temperature, y = equipment on/off. */
  _drawLoop(l, h, mode, phase) {
    const svg = this.shadowRoot.querySelector("svg.loop");
    if (mode !== "heat" && mode !== "cool") { svg.style.display = "none"; return; }
    svg.style.display = "";
    const u = this._unit();
    const x0 = 40, x1 = 260, yOn = 18, yOff = 62;
    const color = mode === "heat" ? "var(--t6-heat)" : "var(--t6-cool)";
    const dim = "var(--divider-color,#ccc)";
    // heat: ON path goes left->right at top (until high), OFF path right->left at bottom (until low)
    const onPath = mode === "heat" ? `M${x0},${yOn} L${x1},${yOn}` : `M${x1},${yOn} L${x0},${yOn}`;
    const offPath = mode === "heat" ? `M${x1},${yOff} L${x0},${yOff}` : `M${x0},${yOff} L${x1},${yOff}`;
    const drop = mode === "heat" ? `M${x1},${yOn} L${x1},${yOff}` : `M${x0},${yOn} L${x0},${yOff}`;
    const rise = mode === "heat" ? `M${x0},${yOff} L${x0},${yOn}` : `M${x1},${yOff} L${x1},${yOn}`;
    const running = phase === "running";
    svg.innerHTML = `
      <defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="${color}"/></marker></defs>
      <path d="${onPath}" stroke="${running ? color : dim}" stroke-width="${running ? 3 : 2}" fill="none" marker-end="url(#ar)"/>
      <path d="${offPath}" stroke="${!running ? color : dim}" stroke-width="${!running ? 3 : 2}" fill="none" marker-end="url(#ar)"/>
      <path d="${drop}" stroke="${dim}" stroke-dasharray="3 3" fill="none"/>
      <path d="${rise}" stroke="${dim}" stroke-dasharray="3 3" fill="none"/>
      <text x="2" y="${yOn + 4}">ON</text><text x="2" y="${yOff + 4}">OFF</text>
      <text x="${x0 - 8}" y="80">${l}${u}</text><text x="${x1 - 8}" y="80">${h}${u}</text>
      <text x="150" y="${yOn - 6}" text-anchor="middle">${mode === "heat" ? "heating \u2192 until high" : "cooling \u2190 until low"}</text>
      <text x="150" y="${yOff + 14}" text-anchor="middle">${mode === "heat" ? "resting \u2190 until low" : "resting \u2192 until high"}</text>`;
  }

  // ------------------------------------------------------------ parameters
  _updateParams(ids) {
    const key = ids.join("|");
    const box = this.shadowRoot.querySelector(".plist");
    if (key !== this._paramKey) {
      this._paramKey = key;
      box.innerHTML = "";
      const groups = {};
      ids.forEach((id) => {
        const s = this._hass.states[id];
        if (!s) return;
        const c = s.attributes.category || "Other";
        (groups[c] = groups[c] || []).push(id);
      });
      const cats = [...CATEGORY_ORDER, ...Object.keys(groups).filter((c) => !CATEGORY_ORDER.includes(c))];
      cats.filter((c) => groups[c]).forEach((c) => {
        const h = document.createElement("div");
        h.className = "cat"; h.textContent = c; box.appendChild(h);
        groups[c].forEach((id) => box.appendChild(this._paramRow(id)));
      });
      if (!ids.length) box.innerHTML = `<div class="status">No parameter entities yet \u2013 is the T6 included in Z-Wave JS?</div>`;
    }
    box.querySelectorAll(".param").forEach((row) => this._syncRow(row));
  }

  _paramRow(id) {
    const s = this._hass.states[id];
    const row = document.createElement("div");
    row.className = "param"; row.dataset.id = id;
    const label = document.createElement("label");
    const nice = (s.attributes.friendly_name || id).replace(/^.*?(P\d\d )/, "$1");
    label.innerHTML = `<span></span><small></small>`;
    label.querySelector("span").textContent = nice;
    const special = s.attributes.special_values
      ? Object.entries(s.attributes.special_values).map(([k, v]) => `${k} = ${v}`).join(", ") : "";
    label.querySelector("small").textContent = [special, s.attributes.unit_of_measurement && !special ? s.attributes.unit_of_measurement : ""].filter(Boolean).join(" ");
    row.appendChild(label);
    let ctl;
    if (id.startsWith("select.")) {
      ctl = document.createElement("select");
      (s.attributes.options || []).forEach((o) => { const op = document.createElement("option"); op.value = o; op.textContent = o; ctl.appendChild(op); });
      ctl.addEventListener("change", () =>
        this._hass.callService("select", "select_option", { entity_id: id, option: ctl.value }));
    } else {
      ctl = document.createElement("input");
      ctl.type = "number";
      ctl.min = s.attributes.min; ctl.max = s.attributes.max; ctl.step = s.attributes.step || 1;
      ctl.addEventListener("change", () => {
        const v = parseFloat(ctl.value);
        if (Number.isNaN(v)) return;
        this._hass.callService("number", "set_value", { entity_id: id, value: v });
      });
    }
    row.appendChild(ctl);
    return row;
  }

  _syncRow(row) {
    const s = this._hass.states[row.dataset.id];
    const ctl = row.querySelector("select, input");
    if (!s || !ctl) return;
    const unavailable = s.state === "unavailable" || s.state === "unknown";
    row.classList.toggle("unavail", unavailable);
    ctl.disabled = s.state === "unavailable";
    if (this.shadowRoot.activeElement === ctl) return; // don't fight the user
    if (unavailable) { if (ctl.tagName === "INPUT") ctl.value = ""; return; }
    ctl.value = ctl.tagName === "INPUT" ? String(parseFloat(s.state)) : s.state;
  }
}

/*
 * Registration.
 * The integration may load this file very early (before the Home Assistant
 * frontend has finished booting). If the frontend then installs its own
 * custom-element registry, a definition made now would be invisible to it.
 * So we (re)register whenever the current registry doesn't know the card.
 * A fresh subclass is used each time because a constructor may only be
 * registered once per registry.
 */
const TAG = "t6-hysteresis-card";
let announced = false;
function registerT6Card() {
  try {
    if (!window.customElements.get(TAG)) {
      window.customElements.define(TAG, class extends T6HysteresisCard {});
    }
  } catch (err) {
    console.warn("t6-hysteresis-card: registration retry failed", err);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === TAG)) {
    window.customCards.push({
      type: TAG,
      name: "Honeywell T6 Hysteresis",
      description: "Two set-point hysteresis control and installer settings for a Honeywell T6 Pro Z-Wave",
      preview: false,
    });
  }
  if (!announced) {
    announced = true;
    console.info(`%c T6-HYSTERESIS-CARD %c ${CARD_VERSION} `, "background:#ff8100;color:#fff", "");
  }
}
registerT6Card();
window.addEventListener("load", registerT6Card);
[250, 1000, 3000, 8000, 15000].forEach((ms) => setTimeout(registerT6Card, ms));
