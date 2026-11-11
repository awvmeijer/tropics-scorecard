// Tropics Scorecard dashboard. Static: every number comes from data/*.json, written by
// `python -m tropics_scorecard.export`. No dependencies.

const NS = "http://www.w3.org/2000/svg";

// Colour follows the entity, never its rank. Baselines are dashed as a second cue.
export const SOURCES = {
  gfs_global: { label: "GFS", slot: 1 },
  ecmwf_ifs025: { label: "ECMWF IFS 0.25°", slot: 2 },
  persistence: { label: "Persistence", slot: 3, dash: "6 4" },
  climatology: { label: "Climatology", slot: 4, dash: "2 3" },
  persistence_issue: { label: "Persistence at issue", slot: 8, dash: "6 4" },
  ecmwf_aifs025_single: { label: "ECMWF AIFS 0.25°", slot: 5 },
  ecmwf_ifs: { label: "ECMWF IFS 9 km", slot: 7 },
};
export const MAIN = ["gfs_global", "ecmwf_ifs025", "persistence", "climatology"];
export const VARIABLES = {
  rain_hourly: { label: "Hourly rain", unit: "mm" },
  temperature_2m: { label: "Temperature at 2 m", unit: "°C" },
  wind_speed_10m: { label: "Wind speed at 10 m", unit: "m/s" },
};
export const METRICS = {
  mae: { label: "Mean absolute error", short: "MAE", lower: true },
  rmse: { label: "Root mean square error", short: "RMSE", lower: true },
  bias: { label: "Mean error (bias)", short: "Bias", lower: null },
  brier: { label: "Brier score", short: "Brier", lower: true },
  ets: { label: "Equitable threat score", short: "ETS", lower: false },
  pod: { label: "Probability of detection", short: "POD", lower: false },
  far: { label: "False alarm ratio", short: "FAR", lower: true },
  csi: { label: "Critical success index", short: "CSI", lower: false },
};
export const REGIME_SHORT = {
  northeast_monsoon: "NE monsoon", inter_monsoon_1: "Mar to May", southwest_monsoon: "SW monsoon", inter_monsoon_2: "Oct to Nov",
};
export const REGIMES = {
  northeast_monsoon: "Northeast monsoon",
  inter_monsoon_1: "Inter-monsoon, Mar to May",
  southwest_monsoon: "Southwest monsoon",
  inter_monsoon_2: "Inter-monsoon, Oct to Nov",
};

const colour = (id) => `var(--s${(SOURCES[id] || { slot: 6 }).slot})`;
const label = (id) => (SOURCES[id] ? SOURCES[id].label : id.replace("@", " with cell rule "));

// ------------------------------------------------------------------ data

const cache = {};
export async function load(name) {
  if (!cache[name]) {
    cache[name] = fetch(`data/${name}.json`, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  }
  return cache[name];
}

export function rowsOf(scores) {
  if (!scores || !scores.columns || !scores.columns.length) return [];
  return scores.rows.map((r) => Object.fromEntries(scores.columns.map((c, i) => [c, r[i]])));
}

export function pick(rows, q) {
  return rows.filter((r) => Object.entries(q).every(([k, v]) => (v === undefined ? true : r[k] === v)));
}

// ------------------------------------------------------------------ small DOM helpers

export function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const k of kids) if (k !== null && k !== undefined) n.append(k);
  return n;
}

function sv(tag, attrs = {}, parent) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) n.setAttribute(k, v);
  if (parent) parent.append(n);
  return n;
}

export const fmt = (v, d = 2) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
  const s = Number(v).toFixed(d);
  return /^-0\.?0*$/.test(s) ? s.slice(1) : s;  // no "-0.000"
};
export const fmtInt = (v) => (v === null || v === undefined ? "n/a" : Number(v).toLocaleString("en-GB"));

function ticks(lo, hi, n = 5) {
  if (!(hi > lo)) return [lo];
  const raw = (hi - lo) / n;
  const p = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw) || raw;
  const out = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + step * 1e-9; t += step) out.push(+t.toFixed(10));
  return out;
}

// ------------------------------------------------------------------ tooltip

function tooltip(host) {
  const tip = el("div", { class: "tip", role: "status" });
  tip.hidden = true;
  host.append(tip);
  return {
    show(x, y, head, rows) {
      tip.replaceChildren(el("div", { class: "t-head", text: head }));
      for (const r of rows) {
        const key = document.createElementNS(NS, "svg");
        key.setAttribute("viewBox", "0 0 14 4");
        key.setAttribute("width", "14");
        key.setAttribute("height", "4");
        if (r.colour) sv("line", { x1: 0, y1: 2, x2: 14, y2: 2, stroke: r.colour, "stroke-width": 3, "stroke-dasharray": r.dash || null }, key);
        tip.append(el("div", { class: "t-row" }, key, el("b", { text: r.value }), el("span", { text: r.label })));
      }
      tip.hidden = false;
      const box = host.getBoundingClientRect();
      const w = tip.offsetWidth;
      const left = Math.min(Math.max(0, x + 14), box.width - w);
      tip.style.left = `${left}px`;
      tip.style.top = `${Math.max(0, y - 10)}px`;
    },
    hide() { tip.hidden = true; },
  };
}

// ------------------------------------------------------------------ legend

export function legend(ids, opts = {}) {
  const box = el("div", { class: "legend", "aria-label": "Legend" });
  for (const id of ids) {
    const key = document.createElementNS(NS, "svg");
    key.setAttribute("viewBox", "0 0 22 10");
    sv("line", { x1: 1, y1: 5, x2: 21, y2: 5, stroke: opts.colour ? opts.colour(id) : colour(id), "stroke-width": 2.5,
      "stroke-dasharray": opts.dash ? opts.dash(id) : (SOURCES[id] || {}).dash || null, "stroke-linecap": "round" }, key);
    box.append(el("span", { class: "key" }, key, document.createTextNode(opts.label ? opts.label(id) : label(id))));
  }
  return box;
}

// ------------------------------------------------------------------ line chart with intervals

/**
 * series: [{ id, label, colour, dash, points: [{ x, y, lo, hi, n }] }]
 * xs: ordered x values; xFormat, yFormat; yLabel; zero: draw a zero line.
 */
export function lineChart(host, { series, xs, xFormat = String, yFormat = (v) => fmt(v), yLabel = "", zero = false, height = 300, directLabels = true, connect = true }) {
  host.replaceChildren();
  host.classList.add("chart");
  // Draw at the container's own width so text stays at its set size.
  const W = Math.max(300, Math.round(host.clientWidth || 640));
  const H = Math.round(Math.min(height, Math.max(220, W * 0.55)));
  const m = { t: 14, r: directLabels ? Math.min(140, W * 0.28) : 16, b: 34, l: 52 };
  if (!host.dataset.watch) {
    host.dataset.watch = "1";
    let last = W, timer = null;
    new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => { if (Math.abs(host.clientWidth - last) > 24 && host._redraw) { last = host.clientWidth; host._redraw(); } }, 150);
    }).observe(host);
  }
  host._redraw = () => lineChart(host, arguments[1]);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": yLabel });
  host.append(svg);
  const all = series.flatMap((s) => s.points.flatMap((p) => [p.y, p.lo, p.hi])).filter((v) => v !== null && v !== undefined);
  if (!all.length) { host.replaceChildren(el("div", { class: "empty", text: "No values for this selection." })); return; }
  let lo = Math.min(...all), hi = Math.max(...all);
  if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.08;
  lo -= pad; hi += pad;
  const xi = (x) => xs.indexOf(x);
  // Categories (connect = false) sit in the middle of equal slots; ordered x runs edge to edge.
  const X = (x) => m.l + (!connect ? (xi(x) + 0.5) / xs.length : xs.length === 1 ? 0.5 : xi(x) / (xs.length - 1)) * (W - m.l - m.r);
  const Y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  for (const t of ticks(lo, hi)) {
    sv("line", { class: "grid-line", x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, svg);
    sv("text", { x: m.l - 8, y: Y(t) + 4, "text-anchor": "end", class: "tick" }, svg).textContent = yFormat(t);
  }
  if (zero && lo < 0 && hi > 0) sv("line", { class: "axis-line", x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0) }, svg);
  const longest = Math.max(...xs.map((x) => String(xFormat(x)).length));
  const every = Math.ceil(xs.length / Math.max(2, Math.floor((W - m.l - m.r) / (7.5 * longest + 16))));
  xs.forEach((x, i) => {
    if (i % every) return;
    sv("text", { x: X(x), y: H - m.b + 18, "text-anchor": "middle", class: "tick" }, svg).textContent = xFormat(x);
  });
  sv("line", { class: "axis-line", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, svg);

  for (const s of series) {
    const pts = s.points.filter((p) => p.y !== null && p.y !== undefined).sort((a, b) => xi(a.x) - xi(b.x));
    const banded = pts.filter((p) => p.lo !== null && p.lo !== undefined);
    if (!connect) {
      const k = series.indexOf(s), off = (k - (series.length - 1) / 2) * 7;
      for (const p of banded) sv("line", { x1: X(p.x) + off, x2: X(p.x) + off, y1: Y(p.lo), y2: Y(p.hi), stroke: s.colour, "stroke-width": 2, "stroke-linecap": "round" }, svg);
      for (const p of pts) sv("circle", { cx: X(p.x) + off, cy: Y(p.y), r: 4, fill: s.colour, stroke: "#fff", "stroke-width": 2 }, svg);
      continue;
    }
    if (banded.length > 1) {
      const d = banded.map((p, i) => `${i ? "L" : "M"}${X(p.x)},${Y(p.hi)}`).join("") +
        banded.slice().reverse().map((p) => `L${X(p.x)},${Y(p.lo)}`).join("") + "Z";
      sv("path", { d, fill: s.colour, "fill-opacity": 0.13, stroke: "none" }, svg);
    } else if (banded.length === 1) {
      const p = banded[0];
      sv("line", { x1: X(p.x), x2: X(p.x), y1: Y(p.lo), y2: Y(p.hi), stroke: s.colour, "stroke-width": 2 }, svg);
    }
    if (pts.length > 1) {
      sv("path", { d: pts.map((p, i) => `${i ? "L" : "M"}${X(p.x)},${Y(p.y)}`).join(""), fill: "none", stroke: s.colour,
        "stroke-width": 2, "stroke-dasharray": s.dash || null, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    }
    if (pts.length <= 8) for (const p of pts) sv("circle", { cx: X(p.x), cy: Y(p.y), r: 4, fill: s.colour, stroke: "#fff", "stroke-width": 2 }, svg);
  }
  if (connect && directLabels && series.length <= 4) {
    const ends = series.map((s) => {
      const pts = s.points.filter((p) => p.y !== null && p.y !== undefined).sort((a, b) => xi(a.x) - xi(b.x));
      return pts.length ? { s, y: Y(pts[pts.length - 1].y) } : null;
    }).filter(Boolean).sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;
    for (const e of ends) {
      sv("text", { x: W - m.r + 10, y: e.y + 4, class: "series-label" }, svg).textContent = e.s.label;
    }
  }
  // Crosshair: snaps to the nearest x and lists every series there.
  const hair = sv("line", { class: "hair", y1: m.t, y2: H - m.b, visibility: "hidden" }, svg);
  const tip = tooltip(host);
  const hit = sv("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent", tabindex: 0 }, svg);
  const at = (clientX) => {
    const b = svg.getBoundingClientRect();
    const sx = ((clientX - b.left) / b.width) * W;
    let best = xs[0], dist = Infinity;
    for (const x of xs) { const d = Math.abs(X(x) - sx); if (d < dist) { dist = d; best = x; } }
    return best;
  };
  const show = (x) => {
    hair.setAttribute("x1", X(x)); hair.setAttribute("x2", X(x)); hair.setAttribute("visibility", "visible");
    const rows = series.map((s) => {
      const p = s.points.find((q) => q.x === x);
      if (!p || p.y === null || p.y === undefined) return null;
      const iv = p.lo !== null && p.lo !== undefined ? ` (${yFormat(p.lo)} to ${yFormat(p.hi)})` : "";
      return { colour: s.colour, dash: s.dash, value: yFormat(p.y) + iv, label: s.label + (p.n ? `, n ${fmtInt(p.n)}` : "") };
    }).filter(Boolean);
    const b = svg.getBoundingClientRect(), hb = host.getBoundingClientRect();
    tip.show((X(x) / W) * b.width + (b.left - hb.left), (m.t / H) * b.height, xFormat(x), rows);
  };
  hit.addEventListener("pointermove", (e) => show(at(e.clientX)));
  hit.addEventListener("pointerleave", () => { hair.setAttribute("visibility", "hidden"); tip.hide(); });
  let kx = 0;
  hit.addEventListener("focus", () => show(xs[kx]));
  hit.addEventListener("blur", () => { hair.setAttribute("visibility", "hidden"); tip.hide(); });
  hit.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") kx = Math.min(xs.length - 1, kx + 1);
    else if (e.key === "ArrowLeft") kx = Math.max(0, kx - 1);
    else return;
    e.preventDefault(); show(xs[kx]);
  });
}

// ------------------------------------------------------------------ heatmap

export function heatmap(host, { rows, cols, values, rowLabel = (r) => r, colLabel = (c) => c, valueFormat = (v) => fmt(v * 100, 0) + "%", head = "" }) {
  host.replaceChildren();
  host.classList.add("chart");
  const W = 900, gap = 1, ch = 6, m = { t: 22, l: 64, r: 8, b: 8 };
  const cw = Math.max(2, (W - m.l - m.r) / cols.length - gap);
  const H = m.t + rows.length * (ch + gap) + m.b;
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": head });
  host.append(svg);
  // Sequential, one hue light to dark. Empty months are the neutral surface.
  const ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
  // Missing is the neutral surface; 0 percent usable is data, drawn as the first step with a red edge.
  const fill = (v) => (v === null || v === undefined ? "var(--none)" : ramp[Math.min(ramp.length - 1, Math.floor(v * ramp.length))]);
  cols.forEach((c, j) => {
    if (j === 0 || c.endsWith("-01")) sv("text", { x: m.l + j * (cw + gap), y: 12, class: "tick" }, svg).textContent = j === 0 ? c : c.slice(0, 4);
  });
  const tip = tooltip(host);
  rows.forEach((r, i) => {
    sv("text", { x: m.l - 6, y: m.t + i * (ch + gap) + ch - 1, "text-anchor": "end", class: "tick", style: "font-size:7px" }, svg).textContent = rows.length > 40 && i % 2 ? "" : rowLabel(r);
    cols.forEach((c, j) => {
      const v = values[i][j];
      const rect = sv("rect", { x: m.l + j * (cw + gap), y: m.t + i * (ch + gap), width: cw, height: ch, rx: 1, fill: fill(v),
        stroke: v === 0 ? "var(--s8)" : null, "stroke-width": v === 0 ? 1 : null }, svg);
      rect.addEventListener("pointermove", (e) => {
        const hb = host.getBoundingClientRect();
        tip.show(e.clientX - hb.left, e.clientY - hb.top - 40, `${rowLabel(r)} · ${colLabel(c)}`, [{ value: v === null || v === undefined ? "no data" : valueFormat(v), label: "of hours usable" }]);
      });
      rect.addEventListener("pointerleave", () => tip.hide());
    });
  });
  const key = el("div", { class: "legend" });
  const steps = document.createElementNS(NS, "svg");
  steps.setAttribute("viewBox", `0 0 ${ramp.length * 16 + 16} 10`);
  steps.style.width = `${ramp.length * 16 + 16}px`;
  sv("rect", { x: 0, y: 0, width: 14, height: 10, rx: 2, fill: "var(--none)" }, steps);
  ramp.forEach((c, i) => sv("rect", { x: 16 + i * 16, y: 0, width: 14, height: 10, rx: 2, fill: c }, steps));
  key.append(el("span", { class: "key" }, el("span", { text: "No data" }), steps, el("span", { text: "100% of hours usable. Red edge: data present, none usable" })));
  host.append(key);
}

// ------------------------------------------------------------------ map

export const VIEWS = {
  island: { label: "Singapore", south: 1.13, north: 1.54, west: 103.55, east: 104.15 },
  region: { label: "Region", south: 0.5, north: 2.6, west: 102.4, east: 105.1 },
};

export function stationMap(host, { basemap, stations, cells, cellSize, model, rule, colourBy, view = "island" }) {
  host.replaceChildren();
  host.classList.add("chart");
  const b = VIEWS[view] || basemap.bbox;
  const k = Math.cos(((b.south + b.north) / 2) * Math.PI / 180);
  const W = 720, H = Math.round((W * (b.north - b.south)) / ((b.east - b.west) * k));
  const X = (lon) => ((lon - b.west) / (b.east - b.west)) * W;
  const Y = (lat) => ((b.north - lat) / (b.north - b.south)) * H;
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Station map" });
  host.append(svg);
  const clipId = `clip-${Math.random().toString(36).slice(2)}`;
  sv("rect", { x: 0, y: 0, width: W, height: H }, sv("clipPath", { id: clipId }, sv("defs", {}, svg)));
  sv("rect", { x: 0, y: 0, width: W, height: H, fill: "#fff", stroke: "var(--rule)" }, svg);
  const body = sv("g", { "clip-path": `url(#${clipId})` }, svg);
  for (const ring of basemap.rings) {
    sv("path", { d: ring.map(([x, y], i) => `${i ? "L" : "M"}${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join("") + "Z",
      fill: "var(--land)", stroke: "var(--coast)", "stroke-width": 0.8 }, body);
  }
  const tip = tooltip(host);
  const cellsFor = (cells[model] || {})[rule] || {};
  const used = new Map();
  for (const s of stations) { const c = cellsFor[s.key]; if (c) used.set(c.join(","), c); }
  // Grid cells: outline squares; stations joined to their cell with a hairline.
  const half = ((cellSize || {})[model] || 0.25) / 2;
  for (const [, [la, lo]] of used) {
    sv("rect", { x: X(lo - half), y: Y(la + half), width: X(lo + half) - X(lo - half), height: Y(la - half) - Y(la + half),
      fill: "none", stroke: "var(--ink-3)", "stroke-width": 1, "stroke-dasharray": "4 3" }, body);
    sv("circle", { cx: X(lo), cy: Y(la), r: 2.5, fill: "var(--ink-3)" }, body);
  }
  for (const s of stations) {
    const c = cellsFor[s.key];
    if (c) sv("line", { x1: X(s.lon), y1: Y(s.lat), x2: X(c[1]), y2: Y(c[0]), stroke: "var(--ink-3)", "stroke-width": 0.6, opacity: 0.7 }, body);
  }
  for (const s of stations) {
    const g = sv("g", { tabindex: 0 }, body);
    const fillC = colourBy ? colourBy(s) : "var(--ink)";
    // Coloured markers get a thin charcoal ring so the lightest steps stay visible on land.
    const ring = colourBy ? { stroke: "var(--ink-2)", "stroke-width": 0.8 } : { stroke: "#fff", "stroke-width": 1.5 };
    if (s.network === "isd") sv("rect", { x: X(s.lon) - 5, y: Y(s.lat) - 5, width: 10, height: 10, fill: fillC, ...ring }, g);
    else sv("circle", { cx: X(s.lon), cy: Y(s.lat), r: colourBy ? 5 : 4, fill: fillC, ...ring }, g);
    sv("circle", { cx: X(s.lon), cy: Y(s.lat), r: 12, fill: "transparent" }, g);
    const showTip = () => {
      const bb = svg.getBoundingClientRect(), hb = host.getBoundingClientRect();
      const c = cellsFor[s.key];
      tip.show((X(s.lon) / W) * bb.width + bb.left - hb.left, (Y(s.lat) / H) * bb.height + bb.top - hb.top - 20,
        `${s.id} · ${s.network === "isd" ? "airport" : "station"}`,
        [{ value: s.name, label: "" }, { value: s.variables.map((v) => (VARIABLES[v] || { label: v }).label).join(", "), label: "" },
          ...(c ? [{ value: `${c[0].toFixed(2)}°N ${c[1].toFixed(2)}°E`, label: "grid cell" }] : [])]);
    };
    g.addEventListener("pointerenter", showTip);
    g.addEventListener("focus", showTip);
    g.addEventListener("pointerleave", () => tip.hide());
    g.addEventListener("blur", () => tip.hide());
  }
  return { cellsUsed: used.size };
}

// ------------------------------------------------------------------ tables

export function table(columns, rows) {
  const t = el("table");
  const head = el("tr");
  for (const c of columns) head.append(el("th", { class: c.num ? "num" : null, text: c.label }));
  t.append(el("thead", {}, head));
  const body = el("tbody");
  for (const r of rows) {
    const tr = el("tr");
    for (const c of columns) {
      const v = c.get(r);
      tr.append(v instanceof Node ? el("td", { class: c.num ? "num" : null }, v) : el("td", { class: c.num ? "num" : null, text: v }));
    }
    body.append(tr);
  }
  t.append(body);
  return el("div", { class: "table-scroll" }, t);
}

// ------------------------------------------------------------------ status

export function statusPanel(meta) {
  const box = el("section", { class: "status", "aria-label": "Build status" });
  const metrics = Object.values(meta.metrics || {});
  const written = metrics.filter((s) => s === "written").length;
  box.append(el("h3", { text: meta.scored ? "Scores are in" : "No scores yet" }));
  box.append(el("p", { class: "note", text: meta.scored
    ? "Every score below was computed after the verification protocol was fixed."
    : "Scoring waits for two things: the verification protocol to be fixed, and the metric functions that compute every score. The data is downloading meanwhile." }));
  const grid = el("div", { class: "progress" });
  const add = (name, done, want) => {
    const pct = want ? Math.min(1, done / want) : 0;
    const bar = el("div", { class: "bar", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": want, "aria-valuenow": done, "aria-label": name });
    const fillEl = el("span");
    fillEl.style.width = `${(pct * 100).toFixed(1)}%`;
    bar.append(fillEl);
    grid.append(el("div", { class: "row" }, el("span", { class: "label", text: name }), bar, el("span", { class: "num", text: `${Math.round(pct * 100)}%` })));
  };
  add("Protocol fixed", meta.protocol_signed_off ? 1 : 0, 1);
  add(`Metric functions (${written} of ${metrics.length})`, written, metrics.length);
  for (const [name, d] of Object.entries(meta.downloads || {})) add(name, d.days_done, d.days_wanted);
  box.append(grid);
  box.append(el("p", { class: "note", text: `Data generated ${meta.generated.replace("T", " ").replace("+00:00", " UTC")}.` }));
  return box;
}

export const LIMITS = [
  "A rain gauge measures one point. A forecast is an average over a grid cell 9 to 28 km wide, so a forecast shows more light rain and less heavy rain than any gauge. Part of every low rain score comes from that mismatch, not from the forecast.",
  "Stations have errors. Tipping-bucket gauges catch less rain than falls in strong wind and very heavy rain, and no correction is applied.",
  "The test period is under three years: each monsoon phase appears two or three times. Differences smaller than their interval are reported as no detectable difference.",
  "Models with a shorter archive are scored on their own period and never pooled with the main table.",
  "This is a study of one region and one set of public archives. It is not a benchmark of record.",
];

export function limitsPanel(extra = []) {
  const box = el("aside", { class: "limits", "aria-label": "Limits" });
  box.append(el("span", { class: "label", text: "Limits" }));
  const ul = el("ul");
  for (const t of [...extra, ...LIMITS]) ul.append(el("li", { text: t }));
  box.append(ul);
  return box;
}
