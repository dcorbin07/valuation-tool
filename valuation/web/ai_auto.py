"""THE AI ANALYSIS RUNS BY ITSELF — once per ticker per day, under a cap Don can move.
[item 52 part 6]

**WHY IT HAD TO BECOME AUTOMATIC.** The panel sat behind a checkbox nobody ticked, so the page
shipped a company description written by nobody and the analysis existed only for whoever
remembered to ask. Don's instruction is that it runs on its own.

**WHY IT MUST NEVER BLOCK THE PAGE, with a number.** Measured on TSLA on 2026-10-13: the
valuation takes **2.0 seconds** and the analyst call takes **27.4**. Awaiting it would make a
two-second page a thirty-second one for a panel that is an addition to it. So the numbers paint
first and this is fetched afterwards, exactly as `loadWhatDo` already is.

**WHAT IT COSTS, MEASURED BEFORE IT WAS SWITCHED ON — the prompt's own precondition.** One real
call: 1,154 input tokens and 2,253 output tokens on `claude-sonnet-5` at the published
$2/$10 per million, i.e. **$0.0248**. About **91% of that is output**, because the schema asks
for eight fields including four multi-sentence theses. At the cap below that is **about 75
cents a day and roughly $22 a month** at 30 billed days.

**THE CAP IS A SPENDING LIMIT AND IT FAILS CLOSED.** `DAILY_CAP` is 30 *"until Don sets a
number"*. When the day's allowance is gone the page offers the button rather than showing
nothing — a reader who wants the analysis can still have it, and the cap stops a crawler or a
bad loop from spending the month's budget in an afternoon. **An unreadable ledger counts as
AT the cap**, because a store we cannot read cannot rule out that the day's calls already
happened, and the safe direction is not spending.

**A CACHED ANALYSIS IS SERVED INSTANTLY AND COSTS NOTHING.** Keyed on `(ticker, date)`, so the
second visitor to a name on the same day pays neither the 27 seconds nor the 2.5 cents.

**THE KEY IS NEVER READ, PRINTED OR LOGGED HERE.** This module decides *whether* to call and
records *what it cost*; the call itself stays in `valuation.ai.analyst`, which is the only
place that touches the credential.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

SCHEMA = "ai_auto/1"

#: NEW analyses a day. 30 until Don sets a number -- his words. At the measured $0.0248 a call
#: that is ~$0.75 a day. A CACHE HIT IS NOT A NEW ANALYSIS and does not count against it.
DAILY_CAP = 30

#: What the panel must say, every time it renders. The analysis is written from the numbers on
#: this page by a language model: it has read no filing, no transcript and no news, and the
#: most confident-sounding paragraph on the page is the one with the least behind it.
PANEL_LABEL = ("Written by AI from the numbers on this page — not from news, filings or "
               "anything else — and it can be wrong.")

#: What the page says when the day's allowance is gone. It OFFERS rather than refuses.
CAP_REACHED = ("Today's automatic analyses are used up (%d a day). You can still run this one "
               "now if you want it." % DAILY_CAP)


def _dir(root: str = None) -> str:
    base = root or os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "data")
    return os.path.join(base, "ai_analysis")


def _today() -> str:
    return _dt.date.today().isoformat()


def path_for(ticker: str, day: str = None, root: str = None) -> str:
    return os.path.join(_dir(root), "%s_%s.json" % (str(day or _today()),
                                                    str(ticker or "").upper()))


def ledger_path(day: str = None, root: str = None) -> str:
    return os.path.join(_dir(root), "_count_%s.json" % str(day or _today()))


def cached(ticker: str, day: str = None, root: str = None) -> Optional[dict]:
    """Today's stored analysis for this ticker, or None. Never raises."""
    try:
        with open(path_for(ticker, day, root), encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError):
        return None
    if (payload or {}).get("schema") != SCHEMA:
        return None
    return payload


def count_today(day: str = None, root: str = None) -> dict:
    """How many NEW analyses have been run today.

    `readable` is False when the ledger exists and cannot be parsed, and the caller treats
    that as AT the cap: a ledger we cannot read cannot rule out that today's calls already
    happened, and the direction that does not spend money is the safe one.
    """
    p = ledger_path(day, root)
    if not os.path.exists(p):
        return {"n": 0, "readable": True, "cost_usd": 0.0, "absent": True}
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return {"n": int(d.get("n") or 0), "readable": True,
                "cost_usd": float(d.get("cost_usd") or 0.0), "absent": False}
    except (OSError, ValueError, TypeError):
        return {"n": DAILY_CAP, "readable": False, "cost_usd": 0.0, "absent": False}


def allowance(day: str = None, root: str = None) -> dict:
    """Is there room for a NEW analysis today, and what has today cost so far."""
    c = count_today(day, root)
    left = max(0, DAILY_CAP - int(c["n"]))
    return {"cap": DAILY_CAP, "used": int(c["n"]), "left": left,
            "may_run": bool(left > 0 and c["readable"]),
            "ledger_readable": bool(c["readable"]),
            "cost_usd_today": round(float(c["cost_usd"]), 4),
            "reason": ("" if c["readable"] else
                       "the day's ledger could not be read, so no new analysis is run")}


def record(ticker: str, analysis: dict, *, day: str = None, root: str = None) -> dict:
    """Store one analysis for the day and charge it to the day's ledger. Never raises.

    **THE LEDGER MOVES ONLY WHEN THE ANALYSIS IS STORED.** Charging first would leak the day's
    allowance on every failed call; charging after a successful write means a failure costs
    money but not allowance, which is the ordering that cannot lock the day out.
    """
    day = day or _today()
    usage = (analysis or {}).get("usage") or {}
    payload = {"schema": SCHEMA, "ticker": str(ticker or "").upper(), "day": day,
               "analysis": analysis,
               "cost_usd": usage.get("cost_usd"),
               "input_tokens": usage.get("input_tokens"),
               "output_tokens": usage.get("output_tokens")}
    try:
        os.makedirs(_dir(root), exist_ok=True)
        p = path_for(ticker, day, root)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        os.replace(tmp, p)
    except OSError as e:
        return {"ok": False, "reason": "could not store the analysis: %s" % e, "charged": False}

    c = count_today(day, root)
    # A COST OF `None` ADDS NOTHING RATHER THAN ZERO. An unpriced model's call still counts
    # against the cap -- it happened -- but it must not be reported as having cost nothing.
    add = usage.get("cost_usd")
    total = float(c["cost_usd"] or 0.0) + (float(add) if add is not None else 0.0)
    try:
        lp = ledger_path(day, root)
        tmp = lp + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"day": day, "n": int(c["n"]) + 1, "cost_usd": round(total, 6),
                       "cost_is_partial": add is None or bool(c.get("cost_is_partial"))},
                      fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, lp)
        return {"ok": True, "reason": "", "charged": True}
    except OSError as e:
        return {"ok": True, "reason": "stored, but the ledger write failed: %s" % e,
                "charged": False}
