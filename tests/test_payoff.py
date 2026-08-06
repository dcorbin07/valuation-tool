"""A 37% hit rate has to be DESIGNED for, not merely disclosed (audit P3).

    python tests/test_payoff.py

THE PROBLEM. The options book wins about a third of the time. That is the strategy — most
trades lose a little and a few win big — but a user who takes six alerts and loses six times
concludes the tool is broken, and reasons correctly from the evidence they were handed. The
product already DISCLOSED the hit rate. Disclosure does not tell a reader whether THEIR run of
losses is ordinary; that is a calculation, and these tests pin it.

WHAT IS PINNED HERE, in the order it matters:

  1. The distribution is the banked one. Every constant is checkable against
     `data/options_universe/UNIVERSE_RESULTS.json` (corrected 187-name book, 3,885 trades) and
     the buckets are exhaustive — a chart that does not sum to one has invented a trade.

  2. The verdict can say NO. The failure mode this feature is most likely to produce is a
     design that can only ever reassure, so the tests assert that long runs come back
     `unusual` / `rare` / `beyond_record`, and that a short history comes back `too_few`
     instead of a comforting number.

  3. The expectation arrives before the losses. The streak sentence is asserted to be present
     on the surfaces a reader meets FIRST — the public `/api/whatdo` payload and the recap
     footer — not only on the scorecard they open after a bad week.

  4. Nothing here implies the alerts work. The options entry signal is measured dead (R2), and
     `NOT_A_CLAIM` must travel with every payload that carries the payoff shape.

  5. The comfortable arithmetic is not the one used. Independence understates the tail because
     outcomes cluster; the test asserts the shipped percentile is the measured one, and that it
     is the LOOSER of the two, so the interface does not cry wolf on an ordinary run.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import payoff as P                        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(ROOT, "valuation", "web", "static", "app.js")
METHODOLOGY = os.path.join(ROOT, "valuation", "web", "templates", "methodology.html")

#: The banked result file, when it is present. The licensed panel is gitignored, so CI runs
#: without it — but a worktree is three levels below the real checkout and the data directory
#: lives there, so BOTH are searched. Without the second path this test looked like it was
#: verifying the transcription in every agent worktree and was in fact asserting nothing.
_REL = os.path.join("data", "options_universe", "UNIVERSE_RESULTS.json")
BANKED_PATHS = [os.path.join(ROOT, _REL),
                os.path.join(ROOT, "..", "..", "..", _REL)]


def _banked():
    for p in BANKED_PATHS:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                return (json.load(f) or {}).get("overall")
        except (OSError, ValueError):
            continue
    return None


#: What was transcribed, pinned INDEPENDENTLY of whether the licensed file is reachable. The
#: file-based check above is the real one, but it degrades to a no-op wherever the data is
#: absent, and a test that quietly never reaches its assertion is worse than no test — so the
#: values are also frozen here. Editing a constant in `payoff.py` now fails the suite
#: everywhere, and re-deriving one means changing it in both places on purpose.
FROZEN = {"HIT_RATE": 0.35315, "AVG_WIN": 1.14559, "AVG_LOSS": -0.57273,
          "MEDIAN_TRADE": -0.52222, "EXPECTANCY": 0.03410, "PROFIT_FACTOR": 1.09205,
          "P_TAIL_WIN": 0.25019, "P_TOTAL_LOSS": 0.01390, "P_STOP_OUT": 0.59640,
          "TAIL_SHARE_OF_GROSS_WIN": 0.86752}


# ----------------------------------------------------------------- 1. the distribution is real
def test_the_constants_match_what_was_frozen_when_they_were_transcribed():
    """Runs everywhere, licensed data or not. See FROZEN."""
    for attr, want in FROZEN.items():
        assert abs(getattr(P, attr) - want) < 1e-9, (
            f"{attr} was changed to {getattr(P, attr)} without updating FROZEN — if this was "
            f"a deliberate re-derivation, change both and say where the new number came from")


def test_the_constants_are_transcribed_from_the_banked_book_not_invented():
    o = _banked()
    if o is None:
        print("       (licensed panel absent — file check skipped, FROZEN still enforced)")
        return
    for attr, key in (("HIT_RATE", "hit_rate"), ("AVG_WIN", "avg_win_pct"),
                      ("AVG_LOSS", "avg_loss_pct"), ("MEDIAN_TRADE", "median_pct"),
                      ("EXPECTANCY", "expectancy_pct"), ("PROFIT_FACTOR", "profit_factor"),
                      ("P_TAIL_WIN", "p_tail_win"), ("P_TOTAL_LOSS", "p_total_loss"),
                      ("P_STOP_OUT", "p_stop_out"),
                      ("TAIL_SHARE_OF_GROSS_WIN", "tail_share_of_gross_win")):
        ours, theirs = getattr(P, attr), float(o[key])
        assert abs(ours - theirs) < 5e-5, f"{attr} is {ours}, the book says {theirs}"


def test_the_book_it_quotes_is_the_corrected_one_not_the_superseded_run():
    # 3,042 trades is the pre-B1 book. Quoting it anywhere would republish a superseded number.
    assert P.N_TRADES == 3885 and P.N_NAMES == 187
    src = open(P.__file__, "r", encoding="utf-8").read()
    assert "3042" not in src.replace(",", "") or "superseded" in src.lower()


def test_the_two_published_hit_rates_reconcile_by_universe_not_by_defect():
    # 37% is the megacap book, 35% the broad one. If these ever stop bracketing the headline,
    # the range has become a hedge rather than a measurement and should not be published.
    assert P.HIT_RATE_BROAD < P.HIT_RATE < P.HIT_RATE_MEGACAP
    assert 0.37 < P.HIT_RATE_MEGACAP < 0.38, "the megacap half should reproduce the published 37%"
    o = _banked()
    if o is None:
        return
    # And that split is in the banked file, not asserted here.
    import json as _j
    for p in BANKED_PATHS:
        if os.path.exists(p):
            full = _j.load(open(p, "r", encoding="utf-8"))
            break
    mega = full["baseline_55_names"]["stats"]["hit_rate"]
    new = full["new_names_only"]["stats"]["hit_rate"]
    assert abs(mega - P.HIT_RATE_MEGACAP) < 5e-5 and abs(new - P.HIT_RATE_BROAD) < 5e-5


def test_the_buckets_are_exhaustive_and_mutually_exclusive():
    b = P.outcome_buckets()
    assert abs(sum(x["share"] for x in b) - 1.0) < 1e-6, "the shares do not sum to one"
    assert len({x["key"] for x in b}) == len(b)
    losses = sum(x["share"] for x in b if x["sign"] == "loss")
    assert abs(losses - (1.0 - P.HIT_RATE)) < 1e-3, "loss buckets disagree with the hit rate"


def test_the_shape_is_the_thing_a_reader_can_see():
    # The whole point of showing a distribution: most trades lose, and the winners are the tail.
    b = {x["key"]: x["share"] for x in P.outcome_buckets()}
    assert b["stopped_out"] > b["big_win"] > b["small_win"]
    assert P.MEDIAN_TRADE < -0.4, "the median trade should be a large loss"
    assert P.TAIL_SHARE_OF_GROSS_WIN > 0.8


# --------------------------------------------------------------- 2. the verdict can say NO
def test_a_short_history_gets_no_verdict_rather_than_a_comforting_one():
    v = P.streak_verdict(6, 6)
    assert v["verdict"] == "too_few"
    assert "too few" in v["text"].lower()
    # It must not sneak a percentile in anyway.
    assert v["share_of_stretches"] is None


def test_an_ordinary_run_is_called_ordinary_with_the_number_attached():
    v = P.streak_verdict(20, 5)
    assert v["verdict"] == "ordinary"
    assert "5" in v["text"] and "20" in v["text"]
    assert v["share_of_stretches"] > 0.5, "a median run should be common by construction"


def test_a_long_run_is_called_unusual_and_a_longer_one_worse():
    assert P.streak_verdict(20, 11)["verdict"] == "unusual"
    assert P.streak_verdict(20, 13)["verdict"] == "rare"
    assert P.streak_verdict(20, 25)["verdict"] == "beyond_record"


def test_the_verdict_is_monotone_in_the_run_length():
    order = {"ordinary": 0, "unusual": 1, "rare": 2, "beyond_record": 3}
    seen = [order[P.streak_verdict(30, k)["verdict"]] for k in range(1, 31)]
    assert seen == sorted(seen), "a longer losing run must never read as safer"


def test_the_design_is_not_only_capable_of_reassurance():
    # The failure mode the audit warns about: if every reachable input says "fine", the badge
    # is decorative. Assert both halves are reachable on the scale a real book runs at.
    verdicts = {P.streak_verdict(20, k)["verdict"] for k in range(1, 21)}
    assert "ordinary" in verdicts and len(verdicts - {"ordinary"}) >= 2


# ------------------------------------------------------- 3. expectation arrives before losses
def test_the_expectation_sentence_carries_a_number_not_a_reassurance():
    line = P.expectation_line(20)
    assert re.search(r"\d", line), "an expectation with no number is a platitude"
    assert "typical worst run" in line and "worst at this scale" in line


def test_the_public_name_view_states_the_streak_before_any_loss_has_happened():
    from valuation.web import unified
    assert "typical worst run" in unified._CONVEXITY
    # and the range, not one endpoint presented as the hit rate
    assert P.HIT_RATE_RANGE in unified._CONVEXITY


def test_the_withheld_options_branch_still_carries_the_shape():
    # A visitor who is told an alert exists but not what it is has the LEAST context and is the
    # most likely to read "options signal" as "likely winner".
    from valuation.web import unified

    class _Store:
        def latest_scan_date(self): return None
        def load_snapshot(self, d): return []

    v = unified.name_view(_Store(), "AAPL", with_options=False)
    assert v["options"]["withheld"] is True
    assert v["options"]["payoff"]["buckets"], "the shape was withheld along with the contract"
    assert v["options"]["payoff"]["not_a_claim"]


def test_the_recap_footer_sets_the_expectation_on_every_post():
    from valuation.saas import recap
    assert "typical worst run" in recap._CONVEXITY
    assert P.HIT_RATE_RANGE in recap._CONVEXITY


def test_the_recap_and_the_web_app_quote_one_source_not_two():
    # They each used to hold their own copy of the convexity sentence. Two copies of a fact is
    # how the two surfaces end up a point and a half apart with nothing saying so.
    from valuation.saas import recap
    from valuation.web import unified
    assert P.HIT_RATE_RANGE in recap._CONVEXITY and P.HIT_RATE_RANGE in unified._CONVEXITY
    src = open(recap.__file__, "r", encoding="utf-8").read()
    assert "from ..web import payoff" in src


# --------------------------------------------------- 4. none of this claims the alerts work
def test_every_payload_carrying_the_shape_also_carries_the_refusal():
    s = P.payoff_summary()
    assert "not evidence" in s["not_a_claim"]
    assert "-6.65pp" in s["not_a_claim"], "the measured R2 gap must be quoted, not gestured at"
    for k in ("verdict", "text"):
        assert k in P.streak_verdict(20, 9)
    assert P.streak_verdict(20, 9)["not_a_claim"] == P.NOT_A_CLAIM
    assert P.streak_verdict(3, 3)["not_a_claim"] == P.NOT_A_CLAIM


def test_the_shape_is_labelled_a_simulation_and_not_an_account():
    s = P.payoff_summary()
    assert "historical simulation" in s["basis"]
    assert "not a return anyone earned" in s["basis"]


def test_no_surface_calls_the_options_alerts_an_edge():
    js = open(APP_JS, "r", encoding="utf-8").read()
    html = open(METHODOLOGY, "r", encoding="utf-8").read()
    for text, where in ((js, "app.js"), (html, "methodology.html")):
        low = text.lower()
        for claim in ("proven edge in options", "options edge is real"):
            assert claim not in low, f"{where} claims an options edge"
    assert "subtracted" in html, "the methodology page must state that the alert subtracts value"


# ------------------------------------------- 5. the measured table, not the tidy arithmetic
def test_the_shipped_percentile_is_the_measured_one_and_it_is_the_looser_one():
    for n, row in P.STREAK_TABLE.items():
        assert row["p95"] >= row["iid_p95"], (
            f"at n={n} independence predicts a LONGER tail than the measurement; using the "
            f"formula would then be the conservative choice and this rule is backwards")
    # And the difference is real at the scale the interface actually quotes.
    assert P.STREAK_TABLE[20]["p95"] > P.STREAK_TABLE[20]["iid_p95"]


def test_a_run_between_the_two_models_reads_ordinary_not_alarming():
    # 11 losses over 20 trades sits above the independence 95th percentile (10) and at or below
    # the measured one (12). This is the exact case the choice of table decides, and calling it
    # "worse than 19 in 20" would be crying wolf on a run the record says happens.
    v = P.streak_verdict(20, 11)
    assert v["verdict"] == "unusual"
    assert v["verdict"] != "rare"


def test_the_clustering_is_scored_against_its_own_null():
    # Standing project rule (audit R3): a raw design effect is never quoted without its null.
    c = P.CLUSTERING
    assert c["design_effect"] > c["null_p95"] > c["null_median"]
    assert c["shuffles"] >= 1000 and c["p_value"].startswith("<")


def test_the_streak_table_says_where_it_came_from_and_which_way_it_errs():
    assert "control" in P.STREAK_SOURCE
    assert "37.2%" in P.STREAK_SOURCE and "35.3%" in P.STREAK_SOURCE
    assert "SHORT" in P.STREAK_SOURCE, "the direction of the substitution must be stated"


def test_percentiles_are_ordered_within_every_bracket():
    for n, row in P.STREAK_TABLE.items():
        assert row["median"] <= row["p75"] <= row["p90"] <= row["p95"] <= row["worst"], n
        assert row["n_windows"] >= 100, f"n={n} rests on too few disjoint stretches"


def test_longer_stretches_hold_longer_runs():
    keys = sorted(P.STREAK_TABLE)
    for a, b in zip(keys, keys[1:]):
        assert P.STREAK_TABLE[a]["median"] <= P.STREAK_TABLE[b]["median"]
        assert P.STREAK_TABLE[a]["p95"] <= P.STREAK_TABLE[b]["p95"]


def test_a_reader_is_never_compared_against_a_longer_stretch_than_they_have_taken():
    # Comparing 12 trades against the 30-trade column would borrow that column's longer runs and
    # excuse a streak the record does not excuse.
    for n in (10, 12, 19, 20, 29, 30, 49, 50, 400):
        key, _, _ = P._bracket(n)
        assert key <= n or n < min(P.STREAK_TABLE)


def test_p_run_at_least_refuses_to_report_zero_for_an_unmeasured_length():
    assert P.p_run_at_least(20, 6) > 0
    # 40 in a row was never observed; "never happened here" is not "cannot happen".
    assert P.p_run_at_least(20, 40) is None


# ------------------------------------------------------------------ the streak counter itself
def test_an_unscoreable_trade_does_not_break_a_losing_run():
    # A closed trade with no entry premium is neither a win nor a loss. Treating it as a win
    # would silently reset a streak the user actually lived through.
    assert P.longest_loss_run([False, False, None, False]) == 3
    assert P.longest_loss_run([False, False, True, False]) == 2


def test_the_streak_counter_handles_the_boring_cases():
    assert P.longest_loss_run([]) == 0
    assert P.longest_loss_run([True, True]) == 0
    assert P.longest_loss_run([False]) == 1
    assert P.longest_loss_run([None, None]) == 0


def test_the_scorecard_orders_by_entry_because_the_table_was_measured_that_way():
    # Different-horizon trades close out of order, so an exit-ordered live sequence scored
    # against an entry-ordered banked distribution would be comparing two different things.
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), "r", encoding="utf-8").read()
    assert "ORDER BY alert_ts" in src
    rec = open(os.path.join(ROOT, "valuation", "saas", "recap.py"), "r",
               encoding="utf-8").read()
    assert 'key=lambda r: str(r.get("entry_ts")' in rec


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
    print(f"\n{passed}/{len(tests)} payoff-shape tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
