import {
  MAIN, METRICS, REGIMES, REGIME_SHORT, SOURCES, VARIABLES, VIEWS, el, fmt, fmtInt, heatmap, legend, limitsPanel, lineChart, load,
  pick, rowsOf, stationMap, statusPanel, table,
} from "./app.js?v=11";

const page = document.body.dataset.page;
const $ = (id) => document.getElementById(id);
const colour = (id) => `var(--s${(SOURCES[id] || { slot: 6 }).slot})`;
const name = (id) => (SOURCES[id] ? SOURCES[id].label : id);
const varLabel = (v) => VARIABLES[v].label;
const unit = (v, metric) => (["brier", "ets", "pod", "far", "csi"].includes(metric) ? "" : ` (${VARIABLES[v].unit})`);

function select(id, labelText, options, value) {
  const s = el("select", { id });
  for (const [v, t] of options) {
    const o = el("option", { value: v, text: t });
    if (String(v) === String(value)) o.selected = true;
    s.append(o);
  }
  return el("label", {}, el("span", { class: "label", text: labelText }), s);
}

function emptyScores(meta, what) {
  const written = Object.values(meta.metrics || {}).filter((s) => s === "written").length;
  const n = Object.keys(meta.metrics || {}).length;
  return el("div", { class: "empty", text: `${what} appear here after scoring. Protocol ${meta.protocol_signed_off ? "fixed" : "in draft"}; ${written} of ${n} metric functions written.` });
}

const base = { qc: "flags_removed", station: "all", hour_local: "all", regime: "all" };

function series(rows, sources, xKey) {
  return sources.map((id) => ({
    id, label: name(id), colour: colour(id), dash: (SOURCES[id] || {}).dash,
    points: rows.filter((r) => r.source === id).map((r) => ({ x: r[xKey], y: r.value, lo: r.low, hi: r.high, n: r.n_pairs })),
  })).filter((s) => s.points.length);
}

function verdict(r, lower) {
  if (r.low === null || r.high === null) return "no interval";
  if (r.low <= 0 && r.high >= 0) return "no detectable difference";
  const better = lower ? r.high < 0 : r.low > 0;
  return better ? "lower error" : "higher error";
}

// ------------------------------------------------------------------ scorecard

async function scorecard() {
  const [meta, scores] = await Promise.all([load("meta"), load("scores")]);
  if (!meta) return;
  $("status").replaceWith(statusPanel(meta));
  const rows = rowsOf(scores);
  const state = { variable: "rain_hourly", metric: "mae", threshold: (meta.rain_thresholds_mm_per_hour || [0.1])[0] };
  const controls = $("controls"), chart = $("lead-chart"), cmp = $("comparisons"), hours = $("hour-lead-chart"), extra = $("secondary");
  const draw = () => {
    const isRainEvent = ["brier", "ets", "pod", "far", "csi"].includes(state.metric);
    if (isRainEvent && state.variable !== "rain_hourly") state.metric = "mae";
    controls.replaceChildren(
      select("v", "Variable", Object.entries(VARIABLES).map(([k, v]) => [k, v.label]), state.variable),
      select("m", "Score", Object.entries(METRICS).filter(([k]) => state.variable === "rain_hourly" || !["brier", "ets", "pod", "far", "csi"].includes(k)).map(([k, v]) => [k, v.label]), state.metric),
      ...(["brier", "ets", "pod", "far", "csi"].includes(state.metric) ? [select("t", "Rain in the hour at least", meta.rain_thresholds_mm_per_hour.map((t) => [t, `${t} mm`]), state.threshold)] : []),
    );
    controls.querySelector("#v").onchange = (e) => { state.variable = e.target.value; draw(); };
    controls.querySelector("#m").onchange = (e) => { state.metric = e.target.value; draw(); };
    const t = controls.querySelector("#t");
    if (t) t.onchange = (e) => { state.threshold = Number(e.target.value); draw(); };
    $("lead-title").textContent = `${METRICS[state.metric].label}${unit(state.variable, state.metric)} by lead time, ${varLabel(state.variable).toLowerCase()}`;
    if (!rows.length) {
      chart.replaceChildren(emptyScores(meta, "Scores by lead time"));
      cmp.replaceChildren(emptyScores(meta, "Paired comparisons with intervals"));
      hours.replaceChildren(emptyScores(meta, "Scores by lead hour"));
      extra.replaceChildren(emptyScores(meta, "Models with a shorter archive"));
      return;
    }
    const thr = ["brier", "ets", "pod", "far", "csi"].includes(state.metric) ? state.threshold : null;
    const sel = pick(rows, { ...base, variable: state.variable, metric: state.metric, lead_kind: "day", against: null })
      .filter((r) => (thr === null ? r.threshold === null : r.threshold === thr));
    const leads = [...new Set(sel.map((r) => r.lead))].sort((a, b) => a - b);
    const lower = METRICS[state.metric].lower;
    chart.replaceChildren();
    const lc = el("div");
    chart.append(legend(MAIN.filter((id) => sel.some((r) => r.source === id))), lc);
    lineChart(lc, { series: series(sel, MAIN, "lead"), xs: leads, xFormat: (d) => `Day ${d}`, yFormat: (v) => fmt(v, state.metric === "brier" ? 3 : 2), zero: state.metric === "bias" });
    // Paired comparisons: only MAE and Brier have per-case values.
    const cm = state.metric === "brier" ? "brier" : "mae";
    const pairs = pick(rows, { ...base, variable: state.variable, metric: cm, lead_kind: "day" })
      .filter((r) => r.against !== null && !r.source.includes("@") && (cm === "mae" ? r.threshold === null : r.threshold === state.threshold));
    const combos = [...new Set(pairs.map((r) => `${r.source}|${r.against}`))];
    cmp.replaceChildren(
      el("p", { class: "note", text: `Difference in ${METRICS[cm].label.toLowerCase()} on the same cases: first source minus second. Below zero means the first source has the lower error. Interval: 95 percent, block bootstrap over days.` }),
      table([{ label: "Forecast", get: (c) => name(c.split("|")[0]) }, { label: "Against", get: (c) => name(c.split("|")[1]) },
        ...leads.map((d) => ({ label: `Day ${d}`, num: true, get: (c) => {
          const r = pairs.find((p) => `${p.source}|${p.against}` === c && p.lead === d);
          if (!r) return "";
          return el("div", { class: "cmp" }, el("div", { class: "num", text: fmt(r.value, 3) }),
            el("div", { class: "num note", text: `${fmt(r.low, 3)} to ${fmt(r.high, 3)}` }),
            el("div", { class: "verdict", text: verdict(r, true) }));
        } }))], combos),
    );
    const hsel = pick(rows, { ...base, variable: state.variable, metric: state.metric, lead_kind: "hour", against: null })
      .filter((r) => (thr === null ? r.threshold === null : r.threshold === thr));
    const hs = ["gfs_global", "ecmwf_ifs025", "persistence_issue", "persistence", "climatology"];
    const hleads = [...new Set(hsel.map((r) => r.lead))].sort((a, b) => a - b);
    hours.replaceChildren();
    const hc = el("div");
    hours.append(legend(hs.filter((id) => hsel.some((r) => r.source === id))), hc);
    $("hour-lead-title").textContent = `${METRICS[state.metric].label}${unit(state.variable, state.metric)} by lead hour`;
    lineChart(hc, { series: series(hsel, hs, "lead"), xs: hleads, xFormat: (h) => `${h} h`, directLabels: false, yFormat: (v) => fmt(v, state.metric === "brier" ? 3 : 2), zero: state.metric === "bias" });
    const sec = pick(rows, { ...base, variable: state.variable, metric: cm, lead_kind: "day", against: null })
      .filter((r) => ["ecmwf_aifs025_single", "ecmwf_ifs"].includes(r.source) && (cm === "mae" ? r.threshold === null : r.threshold === state.threshold));
    extra.replaceChildren(table([{ label: "Model", get: (r) => name(r.source) }, { label: "Lead", get: (r) => `Day ${r.lead}` },
      { label: METRICS[cm].short, num: true, get: (r) => `${fmt(r.value, 3)} [${fmt(r.low, 3)}, ${fmt(r.high, 3)}]` },
      { label: "Days", num: true, get: (r) => fmtInt(r.n_days) }, { label: "Pairs", num: true, get: (r) => fmtInt(r.n_pairs) }], sec));
  };
  draw();
}

// ------------------------------------------------------------------ hour of day and season

async function strata() {
  const [meta, scores] = await Promise.all([load("meta"), load("scores")]);
  if (!meta) return;
  const rows = rowsOf(scores);
  const state = { variable: "rain_hourly", metric: "mae", lead: 1 };
  const draw = () => {
    $("controls").replaceChildren(
      select("v", "Variable", Object.entries(VARIABLES).map(([k, v]) => [k, v.label]), state.variable),
      select("m", "Score", [["mae", METRICS.mae.label], ["bias", METRICS.bias.label], ["rmse", METRICS.rmse.label]], state.metric),
      select("d", "Lead time", (meta.lead_days || [1, 2, 3, 5, 7]).map((d) => [d, `Day ${d}`]), state.lead),
    );
    $("v").onchange = (e) => { state.variable = e.target.value; draw(); };
    $("m").onchange = (e) => { state.metric = e.target.value; draw(); };
    $("d").onchange = (e) => { state.lead = Number(e.target.value); draw(); };
    if (!rows.length) {
      $("hour-chart").replaceChildren(emptyScores(meta, "Scores by hour of day"));
      $("regime-chart").replaceChildren(emptyScores(meta, "Scores by monsoon phase"));
      return;
    }
    const q = { qc: "flags_removed", station: "all", variable: state.variable, metric: state.metric, lead_kind: "day", lead: state.lead, against: null, threshold: null };
    const byHour = pick(rows, { ...q, regime: "all" }).filter((r) => r.hour_local !== "all").map((r) => ({ ...r, hour: Number(r.hour_local) }));
    const hc = el("div");
    $("hour-chart").replaceChildren(legend(MAIN.filter((id) => byHour.some((r) => r.source === id))), hc);
    lineChart(hc, { series: series(byHour, MAIN, "hour"), xs: [...Array(24).keys()], xFormat: (h) => `${String(h).padStart(2, "0")}:00`, zero: state.metric === "bias" });
    const byRegime = pick(rows, { ...q, hour_local: "all" }).filter((r) => r.regime !== "all");
    const rc = el("div");
    $("regime-chart").replaceChildren(legend(MAIN.filter((id) => byRegime.some((r) => r.source === id))), rc);
    lineChart(rc, { series: series(byRegime, MAIN, "regime"), xs: Object.keys(REGIMES), xFormat: (k) => REGIME_SHORT[k], connect: false, directLabels: false, zero: state.metric === "bias" });
  };
  draw();
}

// ------------------------------------------------------------------ stations

async function stations() {
  const [st, bm, scores, meta] = await Promise.all([load("stations"), load("basemap"), load("scores"), load("meta")]);
  if (!st || !bm) return;
  const rows = rowsOf(scores);
  const models = Object.keys(st.cells || {});
  const state = { model: models.includes("ecmwf_ifs025") ? "ecmwf_ifs025" : models[0], rule: (meta && meta.cell_rule) || "nearest", variable: "all", view: "island" };
  const qs = new URLSearchParams(location.search);  // shareable views, for example ?rule=land
  const allowed = { model: models, rule: ["nearest", "land"], variable: ["all", ...Object.keys(VARIABLES)], view: Object.keys(VIEWS) };
  for (const [k, ok] of Object.entries(allowed)) if (ok.includes(qs.get(k))) state[k] = qs.get(k);
  const draw = () => {
    $("controls").replaceChildren(
      select("mo", "Model grid", models.map((m) => [m, name(m)]), state.model),
      select("ru", "Cell rule", [["nearest", "Nearest cell"], ["land", "Land cell"]].map(([k, t]) => [k, k === ((meta && meta.cell_rule) || "nearest") ? `${t} (main)` : `${t} (check)`]), state.rule),
      select("va", "Stations", [["all", "All"], ...Object.entries(VARIABLES).map(([k, v]) => [k, v.label])], state.variable),
      select("vw", "Map", Object.entries(VIEWS).map(([k, v]) => [k, v.label]), state.view),
    );
    $("vw").onchange = (e) => { state.view = e.target.value; draw(); };
    $("mo").onchange = (e) => { state.model = e.target.value; draw(); };
    $("ru").onchange = (e) => { state.rule = e.target.value; draw(); };
    $("va").onchange = (e) => { state.variable = e.target.value; draw(); };
    const list = st.stations.filter((s) => state.variable === "all" || s.variables.includes(state.variable));
    const out = stationMap($("map"), { basemap: bm, stations: list, cells: st.cells, cellSize: st.cell_size_deg, model: state.model, rule: state.rule, view: state.view });
    const other = state.rule === "land" ? "nearest" : "land";
    const a = (st.cells[state.model] || {})[state.rule] || {}, b = (st.cells[state.model] || {})[other] || {};
    const differ = list.filter((s) => a[s.key] && b[s.key] && a[s.key].join() !== b[s.key].join()).length;
    $("map-note").textContent = `${list.length} stations use ${out.cellsUsed} cells of the ${name(state.model)} grid under the ${state.rule} rule. ${differ} of them get a different cell under the ${other} rule. Circles are network stations, squares are airports; dashed squares are grid cells. Coastline from Natural Earth at 1:10 million, so recent reclaimed land is missing.`;
    $("station-table").replaceChildren(table([
      { label: "Station", get: (s) => s.id }, { label: "Name", get: (s) => s.name },
      { label: "Network", get: (s) => (s.network === "isd" ? "Airport (ISD)" : "data.gov.sg") },
      { label: "Measures", get: (s) => s.variables.map((v) => VARIABLES[v].label).join(", ") },
      { label: "Lat", num: true, get: (s) => s.lat.toFixed(3) }, { label: "Lon", num: true, get: (s) => s.lon.toFixed(3) },
      ...(rows.length ? [{ label: "MAE day 1", num: true, get: (s) => {
        const r = rows.find((x) => x.station === s.key && x.metric === "mae" && x.lead === 1 && x.lead_kind === "day" && x.source === "ecmwf_ifs025" && x.against === null);
        return r ? fmt(r.value) : "";
      } }] : []),
    ], list));
  };
  draw();
}

// ------------------------------------------------------------------ observations

async function observationsPage() {
  const [cov, qc, di, meta] = await Promise.all([load("coverage"), load("qc"), load("diurnal"), load("meta")]);
  if (meta) $("status").replaceWith(statusPanel(meta));
  if (cov) {
    const vars = Object.keys(cov.variables);
    const state = { variable: vars[0] };
    const draw = () => {
      $("cov-controls").replaceChildren(select("cv", "Variable", vars.map((v) => [v, VARIABLES[v].label]), state.variable));
      $("cv").onchange = (e) => { state.variable = e.target.value; draw(); };
      const c = cov.variables[state.variable];
      heatmap($("coverage"), { rows: c.stations, cols: c.months, values: c.share_usable, rowLabel: (k) => k.split(":")[1], head: "Share of hours usable" });
      $("cov-note").textContent = `${fmtInt(c.total_usable_hours)} usable station-hours of ${fmtInt(c.total_hours_present)} present. Usable means complete and not flagged by quality control.`;
    };
    draw();
  }
  if (qc) {
    const agg = {};
    for (const f of qc.flags) { const k = `${f.source}|${f.variable}|${f.check}`; agg[k] = (agg[k] || 0) + f.flags; }
    $("qc").replaceChildren(table([
      { label: "Source", get: (k) => (k.split("|")[0] === "isd" ? "Airports (ISD)" : "data.gov.sg") },
      { label: "Variable", get: (k) => k.split("|")[1] }, { label: "Check", get: (k) => k.split("|")[2].replace("_", " ") },
      { label: "Flags", num: true, get: (k) => fmtInt(agg[k]) }], Object.keys(agg).sort()));
  }
  if (di) {
    const ids = ["all", ...Object.keys(REGIMES)];
    const col = { all: "var(--ink)", northeast_monsoon: "var(--s1)", inter_monsoon_1: "var(--s2)", southwest_monsoon: "var(--s3)", inter_monsoon_2: "var(--s4)" };
    const lab = (k) => (k === "all" ? "All months" : REGIMES[k]);
    const s = ids.filter((k) => di.by_regime[k]).map((k) => ({ id: k, label: lab(k), colour: col[k], dash: k === "all" ? "6 4" : null,
      points: di.by_regime[k].share_wet.map((v, h) => ({ x: h, y: v * 100, n: di.by_regime[k].station_hours[h] })) }));
    const host = el("div");
    $("diurnal").replaceChildren(legend(ids.filter((k) => di.by_regime[k]), { colour: (k) => col[k], label: lab, dash: (k) => (k === "all" ? "6 4" : null) }), host);
    lineChart(host, { series: s, xs: [...Array(24).keys()], xFormat: (h) => `${String(h).padStart(2, "0")}:00`, yFormat: (v) => `${fmt(v, 0)}%`, directLabels: false });
    $("diurnal-note").textContent = `Share of complete station-hours with at least ${di.threshold_mm} mm, by local hour (Singapore time). This describes the observations only; it is not a forecast score.`;
  }
}


// ------------------------------------------------------------------ case studies

function profile(host, snd) {
  // Temperature and dew point against pressure, log scale, 1000 to 100 hPa.
  host.replaceChildren();
  host.classList.add("chart");
  const W = Math.max(280, Math.round(host.clientWidth || 360)), H = 340, m = { t: 10, r: 12, b: 30, l: 46 };
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Sounding profile");
  host.append(svg);
  const lv = snd.levels.filter((l) => l.p && l.p <= 1015);
  const ts = lv.flatMap((l) => [l.t, l.td]).filter((v) => v !== null);
  if (!ts.length) { host.replaceChildren(el("div", { class: "empty", text: "No temperatures in this sounding." })); return; }
  const lo = Math.floor(Math.min(...ts) / 10) * 10, hi = Math.ceil(Math.max(...ts) / 10) * 10;
  const X = (t) => m.l + ((t - lo) / (hi - lo)) * (W - m.l - m.r);
  const Y = (p) => m.t + (Math.log(1015 / p) / Math.log(1015 / 100)) * (H - m.t - m.b);
  const add = (tag, attrs) => { const n = document.createElementNS(svgNS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); svg.append(n); return n; };
  for (const p of [1000, 850, 700, 500, 300, 200, 100]) {
    add("line", { class: "grid-line", x1: m.l, x2: W - m.r, y1: Y(p), y2: Y(p) });
    add("text", { x: m.l - 6, y: Y(p) + 4, "text-anchor": "end", class: "tick" }).textContent = `${p}`;
  }
  for (let t = lo; t <= hi; t += 20) add("text", { x: X(t), y: H - 10, "text-anchor": "middle", class: "tick" }).textContent = `${t}°`;
  const line = (key, colour, dash) => {
    const pts = lv.filter((l) => l[key] !== null);
    if (pts.length > 1) add("path", { d: pts.map((l, i) => `${i ? "L" : "M"}${X(l[key]).toFixed(1)},${Y(l.p).toFixed(1)}`).join(""), fill: "none", stroke: colour, "stroke-width": 2, "stroke-dasharray": dash || "none" });
  };
  line("t", "var(--s8)");
  line("td", "var(--s3)", "5 3");
}

async function casesPage() {
  const index = await load("cases/index");
  const host = $("cases");
  if (!index || !index.length) return;
  const qs = new URLSearchParams(location.search);
  const state = { id: index.some((c) => c.id === qs.get("case")) ? qs.get("case") : index[0].id };
  const [st, bm] = await Promise.all([load("stations"), load("basemap")]);
  const draw = async () => {
    const c = await load(`cases/${state.id}`);
    host.replaceChildren();
    const sel = select("cs", "Event", index.map((x) => [x.id, x.title]), state.id);
    host.append(el("div", { class: "controls" }, sel));
    $("cs").onchange = (e) => { state.id = e.target.value; history.replaceState(null, "", `?case=${state.id}`); draw(); };
    if (!c) return;
    host.append(el("h2", { text: c.title, style: "margin-top:8px" }));
    host.append(el("p", { class: "note", text: `Window ${c.window_local[0]} to ${c.window_local[1]}, Singapore time.` }));
    const refs = el("p", { class: "note" });
    c.sources.forEach((u, i) => { refs.append(el("a", { href: u, text: `Report ${i + 1}`, rel: "noopener" })); if (i < c.sources.length - 1) refs.append(document.createTextNode(" · ")); });
    host.append(refs);
    const rain = c.observed.rain_hourly;
    const xs = rain.map((r) => r.t);
    const grid = el("div", { class: "grid two" });
    const rc = el("div"), wc = el("div");
    grid.append(el("section", { class: "card" }, el("span", { class: "label", text: "Rain in the hour, network mean and wettest gauge (mm)" }), legend(["mean", "max"], { colour: (k) => (k === "mean" ? "var(--ink)" : "var(--s1)"), label: (k) => (k === "mean" ? "Network mean" : "Wettest gauge"), dash: () => null }), rc));
    grid.append(el("section", { class: "card" }, el("span", { class: "label", text: "Gauges with rain in the hour" }), wc));
    host.append(grid);
    const fmtT = (t) => t.slice(5, 16).replace("-", "/");
    lineChart(rc, { series: [
      { id: "mean", label: "Network mean", colour: "var(--ink)", points: rain.map((r) => ({ x: r.t, y: r.mean, n: r.n })) },
      { id: "max", label: "Wettest gauge", colour: "var(--s1)", points: rain.map((r) => ({ x: r.t, y: r.max })) },
    ], xs, xFormat: fmtT, directLabels: false });
    lineChart(wc, { series: [{ id: "wet", label: "Gauges wet", colour: "var(--ink)", points: rain.map((r) => ({ x: r.t, y: r.wet, n: r.n })) }], xs, xFormat: fmtT, yFormat: (v) => fmt(v, 0), directLabels: false });
    if (c.forecasts_included && c.forecasts.rain_hourly) {
      const fc = el("div");
      host.append(el("section", { class: "card", style: "margin-top:20px" }, el("span", { class: "label", text: "Forecast network-mean rain by lead day, against the gauges" }), fc));
      const ser = [{ id: "obs", label: "Gauges", colour: "var(--ink)", points: rain.map((r) => ({ x: r.t, y: r.mean })) }];
      for (const [src, leads] of Object.entries(c.forecasts.rain_hourly)) {
        if (!["gfs_global", "ecmwf_ifs025"].includes(src)) continue;
        for (const [lead, pts] of Object.entries(leads)) ser.push({ id: `${src}-${lead}`, label: `${name(src)}, day ${lead}`, colour: colour(src), dash: lead === "1" ? null : lead === "3" ? "6 4" : "2 3", points: pts.map((p) => ({ x: p.t, y: p.mean })) });
      }
      lineChart(fc, { series: ser, xs, xFormat: fmtT, directLabels: false });
    } else {
      host.append(el("div", { class: "empty", style: "margin-top:20px", text: "What each forecast said appears here after the verification protocol is fixed. No forecast has been looked at for this event." }));
    }
    const lower = el("div", { class: "grid two", style: "margin-top:20px" });
    const mapHost = el("div"), sndHost = el("div");
    lower.append(el("section", { class: "card" }, el("span", { class: "label", text: "Event total at each gauge (mm)" }), mapHost));
    const snd = c.soundings.find((s) => s.before_event) || c.soundings[0];
    lower.append(el("section", { class: "card" }, el("span", { class: "label", text: snd ? `Changi sounding ${snd.time_utc.slice(0, 16).replace("T", " ")} UTC${snd.before_event ? ", last before the event" : ""}` : "Changi sounding" }),
      legend(["t", "td"], { colour: (k) => (k === "t" ? "var(--s8)" : "var(--s3)"), label: (k) => (k === "t" ? "Temperature" : "Dew point"), dash: (k) => (k === "td" ? "5 3" : null) }), sndHost));
    host.append(lower);
    if (st && bm) {
      const totals = Object.fromEntries(c.observed.rain_totals.map((r) => [r.station, r.mm]));
      const maxT = Math.max(1, ...Object.values(totals));
      const ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
      const gauges = st.stations.filter((s) => totals[s.key] !== undefined);
      stationMap(mapHost, { basemap: bm, stations: gauges, cells: {}, model: "", rule: "", view: "island",
        colourBy: (s) => ramp[Math.min(ramp.length - 1, Math.floor((totals[s.key] / maxT) * ramp.length))] });
      mapHost.append(el("p", { class: "note", text: `Darkest: ${fmt(maxT, 0)} mm. Gauges with complete hours only.` }));
    }
    if (snd) profile(sndHost, snd);
  };
  draw();
}

// ------------------------------------------------------------------ boot

const pages = { scorecard, strata, stations, observations: observationsPage, cases: casesPage };
const footLimits = document.getElementById("limits");
if (footLimits) footLimits.replaceWith(limitsPanel());
if (pages[page]) pages[page]();
