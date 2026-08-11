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
import datetime as _dt
import json
import os
from typing import Optional

from . import track_age as _track_age

# Trading days of live history before the live figure may become the headline. ~3 months:
# long enough that one good or bad week cannot dominate, short enough to be reachable.
MIN_LIVE_DAYS = 60

# Below this there is not enough of a daily series to estimate a standard deviation that
# means anything, so Sharpe stays None rather than being a ratio of two noise terms.
MIN_SHARPE_DAYS = 20

# LA3. Below this fraction of the ELAPSED trading days actually recorded, the Sharpe is
# withheld rather than corrected. The chained series holds cumulative-since-inception levels,
# so a missing day turns two "daily" returns into one multi-day one; the rescaling applied in
# `summarize` fixes that in expectation under i.i.d. returns, but below half coverage the
# typical observation spans more than two trading days and the correction is doing more work
# than the data supports. Committed in PREREG_la1_la3_repair.md section 4 with that argument,
# BEFORE any coverage figure was computed — it is not tuned to the observed 28.6%.
#
# The annualised ALPHA is deliberately NOT subject to this floor: it rests on two cumulative
# endpoints and a known elapsed window, which a gap between them does not corrupt.
MIN_COVERAGE_FOR_SHARPE = 0.5

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


def _elapsed_trading_days(series: list, meta: dict = None) -> int:
    """Trading days the recorded return actually accrued over (LA3).

    Two definitions, and they COINCIDE on a gapless series, which is what makes the fix
    backwards-compatible rather than a re-basing of every published figure:

      * with an `inception_date`: the half-open interval (inception, last_row], because
        inception is day 0 and carries a zero return by definition -- the same convention
        `track_meter.gap_report` uses to decide which days should have a row;
      * without one: the closed interval [first_row, last_row], i.e. the first recorded row is
        treated as day 1 of the window it opens.

    On a series recorded every trading day from inception+1 onward, both return exactly
    `len(series)`, so `summarize` reproduces its old numbers to the bit on a complete track.
    """
    from .market_session import trading_days_between

    if not series:
        return 0
    last = _date(series[-1].get("date"))
    if last is None:
        return len(series)
    inception = _date((meta or {}).get("inception_date"))
    if inception is not None and inception < last:
        return trading_days_between(inception, last, inclusive_start=False)
    first = _date(series[0].get("date"))
    if first is None:
        return len(series)
    return trading_days_between(first, last, inclusive_start=True)


def _age_trading_days(series: list, meta: dict = None, today: _dt.date = None) -> Optional[int]:
    """Trading days from inception to TODAY -- how old the track is (LA8).

    Deliberately NOT `_elapsed_trading_days`. That one stops at the last recorded row, because
    it is the window the recorded return accrued over and annualisation needs exactly that. This
    one runs to today, because "how old is this track" is a question about the calendar and not
    about how diligent the recorder has been. On a track written every day the two agree; when
    the recorder stops, only this one keeps moving, which is the entire reason it exists.

    Returns None when there is no inception and no first row to anchor to -- the caller then has
    no age to display and says so with the row count instead of guessing.
    """
    from .market_session import now_et, trading_days_between

    if today is None:
        today = now_et().date()
    inception = _date((meta or {}).get("inception_date"))
    if inception is not None:
        # Half-open (inception, today]: inception is day 0 and carries a zero return by
        # definition -- the same convention `_elapsed_trading_days` and `gap_report` use, so
        # "day N" means the same thing on every surface.
        return trading_days_between(inception, today, inclusive_start=False)
    first = _date((series or [{}])[0].get("date")) if series else None
    if first is None:
        return None
    return trading_days_between(first, today, inclusive_start=True)


def _date(x):
    if isinstance(x, _dt.date):
        return x
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return None


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


# --------------------------------------------------------------------------- #
# THE ONE AUTHORITY for a "Valquo Index vs SPY" statement on any outbound surface.
# --------------------------------------------------------------------------- #
#
# WHY THIS EXISTS. On 2026-08-05 the Discord recap posted:
#
#     "Since inception 2026-08-03 (3 sessions): index +3.22%, SPY +3.05% -> **+0.18 pp**"
#
# i.e. the Index was BEATING SPY. The contract-bound recorder over that window reads
# -0.2777pp (2026-07-31) and -2.8468pp (2026-08-06): it was never above SPY, on any day.
# Nothing was miscalculated. The recap read a DIFFERENT BOOK -- the Tradier sandbox engine
# (`paper_track.index_summary`), 10 names against the published book's 86, inception
# 2026-08-03 -- and printed it under the words "Valquo Index vs SPY". A book that size is not
# the Index, so the engine may never be evidence under `PAPER_TRACK_CONTRACT.md`.
#
# CORRECTED 2026-08-11 (cold audit LA11). The two sentences above used to disqualify the engine
# because "those 10% weights violate this contract's own 8% cap". They do not, and session 16
# (`PT-SPLIT`) retracted it: `valquo_index.build_index` sets `cap = max(MAX_WEIGHT,
# 1/len(picks))` on purpose -- ten names at 8% sum to 80%, so on a small book the cap must
# relax to equal weight or the redistribution loop never terminates -- and the payload has
# always self-reported `effective_max_weight`. The weights were correct for the book they
# described; the BOOK was the wrong one. The conclusion is unchanged; only its reason moves,
# from weights to book SIZE. Keeping the retracted reason would have been the more dangerous
# state, because a reader who checks the cap finds it correct and may then doubt the
# separation itself.
#
# WHY IT IS CENTRALISED RATHER THAN PATCHED. The same defect had already been found ON THE
# SITE (audit B7: the live screener and the backtest scored names differently because two code
# paths computed the same thing). The lesson taken then was that a second implementation of one
# number is a bug with a delay fuse, not a style problem. This is that bug on an OUTBOUND
# surface, which is strictly worse: a wrong figure on a page can be corrected in place, but a
# wrong figure in Discord is delivered once, to people, and the correction never catches up
# with it. So there is exactly one function that may answer "how is the Index doing vs SPY",
# it reads only the bound source, and there is no fallback to any other recorder -- an
# unavailable claim is a normal outcome and is reported as such.
#
# WHY THE TEXT IS BUILT HERE. Every claim carries its BOOK and its WINDOW in the same string as
# its numbers, so the two cannot come apart in transit. A surface that wants the numbers gets
# the sentence; a surface that renders its own layout still gets `book` and `window` as fields
# it is expected to show. "+0.18 pp" is not a claim -- "+0.18 pp, this book, this window" is.

# The book, exactly as PAPER_TRACK_CONTRACT.md fixes it (see its "comparison rule").
BOOK = ("Valquo Index — broad top decile of the large-cap tier by hot score, score-weighted, "
        "capped at 8%")
BOOK_SHORT = "Valquo Index (top decile, large-cap tier, score-weighted, 8% cap)"

# The bound source. Named in the claim so a reader can check it against the contract.
RECORDER = "data/valquo_track.json + valquo_track_history.csv"

WINDOW_KINDS = ("inception", "last_point", "trailing")


def _window_return_pct(cum_now, cum_then) -> Optional[float]:
    """Compound a window return out of two cumulative-since-inception PERCENT levels.

    THE ONLY PLACE THIS ARITHMETIC IS ALLOWED TO LIVE. Cumulative levels do not subtract --
    (1+a)/(1+b)-1, not a-b -- and the difference matters once the levels are more than a few
    percent apart. Keeping it here means a surface cannot get it subtly wrong in its own copy.
    """
    a, b = _f(cum_now), _f(cum_then)
    if a is None or b is None:
        return None
    return ((1.0 + a / 100.0) / (1.0 + b / 100.0) - 1.0) * 100.0


def _plural_sessions(n: int) -> str:
    return f"{n} recorded session" + ("" if n == 1 else "s")


def vs_spy_claim(window: str = "inception", points: int = 1, meta_path: str = None,
                 history_path: str = None, store=None) -> dict:
    """The Index's record against its benchmark, over one window, from the bound recorder.

    `window`:
      * `inception`  — first recorded row to the latest one. Uses the tracker's OWN recorded
                       `excess_pp` when it wrote one, so the published number and this one are
                       the same bytes rather than two derivations that agree today.
      * `last_point` — the previous recorded row to the latest one.
      * `trailing`   — `points` recorded rows back to the latest one.

    Windows are counted in RECORDED POINTS, never calendar days, and say so in the text. The
    bound series is maintained by hand on the Cowork side and has gaps (2 of 6 due rows on
    2026-08-09), so "since yesterday" would silently attribute several days of drift to one.

    Returns `available: False` with a `reason` when the bound source has nothing to say. That
    is a normal state on a fresh deploy — `data/` is gitignored — and it is NEVER resolved by
    reading another recorder. A surface with no claim must print no claim.
    """
    if window not in WINDOW_KINDS:
        raise ValueError(f"unknown window {window!r}; expected one of {WINDOW_KINDS}")

    out = {"available": False, "reason": "", "recorder": RECORDER, "book": BOOK,
           "book_short": BOOK_SHORT, "benchmark": "SPY", "window": "", "window_kind": window,
           "since": None, "as_of": None, "n_points": 0, "valquo_pct": None, "spy_pct": None,
           "excess_pp": None, "excess_source": None, "text": ""}

    d = load(meta_path, history_path)
    if not d["series"] and store is not None:
        d = from_store(store)
    series, meta = d["series"], d["meta"]
    out["benchmark"] = meta.get("benchmark") or "SPY"
    out["inception"] = meta.get("inception_date")

    if not series:
        out["reason"] = ("the contract-bound track has no recorded rows, so there is no "
                         "Index-vs-SPY figure to report")
        return out

    last = series[-1]
    out["as_of"] = last["date"]

    if window == "inception":
        first = series[0]
        out.update(since=meta.get("inception_date") or first["date"], n_points=len(series),
                   valquo_pct=_f(last.get("valquo")), spy_pct=_f(last.get("spy")))
        rec = _f(last.get("excess"))
        if rec is not None:
            out["excess_pp"], out["excess_source"] = rec, "recorded"
        elif out["valquo_pct"] is not None and out["spy_pct"] is not None:
            out["excess_pp"] = out["valquo_pct"] - out["spy_pct"]
            out["excess_source"] = "derived-by-recorder"
        out["window"] = (f"since inception {out['since']} through {out['as_of']} "
                         f"({_plural_sessions(len(series))})")
    else:
        back = 1 if window == "last_point" else max(1, int(points))
        if len(series) < back + 1:
            out["reason"] = (f"the bound track has {len(series)} recorded row(s) — too few for a "
                             f"{back}-point window")
            return out
        prev = series[-1 - back]
        out.update(since=prev["date"], n_points=back + 1,
                   valquo_pct=_window_return_pct(last.get("valquo"), prev.get("valquo")),
                   spy_pct=_window_return_pct(last.get("spy"), prev.get("spy")))
        if out["valquo_pct"] is not None and out["spy_pct"] is not None:
            out["excess_pp"] = out["valquo_pct"] - out["spy_pct"]
            out["excess_source"] = "derived-by-recorder"
        out["window"] = (f"{prev['date']} → {out['as_of']} "
                         f"({back} recorded point{'' if back == 1 else 's'} apart)")

    if out["valquo_pct"] is None or out["spy_pct"] is None:
        out["reason"] = "the bound track's latest rows are missing a priced leg"
        return out

    out["available"] = True
    out["text"] = (f"{BOOK_SHORT} vs {out['benchmark']}, {out['window']}: "
                   f"Index {out['valquo_pct']:+.2f}%, {out['benchmark']} {out['spy_pct']:+.2f}% "
                   f"→ {out['excess_pp']:+.2f} pp")
    return out


def summarize(config: str = None, meta_path: str = None, history_path: str = None,
              store=None, contract: str = None, today: _dt.date = None) -> dict:
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
    # LA3 — ROWS AND ELAPSED TIME ARE DIFFERENT DENOMINATORS AND THIS USED TO CONFLATE THEM.
    # `days` (rows recorded) still gates: a track that has not been written down is not
    # evidence, and moving the GATE onto elapsed time would let a gappy track reach
    # MIN_LIVE_DAYS sooner — the flattering direction, advancing the public "backtested ->
    # live" posture on the strength of days nobody recorded. `elapsed` (trading days the
    # return actually accrued over) is what annualisation needs.
    elapsed = _elapsed_trading_days(series, meta)
    coverage = (days / elapsed) if elapsed else None
    # LA8 — a THIRD clock, for the display only. `elapsed` stops at the last recorded row, so a
    # recorder that died leaves it frozen and the track appears to stop ageing exactly when it
    # stopped being written. `age` runs to today, so that gap is visible instead of flattering.
    # It is used for words, never for the gate and never for an exponent.
    age = _track_age.describe(_age_trading_days(series, meta, today), days)
    cum_v, cum_s = last["valquo"], last["spy"]

    # The since-inception excess comes from `vs_spy_claim`, not from a second subtraction here.
    # Both readings agreed, which is exactly why they were dangerous: two derivations that
    # match today are one edit away from not matching, and nothing would have said which was
    # right. `claim` also travels into the payload so the API serves the book and the window
    # attached to the number.
    claim = vs_spy_claim("inception", meta_path=meta_path, history_path=history_path,
                         store=store)
    excess = claim.get("excess_pp")

    live = {
        "days": days, "elapsed_trading_days": elapsed, "coverage": coverage, "age": age,
        "since": series[0]["date"], "as_of": last["date"],
        "cum_valquo_pct": cum_v, "cum_spy_pct": cum_s, "excess_pp": excess,
        "book": claim.get("book_short"), "window": claim.get("window"),
        "claim": claim.get("text"), "recorder": claim.get("recorder"),
        "ann_alpha": None, "sharpe": None, "hit_rate": None,
    }

    # Annualise and estimate Sharpe ONLY with enough history. See the module docstring.
    rv = _daily_returns(series, "valquo")
    rs = _daily_returns(series, "spy")
    if days >= MIN_SHARPE_DAYS and len(rv) == len(rs) and rv:
        ex = [a - b for a, b in zip(rv, rs)]
        sd = _stdev(ex)
        # LA3 — each CHAINED observation spans `elapsed / n_obs` trading days on average, not
        # one. Scaling a multi-day series by sqrt(252) over-annualises it by sqrt(that span),
        # which is how a 33%-recorded year reported a Sharpe of 1.03 against the same year's
        # true 0.54. On a gapless series the ratio is exactly 1 and the figure is unchanged.
        span = (elapsed / len(ex)) if (elapsed and ex) else 1.0
        if sd and coverage is not None and coverage >= MIN_COVERAGE_FOR_SHARPE:
            sharpe = (sum(ex) / len(ex)) / sd * ((TRADING_DAYS / span) ** 0.5)
            live["sharpe"] = sharpe if abs(sharpe) <= MAX_PLAUSIBLE_SHARPE else None
        elif sd:
            # Below the floor the "daily" series is mostly multi-day and the i.i.d. rescaling
            # above would be doing more work than the data supports. WITHHELD, not corrected —
            # the same choice `track_meter.monthly_excess` makes when a month's mark is stale.
            live["sharpe"] = None
            live["sharpe_withheld_reason"] = (
                f"only {days} of {elapsed} trading days recorded "
                f"({coverage:.1%} < {MIN_COVERAGE_FOR_SHARPE:.0%}); a Sharpe built from "
                f"multi-day gaps would not be a daily-volatility estimate")
        live["hit_rate"] = sum(1 for x in ex if x > 0) / len(ex)
    if days >= MIN_LIVE_DAYS and cum_v is not None and cum_s is not None and elapsed:
        # LA3 — the exponent is TIME, not row count. The cumulative levels are
        # since-inception, so this rests on two endpoints and a known elapsed window; a gap
        # between them does not corrupt it, which is why alpha needs no coverage floor.
        gv = (1.0 + cum_v / 100.0) ** (TRADING_DAYS / elapsed) - 1.0
        gs = (1.0 + cum_s / 100.0) ** (TRADING_DAYS / elapsed) - 1.0
        live["ann_alpha"] = gv - gs

    out["live"] = live

    # Rule 3. BOTH conditions, and the day count is not sufficient on its own. Order matters
    # only for the wording: a track that is short is short whatever the contract says.
    long_enough = days >= MIN_LIVE_DAYS
    out["thin"] = not (long_enough and gate["passed"])
    out["headline"] = "backtested" if out["thin"] else "live"
    # LA8 — the AGE CLAUSE of each sentence now comes from `age`, which knows the difference
    # between how old the track is and how much of it was written down. Everything after the
    # em dash is CONTRACT POSTURE and is quoted verbatim from before this change: the floor is
    # counted in recorded rows, deliberately, and these sentences are the public statement of
    # that. `tests/test_track_age.py` fails if either half moves into the other.
    if not long_enough:
        out["note"] = (f"Live track is {age['phrase']} — far too "
                       f"short to judge. It is shown for transparency, not as evidence, and the "
                       f"headline stays on the backtest.")
    elif not gate["passed"]:
        out["note"] = (f"Live track is {age['phrase']}, past the {MIN_LIVE_DAYS}-recorded-day "
                       f"floor, but the paper-track contract's operational gate has not been "
                       f"recorded as passed, so the backtest stays the headline. Elapsed time "
                       f"alone does not promote a live number. ({gate['reason']})")
    else:
        # Anchored on inception, not on the first recorded row: `age` counts from inception, so
        # naming a different start date beside it would put two anchors in one sentence.
        out["note"] = (f"Live forward track since {out['inception'] or live['since']}, "
                       f"{age['phrase']} — real dated positions measured forward, no "
                       f"survivorship or hindsight.")
    return out
