"""The scream-buy TAB: that it consumes the logger and adds no second authority.

The logger itself (`valuation/edge/scream_log.py`) is the greeks lane's and is covered by
`tests/test_scream_log.py`. These tests cover the seam, which is where this lane can go wrong:

1. **No second implementation.** The tab must not define its own statuses, its own reset note,
   its own staleness rule or its own epoch boundary. The first version of this module did all
   four, and three of them were WRONG — it read the paper broker's FILL as "price bought in",
   it expressed the epoch as a date comparison, and it marked staleness in days when the
   logger marks it in minutes.
2. **The fields reach the screen** — including the ones easiest to drop: `dte_at_alert` vs
   `dte_remaining` (different quantities), and `current_premium_stale`.
3. **A reset that has not happened is not implied.** The record has never been reset and
   cannot be from a dev box. The footer must say "original", not imply an archive exists.
4. **The R2 context travels with the table.**
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import payoff, scream_track as ST  # noqa: E402
from valuation.edge import scream_log as SL  # noqa: E402

PASSED = []
FAILED = []
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAILED.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:                                            # noqa: BLE001
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


def _module_code(rel="valuation/web/scream_track.py"):
    """Source with docstrings and comments stripped.

    Needed because this module DISCUSSES at length the things it must not do — its docstring
    explains the paper-fill conflation it was rewritten to undo. A naive substring scan flags
    that explanation as the defect it documents, which would push the explanation out of the
    tree to make a check go green.
    """
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    code = re.sub(r'"""[\s\S]*?"""', " ", src)
    return re.sub(r"^\s*#.*$", " ", code, flags=re.M)


class _Store:
    """Minimal stand-in; the real store is exercised by the logger's own suite."""

    def __init__(self):
        self.path = ":memory:"


# ----------------------------------------------------------------------------------------
# 1. NO SECOND AUTHORITY
# ----------------------------------------------------------------------------------------

def test_the_tab_defines_no_statuses_of_its_own():
    code = _module_code()
    for s in ("HIT TARGET", "TIME-STOPPED", "STOPPED", "EXPIRED"):
        assert f'"{s}"' not in code, f"the tab redefines the status {s!r}"
    assert "STATUS_BY_REASON" not in code
    assert "EXIT_REASON_TO_STATUS" not in code, "the tab keeps its own exit-reason map"


def test_the_tab_computes_no_levels_and_no_staleness_of_its_own():
    code = _module_code()
    for banned in ("target_pct", "stop_pct", "STALE_", "mark_age", "_pct_from",
                   "DEFAULT_TARGET_PCT", "1.0 +", "* 2.0"):
        assert banned not in code, f"the tab recomputes {banned!r} instead of reading it"


def test_the_tab_holds_no_epoch_boundary_of_its_own():
    # THE CORRECTION THAT MATTERS MOST. The first version compared `alert_ts` to a hardcoded
    # date. The real boundary is `record_epoch`, stamped by `reset_record` — and because no
    # reset has run, a date comparison would have hidden the whole record AS THOUGH one had.
    code = _module_code()
    assert "RESET_DATE" not in code
    assert "2026-08-13" not in code, "the tab hardcodes a reset date"
    assert "< reset" not in code and ">= reset" not in code


def test_the_tab_does_not_read_the_paper_brokers_fill_as_the_entry_price():
    # `entry_premium` is the ALERT-TIME premium. `paper_option_orders.entry_premium` is the
    # broker FILL. Two different books; session 16 exists because they were conflated.
    code = _module_code()
    assert "paper_option_orders" not in code, "the tab reads the paper book's fills"
    assert "paper_orders(" not in code
    # It may still SHOW the paper book's conformance check, but only under a name that says so.
    assert "paper_level_conformance" in code


def test_the_tab_issues_no_sql_and_cannot_reset_the_record():
    code = _module_code()
    assert "execute(" not in code, "a display module must not query directly"
    assert "reset_record" not in code, "a display module must not be able to reset a record"
    for verb in ("INSERT", "UPDATE", "DELETE", "DROP"):
        assert verb not in code.upper(), f"{verb} in a read-only display module"


def test_that_scan_would_actually_catch_a_write():
    # A scan that finds nothing proves nothing unless it can find something.
    fake = 'c.execute("DELETE FROM option_alerts")'
    assert "execute(" in fake and "DELETE" in fake.upper()


# ----------------------------------------------------------------------------------------
# 2. THE SEAM — the logger's vocabulary reaches the payload
# ----------------------------------------------------------------------------------------

def test_the_payload_publishes_the_loggers_status_vocabulary_not_a_copy():
    out = ST.summary(_Store())
    assert out["statuses"] == list(SL.ALL_STATUSES), out["statuses"]
    assert len(SL.ALL_STATUSES) == 6, SL.ALL_STATUSES
    assert "CLOSED (unscoreable)" in out["statuses"]


def test_the_payload_publishes_the_loggers_live_field_names():
    out = ST.summary(_Store())
    assert out["live_fields"] == list(SL.LIVE_FIELDS), out["live_fields"]
    assert "current_premium_stale" in out["live_fields"]


def test_a_record_that_cannot_be_read_still_returns_its_footer():
    class _Boom:
        def _conn(self):
            raise RuntimeError("db gone")

    out = ST.summary(_Boom())
    assert out["unavailable"] is True, out
    assert out["rows"] == []
    assert "summary" in out and out["summary"]["reset"] is None
    assert out["context"] == payoff.NOT_A_CLAIM, "the caveat must survive a read failure"


def test_the_r2_context_is_quoted_from_the_module_that_owns_it():
    out = ST.summary(_Store())
    assert out["context"] == payoff.NOT_A_CLAIM
    assert out["context_source"] == payoff.SOURCE
    low = out["context"].lower()
    assert "random entry" in low
    assert "idea generator" in low or "not a demonstrated" in low


def test_the_tab_holds_no_second_copy_of_the_r2_number():
    assert "5.06" not in _module_code(), "the R2 gap is restated instead of quoted"


# ----------------------------------------------------------------------------------------
# 3. THE RENDERER
# ----------------------------------------------------------------------------------------

def _renderer():
    js = open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    m = re.search(r"function renderScreamTrack\([\s\S]*?\n\}", js)
    assert m, "renderScreamTrack not found"
    return m.group(0)


def test_the_four_fields_don_asked_for_are_rendered():
    body = _renderer()
    for col in ("entry_premium", "target_premium", "stop_premium", "current_premium"):
        assert col in body, f"{col} is not rendered"


def test_both_dte_quantities_are_rendered_and_not_merged():
    # The logger's contract: "dte_at_alert and dte_remaining are different quantities - do not
    # render them as one."
    body = _renderer()
    assert "dte_remaining" in body, "the remaining DTE is missing"
    assert "dte_at_alert" in body, "the alert-time DTE is missing"
    assert "DTE now" in body and "DTE at alert" in body, "the two DTEs are not labelled apart"


def test_the_stale_flag_drives_the_badge_and_is_not_short_circuited():
    # Asserting the identifier merely APPEARS is far too weak — it survives
    # `const stale = false && r.current_premium_stale`. Pin the ASSIGNMENT. (Found by mutation
    # on the previous version of this file.)
    body = _renderer()
    a = re.search(r"const stale\s*=\s*([^\n;]+)", body)
    assert a, "no `stale` assignment in the renderer"
    expr = a.group(1).strip()
    assert expr.startswith("r.current_premium_stale"), \
        f"the stale badge is not driven directly by the logger's flag: {expr!r}"
    for killer in ("false &&", "true ?", "0 &&"):
        assert killer not in expr, f"the staleness check is short-circuited: {expr!r}"


def test_the_renderer_does_not_imply_a_reset_that_has_not_happened():
    # The record has never been reset and cannot be from a dev box. The footer must say so
    # rather than printing a register note for an archive that does not exist.
    body = _renderer()
    assert "has not been reset" in body, \
        "the footer does not state the record is original when no reset has run"
    assert "n_prior_epochs" in body, "the count that makes a reset visible is not rendered"


def test_the_renderer_reads_the_footer_from_the_payload_and_not_a_constant():
    body = _renderer()
    assert "2026-08-13" not in body, "the renderer hardcodes a reset date"
    assert "d.reset" in body or "reset.note" in body


# ----------------------------------------------------------------------------------------
# 4. THE SURFACE
# ----------------------------------------------------------------------------------------

def test_the_record_is_owner_only():
    from valuation.saas import surfaces
    assert surfaces.is_owner_only("/api/scream-track"), \
        "a forward performance record naming live contracts must not be public"


def test_the_route_answers_and_carries_its_footer():
    from valuation.web.app import app
    d = app.test_client().get("/api/scream-track").get_json()
    assert d is not None
    assert "rows" in d and "summary" in d
    assert d.get("context"), "the R2 caveat is missing from the route payload"


def test_the_stale_register_document_was_removed_with_the_rewrite():
    # SCREAM_TRACK_RESET.md described a date-based epoch and a register note this lane no
    # longer owns. Leaving it would be a second, contradictory account of the same reset.
    assert not os.path.exists(os.path.join(ROOT, "SCREAM_TRACK_RESET.md")), \
        "the superseded register document is still in the tree"


if __name__ == "__main__":
    print("Scream-buy tab — a consumer of the logger, not a second one")
    for _n, _f in sorted(list(globals().items())):
        if _n.startswith("test_") and callable(_f):
            check(_n, _f)
    print(f"\n{len(PASSED)}/{len(PASSED) + len(FAILED)} scream-tab tests passed")
    if FAILED:
        for n, e in FAILED:
            print(f"  FAILED {n}: {e}")
        sys.exit(1)
