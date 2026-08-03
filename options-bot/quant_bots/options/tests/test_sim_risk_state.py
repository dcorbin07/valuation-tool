"""
Regression tests for the options SIM risk-state bug.

THE BUG: open_job() always took its risk state from the BROKER —
tradier.get_account_value() and tradier.get_positions(). In SIM the bot places
no broker orders, so get_positions() returned [] every single day, forever.
Every cap the risk manager enforces is computed from that list:

  * max_concurrent_positions   saw 0 open  -> approved a full book daily
  * max_positions_per_ticker   saw 0 open  -> re-opened the same ticker daily
  * max_total_deployed_pct     saw $0      -> never bound
  * strategy fingerprint dedup got an empty set -> did nothing

The only brake was a spread_id collision, and spread_ids embed the strikes and
expiration — both of which drift as spot moves and the 35-DTE target rolls, so
they almost never collide. The sim book therefore grew by up to
max_opens_per_run spreads per day without bound, and its equity curve did not
describe the risk-limited strategy at all.

The fix renders the sim book as Tradier-shaped position dicts and feeds THOSE
to the risk manager, so SIM and live enforce identical limits.
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from orchestrator import OrchestratorConfig, TradingMode
from orchestrator.jobs import Jobs
from portfolio.sim_portfolio import OptionsSimPortfolio, SimSpread
from risk import RiskConfig


def _occ(underlying, exp, strike):
    """OCC symbol: root + YYMMDD + P + strike*1000 zero-padded to 8."""
    return f"{underlying}{exp:%y%m%d}P{int(strike * 1000):08d}"


def _spread(underlying, short_k=100.0, contracts=1, credit_ps=100.0, exp=None):
    exp = exp or (date.today() + timedelta(days=35))
    long_k = short_k - 5.0
    return SimSpread(
        spread_id=f"{underlying}-{exp}-{short_k}-{long_k}",
        underlying=underlying, expiration=str(exp),
        short_strike=short_k, long_strike=long_k,
        contracts=contracts, credit_received_per_spread=credit_ps,
        short_put_occ=_occ(underlying, exp, short_k),
        long_put_occ=_occ(underlying, exp, long_k),
    )


def _candidate_payload(symbols):
    exp = date.today() + timedelta(days=35)
    return {"candidates": [{
        "symbol": s, "last_price": 120.0, "is_etf": False,
        "target_expiration": exp.isoformat(), "dte": 35,
        "short_put_strike": 100.0, "short_put_delta": -0.20,
        "short_put_bid": 1.40, "short_put_ask": 1.60, "short_put_mid": 1.50,
        "short_put_iv": 0.30, "short_put_open_interest": 500,
        "long_put_strike": 95.0,
        "long_put_bid": 0.45, "long_put_ask": 0.55, "long_put_mid": 0.50,
        "spread_credit_mid": 1.00, "spread_max_loss": 400.0,
        "spread_return_on_risk": 0.25, "atm_iv": 0.30,
        "next_earnings": None,
    } for s in symbols]}


def _sim_tradier():
    t = MagicMock()
    t.config.sandbox = True
    t.get_account_value.return_value = 500_000.0
    t.get_positions.return_value = []          # the broker is empty in SIM. Always.
    return t


class TestSimPositionsView(unittest.TestCase):
    def test_renders_two_legs_per_spread(self):
        sim = OptionsSimPortfolio(cash=100_000.0, starting_equity=100_000.0)
        sim.open_spread(_spread("AAPL"))
        sim.open_spread(_spread("MSFT"))
        positions = Jobs.sim_positions_view(sim)
        self.assertEqual(len(positions), 4)

    def test_legs_parse_back_to_the_right_underlying(self):
        """risk._count_open_by_ticker slices symbol[:-15] — verify that works."""
        from risk.risk import RiskManager
        sim = OptionsSimPortfolio(cash=100_000.0, starting_equity=100_000.0)
        sim.open_spread(_spread("AAPL"))
        counts = RiskManager._count_open_by_ticker(Jobs.sim_positions_view(sim))
        self.assertEqual(counts["AAPL"], 2)          # 2 legs = 1 spread

    def test_deployed_dollars_equal_true_max_loss(self):
        from risk.risk import RiskManager
        sim = OptionsSimPortfolio(cash=100_000.0, starting_equity=100_000.0)
        # $5 wide, $1.00/share credit, 3 contracts -> (500 - 100) * 3 = $1,200
        sim.open_spread(_spread("AAPL", contracts=3, credit_ps=100.0))
        deployed = RiskManager._sum_deployed_dollars(Jobs.sim_positions_view(sim))
        self.assertAlmostEqual(deployed, 1_200.0)

    def test_empty_book_renders_empty(self):
        sim = OptionsSimPortfolio(cash=100_000.0, starting_equity=100_000.0)
        self.assertEqual(Jobs.sim_positions_view(sim), [])


class TestSimOpenJobRespectsLimits(unittest.TestCase):
    def _jobs(self, root, risk_config=None):
        cfg = OrchestratorConfig(mode=TradingMode.SIM)
        return Jobs(cfg, _sim_tradier(), root, risk_config=risk_config)

    def _write_candidates(self, root, symbols):
        cache = root / "data" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / f"candidates_{date.today().isoformat()}.json"
        path.write_text(json.dumps(_candidate_payload(symbols)))

    def _seed_sim(self, root, spreads):
        sim_path = root / "data" / "sim" / "options" / "portfolio.json"
        sim_path.parent.mkdir(parents=True, exist_ok=True)
        sim = OptionsSimPortfolio(cash=500_000.0, starting_equity=500_000.0)
        for s in spreads:
            sim.open_spread(s)
        sim.save(sim_path)
        return sim_path

    def test_per_ticker_limit_binds_in_sim(self):
        """THE regression: an existing sim spread must block a second on the same name."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_candidates(root, ["AAPL"])
            sim_path = self._seed_sim(root, [_spread("AAPL", short_k=90.0)])

            res = self._jobs(root).open_job()
            self.assertTrue(res.success, res.error)

            sim = OptionsSimPortfolio.load_or_init(sim_path, initial_cash=500_000.0)
            aapl = [s for s in sim.open_spreads.values() if s.underlying == "AAPL"]
            self.assertEqual(len(aapl), 1,
                             "opened a second AAPL spread despite max_positions_per_ticker=1")

    def test_max_concurrent_limit_binds_in_sim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"TK{i}" for i in range(12)]
            self._write_candidates(root, names)
            # Seed the book right at the concurrent cap with unrelated names.
            existing = [_spread(f"EX{i}", short_k=90.0 + i) for i in range(10)]
            sim_path = self._seed_sim(root, existing)

            res = self._jobs(root, RiskConfig(max_concurrent_positions=10)).open_job()
            self.assertTrue(res.success, res.error)

            sim = OptionsSimPortfolio.load_or_init(sim_path, initial_cash=500_000.0)
            self.assertEqual(len(sim.open_spreads), 10,
                             f"book grew past the concurrent cap: {len(sim.open_spreads)}")

    def test_book_does_not_grow_without_bound_across_runs(self):
        """
        Three consecutive days on the same names, with the strike drifting as
        spot moves. The drift matters: the ONLY brake in the old code was a
        spread_id collision, and spread_id embeds the strike — so with a static
        strike the bug hides. Real strikes move every day, which is exactly
        when the book ran away.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [f"TK{i}" for i in range(12)]
            sim_path = root / "data" / "sim" / "options" / "portfolio.json"

            for day in range(3):
                payload = _candidate_payload(names)
                for c in payload["candidates"]:          # spot drifts, strikes follow
                    c["short_put_strike"] = 100.0 + day
                    c["long_put_strike"] = 95.0 + day
                cache = root / "data" / "cache"
                cache.mkdir(parents=True, exist_ok=True)
                (cache / f"candidates_{date.today().isoformat()}.json").write_text(
                    json.dumps(payload))
                self._jobs(root, RiskConfig(max_concurrent_positions=10)).open_job()

            sim = OptionsSimPortfolio.load_or_init(sim_path, initial_cash=500_000.0)
            self.assertLessEqual(
                len(sim.open_spreads), 10,
                f"sim book grew to {len(sim.open_spreads)} spreads over 3 runs "
                f"— the risk caps are not binding in SIM",
            )

    def test_sim_still_opens_when_the_book_is_empty(self):
        """Guard against 'fixing' the bug by simply never opening anything."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_candidates(root, ["AAPL", "MSFT"])
            sim_path = root / "data" / "sim" / "options" / "portfolio.json"

            res = self._jobs(root).open_job()
            self.assertTrue(res.success, res.error)

            sim = OptionsSimPortfolio.load_or_init(sim_path, initial_cash=500_000.0)
            self.assertGreater(len(sim.open_spreads), 0,
                               "SIM opened nothing at all — over-corrected")

    def test_sim_never_touches_the_broker_for_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_candidates(root, ["AAPL"])
            jobs = self._jobs(root)
            jobs.open_job()
            jobs.tradier.place_multileg_order.assert_not_called()


if __name__ == "__main__":
    unittest.main()
