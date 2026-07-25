/* Adaptive DCF Valuation Tool — dashboard front-end */
const STATE = { ticker: null, data: null, charts: {} };
const EXAMPLES = ["AAPL", "NVDA", "MSFT", "AMZN", "KO", "TSLA", "DIS", "PLTR"];

/* ---------- formatters ---------- */
const money = (x, d = 2) => (x == null || isNaN(x)) ? "—" : "$" + Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x, d = 1) => (x == null || isNaN(x)) ? "—" : (x * 100).toFixed(d) + "%";
const num = (x, d = 0) => (x == null || isNaN(x)) ? "—" : Number(x).toLocaleString("en-US", { maximumFractionDigits: d });
const mult = (x) => (x == null || isNaN(x)) ? "—" : x.toFixed(1) + "x";
const scoreColor = (s) => s >= 66 ? "var(--green)" : (s >= 46 ? "var(--amber)" : "var(--red)");
const scoreClass = (s) => s >= 66 ? "g" : (s >= 46 ? "a" : "r");

/* ---------- tabs ---------- */
function switchTab(t) {
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("active", el.dataset.tab === t));
  ["single", "hot", "backtest", "rank"].forEach(name => {
    const el = document.getElementById("tab-" + name);
    if (el) el.style.display = (name === t) ? "block" : "none";
  });
  if (t === "hot" && !STATE.hotLoaded) { STATE.hotLoaded = true; loadHotStocks(); }
}

/* ---------- init ---------- */
window.addEventListener("load", () => {
  const chips = document.getElementById("chips");
  chips.innerHTML = '<span class="muted" style="font-size:12px">Try:</span>';
  EXAMPLES.forEach(t => {
    const b = document.createElement("button"); b.className = "chip"; b.textContent = t;
    b.onclick = () => { document.getElementById("ticker").value = t; runValue(); };
    chips.appendChild(b);
  });
  document.getElementById("dlExcel").onclick = () => { if (STATE.ticker) window.location = `/api/export/excel?ticker=${STATE.ticker}`; };
  document.getElementById("dlPdf").onclick = () => { if (STATE.ticker) window.location = `/api/export/pdf?ticker=${STATE.ticker}`; };
});

/* ---------- run valuation ---------- */
async function runValue(overrides) {
  const ticker = document.getElementById("ticker").value.trim().toUpperCase();
  if (!ticker) return;
  STATE.ticker = ticker;
  show("loader", true); show("results", false); errBox("");
  document.getElementById("go").disabled = true;
  document.getElementById("loadmsg").textContent = overrides ? "Re-running with your assumptions…" : `Fetching live data & valuing ${ticker}…`;
  try {
    const body = { ticker, run_ai: document.getElementById("runai").checked };
    if (overrides) Object.assign(body, overrides);
    const res = await fetch("/api/value", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Valuation failed");
    STATE.data = data;
    render(data);
    show("results", true);
  } catch (e) {
    errBox(e.message);
  } finally {
    show("loader", false);
    document.getElementById("go").disabled = false;
  }
}
function resetAssum() { runValue(); }

/* ---------- master render ---------- */
function render(d) {
  const c = d.company, cls = d.classification, sc = d.scenarios, score = d.score;
  document.getElementById("coName").textContent = `${c.name} (${c.ticker})`;
  document.getElementById("coSub").textContent =
    [c.sector, c.industry].filter(Boolean).join(" · ") + (c.as_of ? ` · as of ${c.as_of}` : "");

  // badges
  const rc = { high: "g", medium: "a", low: "r" }[cls.dcf_reliability] || "";
  document.getElementById("coBadges").innerHTML =
    `<span class="badge">${cls.regime}</span>` +
    `<span class="badge ${rc}">DCF reliability: ${cls.dcf_reliability}</span>` +
    (cls.rule_of_40 != null ? `<span class="badge ${cls.rule_of_40 >= 40 ? 'g' : 'a'}">Rule of 40: ${cls.rule_of_40.toFixed(0)}</span>` : "") +
    (c.cash_runway_years != null ? `<span class="badge ${c.cash_runway_years >= 4 ? 'g' : 'r'}">Runway: ${c.cash_runway_years.toFixed(1)}y</span>` : "");

  // hero metrics
  const up = d.upside;
  document.getElementById("heroMetrics").innerHTML =
    metric("Price", money(c.price)) +
    metric("Base fair value", `<span style="color:var(--navy)">${money(d.base_fair_value)}</span>`) +
    metric("Upside", `<span class="${up >= 0 ? 'pos' : 'neg'}">${up == null ? '—' : (up >= 0 ? '+' : '') + pct(up, 0)}</span>`) +
    metric("WACC", pct(d.wacc.wacc));

  gauge(score.score, score.recommendation, score.confidence);
  rangebar(sc.bear_price, sc.base_price, sc.bull_price, c.price);
  scenarioCards(sc, c.price);
  fcfChart(sc.base.rows);
  mcChart(d.montecarlo);
  scoreBars(score);
  reverseBox(d.reverse);
  compsBox(d.comps, c.price);
  assumEditor(d.assumptions);
  document.getElementById("assumNotes").innerHTML = (d.assumptions.notes || []).map(n => "• " + n).join("<br>");
  sensBox(d.sensitivity, c.price);
  aiBox(d.ai);
  warnBox(d.warnings);
  document.getElementById("sourcesBox").innerHTML = "Sources: " + (d.sources || []).join(" · ");
}

function metric(k, v) { return `<div class="m"><div class="k">${k}</div><div class="v">${v}</div></div>`; }
function show(id, on) { document.getElementById(id).classList.toggle("on", on); }
function errBox(msg) { const e = document.getElementById("err"); e.textContent = msg; e.classList.toggle("on", !!msg); }

/* ---------- gauge ---------- */
function gauge(s, rec, conf) {
  const r = 54, circ = 2 * Math.PI * r, off = circ * (1 - s / 100), col = scoreColor(s);
  document.getElementById("gauge").innerHTML = `
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r="${r}" fill="none" stroke="var(--border)" stroke-width="13"/>
      <circle cx="70" cy="70" r="${r}" fill="none" stroke="${col}" stroke-width="13" stroke-linecap="round"
        stroke-dasharray="${circ}" stroke-dashoffset="${off}"/>
    </svg>
    <div style="margin-top:-96px;text-align:center">
      <div class="score-num" style="color:${col}">${s}</div>
      <div style="font-size:12px;color:var(--muted);margin-top:-4px">/ 100</div>
    </div>
    <div class="rec" style="color:${col};margin-top:44px">${rec}</div>
    <div class="conf">confidence: ${conf}</div>`;
}

/* ---------- scenario range bar ---------- */
function rangebar(bear, base, bull, price) {
  const el = document.getElementById("rangebar");
  if (bear == null || bull == null) { el.innerHTML = '<div class="muted">Per-share value unavailable.</div>'; return; }
  const lo = Math.min(bear, price || bear) * 0.94, hi = Math.max(bull, price || bull) * 1.06;
  const p = v => Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100));
  const dot = (v, lab, col) => `<div class="pt" style="left:${p(v)}%"><div>${lab}</div><div style="color:${col}">${money(v, 0)}</div><div class="dot" style="background:${col}"></div></div>`;
  let html = '<div class="track"></div>';
  html += dot(bear, "Bear", "var(--red)");
  html += dot(base, "Base", "var(--navy)");
  html += dot(bull, "Bull", "var(--green)");
  if (price) html += `<div class="price-marker" style="left:${p(price)}%">Price ${money(price, 0)}<div class="line"></div></div>`;
  el.innerHTML = html;
}
function scenarioCards(sc, price) {
  const card = (lab, v, col) => {
    const u = price ? (v / price - 1) : null;
    return `<div class="card" style="margin:0;box-shadow:none;border:1px solid var(--border);padding:14px">
      <div style="font-size:12px;color:var(--muted);font-weight:700">${lab.toUpperCase()}</div>
      <div style="font-size:22px;font-weight:800;color:${col}">${money(v)}</div>
      <div style="font-size:13px" class="${u >= 0 ? 'pos' : 'neg'}">${u == null ? '' : (u >= 0 ? '+' : '') + pct(u, 0) + ' vs price'}</div></div>`;
  };
  document.getElementById("scenarioCards").innerHTML =
    card("Bear", sc.bear_price, "var(--red)") + card("Base", sc.base_price, "var(--navy)") + card("Bull", sc.bull_price, "var(--green)");
}

/* ---------- charts ---------- */
function killChart(k) { if (STATE.charts[k]) { STATE.charts[k].destroy(); delete STATE.charts[k]; } }
function fcfChart(rows) {
  killChart("fcf");
  const ctx = document.getElementById("fcfChart");
  const labels = rows.map(r => "Yr " + r.year);
  STATE.charts.fcf = new Chart(ctx, {
    type: "bar",
    data: {
      labels, datasets: [
        { label: "Revenue ($mm)", data: rows.map(r => r.revenue), backgroundColor: "#cfe0f7", yAxisID: "y1", order: 2 },
        { label: "Unlevered FCFF ($mm)", data: rows.map(r => r.fcff), backgroundColor: rows.map(r => r.fcff >= 0 ? "#2e5fa3" : "#b3261e"), yAxisID: "y", order: 1 }
      ]
    },
    options: { responsive: true, plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { y: { position: "left", title: { display: true, text: "FCFF" } }, y1: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "Revenue" } } } }
  });
}
function mcChart(mc) {
  killChart("mc");
  const ctx = document.getElementById("mcChart");
  const bins = mc.hist_bins || [], counts = mc.hist_counts || [];
  const labels = counts.map((_, i) => money((bins[i] + bins[i + 1]) / 2, 0));
  const price = mc.price;
  const bg = counts.map((_, i) => (price && (bins[i] + bins[i + 1]) / 2 >= price) ? "#1b7f4b" : "#c96a63");
  STATE.charts.mc = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ label: "trials", data: counts, backgroundColor: bg, barPercentage: 1, categoryPercentage: 1 }] },
    options: { responsive: true, plugins: { legend: { display: false } },
      scales: { x: { ticks: { maxTicksLimit: 8, font: { size: 10 } } }, y: { display: false } } }
  });
  const pu = mc.prob_undervalued;
  document.getElementById("mcNote").innerHTML =
    `Median <b>${money(mc.median)}</b> · 10th–90th pct <b>${money(mc.p10)}–${money(mc.p90)}</b>` +
    (pu != null ? ` · <b style="color:${pu >= 0.5 ? 'var(--green)' : 'var(--red)'}">${pct(pu, 0)} of trials value it above today's price</b>` : "") +
    `<br><span class="muted">Green bars = above current price (undervalued outcomes).</span>`;
}

/* ---------- score bars ---------- */
function scoreBars(score) {
  document.getElementById("scoreHint").innerHTML =
    `Weighted for a <b>${STATE.data.classification.regime}</b> company — weights shift by regime so the DCF is trusted less where it's less reliable. Overall confidence: <b>${score.confidence}</b>.`;
  const order = ["valuation", "quality", "growth", "health", "momentum"];
  let html = "";
  order.forEach(k => {
    const v = score.subscores[k], w = score.weights[k];
    const col = v == null ? "var(--faint)" : scoreColor(v);
    html += `<div class="sbar"><div class="lab"><span><b>${k[0].toUpperCase() + k.slice(1)}</b> <span class="wt">weight ${pct(w, 0)}</span></span>
      <span style="font-weight:700;color:${col}">${v == null ? 'n/a' : v.toFixed(0)}</span></div>
      <div class="bar"><span style="width:${v == null ? 0 : v}%;background:${col}"></span></div></div>`;
  });
  html += `<div style="margin-top:10px;font-size:12.5px" class="muted">Drivers:</div><ul style="margin:4px 0 0;padding-left:18px;font-size:13px">` +
    (score.drivers || []).map(x => `<li>${x}</li>`).join("") + "</ul>";
  document.getElementById("scoreBars").innerHTML = html;
}

/* ---------- reverse & comps ---------- */
function reverseBox(rv) {
  document.getElementById("reverseBox").innerHTML =
    `<div style="font-size:14px">${rv.growth_verdict || "—"}</div>` +
    (rv.margin_verdict ? `<div style="font-size:14px;margin-top:8px" class="muted">${rv.margin_verdict}</div>` : "") +
    (rv.implied_avg_growth != null ?
      `<div class="metricline" style="margin-top:14px">
        ${metric("Market-implied growth", pct(rv.implied_avg_growth))}
        ${metric("Our base growth", pct(rv.base_avg_growth))}</div>` : "");
}
function compsBox(cp, price) {
  const m = cp.subject || {}, imp = cp.implied || {};
  const rows = [["P/E", m.pe, imp.pe], ["EV/EBITDA", m.ev_ebitda, imp.ev_ebitda], ["P/S", m.ps, imp.ps], ["EV/Sales", m.ev_sales, imp.ev_sales]];
  let html = `<div class="note" style="margin-top:0">${cp.benchmark_source}</div><table><tr><th>Multiple</th><th class="num">Current</th><th class="num">Implied value</th></tr>`;
  rows.forEach(([lab, cur, iv]) => { html += `<tr><td>${lab}</td><td class="num">${mult(cur)}</td><td class="num">${money(iv)}</td></tr>`; });
  html += `</table>`;
  if (cp.comps_fair_value != null) {
    const u = price ? cp.comps_fair_value / price - 1 : null;
    html += `<div style="margin-top:12px;font-size:14px">Comps fair value <b>${money(cp.comps_fair_value)}</b> ${u == null ? '' : `<span class="${u >= 0 ? 'pos' : 'neg'}">(${u >= 0 ? '+' : ''}${pct(u, 0)})</span>`}</div>`;
  }
  document.getElementById("compsBox").innerHTML = html;
}

/* ---------- assumptions editor ---------- */
function assumEditor(a) {
  // Percentage fields display as %s for usability, then convert to decimals on rerun.
  document.getElementById("assumEditor").innerHTML =
    fieldPct("start_growth", "Start rev growth %", a.start_growth) +
    fieldPct("target_margin", "Target op margin %", a.target_margin) +
    fieldPct("terminal_growth", "Terminal growth %", a.terminal_growth) +
    fieldNum("sales_to_capital", "Sales-to-capital", a.sales_to_capital, 0.1) +
    fieldNum("n_years", "Forecast years", a.n_years, 1) +
    fieldPct("tax_rate", "Tax rate %", a.tax_rate);
}
function fieldPct(key, lab, val) {
  return `<div class="field"><label>${lab}</label><input type="number" step="0.5" data-key="${key}" data-pct="1" value="${(val * 100).toFixed(2)}"></div>`;
}
function fieldNum(key, lab, val, step) {
  return `<div class="field"><label>${lab}</label><input type="number" step="${step}" data-key="${key}" data-pct="0" value="${val}"></div>`;
}
/* override collection converts % fields back to decimals */
function rerun() {
  const o = {};
  document.querySelectorAll("#assumEditor input").forEach(inp => {
    if (inp.value === "") return;
    let v = parseFloat(inp.value);
    if (inp.dataset.pct === "1") v = v / 100;
    o[inp.dataset.key] = v;
  });
  runValue(o);
}

/* ---------- sensitivity heatmap ---------- */
function sensBox(s, price) {
  const g = s.grid, wa = s.wacc_axis, ga = s.growth_axis;
  let html = '<table class="hm"><tr><th>WACC \\ g</th>';
  ga.forEach(gv => html += `<th>${pct(gv, 1)}</th>`);
  html += "</tr>";
  g.forEach((row, i) => {
    html += `<tr><th>${pct(wa[i], 1)}</th>`;
    row.forEach(v => {
      let bg = "#fff", em = "";
      if (v != null && price) {
        const u = v / price - 1;
        const t = Math.max(-0.4, Math.min(0.4, u)) / 0.4;
        bg = t >= 0 ? `rgba(27,127,75,${0.10 + 0.45 * t})` : `rgba(179,38,30,${0.10 + 0.45 * -t})`;
      }
      html += `<td style="background:${bg}">${v == null ? "—" : money(v, 0)}</td>`;
    });
    html += "</tr>";
  });
  html += "</table><div class='note'>Greener = higher implied value vs today's price; redder = lower. Center ≈ base case.</div>";
  document.getElementById("sensBox").innerHTML = html;
}

/* ---------- AI ---------- */
function aiBox(ai) {
  const card = document.getElementById("aiCard");
  if (!ai) { card.style.display = "none"; return; }
  card.style.display = "block";
  document.getElementById("aiSrc").textContent = ai.source ? `(${ai.source})` : "";
  const list = arr => (arr || []).map(x => `<li>${x}</li>`).join("");
  let html = "";
  if (ai.business_summary) html += `<div style="font-size:14px">${ai.business_summary}</div>`;
  if (ai.moat) html += `<div style="margin-top:10px"><span class="rating">Moat: ${ai.moat.rating}</span> <span style="font-size:14px">${ai.moat.text || ""}</span></div>`;
  if (ai.bull_thesis) html += `<div class="thesis bull"><b style="color:var(--green)">Bull.</b> ${ai.bull_thesis}</div>`;
  if (ai.bear_thesis) html += `<div class="thesis bear"><b style="color:var(--red)">Bear.</b> ${ai.bear_thesis}</div>`;
  if (ai.key_risks) html += `<h4>Key risks</h4><ul>${list(ai.key_risks)}</ul>`;
  if (ai.catalysts) html += `<h4>Catalysts</h4><ul>${list(ai.catalysts)}</ul>`;
  if (ai.assumption_critique) html += `<h4>Assumption critique</h4><ul>${list(ai.assumption_critique)}</ul>`;
  if (ai.overall_take) html += `<div style="margin-top:12px;padding:12px 14px;background:var(--blue-soft);border-radius:10px"><b>Bottom line.</b> ${ai.overall_take}</div>`;
  document.getElementById("aiBox").innerHTML = html;
}
function warnBox(warnings) {
  const el = document.getElementById("warnBox");
  if (!warnings || !warnings.length) { el.innerHTML = ""; return; }
  el.innerHTML = warnings.map(w => `<div class="warn">⚠ ${w}</div>`).join("");
}

/* ---------- watchlist ranking ---------- */
async function runRank() {
  const raw = document.getElementById("rankTickers").value;
  const tickers = raw.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(Boolean);
  if (!tickers.length) return;
  document.getElementById("rankLoader").classList.add("on");
  document.getElementById("rankResults").style.display = "none";
  document.getElementById("rankErr").classList.remove("on");
  document.getElementById("goRank").disabled = true;
  try {
    const res = await fetch("/api/rank", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tickers, run_ai: false }) });
    const data = await res.json();
    const rows = data.rows || [];
    let html = '<table><tr><th>#</th><th>Ticker</th><th>Company</th><th>Regime</th><th class="num">Price</th><th class="num">Fair value</th><th class="num">Upside</th><th class="num">Score</th><th>Call</th></tr>';
    rows.forEach((r, i) => {
      if (r.error) { html += `<tr><td>${i + 1}</td><td><b>${r.ticker}</b></td><td colspan="7" class="muted">${r.error}</td></tr>`; return; }
      const up = r.upside;
      html += `<tr><td>${i + 1}</td><td><b>${r.ticker}</b></td><td>${r.name || ""}</td><td><span class="badge">${r.regime}</span></td>
        <td class="num">${money(r.price)}</td><td class="num">${money(r.fair_value)}</td>
        <td class="num ${up >= 0 ? 'pos' : 'neg'}">${up == null ? '—' : (up >= 0 ? '+' : '') + pct(up, 0)}</td>
        <td class="num"><b style="color:${scoreColor(r.score)}">${r.score}</b></td>
        <td><span class="badge ${scoreClass(r.score)}">${r.recommendation}</span></td></tr>`;
    });
    html += "</table>";
    document.getElementById("rankTable").innerHTML = html;
    document.getElementById("rankResults").style.display = "block";
  } catch (e) {
    const el = document.getElementById("rankErr"); el.textContent = e.message; el.classList.add("on");
  } finally {
    document.getElementById("rankLoader").classList.remove("on");
    document.getElementById("goRank").disabled = false;
  }
}

/* ====================== HOT STOCKS ====================== */
async function loadHotStocks() {
  toggle("hotLoader", true); document.getElementById("hotResults").style.display = "none";
  eshow("hotErr", "");
  document.getElementById("hotLoadMsg").textContent = "Loading latest scan…";
  try {
    const res = await fetch("/api/hotstocks?top=60");
    const d = await res.json();
    if (d.empty) { eshow("hotErr", d.message); return; }
    STATE.hot = d;
    renderHot(d);
    document.getElementById("hotResults").style.display = "block";
  } catch (e) { eshow("hotErr", e.message); }
  finally { toggle("hotLoader", false); }
}
async function runScan() {
  const scope = document.getElementById("scanScope").value;
  const limit = document.getElementById("scanLimit").value;
  toggle("hotLoader", true); document.getElementById("hotResults").style.display = "none"; eshow("hotErr", "");
  document.getElementById("hotLoadMsg").textContent = "Scanning the market (this can take a while on the free feed)…";
  try {
    const res = await fetch("/api/scan/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, limit: limit || null, run_dcf_top: 10 }) });
    const d = await res.json();
    if (d.error) throw new Error(d.error);
    await loadHotStocks();
  } catch (e) { eshow("hotErr", e.message); toggle("hotLoader", false); }
}
function renderHot(d) {
  const f = d.filtered;
  let meta = `scan ${d.scan_date} · ${d.scored}/${d.universe_size || "?"} scored · ${d.provider || ""}`;
  if (f && f.total_removed) meta += ` · ${f.total_removed} junk filtered`;
  document.getElementById("hotMeta").textContent = meta;
  let html = '<table><tr><th>#</th><th>Ticker</th><th>Company</th><th>Sector</th><th>Bucket</th>' +
    '<th class="num">Price</th><th class="num">Hot</th><th class="num">Value</th><th class="num">Qual</th>' +
    '<th class="num">Grow</th><th class="num">Mom</th><th class="num">Fair val</th></tr>';
  d.rows.forEach(r => {
    const up = r.upside;
    html += `<tr><td>${r.rank}</td><td><a href="#" onclick="gotoValue('${r.ticker}');return false"><b>${r.ticker}</b></a></td>
      <td>${(r.name || "").slice(0, 22)}</td><td>${(r.sector || "").slice(0, 16)}</td>
      <td><span class="pill ${r.bucket === 'established' ? 'est' : 'spec'}">${r.bucket || ''}</span></td>
      <td class="num">${money(r.price)}</td>
      <td class="num hotrow-score" style="color:${scoreColor(r.hot_score)}">${r.hot_score == null ? '' : r.hot_score.toFixed(0)}</td>
      <td class="num">${z(r.z_value)}</td><td class="num">${z(r.z_quality)}</td>
      <td class="num">${z(r.z_growth)}</td><td class="num">${z(r.z_momentum)}</td>
      <td class="num">${r.fair_value == null ? '—' : money(r.fair_value) + (up != null ? ` <span class="${up >= 0 ? 'pos' : 'neg'}">(${up >= 0 ? '+' : ''}${pct(up, 0)})</span>` : '')}</td></tr>`;
  });
  html += "</table>";
  if (f && f.total_removed) {
    const parts = Object.entries(f.by_reason || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${v} ${k}`).join(" · ");
    html += `<div class="note">Pre-filtered <b>${f.total_removed}</b> non-investable names before scoring (${parts}). ` +
      `Only tradeable common stocks are ranked — quality is judged by the score, not the filter, so nothing real is dropped.</div>`;
  }
  document.getElementById("hotTable").innerHTML = html;
  renderSectors(d.sectors);
  buildPortfolio();
}
function z(x) { return (x == null || isNaN(x)) ? "—" : (x >= 0 ? "+" : "") + x.toFixed(2); }
function gotoValue(t) { switchTab("single"); document.querySelectorAll(".tab")[0].classList.add("active"); document.getElementById("ticker").value = t; runValue(); }

function renderSectors(sectors) {
  if (!sectors || !sectors.length) { document.getElementById("sectorBox").innerHTML = ""; return; }
  const vals = sectors.map(s => s.avg_composite || 0);
  const lo = Math.min(...vals), hi = Math.max(...vals) || 1;
  let html = "";
  sectors.forEach(s => {
    const t = (s.avg_composite - lo) / ((hi - lo) || 1);
    const col = s.avg_composite >= 0 ? "var(--green)" : "var(--amber)";
    html += `<div class="sector-bar"><span class="nm">#${s.sector_rank} ${s.sector.slice(0, 14)}</span>
      <span class="track"><span style="width:${Math.max(4, t * 100)}%;background:${col}"></span></span>
      <span style="width:96px;text-align:right;color:${col};font-weight:700">${z(s.avg_composite)} <span class="muted" style="font-weight:400">(${s.count})</span></span></div>`;
  });
  document.getElementById("sectorBox").innerHTML = html;
}

async function buildPortfolio() {
  if (!STATE.hot) return;
  const body = { n: parseInt(document.getElementById("pfN").value) || 15,
    weighting: document.getElementById("pfWeight").value,
    max_sector_weight: (parseFloat(document.getElementById("pfCap").value) || 35) / 100, pool: 60 };
  try {
    const res = await fetch("/api/portfolio", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const pf = await res.json();
    if (pf.error) { document.getElementById("portfolioBox").innerHTML = `<div class="muted">${pf.error}</div>`; return; }
    renderPortfolio(pf);
  } catch (e) { document.getElementById("portfolioBox").innerHTML = `<div class="muted">${e.message}</div>`; }
}
function renderPortfolio(pf) {
  const s = pf.stats;
  let html = `<div class="metricline" style="margin:6px 0 10px">
    ${metric("Names", s.n_names)} ${metric("Sectors", s.n_sectors)}
    ${metric("Eff. names", s.effective_names)} ${metric("Wtd hot", s.weighted_hot_score)}</div>`;
  html += '<table><tr><th>Ticker</th><th>Sector</th><th class="num">Weight</th><th class="num">Hot</th></tr>';
  pf.positions.forEach(p => {
    html += `<tr><td><b>${p.ticker}</b></td><td>${(p.sector || '').slice(0, 16)}</td>
      <td class="num">${pct(p.weight, 1)}</td><td class="num">${p.hot_score == null ? '' : p.hot_score.toFixed(0)}</td></tr>`;
  });
  html += "</table>";
  html += `<div class="note">Max sector weight ${pct(s.max_sector_weight, 0)} (cap ${pct(s.max_sector_cap, 0)}). Exposures — value ${z(s.exposure_value)}, quality ${z(s.exposure_quality)}, growth ${z(s.exposure_growth)}, momentum ${z(s.exposure_momentum)}.</div>`;
  document.getElementById("portfolioBox").innerHTML = html;
}

/* ====================== BACKTEST ====================== */
async function runBacktest() {
  toggle("btLoader", true); document.getElementById("btResults").style.display = "none"; eshow("btErr", "");
  const body = { source: document.getElementById("btSource").value,
    tickers: document.getElementById("btTickers").value.split(/[,\s]+/).map(t => t.trim()).filter(Boolean),
    horizon_days: parseInt(document.getElementById("btHorizon").value) || 21,
    rebalance_days: parseInt(document.getElementById("btRebal").value) || 21,
    cost_bps: parseFloat(document.getElementById("btCost").value) || 5,
    benchmark: document.getElementById("btBench").value.trim().toUpperCase() || "SPY", top: 50 };
  try {
    const res = await fetch("/api/backtest/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await res.json();
    if (d.error) throw new Error(d.error);
    renderBacktest(d);
    document.getElementById("btResults").style.display = "block";
  } catch (e) { eshow("btErr", e.message); }
  finally { toggle("btLoader", false); }
}
function renderBacktest(d) {
  const ic = d.ic || {};
  document.getElementById("btVerdict").innerHTML =
    `<div class="verdict ${d.has_edge ? 'good' : 'bad'}">${d.has_edge ? '✓ ' : '⚠ '}${d.verdict}</div>` +
    `<div class="metricline" style="margin-top:14px">
      ${metric("Mean IC", (ic.mean_ic >= 0 ? '+' : '') + (ic.mean_ic || 0).toFixed(3))}
      ${metric("IC t-stat", (ic.ic_t || 0).toFixed(2))}
      ${metric("Hit rate", pct(ic.hit_rate, 0))}
      ${metric("Periods", ic.n_periods || 0)}
      ${metric("Names", d.n_names || 0)}</div>` +
    (d.survivorship_caveat ? `<div class="warn" style="margin-top:12px">⚠ ${d.survivorship_caveat}</div>` : "");
  if (d.equity) eqChart(d.equity);
  if (d.quantiles) qChart(d.quantiles);
  renderBtStats(d);
}
function eqChart(eq) {
  killChart("eq");
  STATE.charts.eq = new Chart(document.getElementById("eqChart"), {
    type: "line",
    data: { labels: eq.dates, datasets: [
      { label: "Top quintile", data: eq.cum_port.map(x => (x - 1) * 100), borderColor: "#1b7f4b", backgroundColor: "transparent", pointRadius: 0, borderWidth: 2 },
      { label: "Benchmark", data: eq.cum_bench.map(x => (x - 1) * 100), borderColor: "#9aa4b5", backgroundColor: "transparent", pointRadius: 0, borderWidth: 2, borderDash: [5, 4] }] },
    options: { responsive: true, plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { x: { ticks: { maxTicksLimit: 7, font: { size: 9 } } }, y: { title: { display: true, text: "cumulative %" } } } }
  });
}
function qChart(q) {
  killChart("q");
  const qm = q.quantile_mean.map(x => x * 100);
  STATE.charts.q = new Chart(document.getElementById("qChart"), {
    type: "bar",
    data: { labels: qm.map((_, i) => "Q" + (i + 1)), datasets: [{ data: qm, backgroundColor: qm.map((_, i) => i === qm.length - 1 ? "#1b7f4b" : (i === 0 ? "#b3261e" : "#cfe0f7")) }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { title: { display: true, text: "avg fwd return %" } } } }
  });
}
function renderBtStats(d) {
  let html = "";
  if (d.equity) {
    const p = d.equity.port, b = d.equity.bench;
    html += '<table><tr><th></th><th class="num">Total</th><th class="num">Annualized</th><th class="num">Volatility</th><th class="num">Sharpe</th><th class="num">Max DD</th></tr>';
    html += `<tr><td><b>Top quintile</b></td><td class="num">${pct(p.total_return, 0)}</td><td class="num">${pct(p.ann_return, 1)}</td><td class="num">${pct(p.volatility, 1)}</td><td class="num">${p.sharpe == null ? '—' : p.sharpe.toFixed(2)}</td><td class="num neg">${pct(p.max_drawdown, 0)}</td></tr>`;
    html += `<tr><td>Benchmark</td><td class="num">${pct(b.total_return, 0)}</td><td class="num">${pct(b.ann_return, 1)}</td><td class="num">${pct(b.volatility, 1)}</td><td class="num">${b.sharpe == null ? '—' : b.sharpe.toFixed(2)}</td><td class="num neg">${pct(b.max_drawdown, 0)}</td></tr>`;
    html += "</table>";
  }
  if (d.factor_ic && Object.keys(d.factor_ic).length) {
    html += '<div class="note" style="margin-top:10px">Per-factor IC: ' +
      Object.entries(d.factor_ic).map(([k, v]) => `${k} ${(v >= 0 ? '+' : '') + v.toFixed(3)}`).join(" · ") + "</div>";
  }
  document.getElementById("btStats").innerHTML = html;
}

/* small helpers */
function toggle(id, on) { const e = document.getElementById(id); if (e) e.classList.toggle("on", on); }
function eshow(id, msg) { const e = document.getElementById(id); if (e) { e.textContent = msg; e.classList.toggle("on", !!msg); } }
