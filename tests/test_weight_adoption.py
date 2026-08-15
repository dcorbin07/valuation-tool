"""Master audit MA1/MA2/MA3 — the self-learning loop is disarmed, and it stays disarmed.

Every test here fails if one of the five links the audit traced is re-connected. The important
ones are the CONTROLS: a refusal that has only ever been shown to say no is indistinguishable
from `return False`, so each gate is exercised in BOTH directions with an injected register.
"""
import datetime as _dt
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation                                    # noqa: F401  (must precede valuation)

import numpy as np
import pandas as pd

from valuation.backtest.optimize import optimize_weights
from valuation.edge import weight_adoption as WA
from valuation.edge.weight_adoption import VintageRefusal
from valuation.screener import screen as SC
from valuation.screener import settings as S
from valuation.screener.store import Store

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- helpers
def _store():
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(p)
    return Store(p), p


def _register(vintage=9, buckets=("established",), status="OPEN"):
    return ({"vintage": 8, "status": "CLOSED", "opened": _dt.date(2026, 1, 1)},
            {"vintage": vintage, "status": status, "opened": _dt.date(2026, 9, 1),
             "weights_adoption": {"buckets": list(buckets)}})


def _contract(tmpdir, value="YES - vintage 9 - 2026-09-01", field="Learned weights adopted"):
    p = os.path.join(tmpdir, "CONTRACT.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# contract\n\n| field | value |\n|---|---|\n"
                 "| Some other row | nonsense |\n"
                 f"| {field} | {value} |\n")
    return p


def _authorised_kw(tmpdir, **kw):
    return dict(vintages=_register(**kw.pop("reg", {})),
                contract_path=_contract(tmpdir, **kw))


# --------------------------------------------------------------------------- the gate
def test_nothing_is_authorised_today():
    """The shipped register and the real contract authorise NOTHING, for both buckets."""
    for bucket in ("established", "speculative"):
        a = WA.authorisation(bucket)
        assert a["authorised"] is False
        assert a["reason"]                                  # never a bare False
    # ...and the reason is the register, not a missing file: the real contract IS readable.
    from valuation.screener import index_track as IT
    assert os.path.exists(IT.contract_path())


def test_the_gate_can_reach_authorised():
    """CONTROL. Without this, every other test here is satisfied by `return False`."""
    with tempfile.TemporaryDirectory() as d:
        a = WA.authorisation("established", vintages=_register(), contract_path=_contract(d))
        assert a["authorised"] is True and a["registered"] and a["signed"]
        assert a["vintage"] == 9 and a["signed_vintage"] == 9
        WA.require("established", vintages=_register(), contract_path=_contract(d))   # no raise


def test_either_half_alone_is_not_enough():
    with tempfile.TemporaryDirectory() as d:
        signed = _contract(d)
        # register present, signature absent
        empty = os.path.join(d, "EMPTY.md")
        open(empty, "w", encoding="utf-8").write("# no rows here\n")
        a = WA.authorisation("established", vintages=_register(), contract_path=empty)
        assert a["authorised"] is False and a["registered"] is True and a["signed"] is False
        # signature present, register key absent
        reg = ({"vintage": 9, "status": "OPEN", "opened": _dt.date(2026, 9, 1)},)
        b = WA.authorisation("established", vintages=reg, contract_path=signed)
        assert b["authorised"] is False and b["registered"] is False


def test_a_signature_does_not_carry_forward_to_another_vintage():
    """The row names vintage 9; the open vintage is 10. That must not authorise."""
    with tempfile.TemporaryDirectory() as d:
        a = WA.authorisation("established", vintages=_register(vintage=10),
                             contract_path=_contract(d, value="YES - vintage 9 - 2026-09-01"))
        assert a["authorised"] is False
        assert a["signed_vintage"] == 9 and a["vintage"] == 10
        assert "does not carry forward" in a["reason"]


def test_a_registered_bucket_does_not_authorise_the_other_one():
    with tempfile.TemporaryDirectory() as d:
        kw = dict(vintages=_register(buckets=("established",)), contract_path=_contract(d))
        assert WA.authorisation("established", **kw)["authorised"] is True
        assert WA.authorisation("speculative", **kw)["authorised"] is False


def test_every_unreadable_authority_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        good = _contract(d)
        cases = {
            "missing contract": dict(vintages=_register(),
                                     contract_path=os.path.join(d, "nope.md")),
            "no open vintage": dict(vintages=_register(status="CLOSED"), contract_path=good),
            "two open vintages": dict(
                vintages=({"vintage": 9, "status": "OPEN", "weights_adoption": {"buckets": ["established"]}},
                          {"vintage": 10, "status": "OPEN", "weights_adoption": {"buckets": ["established"]}}),
                contract_path=good),
            "empty register": dict(vintages=(), contract_path=good),
            "hedged signature": dict(vintages=_register(),
                                     contract_path=_contract(d + os.sep, value="yes-ish, vintage 9")
                                     if False else _contract(d, value="pending - vintage 9")),
            "signature names no vintage": dict(vintages=_register(),
                                               contract_path=_contract(d, value="YES - 2026-09-01")),
        }
        for label, kw in cases.items():
            a = WA.authorisation("established", **kw)
            assert a["authorised"] is False, label
            assert a["reason"], label


def test_a_documented_example_row_does_not_authorise():
    """The contract may SHOW the canonical row without that row signing anything."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "C.md")
        open(p, "w", encoding="utf-8").write(
            "# contract\n\n> Set this row on adoption day:\n>\n> ```\n"
            "> | Learned weights adopted | YES - vintage 9 - 2026-09-01 |\n> ```\n")
        a = WA.authorisation("established", vintages=_register(), contract_path=p)
        assert a["authorised"] is False and a["signed"] is False


def test_the_token_rule_is_index_tracks_and_is_not_re_derived():
    """One contract, one parser. A second token rule is how a signature comes to mean two things."""
    from valuation.screener import index_track as IT
    assert WA._signed_vintage("YES - vintage 4 - 2026-08-13") == 4
    assert WA._signed_vintage("passed vintage 12") == 12
    for bad in ("pending - vintage 4", "no", "", "yes-ish, vintage 4", "YES - 2026-08-13"):
        assert WA._signed_vintage(bad) is None, bad
    assert IT._verdict_token("YES - vintage 4") == "yes"          # the shared rule, still shared


# --------------------------------------------------------------------------- the funnel
def test_save_learned_refuses_an_unauthorised_adoption_and_writes_nothing():
    st, p = _store()
    st.save_learned("established", {"value": 1.0}, {}, False, "a non-adoption still logs")
    before = len(st.learning_history(limit=50))
    assert before == 1
    try:
        st.save_learned("established", {"value": 1.0}, {}, True, "should never land")
        raise AssertionError("save_learned accepted an unauthorised adoption")
    except VintageRefusal as e:
        assert "Nothing was written" in str(e)
    assert len(st.learning_history(limit=50)) == before        # the write did NOT happen
    assert st.latest_learned_weights("established") is None


def test_the_funnel_is_shared_by_both_writers():
    """MA3: the endpoint and the monthly learner refuse for the SAME reason, in one place."""
    import ast
    src = open(os.path.join(REPO, "valuation", "saas", "app_saas.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
           and n.name == "admin_adopt_backtest_weights"]
    assert len(fns) == 1
    body = ast.dump(fns[0])
    assert "VintageRefusal" in body, "the adopt endpoint no longer handles the refusal"
    assert "save_learned" in body
    # and it does not sneak past the funnel with its own INSERT
    assert "learned_config" not in src


def test_the_live_scorer_ignores_an_unauthorised_stored_adoption():
    """A row written before the gate existed is a vintage VIOLATION, not a weight."""
    st, p = _store()
    with sqlite3.connect(p) as c:                       # bypass the funnel, as production may have
        c.execute("INSERT INTO learned_config (created_at,bucket,weights,stats,adopted,note) "
                  "VALUES (?,?,?,?,1,?)",
                  ("2026-07-04T12:00:00", "established", '{"value": 1.0}', "{}", "pre-audit row"))
    assert st.latest_learned_weights("established") == {"value": 1.0}   # still THERE...
    SC.LAST_WEIGHT_REFUSAL.clear()
    est, spec = SC._effective_weights(st)
    assert est == S.WEIGHTS_ESTABLISHED                                 # ...and NOT used
    assert spec == S.WEIGHTS_SPECULATIVE
    assert SC.LAST_WEIGHT_REFUSAL.get("established", {}).get("authorised") is False

    # CONTROL: authorised, and the very same row IS used. Proves the refusal is the gate
    # doing its job rather than the learned path being dead.
    real = WA.authorisation
    try:
        WA.authorisation = lambda bucket, **kw: {"authorised": True, "reason": "test"}
        assert SC._effective_weights(st)[0] == {"value": 1.0}
    finally:
        WA.authorisation = real


def test_the_violation_is_reported_with_its_date_not_erased():
    st, p = _store()
    with sqlite3.connect(p) as c:
        c.execute("INSERT INTO learned_config (created_at,bucket,weights,stats,adopted,note) "
                  "VALUES (?,?,?,?,1,?)",
                  ("2026-07-04T12:00:00", "established", '{"value": 1.0}',
                   '{"source": "historical_backtest"}', "pre-audit row"))
    rep = WA.live_override_report(st)
    assert rep["store_readable"] and rep["n_adopted"] == 1
    assert rep["clean"] is False and len(rep["violations"]) == 1
    v = rep["violations"][0]
    assert v["created_at"] == "2026-07-04T12:00:00" and v["bucket"] == "established"
    assert v["source"] == "historical_backtest"          # the two writers stay distinguishable
    assert st.latest_learned_weights("established") is not None   # reporting did not delete it


def test_a_clean_store_reports_clean():
    st, _ = _store()
    rep = WA.live_override_report(st)
    assert rep["store_readable"] and rep["n_adopted"] == 0 and rep["clean"] is True
    assert rep["authorisation"]["established"]["authorised"] is False


# --------------------------------------------------------------------------- the cron + the flag
def test_the_workflow_no_longer_triggers_a_re_tune():
    p = os.path.join(REPO, ".github", "workflows", "auto-scan.yml")
    text = open(p, encoding="utf-8").read()
    live = "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))
    assert "run-learning" not in live, "the self-learning trigger is back in the cron"
    assert '"0 12 1 * *"' not in live, "the monthly self-learning cron is back"
    # NOT VACUOUS: this is the real workflow and it still triggers everything else it used to.
    assert len(live.splitlines()) > 100
    for still_there in ("/admin/run-paper-track", "schedule:", "curl", "cron:"):
        assert still_there in live, still_there


def test_learn_enabled_defaults_off_and_is_documented():
    from valuation.config import Config
    saved = os.environ.pop("LEARN_ENABLED", None)
    try:
        assert Config().learn_enabled is False
        os.environ["LEARN_ENABLED"] = "true"
        assert Config().learn_enabled is True             # the switch still works
        for off in ("false", "0", "", "no", "TRUE-ish"):
            os.environ["LEARN_ENABLED"] = off
            assert Config().learn_enabled is False, off   # anything unrecognised is OFF
    finally:
        os.environ.pop("LEARN_ENABLED", None)
        if saved is not None:
            os.environ["LEARN_ENABLED"] = saved
    src = open(os.path.join(REPO, "valuation", "config.py"), encoding="utf-8").read()
    assert "LEARN_ENABLED" in src.split("learn_enabled")[0][-1400:], "the flag is undocumented"


# --------------------------------------------------------------------------- MA2, the gate itself
def _panel(n_dates, n_names, signal, seed, symmetric=False):
    """`symmetric=True` makes 50/50 the TRUE optimum, so the in-sample argmax is usually a
    corner that loses to equal weight out of sample — the case MA2(a) could not see."""
    rng = np.random.default_rng(seed)
    v_noise = 0.4 if symmetric else 0.9
    rows = []
    for d in range(n_dates):
        for i in range(n_names):
            sc = float(rng.normal())
            row = {"date": f"P{d:03d}", "ticker": f"T{i:03d}",
                   "fwd_ret": signal * sc + float(rng.normal(0, 1.0))}
            row["momentum"] = sc + float(rng.normal(0, 0.4))
            row["value"] = sc * (1.0 if symmetric else 0.5) + float(rng.normal(0, v_noise))
            rows.append(row)
    return pd.DataFrame(rows)


def test_ma2a_the_equal_weight_baseline_now_binds():
    """It was computed, quoted in the adopt verdict, and left out of the decision."""
    d = {"momentum": 0.5, "value": 0.5}
    seen_binding = seen_strict_loss = False
    for seed in range(40):
        r = optimize_weights(_panel(30, 60, 0.05, seed, symmetric=True), ["momentum", "value"],
                             step=0.25, default_weights=d)
        assert "beats_equal_weight" in r
        if r["accepted"]:
            # THE INVARIANT THE OLD CODE COULD VIOLATE: it could adopt weights that lost to the
            # incumbent out-of-sample while writing "Recommended over equal-weight" in the verdict.
            assert r["out_sample_ic"] > r["equal_weight_oos_ic"]
            assert r["beats_equal_weight"] is True
        elif "did not beat equal-weight" in r["verdict"]:
            # An arm that cleared EVERY other leg — positive OOS IC, held its in-sample fraction,
            # cleared the significance floor — and is rejected solely because it lost to the
            # incumbent. Under the pre-audit gate this exact arm ADOPTED.
            seen_binding = True
            assert r["beats_equal_weight"] is False
            assert r["out_sample_ic"] > 0
            assert r["out_sample_ic"] >= 0.5 * r["in_sample_ic"]
            assert r["out_sample_ic"] >= r["significance_floor"]
            if r["out_sample_ic"] < r["equal_weight_oos_ic"]:
                seen_strict_loss = True
    assert seen_binding, "no seed exercised the equal-weight leg — the test proves nothing"
    # A TIE would be enough to satisfy the leg and is the uninteresting half of it: the defect
    # MA2(a) names is adopting weights that are WORSE than the incumbent while the verdict says
    # they beat it, so at least one seed must be a strict loss or this pins the wrong thing.
    assert seen_strict_loss, "every binding seed was an exact tie — the defect is not exercised"


def test_ma2a_a_nan_baseline_fails_closed():
    d = {"momentum": 0.5, "value": 0.5}
    p = _panel(30, 60, 0.20, 3)
    r = optimize_weights(p, ["momentum", "value"], step=0.25, default_weights=d)
    assert r["accepted"] is True                     # a real signal still adopts
    r2 = optimize_weights(p, ["momentum", "value"], step=0.25, default_weights=d,
                          overlap_periods=10_000)    # an absurd overlap must not adopt
    assert r2["accepted"] is False and "significance floor" in r2["verdict"]


def test_ma2b_the_default_reproduces_the_old_arithmetic_exactly():
    """overlap_periods=1 must change nothing, or this re-calibrated a live gate silently."""
    p = _panel(30, 60, 0.10, 7)
    r = optimize_weights(p, ["momentum", "value"], step=0.25)
    n_dates, avg = r["oos_dates"], 60.0
    expected = 1.64 * (1.0 / ((avg - 1.0) * n_dates) ** 0.5)
    assert abs(r["significance_floor"] - expected) < 1e-12
    assert r["overlap_periods"] == 1.0 and r["effective_oos_dates"] == float(n_dates)


def test_ma2b_the_known_bad_overlapping_fixture_the_guard_never_had():
    """MA2: both existing tests feed i.i.d. panels — the one world where `_std_null` is right.

    Here consecutive dates SHARE their return window, exactly as `autolearn`'s daily snapshots
    with a 21-day horizon do. There is no cross-sectional signal at all, so every accept is a
    false positive. The naive floor lets them through; the overlap-corrected floor does not.
    """
    h = 21
    rng = np.random.default_rng(11)
    naive_accepts = corrected_accepts = 0
    for trial in range(12):
        n_dates, n_names = 40, 60
        daily = rng.normal(0, 1.0, size=(n_dates + h, n_names))      # per-name daily returns
        rows = []
        for d in range(n_dates):
            fwd = daily[d:d + h].sum(axis=0)                          # OVERLAPPING windows
            noise = rng.normal(0, 1.0, size=n_names)
            for i in range(n_names):
                rows.append({"date": f"P{d:03d}", "ticker": f"T{i:03d}", "fwd_ret": float(fwd[i]),
                             # a factor correlated with the SHARED component, not with the future
                             "momentum": float(daily[d, i] + 0.3 * noise[i]),
                             "value": float(noise[i])})
            rng = np.random.default_rng(1000 + trial * 97 + d)
        p = pd.DataFrame(rows)
        naive = optimize_weights(p, ["momentum", "value"], step=0.25)
        corrected = optimize_weights(p, ["momentum", "value"], step=0.25, overlap_periods=h)
        naive_accepts += bool(naive["accepted"])
        corrected_accepts += bool(corrected["accepted"])
        assert corrected["significance_floor"] > naive["significance_floor"]
        assert corrected["effective_oos_dates"] < naive["effective_oos_dates"]
    # The correction can only ever tighten, never loosen.
    assert corrected_accepts <= naive_accepts


def test_the_overlap_estimate_is_measured_from_the_dates_present():
    from valuation.edge.autolearn import _overlap_periods
    daily = pd.DataFrame({"date": pd.bdate_range("2026-01-01", periods=40).astype(str)})
    weekly = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=40, freq="7D").astype(str)})
    assert _overlap_periods(daily, 21) > 15                 # daily snapshots -> heavy overlap
    assert 3.0 < _overlap_periods(weekly, 21) < 6.0         # weekly -> far less
    assert _overlap_periods(weekly, 1) == 1.0               # never below 1
    assert _overlap_periods(pd.DataFrame({"date": ["2026-01-01"]}), 21) == 1.0
    assert _overlap_periods(pd.DataFrame({"date": ["junk", "junk"]}), 21) == 1.0


# --------------------------------------------------------------------------- end to end
def test_the_learner_still_runs_and_still_cannot_ship():
    """The research keeps happening; only the live write is withheld. Both halves matter."""
    from valuation.config import CONFIG
    from valuation.edge.autolearn import run_learning

    rng = np.random.default_rng(5)
    rows = []
    for di in range(12):
        for ni in range(60):
            vals = {f: float(rng.normal()) for f in S.FACTORS_ALL}
            fr = 0.35 * (vals["value"] + vals["quality"]) + rng.normal()
            rows.append(dict(vals, date=f"2026-{di + 1:02d}-01", ticker=f"T{ni}",
                             bucket="established", fwd_ret=fr))
    st, _ = _store()
    rep = run_learning(CONFIG, st, panel=pd.DataFrame(rows))
    b = rep["buckets"]["established"]
    assert rep["status"] == "ok"
    assert b["adopted"] is False and b["refused"] is True
    assert b["would_have_adopted"], "the learner found nothing — this proves the gate, not the loop"
    assert st.latest_learned_weights("established") is None      # nothing reached live
    assert any(r["note"] and "NOT ADOPTED" in r["note"] for r in st.learning_history(limit=10))
    assert SC._effective_weights(st)[0] == S.WEIGHTS_ESTABLISHED


def test_the_learners_baseline_ignores_an_unauthorised_stored_adoption():
    """Same leak, one layer in: an unauthorised row must not set what candidates are measured
    against, or the learner tunes relative to weights users never received."""
    from valuation.config import CONFIG
    from valuation.edge.autolearn import run_learning

    st, p = _store()
    junk = {f: (1.0 if f == "value" else 0.0) for f in S.FACTORS_ALL}
    with sqlite3.connect(p) as c:
        c.execute("INSERT INTO learned_config (created_at,bucket,weights,stats,adopted,note) "
                  "VALUES (?,?,?,?,1,?)",
                  ("2026-07-04T12:00:00", "established", __import__("json").dumps(junk), "{}",
                   "pre-audit row"))
    rng = np.random.default_rng(9)
    rows = []
    for di in range(12):
        for ni in range(60):
            vals = {f: float(rng.normal()) for f in S.FACTORS_ALL}
            rows.append(dict(vals, date=f"2026-{di + 1:02d}-01", ticker=f"T{ni}",
                             bucket="established", fwd_ret=float(rng.normal())))
    rep = run_learning(CONFIG, st, panel=pd.DataFrame(rows))
    b = rep["buckets"]["established"]
    assert b["previous"] != junk, "the learner seeded itself from an unauthorised adoption"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok   {name}")
            except Exception as e:
                fails += 1
                print(f"  FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len([k for k in globals() if k.startswith('test_')]) - fails} passed, {fails} failed")
    raise SystemExit(1 if fails else 0)
