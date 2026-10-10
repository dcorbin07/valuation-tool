"""MC11 (figures read through) + MC10 (labels that name their construction) + MC8 (stale date).

**MC11 — THE FIGURES WERE A SECOND COPY AND THE COPY WAS WRONG.**
`settings.BOOK_CONFIGS["taxable"]["measured"]` carried the **20%-band** numbers under a label
reading *"decile + 30% no-trade band"*, and the gap was not rounding:

| field | settings carried | artifact carries |
|---|---|---|
| `after_tax_alpha` | 0.0081 | **0.021133** (2.6x understated) |
| `annual_turnover` | 1.84 | **1.3747** (the 0.30-band figure) |
| `net_alpha` | 0.0698 | 0.07752 |

The literals are gone and `settings.measured()` reads `BACKTEST_RESULTS.json book_configs.<name>`.
**An absent artifact yields NO figure rather than a stale one**, because a surface showing a
stale number cannot be told from one showing a current number.

**MC10 — "SHARPE-OPTIMAL" WAS FALSE OF THE BOOK IT LABELLED.** roth's net Sharpe is
**1.1018** and taxable's is **1.2096**, so the taxable book is the Sharpe-optimal one. roth is
the highest *net alpha* book (0.1163 vs 0.0775), which is what the label now says.

**MC8 — a `--date` older than the current trading week is refused.** The window is the trading
WEEK rather than a day count, because the honest case that must stay permitted is "Friday's row
is written on Monday after a weekend outage".

Run: python tests/test_mc10_mc11_labels.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts.track_row import _stale_date_refusal, week_start                # noqa: E402
from valuation.screener import settings as S                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACT = os.path.join(ROOT, "BACKTEST_RESULTS.json")

PASSED = FAILED = SKIPPED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def _artifact():
    with open(ARTIFACT, encoding="utf-8") as fh:
        return (json.load(fh) or {}).get("book_configs") or {}


# =======================================================================================
# MC11 — read through, and no literal left behind
# =======================================================================================
def test_every_measured_figure_matches_the_artifact_exactly():
    """Not "close": the whole point is that there is no second copy to be close to."""
    art = _artifact()
    for name in ("roth", "taxable"):
        got, want = S.measured(name), art[name]
        for f in ("net_alpha", "net_sharpe", "after_tax_alpha", "after_tax_sharpe",
                  "annual_turnover", "net_max_drawdown"):
            assert got.get(f) == want.get(f), (name, f, got.get(f), want.get(f))


def test_the_stale_literals_are_gone_from_settings():
    """The specific wrong numbers, banned by VALUE so they cannot return by copy-paste.

    READ FROM THE TOKEN STREAM, not from the text. My first cut dropped only lines STARTING
    with "#", so it fired on its own explanatory comment and on this module's docstring, both
    of which legitimately quote 0.0081 to say what it WAS. The substring-ban family again, and
    the remedy this repository documents is to strip prose before asserting about code.
    """
    import tokenize
    nums = []
    with open(S.__file__, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type == tokenize.NUMBER:
                nums.append(tok.string)
    for bad in ("0.0081", "1.84", "0.0698"):
        assert bad not in nums, (
            "the 20 percent band literal %s is still a NUMBER in settings' code" % bad)
    # NON-VACUOUS: the stream must contain numbers that legitimately remain, or the ban above
    # would be passing by seeing nothing at all.
    assert len(nums) > 5, "the token scan found almost no numbers; the ban saw nothing"


def test_an_unreadable_artifact_yields_no_figure_rather_than_a_stale_one():
    got = S.measured("roth", path=os.path.join(ROOT, "no", "such", "artifact.json"))
    assert got.get("unavailable"), got
    for f in ("net_alpha", "net_sharpe", "annual_turnover"):
        assert got.get(f) is None, (f, got.get(f))


def test_a_config_the_artifact_lacks_is_reported_rather_than_defaulted():
    got = S.measured("no_such_config")
    assert got.get("unavailable"), got
    assert got.get("net_alpha") is None


# =======================================================================================
# MC10 — the labels
# =======================================================================================
def test_the_roth_label_no_longer_claims_a_superlative_the_artifact_refutes():
    art = _artifact()
    roth_s, tax_s = art["roth"]["net_sharpe"], art["taxable"]["net_sharpe"]
    assert tax_s > roth_s, (
        "the premise has changed: roth %r is no longer below taxable %r" % (roth_s, tax_s))
    label = S.BOOK_CONFIGS["roth"]["label"]
    assert "Sharpe-optimal" not in label, (
        "roth is still labelled Sharpe-optimal while taxable's Sharpe is higher "
        "(%.4f vs %.4f)" % (tax_s, roth_s))


def test_the_taxable_label_may_keep_its_claim_because_it_is_true():
    art = _artifact()
    assert art["taxable"]["after_tax_alpha"] > art["roth"]["after_tax_alpha"], art
    assert "after-tax-optimal" in S.BOOK_CONFIGS["taxable"]["label"]


def test_every_measured_block_names_its_construction_universe_weighting_band_and_n():
    for name in ("roth", "taxable"):
        m = S.measured(name)
        assert m.get("basis"), name
        assert m.get("weighting") == "equal-weighted decile", m.get("weighting")
        # ITEM 47: DERIVED FROM THE ARTIFACT, not pinned to 2,531.
        #
        # `settings.measured()` reads both figures THROUGH from `universe` precisely so they
        # cannot disagree with the figures beside them -- that fix landed for the canonical
        # move because the function used to TYPE `n_names = 2531` next to figures it read
        # from the file, which after the move would have labelled a 9,645-name run as a
        # 2,531-name one. A test that pins the literal re-creates the defect it was fixing:
        # it would have gone red on the correct code and green on a function that had typed
        # the old number again.
        #
        # So the property is AGREEMENT with the artifact, which is what the read-through
        # guarantees and what a reader needs.
        art = json.load(io.open(os.path.join(ROOT, "BACKTEST_RESULTS.json"), encoding="utf-8"))
        uni = art.get("universe") or {}
        assert m.get("n_names") == uni.get("n_names"), (m.get("n_names"), uni.get("n_names"))
        assert m.get("n_dates") == uni.get("n_dates"), (m.get("n_dates"), uni.get("n_dates"))
        assert m.get("n_names") and m.get("n_dates"), "the universe stamp is empty"
        assert "no_trade_band" in m, name
        assert m.get("source", "").startswith("BACKTEST_RESULTS.json"), m.get("source")


def test_the_basis_says_it_is_NOT_the_served_book():
    """The figure most likely to be misread: a full-universe equal-weighted decile number
    shown beside a served, score-weighted, large-cap book."""
    assert "not the served" in S.MEASURED_BASIS.lower(), S.MEASURED_BASIS
    assert "equal-weighted" in S.MEASURED_BASIS.lower()


def test_the_after_tax_sentence_travels_wherever_taxable_is_offered():
    m = S.measured("taxable")
    sent = m.get("after_tax_sentence") or ""
    assert sent, "the taxable book offers an after-tax figure with no sentence"
    for token in ("40.8", "23.8", "FIFO"):
        assert token in sent, (token, sent)
    assert "NOT a projection" in sent, sent


def test_the_track_export_publishes_the_label_set():
    from valuation.screener import index_track as IT
    src = open(IT.__file__, encoding="utf-8").read()
    for key in ("weighting", "n_dates", "n_names", "no_trade_band", "after_tax_sentence"):
        assert '"%s"' % key in src, "the export omits %s" % key
    assert "S.MEASURED_BASIS" in src, "the basis is retyped rather than imported"


# =======================================================================================
# MC8 — the stale-date guard
# =======================================================================================
def test_a_date_before_the_current_trading_week_is_refused():
    T = dt.date(2026, 9, 30)                      # Wednesday
    assert week_start(T) == dt.date(2026, 9, 28)
    r = _stale_date_refusal("2026-09-25", today=T)
    assert r and "older than the current trading week" in r, r
    assert "--allow-stale-date" in r, "the refusal does not name the deliberate route"


def test_monday_may_still_write_fridays_row():
    """The honest case a naive "within 1 day" rule would have refused."""
    mon = dt.date(2026, 9, 28)
    assert _stale_date_refusal("2026-09-28", today=mon) == ""
    # ...and Friday 09-25 is NOT in that week, so it needs the flag — which is the point:
    # a weekend-outage backfill is a deliberate act, not a daily mark.
    assert _stale_date_refusal("2026-09-25", today=mon)


def test_a_future_date_is_refused_separately_and_says_why():
    r = _stale_date_refusal("2026-10-05", today=dt.date(2026, 9, 30))
    assert "FUTURE" in r, r


def test_a_malformed_date_is_refused_rather_than_guessed():
    r = _stale_date_refusal("not-a-date", today=dt.date(2026, 9, 30))
    assert "not an ISO date" in r, r


def test_today_is_always_allowed():
    for d in (dt.date(2026, 9, 28), dt.date(2026, 9, 30), dt.date(2026, 10, 2)):
        assert _stale_date_refusal(d.isoformat(), today=d) == "", d


def test_the_CLI_ACTUALLY_APPLIES_the_stale_date_guard():
    """THE GAP MY OTHER MC8 TESTS MISSED, found by mutation.

    They all call `_stale_date_refusal` directly, so disabling the call site inside `main()`
    left every one of them passing — the rule was tested and its APPLICATION was not. The same
    class as testing a refusal by grepping for its error text.

    Runs the real CLI in a subprocess and requires exit 2 plus the refusal on stderr. No
    network is reached, because the guard refuses BEFORE `contract_row` is called.
    """
    import subprocess
    r = subprocess.run([sys.executable, "-m", "scripts.track_row", "--date", "2020-01-02"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    assert r.returncode == 2, (r.returncode, (r.stderr or "")[-300:])
    blob = (r.stdout or "") + (r.stderr or "")
    assert "older than the current trading week" in blob, blob[-300:]
    assert "--allow-stale-date" in blob, blob[-300:]


def test_the_deliberate_backfill_route_still_gets_past_the_guard():
    """A refusal that cannot be overridden deliberately would break every legitimate
    backfill, so the flag is proved to WORK rather than merely to exist."""
    import subprocess
    r = subprocess.run([sys.executable, "-m", "scripts.track_row", "--date", "2020-01-02",
                        "--allow-stale-date"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    blob = (r.stdout or "") + (r.stderr or "")
    # It will still refuse -- 2020-01-02 predates inception -- but NOT for staleness, which is
    # the property under test: the guard let it through to the real mechanism.
    assert "older than the current trading week" not in blob, blob[-300:]


def run():
    global PASSED, FAILED
    print("MC10 / MC11 / MC8")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
