#!/usr/bin/env python3
"""Tests for `scripts/slippage_report.py` — V5, measured slippage vs modelled costs.

Its own file, so parallel lanes editing the shared suites cannot collide with it.

What is worth pinning here is not "does it add up" but the three things that make the report
honest, each of which a later edit could quietly undo:

  * the MINIMUM SAMPLE is a refusal, not a warning. Below 30 legs there must be no mean, no CI
    and no verdict anywhere in the output — an aggregate over nine fills reads as a finding to
    anyone who skims past the n beside it.
  * the SIGN CONVENTION is "positive is a cost" on both legs. A buyer paying above the mid and a
    seller receiving below it are the same event, and a flipped sign on one leg would report the
    exit book as free.
  * the ENTRY-ASK RECONSTRUCTION inverts `paper_track._place_entry` exactly. If that function's
    arithmetic changes, this must fail rather than silently measure against a wrong touch.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location(
    "slippage_report", os.path.join(ROOT, "scripts", "slippage_report.py"))
SR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SR)


def _order(**kw):
    row = {"alert_id": 1, "ticker": "AAA", "occ_symbol": "AAA260101C00100000",
           "expiry": "2026-01-01", "contracts": 1, "state": "closed",
           "entry_order_id": "e1", "entry_premium": None, "entry_ts": "2026-08-03T15:00:00",
           "target_premium": None, "stop_premium": None, "time_stop_date": None,
           "last_mark": None, "last_mark_ts": None, "last_mid": None,
           "exit_order_id": "x1", "exit_premium": None, "exit_ts": "2026-08-10T15:00:00",
           "exit_reason": "target", "note": None,
           "created_at": "2026-08-03T14:00:00", "updated_at": "2026-08-10T15:00:00"}
    row.update(kw)
    return row


class TheMinimumSampleIsARefusalNotAWarning(unittest.TestCase):
    def test_below_the_minimum_there_is_no_mean_no_ci_and_no_verdict(self):
        vals = [100.0] * (SR.MIN_N - 1)
        out = SR.summarise(vals, ["2026-W32"] * len(vals), "x", modelled=410.0)
        self.assertEqual(out["n"], SR.MIN_N - 1)
        self.assertFalse(out["quotable"])
        for forbidden in ("mean", "median", "p10", "p90", "ci90"):
            self.assertNotIn(forbidden, out, "%s must not be computed below MIN_N" % forbidden)
        self.assertEqual(out["verdict"], "INSUFFICIENT")

    def test_at_exactly_the_minimum_it_starts_quoting(self):
        vals = [100.0] * SR.MIN_N
        out = SR.summarise(vals, ["2026-W%02d" % (32 + i % 5) for i in range(SR.MIN_N)], "x",
                           modelled=410.0)
        self.assertTrue(out["quotable"])
        self.assertAlmostEqual(out["mean"], 100.0)
        self.assertIsNotNone(out["ci90"])

    def test_the_minimum_is_the_pre_registered_thirty(self):
        self.assertEqual(SR.MIN_N, 30)

    def test_an_empty_measure_is_insufficient_and_says_so(self):
        out = SR.summarise([], [], "x", modelled=410.0)
        self.assertEqual(out["n"], 0)
        self.assertEqual(out["verdict"], "INSUFFICIENT")
        self.assertIn("no filled legs", out["note"])

    def test_the_raw_values_are_shown_below_the_minimum_so_nothing_is_hidden(self):
        out = SR.summarise([1.0, 2.0, 3.0], [None, None, None], "x")
        self.assertEqual(out["values"], [1.0, 2.0, 3.0])


class PositiveIsACostOnBothLegs(unittest.TestCase):
    def test_a_seller_receiving_below_the_mid_reports_a_positive_cost(self):
        # mid 1.00, sold at 0.95 -> gave up 5% = 500 bps
        self.assertAlmostEqual(SR.half_spread_bps(1.00, 0.95, "sell"), 500.0)

    def test_a_buyer_paying_above_the_mid_reports_a_positive_cost(self):
        self.assertAlmostEqual(SR.half_spread_bps(1.00, 1.05, "buy"), 500.0)

    def test_price_improvement_is_negative_on_both_sides(self):
        self.assertLess(SR.half_spread_bps(1.00, 1.02, "sell"), 0)
        self.assertLess(SR.half_spread_bps(1.00, 0.98, "buy"), 0)

    def test_a_non_positive_mid_yields_nothing_rather_than_a_division(self):
        self.assertIsNone(SR.half_spread_bps(0.0, 0.5, "sell"))
        self.assertIsNone(SR.half_spread_bps(None, 0.5, "sell"))

    def test_an_unknown_side_is_an_error_not_a_silent_zero(self):
        with self.assertRaises(ValueError):
            SR.half_spread_bps(1.0, 1.0, "hold")

    def test_fill_versus_limit_is_positive_only_when_worse_than_the_limit(self):
        # buy limit 1.00 filled at 0.98 is price IMPROVEMENT -> negative
        self.assertAlmostEqual(SR.signed_vs_limit(0.98, 1.00, "buy"), -200.0)
        # sell limit 1.00 filled at 1.02 is improvement -> negative
        self.assertAlmostEqual(SR.signed_vs_limit(1.02, 1.00, "sell"), -200.0)


class TheEntryAskReconstructionInvertsPlaceEntryExactly(unittest.TestCase):
    def test_it_matches_the_shipped_arithmetic_at_the_shipped_default(self):
        from valuation.edge import options_tracker as OT
        ask = 2.37
        target = round(ask * (1.0 + OT.DEFAULT_TARGET_PCT), 4)   # exactly `_place_entry`
        back = SR.submit_ask_from_target(target, OT.DEFAULT_TARGET_PCT)
        self.assertAlmostEqual(back, ask, places=4)

    def test_the_scripts_default_target_matches_the_shipped_one(self):
        from valuation.edge import options_tracker as OT
        self.assertEqual(SR.DEFAULT_TARGET_PCT, OT.DEFAULT_TARGET_PCT)

    def test_a_custom_policy_target_is_read_from_the_alert_not_assumed(self):
        feats = json.dumps({"exit_policy": {"target_pct": 0.60}})
        self.assertAlmostEqual(SR.exit_policy_target_pct(feats), 0.60)
        ask = 1.25
        target = round(ask * 1.60, 4)
        self.assertAlmostEqual(SR.submit_ask_from_target(target, 0.60), ask, places=4)

    def test_unparseable_features_fall_back_to_the_default_rather_than_crashing(self):
        self.assertEqual(SR.exit_policy_target_pct("{not json"), SR.DEFAULT_TARGET_PCT)
        self.assertEqual(SR.exit_policy_target_pct(None), SR.DEFAULT_TARGET_PCT)

    def test_a_missing_target_premium_yields_nothing(self):
        # audit B5c left rows with no exit levels at all; they must not produce a fake touch
        self.assertIsNone(SR.submit_ask_from_target(None))
        self.assertIsNone(SR.submit_ask_from_target(0.0))

    def test_a_degenerate_target_pct_does_not_divide_by_zero(self):
        self.assertIsNone(SR.submit_ask_from_target(1.0, -1.0))


class TheVerdictRuleIsTheRegistersTable(unittest.TestCase):
    def test_an_interval_entirely_above_the_bar_is_costlier(self):
        self.assertEqual(SR.verdict(50, {"lo": 500.0, "hi": 600.0}, 410.0), "DIVERGENT-COSTLIER")

    def test_an_interval_entirely_below_the_bar_is_cheaper(self):
        self.assertEqual(SR.verdict(50, {"lo": 100.0, "hi": 200.0}, 410.0), "DIVERGENT-CHEAPER")

    def test_an_interval_straddling_the_bar_is_consistent(self):
        self.assertEqual(SR.verdict(50, {"lo": 300.0, "hi": 500.0}, 410.0), "CONSISTENT")

    def test_a_small_sample_overrides_any_interval(self):
        self.assertEqual(SR.verdict(29, {"lo": 900.0, "hi": 999.0}, 410.0), "INSUFFICIENT")

    def test_a_missing_interval_is_insufficient_rather_than_consistent(self):
        self.assertEqual(SR.verdict(500, None, 410.0), "INSUFFICIENT")

    def test_the_modelled_bar_is_the_pre_registered_literal(self):
        self.assertEqual(SR.MODELLED_ENTRY_HALF_SPREAD_BPS, 410.0)
        self.assertEqual(SR.MODELLED_COMMISSION_ROUND_TRIP, 1.30)


class TheBootstrapResamplesWeeksNotLegs(unittest.TestCase):
    def test_it_is_deterministic_at_the_pre_registered_seed(self):
        vals = [float(i % 7) for i in range(120)]
        blocks = ["2026-W%02d" % (i // 10) for i in range(120)]
        a = SR.clustered_bootstrap_ci(vals, blocks)
        b = SR.clustered_bootstrap_ci(vals, blocks)
        self.assertEqual(a["lo"], b["lo"])
        self.assertEqual(a["hi"], b["hi"])
        self.assertEqual(a["seed"], SR.BOOTSTRAP_SEED)
        self.assertEqual(a["draws"], SR.BOOTSTRAP_DRAWS)

    def test_clustering_widens_the_interval_when_weeks_disagree(self):
        # Same 120 values either way. Grouped: each week is internally identical, so a draw is
        # dominated by WHICH weeks came up. Scattered: every week holds a mix, so the mean
        # barely moves. Clustered inference must be the wider of the two - that is the whole
        # point of audit R3's finding that trade-level intervals were optimistically narrow.
        vals = [0.0] * 60 + [100.0] * 60
        grouped = ["2026-W%02d" % (i // 10) for i in range(120)]
        scattered = ["2026-W%02d" % (i % 12) for i in range(120)]
        g = SR.clustered_bootstrap_ci(vals, grouped)
        s = SR.clustered_bootstrap_ci(vals, scattered)
        self.assertGreater(g["hi"] - g["lo"], s["hi"] - s["lo"])

    def test_unlabelled_values_become_their_own_blocks_rather_than_one_shared_block(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        ci = SR.clustered_bootstrap_ci(vals, [None, None, None, None])
        self.assertEqual(ci["n_blocks"], 4)
        self.assertEqual(ci["n"], 4)

    def test_mismatched_lengths_are_an_error_not_a_silent_truncation(self):
        with self.assertRaises(ValueError):
            SR.clustered_bootstrap_ci([1.0, 2.0], ["a"])

    def test_the_week_key_is_the_iso_week_and_tolerates_both_timestamp_shapes(self):
        self.assertEqual(SR.week_key("2026-08-03T15:00:00"), SR.week_key("2026-08-03"))
        self.assertIsNone(SR.week_key(None))
        self.assertIsNone(SR.week_key("not a date"))


class TheHeadlineNeedsTheMidAndWillNotInventOne(unittest.TestCase):
    def test_a_row_without_last_mid_contributes_no_half_spread(self):
        rows = [_order(exit_premium=0.95, last_mark=0.95, last_mid=None)]
        legs = SR.build_legs(rows, {})
        self.assertEqual(legs["exit_half_spread"][0], [])
        # ...but it still contributes to the bounded fill-vs-touch measure
        self.assertEqual(len(legs["exit_vs_touch"][0]), 1)

    def test_a_row_with_last_mid_reports_the_half_spread_it_actually_paid(self):
        rows = [_order(exit_premium=0.95, last_mark=0.95, last_mid=1.00)]
        legs = SR.build_legs(rows, {})
        self.assertAlmostEqual(legs["exit_half_spread"][0][0], 500.0)

    def test_the_entry_half_spread_is_reported_as_not_measurable_rather_than_estimated(self):
        rep = SR.build_report(_tmp_db([]))
        self.assertIn("entry_half_spread", rep["not_measurable"])
        self.assertIn("ROUTED, NOT MADE", rep["not_measurable"]["entry_half_spread"])
        # and no measure block anywhere claims to be an ENTRY half-spread
        for k, v in rep.items():
            if isinstance(v, dict) and "label" in v:
                self.assertNotIn("entry half-spread", v["label"].lower())


class TheFunnelCountsTheCostTheBoundedMeasureCannotSee(unittest.TestCase):
    def test_a_book_that_never_fills_reports_a_fill_rate_not_a_clean_slippage_number(self):
        rows = [_order(alert_id=i, state="rejected") for i in range(5)]
        rows += [_order(alert_id=100 + i, state="closed", exit_premium=1.0, last_mid=1.0)
                 for i in range(5)]
        legs = SR.build_legs(rows, {})
        f = SR.fill_funnel(rows, legs["states"])
        self.assertEqual(f["n_rejected"], 5)
        self.assertEqual(f["n_filled"], 5)
        self.assertAlmostEqual(f["fill_rate_of_decided"], 0.5)

    def test_deferred_no_bid_rows_are_counted_from_their_note(self):
        rows = [_order(state="open", note="target deferred: no bid, and a market order is "
                                          "outside the bid-out convention (audit B5)")]
        legs = SR.build_legs(rows, {})
        self.assertEqual(SR.fill_funnel(rows, legs["states"])["n_deferred_no_bid"], 1)

    def test_an_empty_book_reports_no_fill_rate_rather_than_zero_or_one(self):
        self.assertIsNone(SR.fill_funnel([], {})["fill_rate_of_decided"])


class AlertToFillIsLabelledNotSlippage(unittest.TestCase):
    def test_the_drift_measure_says_so_in_its_own_key_and_label(self):
        rep = SR.build_report(_tmp_db([]))
        self.assertIn("m5_alert_to_fill_NOT_SLIPPAGE", rep)
        self.assertIn("NOT SLIPPAGE", rep["m5_alert_to_fill_NOT_SLIPPAGE"]["label"])

    def test_it_measures_the_fill_against_the_alert_time_ask(self):
        rows = [_order(entry_premium=1.10, target_premium=2.20)]
        alerts = {1: {"entry_premium": 1.00, "features": None, "alert_ts": "2026-08-01"}}
        legs = SR.build_legs(rows, alerts)
        self.assertAlmostEqual(legs["alert_to_fill"][0][0], 1000.0)   # paid 10% more than alert
        # and that is NOT the same quantity as the fill against its own limit
        self.assertAlmostEqual(legs["entry_vs_touch"][0][0], 0.0)


class TheSandboxCaveatAndTheEquityCategoryErrorAreAlwaysPrinted(unittest.TestCase):
    def test_every_rendering_carries_the_sandbox_caveat(self):
        rep = SR.build_report(_tmp_db([]))
        self.assertIn("delayed ~15 minutes", rep["sandbox_caveat"])
        self.assertIn("SANDBOX CAVEAT", SR.render(rep))

    def test_the_33_4bps_equity_figure_is_named_as_not_applicable(self):
        rep = SR.build_report(_tmp_db([]))
        note = rep["modelled"]["equity_33_4bps_does_not_apply"]
        self.assertIn("33.4", note)
        self.assertIn("STOCK NOTIONAL", note)
        self.assertIn("33.4", SR.render(rep))

    def test_the_bar_quoted_in_the_text_is_the_options_one_not_the_equity_one(self):
        txt = SR.render(SR.build_report(_tmp_db([])))
        self.assertIn("410.0 bps", txt)


class TheStoreIsReadOnlyAndAnAbsentTableIsNotACrash(unittest.TestCase):
    def test_a_store_without_the_paper_table_reports_absent_rather_than_raising(self):
        path = os.path.join(tempfile.mkdtemp(), "bare.db")
        sqlite3.connect(path).close()
        rep = SR.build_report(path)
        self.assertEqual(rep["schema"], "absent")
        self.assertEqual(rep["m3_exit_half_spread_HEADLINE"]["verdict"], "INSUFFICIENT")

    def test_a_missing_file_is_a_clean_error(self):
        with self.assertRaises(FileNotFoundError):
            SR.build_report(os.path.join(tempfile.mkdtemp(), "nope.db"))

    def test_reading_cannot_write_to_the_store(self):
        path = _tmp_db([_order(exit_premium=1.0, last_mid=1.0)])
        before = os.path.getmtime(path), os.path.getsize(path)
        SR.build_report(path)
        self.assertEqual((os.path.getmtime(path), os.path.getsize(path)), before)

    def test_an_end_to_end_run_against_a_real_store_renders(self):
        rows = [_order(alert_id=i, entry_premium=1.0, target_premium=2.0,
                       exit_premium=0.9, last_mark=0.9, last_mid=1.0)
                for i in range(3)]
        txt = SR.render(SR.build_report(_tmp_db(rows)))
        self.assertIn("NOT QUOTABLE (n=3 < 30)", txt)
        self.assertIn("M4  fill funnel", txt)


class TheExportPayloadIsAFirstClassSource(unittest.TestCase):
    """The only reachable source of real fills, so it is not an afterthought."""

    def test_the_committed_backup_reads_and_matches_its_own_counts(self):
        path = os.path.join(ROOT, "data_export", "paper_track_history.json")
        if not os.path.exists(path):
            self.skipTest("no committed backup in this checkout")
        raw = json.load(open(path, encoding="utf-8"))
        got = SR.read_export(path)
        self.assertEqual(len(got["orders"]), raw["counts"]["paper_orders"])
        self.assertEqual(len(got["alerts"]), raw["counts"]["option_alerts"])

    def test_a_nested_export_envelope_is_unwrapped(self):
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"ok": True, "export": {"schema_version": 1, "paper_orders": [
                {"alert_id": 7, "ticker": "ZZZ", "entry_premium": 1.0}], "option_alerts": []}}, fh)
        got = SR.read_export(path)
        self.assertEqual(len(got["orders"]), 1)
        self.assertEqual(got["orders"][0]["ticker"], "ZZZ")

    def test_the_report_runs_end_to_end_from_an_export(self):
        path = os.path.join(ROOT, "data_export", "paper_track_history.json")
        if not os.path.exists(path):
            self.skipTest("no committed backup in this checkout")
        txt = SR.render(SR.build_report(None, export_path=path))
        self.assertIn("V5 - MEASURED SLIPPAGE", txt)
        self.assertIn("SANDBOX CAVEAT", txt)


class TheTwoDiagnosticsCarryNoVerdictAndSayWhy(unittest.TestCase):
    def test_a_fill_below_its_limit_leaves_the_position_off_spec(self):
        # submitted at 4.45 -> target 8.90; filled at 3.55 -> the live target is +150.7%, not +100%
        rows = [_order(entry_premium=3.55, target_premium=8.90, stop_premium=2.225)]
        d = SR.exit_level_fidelity(rows, {})
        self.assertEqual(d["n_off_spec"], 1)
        r = d["rows"][0]
        self.assertAlmostEqual(r["realised_target_pct"], 8.90 / 3.55 - 1.0)
        self.assertAlmostEqual(r["intended_target_pct"], 1.00)
        self.assertAlmostEqual(r["realised_stop_pct"], 2.225 / 3.55 - 1.0)

    def test_a_fill_at_its_limit_is_on_spec(self):
        rows = [_order(entry_premium=16.10, target_premium=32.20, stop_premium=8.05)]
        d = SR.exit_level_fidelity(rows, {})
        self.assertEqual(d["n_off_spec"], 0)

    def test_the_diagnostics_never_claim_a_verdict(self):
        self.assertIn("NO VERDICT", SR.exit_level_fidelity([], {})["verdict"])
        self.assertIn("NO VERDICT", SR.sizing_veto_ignored([], {})["verdict"])

    def test_a_position_the_alerts_sizing_refused_is_flagged_with_its_reason(self):
        rows = [_order(alert_id=3, ticker="ETN", entry_premium=16.10)]
        alerts = {3: {"entry_premium": 16.10, "alert_ts": "2026-08-07",
                      "features": json.dumps({"sizing": {"contracts": 0, "skip": True,
                                                         "reason": "above the budget"}})}}
        d = SR.sizing_veto_ignored(rows, alerts)
        self.assertEqual(d["n_traded_against_a_skip"], 1)
        self.assertEqual(d["rows"][0]["ticker"], "ETN")
        self.assertIn("budget", d["rows"][0]["reason"])

    def test_an_alert_that_did_not_skip_is_not_flagged(self):
        rows = [_order(alert_id=1, entry_premium=1.0)]
        alerts = {1: {"entry_premium": 1.0, "alert_ts": "2026-08-07",
                      "features": json.dumps({"sizing": {"contracts": 1, "skip": False}})}}
        self.assertEqual(SR.sizing_veto_ignored(rows, alerts)["n_traded_against_a_skip"], 0)


class FillVersusLimitIsNotExecutionQualityAndTheReportSaysSo(unittest.TestCase):
    """The field that stops a -20% fill-vs-limit being credited to the execution."""

    def test_an_order_filled_the_next_session_is_flagged_as_crossing_a_day(self):
        rows = [_order(created_at="2026-08-03T21:51:47", entry_ts="2026-08-04T13:46:15.812Z")]
        d = SR.submit_to_fill(rows)
        self.assertEqual(d["n_crossing_a_calendar_day"], 1)
        self.assertFalse(d["rows"][0]["same_calendar_day"])

    def test_the_broker_utc_stamp_and_the_naive_local_stamp_both_parse(self):
        self.assertIsNotNone(SR._parse_ts("2026-08-04T13:46:15.812Z"))
        self.assertIsNotNone(SR._parse_ts("2026-08-03T21:51:47"))
        self.assertIsNone(SR._parse_ts("not a timestamp"))
        self.assertIsNone(SR._parse_ts(None))

    def test_the_explanation_names_the_after_close_schedule(self):
        what = SR.submit_to_fill([])["what"]
        self.assertIn("AFTER THE CLOSE", what)
        self.assertIn("NOT execution quality", what)

    def test_it_carries_no_verdict(self):
        self.assertIn("NO VERDICT", SR.submit_to_fill([])["verdict"])

    def test_the_rendered_report_shows_the_next_session_marker(self):
        rows = [_order(created_at="2026-08-03T21:51:47", entry_ts="2026-08-04T13:46:15.812Z",
                       entry_premium=3.55, target_premium=8.90)]
        txt = SR.render(SR.build_report(_tmp_db(rows)))
        self.assertIn("[NEXT SESSION]", txt)


class TheRawValuesArePrintedBelowTheMinimum(unittest.TestCase):
    def test_the_rendered_text_shows_them_rather_than_only_saying_not_quotable(self):
        rows = [_order(alert_id=i, entry_premium=3.55, target_premium=8.90) for i in range(3)]
        txt = SR.render(SR.build_report(_tmp_db(rows)))
        self.assertIn("NOT QUOTABLE (n=3 < 30)", txt)
        self.assertIn("raw:", txt)


def _tmp_db(rows) -> str:
    """A throwaway store carrying the real paper-track schema."""
    path = os.path.join(tempfile.mkdtemp(), "screener.db")
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE paper_option_orders (
        alert_id INTEGER PRIMARY KEY, ticker TEXT, occ_symbol TEXT, expiry TEXT,
        contracts INTEGER, state TEXT, entry_order_id TEXT, entry_premium REAL, entry_ts TEXT,
        target_premium REAL, stop_premium REAL, time_stop_date TEXT, last_mark REAL,
        last_mark_ts TEXT, last_mid REAL, exit_order_id TEXT, exit_premium REAL, exit_ts TEXT,
        exit_reason TEXT, note TEXT, created_at TEXT, updated_at TEXT)""")
    c.execute("""CREATE TABLE option_alerts (
        id INTEGER PRIMARY KEY, entry_premium REAL, features TEXT, alert_ts TEXT)""")
    for r in rows:
        cols = list(r)
        c.execute("INSERT INTO paper_option_orders (%s) VALUES (%s)"
                  % (",".join(cols), ",".join("?" * len(cols))), [r[k] for k in cols])
    c.commit()
    c.close()
    return path


if __name__ == "__main__":
    unittest.main(verbosity=2)
