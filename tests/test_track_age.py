"""The forward track's age is the calendar's, not the recorder's — offline.

    python tests/test_track_age.py

WHAT IS AT RISK, and it is not a label.

`VALQUO_LIVE_AUDIT.md` **LA8**: every surface rendering the track's age rendered `len(series)`,
the number of rows the recorder managed to write, under the word "Days" and beside "Alpha / yr"
and "Sharpe". The track was **7 trading days old with 2 recorded rows**, and the server said
*"Live track is 2 trading days old — far too short to judge."*

The sentence is false in the flattering direction. A reader is told the RECORD IS SHORT; the
true statement is that the RECORDER IS MISSING 71% OF ITS ROWS — a different problem, with a
different owner (`PT-WRITER`, Cowork lane), and one someone might act on. The one number that
would have made the recording failure visible was being spent to say something else.

Four ways the fix could rot, one test group each:

1. **THE GAP STOPS BEING SHOWN.** Age and rows must both appear whenever they differ. A surface
   that renders the age alone is the same defect with the other number — it would say the track
   is 14 days old and never mention that 5 of those days were never written down.

2. **A CLOCK GETS REUSED FOR THE WRONG JOB.** Three exist and they answer different questions:
   rows gate, elapsed-to-last-row annualises, age displays. LA3 separated the first two; this
   separates the third. The dangerous one is the GATE: moving `MIN_LIVE_DAYS` onto age would let
   a gappy track reach the floor sooner and promote the public "backtested -> live" posture on
   the strength of days nobody recorded.

3. **A DEAD RECORDER GOES QUIET.** `elapsed_trading_days` stops at the last recorded row, so a
   recorder that died leaves it frozen — the track appears to stop ageing at the moment it
   stopped being written, which is the most flattering failure mode available. Age runs to
   today and must keep moving.

4. **CONTRACT POSTURE LEAKS INTO THE AGE CLAUSE.** The floor really is counted in recorded rows
   and the notes are the public statement of that. Those halves are pinned verbatim; only the
   age clause was allowed to change.
"""
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_track as IT          # noqa: E402
from valuation.screener import track_age as TA            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "valuation", "web")


def _read(*parts) -> str:
    with open(os.path.join(*parts), "r", encoding="utf-8") as fh:
        return fh.read()


def _trading_days_after(start: dt.date, n: int) -> list:
    """The next `n` trading days strictly after `start`, using the shipped calendar."""
    from valuation.screener.market_session import is_trading_day
    out, cur = [], start + dt.timedelta(days=1)
    while len(out) < n:
        if is_trading_day(cur):
            out.append(cur)
        cur += dt.timedelta(days=1)
    return out


def _summarize(series, inception, today):
    """`summarize` over a synthetic series, with no disk and no contract."""
    meta = {"inception_date": inception.isoformat(), "benchmark": "SPY"}
    orig = IT.load
    IT.load = lambda *a, **k: {"series": series, "meta": meta}
    try:
        return IT.summarize(contract=os.path.join(ROOT, "__no_such_contract__"), today=today)
    finally:
        IT.load = orig


def _rows(dates):
    return [{"date": d.isoformat(), "valquo": i * 0.1, "spy": i * 0.05}
            for i, d in enumerate(dates, 1)]


# --- 1. the gap is shown -----------------------------------------------------------------

def test_a_gap_shows_the_age_and_the_rows_in_the_audits_own_shape():
    d = TA.describe(14, 9)
    assert d["label"] == "day 14 · 9 recorded", d["label"]
    assert d["metric_note"] == "9 of 14 recorded", d["metric_note"]
    assert d["age"] == 14 and d["recorded"] == 9 and d["missing"] == 5
    assert d["complete"] is False


def test_the_phrase_names_the_shortfall_and_not_only_the_age():
    d = TA.describe(7, 2)
    # Both numbers, in that order: the age first because that is what the word "old" means.
    assert d["phrase"] == "7 trading days old, with only 2 of those days recorded", d["phrase"]


def test_a_complete_track_states_its_age_alone():
    d = TA.describe(14, 14)
    assert d["complete"] is True and d["missing"] == 0
    assert d["label"] == "day 14" and d["metric_note"] == ""


def test_the_complete_phrase_is_byte_identical_to_the_wording_it_replaces():
    """The gapless case must not move. This is what makes the fix safe to land.

    Reproduces the exact f-string `summarize` used before LA8. If they ever disagree, the fix
    has started re-wording tracks that had nothing wrong with them.
    """
    for n in (1, 2, 5, 60, 252):
        old = f"{n} trading day{'s' if n != 1 else ''} old"
        assert TA.describe(n, n)["phrase"] == old, (n, TA.describe(n, n)["phrase"], old)


def test_one_day_is_singular_on_every_string():
    d = TA.describe(1, 1)
    assert d["phrase"] == "1 trading day old" and d["label"] == "day 1"


def test_a_negative_gap_is_never_reported():
    """More rows than trading days means a row on a non-trading day — a data question.

    It is emphatically not a coverage claim, and reporting `missing: -4` would put a nonsense
    number on a public card.
    """
    d = TA.describe(5, 9)
    assert d["complete"] is True and d["missing"] == 0
    assert "recorded" not in d["label"], d["label"]


def test_an_unknown_age_falls_back_to_rows_without_inventing_a_gap():
    d = TA.describe(None, 3)
    assert d["age"] == 3 and d["complete"] is True and d["missing"] == 0
    assert TA.describe(0, 3)["complete"] is True


# --- 2. the three clocks stay distinct ---------------------------------------------------

def test_rows_and_the_annualisation_denominator_are_untouched():
    """LA3 regression. `days` gates, `elapsed_trading_days` annualises; LA8 adds a third."""
    inception = dt.date(2026, 1, 5)
    cal = _trading_days_after(inception, 40)
    kept = cal[::2]                                   # 20 rows, every other trading day
    out = _summarize(_rows(kept), inception, today=cal[-1])
    live = out["live"]
    assert live["days"] == len(kept) == 20
    # All three differ here, which is the point: the last ROW is trading day 39, so that is the
    # window the return accrued over, while today is day 40 and 20 days were written down.
    assert live["elapsed_trading_days"] == 39, live["elapsed_trading_days"]
    assert live["age"]["age"] == 40 and live["age"]["recorded"] == 20


def test_a_dead_recorder_keeps_ageing():
    """THE CAPABILITY THAT DID NOT EXIST. `elapsed` freezes at the last row; `age` does not.

    A recorder that stopped a month ago leaves every other field looking like a young track.
    """
    inception = dt.date(2026, 3, 2)
    cal = _trading_days_after(inception, 45)
    stopped = cal[:3]                                 # wrote 3 rows, then died
    out = _summarize(_rows(stopped), inception, today=cal[-1])
    live = out["live"]
    assert live["elapsed_trading_days"] == 3, "elapsed should stop at the last recorded row"
    assert live["age"]["age"] == 45, live["age"]["age"]
    assert live["age"]["recorded"] == 3
    assert "3 of 45 recorded" == live["age"]["metric_note"]
    # And the note must say it, not merely carry it in a field nothing renders.
    assert "45 trading days old" in out["note"] and "only 3 of those days" in out["note"], \
        out["note"]


def test_the_default_clock_is_today_and_not_the_last_recorded_row():
    """THE PRODUCTION PATH. Every other test here passes `today` explicitly and so would pass
    even if the default read the last row — which is exactly the defect, restored.

    Anchored on a series that is already historic, so the assertion strengthens with time
    rather than expiring: whenever this runs, today is well past the last recorded row.
    """
    inception = dt.date(2025, 1, 2)
    cal = _trading_days_after(inception, 4)
    meta = {"inception_date": inception.isoformat(), "benchmark": "SPY"}
    orig = IT.load
    IT.load = lambda *a, **k: {"series": _rows(cal), "meta": meta}
    try:
        out = IT.summarize(contract=os.path.join(ROOT, "__no_such_contract__"))   # no `today`
    finally:
        IT.load = orig
    live = out["live"]
    assert live["elapsed_trading_days"] == 4, live["elapsed_trading_days"]
    assert live["age"]["age"] > live["elapsed_trading_days"], \
        "age froze at the last recorded row, so a dead recorder would never show as one"
    assert live["age"]["recorded"] == 4 and live["age"]["complete"] is False


def test_the_gate_did_not_move_onto_age():
    """A gappy track must not reach the live floor early. The flattering direction, refused.

    `thin` alone cannot see this: the contract gate is independently unpassed here, so `thin`
    stays True whichever count the floor reads and the mutation hides behind it. The NOTE is
    what distinguishes them — "far too short to judge" is the branch where the floor was NOT
    reached, and it is the only observable that separates the two rules.
    """
    inception = dt.date(2025, 6, 2)
    cal = _trading_days_after(inception, IT.MIN_LIVE_DAYS + 40)
    kept = cal[:IT.MIN_LIVE_DAYS - 10]                # age well past the floor, rows short of it
    out = _summarize(_rows(kept), inception, today=cal[-1])
    assert out["live"]["age"]["age"] >= IT.MIN_LIVE_DAYS
    assert out["days"] < IT.MIN_LIVE_DAYS
    assert out["thin"] is True, "age reached the floor and promoted the track"
    assert out["headline"] == "backtested"
    assert "far too short to judge" in out["note"], \
        f"the floor is being counted in elapsed days, not recorded rows: {out['note']}"
    assert "floor, but the paper-track contract" not in out["note"]


def test_age_counts_from_inception_not_from_the_first_recorded_row():
    """Inception is day 0. A recorder that starts late does not reset the clock."""
    inception = dt.date(2026, 2, 2)
    cal = _trading_days_after(inception, 30)
    late = cal[20:]                                   # first row on trading day 21
    out = _summarize(_rows(late), inception, today=cal[-1])
    assert out["live"]["age"]["age"] == 30, out["live"]["age"]["age"]
    assert out["live"]["age"]["recorded"] == 10


# --- 3. the note ------------------------------------------------------------------------

def test_the_note_no_longer_words_the_row_count_as_an_age():
    """LA8's own case: 2 rows, a track older than that, and the old sentence's exact shape."""
    inception = dt.date(2026, 7, 30)
    cal = _trading_days_after(inception, 7)
    out = _summarize(_rows(cal[:2]), inception, today=cal[-1])
    note = out["note"]
    assert "Live track is 7 trading days old" in note, note
    assert "only 2 of those days recorded" in note, note
    assert "is 2 trading days old" not in note, "the row count is still being read as an age"


def test_the_contract_posture_sentences_are_verbatim():
    """Everything after the age clause is posture and was not this task's to reword."""
    inception = dt.date(2026, 7, 30)
    cal = _trading_days_after(inception, 7)
    thin = _summarize(_rows(cal[:2]), inception, today=cal[-1])["note"]
    assert ("It is shown for transparency, not as evidence, and the headline stays on the "
            "backtest.") in thin, thin

    cal2 = _trading_days_after(dt.date(2025, 1, 6), IT.MIN_LIVE_DAYS + 5)
    passed_floor = _summarize(_rows(cal2), dt.date(2025, 1, 6), today=cal2[-1])["note"]
    assert ("but the paper-track contract's operational gate has not been recorded as passed, "
            "so the backtest stays the headline. Elapsed time alone does not promote a live "
            "number.") in passed_floor, passed_floor


def test_the_floor_is_described_as_counting_recorded_days():
    """The floor IS rows. Saying "60-day floor" beside a corrected age re-creates the defect."""
    start = dt.date(2025, 1, 6)
    cal = _trading_days_after(start, IT.MIN_LIVE_DAYS + 5)
    note = _summarize(_rows(cal), start, today=cal[-1])["note"]
    assert f"{IT.MIN_LIVE_DAYS}-recorded-day floor" in note, note


# --- 4. the rendered surfaces -----------------------------------------------------------

def test_the_hero_passes_the_age_through_rather_than_re_deriving_it():
    src = _read(WEB, "hero.py")
    assert '"age": live.get("age")' in src, "the hero band cannot show an age it is not given"


def test_the_hero_band_renders_the_age_and_a_recorded_stat_beside_it():
    html = _read(WEB, "templates", "index.html")
    assert "hero.index.age.age" in html, "the Days stat still renders the row count"
    assert "hero.index.age.recorded" in html and "Recorded" in html, \
        "the row count is no longer shown at all, so a gap is invisible the other way"
    assert "not hero.index.age.complete" in html, "the Recorded stat must appear only on a gap"


def test_the_landing_page_states_an_age_it_can_defend():
    html = _read(WEB, "templates", "landing.html")
    assert "track.live.age.phrase" in html, html[:0] or "landing still words rows as an age"
    assert "{{ track.days }} trading day" not in html


def test_the_track_card_renders_the_age_and_adds_a_recorded_tile():
    js = _read(WEB, "static", "app.js")
    assert 'metric("Days", age ? age.age : live.days)' in js, "the Days tile still shows rows"
    assert 'metric("Recorded", age.recorded)' in js, "the gap has no second number"
    assert "age && !age.complete ?" in js, "the Recorded tile must be conditional on a gap"


def test_the_card_reads_the_age_from_the_payload_and_does_not_compute_one():
    """One authority. A second derivation in JavaScript is one edit from disagreeing."""
    js = _read(WEB, "static", "app.js")
    assert "const age = live && live.age ? live.age : null;" in js
    # No client-side calendar arithmetic snuck in beside it.
    window = js[js.index("const age = live"): js.index("const age = live") + 1200]
    for banned in ("new Date(", "Date.parse", "86400"):
        assert banned not in window, f"the card is computing its own age with {banned}"


def test_the_withheld_annualisation_sentence_names_recorded_days():
    """It withholds on ROWS. With the age now correct beside it, it must say which it counts."""
    js = _read(WEB, "static", "app.js")
    assert "RECORDED trading days" in js, "the floor's unit is ambiguous next to a real age"
    assert "recorded day${live.days === 1" in js


def test_no_surface_renders_the_bare_row_count_under_the_word_days():
    """The regression grep. `Days` next to `.days` is the defect's exact signature."""
    offenders = []
    for parts in (("templates", "index.html"), ("templates", "landing.html"),
                  ("static", "app.js")):
        src = _read(WEB, *parts)
        # Comments are prose ABOUT the defect — this file and those comments both name it.
        src = re.sub(r"/\*.*?\*/|\{#.*?#\}", " ", src, flags=re.S)
        for m in re.finditer(r"Days.{0,80}", src, re.S):
            seg = m.group(0)
            # A row count reached under an `age` guard is the documented fallback for an older
            # payload. A row count reached with no mention of age at all is the defect.
            if re.search(r"\b(live|track|hero\.index)\.days\b", seg) and "age" not in seg:
                offenders.append((parts[-1], " ".join(seg.split())[:90]))
    assert not offenders, f"row count still rendered as an age: {offenders}"


if __name__ == "__main__":
    fns = [(k, v) for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}\n      {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
