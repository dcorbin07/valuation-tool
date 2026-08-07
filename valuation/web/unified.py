"""
One name, both books — "what does this tool actually do with AAPL?"

The product has been answering that question in three places that never meet: the opportunity
score on the Single tab, the scream-buy options alert on Signals, and the tracked outcome on
Track Record. A reader holding one name had to visit all three and join them by hand.

This composes them for a single ticker. It is a READ over what is already stored — the scan
snapshot, the constructed book, the logged option alerts, the paper positions. Nothing here
recomputes a score, an expectancy or a P&L: every figure comes back from the module that owns
it (`valquo_index.build_index`, `options_tracker`, `options_paper.paper_report`), so this view
cannot quietly disagree with the tab it was summarized from. That is also why it is cheap
enough to call on every valuation — no network, no chain fetch, no DCF.

THE HONESTY RULES, which are the hard part rather than the plumbing:

  * Options are CONVEX, not likely. The backtested hit rate is ~37%: most alerts lose a little
    and a few win big. Nothing here may render a hit rate as a success probability, and a
    per-ticker record (a handful of trades at most) is reported as a COUNT, never as a rate.
  * Sizing is whole contracts against a fixed risk budget, and "0 contracts" is a real answer
    meaning the premium exceeds the budget — not a number to round up to 1.
  * A name absent from the scan is absent, not bad. A name outside the book is outside it
    because of where it ranks, and the line says so.
  * Every forward figure is paper, and labelled with the label the paper track itself
    publishes rather than a friendlier one written here.
"""
from __future__ import annotations

from typing import Optional

# The one number that has to travel with every options statement on the page.
from ..edge.options_confidence import HIT_RATE
from .payoff import expectation_line, payoff_summary, HIT_RATE_RANGE

# Written once, attached everywhere an options figure appears — including the withheld case,
# where a reader still sees a contract exists and would otherwise fill in "signal = likely".
#
# It quotes the RANGE rather than 37%: the confidence tables are calibrated on a 55-name book
# that hits 37.4% and the broad corrected book hits 35.3%, and picking one of them to be "the"
# hit rate would make two surfaces of the same product disagree by a point and a half with
# nothing on either saying so. `payoff.HIT_RATE_RANGE` is the single place that range is written.
#
# The second sentence is the part that is new, and it is the whole point of P3: a reader told
# only that "most trades lose" still has no way to judge their own run of losses. The streak
# number is measured, and it is stated BEFORE anyone is down rather than offered afterwards as
# an excuse.
_CONVEXITY = (f"Options here are CONVEX, not high-probability: the backtest hits "
              f"{HIT_RATE_RANGE} of the time — most trades lose a little and a few win big. "
              f"A hit rate on its own says nothing about whether this works. "
              + expectation_line(20))


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _fmt_money(x) -> str:
    v = _f(x)
    return "—" if v is None else f"${v:,.2f}"


def _scan_row(rows, ticker):
    for r in rows:
        if str(r.get("ticker", "")).upper() == ticker:
            return r
    return None


def _index_membership(rows, ticker, config_name=None):
    """Is this name in the book the Index tab shows, and at what weight?"""
    from ..edge.valquo_index import build_index
    from ..screener import settings as S

    name = (config_name or S.DEFAULT_BOOK_CONFIG or "roth").lower()
    cfg = (S.BOOK_CONFIGS or {}).get(name) or {}
    kw = {}
    if cfg.get("top_n"):
        kw["top_n"] = cfg["top_n"]
    if cfg.get("top_frac"):
        kw["top_decile"] = cfg["top_frac"]
    try:
        book = build_index(rows, **kw)
    except Exception:
        return {"config": name, "available": False}
    positions = book.get("positions") or []
    mine = next((p for p in positions if str(p.get("ticker", "")).upper() == ticker), None)
    return {"config": name, "label": cfg.get("label"), "available": True,
            "in_book": bool(mine), "weight": (mine or {}).get("weight"),
            "n_positions": len(positions), "n_eligible": book.get("n_eligible")}


def _paper_stock_position(store, ticker):
    """The sell-logic paper book's position in this name, if it has one."""
    try:
        rows = store.all_positions("hot10") or []
    except Exception:
        return None
    mine = [dict(r) for r in rows if str(r["ticker"]).upper() == ticker]
    if not mine:
        return None
    mine.sort(key=lambda r: str(r.get("entry_date") or ""))
    last = mine[-1]
    return {"state": "open" if not last.get("exit_date") else "closed",
            "entry_date": last.get("entry_date"), "entry_price": _f(last.get("entry_price")),
            "exit_date": last.get("exit_date"), "exit_price": _f(last.get("exit_price")),
            "reason": last.get("reason"), "n_episodes": len(mine)}


def _option_alerts(store, ticker):
    with store._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts WHERE ticker = ? ORDER BY alert_ts", (ticker,))
        keys = [d[0] for d in cur.description]
        return [dict(zip(keys, r)) for r in cur.fetchall()]


def _contract_label(a) -> str:
    right = "call" if str(a.get("opt_right") or "").lower().startswith("c") else "put"
    strike = _f(a.get("strike"))
    strike_s = f"${strike:g}" if strike is not None else "?"
    return f"{ticker_of(a)} {strike_s} {right} exp {str(a.get('expiry') or '?')[:10]}"


def ticker_of(a) -> str:
    return str(a.get("ticker") or "").upper()


def options_for(store, ticker, risk_budget=None) -> dict:
    """This name's options record: the latest alert, its sizing, and what has closed.

    The per-ticker sample is always tiny, so closed trades are reported as a COUNT and a total
    — never as a hit rate or an expectancy, both of which need the book-wide sample to mean
    anything. The book-wide figures come back from `paper_report` untouched, with the reference
    it says is the comparable one.
    """
    from ..edge.options_sizing import contracts_for, RISK_PER_TRADE

    try:
        alerts = _option_alerts(store, ticker)
    except Exception:
        alerts = []
    closed = [a for a in alerts if str(a.get("status")) == "closed"]
    open_rows = [a for a in alerts if str(a.get("status")) != "closed"]
    budget = _f(risk_budget) or RISK_PER_TRADE

    latest = None
    src = open_rows or alerts
    if src:
        a = sorted(src, key=lambda r: str(r.get("alert_ts") or ""))[-1]
        prem = _f(a.get("entry_premium"))
        n = contracts_for(prem, budget) if prem else 0
        latest = {
            "alert_ts": a.get("alert_ts"), "status": a.get("status"),
            "contract": _contract_label(a), "expiry": a.get("expiry"),
            "opt_right": a.get("opt_right"), "strike": _f(a.get("strike")),
            "entry_premium": prem, "dte": a.get("dte"), "horizon": a.get("horizon"),
            "score": _f(a.get("score")),
            "sizing": {
                "risk_budget": budget, "contracts": n,
                "cost": (prem * 100.0 * n) if (prem is not None and n) else None,
                # 0 is a real answer: one contract would exceed the risk budget. Rounding it
                # up would break the only risk rule this page states.
                "note": ("one contract costs more than the risk budget — the honest size is "
                         "zero, not one" if prem and n == 0 else
                         f"whole contracts only, at {_fmt_money(budget)} of premium at risk"),
            },
        }

    wins = [a for a in closed if (_f(a.get("pnl_pct")) or 0) > 0]
    pnl = [_f(a.get("pnl_dollars")) for a in closed if _f(a.get("pnl_dollars")) is not None]
    return {
        "n_logged": len(alerts), "n_open": len(open_rows), "n_closed": len(closed),
        "latest": latest,
        # Deliberately a count, not a rate. Two of three winners is not a 67% strategy.
        "closed_here": ({"n": len(closed), "n_won": len(wins),
                         "total_pnl_dollars": (sum(pnl) if pnl else None),
                         "note": "too few trades on one name to read as a rate"}
                        if closed else None),
        "hit_rate_reference": HIT_RATE,
        "convexity": _CONVEXITY,
        # The distribution, not just the average. A hit rate and a mean expectancy describe a
        # convex book badly, and the reader who most needs the shape is the one who has just
        # seen a loss — so it ships on every options payload rather than on request.
        "payoff": payoff_summary(),
    }


def name_view(store, ticker: str, book_config: str = None, risk_budget=None,
              with_options: bool = True, with_book: bool = True) -> dict:
    """Everything the product knows about one name, from what is already stored.

    Two independent switches, because this panel spans the public product and two owner-only
    surfaces and a visitor should still get the half that is theirs:

    * `with_options=False` withholds the specific contract (an actionable live pick).
    * `with_book=False` withholds where the name sits in the CONSTRUCTED book and in the paper
      account — a live position and a paper-account record, which are owner-only on a public
      instance for the reasons in `saas/surfaces.py`.

    The ranking half is public either way: it is the same ranking the Hot tab serves, and
    refusing it here while publishing it there would be theatre. Both withholdings say so in
    the payload rather than silently omitting a key — a missing field reads as "no book
    position", which is a different and false statement.
    """
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"error": "no ticker"}

    out = {"ticker": ticker, "stock": {"in_scan": False}, "options": {}, "action": []}

    try:
        scan_date = store.latest_scan_date()
    except Exception:
        scan_date = None
    rows = []
    if scan_date:
        try:
            rows = store.load_snapshot(scan_date) or []
        except Exception:
            rows = []

    row = _scan_row(rows, ticker) if rows else None
    if not scan_date:
        out["stock"]["message"] = ("No scan has loaded into this site yet, so there is no "
                                   "ranking to place this name in.")
    elif row is None:
        out["stock"].update({
            "scan_date": scan_date, "n_scored": len(rows),
            "message": (f"Not in the {scan_date} scan of {len(rows)} names — the screen covers "
                        f"a defined universe, so being absent says nothing about the company."),
        })
    else:
        # Fair value: only the top few names carry a full DCF, so fill the rest with the same
        # peer-relative estimate the Hot tab uses, computed against the WHOLE scan.
        try:
            from ..screener.fairvalue import estimate_fair_values
            estimate_fair_values([row], peer_rows=rows)
        except Exception:
            pass
        # The SECOND public surface fed by that estimator (the first is /api/hotstocks), and
        # it has to apply the same band or the leak just moves one endpoint over.
        try:
            from .withhold import withhold_implausible_fair_values
            withhold_implausible_fair_values([row])
        except Exception:
            pass
        extra = row.get("extra") or {}
        out["stock"] = {
            "in_scan": True, "scan_date": scan_date, "n_scored": len(rows),
            "name": row.get("name"), "sector": row.get("sector"), "bucket": row.get("bucket"),
            "rank": row.get("rank"), "hot_score": _f(row.get("hot_score")),
            "composite": _f(row.get("composite")), "price": _f(row.get("price")),
            "fair_value": _f(row.get("fair_value")), "upside": _f(row.get("upside")),
            "fair_value_method": row.get("fair_value_method"),
            "fair_value_withheld": bool(row.get("fair_value_withheld")),
            "fair_value_withheld_reason": row.get("fair_value_withheld_reason"),
            "why": extra.get("why") or [], "why_composite": extra.get("why_composite"),
            # The two owner-only halves. `book_withheld` is carried explicitly so the reader
            # (and _action_lines below) can tell "not published" from "not in the book".
            "index": (_index_membership(rows, ticker, book_config) if with_book
                      else {"withheld": True}),
            "paper_position": (_paper_stock_position(store, ticker) if with_book else None),
            "book_withheld": not with_book,
        }
        try:
            from ..screener.freshness import status as _freshness
            out["stock"]["freshness"] = _freshness(scan_date, label="ranking")
        except Exception:
            pass

    if with_options:
        out["options"] = options_for(store, ticker, risk_budget=risk_budget)
    else:
        # The CONTRACT is withheld; the payoff SHAPE is not. Withholding the shape would leave a
        # visitor who can see an alert exists with nothing but "options" to reason from, which
        # is the exact gap that makes a 35% hit rate read as a broken product. The shape is a
        # property of a historical simulation, not a live pick and not a performance claim.
        out["options"] = {"withheld": True, "hit_rate_reference": HIT_RATE,
                          "message": ("The specific options contract is part of Signals. The "
                                      "ranking above is the same one the Hot Stocks tab shows."),
                          "convexity": _CONVEXITY,
                          "payoff": payoff_summary()}
    out["action"] = _action_lines(out)
    out["disclaimer"] = ("Educational only, not advice, and nothing here is routed to a broker. "
                         "Forward figures are paper.")
    return out


def _action_lines(view: dict) -> list:
    """Plain statements of what the tool IS doing with this name — not what to do about it.

    Every line is a fact already on the page above it. The distinction matters: this is the
    part of the view that reads most like a recommendation, so it is restricted to describing
    the model's own positions and rankings.
    """
    lines = []
    s = view.get("stock") or {}
    o = view.get("options") or {}

    if not s.get("in_scan"):
        lines.append({"kind": "stock", "text": s.get("message") or "Not in the current ranking."})
    else:
        idx = s.get("index") or {}
        rank, n = s.get("rank"), s.get("n_scored")
        if s.get("book_withheld"):
            # Says which, deliberately. "NOT in the Valquo Index" would be a statement about
            # the book, and we did not look at the book.
            lines.append({"kind": "stock", "text":
                          f"It ranks {rank} of {n} in the {s.get('scan_date')} scan. Whether "
                          f"the model's own book holds it is not published — that is a live "
                          f"position, and this is an educational tool, not a signal service."})
        elif idx.get("in_book"):
            w = _f(idx.get("weight"))
            lines.append({"kind": "stock", "text":
                          f"HELD in the Valquo Index ({idx.get('config')}) at "
                          f"{'—' if w is None else format(w, '.1%')} of the book — it ranks "
                          f"{rank} of {n} in the {s.get('scan_date')} scan."})
        elif idx.get("available"):
            lines.append({"kind": "stock", "text":
                          f"NOT in the Valquo Index: it ranks {rank} of {n} and the book takes "
                          f"the top {idx.get('n_positions')} of {idx.get('n_eligible')} eligible "
                          f"names. Ranking well is not the same as making the book."})
        pos = s.get("paper_position")
        if pos and pos.get("state") == "open":
            lines.append({"kind": "stock", "text":
                          f"The paper account has held it since {pos.get('entry_date')} at "
                          f"{_fmt_money(pos.get('entry_price'))}."})
        elif pos:
            lines.append({"kind": "stock", "text":
                          f"The paper account sold it on {pos.get('exit_date')} "
                          f"({pos.get('reason') or 'no reason recorded'})."})

    latest = o.get("latest")
    if o.get("withheld"):
        # "No alert on this name" would be a lie here — we did not look. Say which.
        lines.append({"kind": "options", "text": o.get("message")})
    elif latest:
        sz = latest.get("sizing") or {}
        state = "open" if str(latest.get("status")) != "closed" else "closed"
        lines.append({"kind": "options", "text":
                      f"Scream-buy options alert ({state}) from {str(latest.get('alert_ts'))[:10]}: "
                      f"{latest.get('contract')} at {_fmt_money(latest.get('entry_premium'))} — "
                      f"{sz.get('contracts')} contract(s) at a {_fmt_money(sz.get('risk_budget'))} "
                      f"risk budget."})
    else:
        lines.append({"kind": "options", "text":
                      "No scream-buy options alert has ever fired on this name."})
    ch = o.get("closed_here")
    if ch:
        lines.append({"kind": "options", "text":
                      f"{ch['n_won']} of {ch['n']} closed option trade(s) on this name won "
                      f"({ch['note']})."})
    lines.append({"kind": "caveat", "text": o.get("convexity")})
    return lines
