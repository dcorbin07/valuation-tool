"""
The Valquo Index's LIVE forward track — the one number that is not backtested.

Everything else the product reports about the Index comes from an 18-year point-in-time
panel that the model was also tuned on. This module reads the forward paper-track that
started on the inception date and reports it *beside* the backtest, never blended into it.

Three rules encoded here, all about not flattering the live number:

  1. **The backtest stays the headline until the live track is long enough to mean
     anything.** `MIN_LIVE_DAYS` trading days. Before that the live figure is served with
     `thin: true` and a day count, so the UI can show it while refusing to lead with it.
     A week of noise is not evidence, and a good first week is exactly when it is most
     tempting to publish one.
  2. **No annualising a stub.** Compounding 5 days of drift to a yearly rate manufactures a
     number nobody should believe. Annualised alpha and Sharpe are only computed once there
     is enough history, and are `None` before that — not zero, not the cumulative figure
     wearing an annual label.
  3. **A day count may not promote the live number on its own.** Until 2026-08-09 rule 1 was
     the WHOLE rule, so on the 60th trading day `headline` flipped to `"live"`, the
     "too early to judge" pill vanished and the live number became allowed to lead the page —
     automatically, on a date already fixed, with nobody approving it. On the recorded
     inception of 2026-07-30 that fired in late October 2026, at a horizon
     `PAPER_TRACK_CONTRACT.md` §2 measures at **13% power**, unable to detect an edge below
     +49pp/yr. The public posture now changes only when that contract's **6-month operational
     gate** is recorded as passed — see `gate_state()`. The day count is still required; the
     gate is an ADDITIONAL condition, never a replacement, so a three-day track cannot lead
     just because the gate passed.

Source of truth is the tracker the Cowork side maintains (`data/valquo_track.json` plus
`valquo_track_history.csv`). Those live under `data/`, which is gitignored, so on a fresh
deploy they are simply absent — `summarize()` then reports `available: false` and the UI says
the track has not started rather than inventing one.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Optional

# Trading days of live history before the live figure may become the headline. ~3 months:
# long enough that one good or bad week cannot dominate, short enough to be reachable.
MIN_LIVE_DAYS = 60

# Below this there is not enough of a daily series to estimate a standard deviation that
# means anything, so Sharpe stays None rather than being a ratio of two noise terms.
MIN_SHARPE_DAYS = 20

TRADING_DAYS = 252.0

# A daily-excess Sharpe above this is not a great strategy, it is a broken series — a run of
# near-identical excess returns drives the denominator toward zero and the ratio toward
# infinity. Publishing "Sharpe 444" would discredit every other number on the page, so an
# implausible value is suppressed rather than shown. (For scale: the backtested book is 1.17,
# and sustained real-world Sharpes above ~3 are extraordinary.)
MAX_PLAUSIBLE_SHARPE = 6.0


# --- The contract gate. See rule 3 above and PAPER_TRACK_CONTRACT.md §5. ---
#
# ONE authority, deliberately: the contract's own register. Not a constant here, not an env
# var, not a store key. A code flag would be a SECOND record of the same fact, free to
# disagree with the document Don signs and with no way to tell which was right; reading the
# register makes the human record and the machine record the same bytes.
#
# The known risk, and why it is acceptable. This project has already been bitten by parsing a
# markdown table — `research_log._parse` matched `\bFIXED\b` across joined cells, and an
# unescaped `|` inside a cell shifted every column after it and understated the trial count.
# So this parser is deliberately dumb and deliberately one-directional:
#   * it recognises ONE row form, and anything it does not recognise is not a pass;
#   * EVERY failure resolves to NOT PASSED — file missing, unreadable, malformed, row absent,
#     value unrecognised. The conservative error is a mature track still labelled "backtested";
#     the harmful error is the reverse, and no accident can reach it;
#   * fenced code blocks are skipped, so documenting the row form cannot flip the gate on;
#   * if two rows disagree, NOT PASSED wins.
# The parse is published in the payload (`gate`), so a mis-parse is visible, not silent.
CONTRACT_FILE = "PAPER_TRACK_CONTRACT.md"
GATE_FIELD = "operational gate passed"
GATE_YES = ("yes", "passed", "true")


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def contract_path() -> str:
    return os.path.join(_repo_root(), CONTRACT_FILE)


def _verdict_token(s: str) -> str:
    """First WHOLE word of a register value: 'YES - 2027-01-30' -> 'yes', '*pending*' ->
    'pending', 'yes-ish, mostly' -> 'yes-ish'.

    TIGHTER THAN THE PRE-COMMITMENT, deliberately. Part 10 committed "the value must BEGIN
    with yes/passed/true", and the first implementation took the leading run of letters — so
    `yes-ish, mostly` read as a PASS. Its own test caught it. Requiring a whole word instead
    can only make the gate HARDER to pass, so it cannot reach the harmful error; a rule that
    reads hedged prose as an approval can.

    Dashes separate (the canonical row is `YES - <date>`); hyphens do not, which is exactly
    what keeps `yes-ish` out.
    """
    for dash in ("—", "–"):
        s = s.replace(dash, " ")
    words = s.lower().split()
    return words[0].strip(".,;:!()[]'\"") if words else ""


def gate_state(path: str = None) -> dict:
    """Has the paper-track contract's 6-month OPERATIONAL GATE been recorded as passed?

    The gate is a test of whether the track is being RECORDED properly — daily rows with no
    gaps, the book turning over as modelled, realised costs near the backtest's — not a test
    of returns (`PAPER_TRACK_CONTRACT.md` §3). It is what the contract makes the public
    posture depend on, and it is a human judgement, so it is recorded by a human, in the
    contract, in exactly one place. The edge lane sets this row on gate day:

        | Operational gate passed | YES - <date> |

    Field match is case- and whitespace-insensitive; the value's FIRST WHOLE WORD must be one
    of `yes` / `passed` / `true`. `pending`, `no`, blank, an absent row and hedged prose like
    `yes-ish, mostly` are all not-passed.
    """
    p = path or contract_path()
    out = {"passed": False, "source": CONTRACT_FILE, "field": GATE_FIELD, "value": None,
           "reason": "", "contract_present": False}
    try:
        with open(p, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        out["reason"] = (f"{CONTRACT_FILE} is not readable, so the operational gate cannot have "
                         f"been recorded as passed.")
        return out
    out["contract_present"] = True

    values, fenced = [], False
    for line in text.splitlines():
        s = line.strip()
        # Strip blockquote markers FIRST. The contract documents the canonical row inside a
        # fenced block inside a blockquote; without this the fence markers read as prose, the
        # example is skipped only because of its "> " prefix, and the fence rule above would
        # be true by accident rather than by construction.
        while s.startswith(">"):
            s = s[1:].strip()
        if s.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if " ".join(cells[0].replace("*", "").lower().split()) == GATE_FIELD:
            values.append(cells[1].replace("*", "").strip())

    if not values:
        out["reason"] = (f"{CONTRACT_FILE} carries no '{GATE_FIELD}' row, so the operational gate "
                         f"has not been recorded as passed.")
        return out

    out["value"] = values[0] if len(values) == 1 else values
    verdicts = [_verdict_token(v) in GATE_YES for v in values]
    if all(verdicts):
        out["passed"] = True
        out["reason"] = f"{CONTRACT_FILE} records the operational gate as passed ({values[0]!r})."
    elif any(verdicts):
        # Two rows disagreeing is a broken register, not a pass.
        out["reason"] = (f"{CONTRACT_FILE} carries conflicting '{GATE_FIELD}' rows ({values!r}); "
                         f"resolved as NOT passed.")
    else:
        out["reason"] = (f"{CONTRACT_FILE} records the operational gate as {values[0]!r}, which "
                         f"is not a pass.")
    return out


def default_paths() -> tuple:
    d = os.path.join(_repo_root(), "data")
    return os.path.join(d, "valquo_track.json"), os.path.join(d, "valquo_track_history.csv")


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def load(meta_path: str = None, history_path: str = None) -> dict:
    """Read the tracker files. Missing files are a normal state, not an error."""
    mp, hp = default_paths()
    meta_path = meta_path or mp
    history_path = history_path or hp

    meta = {}
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f) or {}
    except Exception:
        meta = {}

    series = []
    try:
        with open(history_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                d = (row.get("date") or "").strip()
                v, s = _f(row.get("valquo_pct")), _f(row.get("spy_pct"))
                if not d or v is None or s is None:
                    continue
                series.append({"date": d, "valquo": v, "spy": s,
                               "excess": _f(row.get("excess_pp")),
                               "n_priced": _f(row.get("n_priced"))})
    except Exception:
        series = []

    # The file is appended to, and a re-run can legitimately rewrite a day. Keep the LAST
    # row per date and order by date so the chart cannot zig-zag backwards.
    dedup = {}
    for r in series:
        dedup[r["date"]] = r
    series = [dedup[k] for k in sorted(dedup)]
    return {"meta": meta, "series": series}


def _daily_returns(series: list, key: str) -> list:
    """Cumulative percent-since-inception -> daily simple returns."""
    out, prev = [], 0.0
    for r in series:
        cum = r.get(key)
        if cum is None:
            continue
        # (1+cum_t)/(1+cum_{t-1}) - 1, with cum in PERCENT.
        out.append((1.0 + cum / 100.0) / (1.0 + prev / 100.0) - 1.0)
        prev = cum
    return out


def _stdev(xs: list) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return var ** 0.5 if var > 0 else None


STORE_KEY = "index_track"          # where an ingested track lives when there are no files


def from_store(store) -> dict:
    """An ingested track, for deploys where the tracker files are not on disk.

    `data/` is gitignored, so the Cowork side's track never ships with the app. Without this
    the live column would be permanently empty in production while looking fine locally —
    the worst kind of feature, one that only works on the developer's machine.
    """
    try:
        d = store.get_meta(STORE_KEY) or {}
    except Exception:
        return {"meta": {}, "series": []}
    series = []
    for r in (d.get("series") or []):
        if r.get("date") is not None and _f(r.get("valquo")) is not None:
            series.append({"date": str(r["date"]), "valquo": _f(r.get("valquo")),
                           "spy": _f(r.get("spy")), "excess": _f(r.get("excess")),
                           "n_priced": _f(r.get("n_priced"))})
    series = [x for x in series if x["spy"] is not None]
    return {"meta": {k: d.get(k) for k in ("inception_date", "benchmark", "scan_date")},
            "series": sorted(series, key=lambda r: r["date"])}


def summarize(config: str = None, meta_path: str = None, history_path: str = None,
              store=None, contract: str = None) -> dict:
    """Live track + the backtested figures for the same book, side by side.

    Never merges the two. `headline` names which one the UI is allowed to lead with, and per
    rule 3 that requires BOTH enough days AND the contract's operational gate.
    """
    from . import settings as S

    cfg_name = (config or S.DEFAULT_BOOK_CONFIG or "roth").lower()
    measured = ((S.BOOK_CONFIGS or {}).get(cfg_name) or {}).get("measured") or {}
    backtested = {
        "net_alpha": measured.get("net_alpha"),
        "net_sharpe": measured.get("net_sharpe"),
        "after_tax_alpha": measured.get("after_tax_alpha"),
        "after_tax_sharpe": measured.get("after_tax_sharpe"),
        "annual_turnover": measured.get("annual_turnover"),
        # Panel descriptor refreshed 2026-08-08 (P2 crowding memo): this said
        # "2,710-name / 110-date", the pre-B6 panel, and it ships on the track export.
        "basis": ("full 2,531-name / 69-date point-in-time panel, ~18 years, net of "
                  "modelled transaction costs"),
    }

    gate = gate_state(contract)
    d = load(meta_path, history_path)
    if not d["series"] and store is not None:
        d = from_store(store)
    series, meta = d["series"], d["meta"]
    out = {
        "config": cfg_name,
        "benchmark": meta.get("benchmark") or "SPY",
        "inception": meta.get("inception_date"),
        "min_live_days": MIN_LIVE_DAYS,
        "gate": gate,
        "backtested": backtested,
        "series": series,
        "available": bool(series),
        "days": len(series),
        "thin": True,
        "headline": "backtested",
        "live": None,
    }
    if not series:
        out["note"] = ("The live forward track has not started reporting yet. Until it does, "
                       "every figure shown for the Index is backtested.")
        return out

    last = series[-1]
    days = len(series)
    cum_v, cum_s = last["valquo"], last["spy"]
    excess = last.get("excess")
    if excess is None and cum_v is not None and cum_s is not None:
        excess = cum_v - cum_s

    live = {
        "days": days, "since": series[0]["date"], "as_of": last["date"],
        "cum_valquo_pct": cum_v, "cum_spy_pct": cum_s, "excess_pp": excess,
        "ann_alpha": None, "sharpe": None, "hit_rate": None,
    }

    # Annualise and estimate Sharpe ONLY with enough history. See the module docstring.
    rv = _daily_returns(series, "valquo")
    rs = _daily_returns(series, "spy")
    if days >= MIN_SHARPE_DAYS and len(rv) == len(rs) and rv:
        ex = [a - b for a, b in zip(rv, rs)]
        sd = _stdev(ex)
        if sd:
            sharpe = (sum(ex) / len(ex)) / sd * (TRADING_DAYS ** 0.5)
            live["sharpe"] = sharpe if abs(sharpe) <= MAX_PLAUSIBLE_SHARPE else None
        live["hit_rate"] = sum(1 for x in ex if x > 0) / len(ex)
    if days >= MIN_LIVE_DAYS and cum_v is not None and cum_s is not None:
        gv = (1.0 + cum_v / 100.0) ** (TRADING_DAYS / days) - 1.0
        gs = (1.0 + cum_s / 100.0) ** (TRADING_DAYS / days) - 1.0
        live["ann_alpha"] = gv - gs

    out["live"] = live

    # Rule 3. BOTH conditions, and the day count is not sufficient on its own. Order matters
    # only for the wording: a track that is short is short whatever the contract says.
    long_enough = days >= MIN_LIVE_DAYS
    out["thin"] = not (long_enough and gate["passed"])
    out["headline"] = "backtested" if out["thin"] else "live"
    if not long_enough:
        out["note"] = (f"Live track is {days} trading day{'s' if days != 1 else ''} old — far too "
                       f"short to judge. It is shown for transparency, not as evidence, and the "
                       f"headline stays on the backtest.")
    elif not gate["passed"]:
        out["note"] = (f"Live track is {days} trading days old, past the {MIN_LIVE_DAYS}-day "
                       f"floor, but the paper-track contract's operational gate has not been "
                       f"recorded as passed, so the backtest stays the headline. Elapsed time "
                       f"alone does not promote a live number. ({gate['reason']})")
    else:
        out["note"] = (f"Live forward track, {days} trading days since {live['since']} — real "
                       f"dated positions measured forward, no survivorship or hindsight.")
    return out
