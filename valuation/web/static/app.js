/* Valquo — dashboard front-end */
const STATE = { ticker: null, data: null, charts: {} };
const EXAMPLES = ["AAPL", "NVDA", "MSFT", "AMZN", "KO", "TSLA", "DIS", "PLTR"];

/* ---------- formatters ---------- */
const money = (x, d = 2) => (x == null || isNaN(x)) ? "—" : "$" + Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x, d = 1) => (x == null || isNaN(x)) ? "—" : (x * 100).toFixed(d) + "%";
const num = (x, d = 0) => (x == null || isNaN(x)) ? "—" : Number(x).toLocaleString("en-US", { maximumFractionDigits: d });
const mult = (x) => (x == null || isNaN(x)) ? "—" : x.toFixed(1) + "x";
/* Market cap — ONE convention everywhere it appears. Values arrive in USD dollars
   (valuation/screener/providers.py::METRICS_UNITS); $B is the default unit, with $T above a
   trillion and $M below a billion so a mega-cap doesn't read as a four-digit blur. Two
   decimals throughout. */
const mcap = (x) => {
  if (x == null || isNaN(x)) return "—";
  const v = Number(x), a = Math.abs(v);
  if (a >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
  if (a >= 1e9) return "$" + (v / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return "$" + (v / 1e6).toFixed(0) + "M";
  return money(v, 0);
};
/* Signed percentage, for figures where the direction is the point (alpha, P&L). */
const spct = (x, d = 1) => (x == null || isNaN(x)) ? "—" : (x >= 0 ? "+" : "") + pct(x, d);
/* Company names and sectors are third-party strings (FMP / SEC) dropped into innerHTML. */
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const scoreColor = (s) => s >= 66 ? "var(--green)" : (s >= 46 ? "var(--amber)" : "var(--red)");
const scoreClass = (s) => s >= 66 ? "g" : (s >= 46 ? "a" : "r");

/* ---------- tabs ---------- */
function switchTab(t) {
  document.querySelectorAll(".tab").forEach(el => el.classList.toggle("active", el.dataset.tab === t));
  ["single", "hot", "dip", "index", "signals", "track", "rank", "edge"].forEach(name => {
    const el = document.getElementById("tab-" + name);
    if (el) el.style.display = (name === t) ? "block" : "none";
  });
  if (t === "hot" && !STATE.hotLoaded) { STATE.hotLoaded = true; loadHotStocks(); }
  if (t === "dip" && !STATE.dipLoaded) { STATE.dipLoaded = true; loadDip(); }
  if (t === "index" && !STATE.indexLoaded) { STATE.indexLoaded = true; loadValquoIndex(); loadIndexTrack(); }
  if (t === "signals" && !STATE.sigLoaded) { STATE.sigLoaded = true; loadSignals(); loadOptionsScorecard(); loadScreamTrack(); }
  if (t === "track" && !STATE.trackLoaded) { STATE.trackLoaded = true; loadTrack(); }
  // The Edge Lab has no autoload for the owner — every button on it is expensive, so it
  // waits to be asked. A READ-ONLY session has no such buttons, so the tab would open
  // empty and read as broken; #edgeReadOnlyNote is rendered only in that case, and the
  // one thing that session CAN do is the thing it came to see.
  if (t === "edge" && !STATE.edgeLoaded && document.getElementById("edgeReadOnlyNote")) {
    STATE.edgeLoaded = true; edgeLearning();
  }
  if (t !== "signals") stopSigAuto();
}

/* ---------- theme ----------
   The initial theme is applied by an inline script in <head> (before first paint, so
   there's no white flash). This only handles toggling and persistence. */
function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("valquo-theme", t); } catch (e) { }
  const b = document.getElementById("themeBtn");
  if (b) {
    b.textContent = t === "dark" ? "☀" : "🌙";
    b.title = t === "dark" ? "Switch to light mode" : "Switch to dark mode";
  }
  // Charts bake their colours in at construction, so redraw with the new palette.
  if (STATE.data) { try { render(STATE.data); } catch (e) { } }
}
function toggleTheme() { applyTheme(currentTheme() === "dark" ? "light" : "dark"); }

/* ---------- init ---------- */
window.addEventListener("load", () => {
  applyTheme(currentTheme());        // sync the button icon with the applied theme
  const chips = document.getElementById("chips");
  chips.innerHTML = '<span class="muted" style="font-size:12px">Try:</span>';
  EXAMPLES.forEach(t => {
    const b = document.createElement("button"); b.className = "chip"; b.textContent = t;
    b.onclick = () => { document.getElementById("ticker").value = t; runValue(); };
    chips.appendChild(b);
  });
  document.getElementById("dlExcel").onclick = () => { if (STATE.ticker) window.location = exportUrl("excel"); };
  document.getElementById("dlPdf").onclick = () => { if (STATE.ticker) window.location = exportUrl("pdf"); };
});

/* ---------- ticker typeahead ----------
   Hits a local endpoint (latest scan + bundled universe), so it's instant and safe to
   fire per keystroke. `seq` guards against a slow response overwriting a newer one. */
const AC = { items: [], idx: -1, seq: 0, timer: null };

function acEl() { return document.getElementById("tickerAc"); }

function acClose() {
  const el = acEl();
  if (el) { el.classList.remove("on"); el.innerHTML = ""; }
  AC.items = []; AC.idx = -1;
  const inp = document.getElementById("ticker");
  if (inp) inp.setAttribute("aria-expanded", "false");
}

function acInput() {
  clearTimeout(AC.timer);
  const q = document.getElementById("ticker").value.trim();
  if (!q) { acClose(); return; }
  AC.timer = setTimeout(() => acFetch(q), 120);
}

async function acFetch(q) {
  const seq = ++AC.seq;
  try {
    const res = await fetch(`/api/tickers?q=${encodeURIComponent(q)}`);
    const d = await res.json();
    if (seq !== AC.seq) return;                 // a newer keystroke already won
    acRender(d.results || []);
  } catch (e) { acClose(); }
}

function acRender(items) {
  const el = acEl();
  if (!el) return;
  AC.items = items; AC.idx = -1;
  if (!items.length) { acClose(); return; }
  el.innerHTML = items.map((r, i) =>
    `<div class="ac-item" role="option" data-i="${i}" onmousedown="acPick(${i})">
       <b>${r.ticker}</b><span class="ac-name">${r.name || ""}</span>
       <span class="ac-sec">${r.sector || ""}</span></div>`).join("");
  el.classList.add("on");
  document.getElementById("ticker").setAttribute("aria-expanded", "true");
}

function acHighlight(n) {
  const el = acEl();
  if (!el || !AC.items.length) return;
  AC.idx = (n + AC.items.length) % AC.items.length;
  el.querySelectorAll(".ac-item").forEach((d, i) => d.classList.toggle("sel", i === AC.idx));
}

function acPick(i) {
  const r = AC.items[i];
  if (!r) return;
  document.getElementById("ticker").value = r.ticker;
  acClose();
  runValue();
}

function acKey(e) {
  const open = AC.items.length > 0;
  if (e.key === "ArrowDown" && open) { e.preventDefault(); acHighlight(AC.idx + 1); return; }
  if (e.key === "ArrowUp" && open) { e.preventDefault(); acHighlight(AC.idx - 1); return; }
  if (e.key === "Escape") { acClose(); return; }
  if (e.key === "Enter") {
    e.preventDefault();
    if (open && AC.idx >= 0) { acPick(AC.idx); return; }
    acClose();
    runValue();
  }
}

function acBlur() { setTimeout(acClose, 150); }   // let a click on an item land first

/* ---------- run valuation ---------- */
async function runValue(overrides) {
  const ticker = document.getElementById("ticker").value.trim().toUpperCase();
  if (!ticker) return;
  STATE.ticker = ticker;
  STATE.overrides = overrides || null;   // what the export must reproduce, not guess at
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
    // Fired AFTER the valuation has painted, and never awaited: the unified view is an
    // addition to the page, so a slow or broken /api/whatdo must not delay or break it.
    loadWhatDo(ticker);
  } catch (e) {
    errBox(e.message);
  } finally {
    show("loader", false);
    document.getElementById("go").disabled = false;
  }
}
function resetAssum() { runValue(); }

/* The download has to describe the same thing the screen does, so the assumptions the page
   was rendered with travel with it. Without them the export could only ask the server for
   "the last <ticker> anyone computed", which is a different question the moment a visitor
   touches the assumption panel — and, behind two workers, sometimes a different answer. */
function exportUrl(kind) {
  const p = new URLSearchParams({ ticker: STATE.ticker });
  Object.entries(STATE.overrides || {}).forEach(([k, v]) => p.set(k, v));
  (STATE.peers || []).forEach(t => p.append("peers", t));
  return `/api/export/${kind}?${p.toString()}`;
}

/* ---------- master render ---------- */
function render(d) {
  const c = d.company, cls = d.classification, sc = d.scenarios, score = d.score;
  document.getElementById("coName").textContent = `${c.name} (${c.ticker})`;
  // `as_of` is the fundamentals date and reads as today however old the figures are, so it
  // never told the reader whether the page was current. `computed_at` does, and it is the
  // same stamp the exported workbook and tearsheet print — so the two can be compared.
  document.getElementById("coSub").textContent =
    [c.sector, c.industry].filter(Boolean).join(" · ") + (c.as_of ? ` · as of ${c.as_of}` : "")
    + (d.computed_at ? ` · computed ${d.computed_at}` : "");

  // badges
  const rc = { high: "g", medium: "a", low: "r" }[cls.dcf_reliability] || "";
  document.getElementById("coBadges").innerHTML =
    `<span class="badge">${cls.regime}</span>` +
    `<span class="badge ${rc}">DCF reliability: ${cls.dcf_reliability}</span>` +
    (cls.rule_of_40 != null ? `<span class="badge ${cls.rule_of_40 >= 40 ? 'g' : 'a'}">Rule of 40: ${cls.rule_of_40.toFixed(0)}</span>` : "") +
    (c.cash_runway_years != null ? `<span class="badge ${c.cash_runway_years >= 4 ? 'g' : 'r'}">Runway: ${c.cash_runway_years.toFixed(1)}y</span>` : "") +
    (c.next_earnings_date ? `<span class="badge a">📅 Earnings ${_earnLabel(c.next_earnings_date)}</span>` : "");

  // hero metrics — a company the DCF can't value shows so explicitly, never a
  // negative "fair value" (which reads as precision the model doesn't have).
  // A growth/pre-profit name shows a RANGE instead of a point: its value is a wide
  // band by nature, and pretending otherwise is the false precision that produced
  // things like a $2.63 headline on a $65 stock.
  const up = d.upside;
  const fvb = d.fair_value_blend || {};
  const fvs = d.fair_value_scenarios || {};
  const notValuable = (d.base_fair_value == null && fvb.valuable === false);
  const asRange = (!notValuable && fvb.growth_led && fvs.bear != null && fvs.bull != null);
  const fvCell = notValuable
    ? `<span class="nv">Not DCF-valuable</span>`
    : (asRange
      ? `<span style="color:var(--navy)">${money(fvs.bear, 0)}–${money(fvs.bull, 0)}</span>`
      : `<span style="color:var(--navy)">${money(d.base_fair_value)}</span>`);
  document.getElementById("heroMetrics").innerHTML =
    metric("Price", money(c.price)) +
    metric(notValuable ? "Fair value" : (asRange ? "Fair value range" : "Base fair value"), fvCell) +
    metric("Upside", notValuable ? '<span class="muted">n/a</span>'
      : `<span class="${up >= 0 ? 'pos' : 'neg'}">${up == null ? '—' : (up >= 0 ? '+' : '') + pct(up, 0)}</span>`) +
    metric("WACC", pct(d.wacc.wacc));

  gauge(score.score, score.recommendation, score.confidence, notValuable, d.withheld);
  fairValueMethod(fvb, d);
  // WHEN THE MODEL REFUSES, THE WHOLE PAGE REFUSES (2026-08-05).
  // The headline said "Not DCF-valuable" and the cards below printed the withheld number
  // anyway — $1,289.68 at +1299% on KSPI, three inches under the notice withholding it.
  // Every card downstream of the DCF now refuses with it. The server already strips these
  // figures from the response (web/withhold.py), so this is the second lock, not the only
  // one: even if a number arrives, nothing here draws it.
  if (notValuable) {
    withheldCards(d);
  } else {
    // Scenarios are drawn from the SAME method as the headline when we have it. Showing
    // the raw DCF cone under a multiples-based headline is how a growth name ended up
    // displaying three negative scenario cards beneath a positive fair value.
    const scen = (fvs.base != null)
      ? { bear: fvs.bear, base: fvs.base, bull: fvs.bull, method: fvs.method }
      : { bear: sc.bear_price, base: sc.base_price, bull: sc.bull_price, method: "DCF" };
    rangebar(scen.bear, scen.base, scen.bull, c.price);
    scenarioCards(scen, c.price, fvb);
    fcfChart(sc.base.rows);
    mcChart(d.montecarlo);
    reverseBox(d.reverse);
    sensBox(d.sensitivity, c.price);
  }
  scoreBars(score, notValuable, d.withheld);
  compsBox(d.comps, c.price, (d.reverse && d.reverse.base_avg_growth != null) ? d.reverse.base_avg_growth : (d.assumptions ? d.assumptions.start_growth : null), d.withheld);
  assumEditor(d.assumptions);
  document.getElementById("assumNotes").innerHTML = (d.assumptions.notes || []).map(n => "• " + n).join("<br>");
  aiBox(d.ai);
  earningsBox(c);
  warnBox(d.warnings);
  document.getElementById("sourcesBox").innerHTML = "Sources: " + (d.sources || []).join(" · ");
}

function metric(k, v) { return `<div class="m"><div class="k">${k}</div><div class="v">${v}</div></div>`; }
function show(id, on) { document.getElementById(id).classList.toggle("on", on); }
function errBox(msg) { const e = document.getElementById("err"); e.textContent = msg; e.classList.toggle("on", !!msg); }

/* ---------- the page-wide refusal ----------
   One place decides what a withheld name shows, so a card cannot be added later that
   quietly starts drawing the number again: everything here writes a REASON where a figure
   would have been. Blank space would read as "loading" or "no data"; the reader is owed the
   same sentence the headline gave them. Copy comes from the server (web/withhold.py) so the
   wire and the page cannot disagree about why something is missing. */
const _WITHHELD_FALLBACK = {
  scenarios: "Bear, base and bull are the same valuation re-run on shifted assumptions, so they are withheld with it.",
  montecarlo: "The distribution is that same valuation re-run thousands of times, so it is withheld with it.",
  sensitivity: "The grid is that same valuation at other discount and growth rates, so it is withheld with it.",
  fcf: "The projection is the forecast the valuation was built from, so it is withheld with it.",
  comps: "Multiples are ratios and are shown. The per-share values implied by them are not.",
  reverse: "The market-implied growth read is solved from the same model, so it is withheld with it.",
  score: "The valuation part of the score is computed from figures that were withheld."
};
function _wReason(w, key) { return ((w && w.cards) || {})[key] || _WITHHELD_FALLBACK[key] || ""; }
function withheldBox(w, key) {
  return `<div class="nv-box"><b>Not published for this name.</b> ${esc(_wReason(w, key))}</div>`;
}
function _canvasCard(id, on) {
  const el = document.getElementById(id);
  if (el) el.style.display = on ? "" : "none";
}
function withheldCards(d) {
  const w = d.withheld || {};
  // Charts are stateful: skipping the draw would leave the PREVIOUS ticker's cone on screen,
  // which is the same bug with an extra step.
  killChart("fcf"); killChart("mc");
  _canvasCard("fcfChart", false); _canvasCard("mcChart", false);
  setHtml("rangebar", "");
  setHtml("scenarioCards", withheldBox(w, "scenarios"));
  setHtml("scenarioNote", "");
  setHtml("fcfNote", withheldBox(w, "fcf"));
  setHtml("mcNote", withheldBox(w, "montecarlo"));
  setHtml("sensBox", withheldBox(w, "sensitivity"));
  setHtml("reverseBox", withheldBox(w, "reverse"));
}

/* ---------- gauge ---------- */
function gauge(s, rec, conf, notValuable, w) {
  if (s == null) {
    document.getElementById("gauge").innerHTML =
      `<div class="nv-box" style="text-align:left;max-width:260px">
         <b>Not rated.</b> ${esc((w && w.score_note) || _WITHHELD_FALLBACK.score)}</div>`;
    return;
  }
  const r = 54, circ = 2 * Math.PI * r, off = circ * (1 - s / 100), col = scoreColor(s);
  // A PARTIAL score is a real number built from four of the five sub-scores — the engine
  // drops the valuation component entirely for a withheld name — and it must not be dressed
  // as a complete one. The distinction is on the dial itself (dashed arc, "PARTIAL" over the
  // number, "4 of 5 components" under it) rather than in a tooltip, because the failure mode
  // this whole thread is about is a partial thing read as a whole one.
  if (notValuable) {
    document.getElementById("gauge").innerHTML = `
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="${r}" fill="none" stroke="var(--border)" stroke-width="13"/>
        <!-- same geometry as a full gauge so the number and the arc still agree, at 60%
             opacity, with an amber dashed ring inside it: the dial reads as unfinished
             at a glance, which is the honest impression. -->
        <circle cx="70" cy="70" r="${r}" fill="none" stroke="${col}" stroke-width="13" stroke-linecap="round"
          stroke-dasharray="${circ}" stroke-dashoffset="${off}" opacity=".6"/>
        <circle cx="70" cy="70" r="${r - 9}" fill="none" stroke="var(--amber)" stroke-width="1.5"
          stroke-dasharray="4 5" opacity=".85"/>
      </svg>
      <div style="margin-top:-104px;text-align:center">
        <div style="font-size:10.5px;font-weight:800;letter-spacing:.09em;color:var(--amber)">PARTIAL</div>
        <div class="score-num" style="color:${col};opacity:.85">${s}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:-4px">/ 100 · 4 of 5 components</div>
      </div>
      <div class="rec" style="color:var(--muted);margin-top:36px;font-size:15px">${esc(rec || "")}<span
        style="font-size:11px;font-weight:700;color:var(--amber)"> — partial</span></div>
      <div class="conf">confidence: ${esc(conf || "low")}</div>
      <div class="nv-box" style="text-align:left;margin-top:10px;max-width:270px;font-size:12px">
        <b>Valuation withheld.</b> ${esc((w && w.score_note) || _WITHHELD_FALLBACK.score)}</div>`;
    return;
  }
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

/* ---------- how the fair value was reached ----------
   Which lenses were used and in what mix, so the number is never a black box. */
function fairValueMethod(fvb, d) {
  const el = document.getElementById("fvMethod");
  if (!el) return;
  if (!fvb || fvb.method === undefined) { el.innerHTML = ""; return; }
  const LENS = { dcf: "DCF", pb_roe: "P/B–ROE", growth: "growth (revenue)", multiples: "multiples" };
  let html = "";
  if (fvb.valuable === false) {
    html = `<div class="nv-box"><b>Not DCF-valuable.</b> ${fvb.reason || ""}</div>`;
  } else {
    // A growth name leads with what the PRICE implies, not with our point value —
    // the reverse-DCF read is the decision-grade statement for a pre-profit company.
    if (fvb.headline) {
      html += `<div class="nv-box" style="margin-top:0"><b>Priced for growth.</b> ${fvb.headline}</div>`;
    }
    const lens = Object.entries(fvb.lenses || {})
      .map(([k, v]) => `${LENS[k] || k} ${money(v.value)}`)
      .join(" · ");
    html += `<div class="note" style="margin-top:0">Valued as <b>${fvb.method}</b>` +
      (lens ? ` — ${lens}.` : ".") +
      (fvb.confidence ? ` Confidence: <b>${fvb.confidence}</b>.` : "") +
      ` <span class="muted">The mix adapts to the company: cash-generative businesses lean on the
        DCF, growth and pre-profit names on a revenue multiple scaled to their growth rate,
        banks on book value and ROE.</span></div>`;
    const gl = d && d.growth_lens;
    if (gl && gl.applies) {
      html += `<div class="note">Growth lens: revenue compounds to ${money(gl.revenue_at_horizon, 0)}mm over
        ~${gl.horizon_years}y and exits at ${(gl.exit_multiple || 0).toFixed(1)}x sales — a justified
        <b>${gl.implied_ev_sales_now}x</b> sales today` +
        (gl.current_ev_sales != null ? ` versus the <b>${gl.current_ev_sales}x</b> it trades at` : "") + `.</div>`;
    }
    if (d && d.dcf_per_share != null && fvb.dcf_meaningful === false) {
      html += `<div class="note">The raw DCF returns ${money(d.dcf_per_share)} here, which is why it's
        excluded rather than averaged in.</div>`;
    }
  }
  (fvb.notes || []).forEach(n => { html += `<div class="note">${n}</div>`; });
  el.innerHTML = html;
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
function scenarioCards(scen, price, fvb) {
  const card = (lab, v, col) => {
    const u = (price && v != null) ? (v / price - 1) : null;
    return `<div class="card" style="margin:0;box-shadow:none;border:1px solid var(--border);padding:14px">
      <div style="font-size:12px;color:var(--muted);font-weight:700">${lab.toUpperCase()}</div>
      <div style="font-size:22px;font-weight:800;color:${col}">${v == null ? '—' : money(v)}</div>
      <div style="font-size:13px" class="${u >= 0 ? 'pos' : 'neg'}">${u == null ? '' : (u >= 0 ? '+' : '') + pct(u, 0) + ' vs price'}</div></div>`;
  };
  let html = card("Bear", scen.bear, "var(--red)") + card("Base", scen.base, "var(--navy)") + card("Bull", scen.bull, "var(--green)");
  document.getElementById("scenarioCards").innerHTML = html;
  const el = document.getElementById("scenarioNote");
  if (el) {
    const conf = (fvb && fvb.confidence) ? fvb.confidence : null;
    // The band is a ZONE, not a number to trade toward. Wording from window.HOLD_HORIZON so
    // it cannot drift, and BAND_SCOPE is not optional: this spread comes from the valuation
    // engine on one company's filings, while the hot list's backtested figures come from the
    // composite. Letting a reader take one as evidence for the other is the misreading that
    // putting both on the same product invites.
    const band = _HOLD_H ? ` <b>${esc(_HOLD_H.band)}</b> ${esc(_HOLD_H.band_scope)}` : "";
    el.innerHTML = `<div class="note">Each case is valued the same way as the headline${scen.method ? ` (${scen.method})` : ""} —
      growth and margins shifted, and the exit multiple compressed or expanded with them.` + band +
      (conf === "low" ? ` <b>Confidence: low.</b> This is a range, not a forecast — a growth valuation
      moves a long way on assumptions nobody can pin down yet.` : "") + `</div>`;
  }
}

/* ---------- charts ---------- */
function killChart(k) { if (STATE.charts[k]) { STATE.charts[k].destroy(); delete STATE.charts[k]; } }
function fcfChart(rows) {
  killChart("fcf");
  _canvasCard("fcfChart", true); setHtml("fcfNote", "");
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
  _canvasCard("mcChart", true);
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
function scoreBars(score, notValuable, wh) {
  // On a withheld name the number IS published — it just rests on four components instead of
  // five. Name the arithmetic (which weight was dropped, what the rest renormalise to) rather
  // than leaving the reader to infer it from a greyed-out bar.
  const dropped = notValuable ? (score.weights || {}).valuation : null;
  document.getElementById("scoreHint").innerHTML = notValuable
    ? `<div class="nv-box" style="margin-top:0"><b>Partial score — 4 of 5 components.</b>
         ${esc((wh && wh.score_note) || score.partial_note || _WITHHELD_FALLBACK.score)}
         ${dropped != null ? `The valuation component normally carries <b>${pct(dropped, 0)}</b>
         of this score for a <b>${esc(STATE.data.classification.regime)}</b> company; that weight
         is not reassigned to a substitute, it is removed and the remaining four are
         renormalised.` : ""}</div>`
    : `Weighted for a <b>${STATE.data.classification.regime}</b> company — weights shift by regime so the DCF is trusted less where it's less reliable. Overall confidence: <b>${score.confidence}</b>.`;
  const order = ["valuation", "quality", "growth", "health", "momentum"];
  let html = "";
  order.forEach(k => {
    const v = score.subscores[k], w = score.weights[k];
    const col = v == null ? "var(--faint)" : scoreColor(v);
    // "n/a" is the right word for a sub-score that could not be computed and the WRONG word
    // for one that was computed and then withheld — say which.
    const held = notValuable && k === "valuation" && v == null;
    const lab = v == null ? (held ? "withheld" : "n/a") : v.toFixed(0);
    const wt = held ? `<span class="wt">weight ${pct(w, 0)} — dropped, not reassigned</span>`
                    : `<span class="wt">weight ${pct(w, 0)}</span>`;
    html += `<div class="sbar"><div class="lab"><span><b>${k[0].toUpperCase() + k.slice(1)}</b> ${wt}</span>
      <span style="font-weight:700;color:${held ? 'var(--amber)' : col}">${lab}</span></div>
      <div class="bar"${held ? ' style="background:repeating-linear-gradient(90deg,var(--border) 0 4px,transparent 4px 9px)"' : ''}><span style="width:${v == null ? 0 : v}%;background:${col}"></span></div></div>`;
  });
  html += `<div style="margin-top:10px;font-size:12.5px" class="muted">Drivers:</div><ul style="margin:4px 0 0;padding-left:18px;font-size:13px">` +
    (score.drivers || []).map(x => `<li>${x}</li>`).join("") + "</ul>";
  document.getElementById("scoreBars").innerHTML = html;
}

/* ====================== UNIFIED "what the tool does with this name" ======================
   The product used to answer this across three tabs that never met: the opportunity score
   here, the scream-buy alert on Signals, the tracked outcome on Track Record. This joins them
   for one ticker from a single read of what is already stored (/api/whatdo).

   The framing rule is the important part. These lines describe what the MODEL is doing — held
   in the book at this weight, alerted on this contract, sold on this date — never what the
   reader should do. And every options figure carries the convexity line: the backtested hit
   rate is ~37%, so an alert is a bet with a fat right tail, not a likely winner. A "1 of 1
   won" on a single name is a count and is labelled as one; it is never a rate. */
async function loadWhatDo(ticker) {
  const box = document.getElementById("whatDoCard");
  if (!box) return;
  box.style.display = "";
  document.getElementById("whatDoBody").innerHTML = skeleton(3);
  let d;
  try {
    d = await (await fetch("/api/whatdo?ticker=" + encodeURIComponent(ticker))).json();
  } catch (e) {
    box.style.display = "none";
    return;
  }
  if (!d || (d.error && !d.action?.length)) { box.style.display = "none"; return; }
  STATE.whatdo = d;
  renderWhatDo(d);
}

function renderWhatDo(d) {
  const s = d.stock || {}, o = d.options || {};
  const lines = (d.action || []).map(a => {
    const cls = a.kind === "caveat" ? "wd-caveat" : "wd-line";
    return `<div class="${cls}">${a.kind === "caveat" ? "" : "<span class=\"wd-dot\"></span>"}${esc(a.text || "")}</div>`;
  }).join("");

  let stats = "";
  if (s.in_scan) {
    stats = `<div class="metricline" style="margin:4px 0 12px">
      ${metric("Hot score", s.hot_score == null ? "—" :
        `<span style="color:${scoreColor(s.hot_score)}">${s.hot_score.toFixed(0)}</span>`)}
      ${metric("Rank", `${s.rank} / ${s.n_scored}`)}
      ${metric("In the book", (s.index || {}).in_book
        ? `<span class="pos">${pct((s.index || {}).weight, 1)}</span>`
        : `<span class="muted">no</span>`)}
      ${metric("Options alerts", o.withheld ? "—" : (o.n_logged || 0))}
    </div>`;
  }

  // The same attribution the Hot tab shows, on the name the reader is already looking at —
  // one explanation of one ranking, not a second opinion.
  const why = (s.why || []).length
    ? `<div style="margin-top:6px">${attributionPanel(
        { ticker: d.ticker, rank: s.rank, hot_score: s.hot_score, composite: s.composite,
          extra: { why: s.why, why_composite: s.why_composite } }, { of: s.n_scored })}</div>`
    : "";

  const opt = o.withheld
    ? `<div class="note">${esc(o.message || "")}</div>`
    : "";

  // The payoff SHAPE, on the public side too — and on the withheld branch as well, because a
  // visitor who is told an alert exists but not what it is has the least context of anyone and
  // is the most likely to read "options signal" as "likely winner". The contract stays hidden;
  // the distribution is a property of a historical simulation, not a live pick.
  const shape = payoffCompact(o.payoff);

  document.getElementById("whatDoBody").innerHTML = stats + lines + opt + shape + why +
    (s.freshness ? freshnessBanner(s.freshness) : "");
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
function compsBox(cp, price, growth, wh) {
  const m = cp.subject || {}, imp = cp.implied || {};
  // A multiple is a ratio of two figures in the same currency, so it survives the mismatch
  // that triggers most refusals. The per-share value implied by it does not — that step
  // prices a reporting-currency figure against a USD quote, and it is how a $92 stock got a
  // "$326 implied value". Ratios stay, implied dollars go, and the card says which.
  const withheld = !!cp.withheld;
  const rows = [["P/E", m.pe, imp.pe], ["EV/EBITDA", m.ev_ebitda, imp.ev_ebitda], ["P/S", m.ps, imp.ps], ["EV/Sales", m.ev_sales, imp.ev_sales]];
  let html = `<div class="note" style="margin-top:0">${esc(cp.benchmark_source || "")}</div>`;
  if (withheld) html += withheldBox(wh, "comps");
  html += `<table><tr><th>Multiple</th><th class="num">Current</th><th class="num">Implied value</th></tr>`;
  rows.forEach(([lab, cur, iv]) => {
    const cell = withheld ? '<span class="muted">withheld</span>' : money(iv);
    html += `<tr><td>${lab}</td><td class="num">${mult(cur)}</td><td class="num">${cell}</td></tr>`;
  });
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
  // EVERY field below is model output, written from filings and news text — i.e. from
  // sources an outsider can influence. Interpolating it raw into innerHTML made a crafted
  // string in a filing into script in the user's page (SECURITY_AUDIT.md M6). Jinja
  // autoescapes the templates, but this path bypasses templates entirely, so it has to
  // escape here. The layout markup is ours; only the values are escaped.
  const list = arr => (arr || []).map(x => `<li>${esc(x)}</li>`).join("");
  let html = "";
  if (ai.business_summary) html += `<div style="font-size:14px">${esc(ai.business_summary)}</div>`;
  if (ai.moat) html += `<div style="margin-top:10px"><span class="rating">Moat: ${esc(ai.moat.rating)}</span> <span style="font-size:14px">${esc(ai.moat.text || "")}</span></div>`;
  if (ai.bull_thesis) html += `<div class="thesis bull"><b style="color:var(--green)">Bull.</b> ${esc(ai.bull_thesis)}</div>`;
  if (ai.bear_thesis) html += `<div class="thesis bear"><b style="color:var(--red)">Bear.</b> ${esc(ai.bear_thesis)}</div>`;
  if (ai.key_risks) html += `<h4>Key risks</h4><ul>${list(ai.key_risks)}</ul>`;
  if (ai.catalysts) html += `<h4>Catalysts</h4><ul>${list(ai.catalysts)}</ul>`;
  if (ai.assumption_critique) html += `<h4>Assumption critique</h4><ul>${list(ai.assumption_critique)}</ul>`;
  if (ai.overall_take) html += `<div style="margin-top:12px;padding:12px 14px;background:var(--blue-soft);border-radius:10px"><b>Bottom line.</b> ${esc(ai.overall_take)}</div>`;
  document.getElementById("aiBox").innerHTML = html;
}
function warnBox(warnings) {
  const el = document.getElementById("warnBox");
  if (!warnings || !warnings.length) { el.innerHTML = ""; return; }
  el.innerHTML = warnings.map(w => `<div class="warn">⚠ ${esc(w)}</div>`).join("");
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
      // A partial score sits in the same column as full ones. Mark it in the cell, not in a
      // footnote — an unmarked 50 beside a full 50 says they mean the same thing.
      const part = r.score_partial;
      html += `<tr><td>${i + 1}</td><td><b>${r.ticker}</b></td><td>${r.name || ""}</td><td><span class="badge">${r.regime}</span></td>
        <td class="num">${money(r.price)}</td><td class="num">${part
          ? `<span class="muted" style="font-weight:700${r.fair_value_withheld_kind === "unavailable" ? ";font-style:italic" : ""}" title="${esc(r.fair_value_withheld_reason || "")}">${r.fair_value_withheld_kind === "unavailable" ? "no data" : "withheld"}</span>`
          : money(r.fair_value)}</td>
        <td class="num ${up >= 0 ? 'pos' : 'neg'}">${up == null ? '—' : (up >= 0 ? '+' : '') + pct(up, 0)}</td>
        <td class="num"><b style="color:${scoreColor(r.score)}${part ? ';opacity:.7' : ''}">${r.score}</b>${part
          ? ` <span style="font-size:10px;font-weight:800;color:var(--amber)" title="Valuation withheld — scored on quality, growth, financial health and momentum only.">PARTIAL</span>` : ""}</td>
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
  eshow("hotErr", "");
  const results = document.getElementById("hotResults");
  // Paint SOMETHING before the network: the last good ranking if we have one, a
  // table-shaped skeleton if we don't. Either way the spinner never appears for this tab.
  const cached = cacheGet("hot");
  if (cached) {
    try { renderHot(cached.d); } catch (e) { }
    // The freshness verdict inside a cached payload was computed WHEN IT WAS CACHED. A copy
    // saved yesterday still says "ranking from today", which is the exact lie the freshness
    // banner exists to prevent — so it is suppressed until the live fetch replaces it.
    setHtml("hotFreshness", "");
    cacheBanner("hotCache", cached);
  } else {
    setHtml("hotTable", skeletonTable(10, 8));
    setHtml("hotCache", "");
  }
  results.style.display = "block";
  toggle("hotLoader", false);
  try {
    const res = await fetch("/api/hotstocks?top=100");
    const d = await res.json();
    if (d.empty) {
      eshow("hotErr", d.message);
      if (!cached) { results.style.display = "none"; }
      return;
    }
    STATE.hot = d;
    renderHot(d);
    cacheSet("hot", d);
    setHtml("hotCache", "");
  } catch (e) {
    eshow("hotErr", cached
      ? `${e.message} — the ranking above is your last saved copy, not a fresh one.`
      : e.message);
    if (!cached) { results.style.display = "none"; }
  }
}
async function runScan() {
  // Owner-only controls — absent from the page for everyone else.
  const scopeEl = document.getElementById("scanScope"), limitEl = document.getElementById("scanLimit");
  if (!scopeEl) return;
  const scope = scopeEl.value;
  const limit = limitEl ? limitEl.value : null;
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
function _ageStr(dstr) {
  try { const days = Math.round((Date.now() - new Date(dstr + "T00:00:00")) / 86400000);
    return days <= 0 ? " (today)" : ` (${days}d ago)`; } catch (e) { return ""; }
}
function _whyChips(r) {
  const w = (r.extra && r.extra.why) || [];
  if (!w.length) return "";
  return `<div class="muted" style="font-size:10px">` +
    w.slice(0, 3).map(x => `<span class="${x.c >= 0 ? 'pos' : 'neg'}">${x.theme.replace(/_/g, ' ')}</span>`).join(" · ") + `</div>`;
}

/* ---------- "why this score" attribution ----------
   The hot score is a percentile RANK of a composite, and the composite is a weighted average
   of standardized themes. The server decomposes that average back into per-theme
   contributions that SUM to the composite (valuation/screener/attribution.py), so this panel
   is arithmetic rather than a narrative: every bar is a real term in the number above it.

   THREE things this must never imply. The contributions are in composite units — cross-sectional
   standard deviations — NOT points of the 1-100 score, because rank is a monotone but
   non-linear map. And a theme's contribution is relative to the rest of the scan that day,
   so "+0.2 quality" means "better than this cross-section", not "good in absolute terms".

   THIRD, added after extension V3's noise calibration (HANDOFF_extensions_v3.md): the panel
   decomposes the rank exactly, and that exactness is about the ARITHMETIC, not about the
   rank's precision. V3 tested the score against a permutation null and the per-name result
   FAILED its pre-registered bar — the composite at rank 10 sits at empirical p 0.116, i.e.
   roughly one chance-assembled universe in nine reaches it at that rank. A panel that shows
   three decimals of attribution for a position that is not distinguishable from chance is
   precisely the impression this project must not give, so the calibrated sentence travels
   with every panel. Its wording comes from window.SCORE_CONFIDENCE (injected by index.html
   from valuation/web/score_confidence.py) and is NEVER re-worded here — one source, so a
   name row cannot state a softer limit than the legend printed above the table. */
const _SCORE_CONF = (typeof window !== "undefined" && window.SCORE_CONFIDENCE) || null;
/* S22's hold-horizon copy (valuation/web/hold_horizon.py, injected by index.html). Same rule
   as _SCORE_CONF above: never re-worded here, so a name row cannot state a longer-lasting or
   more personal version of the edge than the legend printed above the table. The figures stay
   in the legend; what reaches a NAME is the limit — the edge is the decile's property and a
   name usually leaves after one quarter. */
const _HOLD_H = (typeof window !== "undefined" && window.HOLD_HORIZON) || null;
const THEME_LABEL = {
  value: ["Value", "cheap vs earnings, cash flow and book"],
  quality: ["Quality", "returns on capital, margins, low debt"],
  growth: ["Growth", "revenue growth and its acceleration"],
  momentum: ["Momentum", "6- and 12-month price trend"],
  insider: ["Insider buying", "cluster buying by company officers"],
  low_risk: ["Low risk", "low beta and realized volatility"],
  capital_discipline: ["Capital discipline", "not issuing shares to fund itself"],
  sentiment: ["Analyst sentiment", "rating actions and estimate revisions"],
  size: ["Size", "small-cap tilt"],
  institutional: ["Institutional buying", "13F accumulation and holder breadth"],
};
function _themeLabel(k) { return (THEME_LABEL[k] || [k.replace(/_/g, " "), ""])[0]; }
function _themeHint(k) { return (THEME_LABEL[k] || ["", ""])[1]; }

function attributionPanel(r, opts) {
  const why = (r.extra && r.extra.why) || [];
  const o = opts || {};
  if (!why.length) {
    return `<div class="note">No attribution stored for this name — it is written at scan time,
      so rows saved by an older scan show none. It appears after the next daily scan.</div>`;
  }
  const max = Math.max(...why.map(x => Math.abs(x.c))) || 1;
  const comp = (r.extra && r.extra.why_composite != null) ? r.extra.why_composite : r.composite;
  const up = why.filter(x => x.c > 0), down = why.filter(x => x.c < 0);
  const bars = why.map(x => {
    const w = Math.max(2, Math.round(Math.abs(x.c) / max * 50));
    const pos = x.c >= 0;
    return `<div class="attr-row">
      <span class="nm" title="${esc(_themeHint(x.theme))}">${esc(_themeLabel(x.theme))}</span>
      <span class="track"><span class="mid"></span>
        <span class="fill ${pos ? "pos" : "neg"}" style="${pos ? "left:50%" : `right:50%`};width:${w}%"></span></span>
      <span class="val ${pos ? "pos" : "neg"}">${x.c >= 0 ? "+" : ""}${x.c.toFixed(3)}</span>
      <span class="sh">${Math.round(x.share * 100)}%</span></div>`;
  }).join("");
  const head = `<div class="attr-head">
      <b>Hot ${r.hot_score == null ? "—" : r.hot_score.toFixed(0)}</b> = rank ${r.rank}${
        o.of ? " of " + o.of : ""} · composite <b>${comp == null ? "—" : (comp >= 0 ? "+" : "") + comp.toFixed(3)}</b>
      ${up.length ? `· helped by <b class="pos">${up.slice(0, 2).map(x => esc(_themeLabel(x.theme).toLowerCase())).join(", ")}</b>` : ""}
      ${down.length ? `· held back by <b class="neg">${down.slice(0, 2).map(x => esc(_themeLabel(x.theme).toLowerCase())).join(", ")}</b>` : ""}
    </div>`;
  // The precision limit sits ABOVE the three-decimal bars, not under them. A caveat printed
  // after the evidence reads as a footnote; printed before it, it frames how the bars are read.
  const calib = _SCORE_CONF ? `<div class="note" style="margin-bottom:8px">
      <b>This decomposition is exact; the position it explains is not.</b>
      ${esc(_SCORE_CONF.per_name)} — so treat the themes below as the reason this name is in
      the conversation, not as proof it belongs at this exact rank.</div>` : "";
  // How long the edge lasted belongs next to the rank it qualifies, but as a LIMIT rather than
  // a figure: S22's returns are the top decile's as a group, and V3 forbids a per-name promise.
  const horizon = _HOLD_H ? `<div class="note" style="margin-bottom:8px">
      <b>And it is the list's edge, not this name's.</b> ${esc(_HOLD_H.per_name_note)}</div>` : "";
  return `<div class="attr">${head}${calib}${horizon}${bars}
    <div class="note">Bars are the actual terms of the score: they add up to the composite
      (${comp == null ? "—" : comp.toFixed(3)}), and the 1–100 is that composite's percentile rank
      against every other name in this scan. Units are standard deviations versus this scan, not
      percent — "+0.20 quality" means better quality than this peer set, not good in the abstract.
      The % column is the share of everything that moved this name, positive and negative alike.</div></div>`;
}

function toggleWhy(t) {
  const el = document.getElementById("why-" + t);
  if (!el) return;
  const open = el.style.display !== "none";
  el.style.display = open ? "none" : "";
  const btn = document.getElementById("whybtn-" + t);
  if (btn) { btn.textContent = open ? "why?" : "hide"; btn.setAttribute("aria-expanded", String(!open)); }
}
async function loadRegime() {
  try {
    const g = await (await fetch("/api/regime")).json();
    const el = document.getElementById("hotMeta");
    if (el && g && g.regime) {
      const c = g.regime === "risk-on" ? "pos" : (g.regime === "risk-off" ? "neg" : "");
      el.innerHTML += ` &nbsp;·&nbsp; <b class="${c}">market: ${g.regime}</b>` +
        (g.vix != null ? ` · VIX ${g.vix}` : "") + (g.ten_year != null ? ` · 10Y ${g.ten_year}%` : "") +
        (g.sp_above_200dma_pct != null ? ` · S&P ${g.sp_above_200dma_pct >= 0 ? '+' : ''}${g.sp_above_200dma_pct}% vs 200d` : "");
    }
  } catch (e) { }
}
// Mark a name whose fundamentals came from the broker alone. That row has a real market cap,
// value and quality reading but NO margins, free cash flow or revenue growth, so it is scored
// on fewer themes than its neighbours — a difference worth seeing rather than inferring.
function _srcMark(r) {
  const src = (r.extra || {}).source;
  if (src !== "broker") return "";
  return ` <span class="est-mark" title="Partial fundamentals: broker feed only — no margins, free cash flow or revenue growth for this name, so its score rests on fewer factors.">p</span>`;
}

function renderHot(d) {
  const f = d.filtered;
  let meta = `scan ${d.scan_date}${_ageStr(d.scan_date)} · ${d.scored}/${d.universe_size || "?"} scored · ${d.provider || ""}`;
  if (f && f.total_removed) meta += ` · ${f.total_removed} junk filtered`;
  document.getElementById("hotMeta").textContent = meta;
  setHtml("hotFreshness", freshnessBanner(d.freshness));
  loadRegime();
  const NCOLS = 14;
  let html = '<table><tr><th>#</th><th>Ticker</th><th>Company</th><th>Sector</th><th>Bucket</th>' +
    '<th class="num">Price</th><th class="num">Market cap</th><th class="num">Hot</th>' +
    '<th></th><th class="num">Value</th><th class="num">Qual</th>' +
    '<th class="num">Grow</th><th class="num">Mom</th><th class="num">Fair val</th></tr>';
  d.rows.forEach(r => {
    const up = r.upside;
    html += `<tr><td>${r.rank}</td><td><a href="#" onclick="gotoValue('${r.ticker}');return false"><b>${r.ticker}</b></a></td>
      <td>${esc((r.name || "").slice(0, 22))}${_srcMark(r)}${_whyChips(r)}</td><td>${esc((r.sector || "—").slice(0, 16))}</td>
      <td><span class="pill ${r.bucket === 'established' ? 'est' : 'spec'}">${r.bucket || ''}</span></td>
      <td class="num">${money(r.price)}</td>
      <td class="num">${mcap(r.market_cap)}</td>
      <td class="num hotrow-score" style="color:${scoreColor(r.hot_score)}">${r.hot_score == null ? '—' : r.hot_score.toFixed(0)}</td>
      <td><button class="whybtn" id="whybtn-${r.ticker}" aria-expanded="false"
            onclick="toggleWhy('${r.ticker}')" title="Break this score into the themes that produced it">why?</button></td>
      <td class="num">${z(r.z_value)}</td><td class="num">${z(r.z_quality)}</td>
      <td class="num">${z(r.z_growth)}</td><td class="num">${z(r.z_momentum)}</td>
      <td class="num">${_fairValCell(r, up)}</td></tr>
      <tr class="whyrow" id="why-${r.ticker}" style="display:none"><td colspan="${NCOLS}">${
        attributionPanel(r, { of: d.scored })}</td></tr>`;
  });
  html += "</table>";
  html += `<div class="note"><b>Fair value.</b> Names marked <span class="est-mark" title="peer-relative estimate">e</span>
    use a quick peer-relative estimate (what the stock would be worth on its sector's median earnings / free-cash-flow
    yield) — the full discounted-cash-flow model is far too slow to run on every name, so only the top few carry one.
    Unmarked values are the full DCF. The estimate says "cheap versus peers", which is a rougher claim than the DCF's
    "worth this much" — open a name in Single valuation for the real model.
    A cell reading <b>withheld</b> is not missing data: the estimate came out past the same band at which the valuation
    page refuses to publish a fair value (more than 5× the price, which is almost always a currency or share-count
    problem rather than an opportunity), so it is not published here either. The ranking does not use it.
    <b>Known inconsistency, stated rather than hidden:</b> these two surfaces can still disagree. A name whose full
    model is refused outright — Kaspi, for one, where the statements and the price are in different currencies — can
    carry a peer-relative estimate here, because a ratio of two same-currency figures survives the mismatch that
    breaks the valuation. <b>When they disagree, the Single-valuation page's refusal is the one to believe</b>, and
    fixing the disagreement is open work.</div>`;
  // MA29 — "what the model cannot value". The refusal count reaches a reader, so LA1's failure
  // mode (a refusal that is recorded and then seen by nobody) is loud instead of silent. Every
  // string comes from the `refusals` block: `web/refusals.py` owns the wording and a test pins
  // it verbatim, so nothing here may paraphrase. The two KINDS are drawn as separate sentences
  // on purpose — "we could not look" must never render as "we looked and refused".
  const rf = d.refusals || null;
  if (rf && rf.available && rf.sentence) {
    const extra = [rf.unavailable_sentence, rf.display_sentence].filter(Boolean)
      .map(s => ` ${esc(s)}`).join("");
    html += `<div class="note"><b>${esc(rf.label)}.</b> ${esc(rf.sentence)}${extra} ` +
      `${esc(rf.explainer)}</div>`;
  }
  // Prefer theme_contributing over theme_coverage: a theme can be 100% "covered" and still be
  // a constant, which standardizes to nothing and drops out of the score entirely. Reporting
  // the presence number here would call such a theme healthy.
  const th = (d.health && (d.health.theme_contributing || d.health.theme_coverage)) || null;
  const hz = th ? Object.entries(th).filter(([k, v]) => v < 0.5) : [];
  if (hz.length) {
    html += `<div class="note">⚠ Themes not driving this scan: ${hz.map(([k, v]) => `${k.replace(/_/g, ' ')} ${Math.round(v * 100)}%`).join(" · ")}. ` +
      `Scores are computed on the themes that are present (the rest are neutralized and their weight redistributed), but worth a glance.</div>`;
  }
  // Where the fundamentals came from. A book built from two feeds that cover different fields
  // should never be a silent fact.
  const fu = (d.health && d.health.fundamentals) || null;
  if (fu && fu.by_source) {
    const parts = Object.entries(fu.by_source).sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `${v} ${k.replace(/\+/g, " + ")}`).join(" · ");
    html += `<div class="note">Fundamentals source: ${parts}. Names marked ` +
      `<span class="est-mark">p</span> carry broker data only — real market cap, value and quality, ` +
      `but no margins, free cash flow or revenue growth.</div>`;
  }
  // Company name / sector / market cap are invisible to every scoring check, so a gap in
  // them can sit on the live site for weeks unnoticed. Say it out loud when it happens.
  const dc = (d.health && d.health.display_coverage) || null;
  const gaps = dc ? Object.entries(dc).filter(([k, v]) => v < 0.9) : [];
  if (gaps.length) {
    html += `<div class="note">⚠ Missing display data: ${gaps.map(([k, v]) =>
      `${k.replace(/_/g, " ")} present on ${pct(v, 0)} of names`).join(" · ")}. `
      + `Scores are unaffected — this is what the table can show, not what it ranked on.</div>`;
  }
  if (d.health && d.health.universe_note) {
    html += `<div class="note">⚠ Universe: ${esc(d.health.universe_note)}.</div>`;
  }
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
function _fairValCell(r, up) {
  // A withheld estimate is not a missing one. "—" reads as "we don't have this yet" and
  // invites someone to fill it back in; this says the number existed and was refused, and
  // carries the reason with it. See web/withhold.py::withhold_implausible_fair_values.
  //
  // TWO KINDS, RENDERED DIFFERENTLY (2026-08-11). "the model rejects this valuation" and
  // "we could not fetch this name today" both blank the cell, and showing one word for both
  // turns a temporary feed problem into what reads as a permanent verdict on the company.
  // `no data` also says, in its tooltip, that the next scan retries it automatically.
  if (r.fair_value_withheld) {
    if (r.fair_value_withheld_kind === "unavailable") {
      return `<span class="muted" style="font-weight:700;font-style:italic" title="${esc(r.fair_value_withheld_reason || "")}">no data</span>`;
    }
    return `<span class="muted" style="font-weight:700" title="${esc(r.fair_value_withheld_reason || "")}">withheld</span>`;
  }
  if (r.fair_value == null) return "—";
  const est = r.fair_value_method === "multiples";
  const mark = est ? `<span class="est-mark" title="Peer-relative estimate, not the full DCF">e</span>` : "";
  const upHtml = up == null ? "" :
    ` <span class="${up >= 0 ? 'pos' : 'neg'}">(${up >= 0 ? '+' : ''}${pct(up, 0)})</span>`;
  return money(r.fair_value) + mark + upHtml;
}
function gotoValue(t) {
  switchTab("single");
  document.querySelectorAll(".tab")[0].classList.add("active");
  acClose();
  document.getElementById("ticker").value = t;
  runValue();
}

function renderSectors(sectors) {
  if (!sectors || !sectors.length) { document.getElementById("sectorBox").innerHTML = ""; return; }
  const vals = sectors.map(s => s.avg_composite || 0);
  const lo = Math.min(...vals), hi = Math.max(...vals) || 1;
  let html = "";
  sectors.forEach(s => {
    const t = (s.avg_composite - lo) / ((hi - lo) || 1);
    const col = s.avg_composite >= 0 ? "var(--green)" : "var(--amber)";
    html += `<div class="sector-bar"><span class="nm">#${s.sector_rank} ${esc(String(s.sector || "—").slice(0, 14))}</span>
      <span class="track"><span style="width:${Math.max(4, t * 100)}%;background:${col}"></span></span>
      <span style="width:96px;text-align:right;color:${col};font-weight:700">${z(s.avg_composite)} <span class="muted" style="font-weight:400">(${s.count})</span></span></div>`;
  });
  document.getElementById("sectorBox").innerHTML = html;
}

/* ====================== DIP DETECTOR ======================
   Healthy names trading well below their own 52-week high.

   THE COPY IS NOT HERE. Every claim-bearing sentence on this tab is server-rendered from
   `web/dip_posture.py` into the template, because it is written to be replaced when a register
   closes — and TWO have now closed, to opposite answers: V6 found no return edge, V6-B found a
   large and replicated reduction in how often these names fall a further 20%. Neither verdict
   appears in this file. It renders NUMBERS and the per-check badges, and the one string it does
   own — the "not checked" label — describes the payload rather than the world.

   WHY A CHECK THAT DID NOT RUN GETS ITS OWN BADGE. Two of the four disqualifiers need a full
   DCF. Rendering "not checked" as a tick would tell a reader that four things were verified
   when two were, which is the same defect as an out-of-sample block reporting zero directions
   tested as a pass. The badge is deliberately neutral-coloured: not a warning, not a tick. */
const _DIP_CHECK_LABEL = { pass: "✓", fail: "✕", not_run: "–" };

function _dipChecks(row, defs) {
  const ch = row.checks || {};
  return Object.keys(ch).sort().map(k => {
    const v = ch[k], mark = _DIP_CHECK_LABEL[v] || "?";
    const col = v === "pass" ? "var(--green)" : (v === "fail" ? "var(--red)" : "var(--muted)");
    const why = v === "not_run"
      ? "Not checked — this one needs a full discounted-cash-flow valuation, which this screen does not run for every name."
      : ((defs || {})[k] || k);
    return `<span class="chip" style="color:${col}" title="${esc(why)}">${mark} ${esc(k.replace(/_/g, " "))}</span>`;
  }).join(" ");
}

function _dipHealthChips(row, floors) {
  const h = row.health || {};
  return Object.keys(h).sort().map(k => {
    const v = h[k];
    const floor = (floors || {})[k];
    const col = (v == null) ? "var(--muted)" : scoreColor(v);
    return `<span class="chip" style="color:${col}" title="${esc(k)} ${v == null ? "not computed" : Math.round(v)} of 100, floor ${floor == null ? "—" : Math.round(floor)}">`
      + `${esc(k)} ${v == null ? "—" : Math.round(v)}</span>`;
  }).join(" ");
}

/* V6-B's per-name further-fall rate. Served on /api/dip since 2026-08-16 and, until this
   function existed, rendered to nobody: `HANDOFF_v6b_health_gap.md` §5 measured
   `grep -c dip_risk app.js` -> 0, so the class, both rates, the method note and the "not a
   probability" caveat were computed on every request and displayed to no reader.

   EVERY STRING COMES FROM THE SERVER. `web/dip_risk.py` owns the wording and a test pins it
   verbatim, so nothing here may paraphrase — the rate, the reason a row has none, the size
   caveat, the method note, the pre-filter note and the "not a probability" caveat are all
   rendered exactly as served. This file contributes layout.

   THE PEER RATE IS DELIBERATELY NOT RENDERED ON A ROW, and that is the whole point of the
   change. r1 measured that this screen's own prefilter removes M1's unhealthy side before the
   classification runs, so a listed name essentially never classifies unhealthy. Putting
   "32.5% against 43.4%" on a row would therefore invite reading the screen as having done the
   separating when the prefilter did it upstream (§6.1) — a comparison the live data cannot
   make. The panel contrast is stated ONCE below the table, as a fact about the panel, beside
   the sentence saying it does not exist here. */
function _dipRate(r) {
  const b = (r || {}).dip_risk || null;
  if (!b) return "—";
  /* A class with no rate renders its REASON, never a blank and never a zero. "shallower than
     the measurement" and "we could not place this name" are different facts and a dash that
     means both is the failure `checks_not_run` already exists to avoid. */
  if (!b.applies) {
    return `<span class="muted" title="${esc(b.why_not || "No rate applies to this name.")}">—</span>`;
  }
  const tip = [b.label, b.not_a_probability].filter(Boolean).join(" ");
  const dagger = b.size_caveat
    ? ` <span class="muted" title="${esc(b.size_caveat)}">†</span>` : "";
  return `<span title="${esc(tip)}">${pct(b.further_fall_rate, 1)}</span>${dagger}`;
}

async function loadDip() {
  eshow("dipErr", "");
  toggle("dipLoader", true);
  const sel = document.getElementById("dipThreshold");
  const thr = sel ? sel.value : "0.20";
  try {
    const d = await (await fetch("/api/dip?min_drawdown=" + encodeURIComponent(thr))).json();
    renderDip(d);
  } catch (e) {
    eshow("dipErr", e.message);
    setHtml("dipResults", "");
  }
  toggle("dipLoader", false);
}

function renderDip(d) {
  d = d || {};
  setHtml("dipDisclaimer", esc(d.disclaimer || ""));
  setHtml("dipFreshness", d.freshness ? freshnessBanner(d.freshness) : "");
  if (d.error) { eshow("dipErr", d.error); setHtml("dipResults", ""); return; }
  if (d.empty) {
    setHtml("dipResults", `<div class="card"><div class="muted">${esc(d.message || "Nothing to screen yet.")}</div></div>`);
    setHtml("dipMeta", "");
    return;
  }
  const rows = d.rows || [];

  /* THE BOUNDS ARE REPORTED, ALWAYS — including when they did not bite. A screen that says
     "12 names" without saying "out of 340 eligible, 12 measured" reads as coverage, and this
     project has paid for silent truncation before. */
  const bits = [];
  bits.push(`${num(d.n_universe)} names scanned`);
  bits.push(`${num(d.n_eligible)} passed the pre-filter`);
  /* `n_measured` counts measurement ATTEMPTS, not successes — the ones that failed are in
     `n_unmeasured` below. "fully measured" would overstate it whenever a valuation fell over. */
  bits.push(`${num(d.n_measured)} examined in detail`);
  if (d.capped) bits.push(`<b>${num(d.capped)} more not measured (per-request limit)</b>`);
  if (d.n_unmeasured) bits.push(`${num(d.n_unmeasured)} could not be measured`);
  setHtml("dipMeta", bits.join(" · "));

  if (!rows.length) {
    setHtml("dipResults", `<div class="card"><div class="muted">No name cleared a
      ${pct(d.min_drawdown, 0)} fall from its 52-week high while also scoring healthy today.
      ${d.capped ? "Note the per-request measurement limit above — this is not a statement about every name in the universe." : ""}</div></div>`);
    return;
  }

  /* The risk block's own coverage summary. Its strings are the column's vocabulary too — the
     header's tooltip is the SERVED caveat, not a second wording of it, because two copies of
     one rule is how a badge and a tooltip come to disagree. */
  const rk = d.dip_risk || {};

  let html = `<div class="card"><h3>Down ${pct(d.min_drawdown, 0)}+ from the 52-week high, fundamentals still healthy</h3>
    <div class="section-hint">${esc(d.health_floor_note || "")}</div>
    <table><tr><th>Ticker</th><th class="num">Fall from high</th><th class="num">Price</th>
      <th class="num">52-wk high</th><th>Health</th><th class="num">Fair value</th>
      <th class="num" title="${esc(rk.not_a_probability || "")}">Past group rate</th>
      <th>Checks</th></tr>`;
  rows.forEach(r => {
    const fv = r.fair_value_withheld_reason
      ? `<span class="muted" title="${esc(r.fair_value_withheld_reason)}">withheld</span>`
      : (r.fair_value == null ? "—" : money(r.fair_value));
    html += `<tr>
      <td><a href="#" onclick="gotoValue('${esc(r.ticker)}');return false"><b>${esc(r.ticker)}</b></a>
        <div class="muted" style="font-size:11px">${esc(String(r.name || "").slice(0, 28))}</div></td>
      <td class="num neg">−${pct(r.drawdown, 1)}</td>
      <td class="num">${money(r.price)}</td>
      <td class="num">${money(r.high_52w)}</td>
      <td>${_dipHealthChips(r, d.health_floors)}</td>
      <td class="num">${fv}</td>
      <td class="num">${_dipRate(r)}</td>
      <td>${_dipChecks(r, d.checks)}</td></tr>`;
  });
  html += "</table>";
  if (rows.some(r => (r.checks_not_run || []).length)) {
    html += `<div class="note" style="margin-top:10px">A “–” means that check was <b>not run</b>
      for this name, not that it passed. Two of the four need a full discounted-cash-flow
      valuation, which this screen does not run for every name.</div>`;
  }
  /* The rate never appears without its scope. `HANDOFF_v6b_health_gap.md` §6.1 is explicit that
     a bare percentage beside a list of names is "the one presentation §3 and §4 do not
     support", so the method note and the pre-filter note render whenever any rate does —
     rendered from the payload, in the server's words, and only when there is a rate to
     qualify. */
  if (rows.some(r => ((r.dip_risk || {}).applies))) {
    html += `<div class="note" style="margin-top:10px"><b>Past group rate.</b>
      ${esc(rk.screen_contrast_note || "")} ${esc(rk.method_note || "")}
      ${esc(rk.not_a_probability || "")}</div>`;
  }
  if (rows.some(r => ((r.dip_risk || {}).size_caveat))) {
    html += `<div class="note" style="margin-top:6px">† ${esc(
      (rows.find(r => (r.dip_risk || {}).size_caveat).dip_risk || {}).size_caveat || "")}</div>`;
  }
  html += "</div>";
  setHtml("dipResults", html);
}

/* ====================== SCREAM-BUY TRACK RECORD ======================
   Reset 2026-08-13 at Don's direction; the prior record is archived, not deleted, and the
   register note below renders with the table every time. Entry / target / stop / current are
   READ from the stored columns — see web/scream_track.py for why re-deriving them would look
   right and be wrong. */
/* Six statuses, not five. `CLOSED (unscoreable)` is the logger's own sixth: a closed row whose
   exit reason maps to none of Don's five must not be forced into one that misdescribes it. It
   is deliberately muted rather than red — unscoreable is not a loss. */
function _screamStatusColor(s) {
  if (s === "HIT TARGET") return "var(--green)";
  if (s === "STOPPED") return "var(--red)";
  if (s === "LIVE") return "var(--navy)";
  return "var(--muted)";
}

async function loadScreamTrack() {
  const box = document.getElementById("screamTrack");
  if (!box) return;
  let d;
  try { d = await (await fetch("/api/scream-track")).json(); } catch (e) { return; }
  box.style.display = "";
  renderScreamTrack(d || {});
}

function renderScreamTrack(d) {
  const foot = d.summary || {};
  const reset = d.reset || null;
  setHtml("screamContext", esc(d.context || ""));
  const rows = d.rows || [];

  let body;
  if (!rows.length) {
    body = `<div class="muted">${d.unavailable
      ? "The record could not be read just now."
      : "No scream-buy alerts in the current record yet."}</div>`;
  } else {
    body = `<div class="metricline" style="margin:6px 0 12px">
      ${metric("Live", d.n_live)}${metric("Closed", d.n_closed)}
      ${metric("Record", foot.epoch || "—")}</div>`;
    /* dte_at_alert and dte_remaining are DIFFERENT QUANTITIES and the logger's contract says
       not to render them as one. Both columns, both labelled. */
    body += `<table><tr><th>Alert</th><th>Contract</th><th>Status</th>
      <th class="num">Bought in</th><th class="num">Target sale</th><th class="num">Stop</th>
      <th class="num">Current</th><th class="num">P&amp;L</th>
      <th class="num">DTE now</th><th class="num">DTE at alert</th></tr>`;
    rows.forEach(r => {
      const col = _screamStatusColor(r.status);
      /* A stale mark is LABELLED, never silently rendered as current. The logger sets
         current_premium_stale true when the quote is older than its own window OR when no
         quote arrived at all — absent is not fresh, and a row the market could not price must
         never render as a live price. */
      const age = r.current_premium_age_seconds;
      const stale = r.current_premium_stale
        ? ` <span class="muted" title="Quoted ${esc(r.current_premium_ts || "never")}${age == null ? "" : " — " + Math.round(age / 60) + " min ago"}">⚠ stale</span>`
        : "";
      const contract = [r.opt_right ? String(r.opt_right).toUpperCase() : "",
        r.strike == null ? "" : money(r.strike, 2), r.expiry || ""].filter(Boolean).join(" ");
      /* A non-default exit policy is flagged, because the whole point of reading the stored
         level rather than deriving it is that the policy can differ from +100%/-50%. */
      const pol = (r.policy_is_default === false)
        ? ` <span class="muted" title="This alert carries its own exit policy, not the default +100%/-50%.">·custom</span>` : "";
      const live = r.pnl_pct_live;
      body += `<tr>
        <td><b>${esc(r.ticker || "—")}</b><div class="muted" style="font-size:11px">${esc(String(r.alert_ts || "").slice(0, 10))}</div></td>
        <td style="font-size:12px">${esc(contract || r.occ_symbol || "—")}</td>
        <td style="color:${col};font-weight:700">${esc(r.status)}${stale}</td>
        <td class="num">${money(r.entry_premium)}</td>
        <td class="num">${money(r.target_premium)}${r.target_pct == null ? "" : ` <span class="muted">(${spct(r.target_pct, 0)})</span>`}${pol}</td>
        <td class="num">${money(r.stop_premium)}${r.stop_pct == null ? "" : ` <span class="muted">(${spct(r.stop_pct, 0)})</span>`}</td>
        <td class="num">${money(r.current_premium)}</td>
        <td class="num ${live == null ? "" : (live >= 0 ? "pos" : "neg")}">${live == null ? (r.pnl_pct == null ? "—" : spct(r.pnl_pct, 0)) : spct(live, 0)}</td>
        <td class="num">${r.dte_remaining == null ? "—" : r.dte_remaining + "d"}</td>
        <td class="num muted">${r.dte_at_alert == null ? "—" : r.dte_at_alert + "d"}</td></tr>`;
    });
    body += "</table>";
  }

  const lc = d.paper_level_conformance;
  if (lc && lc.off_spec) {
    body += `<div class="note" style="margin-top:10px;border-left:3px solid #c0392b;padding-left:9px">
      ⚠️ <b>${num(lc.off_spec)} live PAPER position(s) are trading to a target or stop the
      strategy does not specify.</b> That is the paper book, a different object from this
      record. Reported read-only; the next paper cycle repairs them.</div>`;
  }
  setHtml("screamBody", body);

  /* THE FOOTER. `reset` is null until a reset has ACTUALLY run — the record cannot be reset
     from a dev box — so the surface says the record is original rather than implying a reset
     happened. `n_prior_epochs` is what makes a reset visible rather than merely honest. */
  let note;
  if (reset && reset.note) {
    note = esc(reset.note);
    if (foot.n_prior_epochs) {
      note += ` <b>${num(foot.n_prior_epochs)} earlier record${foot.n_prior_epochs === 1 ? "" : "s"}</b> remain queryable — nothing was deleted.`;
    }
  } else {
    note = "This is the original record — it has not been reset. Nothing here has ever been "
      + "deleted, and a reset would archive first and keep the prior rows queryable.";
  }
  setHtml("screamRegister", note);
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
  html += '<table><tr><th>Ticker</th><th>Company</th><th>Sector</th><th class="num">Weight</th><th class="num">Hot</th></tr>';
  pf.positions.forEach(p => {
    html += `<tr><td><b>${p.ticker}</b></td><td>${esc((p.name || '').slice(0, 24))}</td>
      <td>${esc((p.sector || '—').slice(0, 16))}</td>
      <td class="num">${pct(p.weight, 1)}</td><td class="num">${p.hot_score == null ? '—' : p.hot_score.toFixed(0)}</td></tr>`;
  });
  html += "</table>";
  html += `<div class="note">Max sector weight ${pct(s.max_sector_weight, 0)} (cap ${pct(s.max_sector_cap, 0)}). Exposures — value ${z(s.exposure_value)}, quality ${z(s.exposure_quality)}, growth ${z(s.exposure_growth)}, momentum ${z(s.exposure_momentum)}.</div>`;
  document.getElementById("portfolioBox").innerHTML = html;
}

/* ====================== TRACK RECORD ====================== */
async function loadTrack() {
  eshow("trackErr", "");
  // /api/track can kick off a background refresh, so it is the slowest read in the app and
  // the one most worth painting from cache first.
  const cached = cacheGet("track");
  if (cached) { try { renderTrack(cached.d); } catch (e) { } }
  else { document.getElementById("trackResults").innerHTML = skeleton(6, { head: true }); }
  toggle("trackLoader", false);
  try {
    const res = await fetch("/api/track");
    const d = await res.json();
    renderTrack(d);
    cacheSet("track", d);
  } catch (e) {
    eshow("trackErr", e.message);
    if (!cached) document.getElementById("trackResults").innerHTML = "";
  }
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
  const sig = b.t_stat == null ? '' :
    ` · t-stat ${b.t_stat.toFixed(1)} <b class="${b.significant ? 'pos' : ''}">(${b.significant ? 'significant' : 'not significant yet'})</b>`;
  const benchLine = (b.avg_alpha != null || b.spy_all_time != null)
    ? `<div class="note" style="margin:2px 0 8px">vs <b>S&amp;P 500</b> (net of costs): ` +
      (b.avg_alpha != null ? `avg <b class="${b.avg_alpha >= 0 ? 'pos' : 'neg'}">${b.avg_alpha >= 0 ? '+' : ''}${pct(b.avg_alpha, 1)}</b> alpha per closed pick` : '') +
      (b.spy_all_time != null ? ` · S&amp;P returned ${pct(b.spy_all_time, 1)} over the same span` : '') + sig + `</div>`
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
const SIG_HORIZONS = ["short", "swing", "position"];
const SIG_HZ_LABEL = { short: "short (3–5 wk)", swing: "swing (6–11 wk)", position: "position (3–6 mo)" };

function renderSignals(d) {
  if (!d) return;
  setHtml("sigFreshness", freshnessBanner(d.freshness));
  setHtml("sigDisclaimer", d.disclaimer ? esc(d.disclaimer) : "");
  document.getElementById("sigMeta").textContent = "";
  document.getElementById("sigTime").textContent = d.run_time ? ("updated " + d.run_time) : "";
  const hz = (document.getElementById("sigHorizon") || {}).value || "all";
  const dir = (document.getElementById("sigDir") || {}).value || "bull";
  const bear = dir === "bear";
  const all = hz === "all";
  const scoreKey = bear ? "scores_bear" : "scores";
  const contractKey = bear ? "contracts_bear" : "contracts";

  // Score for one specific horizon. Falls back to the row's headline score on the bull
  // side (which is the swing read) when the per-horizon map is missing.
  const scoreAt = (r, h) => {
    const m = r.detail && r.detail[scoreKey];
    return (m && m[h] != null) ? m[h] : (bear ? null : (h === "swing" ? r.score : null));
  };
  // "All" merges the horizons into one list: each name is ranked on its BEST setup, and
  // we remember which horizon that was so the contract idea and label match it.
  const best = r => {
    if (!all) { const s = scoreAt(r, hz); return s == null ? null : { h: hz, s }; }
    let b = null;
    SIG_HORIZONS.forEach(h => {
      const s = scoreAt(r, h);
      if (s != null && (b == null || s > b.s)) b = { h, s };
    });
    return b;
  };

  const labelsFor = r => bear ? ((r.detail && r.detail.labels_bear) || []) : (r.labels || []);
  const rows = (d.rows || []).slice()
    .map(r => ({ r, b: best(r) }))
    .filter(x => x.b != null)
    .sort((a, b) => b.b.s - a.b.s);

  const head = (bear ? "bearish · " : "") + (all ? "best horizon" : SIG_HZ_LABEL[hz] || hz);
  let html = '<table><tr><th>#</th><th>Ticker</th><th class="num">Score</th>' +
    (all ? '<th>Horizon</th>' : '') +
    `<th>Setup / signals</th><th>Contract idea (${head})</th><th>AI read</th></tr>`;
  rows.forEach((x, i) => {
    const r = x.r, s = x.b.s, h = x.b.h;
    const badges = labelsFor(r).slice(0, 3).map(l => `<span class="pill ${bear ? 'spec' : 'est'}" style="margin:1px 2px">${l}</span>`).join(" ");
    const c = (r.detail && r.detail[contractKey] && r.detail[contractKey][h]) || null;
    const cHtml = c
      ? `<div style="font-size:12px"><b>${c.directional}</b><br><span class="muted">${c.defined_risk}</span></div>`
      : '<span class="muted">—</span>';
    html += `<tr><td>${i + 1}</td><td><a href="#" onclick="gotoValue('${r.ticker}');return false"><b>${r.ticker}</b></a></td>
      <td class="num" style="font-weight:800;color:${scoreColor(s)}">${s == null ? '' : s.toFixed(0)}</td>` +
      (all ? `<td style="font-size:12px">${SIG_HZ_LABEL[h] || h}</td>` : '') +
      `<td style="max-width:240px">${badges}</td>
      <td style="max-width:270px">${cHtml}</td>
      <td style="max-width:260px;font-size:12.5px" class="muted">${bear ? '' : (r.ai || r.summary || '')}</td></tr>`;
  });
  html += "</table>";
  if (all) {
    html += `<div class="note">Every horizon merged into one list — each name is ranked on its strongest setup, and the
      Horizon column shows which one that is. Pick a specific horizon above to see the list for just that timeframe.</div>`;
  }
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

function _wstr(w) {
  if (!w) return "—";
  return Object.entries(w).map(([k, v]) => `${k[0].toUpperCase() + k.slice(1, 3)} ${(+v).toFixed(2)}`).join(" · ");
}
async function edgeLearning() {
  toggle("edgeLoader", true); eshow("edgeErr", ""); document.getElementById("edgeMsg").textContent = "Loading self-learning log…";
  try {
    const res = await fetch("/api/edge/learning");
    if (res.status === 403) { eshow("edgeErr", "Owner-only research tools."); return; }
    renderLearning(await res.json());
  } catch (e) { eshow("edgeErr", e.message); }
  finally { toggle("edgeLoader", false); }
}
/* The theme legend — inputs, and whether a theme reaches a live score.

   THIS USED TO BE A HARDCODED MAP HERE, AND IT WENT WRONG IN THE WORST POSSIBLE PLACE. On
   2026-08-11 it described `capital_discipline` as "low share issuance · low asset growth
   (dormant — needs data)" on the exact day that theme was restored to the live scoring path —
   the adoption that opened vintage 3 — and it named an input (asset growth) that factors.py had
   stopped averaging into the theme.

   Worth being precise about which half was broken, because it is not the obvious one: the BARS
   were always data-driven and picked the fifth theme up on their own, since they enumerate
   whatever weights the payload carries. What was hardcoded was the CAPTION UNDER the bar, and a
   confident wrong caption is worse than a missing bar — a missing bar invites a question, a
   caption closes one.

   Now served from valuation/web/theme_status.py as window.THEME_STATUS and only escaped here,
   the same one-source rule as _SCORE_CONF and _HOLD_H. tests/test_theme_status.py fails if this
   file grows its own copy back. */
const _THEME_STATUS = (typeof window !== "undefined" && window.THEME_STATUS) || {};
function _themeInputs(k) { return (_THEME_STATUS[k] || {}).inputs || ""; }
function _themeDormant(k) { return (_THEME_STATUS[k] || {}).dormant || ""; }
function _themeBars(w) {
  if (!w) return "<div class='muted'>—</div>";
  const entries = Object.entries(w).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(e => e[1]), 0.01);
  return entries.map(([k, v]) => {
    const label = pct(v, 0), wd = Math.round(v / max * 100);
    // A theme carrying weight while contributing nothing is the failure mode this legend
    // exists to make visible (`insider` is the standing example — 100% "covered", constant,
    // renormalised away). So the dormancy note is rendered as its own flagged line rather
    // than folded into the input list, where it read as one more ingredient.
    const dormant = _themeDormant(k);
    return `<div style="margin:5px 0">
      <div style="display:flex;justify-content:space-between;font-size:12px">
        <span style="text-transform:capitalize"><b>${k.replace(/_/g, " ")}</b></span><span>${label}</span></div>
      <div style="background:#eef;border-radius:4px;height:8px"><div style="width:${wd}%;background:#3454a4;height:8px;border-radius:4px"></div></div>
      <div class="muted" style="font-size:11px">${esc(_themeInputs(k))}</div>
      ${dormant ? `<div class="muted" style="font-size:11px;font-style:italic">⚠ ${esc(dormant)}</div>` : ""}</div>`;
  }).join("");
}
function _numberICSection(nic) {
  if (!nic) return `<div class="section-hint" style="margin-top:14px"><b>Number diagnostics:</b> computed on the monthly learning run — nothing yet.</div>`;
  if (nic.status !== "ok") return `<div class="section-hint" style="margin-top:14px"><b>Number diagnostics:</b> not enough history yet (${nic.dates || 0} scan dates) to measure individual numbers.</div>`;
  const nums = nic.numbers || [], byTheme = {};
  nums.forEach(r => { (byTheme[r.theme] = byTheme[r.theme] || []).push(r); });
  const maxAbs = Math.max(...nums.map(r => Math.abs(r.ic || 0)), 0.01);
  let s = `<h4 style="margin:16px 0 4px">Which numbers are pulling weight</h4>
    <div class="section-hint" style="margin-top:0">Each number's standalone predictive power (information coefficient) over
    ${nic.dates} scan dates, ~${nic.horizon}-day forward returns. <b>Visibility only</b> — numbers stay equal-weighted inside a
    theme; use this to retire a dead one or promote a strong one by hand. Green = predictive, red = inverted, grey = no data yet.</div>`;
  Object.keys(byTheme).forEach(theme => {
    s += `<div style="margin:8px 0 2px;text-transform:capitalize"><b>${theme.replace(/_/g, " ")}</b></div>`;
    byTheme[theme].forEach(r => {
      const has = r.ic != null, col = !has ? "#bbb" : (r.ic >= 0 ? "#1a7f37" : "#c0392b");
      const wd = has ? Math.round(Math.abs(r.ic) / maxAbs * 100) : 0, cov = Math.round((r.coverage || 0) * 100);
      s += `<div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:12px">
        <span style="width:130px">${r.number.replace(/_/g, " ")}</span>
        <div style="flex:1;background:#eef;border-radius:4px;height:7px"><div style="width:${wd}%;background:${col};height:7px;border-radius:4px"></div></div>
        <span style="width:60px;text-align:right;color:${col}">${has ? r.ic.toFixed(3) : "—"}</span>
        <span style="width:42px;text-align:right" class="muted">${cov}%</span></div>`;
    });
  });
  return s;
}
function _fundamentalBTSection(fb) {
  if (!fb) return `<div class="section-hint" style="margin-top:14px"><b>Historical backtest:</b> connect a point-in-time data source (Sharadar/WRDS) and run it to see the full model vs the S&P over real history.</div>`;
  if (fb.ready === false) return `<div class="section-hint" style="margin-top:14px"><b>Historical backtest:</b> ${fb.message || 'data source not configured.'}</div>`;
  const hs = fb.horizons || {}, keys = Object.keys(hs).sort((a, b) => (+a) - (+b));
  if (!keys.length) return `<div class="section-hint" style="margin-top:14px"><b>Historical backtest:</b> no results yet — run it once your data key is set.</div>`;
  const row = (lab, b) => { b = b || {}; const a = (b.cagr || 0) - (b.bench_cagr || 0); return `<tr><td>${lab}</td><td class="num">${pct(b.cagr, 1)}</td><td class="num">${pct(b.bench_cagr, 1)}</td>
    <td class="num ${a >= 0 ? 'pos' : 'neg'}">${a >= 0 ? '+' : ''}${pct(a, 1)}</td>
    <td class="num">${pct(b.hit_rate, 0)}</td></tr>`; };
  let s = `<h4 style="margin:16px 0 4px">Historical backtest vs S&P — ${fb.provider}${fb.survivorship_free ? ' · survivorship-free' : ''}</h4>
    <div class="section-hint" style="margin-top:0">Recency half-life ${fb.recency_halflife_years || '?'}y · primary (adopted) horizon <b>${fb.primary_horizon || '—'}</b> trading days. Weights are adopted only where they beat the default out-of-sample.</div>`;
  keys.forEach(H => {
    const r = hs[H];
    if (r.status) { s += `<div class="muted" style="font-size:12px">Horizon ${H}d: ${r.status}.</div>`; return; }
    s += `<div style="margin-top:8px"><b>Horizon ${H} trading days</b> — ${r.names} names · ${r.dates} dates · optimized beats default OOS: <b class="${r.accepted ? 'pos' : ''}">${r.accepted ? 'yes' : 'no'}</b>${r.out_sample_ic != null ? ` (OOS IC ${(+r.out_sample_ic).toFixed(3)})` : ''}
      <table><tr><th>Weights</th><th class="num">CAGR/yr</th><th class="num">S&amp;P/yr</th><th class="num">Alpha</th><th class="num">Hit</th></tr>${row('Default', r.backtest_default)}${row('Optimized', r.backtest_optimized)}</table>
      <div class="muted" style="font-size:11px">Optimized: ${_wstr(r.optimized_weights)}</div></div>`;
  });
  s += `<div class="muted" style="font-size:11px;margin-top:6px">Lock the primary horizon's optimized weights into the live tuner: <code>POST /admin/adopt-backtest-weights</code> (only works when it beat default OOS).</div>`;
  return s;
}
function renderLearning(d) {
  const cur = d.current || {}, hist = d.history || [];
  let h = `<div class="card"><h3>🧠 Self-learning — live theme weights</h3>
    <div class="section-hint">A monthly, <b>out-of-sample-gated</b> re-tune, learned from the tool's own snapshots + realized
      forward returns. A change is adopted <b>only</b> if it beats the current weights out-of-sample. <b>The theme weights below
      are what gets tuned;</b> inside each theme the individual numbers are equal-weighted (a deliberately robust choice).</div>
    <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:10px">
      <div style="flex:1;min-width:260px"><span class="pill est">Established</span>${_themeBars(cur.established)}</div>
      <div style="flex:1;min-width:260px"><span class="pill spec">Speculative</span>${_themeBars(cur.speculative)}</div></div>`;
  h += _numberICSection(d.number_ic);
  h += _fundamentalBTSection(d.fundamental_backtest);
  if (!hist.length) {
    h += `<div class="muted" style="margin-top:10px">No learning runs yet — it kicks off monthly once enough track-record history has
      accrued (and correctly declines to change anything until then, so these stay at their starting values).</div>`;
  } else {
    h += '<h4 style="margin:14px 0 6px">Change log</h4><table><tr><th>When</th><th>Bucket</th><th>Adopted</th><th class="num">OOS IC</th><th>Note</th></tr>';
    hist.forEach(r => {
      const st = r.stats || {};
      h += `<tr><td>${(r.created_at || '').slice(0, 10)}</td><td style="text-transform:capitalize">${r.bucket}</td>
        <td>${r.adopted ? '<span class="pill est">adopted</span>' : '<span class="muted">held</span>'}</td>
        <td class="num">${st.out_sample_ic == null ? '—' : (+st.out_sample_ic).toFixed(3)}</td>
        <td style="font-size:12px;max-width:320px" class="muted">${r.note || ''}</td></tr>`;
    });
    h += '</table>';
  }
  document.getElementById("edgeResults").innerHTML = h + '</div>';
}

/* small helpers */
function toggle(id, on) { const e = document.getElementById(id); if (e) e.classList.toggle("on", on); }
function eshow(id, msg) { const e = document.getElementById(id); if (e) { e.textContent = msg; e.classList.toggle("on", !!msg); } }

/* ---------- skeletons ----------
   A spinner says "something is happening"; a skeleton says "content of about this shape is
   coming", which is why the wait feels shorter even when it isn't. Deliberately NOT used for
   anything whose shape we can't honestly predict — a skeleton table that resolves to "no data"
   has promised something that never arrives. */
function skeleton(rows, opts) {
  const o = opts || {};
  let h = "";
  if (o.head) h += `<div class="sk sk-head"></div>`;
  for (let i = 0; i < (rows || 3); i++) {
    h += `<div class="sk sk-row" style="width:${[100, 92, 84, 96, 88][i % 5]}%"></div>`;
  }
  return `<div class="sk-wrap" aria-busy="true" aria-live="polite">${h}
    <span class="sk-sr">Loading…</span></div>`;
}
/* A skeleton shaped like the table that is coming, so the page doesn't jump when it lands. */
function skeletonTable(rows, cols) {
  const n = cols || 6;
  let h = `<div class="sk-tbl" aria-busy="true"><div class="sk-tr head">` +
    Array.from({ length: n }, () => `<div class="sk sk-cell"></div>`).join("") + `</div>`;
  for (let i = 0; i < (rows || 8); i++) {
    h += `<div class="sk-tr">` +
      Array.from({ length: n }, () => `<div class="sk sk-cell"></div>`).join("") + `</div>`;
  }
  return h + `<span class="sk-sr">Loading…</span></div>`;
}

/* ---------- last-good cache (perceived speed) ----------
   These tabs read a snapshot that only changes once a day, so re-fetching before painting
   anything means staring at a spinner for data the browser already had. The last good
   payload is stored and painted IMMEDIATELY on open, then replaced by the live fetch.

   Two rules keep this from becoming a lie. A cached paint is LABELLED as one until the
   refresh lands — silently serving yesterday's ranking as today's is precisely the failure
   the freshness banner was built for. And the cache hard-expires, so a browser left open
   over a long weekend re-fetches rather than painting something days old. The payload
   carries its own scan_date and freshness block, so the stale banner renders from the cache
   too and cannot be lost by caching. */
const CACHE_PREFIX = "valquo-cache:";
const CACHE_TTL_MS = 36 * 3600 * 1000;

function cacheGet(key) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || !o.t || (Date.now() - o.t) > CACHE_TTL_MS) return null;
    return o;
  } catch (e) { return null; }
}
function cacheSet(key, data) {
  try { localStorage.setItem(CACHE_PREFIX + key, JSON.stringify({ t: Date.now(), d: data })); }
  catch (e) { }                       // private mode / quota — the app works without it
}
function cacheAge(o) {
  const mins = Math.round((Date.now() - o.t) / 60000);
  if (mins < 1) return "moments ago";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  return h < 24 ? `${h} hour${h === 1 ? "" : "s"} ago` : `${Math.round(h / 24)} day(s) ago`;
}
function cacheBanner(id, o) {
  setHtml(id, o ? `<div class="cachebar">Showing your last copy (loaded ${cacheAge(o)}) —
    refreshing…</div>` : "");
}

// ---------------------------------------------------------------------------------------- //
// THE DISTRIBUTION, NOT THE AVERAGE.
//
// A hit rate and a mean expectancy describe a convex book badly: "35% win, +3.4%/trade" is
// true and tells a reader nothing about what their own run of trades will feel like. This
// draws the banked outcome distribution as a single stacked bar, worst outcome on the left,
// so "most of these lose a little and a few win a lot" is visible instead of asserted.
//
// It renders ABOVE the alert table on purpose. An explanation of losing streaks that only
// appears once someone is down reads as an excuse; the same sentence before they start is an
// expectation. Numbers come from /api/whatdo's payoff block (valuation/web/payoff.py) — this
// file computes none of them.
// ---------------------------------------------------------------------------------------- //
const PAYOFF_COLOR = {
  near_total_loss: "#8b1a1a", stopped_out: "#c0392b", small_loss: "#e08e6d",
  small_win: "#7fb069", big_win: "#2d7a3e",
};

// One stacked bar. Shared so the public panel and the owner card cannot draw the same
// distribution two different ways.
function payoffBar(p, height) {
  return `<div style="display:flex;height:${height}px;border-radius:4px;overflow:hidden">` +
    p.buckets.map(b =>
      `<div title="${esc(b.label)} (${esc(b.detail)}): ${pct(b.share, 1)}"
            style="width:${(b.share * 100).toFixed(2)}%;background:${PAYOFF_COLOR[b.key] || "#888"}"></div>`
    ).join("") + `</div>`;
}

// The public, compact form: the bar, the shape in one sentence, the streak expectation, and
// the refusal to call any of it evidence. Returns "" when there is no payoff block, so a
// caller can concatenate it unconditionally.
function payoffCompact(p) {
  if (!p || !p.buckets) return "";
  const s = p.streaks || {};
  return `<div class="note" style="margin-top:8px">
    <b>What an options trade here looks like</b>
    <div style="margin:7px 0">${payoffBar(p, 14)}</div>
    <div>${esc(p.headline)}</div>
    <div style="margin-top:6px">${esc(s.expectation || "")}</div>
    <div class="muted" style="margin-top:6px">${esc(p.not_a_claim || "")}</div>
  </div>`;
}

function renderPayoff(p) {
  const card = document.getElementById("payoffCard");
  if (!card || !p || !p.buckets) return;
  card.style.display = "";
  const bars = payoffBar(p, 22);
  const legend = p.buckets.slice().reverse().map(b =>
    `<div style="display:flex;align-items:center;gap:6px;font-size:12px">
       <span style="width:10px;height:10px;border-radius:2px;flex:none;
                    background:${PAYOFF_COLOR[b.key] || "#888"}"></span>
       <b>${pct(b.share, 1)}</b><span class="muted">${esc(b.label)} (${esc(b.detail)})</span>
     </div>`).join("");
  const s = p.streaks || {};
  setHtml("payoffBody",
    `<div style="margin-bottom:10px">${bars}</div>
     <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:4px 14px;margin-bottom:10px">${legend}</div>
     <div class="note" style="margin-bottom:8px">${esc(p.headline)}</div>
     <div class="note" style="margin-bottom:8px"><b>${esc(s.expectation || "")}</b>
       <br><span class="muted">Independence would predict a worst run of about ${s.iid_p95} at the
       95th percentile; the measured figure is ${s.p95}, because outcomes cluster in time.
       ${esc(s.source || "")}.</span></div>
     <div class="note"><b>This is not a claim that the alerts work.</b> ${esc(p.not_a_claim || "")}
       <br><span class="muted">${esc(p.source || "")} — ${esc(p.basis || "")}.</span></div>`);
}

// The realized losing run against that distribution. The only part of this feature that can
// tell a reader something is genuinely wrong, so it is styled by verdict rather than always
// reassuring: `ordinary` is quiet, everything else is a warning.
function renderStreak(st) {
  if (!st || !st.verdict) { setHtml("optStreak", ""); return; }
  if (st.verdict === "too_few") {
    setHtml("optStreak", `<div class="note muted">${esc(st.text)}</div>`);
    return;
  }
  const ok = st.verdict === "ordinary";
  const live = st.current_loss_run
    ? ` Currently ${st.current_loss_run} in a row${st.current_is_longest ? " — the longest so far" : ""}.`
    : "";
  setHtml("optStreak",
    `<div class="note" style="${ok ? "" : "border-left:3px solid #c0392b;padding-left:9px"}">
       ${ok ? "" : "⚠️ "}<b>Losing streak: ${esc(st.verdict.replace(/_/g, " "))}.</b>
       ${esc(st.text)}${esc(live)}</div>`);
}

// ---------------------------------------------------------------------------------------- //
// Scream-buy options expectancy. EXPECTANCY, not "success rate": with a payoff this
// asymmetric a hit rate on its own is uninformative — a 40%-hit setup whose winners triple
// beats a 70%-hit one that gives it back. So win/loss size and profit factor sit next to it.
// It now also renders the payoff shape and the running losing streak, above the table.
// ---------------------------------------------------------------------------------------- //
async function loadOptionsScorecard() {
  const box = document.getElementById("optScorecard");
  if (!box) return;
  let d;
  try {
    d = await (await fetch("/api/options-scorecard")).json();
  } catch (e) { return; }
  renderPayoff(d && d.payoff);
  renderStreak(d && d.streak);
  const o = (d && d.overall) || {};
  const n = o.n_closed || 0, open = d.n_open || 0;
  box.style.display = "";
  const note = document.getElementById("optScoreNote");
  if (!n) {
    note.textContent = `No closed trades yet — ${open} alert${open === 1 ? "" : "s"} logged and `
      + `awaiting outcomes. Contract results are written back by the Robinhood job; until then `
      + `there is nothing to score.`;
    document.getElementById("optScoreBody").innerHTML = "";
    return;
  }
  note.innerHTML = `<b>${n}</b> closed · <b>${open}</b> open · expectancy is per trade on the `
    + `premium, 1-contract basis. ${n < (d.min_closed_per_bucket || 30)
      ? `<b>Below the ${d.min_closed_per_bucket || 30}-trade floor</b> — read as directional only; `
        + `no criterion is tuned on this.` : ``}`;
  const rows = [
    ["Expectancy / trade", spct(o.expectancy_pct)],
    ["Hit rate", pct(o.hit_rate)],
    ["Avg win", spct(o.avg_win_pct)],
    ["Avg loss", spct(o.avg_loss_pct)],
    ["Profit factor", o.profit_factor == null ? "— (undefined)" : num(o.profit_factor, 2)],
    ["Cumulative P&L (1 contract)", o.cum_pnl_dollars == null ? "—"
      : (o.cum_pnl_dollars >= 0 ? "+" : "−") + money(Math.abs(o.cum_pnl_dollars), 0)],
  ];
  let html = '<table class="tbl"><tbody>' + rows.map(
    r => `<tr><td class="muted">${r[0]}</td><td style="text-align:right"><b>${r[1]}</b></td></tr>`
  ).join("") + "</tbody></table>";
  const buckets = (d.buckets || {});
  const dims = Object.keys(buckets);
  if (dims.length) {
    html += '<div class="note" style="margin-top:12px">By setup — a bucket under the trade '
      + 'floor is shown but is <b>not</b> actionable:</div>';
    html += '<table class="tbl"><thead><tr><th>setup</th><th>n</th><th>expectancy</th>'
      + '<th>hit</th><th>profit factor</th></tr></thead><tbody>';
    dims.forEach(dim => Object.keys(buckets[dim]).forEach(b => {
      const s = buckets[dim][b];
      const thin = !s.enough_to_tune;
      html += `<tr style="${thin ? "opacity:.55" : ""}"><td>${dim}: ${b}${thin ? " ⚠" : ""}</td>`
        + `<td>${s.n_closed}</td><td>${spct(s.expectancy_pct)}</td><td>${pct(s.hit_rate)}</td>`
        + `<td>${s.profit_factor == null ? "—" : num(s.profit_factor, 2)}</td></tr>`;
    }));
    html += "</tbody></table>";
  }
  const tune = d.tuning || {};
  if (tune.ready && (tune.suggestions || []).length) {
    html += '<div class="note" style="margin-top:12px"><b>Enough evidence to tune:</b><ul>'
      + tune.suggestions.map(s => `<li>${s.note}</li>`).join("") + "</ul></div>";
  } else {
    html += `<div class="note" style="margin-top:12px">Not enough closed trades to tune any `
      + `criterion yet (need ${d.min_closed_per_bucket || 30} per bucket).</div>`;
  }
  document.getElementById("optScoreBody").innerHTML = html;
}


/* ====================== FRESHNESS ======================
   The scan stopped running on 2026-07-29 and the site served that snapshot as if it were
   today's for four days. Nothing looked broken — the numbers had just stopped being about
   now. Every scan-derived surface renders this, and a stale one says so loudly. */
function setHtml(id, html) { const el = document.getElementById(id); if (el) el.innerHTML = html; }

function freshnessBanner(f) {
  if (!f) return "";
  if (f.level === "fresh") {
    return `<div class="muted" style="font-size:12px;margin-top:8px">🕒 ${esc(f.message)}</div>`;
  }
  const bad = f.level === "stale" || f.level === "unknown";
  return `<div class="note" style="margin-top:8px;${bad
    ? "background:#fdecec;border-color:#f3c2c2;color:#8a1c1c;font-weight:600" : ""}">`
    + `${bad ? "⚠ " : "🕒 "}${esc(f.message)}</div>`;
}

// ---------------------------------------------------------------------------------------- //
// Valquo Index — the constructed top-slice of the SAME ranking Hot Stocks shows. One ranking,
// two views: Hot Stocks is discovery, the Index is the book you would hold. The account-type
// toggle switches which validated construction is applied (roth vs taxable).
// ---------------------------------------------------------------------------------------- //
async function loadValquoIndex() {
  const body0 = document.getElementById("valquoIndexBody");
  if (!body0) return;
  const cfg = (document.getElementById("bookConfig") || {}).value || "roth";
  // The Index is the tab people open on a phone, on a cold connection. Cached holdings paint
  // first; the skeleton only shows on a genuinely first visit.
  const cached = cacheGet("index:" + cfg);
  if (cached) {
    try { _renderValquoIndex(cached.d, cfg); } catch (e) { }
    setHtml("indexFreshness", "");     // stale verdict, cached — see loadHotStocks
    cacheBanner("indexCache", cached);
  } else { setHtml("valquoIndexBody", skeletonTable(8, 7)); setHtml("indexCache", ""); }
  let d;
  try {
    d = await (await fetch("/api/valquo-index?config=" + encodeURIComponent(cfg))).json();
  } catch (e) {
    if (!cached) setHtml("valquoIndexBody", "");
    setHtml("indexCache", cached
      ? `<div class="cachebar warnish">Couldn't refresh — these holdings are your last saved copy.</div>` : "");
    return;
  }
  setHtml("indexCache", "");
  if (!(d.empty || d.error)) cacheSet("index:" + cfg, d);
  _renderValquoIndex(d, cfg);
}

function _renderValquoIndex(d, cfg) {
  setHtml("indexFreshness", freshnessBanner(d.freshness));
  setHtml("indexDisclaimer", d.disclaimer ? esc(d.disclaimer) : "");
  const note = document.getElementById("valquoIndexNote");
  const body = document.getElementById("valquoIndexBody");
  if (d.empty || d.error) {
    note.textContent = d.message || d.error || "Unavailable.";
    body.innerHTML = "";
    return;
  }
  const c = d.config || {};
  const m = c.measured || {};
  const meas = (m.net_sharpe != null)
    ? `backtested net Sharpe <b>${m.net_sharpe.toFixed(2)}</b>, net alpha <b>${(m.net_alpha * 100).toFixed(1)}%</b>`
    : (m.after_tax_sharpe != null
        ? `backtested after-tax Sharpe <b>${m.after_tax_sharpe.toFixed(2)}</b>, after-tax alpha <b>${(m.after_tax_alpha * 100).toFixed(1)}%</b>`
        : "");
  note.innerHTML = `<b>${c.label || cfg}</b> — ${d.n_positions} of ${d.n_eligible} eligible `
    + `(${d.n_scored} scored). Rebalance every ~${c.rebalance_months} months`
    + (c.exit_frac ? `, hold until a name falls past the top ${(c.exit_frac * 100).toFixed(0)}%` : ", full rotation")
    + `. ${meas}<br><span class="muted">${d.source_note || ""}</span>`;
  const rows = (d.positions || []).slice(0, 30);
  body.innerHTML = _indexSectorBox(d)
    + '<table class="tbl"><thead><tr><th>#</th><th>Ticker</th><th>Company</th><th>Sector</th>'
    + '<th class="num">Weight</th><th class="num">Hot score</th><th class="num">Market cap</th>'
    + '</tr></thead><tbody>'
    + rows.map((p, i) => `<tr><td>${i + 1}</td><td><b>${p.ticker}</b></td>`
        + `<td>${esc((p.name || "").slice(0, 28))}</td><td>${esc((p.sector || "—").slice(0, 18))}</td>`
        + `<td class="num">${pct(p.weight, 2)}</td>`
        + `<td class="num">${p.hot_score == null ? "—" : p.hot_score.toFixed(1)}</td>`
        + `<td class="num">${mcap(p.market_cap)}</td></tr>`).join("")
    + "</tbody></table>"
    + ((d.positions || []).length > rows.length
        ? `<div class="note">… and ${d.positions.length - rows.length} more</div>` : "");
}

/* Sector breakdown of the book — the one view that makes its diversification visible.
   `sector_data_available` is a real signal, not a formatting detail: a source with no sector
   column (the Sharadar export has none) would otherwise render a single "unknown" bar that
   reads as "this book is 100% one sector" rather than "this data is missing". Say which. */
function _indexSectorBox(d) {
  const w = d.sector_weights || {};
  const entries = Object.entries(w).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return "";
  if (!d.sector_data_available) {
    return `<div class="note">Sector breakdown unavailable — this book was built from a source `
      + `that carries no sector labels, so its diversification can't be shown.</div>`;
  }
  const top = entries[0];
  const hhi = entries.reduce((s, e) => s + e[1] * e[1], 0);
  return `<div style="margin:6px 0 12px">
    <div class="metricline" style="margin-bottom:8px">
      ${metric("Sectors", entries.length)}
      ${metric("Largest", esc(top[0]) + " " + pct(top[1], 1))}
      ${metric("Eff. sectors", (1 / (hhi || 1)).toFixed(1))}</div>`
    + entries.map(([s, v]) => `<div class="sector-bar">
        <span class="nm">${esc(s.slice(0, 20))}</span>
        <span class="track"><span style="width:${Math.max(3, Math.round(v / top[1] * 100))}%;background:var(--green)"></span></span>
        <span style="width:64px;text-align:right;font-weight:700">${pct(v, 1)}</span></div>`).join("")
    + `<div class="note">Weight by sector across the whole book (not just the ${
        Math.min(30, (d.positions || []).length)} rows shown). "Eff. sectors" is the
        inverse Herfindahl — how many sectors this book is really spread across.</div></div>`;
}


/* ====================== INDEX: BACKTESTED vs LIVE ======================
   The single most important honesty problem in the product. The backtest is 18 years of
   point-in-time history that the model was ALSO tuned on; the live track is a handful of
   days of real forward evidence. Showing one number for "performance" would either bury
   the backtest's weakness or dress up a week of noise as a track record.

   So: two columns, always both, always labelled, never blended. The server decides which
   one may be the headline (`headline`) and flags the live one `thin` until it has enough
   trading days — the UI never makes that call from a return figure it likes. */
async function loadIndexTrack() {
  const body = document.getElementById("indexPerfBody");
  if (!body) return;
  const cfg = (document.getElementById("bookConfig") || {}).value || "roth";
  const cached = cacheGet("indextrack:" + cfg);
  if (cached) { try { _renderIndexTrack(cached.d); } catch (e) { } }
  else { body.innerHTML = skeleton(4, { head: true }); }
  let d;
  try {
    d = await (await fetch("/api/index-track?config=" + encodeURIComponent(cfg))).json();
  } catch (e) {
    if (!cached) body.innerHTML = `<div class="muted">Performance unavailable.</div>`;
    return;
  }
  cacheSet("indextrack:" + cfg, d);
  _renderIndexTrack(d);
}

function _renderIndexTrack(d) {
  const body = document.getElementById("indexPerfBody");
  if (!body) return;

  const bt = d.backtested || {}, live = d.live;
  const liveLeads = d.headline === "live";
  const btAlpha = bt.net_alpha != null ? bt.net_alpha : bt.after_tax_alpha;
  const btSharpe = bt.net_sharpe != null ? bt.net_sharpe : bt.after_tax_sharpe;
  const btKind = bt.net_alpha != null ? "net of costs" : "after tax";

  const card = (title, badge, badgeClass, rows, lead) => `
    <div class="card" style="margin:0;${lead ? "border:2px solid var(--navy)" : "opacity:.92"}">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <b>${title}</b><span class="pill ${badgeClass}">${badge}</span></div>
      ${rows}
    </div>`;

  const btRows = `<div class="metricline" style="margin-top:8px">
      ${metric("Alpha / yr", btAlpha == null ? "—" : spct(btAlpha))}
      ${metric("Sharpe", btSharpe == null ? "—" : num(btSharpe, 2))}
      ${metric("Turnover / yr", bt.annual_turnover == null ? "—" : num(bt.annual_turnover, 2) + "x")}
    </div>
    <div class="muted" style="font-size:11px;margin-top:6px">${esc(bt.basis || "")}. Hypothetical —
      the model was tuned on this same history.</div>`;

  // LA8 — supplied by the server (index_track.track_age) rather than derived here, so the card,
  // the hero band, the landing page and the server's own note cannot disagree about how old
  // the track is. Null-guarded: an older payload simply falls back to the row count.
  const age = live && live.age ? live.age : null;

  // WHICH BOOK THIS RECORD IS OF. Contract §5a Rule 4 — a verdict is a statement about a
  // vintage and must name it. Served pre-rendered by the server (track_meter.vintage_label,
  // derived from the register) and only escaped here: the vintage number and the inception date
  // must move together, and a card that assembled its own sentence is where they would stop.
  // It sits ABOVE the metrics on purpose. Printed underneath, it reads as a footnote about the
  // past; printed above, it says what the numbers below are a record OF — which is the point,
  // because the series restarted and the figures do not carry that on their face.
  const vin = d.vintage || null;
  const vintageLine = vin ? `<div class="muted" style="font-size:11px;margin-top:8px"
      title="${esc(vin.rule || "")}"><b>${esc(vin.phrase)}</b></div>` : "";

  let liveRows;
  if (!d.available || !live) {
    liveRows = vintageLine +
      `<div class="muted" style="margin-top:10px">${esc(d.note || "Not started yet.")}</div>`;
  } else {
    // Cumulative-since-inception is the ONLY honest headline for a short track. Annualised
    // alpha and Sharpe are served as null until there is enough history, and render as "—"
    // with the reason — never as a compounded stub.
    liveRows = vintageLine + `<div class="metricline" style="margin-top:8px">
        ${metric("Index", spct(live.cum_valquo_pct / 100))}
        ${metric(esc(d.benchmark || "SPY"), spct(live.cum_spy_pct / 100))}
        ${metric("Excess", live.excess_pp == null ? "—" : spct(live.excess_pp / 100))}
      </div>
      <div class="metricline" style="margin-top:6px">
        ${metric("Alpha / yr", live.ann_alpha == null ? "—" : spct(live.ann_alpha))}
        ${metric("Sharpe", live.sharpe == null ? "—" : num(live.sharpe, 2))}
        ${/* LA8 — "Days" was live.days, the number of rows the recorder wrote, sitting beside
              two performance figures under a word that means age. A track 7 days old with 2
              rows read as "2". The age tile now shows the calendar; the Recorded tile appears
              only when they differ, so the gap is a visible second number rather than a
              silently smaller first one. */
          metric("Days", age ? age.age : live.days)}
        ${age && !age.complete ? metric("Recorded", age.recorded) : ""}
      </div>
      <div class="muted" style="font-size:11px;margin-top:6px">${esc(live.book || "")}${live.book
          ? " · " + esc(live.window || "") + " · source: " + esc(live.recorder || "") + ". "
          : ""}Dated model positions since
        ${esc(d.inception || live.since)}, priced forward — a model portfolio, not a traded
        account, and no capital is at risk in it. ${d.thin
          ? `Annualised figures are withheld until ${d.min_live_days} RECORDED trading days —
             compounding ${live.days} recorded day${live.days === 1 ? "" : "s"} to a yearly rate
             would invent a number.`
          : "Net of the same cost model as the backtest."}</div>`;
  }

  body.innerHTML = `<div class="grid2" style="margin-top:10px">`
    + card("Backtested", liveLeads ? "reference" : "headline",
           liveLeads ? "spec" : "est", btRows, !liveLeads)
    + card("Forward, model portfolio",
           d.available ? (d.thin ? `thin — ${age ? esc(age.short) : live.days + "d"}` : "headline")
                       : "not started",
           d.thin || !d.available ? "spec" : "est", liveRows, liveLeads)
    + `</div>`
    + (d.note ? `<div class="note" style="margin-top:10px">${esc(d.note)}</div>` : "");

  indexChart(d);
}

function indexChart(d) {
  const el = document.getElementById("indexChart");
  const note = document.getElementById("indexChartNote");
  if (!el) return;
  killChart("idx");
  const s = (d && d.series) || [];
  // One point is not a line. Say why the chart is empty rather than drawing a dot and
  // letting it read as a flat year.
  if (s.length < 2) {
    el.style.display = "none";
    if (note) {
      note.textContent = d && d.available
        ? `The cumulative chart needs at least two days of live history — there ${
            s.length === 1 ? "is 1 day" : "are 0 days"} so far. It appears automatically as the track accrues.`
        : "The cumulative chart appears once the live forward track starts reporting.";
    }
    return;
  }
  el.style.display = "";
  // The caption carries the framing, because a chart travels: this is the one element on the
  // page most likely to be screenshotted away from every other caveat around it.
  if (note) note.textContent = `Cumulative return of the MODEL portfolio since inception vs `
    + `${d.benchmark || "SPY"}, net of modelled costs. No capital is invested — these are `
    + `closing-price marks, not fills, and not a return anyone received.`;
  STATE.charts.idx = new Chart(el, {
    type: "line",
    data: {
      labels: s.map(r => r.date),
      datasets: [
        { label: "Valquo Index", data: s.map(r => r.valquo), borderColor: "#3454a4",
          backgroundColor: "rgba(52,84,164,.10)", fill: true, tension: .2, pointRadius: 0, borderWidth: 2 },
        { label: d.benchmark || "SPY", data: s.map(r => r.spy), borderColor: "#9aa4b8",
          borderDash: [5, 4], fill: false, tension: .2, pointRadius: 0, borderWidth: 2 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { boxWidth: 12 } },
        tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y >= 0 ? "+" : ""}${c.parsed.y.toFixed(2)}%` } },
      },
      scales: {
        // One label per trading day is unreadable by the second month and only gets worse
        // as the track grows — thin them and keep them horizontal.
        x: { ticks: { maxTicksLimit: 8, maxRotation: 0, autoSkip: true } },
        y: { ticks: { callback: v => v + "%" } },
      },
    },
  });
}
