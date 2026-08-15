"""Intraday signal tests (offline, synthetic bars). Run: python tests/test_intraday.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.intraday.signals import evaluate
from valuation.intraday.contracts import contract_idea, HORIZONS


def _uptrend_bars(n=260):
    close = [10.0 * (1 + 0.001 * i) for i in range(n)]
    return {"close": close, "high": [c * 1.01 for c in close],
            "low": [c * 0.99 for c in close], "volume": [1e6] * n}


def test_horizon_changes_score():
    bars = _uptrend_bars()
    opt = {"put_volume": 100, "call_volume": 400, "put_oi": 1000, "call_oi": 1000, "atm_iv": 0.35}
    sc = {h: evaluate(bars, opt, horizon=h)["score"] for h in HORIZONS}
    assert all(v is not None and 0 <= v <= 100 for v in sc.values())
    assert len({round(v, 1) for v in sc.values()}) >= 2      # horizon actually changes the blend


def test_contract_idea_scales_with_horizon():
    short = contract_idea(100.0, 0.30, "short")
    pos = contract_idea(100.0, 0.30, "position")
    assert short and pos
    assert short["dte_range"][1] < pos["dte_range"][0]              # nearer expiries for short
    assert pos["expected_move_abs"] > short["expected_move_abs"]     # longer horizon = bigger move
    assert "Put credit spread" in short["defined_risk"]
    assert contract_idea(None, 0.3, "swing") is None                # no price -> no idea


def test_bearish_scores_downtrend():
    from valuation.intraday.signals import evaluate_bearish
    n = 260
    down = {"close": [100.0 * (1 - 0.001 * i) for i in range(n)]}
    down["high"] = [c * 1.01 for c in down["close"]]
    down["low"] = [c * 0.99 for c in down["close"]]
    down["volume"] = [1e6] * n
    sb_down = evaluate_bearish(down, None, "swing")["score"]
    sb_up = evaluate_bearish(_uptrend_bars(), None, "swing")["score"]
    assert sb_down is not None and sb_down > 55        # a downtrend reads bearish
    assert sb_down > sb_up                              # ...and more bearish than an uptrend


def test_contract_direction():
    from valuation.intraday.contracts import contract_idea
    bull = contract_idea(100.0, 0.3, "swing", "bull")
    bear = contract_idea(100.0, 0.3, "swing", "bear")
    assert "call" in bull["directional"] and "Put credit spread" in bull["defined_risk"]
    assert "put" in bear["directional"] and "Call credit spread" in bear["defined_risk"]


# ----------------------------- options exit rule -----------------------------
def _flat_then(move_pct, n_pre=80, n_post=200, start=100.0):
    """80 quiet bars (so realized vol is defined) then a decisive step to start*(1+move_pct).

    The step is deliberately far beyond the ~12% 1-sigma band at iv=0.30/swing, so the
    target or stop is unambiguously crossed and the test isn't sitting on a boundary.
    """
    pre = [start * (1 + 0.001 * ((i % 5) - 2)) for i in range(n_pre)]   # tiny wiggle
    post = [start * (1 + move_pct)] * n_post
    return pre + post


def test_options_exit_take_profit_fires_first():
    from valuation.edge.deprecated_options_exit import simulate_exit
    closes = _flat_then(+0.40)                      # strong rally after entry
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "take_profit", e["outcome"]
    assert e["signal_return"] > 0
    assert e["exit_idx"] > e["entry_idx"]
    assert e["bars_held"] <= round(e["dte"] * 252 / 365) + 1


def test_options_exit_stop_loss_fires_first():
    from valuation.edge.deprecated_options_exit import simulate_exit
    closes = _flat_then(-0.40)                      # sharp decline after entry
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "stop_loss", e["outcome"]
    assert e["signal_return"] < 0


def test_options_exit_time_stop_when_nothing_triggers():
    from valuation.edge.deprecated_options_exit import simulate_exit
    closes = [100.0] * 400                          # dead flat: never hits +/-1 sigma
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bull", iv=0.30)
    assert e["outcome"] == "time_stop", e["outcome"]
    assert abs(e["signal_return"]) < 1e-9
    assert e["bars_held"] == round(e["dte"] * 252 / 365)


def test_options_exit_bearish_profits_on_a_fall():
    from valuation.edge.deprecated_options_exit import simulate_exit
    closes = _flat_then(-0.40)
    e = simulate_exit(closes, entry_idx=79, horizon="swing", direction="bear", iv=0.30)
    assert e["outcome"] == "take_profit", e["outcome"]
    assert e["signal_return"] > 0, "a bearish signal should profit when price falls"
    assert e["underlying_return"] < 0


def test_options_exit_vol_fallback_is_strictly_pre_entry():
    """Direct no-look-ahead check: mutating bars AFTER the entry must not move the vol."""
    from valuation.edge.deprecated_options_exit import realized_vol
    closes = _flat_then(+0.40)
    v_before = realized_vol(closes, end_idx=79)
    tampered = list(closes)
    for i in range(79, len(tampered)):            # violent post-entry noise
        tampered[i] = 100.0 * (3.0 if i % 2 else 0.4)
    v_after = realized_vol(tampered, end_idx=79)
    assert v_before is not None and v_before > 0
    assert v_after == v_before, "realized_vol must ignore everything at/after entry_idx"


def test_options_exit_summary_shapes():
    from valuation.edge.deprecated_options_exit import simulate_exit, summarize_exits
    ex = [simulate_exit(_flat_then(+0.40), 79, iv=0.30),
          simulate_exit(_flat_then(-0.40), 79, iv=0.30),
          simulate_exit([100.0] * 400, 79, iv=0.30)]
    s = summarize_exits(ex)
    assert s["n"] == 3
    assert set(s["by_outcome"]) == {"take_profit", "stop_loss", "time_stop"}
    assert abs(s["take_profit_rate"] - 1 / 3) < 1e-9
    assert summarize_exits([])["n"] == 0


# ----------------------------- live data archive -----------------------------
def _arch_root():
    import tempfile, os
    return os.path.join(tempfile.mkdtemp(), "arch")


def test_archive_captures_iv_and_contracts():
    """The whole point is preserving IV/skew + the contract we'd have traded, since that's
    what a real options-exit backtest needs and no vendor sells us cheaply."""
    import gzip, json, os
    from valuation.edge.archive import archive_intraday
    root = _arch_root()
    rows = [{"ticker": "AAPL", "score": 88, "rank": 1, "price": 210.0,
             "detail": {"price": 210.0, "opt_atm_iv": 0.29, "opt_put_call": 0.7,
                        "realized_vol": 0.24,
                        "contracts": {"swing": {"directional": "~35d call, ~60 DTE"}}}}]
    path = archive_intraday(rows, "2026-07-29 13:45", "tradier", root=root)
    assert path and os.path.exists(path)
    assert path.endswith(os.path.join("2026-07-29", "1345.json.gz")), path
    d = json.load(gzip.open(path, "rt", encoding="utf-8"))
    assert d["rows"][0]["detail"]["opt_atm_iv"] == 0.29
    assert "contracts" in d["rows"][0]
    # Two runs on the same day must not overwrite each other.
    p2 = archive_intraday(rows, "2026-07-29 15:30", "tradier", root=root)
    assert p2 != path and os.path.exists(p2)


def test_archive_scan_and_stats():
    import os
    from valuation.edge.archive import archive_scan, stats
    root = _arch_root()
    rows = [{"ticker": "KO", "rank": 1, "hot_score": 91.0, "price": 60.0,
             "sector": "Consumer Defensive", "extra": {"factors": {"value": 0.4}}}]
    p = archive_scan(rows, "2026-07-29", "fmp", root=root)
    assert p and os.path.exists(p)
    st = stats(root)
    assert st["scans"]["files"] == 1 and st["scans"]["days"] == 1


def test_archive_never_raises_and_skips_empty():
    """Archiving is a side benefit — it must never be able to take a scan down."""
    from valuation.edge.archive import archive_intraday, archive_scan
    root = _arch_root()
    assert archive_intraday([], "2026-07-29 13:45", root=root) is None
    assert archive_scan([], "2026-07-29", root=root) is None
    # A malformed run_time still archives (it just lands under an odd folder name).
    assert archive_intraday([{"ticker": "X"}], "bad-run-time", root=root) is not None
    # An unwritable root (a FILE where a directory must go) returns None, not an
    # exception - archiving must never be able to take a scan down.
    import tempfile, os
    fd, blocker = tempfile.mkstemp()
    os.close(fd)
    assert archive_scan([{"ticker": "X"}], "2026-07-29", root=blocker) is None


# ---------------------------------------------------------------------------------------- #
# Scream-buy options tracker: log the contract, score EXPECTANCY, tune only with evidence.
# ---------------------------------------------------------------------------------------- #

def _opt_store():
    import tempfile, os as _os
    from valuation.screener.store import Store
    return Store(_os.path.join(tempfile.mkdtemp(prefix="valquo_opt_"), "s.db"))


def _alert(ticker="AAPL", ts="2026-07-31T14:30:00", **kw):
    a = {"alert_ts": ts, "ticker": ticker, "opt_right": "call", "strike": 250.0,
         "expiry": "2026-12-18", "entry_premium": 5.00, "underlying_price": 240.0,
         "score": 93.0, "momentum_score": 80.0, "technical_score": 75.0,
         "iv": 0.35, "iv_rank": 45.0, "horizon": "swing", "target_delta": 35.0,
         "dte": 60, "flow_read": "Call-heavy", "labels": ["Breakout", "Call-heavy"]}
    a.update(kw)
    return a


def test_options_tracker_logs_contract_and_fingerprint():
    """The old tracking recorded the UNDERLYING's move. An option's P&L is not the stock's
    move, so the specific contract and the features that fired the alert must both be stored."""
    from valuation.edge import options_tracker as OT
    st = _opt_store()
    rid = OT.log_alert(st, _alert())
    assert rid, "first alert must be stored"
    # OCC id is derived so the same contract can be identified by an external filler.
    assert OT.occ_symbol("AAPL", "2026-12-18", "call", 250.0) == "AAPL261218C00250000"
    assert OT.occ_symbol("AAPL", None, "call", 250.0) is None
    # Same contract, same timestamp -> deduped, not double counted.
    assert OT.log_alert(st, _alert()) is None
    # Same contract on a LATER alert is a genuinely new observation.
    assert OT.log_alert(st, _alert(ts="2026-08-05T14:30:00"))
    rows = OT.open_alerts(st)
    assert len(rows) == 2
    r = rows[0]
    for f in ("ticker", "opt_right", "strike", "expiry", "entry_premium", "iv_rank",
              "horizon", "flow_read", "score"):
        assert r.get(f) is not None, f
    assert r["status"] == "open"
    # An alert with no chain detail is still worth recording -- the fingerprint is what the
    # tuning loop learns from.
    assert OT.log_alert(st, {"alert_ts": "2026-08-06T10:00:00", "ticker": "MSFT",
                             "score": 91.0, "horizon": "short"})
    assert OT.log_alert(st, {"ticker": "NOTS"}) is None      # no timestamp -> rejected


def test_options_expectancy_not_just_hit_rate():
    """Hit rate alone is meaningless for an asymmetric payoff: a 40%-hit strategy whose winners
    triple beats a 70%-hit one that gives it all back."""
    from valuation.edge import options_tracker as OT
    st = _opt_store()
    # 4 winners at +100%, 6 losers at -50% -> hit rate 40%, but expectancy is POSITIVE.
    for i in range(10):
        ts = f"2026-07-{i+1:02d}T10:00:00"
        OT.log_alert(st, _alert(ticker=f"T{i}", ts=ts, entry_premium=5.0))
        exit_prem = 10.0 if i < 4 else 2.5
        assert OT.record_outcome(st, ticker=f"T{i}", alert_ts=ts, exit_premium=exit_prem,
                                 exit_ts=ts, exit_reason="target" if i < 4 else "stop")
    sc = OT.scorecard(st)["overall"]
    assert sc["n_closed"] == 10
    assert abs(sc["hit_rate"] - 0.4) < 1e-9
    assert abs(sc["avg_win_pct"] - 1.0) < 1e-9
    assert abs(sc["avg_loss_pct"] - (-0.5)) < 1e-9
    assert abs(sc["expectancy_pct"] - 0.10) < 1e-9, sc["expectancy_pct"]   # .4*1 + .6*(-.5)
    assert abs(sc["profit_factor"] - (4.0 / 3.0)) < 1e-9
    # AUDIT MA46 — the same book on the commission-net basis, reported beside the gross one so a
    # comparison with the backtest reference is like-for-like. It does not REPLACE the figures
    # above: a $1.30 round trip on a $5.00 entry is 0.26pp, so net expectancy sits just below.
    assert sc["expectancy_pct_net"] < sc["expectancy_pct"]
    assert abs(sc["expectancy_pct_net"] - (0.10 - 0.0026)) < 1e-9, sc["expectancy_pct_net"]
    assert "gross" in sc["pnl_basis"]
    # 1-contract basis: 4 x +$500, 6 x -$250 = +$500
    assert abs(sc["cum_pnl_dollars"] - 500.0) < 1e-6
    # A closed trade must leave the open work list.
    assert OT.open_alerts(st) == []
    # Recording the same outcome twice must not double count.
    assert OT.record_outcome(st, ticker="T0", alert_ts="2026-07-01T10:00:00",
                             exit_premium=99.0) is False


def test_options_tuning_blocked_until_enough_closed_trades():
    """The hard guard: options outcomes are noisy and a handful of trades will always produce
    a flattering subgroup. Nothing may be tuned below MIN_CLOSED_PER_BUCKET."""
    from valuation.edge import options_tracker as OT
    st = _opt_store()
    # 10 swing winners, 10 short losers -- a huge apparent gap, but far too few trades.
    for i in range(10):
        for hz, prem in (("swing", 12.0), ("short", 2.0)):
            ts = f"2026-06-{i+1:02d}T10:00:00"
            OT.log_alert(st, _alert(ticker=f"{hz[:2].upper()}{i}", ts=ts, horizon=hz,
                                    entry_premium=5.0))
            OT.record_outcome(st, ticker=f"{hz[:2].upper()}{i}", alert_ts=ts,
                              exit_premium=prem, exit_ts=ts, exit_reason="x")
    tc = OT.tuning_candidates(st)
    assert tc["ready"] is False, "20 trades must not be enough to change a criterion"
    assert tc["suggestions"] == []
    assert any(b["dim"] == "horizon" for b in tc["blocked"])
    sc = OT.scorecard(st)
    assert sc["buckets"]["horizon"]["swing"]["enough_to_tune"] is False
    assert sc["buckets"]["horizon"]["swing"]["n_closed"] == 10

    # Past the floor on BOTH sides, the same separation becomes actionable.
    for i in range(10, 45):
        for hz, prem in (("swing", 12.0), ("short", 2.0)):
            ts = f"2026-09-{(i % 28) + 1:02d}T{i:02d}:00:00"
            OT.log_alert(st, _alert(ticker=f"{hz[:2].upper()}{i}", ts=ts, horizon=hz,
                                    entry_premium=5.0))
            OT.record_outcome(st, ticker=f"{hz[:2].upper()}{i}", alert_ts=ts,
                              exit_premium=prem, exit_ts=ts, exit_reason="x")
    tc2 = OT.tuning_candidates(st)
    assert tc2["ready"] is True
    s = [x for x in tc2["suggestions"] if x["dim"] == "horizon"]
    assert s and s[0]["favour"] == "swing" and s[0]["avoid"] == "short"
    assert s[0]["n_favour"] >= OT.MIN_CLOSED_PER_BUCKET
    assert s[0]["n_avoid"] >= OT.MIN_CLOSED_PER_BUCKET


def test_options_profit_factor_undefined_reads_as_no_evidence():
    """With no losing trades the ratio is undefined. It must read as 'not enough evidence',
    never as an infinitely good score."""
    from valuation.edge import options_tracker as OT
    st = _opt_store()
    for i in range(3):
        ts = f"2026-05-{i+1:02d}T10:00:00"
        OT.log_alert(st, _alert(ticker=f"W{i}", ts=ts, entry_premium=5.0))
        OT.record_outcome(st, ticker=f"W{i}", alert_ts=ts, exit_premium=8.0, exit_ts=ts)
    sc = OT.scorecard(st)["overall"]
    assert sc["hit_rate"] == 1.0
    assert sc["profit_factor"] is None, "undefined, not infinity"
    assert sc["avg_loss_pct"] is None
    assert sc["enough_to_tune"] is False
    # Empty store: no fake precision anywhere.
    empty = OT.scorecard(_opt_store())["overall"]
    assert empty["n_closed"] == 0 and empty["expectancy_pct"] is None


def test_options_outcome_api_contract_shape():
    """The Cowork filler talks to two endpoints. flask is not installed here so the routes
    cannot be exercised, but the contract they depend on can be: the work list, the write, and
    the fact that P&L is recomputed from the STORED entry premium rather than trusted."""
    # Read the SOURCE rather than importing: app_saas needs flask, which is not installed in
    # this environment, and the contract is a source-level fact.
    import os as _os
    _p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                       "valuation", "saas", "app_saas.py")
    with open(_p, encoding="utf-8") as _fh:
        src = _fh.read()
    assert '/api/option-alerts/open' in src and '/api/option-alerts/outcome' in src
    assert "X-Admin-Token" in src, "must be token-guarded, not session-guarded"
    # The endpoints must use the SCREENER store; `store` in that factory is the UserStore.
    assert "open_alerts(Store(), limit=limit)" in src
    assert "scr, alert_id=" in src

    from valuation.edge import options_tracker as OT
    st = _opt_store()
    ts = "2026-07-31T15:00:00"
    OT.log_alert(st, _alert(ticker="NVDA", ts=ts, entry_premium=4.0))
    work = OT.open_alerts(st)
    assert len(work) == 1 and work[0]["ticker"] == "NVDA"
    # A caller-supplied P&L is ignored: it is recomputed from the stored entry premium.
    assert OT.record_outcome(st, ticker="NVDA", alert_ts=ts, exit_premium=6.0,
                             exit_ts="2026-08-15T15:00:00", exit_reason="target")
    sc = OT.scorecard(st)["overall"]
    assert abs(sc["expectancy_pct"] - 0.5) < 1e-9, "6.00 vs 4.00 entry = +50%"
    assert abs(sc["cum_pnl_dollars"] - 200.0) < 1e-6
    # AUDIT MA46 — and +49.675% net of the $1.30 round trip, reported beside it rather than
    # replacing it, so the live book and the backtest can be compared on the same basis.
    assert abs(sc["expectancy_pct_net"] - 0.49675) < 1e-9, sc["expectancy_pct_net"]
    # An unmatched write must fail loudly rather than silently no-op.
    assert OT.record_outcome(st, ticker="NOPE", alert_ts=ts, exit_premium=1.0) is False


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} intraday tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
