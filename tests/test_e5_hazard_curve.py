# -*- coding: utf-8 -*-
"""E-5 / INV-A -- the hazard curve of flagged names. `PREREG_e5_hazard_curve.md`.

The tests that matter here are the four the register names as pins, and they are written to
FAIL against the obvious wrong implementation rather than to describe the right one:

* **C7** -- the decay null's shuffle must reproduce `crash_gate.permutation_null` EXACTLY on a
  degenerate single-quarter case, at the same seed and draw count. That is `B7` protection by
  measurement: two loops that look alike are not evidence that they are alike.
* **§0b** -- a row that crashes at k=1 and then has no further prices is an EVENT at k=1 and
  not a dropped row. Requiring the full four quarters selects on survival and deletes exactly
  the early events the hypothesis is about.
* **C1** -- the forward window starts STRICTLY after the flag date.
* **no defaults** -- every bar is keyword-only with no default, `I-3`'s design decision
  inherited for `MA5`'s reason.

The AST guards read the SYNTAX TREE and never the source text. This record's most repeated
guard defect is a banned substring firing against the CORRECT tree because prose documenting a
rule quotes what the rule forbids -- `MA49`, `MA5`, `MB15`, `MB22`/`MB23` and `SC-1` all hit
it. `scripts/e5_hazard_curve.py`'s own docstring contains the words "quantile_backtest" and
"alpha" for exactly that reason, so a text search would go red on a clean file.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
_SCRIPTS = os.path.join(REPO, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from valuation.studies import crash_gate as CG          # noqa: E402
from valuation.studies import hazard_curve as HC        # noqa: E402

_SKIPS = []
RUNNER = os.path.join(REPO, "scripts", "e5_hazard_curve.py")
REGISTER = os.path.join(REPO, "PREREG_e5_hazard_curve.md")


def _src(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _tree(path):
    return ast.parse(_src(path))


def _named(tree):
    """Every NAME and ATTRIBUTE the tree actually references. Docstrings and string literals
    are excluded by construction -- this walks nodes, not text."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _imported(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out.update((n.module or "") + "." + a.name for a in n.names)
    return out


def _synthetic(n_dates=6, n_names=200, seed=7):
    """A panel-shaped frame with a KNOWN hazard structure. Flagged names crash more, and more
    of their crashes land in quarter 1 -- so a front-loading test on it must say FRONT-LOADED
    and a broken one will not."""
    rng = np.random.default_rng(seed)
    rows = []
    for di in range(n_dates):
        d = f"20{20 + di // 4:02d}-{1 + 3 * (di % 4):02d}-15"
        for i in range(n_names):
            flagged = i < 40
            if flagged:
                p = [0.10, 0.05, 0.02, 0.01]
            else:
                p = [0.01, 0.01, 0.01, 0.01]
            ev = 0
            for k in range(1, 5):
                if rng.random() < p[k - 1]:
                    ev = k
                    break
            rows.append({"date": d, "ticker": f"T{i:04d}", "flagged": flagged,
                         "ev": ev, "obs": 4,
                         "last_price_date": "2026-07-24"})
    return pd.DataFrame(rows)


# =============================================================================================
class TestConstruction(unittest.TestCase):

    def test_a_crash_at_k1_with_no_later_prices_is_an_EVENT_not_a_dropped_row(self):
        """The register's §0b, and the single most important pin in this file.

        Requiring four quarters of forward prices would delete this row -- and rows shaped like
        it are precisely the early events the hypothesis is about, so deleting them biases the
        curve toward FLAT, against the hypothesis, silently."""
        fw = pd.DataFrame([{"date": "2020-01-15", "ticker": "DEAD", "c0": 100.0,
                            "last_price_date": "2020-05-01",
                            "r_1": -0.62, "dt_1": "2020-04-15",
                            "r_2": np.nan, "dt_2": None,
                            "r_3": np.nan, "dt_3": None,
                            "r_4": np.nan, "dt_4": None}])
        out = HC.event_and_observable(fw, crash=-0.50, k_max=4)
        self.assertEqual(int(out["ev"].iloc[0]), 1, "the k=1 crash was lost")
        self.assertEqual(int(out["obs"].iloc[0]), 1)
        at_risk, event = HC._at_risk_and_event(
            out["ev"].to_numpy(int), out["obs"].to_numpy(int), 1)
        self.assertTrue(bool(event[0]) and bool(at_risk[0]))
        # and it is NOT at risk at k=2: it already had its event
        at_risk2, event2 = HC._at_risk_and_event(
            out["ev"].to_numpy(int), out["obs"].to_numpy(int), 2)
        self.assertFalse(bool(at_risk2[0]))
        self.assertFalse(bool(event2[0]))

    def test_observability_is_a_PREFIX_not_a_maximum(self):
        """A gap in the middle of a series must not resurrect a later quarter. Taking the max
        observable k would score a name on quarter 4 while quarter 2 is missing, i.e. it would
        silently skip over the window in which the name may have crashed."""
        fw = pd.DataFrame([{"date": "2020-01-15", "ticker": "GAP", "c0": 100.0,
                            "last_price_date": "2026-07-24",
                            "r_1": -0.10, "dt_1": "2020-04-15",
                            "r_2": np.nan, "dt_2": None,
                            "r_3": -0.80, "dt_3": "2020-10-15",
                            "r_4": -0.90, "dt_4": "2021-01-15"}])
        out = HC.event_and_observable(fw, crash=-0.50, k_max=4)
        self.assertEqual(int(out["obs"].iloc[0]), 1)
        self.assertEqual(int(out["ev"].iloc[0]), 0, "a crash was read across an unobserved gap")

    def test_the_first_crossing_wins_and_later_ones_do_not_double_count(self):
        fw = pd.DataFrame([{"date": "2020-01-15", "ticker": "X", "c0": 100.0,
                            "last_price_date": "2026-07-24",
                            "r_1": -0.55, "dt_1": "a", "r_2": -0.70, "dt_2": "b",
                            "r_3": -0.80, "dt_3": "c", "r_4": -0.90, "dt_4": "d"}])
        out = HC.event_and_observable(fw, crash=-0.50, k_max=4)
        self.assertEqual(int(out["ev"].iloc[0]), 1)
        for k in (2, 3, 4):
            _, event = HC._at_risk_and_event(out["ev"].to_numpy(int),
                                             out["obs"].to_numpy(int), k)
            self.assertFalse(bool(event[0]))

    def test_the_threshold_is_inclusive_at_exactly_minus_50_percent(self):
        """`MA28`'s comparison is `<=`. A name exactly halved crashed."""
        fw = pd.DataFrame([{"date": "d", "ticker": "X", "c0": 1.0, "last_price_date": "z",
                            "r_1": -0.50, "dt_1": "a", "r_2": np.nan, "dt_2": None,
                            "r_3": np.nan, "dt_3": None, "r_4": np.nan, "dt_4": None}])
        self.assertEqual(int(HC.event_and_observable(fw, crash=-0.50, k_max=4)["ev"].iloc[0]), 1)

    def test_the_forward_window_starts_STRICTLY_after_the_flag_date(self):
        """C1. A crash printed ON the flag date must not register: the anchor is the last close
        on or before `d`, and the first forward observation is the next row."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            dates = pd.bdate_range("2020-01-01", periods=200).strftime("%Y-%m-%d")
            close = [100.0] * 200
            close[9] = 1.0                       # a collapse ON the anchor day itself
            pd.DataFrame({"date": dates, "close": close}).to_csv(
                os.path.join(td, "AAA.csv"), index=False)
            anchor = dates[9]
            fw = HC.forward_quarters(td, ["AAA"], [anchor], quarter_td=63, k_max=1)
            self.assertEqual(len(fw), 1)
            # c0 IS the collapsed close, and r_1 looks UP from it -- the collapse is in the past
            self.assertAlmostEqual(float(fw["c0"].iloc[0]), 1.0)
            self.assertGreater(float(fw["r_1"].iloc[0]), 0.0)

    def test_forward_quarters_censors_a_short_window_rather_than_dropping_the_row(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            dates = pd.bdate_range("2020-01-01", periods=100).strftime("%Y-%m-%d")
            pd.DataFrame({"date": dates, "close": [100.0] * 100}).to_csv(
                os.path.join(td, "BBB.csv"), index=False)
            fw = HC.forward_quarters(td, ["BBB"], [dates[0]], quarter_td=63, k_max=4)
            self.assertEqual(len(fw), 1, "the row was dropped instead of censored")
            self.assertTrue(np.isfinite(float(fw["r_1"].iloc[0])))
            self.assertTrue(np.isnan(float(fw["r_2"].iloc[0])))


# =============================================================================================
class TestTerminalValue(unittest.TestCase):
    """K3's repair, found PRE-ARM by the gate refusing.

    A ticker that STOPS TRADING has a terminal value; a ticker whose data merely runs out does
    not. Getting that distinction backwards in either direction is a real defect: filling an
    administrative censor is `S22`'s forbidden last-price fallback, and NOT filling a delisting
    deletes 591 panel rows carrying 16 crashes, 5 of them flagged -- survivorship selection in
    the instrument the register's own §0b was written to avoid.
    """

    def _fw(self, last, n_fwd, term, r1=np.nan, r2=np.nan):
        return pd.DataFrame([{"date": "2020-01-15", "ticker": "X", "c0": 100.0,
                              "last_price_date": last, "n_forward_rows": n_fwd,
                              "terminal_ret": term,
                              "r_1": r1, "dt_1": None, "r_2": r2, "dt_2": None}])

    def test_a_delisted_name_gets_its_terminal_value_at_the_first_unreachable_quarter(self):
        fw = self._fw("2020-03-01", n_fwd=30, term=-0.72)
        out = HC.apply_terminal_value(fw, quarter_td=63, k_max=2,
                                      global_last_price_date="2026-07-24")
        self.assertAlmostEqual(float(out["r_1"].iloc[0]), -0.72)
        self.assertTrue(np.isnan(float(out["r_2"].iloc[0])),
                        "the name is gone; it must not reappear in a later quarter")
        self.assertTrue(bool(out["terminal_filled"].iloc[0]))

    def test_it_lands_at_quarter_2_when_quarter_1_was_reachable(self):
        fw = self._fw("2020-08-01", n_fwd=80, term=-0.90, r1=-0.10)
        out = HC.apply_terminal_value(fw, quarter_td=63, k_max=2,
                                      global_last_price_date="2026-07-24")
        self.assertAlmostEqual(float(out["r_1"].iloc[0]), -0.10, msg="an observed quarter moved")
        self.assertAlmostEqual(float(out["r_2"].iloc[0]), -0.90)

    def test_an_ADMINISTRATIVE_end_is_NOT_filled(self):
        """`S22`'s rule, kept exactly where it applies: a 30-day return labelled as a 63-day one
        is a defect, and it lands systematically on the most recent dates."""
        fw = self._fw("2026-07-24", n_fwd=30, term=-0.72)
        out = HC.apply_terminal_value(fw, quarter_td=63, k_max=2,
                                      global_last_price_date="2026-07-24")
        self.assertTrue(np.isnan(float(out["r_1"].iloc[0])),
                        "end-of-data was scored as a terminal value")
        self.assertFalse(bool(out["terminal_filled"].iloc[0]))

    def test_a_terminal_loss_below_the_threshold_becomes_an_EVENT(self):
        """The whole point: 16 of the 591 rows are crashes, and 5 of those are flagged."""
        fw = self._fw("2020-03-01", n_fwd=30, term=-0.72)
        out = HC.apply_terminal_value(fw, quarter_td=63, k_max=2,
                                      global_last_price_date="2026-07-24")
        ev = HC.event_and_observable(out, crash=-0.50, k_max=2)
        self.assertEqual(int(ev["ev"].iloc[0]), 1)
        self.assertEqual(int(ev["obs"].iloc[0]), 1)

    def test_a_terminal_value_ABOVE_the_threshold_censors_rather_than_survives(self):
        """An acquisition at +23% is not a name that survived four quarters -- it left. It must
        be observable at the quarter it died and at no later one."""
        fw = self._fw("2020-03-01", n_fwd=30, term=0.23)
        ev = HC.event_and_observable(
            HC.apply_terminal_value(fw, quarter_td=63, k_max=2,
                                    global_last_price_date="2026-07-24"),
            crash=-0.50, k_max=2)
        self.assertEqual(int(ev["ev"].iloc[0]), 0)
        self.assertEqual(int(ev["obs"].iloc[0]), 1)
        at_risk2, _ = HC._at_risk_and_event(ev["ev"].to_numpy(int), ev["obs"].to_numpy(int), 2)
        self.assertFalse(bool(at_risk2[0]))

    def test_the_arguments_are_required(self):
        with self.assertRaises(TypeError):
            HC.apply_terminal_value(self._fw("2020-03-01", 30, -0.5))  # type: ignore[call-arg]
        with self.assertRaises(ValueError):
            HC.apply_terminal_value(self._fw("2020-03-01", 30, -0.5), quarter_td=None,
                                    k_max=None, global_last_price_date=None)


# =============================================================================================
class TestNoDefaults(unittest.TestCase):
    """`I-3`'s design decision, inherited: a bar with a default is a pre-registration the next
    caller never wrote. `MA5` measured that exact failure on the HLZ hurdle."""

    def test_every_bar_is_required(self):
        fw = pd.DataFrame([{"date": "d", "ticker": "X", "c0": 1.0, "last_price_date": "z",
                            "r_1": -0.9, "dt_1": "a"}])
        with self.assertRaises(TypeError):
            HC.forward_quarters("dir", [], [])                       # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            HC.event_and_observable(fw)                               # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            HC.hazard_cells(fw, flag_col="flagged", date_col="date")  # type: ignore[call-arg]
        with self.assertRaises(ValueError):
            HC.forward_quarters("dir", [], [], quarter_td=None, k_max=None)
        with self.assertRaises(ValueError):
            HC.event_and_observable(fw, crash=None, k_max=None)


# =============================================================================================
class TestStatistics(unittest.TestCase):

    def test_decay_returns_None_rather_than_infinity_on_an_empty_denominator(self):
        """A ratio with no kept events is not a large number; it is not a value. Returning inf
        would let one degenerate draw dominate a permutation percentile."""
        cells = pd.DataFrame([
            {"date": "d", "k": 1, "at_risk_flagged": 50, "at_risk_kept": 200,
             "event_flagged": 5, "event_kept": 0, "qualifies": True},
            {"date": "d", "k": 2, "at_risk_flagged": 50, "at_risk_kept": 200,
             "event_flagged": 5, "event_kept": 0, "qualifies": True},
            {"date": "d", "k": 3, "at_risk_flagged": 50, "at_risk_kept": 200,
             "event_flagged": 1, "event_kept": 2, "qualifies": True},
            {"date": "d", "k": 4, "at_risk_flagged": 50, "at_risk_kept": 200,
             "event_flagged": 1, "event_kept": 2, "qualifies": True}])
        self.assertIsNone(HC.decay_statistic(cells, front=(1, 2), back=(3, 4)))

    def test_excess_share_refuses_a_share_of_a_NEGATIVE_total(self):
        """If the flag produced no excess crashes overall, a 'share of the excess' is not a
        quantity. Reporting 0.7 there would read as front-loading."""
        cells = pd.DataFrame([
            {"date": "d", "k": k, "at_risk_flagged": 100, "at_risk_kept": 1000,
             "event_flagged": 0, "event_kept": 50, "qualifies": True} for k in range(1, 5)])
        r = HC.excess_share(cells, front=(1, 2), k_max=4)
        self.assertIsNone(r["share"])
        self.assertIn("not positive", r["reason"])

    def test_excess_share_reads_50_percent_on_a_FLAT_hazard(self):
        """The register's own arithmetic, pinned: under a flat hazard ratio on a flat risk set
        the front share is 0.50, so the 0.60 bar is not free."""
        cells = pd.DataFrame([
            {"date": "d", "k": k, "at_risk_flagged": 100, "at_risk_kept": 1000,
             "event_flagged": 3, "event_kept": 10, "qualifies": True} for k in range(1, 5)])
        self.assertAlmostEqual(HC.excess_share(cells, front=(1, 2), k_max=4)["share"], 0.50, 12)

    def test_a_front_loaded_hazard_reads_above_the_bar_and_a_flat_one_does_not(self):
        """A positive control on the leg itself: a synthetic panel built front-loaded must
        clear 0.60, and one built flat must not. Without this the bar could be unreachable and
        the register would look conservative while being vacuous."""
        front = pd.DataFrame(
            [{"date": "d", "k": 1, "at_risk_flagged": 100, "at_risk_kept": 1000,
              "event_flagged": 10, "event_kept": 10, "qualifies": True},
             {"date": "d", "k": 2, "at_risk_flagged": 100, "at_risk_kept": 1000,
              "event_flagged": 6, "event_kept": 10, "qualifies": True},
             {"date": "d", "k": 3, "at_risk_flagged": 100, "at_risk_kept": 1000,
              "event_flagged": 2, "event_kept": 10, "qualifies": True},
             {"date": "d", "k": 4, "at_risk_flagged": 100, "at_risk_kept": 1000,
              "event_flagged": 2, "event_kept": 10, "qualifies": True}])
        self.assertGreaterEqual(HC.excess_share(front, front=(1, 2), k_max=4)["share"], 0.60)
        self.assertGreater(HC.decay_statistic(front, front=(1, 2), back=(3, 4)), 0.0)

    def test_non_qualifying_cells_are_retained_and_excluded_rather_than_dropped(self):
        df = _synthetic(n_dates=2, n_names=60)
        cells = HC.hazard_cells(df, flag_col="flagged", date_col="date", k_max=4,
                                min_flagged_per_date=30, min_kept_per_date=100)
        self.assertEqual(len(cells), 8)
        self.assertFalse(cells["qualifies"].any(), "60 names cannot clear a 100-kept floor")
        self.assertIsNone(HC.decay_statistic(cells, front=(1, 2), back=(3, 4)))

    def test_an_event_that_is_not_at_risk_raises_rather_than_being_counted(self):
        with self.assertRaises(AssertionError):
            HC._at_risk_and_event(np.array([2]), np.array([1]), 2)


# =============================================================================================
class TestC7ShuffleIsI3sShuffle(unittest.TestCase):
    """C7. The decay null's permutation scheme must BE `crash_gate`'s, not merely resemble it."""

    def test_reproduces_crash_gate_permutation_null_exactly_on_one_quarter(self):
        df = _synthetic(n_dates=5, n_names=300, seed=11)
        df["_crash"] = df["ev"] == 1

        ref = CG.permutation_null(df, crash_col="_crash", flag_col="flagged", date_col="date",
                                  n_draws=40, seed=4242,
                                  min_flagged_per_date=30, min_kept_per_date=100)

        def mean_per_date_diff(cells):
            return float(cells["d"].mean())

        mine = HC.permutation_draws(df, flag_col="flagged", date_col="date", k_max=1,
                                    n_draws=40, seed=4242,
                                    min_flagged_per_date=30, min_kept_per_date=100,
                                    statfn=mean_per_date_diff)
        for key in ("p95", "p50", "max"):
            self.assertAlmostEqual(mine[key], ref[key], places=15,
                                   msg=f"{key} differs -- the shuffles are not the same scheme")
        self.assertEqual(mine["n_draws"], ref["n_draws"])

    def test_a_DIFFERENT_seed_gives_a_different_answer(self):
        """The equivalence above is worth nothing if the statistic is constant. This is the
        non-vacuity companion: `MB21`'s C1 scored a perfect 0.000e+00 by comparing nothing."""
        df = _synthetic(n_dates=5, n_names=300, seed=11)
        df["_crash"] = df["ev"] == 1

        def stat(cells):
            return float(cells["d"].mean())

        a = HC.permutation_draws(df, flag_col="flagged", date_col="date", k_max=1,
                                 n_draws=40, seed=1, min_flagged_per_date=30,
                                 min_kept_per_date=100, statfn=stat)
        b = HC.permutation_draws(df, flag_col="flagged", date_col="date", k_max=1,
                                 n_draws=40, seed=2, min_flagged_per_date=30,
                                 min_kept_per_date=100, statfn=stat)
        self.assertNotAlmostEqual(a["p95"], b["p95"], places=12)

    def test_undefined_draws_are_counted_and_never_coerced_to_zero(self):
        """Coercing would pad the null with fake draws and LOWER its percentile -- i.e. make
        the bar EASIER. `V6` caught that direction once already."""
        df = _synthetic(n_dates=4, n_names=300, seed=3)
        out = HC.permutation_draws(df, flag_col="flagged", date_col="date", k_max=4,
                                   n_draws=10, seed=9, min_flagged_per_date=30,
                                   min_kept_per_date=100, statfn=lambda c: None)
        self.assertEqual(out["n_draws"], 0)
        self.assertEqual(out["n_undefined"], 10)


# =============================================================================================
class TestCensusAndDiagnostics(unittest.TestCase):

    def test_censoring_census_separates_administrative_from_delisting(self):
        df = pd.DataFrame([
            {"flagged": True, "ev": 0, "obs": 2, "last_price_date": "2026-07-24"},
            {"flagged": True, "ev": 0, "obs": 1, "last_price_date": "2019-03-01"},
            {"flagged": False, "ev": 0, "obs": 4, "last_price_date": "2026-07-24"},
            {"flagged": False, "ev": 1, "obs": 1, "last_price_date": "2019-03-01"}])
        c = HC.censoring_census(df, flag_col="flagged", k_max=4,
                                global_last_price_date="2026-07-24")
        self.assertEqual(c["flagged"]["censored_administrative"], 1)
        self.assertEqual(c["flagged"]["censored_delisting"], 1)
        self.assertEqual(c["kept"]["censored_before_k_max"], 0,
                         "a row with an EVENT is not a censored row")

    def test_flag_persistence_counts_an_absent_name_as_not_flagged(self):
        p = pd.DataFrame([
            {"date": "2020-01-01", "ticker": "A", "flagged": True},
            {"date": "2020-01-01", "ticker": "B", "flagged": True},
            {"date": "2020-04-01", "ticker": "A", "flagged": True},
        ])
        r = HC.flag_persistence(p, flag_col="flagged", date_col="date", k_max=1)
        self.assertAlmostEqual(r["still_flagged_after_1_quarters"], 0.5)


# =============================================================================================
class TestRunnerDiscipline(unittest.TestCase):
    """AST guards. They read the tree, never the text -- the runner's own docstring names the
    things these forbid, so a substring search would go red on a clean file."""

    def test_the_arm_path_computes_no_return_based_statistic(self):
        names = _named(_tree(RUNNER))
        for banned in ("quantile_backtest", "top_decile_alpha", "long_short_tstat",
                       "run_backtest", "cpcv_validate"):
            self.assertNotIn(banned, names,
                             f"{banned} is referenced in the arm path; the verdict object is a "
                             f"crash RATE and the register makes alpha a void condition")

    def test_the_guard_is_not_vacuous(self):
        """A guard that sees nothing passes everything. This proves the extractor works on the
        very file it is pointed at, in both directions."""
        names = _named(_tree(RUNNER))
        self.assertIn("hazard_cells", names)
        self.assertIn("required_rows", names)
        banned_appear_in_source_text = "quantile_backtest" in _src(RUNNER)
        self.assertTrue(banned_appear_in_source_text,
                        "the docstring no longer mentions it, so this test no longer proves "
                        "that the AST route beats the substring route")

    def test_no_options_or_live_data_module_is_imported(self):
        imported = " ".join(sorted(_imported(_tree(RUNNER))))
        for banned in ("options_", "intraday", "thetadata", "yfinance", "tradier", "screener"):
            self.assertNotIn(banned, imported,
                             f"the arm path imports {banned}; §3 says no option chain, no tick "
                             f"cache, no live quote and no network call")

    def test_the_flag_definition_is_imported_and_never_re_implemented(self):
        """`B7`/`MA5`: one definition. The runner may call `build_flags`; it may not contain a
        second Beneish or Altman formula."""
        tree = _tree(RUNNER)
        self.assertIn("s10_accounting_veto.build_flags", _imported(tree))
        defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("beneish_m", "altman_z", "build_flags"):
            self.assertNotIn(banned, defs)

    def test_the_register_is_on_disk_and_carries_the_bars_the_runner_uses(self):
        """`SC-1`'s lesson: assert the register EXISTS rather than that a string starts with
        `PREREG_`. Two lanes once named the same unbuilt file differently."""
        self.assertTrue(os.path.isfile(REGISTER))
        txt = _src(REGISTER)
        for bar in ("-0.50", "63", "2.0", "0.60", "30", "100"):
            self.assertIn(bar, txt)
        self.assertIn("dd6fe93", _src(RUNNER))

    def test_the_runner_constants_match_the_register(self):
        import importlib
        mod = importlib.import_module("e5_hazard_curve")
        self.assertEqual(mod.CRASH, -0.50)
        self.assertEqual(mod.QUARTER_TD, 63)
        self.assertEqual(mod.K_MAX, 4)
        self.assertEqual(mod.RATIO_FLOOR_Q1, 2.0)
        self.assertEqual(mod.FRONT_SHARE_FLOOR, 0.60)
        self.assertEqual(mod.MIN_FLAGGED_PER_DATE, 30)
        self.assertEqual(mod.MIN_KEPT_PER_DATE, 100)
        self.assertEqual((mod.FRONT, mod.BACK), ((1, 2), (3, 4)))

    def test_the_arms_pass_refuses_without_a_passing_controls_artifact(self):
        """The two-pass separation, exercised rather than asserted. Session 26's process defect
        was computing a gating control and the outcomes it gates in one pass."""
        import importlib
        import tempfile
        mod = importlib.import_module("e5_hazard_curve")
        with tempfile.TemporaryDirectory() as td:
            saved = mod.CTRL_JSON
            try:
                args = type("A", (), {"panel": "x", "data_dir": td, "out_dir": td})()
                mod.CTRL_JSON = "absent.json"
                self.assertEqual(mod.run_arms(args), 2, "a MISSING controls file must refuse")
                mod.CTRL_JSON = "failing.json"
                with io.open(os.path.join(td, "failing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": false}')
                self.assertEqual(mod.run_arms(args), 2, "a FAILING controls file must refuse")
                # and the refusal is NOT unconditional -- MB15's proof obligation. A PASSING
                # file gets past the gate and then dies on the absent panel, which is a
                # different failure entirely. Without this the gate could be `return 2`.
                mod.CTRL_JSON = "passing.json"
                with io.open(os.path.join(td, "passing.json"), "w", encoding="utf-8") as fh:
                    fh.write('{"all_gating_pass": true}')
                with self.assertRaises(Exception):
                    mod.run_arms(args)
            finally:
                mod.CTRL_JSON = saved


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
