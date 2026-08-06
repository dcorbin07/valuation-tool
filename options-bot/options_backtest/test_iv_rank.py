"""
O9 — IV rank as a sell-timing switch. Tests for the gate and its rank statistic.

The thing most worth pinning is that the rank is computable on the entry date
from data the trader had. A sell-timing rule that peeks one day forward would
look excellent and be worthless, and nothing about the equity curve would say so.

    python -m unittest test_iv_rank -v
"""
import unittest
from datetime import date, timedelta

import backtest_engine as be


def _days(n, start=date(2020, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


class RankIsPointInTime(unittest.TestCase):
    def test_no_signal_until_the_window_is_full(self):
        """
        Ranking against a partial window invents confident percentiles out of a
        handful of observations. Those days must return None and therefore not
        trade, rather than quietly ranking 3 observations as a percentile.
        """
        d = _days(10)
        vols = {x: 0.2 for x in d}
        r = be.iv_rank_series(d, vols, window=5)
        self.assertTrue(all(r[x] is None for x in d[:4]))
        self.assertIsNotNone(r[d[4]])

    def test_rank_ignores_the_future(self):
        """
        The decisive property. Build two series identical up to day K and wildly
        different after it; every rank on or before K must match.
        """
        d = _days(60)
        base = {x: 0.10 + 0.001 * i for i, x in enumerate(d)}
        spiked = dict(base)
        for x in d[40:]:
            spiked[x] = 5.0                      # an enormous later vol spike
        a = be.iv_rank_series(d, base, window=20)
        b = be.iv_rank_series(d, spiked, window=20)
        for x in d[:40]:
            self.assertEqual(a[x], b[x], f"rank on {x} changed because of FUTURE vol")

    def test_todays_value_counts_in_its_own_window(self):
        """On the entry date the trader knows today's vol, so the highest value
        seen so far should rank 1.0, not (n-1)/n."""
        d = _days(5)
        vols = {d[0]: 0.1, d[1]: 0.2, d[2]: 0.3, d[3]: 0.4, d[4]: 0.5}
        r = be.iv_rank_series(d, vols, window=5)
        self.assertEqual(r[d[4]], 1.0)

    def test_lowest_value_ranks_lowest(self):
        d = _days(5)
        vols = {d[0]: 0.5, d[1]: 0.4, d[2]: 0.3, d[3]: 0.2, d[4]: 0.1}
        r = be.iv_rank_series(d, vols, window=5)
        self.assertEqual(r[d[4]], 0.2)          # only itself is <= itself

    def test_window_rolls_forward(self):
        """A value extreme a year ago must stop suppressing today's rank once it
        leaves the trailing window."""
        d = _days(12)
        vols = {x: 0.1 for x in d}
        vols[d[0]] = 9.9                          # ancient spike
        r = be.iv_rank_series(d, vols, window=5)
        self.assertEqual(r[d[11]], 1.0,
                         "a spike outside the trailing window must not bind")

    def test_missing_vol_yields_no_signal(self):
        d = _days(8)
        vols = {x: 0.2 for x in d}
        del vols[d[5]]
        r = be.iv_rank_series(d, vols, window=3)
        self.assertIsNone(r[d[5]])


class GateBehaviour(unittest.TestCase):
    """
    Drives the full engine on synthetic series. The point is the GATE mechanics,
    not the P&L: with IV pinned to realized vol there is no variance risk
    premium by construction, so the strategy has no edge either way.
    """

    @staticmethod
    def _series(n=600, vol_hi=0.60, vol_lo=0.12):
        d = _days(n)
        prices, vols, rates = {}, {}, {}
        px = 100.0
        for i, x in enumerate(d):
            px *= 1.0002
            prices[x] = px
            # Vol alternates in long blocks so IV rank genuinely spans its range.
            vols[x] = vol_hi if (i // 60) % 2 == 0 else vol_lo
            rates[x] = 0.03
        return d, prices, vols, rates

    def test_gate_off_reproduces_more_trades_than_gate_on(self):
        _d, prices, vols, rates = self._series()
        off = be.OptionsBacktester(be.BacktestConfig()).run(prices, vols, rates)
        on = be.OptionsBacktester(
            be.BacktestConfig(iv_rank_min=0.667, iv_rank_window=100)
        ).run(prices, vols, rates)
        self.assertNotIn("error", off)
        self.assertNotIn("error", on)
        self.assertLess(on["stats"]["num_trades"], off["stats"]["num_trades"],
                        "the gate must actually block entries")

    def test_gate_off_reports_no_fraction_invested(self):
        _d, prices, vols, rates = self._series()
        res = be.OptionsBacktester(be.BacktestConfig()).run(prices, vols, rates)
        self.assertFalse(res["iv_rank"]["gate_applied"])
        self.assertNotIn("fraction_of_time_invested", res["iv_rank"])

    def test_fraction_invested_is_reported_and_bounded(self):
        _d, prices, vols, rates = self._series()
        res = be.OptionsBacktester(
            be.BacktestConfig(iv_rank_min=0.667, iv_rank_window=100)
        ).run(prices, vols, rates)
        f = res["iv_rank"]["fraction_of_time_invested"]
        self.assertGreaterEqual(f, 0.0)
        self.assertLessEqual(f, 1.0)

    def test_an_impossible_threshold_blocks_everything(self):
        _d, prices, vols, rates = self._series()
        res = be.OptionsBacktester(
            be.BacktestConfig(iv_rank_min=1.01, iv_rank_window=100)
        ).run(prices, vols, rates)
        self.assertEqual(res["stats"]["num_trades"], 0)
        self.assertEqual(res["iv_rank"]["fraction_of_time_invested"], 0.0)

    def test_exits_are_not_gated(self):
        """
        A sell-TIMING rule gates entries only. If exits were gated too, positions
        opened in high vol would be held through the low-vol regime because the
        rule said 'do nothing', which is a different and much worse strategy.
        Assert every trade closes rather than being stranded.
        """
        _d, prices, vols, rates = self._series()
        res = be.OptionsBacktester(
            be.BacktestConfig(iv_rank_min=0.667, iv_rank_window=100)
        ).run(prices, vols, rates)
        reasons = set(res["stats"]["exits_by_reason"])
        self.assertTrue(reasons, "no exits recorded at all")
        self.assertTrue(reasons <= {"profit", "stop", "time", "expiration"})

    def test_every_trade_carries_the_rank_it_was_opened_at(self):
        _d, prices, vols, rates = self._series()
        res = be.OptionsBacktester(
            be.BacktestConfig(iv_rank_min=0.667, iv_rank_window=100)
        ).run(prices, vols, rates)
        for t in res["trades"]:
            self.assertIsNotNone(t["entry_iv_rank"])
            self.assertGreaterEqual(t["entry_iv_rank"], 0.667,
                                    "a trade was opened below the gate threshold")


class TercileReport(unittest.TestCase):
    def test_terciles_cut_on_the_observed_distribution(self):
        """
        IV rank is not uniform on [0,1] — vol sits in the lower half of its own
        trailing range most of the time. Cutting at a fixed 1/3 and 2/3 would put
        far fewer than a third of days in the top bucket and compare groups of
        very different size.
        """
        d, prices, vols, rates = GateBehaviour._series()
        res = be.OptionsBacktester(be.BacktestConfig()).run(prices, vols, rates)
        bt = res["iv_rank"].get("by_tercile")
        self.assertIsNotNone(bt)
        counts = [bt[k]["n_trades"] for k in ("bottom", "middle", "top")]
        self.assertTrue(all(c > 0 for c in counts), f"empty tercile: {counts}")
        # The terciles cover only trades that HAD a rank. Trades opened before
        # the trailing window filled are legitimately excluded — but that gap
        # must be reported, not left for a reader to discover by failing to
        # reconcile the tercile P&L against the strategy total.
        ivr = res["iv_rank"]
        self.assertEqual(sum(counts), ivr["trades_with_a_rank"])
        self.assertEqual(ivr["trades_with_a_rank"] + ivr["trades_without_a_rank"],
                         res["stats"]["num_trades"])

    def test_the_unranked_trade_count_is_reported(self):
        d, prices, vols, rates = GateBehaviour._series()
        res = be.OptionsBacktester(be.BacktestConfig()).run(prices, vols, rates)
        self.assertGreater(res["iv_rank"]["trades_without_a_rank"], 0,
                           "with a 252-session window and a 600-day series, some "
                           "early trades must predate the first signal")


if __name__ == "__main__":
    unittest.main()
