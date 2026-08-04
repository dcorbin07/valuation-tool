#!/usr/bin/env python3
"""
preflight.py — refuse to deploy code that is missing pieces or missing fixes.

C6. Three correctness fixes (FIXES.md) sat in this repository, fixed and
undeployed, for long enough that the audit called out the state itself as the
problem: "fixed in repo, not deployed" decays, because it is forgotten and then
someone assumes the deployed system has the fix.

This script exists so that state cannot recur silently. It answers two questions
the deploy previously could not:

  1. CAN this tree even run?  `deploy.sh` ran the two test suites and treated a
     failure as fatal — correctly — but the failure it hit was 14 identical
     `ModuleNotFoundError: No module named 'data'` errors, which reads like a
     broken test environment rather than what it is: the `data` source package
     is not in the repository, because the repo-root .gitignore's blanket
     `data/` rule excludes it at every depth. A deploy that aborts for a reason
     nobody can decode is a deploy that stops happening.

  2. ARE the fixes actually here?  FIXES.md says "Test counts changed. If you
     see the old numbers after a deploy, the old code is still there." That is a
     PROXY, and deploy.sh's copy of the expected numbers (106 / 181) had gone
     stale by two generations, so the proxy could not have fired. This checks
     for the fixes themselves — the specific symbols and behaviours each one
     introduced — instead of counting tests.

Exit code 0 = safe to deploy. Non-zero = stop, with a named reason.

    python3 deploy/preflight.py            # from the quant_bots root
    python3 deploy/preflight.py --quiet
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Packages every bot needs at import time. `data` is here because its absence is
# the failure this file was written for.
REQUIRED_PACKAGES = [
    ("core", "shared broker/sim/universe layer"),
    ("trend", "trend bot"),
    ("momentum", "momentum bot"),
    ("reversion", "reversion bot"),
]

# Same, but resolved with options/ on the path — the options bot is a separate
# package root and imports `data` as a top-level name.
OPTIONS_PACKAGES = [
    ("data", "options bot's universe + earnings calendar package"),
    ("risk", "options risk manager"),
    ("strategy", "options spread builder"),
    ("portfolio", "options portfolio manager"),
    ("screener", "options screener"),
]


def _fail(msg, hint=""):
    print(f"  FAIL  {msg}")
    if hint:
        for line in hint.strip().splitlines():
            print(f"        {line}")
    return False


def _ok(msg):
    print(f"  ok    {msg}")
    return True


# ---------------------------------------------------------------------------
#  1. Importability
# ---------------------------------------------------------------------------

def check_imports():
    good = True
    for name, what in REQUIRED_PACKAGES:
        try:
            importlib.import_module(name)
            _ok(f"import {name} ({what})")
        except Exception as e:
            good = _fail(f"import {name} ({what}): {e}") and good

    opt = ROOT / "options"
    sys.path.insert(0, str(opt))
    for name, what in OPTIONS_PACKAGES:
        try:
            importlib.import_module(name)
            _ok(f"import {name} ({what})")
        except Exception as e:
            hint = ""
            if name == "data":
                hint = (
                    "The `data` package is NOT tracked in git. The repo-root\n"
                    ".gitignore has a bare `data/` rule, which matches at every\n"
                    "depth and excluded options-bot/quant_bots/data/ wholesale.\n"
                    "quant_bots/.gitignore now re-includes it (`!data/`), but the\n"
                    "SOURCE FILES still have to be committed once, from a machine\n"
                    "that has them — the Oracle box does, since the bots run there:\n"
                    "    scp -r ubuntu@BOX:~/quant_bots/data/*.py quant_bots/data/\n"
                    "    git add quant_bots/data && git commit\n"
                    "Until then this repository cannot deploy the options bot."
                )
            good = _fail(f"import {name} ({what}): {e}", hint) and good
    return good


# ---------------------------------------------------------------------------
#  2. The three FIXES.md fixes, checked directly
# ---------------------------------------------------------------------------

def check_fix_1_exit_orders():
    """
    FIXES.md #1 — exit orders silently dropped in SIM.

    A position that fell out of the top/bottom-N had no price in the selection's
    price map, so `apply_orders_to_sim` skipped its exit order at debug level and
    `total_equity` marked it at cost forever. The fix gives RankedSelection an
    `all_prices` map covering EVERY scored name, adds `resolve_prices` to backfill
    what is still held but no longer scored, and makes the backtester mark from
    that union.
    """
    try:
        from core.sim_execution import resolve_prices              # noqa: F401
        from momentum.signals import RankedSelection as MomSel
        from reversion.signals import RankedSelection as RevSel
    except Exception as e:
        return _fail(f"fix 1 (exit orders): {e}")
    for cls, who in ((MomSel, "momentum"), (RevSel, "reversion")):
        if "all_prices" not in getattr(cls, "__dataclass_fields__", {}):
            return _fail(f"fix 1 (exit orders): {who}.RankedSelection has no "
                         f"`all_prices` — the selection-only price map is back")
    src = (ROOT / "core" / "backtest.py").read_text(encoding="utf-8", errors="ignore")
    if "mark_prices" not in src:
        return _fail("fix 1 (exit orders): core/backtest.py does not mark from "
                     "mark_prices — it is back on the selection-only map")
    return _ok("fix 1 — exit orders are priced from the full map (all_prices + "
               "resolve_prices + mark_prices)")


def check_fix_2_reversion_sign():
    """
    FIXES.md #2 — mean reversion shorted OVERSOLD names in a selloff.

    `rank_and_select` filtered on |z| and then sliced the top and bottom of one
    ranked pool, so on a day when every name had z < 0 the "bottom" was the least
    oversold name — still oversold. Behavioural check, not a source grep: feed it
    a cross-section where everything is oversold and assert it shorts nothing.
    """
    try:
        from reversion.signals import (MeanReversionConfig, ReversionScore,
                                       rank_and_select)
    except Exception as e:
        return _fail(f"fix 2 (reversion sign): {e}")
    cfg = MeanReversionConfig()
    scores = {}
    for i in range(40):
        z = -1.2 - i * 0.025           # every name oversold; none overbought
        scores[f"T{i:02d}"] = ReversionScore(
            symbol=f"T{i:02d}", zscore=z, score=-z, annualized_vol=0.30,
            last_price=50.0, bars_used=400, usable=True, note="")
    sel = rank_and_select(scores, cfg)
    if sel.shorts:
        return _fail(f"fix 2 (reversion sign): shorted {len(sel.shorts)} name(s) "
                     f"in an all-oversold cross-section — the bug is back")
    if not sel.longs:
        return _fail("fix 2 (reversion sign): selected no longs from 40 oversold "
                     "names — something else is wrong")
    return _ok(f"fix 2 — all-oversold cross-section yields {len(sel.longs)} longs, "
               f"0 shorts")


def check_fix_3_sim_risk_caps():
    """
    FIXES.md #3 — every options risk cap was inert in SIM.

    `open_job` always read positions from the broker, and in SIM the bot places
    no broker orders, so `get_positions()` returned [] forever: max-concurrent,
    max-per-ticker, max-deployed and the fingerprint dedup all saw an empty book
    and approved everything, daily. The fix renders the sim book as
    Tradier-shaped position dicts via `Jobs.sim_positions_view()`.
    """
    sys.path.insert(0, str(ROOT / "options"))
    try:
        from orchestrator.jobs import Jobs
    except Exception as e:
        return _fail(f"fix 3 (sim risk caps): {e}")
    if not hasattr(Jobs, "sim_positions_view"):
        return _fail("fix 3 (sim risk caps): Jobs.sim_positions_view is gone — "
                     "the risk manager is being fed the broker's empty SIM book")
    return _ok("fix 3 — Jobs.sim_positions_view present (risk caps see the sim book)")


FIX_CHECKS = (check_fix_1_exit_orders, check_fix_2_reversion_sign,
              check_fix_3_sim_risk_caps)


def main():
    ap = argparse.ArgumentParser(description="Pre-deploy sanity checks.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    print("== preflight: can this tree run? ==")
    imports_ok = check_imports()

    print("== preflight: are the FIXES.md fixes present? ==")
    fixes_ok = all([c() for c in FIX_CHECKS])   # list(), not all-with-generator:
                                                # every check must RUN and report,
                                                # not short-circuit on the first.

    print()
    if imports_ok and fixes_ok:
        print("PREFLIGHT OK — safe to deploy.")
        return 0
    print("PREFLIGHT FAILED — do not deploy. Nothing has been restarted.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
