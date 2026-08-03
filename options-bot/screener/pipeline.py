"""
pipeline.py — the daily run. Wires the tested engine to the live data layer.

  build universe (cached fundamentals + daily price) -> provisional score ->
  rank into two buckets -> for each bucket's candidate pool: pull fresh insider
  + 8-K, re-score, apply >$10B override -> Opus-dive new top entrants (cost-capped)
  -> detect events/alerts -> log picks + track entries -> what-changed -> post.

Run:
    python pipeline.py            # live
    python pipeline.py --dry-run    # validate without posting to Discord
    python pipeline.py --review   # run the advisory self-review and post it

Efficiency model (see config):
  * Fundamentals (XBRL) are cached and reused for FUNDAMENTALS_TTL_DAYS — they
    change quarterly, so only price is refreshed daily.
  * The expensive insider Form-4 pull + fresh 8-K fetch happen ONLY for the top
    CANDIDATE_POOL_PER_BUCKET names, not the whole universe. The intraday poller
    is the backstop for insider activity on names outside the pool.
"""

import os
import sys
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

import config as C
import scoring as S
import decisions as D
import edgar
import prices
import claude_analyst as ai
import discord_alerts as discord
from store import Store

DRY_RUN = "--dry-run" in sys.argv  # run fully but print instead of posting (no trading here)
DB_PATH = os.getenv("SCREENER_DB", "screener.db")


def universe_tickers():
    """
    The candidate universe. Defaults to all EDGAR filers, capped by UNIVERSE_LIMIT.

    RECOMMENDED (see README): seed this from the holdings of IWM (Russell 2000) +
    IJR (S&P SmallCap 600) instead of a raw 13k-filer scan. Those ETFs ARE the
    liquid sub-$10B universe this screener targets (~2,600 names), they match the
    benchmarks in config, and they keep the daily price pull tractable.
    """
    tickers = list(edgar.all_filers().keys())
    if C.UNIVERSE_LIMIT:
        tickers = tickers[:C.UNIVERSE_LIMIT]
    return tickers


def build_stock_data(ticker, store, today, with_insider=False):
    """
    Assemble one stock's data dict. Fundamentals come from cache when fresh
    (< FUNDAMENTALS_TTL_DAYS old); price is always refreshed. Insider + fresh
    8-K are pulled only when with_insider=True (candidate stage).
    """
    fund = None
    age = store.get_universe_age_days(ticker, today)
    if age is not None and age < C.FUNDAMENTALS_TTL_DAYS:
        fund = store.get_cached_fundamentals(ticker)          # fresh cache hit -> no EDGAR call
    if fund is None:
        fund = edgar.get_fundamentals(ticker)                 # cache miss/stale -> fetch + cache
        if fund:
            store.upsert_universe(ticker, fund.get("sector"), fund.get("shares"), fund)
    if not fund:
        return None

    quote = prices.get_quote(ticker)                          # always fresh (cheap, daily)
    if not quote:
        return None

    d = {**fund, **quote}
    if d.get("shares") and d.get("price"):
        d["market_cap"] = d["shares"] * d["price"]
    d.setdefault("ev_sales_percentile", None)

    if with_insider:                                          # candidate stage only
        d["insider_transactions"] = edgar.get_insider_txns(ticker, limit=6)
        d["recent_8k_items"] = edgar.get_8k_items(ticker)     # fresh, for event detection
    else:
        d.setdefault("insider_transactions", [])              # neutral until candidate stage
        d.setdefault("recent_8k_items", [])
    return d


def _prev_run_date(store, today, bucket):
    """The actual most-recent prior run date for this bucket (handles weekends/gaps)."""
    row = store.db.execute(
        "SELECT MAX(run_date) FROM daily_picks WHERE run_date < ? AND bucket=?",
        (today.isoformat(), bucket)).fetchone()
    if row and row[0]:
        return date.fromisoformat(row[0])
    return today - timedelta(days=1)


def _max_price_age_hours(universe_data):
    """
    Oldest price in the cross-section, in hours.

    This used to be the literal `24`, passed against a `> 48` threshold — so
    the staleness check was structurally incapable of firing. Now it is
    measured. Returns None when nothing carries a timestamp, which the gate
    treats as "unknown" rather than "fine".
    """
    from datetime import datetime, timezone
    ages = []
    now = datetime.now(timezone.utc)
    for d in universe_data:
        ts = d.get("price_asof") or d.get("price_date")
        if not ts:
            continue
        try:
            when = datetime.fromisoformat(str(ts))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            ages.append((now - when).total_seconds() / 3600.0)
        except (TypeError, ValueError):
            continue
    return max(ages) if ages else None


def run_daily(dry_run=DRY_RUN):
    today = date.today()
    store = Store(DB_PATH)

    # 1) cheap pass over the universe: cached fundamentals + daily price, NO insider yet
    tickers = universe_tickers()
    universe_data, errors = [], 0
    for tkr in tickers:
        try:
            d = build_stock_data(tkr, store, today, with_insider=False)
            if d:
                universe_data.append(d)
        except Exception:
            errors += 1

    # 2) data-health gate — skip + alert rather than publish garbage.
    #    `attempted` is what makes the gate a RATE rather than an absolute; and
    #    price age is now MEASURED rather than the hardcoded literal 24 that was
    #    passed against a >48 threshold, i.e. a check that could never fire.
    ok, reasons = D.health_check(
        len(universe_data),
        max_price_age_hours=_max_price_age_hours(universe_data),
        feed_errors=errors,
        attempted=len(tickers),
    )
    if not ok:
        discord.post("daily_list", "⚠️ Run skipped — data health", "; ".join(reasons), dry_run=dry_run)
        return

    # 3) Cross-sectional VALUE percentiles, then PROVISIONAL score (insider
    #    neutral) to find candidates.
    #
    #    This used to call the local compute_ev_sales_percentiles(), which set
    #    ONLY ev_sales_percentile — the Speculative bucket's value input. The
    #    Established bucket's value score read `dcf_upside`, which nothing in
    #    this codebase ever computed, so the single largest weight in the model
    #    (35%) returned a constant 50 for every name, every day.
    #
    #    scoring.compute_value_percentiles() replaces it and is a strict
    #    superset: it computes earnings_yield_percentile and ebit_ev_percentile
    #    for Established alongside the same ev_sales_percentile for Speculative,
    #    all sector-relative, all as YIELDS so that losses and negative
    #    enterprise values rank at the bottom rather than the top.
    S.compute_value_percentiles(universe_data)
    provisional = [s for s in (S.score_stock(d) for d in universe_data) if s]
    by_ticker = {d["ticker"]: d for d in universe_data}
    ranked0 = S.rank_universe(provisional)

    breaker = D.CostBreaker(spent_today=store.spend_today(today))
    throttle = D.AlertThrottle(store.recent_alerts())

    for bucket, names in ranked0.items():
        # 4) candidate pool: pull fresh insider + 8-K for the top pool, then RE-SCORE
        pool = names[:C.CANDIDATE_POOL_PER_BUCKET]
        for sc in pool:
            d = by_ticker[sc.ticker]
            d["insider_transactions"] = edgar.get_insider_txns(sc.ticker, limit=6)
            d["recent_8k_items"] = edgar.get_8k_items(sc.ticker)
        rescored = sorted((s for s in (S.score_stock(by_ticker[sc.ticker]) for sc in pool) if s),
                          key=lambda s: s.composite, reverse=True)

        # 5) >$10B eligibility (with override), then top / watchlist
        eligible = []
        for rank, sc in enumerate(rescored, start=1):
            d = by_ticker[sc.ticker]
            opens = [t for t in (d.get("insider_transactions") or []) if t.get("code") == "P"]
            if S.market_cap_eligible(d, rank, opens):
                eligible.append((rank, sc))
        top = eligible[:C.TOP_N]
        watch = eligible[C.TOP_N:C.TOP_N + C.WATCHLIST_N]

        yesterday = store.yesterday_ranks(_prev_run_date(store, today, bucket), bucket)
        today_ranks = {sc.ticker: r for r, sc in top}
        changes = D.rank_changes(today_ranks, yesterday)

        dive_summaries = {}
        for rank, sc in top:
            d = by_ticker[sc.ticker]
            events = D.detect_major_events(d, prior_rank=yesterday.get(sc.ticker), current_rank=rank)
            eligible_dive, why = D.deep_dive_eligible(
                sc.ticker, in_top_today=True,
                last_dive_date=store.last_dive_date(sc.ticker),
                first_listed_date=today, today=today, major_event=bool(events))
            if eligible_dive and breaker.can_dive() and not dry_run:   # dry-run never spends on dives
                text, cost = ai.deep_dive(d, sc, os.getenv("ANTHROPIC_API_KEY"))
                breaker.record(cost)
                store.record_dive(sc.ticker, today, today, {"text": text, "why": why})
                dive_summaries[sc.ticker] = text
            elif eligible_dive and dry_run:
                dive_summaries[sc.ticker] = "[dry-run: deep dive skipped — no API spend]"
            store.log_pick(today, sc, d.get("price"), d.get("market_cap"), rank)
            store.log_track(today, sc.ticker, d.get("price"))
            for ev in events:
                if throttle.allow(sc.ticker, datetime.now()):
                    discord.post("insider_flags", f"🚨 {sc.ticker}: {ev}",
                                 f"{d.get('name')} — rank #{rank} ({bucket})", dry_run=dry_run)
                    store.log_alert(datetime.now(), sc.ticker, "event", ev)

        # 6) post the daily list for this bucket
        body = _format_bucket(bucket, top, watch, changes, dive_summaries, by_ticker)
        discord.post("daily_list", f"📊 {bucket.title()} — {today.isoformat()}", body, dry_run=dry_run)

    store.set_spend(today, breaker.spent)
    if breaker.tripped:
        discord.post("daily_list", "⚠️ AI budget hit",
                     f"Hit ${C.MAX_DAILY_AI_SPEND}/day cap; remaining dives deferred.", dry_run=dry_run)


def _format_bucket(bucket, top, watch, changes, dives, by_ticker):
    lines = []
    for rank, sc in top:
        d = by_ticker[sc.ticker]
        tag = " 🔎" if sc.ticker in dives else ""
        lines.append(f"**#{rank} {sc.ticker}** — {sc.composite}/100 "
                     f"(${(d.get('market_cap') or 0)/1e9:.1f}B){tag}")
        if sc.ticker in dives:
            lines.append(f"> {dives[sc.ticker][:600]}")
    if watch:
        lines.append("\n*Watchlist:* " + ", ".join(f"{sc.ticker} ({sc.composite:.0f})" for _, sc in watch))
    if changes["added"] or changes["dropped"]:
        lines.append(f"\n*New:* {', '.join(changes['added']) or '—'}  |  "
                     f"*Dropped:* {', '.join(changes['dropped']) or '—'}")
    if changes["climbers"]:
        lines.append("*Climbing:* " + ", ".join(f"{t} (+{n})" for t, n in changes["climbers"]))
    return "\n".join(lines) or "No eligible names."


def run_review(dry_run=DRY_RUN):
    store = Store(DB_PATH)
    rows = store.db.execute(
        "SELECT t.run_date, t.ticker, t.ret_30, t.bench_iwm_30, t.bench_ijr_30, "
        "p.bucket, p.composite, p.components_json FROM track_record t "
        "LEFT JOIN daily_picks p ON t.run_date=p.run_date AND t.ticker=p.ticker").fetchall()
    cols = ["run_date", "ticker", "ret_30", "bench_iwm_30", "bench_ijr_30", "bucket", "composite", "components"]
    track = [dict(zip(cols, r)) for r in rows]
    text, _ = ai.self_review(track, os.getenv("ANTHROPIC_API_KEY"))
    discord.post("improvement_suggestions", "🧠 Strategy review (advisory)", text, dry_run=dry_run)


if __name__ == "__main__":
    if "--review" in sys.argv:
        run_review()
    else:
        run_daily()
