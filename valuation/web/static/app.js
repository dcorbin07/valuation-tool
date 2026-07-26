/* Valquo — dashboard front-end */
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
  ["single", "hot", "signals", "track", "rank", "edge"].forEach(name => {
    const el = document.getElementById("tab-" + name);
    if (el) el.style.display = (name === t) ? "block" : "none";
  });
  if (t === "hot" && !STATE.hotLoaded) { STATE.hotLoaded = true; loadHotStocks(); }
  if (t === "signals" && !STATE.sigLoaded) { STATE.sigLoaded = true; loadSignals(); }
  if (t === "track" && !STATE.trackLoaded) { STATE.trackLoaded = true; loadTrack(); }
  if (t !== "signals") stopSigAuto();
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
    (c.cash_runway_years != null ? `<span class="badge ${c.cash_runway_years >= 4 ? 'g' : 'r'}">Runway: ${c.cash_runway_years.toFixed(1)}y</span>` : "") +
    (c.next_earnings_date ? `<span class="badge a">📅 Earnings ${_earnLabel(c.next_earnings_date)}</span>` : "");

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
  compsBox(d.comps, c.price, (d.reverse && d.reverse.base_avg_growth != null) ? d.reverse.base_avg_growth : (d.assumptions ? d.assumptions.start_growth : null));
  assumEditor(d.assumptions);
  document.getElementById("assumNotes").innerHTML = (d.assumptions.notes || []).map(n => "• " + n).join("<br>");
  sensBox(d.sensitivity, c.price);
  aiBox(d.ai);
  earningsBox(c);
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
function compsBox(cp, price, growth) {
  const m = cp.subject || {}, imp = cp.implied || {};
  const rows = [["P/E", m.pe, imp.pe], ["EV/EBITDA", m.ev_ebitda, imp.ev_ebitda], ["P/S", m.ps, imp.ps], ["EV/Sales", m.ev_sales, imp.ev_sales]];
  let html = `<div class="note" style="margin-top:0">${cp.benchmark_source}</div><table><tr><th>Multiple</th><th class="num">Current</th><th class="num">Implied value</th></tr>`;
  rows.forEach(([lab, cur, iv]) => { html += `<tr><td>${lab}</td><td class="num">${mult(cur)}</td><td class="num">${money(iv)}</td></tr>`; });
  html += `</table>`;
  if (cp.comps_fair_value != null) {
    const u = price ? cp.comps_fair_value / price - 1 : null;
    html += `<div style="margin-top:12px;font-size:14px">Comps fair value <b>${money(cp.comps_fair_value)}</b> ${u == null ? '' : `<span class="${u >= 0 ? 'pos' : 'neg'}">(${u >= 0 ? '+' : ''}${pct(u, 0)})</span>`}</div>`;
  }
  // PEG = P/E ÷ expected growth% (uses the model's base growth). Only meaningful with a positive P/E and growth.
  const gpc = (growth != null && !isNaN(growth)) ? growth * 100 : null;
  const peg = (m.pe != null && m.pe > 0 && gpc != null && gpc > 0) ? m.pe / gpc : null;
  if (peg != null) {
    const col = peg < 1 ? "var(--green)" : (peg <= 2 ? "var(--amber)" : "var(--red)");
    const read = peg < 1 ? "growth looks under-priced" : (peg <= 2 ? "growth roughly in line with price" : "growth looks more than priced in");
    html += `<div style="margin-top:8px;font-size:14px">PEG ratio <b style="color:${col}">${peg.toFixed(2)}</b>
      <span class="muted" style="font-size:12.5px">(P/E ${m.pe.toFixed(1)} ÷ ${gpc.toFixed(0)}% base growth — ${read})</span></div>`;
  } else {
    html += `<div style="margin-top:8px;font-size:12.5px" class="muted">PEG n/m (needs a positive P/E and growth).</div>`;
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

/* ---------- earnings awareness ---------- */
function _earnDays(dateStr) {
  return Math.round((new Date(dateStr + "T00:00:00") - new Date()) / 86400000);
}
function _earnLabel(dateStr) {
  const n = _earnDays(dateStr);
  return isNaN(n) ? "" : (n <= 0 ? "today" : "in " + n + "d");
}
function earningsBox(c) {
  const card = document.getElementById("earnCard");
  const ed = c.next_earnings_date, days = ed ? _earnDays(ed) : null;
  if (ed == null || days == null || days < 0 || days > 45) { card.style.display = "none"; return; }
  card.style.display = "block";
  let em = "";
  if (c.realized_vol && c.price) {
    const move = c.price * c.realized_vol * Math.sqrt(Math.max(days, 1) / 365);
    em = `Expected move by then ≈ <b>±${money(move, 2)} (${pct(move / c.price, 0)})</b> <span class="muted">(from recent volatility)</span>. `;
  }
  const play = `<div style="margin-top:8px;font-size:13.5px" class="muted">Common ways to play it: a
    <b>long straddle/strangle</b> profits if the actual move beats that; <b>selling defined-risk premium</b>
    (e.g. an iron condor) profits from the post-earnings IV crush if it stays inside; or a
    <b>defined-risk directional</b> if the signal gives you a lean. Premium is elevated into the print and IV
    collapses right after — earnings are binary and risky. Not investment advice.</div>`;
  document.getElementById("earnBox").innerHTML =
    `<div style="font-size:15px"><b>${days <= 0 ? 'Today' : days + ' day' + (days === 1 ? '' : 's')}</b> until earnings (${ed}). ${em}</div>${play}`;
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
    const res = await fetch("/api/hotstocks?top=100");
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

/* ====================== TRACK RECORD ====================== */
async function loadTrack() {
  toggle("trackLoader", true); eshow("trackErr", "");
  document.getElementById("trackResults").innerHTML = "";
  try {
    const res = await fetch("/api/track");
    renderTrack(await res.json());
  } catch (e) { eshow("trackErr", e.message); }
  finally { toggle("trackLoader", false); }
}
function _trackCard(title, sub, s) {
  const sm = (s && s.summary) || {}, rec = (s && s.recent) || [];
  const H = [["21", "1-month"], ["63", "3-month"], ["126", "6-month"], ["252", "1-year"], ["all", "All-time"]];
  let inner;
  if (!H.some(([k]) => sm[k])) {
    inner = `<div class="muted">Accruing — picks need ~1 month to mature before they count (${rec.length} logged so far). Check back as the record builds.</div>`;
  } else {
    inner = '<table><tr><th>Horizon</th><th class="num">Picks</th><th class="num">Avg return</th><th class="num">S&amp;P</th><th class="num">Alpha</th><th class="num">Beat S&amp;P</th><th class="num">Win rate</th></tr>';
    H.forEach(([k, lab]) => {
      const x = sm[k];
      if (!x) { inner += `<tr><td>${lab}</td><td colspan="6" class="muted">accruing…</td></tr>`; return; }
      inner += `<tr><td><b>${lab}</b></td><td class="num">${x.n}</td><td class="num">${pct(x.avg_return, 1)}</td>
        <td class="num">${pct(x.avg_bench, 1)}</td>
        <td class="num ${x.avg_alpha >= 0 ? 'pos' : 'neg'}">${x.avg_alpha >= 0 ? '+' : ''}${pct(x.avg_alpha, 1)}</td>
        <td class="num">${pct(x.hit_rate_vs_bench, 0)}</td><td class="num">${pct(x.win_rate, 0)}</td></tr>`;
    });
    inner += '</table>';
  }
  if (rec.length) {
    inner += '<div class="note" style="margin-top:10px">Most recent picks (1-month return vs S&amp;P as they mature):</div>' +
      '<table><tr><th>Date</th><th>Ticker</th><th class="num">1-mo</th><th class="num">S&amp;P</th></tr>';
    rec.forEach(p => {
      const r = p.ret_1m;
      inner += `<tr><td>${p.date || ''}</td><td><b>${p.ticker}</b></td>
        <td class="num ${r == null ? '' : (r >= 0 ? 'pos' : 'neg')}">${r == null ? '—' : pct(r, 1)}</td>
        <td class="num">${p.bench_1m == null ? '—' : pct(p.bench_1m, 1)}</td></tr>`;
    });
    inner += '</table>';
  }
  return `<div class="card"><h3>${title}</h3><div class="section-hint">${sub}</div>${inner}</div>`;
}
function _paperCard(paper) {
  const s = (paper && paper.summary) || {}, watch = (paper && paper.watching) || [], closed = (paper && paper.closed) || [];
  const sub = 'Buys when a name enters the top-10; holds ≥1 month (no churn) and keeps holding while it stays hot — ' +
    'it is <b>not</b> sold just because another name got hotter. Sells only when it is genuinely no longer hot ' +
    '(score below the floor) or reaches its DCF fair value. No time cap by default, so a gem can compound for years. ' +
    'Suggested sizing is score-weighted (hotter = bigger), capped.';
  if (!s.n_total) {
    return `<div class="card"><h3>💼 Paper account — top-10 hot stocks (sell logic)</h3>
      <div class="section-hint">${sub}</div>
      <div class="muted">No positions yet — they open as the daily scan runs (and need the persistent disk to accrue).</div></div>`;
  }
  const reasons = Object.entries(s.by_reason || {}).map(([k, v]) => `${v} ${k}`).join(" · ");
  const head = `<div class="metricline" style="margin:6px 0 12px">
    ${metric("Avg return / pick", s.avg_return == null ? '—' : pct(s.avg_return, 1))}
    ${metric("Realized (closed)", s.avg_return_closed == null ? '—' : pct(s.avg_return_closed, 1))}
    ${metric("Win rate", s.win_rate == null ? '—' : pct(s.win_rate, 0))}
    ${metric("Avg hold", s.avg_hold_days == null ? '—' : Math.round(s.avg_hold_days) + 'd')}
    ${metric("Holding", s.n_open)} ${metric("Closed", s.n_closed)}</div>`;
  let watchTbl = '';
  if (watch.length) {
    watchTbl = '<div class="note" style="margin-top:6px"><b>Currently held (watching)</b> — suggested size &amp; live return:</div>' +
      '<table><tr><th>Ticker</th><th class="num">Size</th><th class="num">Score</th><th>Entry</th><th class="num">Entry $</th><th class="num">Return</th><th class="num">Held</th></tr>';
    watch.forEach(p => {
      watchTbl += `<tr><td><a href="#" onclick="gotoValue('${p.ticker}');return false"><b>${p.ticker}</b></a></td>
        <td class="num">${p.weight == null ? '—' : pct(p.weight, 0)}</td>
        <td class="num" style="color:${scoreColor(p.score || 0)}">${p.score == null ? '—' : p.score.toFixed(0)}</td>
        <td>${p.entry_date}</td><td class="num">${money(p.entry_price)}</td>
        <td class="num ${p.ret == null ? '' : (p.ret >= 0 ? 'pos' : 'neg')}">${p.ret == null ? '—' : pct(p.ret, 1)}</td>
        <td class="num">${p.hold_days}d</td></tr>`;
    });
    watchTbl += '</table>';
  }
  let exitTbl = '';
  if (closed.length) {
    exitTbl = '<div class="note" style="margin-top:12px"><b>Recent exits:</b></div>' +
      '<table><tr><th>Ticker</th><th>Entry</th><th>Exit</th><th>Reason</th><th class="num">Return</th><th class="num">Held</th></tr>';
    closed.forEach(p => {
      exitTbl += `<tr><td><b>${p.ticker}</b></td><td>${p.entry_date}</td><td>${p.exit_date || ''}</td>
        <td style="font-size:12px">${p.reason || ''}</td>
        <td class="num ${p.ret == null ? '' : (p.ret >= 0 ? 'pos' : 'neg')}">${p.ret == null ? '—' : pct(p.ret, 1)}</td>
        <td class="num">${p.hold_days}d</td></tr>`;
    });
    exitTbl += '</table>';
  }
  const b = (paper && paper.bench) || {};
  const benchLine = (b.avg_alpha != null || b.spy_all_time != null)
    ? `<div class="note" style="margin:2px 0 8px">vs <b>S&amp;P 500</b>: ` +
      (b.avg_alpha != null ? `avg <b class="${b.avg_alpha >= 0 ? 'pos' : 'neg'}">${b.avg_alpha >= 0 ? '+' : ''}${pct(b.avg_alpha, 1)}</b> alpha per closed pick` : '') +
      (b.spy_all_time != null ? ` · S&amp;P returned ${pct(b.spy_all_time, 1)} over the same span` : '') + `</div>`
    : '';
  return `<div class="card"><h3>💼 Paper account — top-10 hot stocks (sell logic)</h3>
    <div class="section-hint">${sub}${reasons ? ' Exits so far: ' + reasons + '.' : ''}</div>${head}${benchLine}${watchTbl}${exitTbl}</div>`;
}
function renderTrack(d) {
  const src = (d && d.sources) || {};
  let html = _paperCard(d && d.paper);
  html += _trackCard("📈 Top-10 Hot Stocks — signal quality",
    "Every daily top-10 pick's forward return vs the S&amp;P 500, regardless of when you'd sell.", src.hot10);
  html += _trackCard("⚡ Screaming-Buy Options (underlying)",
    "Forward return of the underlying for each screaming-buy signal — signal accuracy, not option P&amp;L.", src.options);
  html += `<div class="disclaimer">${(d && d.note) || ''}</div>`;
  document.getElementById("trackResults").innerHTML = html;
}

/* ====================== BACKTEST (custom; used by Edge Lab / API) ====================== */
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

/* ====================== INTRADAY SIGNALS (Premium) ====================== */
async function loadSignals() {
  toggle("sigLoader", true); document.getElementById("sigResults").style.display = "none"; eshow("sigErr", "");
  try {
    const res = await fetch("/api/signals?top=40");
    const d = await res.json();
    if (res.status === 401 || d.need_login) { eshow("sigErr", "Please sign in to use Signals."); return; }
    if (res.status === 402 || d.upgrade) { eshow("sigErr", "⚡ Signals is a Premium feature — upgrade to unlock the intraday scanner."); return; }
    if (d.empty) { eshow("sigErr", d.message); return; }
    STATE.signals = d; renderSignals(d);
    document.getElementById("sigResults").style.display = "block";
  } catch (e) { eshow("sigErr", e.message); }
  finally { toggle("sigLoader", false); }
}
async function runSignals() {
  toggle("sigLoader", true); eshow("sigErr", "");
  try {
    const res = await fetch("/api/signals/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ limit: 60 }) });
    const d = await res.json();
    if (res.status === 402 || d.upgrade) { eshow("sigErr", "⚡ Signals is a Premium feature."); toggle("sigLoader", false); return; }
    if (d.error) throw new Error(d.error);
    await loadSignals();
  } catch (e) { eshow("sigErr", e.message); toggle("sigLoader", false); }
}
function renderSignals(d) {
  if (!d) return;
  document.getElementById("sigMeta").textContent = "";
  document.getElementById("sigTime").textContent = d.run_time ? ("updated " + d.run_time) : "";
  const hz = (document.getElementById("sigHorizon") || {}).value || "swing";
  const dir = (document.getElementById("sigDir") || {}).value || "bull";
  const bear = dir === "bear";
  const scoreKey = bear ? "scores_bear" : "scores";
  const contractKey = bear ? "contracts_bear" : "contracts";
  const scoreH = r => {
    const m = r.detail && r.detail[scoreKey];
    return (m && m[hz] != null) ? m[hz] : (bear ? null : r.score);
  };
  const labelsFor = r => bear ? ((r.detail && r.detail.labels_bear) || []) : (r.labels || []);
  // Re-rank by the chosen direction + horizon's score.
  const rows = (d.rows || []).slice()
    .filter(r => scoreH(r) != null)
    .sort((a, b) => (scoreH(b) || 0) - (scoreH(a) || 0));
  const label = (bear ? "bearish · " : "") + hz;
  let html = '<table><tr><th>#</th><th>Ticker</th><th class="num">Score</th><th>Setup / signals</th>' +
    `<th>Contract idea (${label})</th><th>AI read</th></tr>`;
  rows.forEach((r, i) => {
    const s = scoreH(r);
    const badges = labelsFor(r).slice(0, 3).map(l => `<span class="pill ${bear ? 'spec' : 'est'}" style="margin:1px 2px">${l}</span>`).join(" ");
    const c = (r.detail && r.detail[contractKey] && r.detail[contractKey][hz]) || null;
    const cHtml = c
      ? `<div style="font-size:12px"><b>${c.directional}</b><br><span class="muted">${c.defined_risk}</span></div>`
      : '<span class="muted">—</span>';
    html += `<tr><td>${i + 1}</td><td><a href="#" onclick="gotoValue('${r.ticker}');return false"><b>${r.ticker}</b></a></td>
      <td class="num" style="font-weight:800;color:${scoreColor(s)}">${s == null ? '' : s.toFixed(0)}</td>
      <td style="max-width:240px">${badges}</td>
      <td style="max-width:270px">${cHtml}</td>
      <td style="max-width:260px;font-size:12.5px" class="muted">${bear ? '' : (r.ai || r.summary || '')}</td></tr>`;
  });
  html += "</table>";
  document.getElementById("sigTable").innerHTML = html;
}
let sigTimer = null;
function toggleSigAuto() { document.getElementById("sigAuto").checked ? startSigAuto() : stopSigAuto(); }
function startSigAuto() { stopSigAuto(); sigTimer = setInterval(loadSignals, 60000); }
function stopSigAuto() { if (sigTimer) { clearInterval(sigTimer); sigTimer = null; } }

/* ====================== EDGE LAB (owner-only) ====================== */
async function _edgeCall(url, body, msg) {
  toggle("edgeLoader", true); eshow("edgeErr", ""); document.getElementById("edgeMsg").textContent = msg;
  try {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const d = await res.json();
    if (res.status === 403 || d.owner_only) { eshow("edgeErr", "Owner-only research tools."); return null; }
    if (d.error) throw new Error(d.error);
    return d;
  } catch (e) { eshow("edgeErr", e.message); return null; }
  finally { toggle("edgeLoader", false); }
}
async function edgeBacktest() {
  const d = await _edgeCall("/api/edge/backtest",
    { strategy: document.getElementById("edgeStrategy").value, limit: parseInt(document.getElementById("edgeLimit").value) || 100 },
    "Backtesting the strategy vs SPY (downloading price history)…");
  if (!d) return;
  let h = `<div class="card"><h3>Backtest — ${d.strategy} strategy vs SPY (universe ${d.n_universe})</h3><table><tr><th>Horizon</th><th class="num">Strategy CAGR</th><th class="num">SPY CAGR</th><th class="num">Alpha</th><th class="num">Sharpe</th><th class="num">Max DD</th></tr>`;
  ["1y", "5y", "10y", "full"].forEach(k => {
    const s = d[k]; if (!s || !s.available) { h += `<tr><td>${k}</td><td colspan="5" class="muted">n/a</td></tr>`; return; }
    const p = s.portfolio, b = s.benchmark, al = s.alpha_cagr;
    h += `<tr><td><b>${k}</b></td><td class="num">${pct(p.cagr, 1)}</td><td class="num">${pct(b.cagr, 1)}</td>
      <td class="num ${al >= 0 ? 'pos' : 'neg'}">${al >= 0 ? '+' : ''}${pct(al, 1)}</td>
      <td class="num">${p.sharpe == null ? '—' : p.sharpe.toFixed(2)}</td><td class="num neg">${pct(p.max_drawdown, 0)}</td></tr>`;
  });
  h += `</table><div class="warn" style="margin-top:10px">⚠ ${d.survivorship_caveat || ''}</div></div>`;
  document.getElementById("edgeResults").innerHTML = h;
}
async function edgeOptimize() {
  const d = await _edgeCall("/api/edge/optimize", { limit: parseInt(document.getElementById("edgeLimit").value) || 100 },
    "Building the panel & walk-forward optimizing (no-overfit)…");
  if (!d) return;
  const wf = d.walk_forward, adv = d.advisor;
  let h = `<div class="card"><h3>Walk-forward optimize — ${d.n_rows} rows · ${d.n_dates} dates</h3>`;
  h += `<div class="verdict ${wf.adopt ? 'good' : 'bad'}">${wf.adopt ? '✓ ' : '● '}${wf.verdict}</div>`;
  h += `<div class="note" style="margin-top:8px">Recommended weights: ${Object.entries(wf.final_weights).map(([k, v]) => `${k} ${v.toFixed(2)}`).join(" · ")}</div>`;
  h += `<div style="margin-top:10px"><b>Advisor:</b> ${adv.note}`;
  if (adv.adopted) h += `<div class="note">Proposal (${adv.adopted.source}): ${Object.entries(adv.adopted.weights).map(([k, v]) => `${k} ${(+v).toFixed(2)}`).join(" · ")} — holdout IC ${adv.adopted.holdout_ic.toFixed(3)}. ${adv.adopted.rationale}</div>`;
  h += `</div>`;
  const ds = d.deflated_sharpe;
  if (ds && ds.deflated_sharpe != null) {
    h += `<div class="verdict ${ds.deflated_sharpe > 0.95 ? 'good' : 'bad'}" style="margin-top:10px">Deflated Sharpe: <b>${pct(ds.deflated_sharpe, 0)}</b> probability the best of ${ds.n_trials} searched weightings is a <i>real</i> edge (not luck from multiple testing) — ${ds.note}</div>`;
  }
  h += `<div class="note" style="margin-top:8px">Per-factor IC (discovery half): ${Object.entries(adv.factor_ic_discovery || {}).map(([k, v]) => `${k} ${(v >= 0 ? '+' : '') + v.toFixed(3)}`).join(" · ")}</div>`;
  document.getElementById("edgeResults").innerHTML = h;
}
async function edgeTrack() {
  const d = await _edgeCall("/api/edge/track", { source: "hot" }, "Updating the live paper track record…");
  if (!d) return;
  let h = `<div class="card"><h3>Live paper track record — hot-list picks vs SPY</h3>`;
  const S = d.summary || {}; const has = Object.values(S).some(x => x);
  if (!has) { h += `<div class="muted">No matured picks yet — the record accrues as your daily picks age (needs ~1+ month of history). Keep scanning daily.</div>`; }
  else {
    h += `<table><tr><th>Horizon</th><th class="num">Picks</th><th class="num">Avg return</th><th class="num">SPY</th><th class="num">Alpha</th><th class="num">Beat SPY</th></tr>`;
    [["21", "1-month"], ["63", "3-month"], ["126", "6-month"], ["252", "1-year"]].forEach(([k, lab]) => {
      const s = S[k]; if (!s) { h += `<tr><td>${lab}</td><td colspan="5" class="muted">accruing…</td></tr>`; return; }
      h += `<tr><td><b>${lab}</b></td><td class="num">${s.n}</td><td class="num">${pct(s.avg_return, 1)}</td><td class="num">${pct(s.avg_bench, 1)}</td>
        <td class="num ${s.avg_alpha >= 0 ? 'pos' : 'neg'}">${s.avg_alpha >= 0 ? '+' : ''}${pct(s.avg_alpha, 1)}</td><td class="num">${pct(s.hit_rate_vs_bench, 0)}</td></tr>`;
    });
    h += `</table>`;
  }
  h += `<div class="note" style="margin-top:8px">Seeded/updated: ${JSON.stringify(d.updated)}. This accrues survivorship-free going forward.</div></div>`;
  document.getElementById("edgeResults").innerHTML = h;
}

/* small helpers */
function toggle(id, on) { const e = document.getElementById(id); if (e) e.classList.toggle("on", on); }
function eshow(id, msg) { const e = document.getElementById(id); if (e) { e.textContent = msg; e.classList.toggle("on", !!msg); } }
