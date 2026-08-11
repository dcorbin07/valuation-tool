"""The shape of the options payoff, and how long a losing run has to get before it is strange.

WHY THIS MODULE EXISTS
----------------------
The options book wins about a third of the time. That is not a defect, it is the strategy: most
trades lose a little and a few win big. But a product built for a 37% hit rate has to LOOK
different from one built for a 70% hit rate, and this one looked like the latter. A user who
takes six alerts and loses six times concludes the tool is broken — and reasons correctly from
the evidence they were given, because nobody told them six is an ordinary number.

Disclosure already existed: `options_confidence.DISCLAIMER` says "most trades lose". Disclosure
is not design. A sentence saying losses are common does not tell a reader whether THEIR run of
losses is common. That is a calculation, and it is the calculation this module does.

WHAT IS MEASURED, AND WHAT IS ONLY DERIVED
------------------------------------------
Every constant is transcribed from a banked result file. Nothing here re-runs a backtest, and
nothing here is an estimate dressed as a measurement.

  * `SHAPE` — the corrected 187-name book, 3,885 closed trades, 2016-01 .. 2025-10, from
    `data/options_universe/UNIVERSE_RESULTS.json` (`overall`). This is the B1-corrected book;
    the pre-correction 3,042-trade run is superseded and is not quoted anywhere here.

  * `STREAK_TABLE` — measured, not modelled, on the only per-trade SEQUENCE from the corrected
    era that is still banked: the seed-0 random-entry control (`control_rows.pkl`, 6,032
    trades). The real book's own per-trade rows were a temp file (`r2_state.pkl`) and are gone,
    so a streak table on the alert sequence itself CANNOT be computed from what is on disk.
    That substitution is stated wherever the numbers are shown, and it is conservative in a way
    worth spelling out: the control's hit rate is 37.2% against the real book's 35.3%, and a
    HIGHER hit rate means SHORTER losing runs. So this table understates the real book's
    streaks. The interface will therefore call a genuinely-ordinary run unusual slightly too
    often, and will never do the reverse — which is the direction an honest design errs in.

  * `iid_*` — DERIVED, by exact arithmetic on the measured 35.3% hit rate, assuming trades are
    independent. Carried only so the reader can see how badly independence understates the
    tail, and labelled `derived` in the payload. It is never the number used for a verdict.

THE THING THAT MAKES THIS HARDER THAN IT LOOKS: OUTCOMES CLUSTER
----------------------------------------------------------------
Losing runs are LONGER than a coin-flip model predicts, because trades opened near each other
in time share a market. Measured on the control sequence, the monthly design effect is 2.667
against a shuffled null whose p95 is 1.244 (1,000 shuffles, p < 0.001) — and runs of ten or more
losses appear 58 times against a null median of 21. This project's standing rule is that a raw
design effect is never quoted without its own null (audit R3), so it is scored here the same
way, and it clears decisively.

The consequence is the whole reason the verdict below reads off a measured table instead of the
tidy Bernoulli formula: at twenty trades, independence puts the 95th percentile of the worst
losing run at 10, and the measurement puts it at 12. Using the formula would have labelled a run
of 11 or 12 "worse than 19 in 20 stretches" when the record says it is ordinary. **The
comfortable arithmetic is the one that cries wolf.**

WHAT THIS MODULE REFUSES TO DO
------------------------------
It does not say the alerts work. It cannot, because they do not: measured against random entry
on the same names and dates, the alert's day-selection SUBTRACTS value (−5.06pp per trade,
paired sign test z −4.961, p < 1e-6, audit R2 as corrected by U1-SPLIT on 2026-08-11; the
figure read −6.65pp / z −4.903 before a corporate-action defect was repaired, and the verdict
is unchanged). A streak being normal is a statement about the
SHAPE of a convex payoff. It is not evidence of edge, and `NOT_A_CLAIM` travels with every
payload so the two cannot be read as one.

It also does not only say "this is fine". `streak_verdict` returns `unusual`, `rare` and
`beyond_record` on real inputs, and below ten closed trades it returns `too_few` rather than a
comforting number — a design that can only ever reassure would be worse than no design.
"""
from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------------------
# THE BOOK. Transcribed from data/options_universe/UNIVERSE_RESULTS.json -> "overall".
# The licensed panel is gitignored, so these are committed rather than read at runtime —
# the same reason `options_confidence` commits its bucket tables.
# ---------------------------------------------------------------------------------------
SOURCE = ("corrected 187-name options book, 3,885 closed trades, 2016-01 to 2025-10 "
          "(data/options_universe/UNIVERSE_RESULTS.json)")
N_TRADES = 3885
N_NAMES = 187
WINDOW = "2016-01 to 2025-10"

HIT_RATE = 0.35315                 # fraction of trades with pnl > 0
AVG_WIN = 1.14559                  # mean return of the winners
AVG_LOSS = -0.57273                # mean return of the losers
MEDIAN_TRADE = -0.52222            # the MIDDLE trade loses half the premium
EXPECTANCY = 0.03410               # gross of nothing further; per trade on the premium
PROFIT_FACTOR = 1.09205

P_TAIL_WIN = 0.25019               # >= +100%
P_TOTAL_LOSS = 0.01390             # <= -90%
P_STOP_OUT = 0.59640               # <= -45%, i.e. at or through the stop
TAIL_SHARE_OF_GROSS_WIN = 0.86752  # share of ALL winnings made by the >= +100% trades

#: The confidence tables are calibrated on a different, narrower book (55 names, 1,540 trades)
#: which reports 37.4%. Both are real and they measure different universes, so the honest
#: public form is the range rather than either endpoint presented as "the" hit rate. This is
#: the same house style the equity side uses for the grid-dependent long-short t.
HIT_RATE_RANGE = "35-37%"

#: WHY THE RANGE IS A MEASUREMENT AND NOT A HEDGE. The obvious worry is that 37.4% and 35.3%
#: differ because the older book was computed on the pre-B1 price basis. It is not that. The
#: corrected book splits cleanly by universe, and the megacap half reproduces the published
#: figure almost exactly:
#:
#:      54 original megacaps  n=1,532   hit 37.27%   expectancy  +9.37%
#:      132 names added       n=2,353   hit 34.04%   expectancy  -0.47%
#:      whole book            n=3,885   hit 35.32%   expectancy  +3.41%
#:
#: CORRECTED 2026-08-11 (`U1-SPLIT`): split-clean these read +9.14% / -0.56% / +3.27% on
#: n=1,528 / 2,342 / 3,870. The hit rates and the breadth story are unchanged; the constants
#: above are left as transcribed because a test pins them to the banked book they came from.
#:
#: So the two endpoints of the range mean something specific — 37% is the megacap book, 35% is
#: the broad one — and the spread is breadth, not a defect. Worth keeping written down, because
#: "our two surfaces quote different hit rates" is otherwise indistinguishable from a bug.
HIT_RATE_MEGACAP = 0.37272     # 54 original names, 1,532 trades
HIT_RATE_BROAD = 0.34042       # the 132 names added by the breadth run, 2,353 trades

# ---------------------------------------------------------------------------------------
# THE SHAPE, as five mutually exclusive buckets that sum to 1. Ordered worst to best so a
# renderer that just walks the list produces the picture in the right direction.
# ---------------------------------------------------------------------------------------
def outcome_buckets() -> list:
    """The distribution as a renderable list. Shares are derived from the banked cuts.

    The cuts are the book's own (`options_universe`: TAIL_WIN +100%, TOTAL_LOSS -90%,
    STOP_OUT -45%), not new ones invented for a chart — a chart with its own thresholds would
    be a second opinion about the same trades.
    """
    near_total = P_TOTAL_LOSS
    stopped = P_STOP_OUT - P_TOTAL_LOSS
    small_loss = (1.0 - HIT_RATE) - P_STOP_OUT
    small_win = HIT_RATE - P_TAIL_WIN
    big_win = P_TAIL_WIN
    return [
        {"key": "near_total_loss", "label": "lost almost everything", "detail": "worse than -90%",
         "share": round(near_total, 4), "sign": "loss"},
        {"key": "stopped_out", "label": "hit the stop", "detail": "-45% to -90%",
         "share": round(stopped, 4), "sign": "loss"},
        {"key": "small_loss", "label": "small loss", "detail": "0 to -45%",
         "share": round(small_loss, 4), "sign": "loss"},
        {"key": "small_win", "label": "small win", "detail": "up to +100%",
         "share": round(small_win, 4), "sign": "win"},
        {"key": "big_win", "label": "at least doubled", "detail": "+100% or better",
         "share": round(big_win, 4), "sign": "win"},
    ]


# ---------------------------------------------------------------------------------------
# STREAKS. Measured on the corrected-era control sequence; see the module docstring for why
# that is the sequence available and why the substitution errs toward alarm.
#
# `p_run_ge[k]` = share of n-trade stretches containing at least one run of k straight losses.
# Windows slide one trade at a time, so they overlap: `n_windows` records how many DISJOINT
# stretches the 6,032 trades hold, which is the honest sample size behind each column.
# ---------------------------------------------------------------------------------------
STREAK_TABLE = {
    10: {"median": 4, "p75": 5, "p90": 7, "p95": 9, "worst": 10, "n_windows": 603,
         "iid_median": 4, "iid_p90": 6, "iid_p95": 8,
         "p_run_ge": {1: 0.9995, 2: 0.9588, 3: 0.7779, 4: 0.5393, 5: 0.3583, 6: 0.2275,
                      7: 0.1446, 8: 0.0948, 9: 0.0629, 10: 0.0390}},
    20: {"median": 5, "p75": 7, "p90": 10, "p95": 12, "worst": 20, "n_windows": 301,
         "iid_median": 5, "iid_p90": 8, "iid_p95": 10,
         "p_run_ge": {1: 1.0, 2: 0.9953, 3: 0.9426, 4: 0.7781, 5: 0.5997, 6: 0.4412,
                      7: 0.3163, 8: 0.2323, 9: 0.1806, 10: 0.1355, 11: 0.0878, 12: 0.0642,
                      13: 0.0469, 14: 0.0346, 15: 0.0243, 16: 0.0153, 17: 0.0103, 18: 0.0053,
                      19: 0.0033, 20: 0.0023}},
    30: {"median": 6, "p75": 9, "p90": 12, "p95": 15, "worst": 27, "n_windows": 201,
         "iid_median": 6, "iid_p90": 10, "iid_p95": 11,
         "p_run_ge": {1: 1.0, 2: 0.9993, 3: 0.9852, 4: 0.8816, 5: 0.7388, 6: 0.5722,
                      7: 0.4376, 8: 0.3323, 9: 0.2752, 10: 0.2159, 11: 0.1456, 12: 0.1143,
                      13: 0.0880, 14: 0.0693, 15: 0.0526, 16: 0.0353, 17: 0.0270, 18: 0.0137,
                      19: 0.0083, 20: 0.0073}},
    50: {"median": 7, "p75": 10, "p90": 15, "p95": 17, "worst": 27, "n_windows": 120,
         "iid_median": 7, "iid_p90": 11, "iid_p95": 12,
         "p_run_ge": {1: 1.0, 2: 1.0, 3: 0.9992, 4: 0.9659, 5: 0.8833, 6: 0.7359,
                      7: 0.6009, 8: 0.4703, 9: 0.4153, 10: 0.3410, 11: 0.2440, 12: 0.1997,
                      13: 0.1633, 14: 0.1322, 15: 0.1045, 16: 0.0724, 17: 0.0578, 18: 0.0304,
                      19: 0.0184, 20: 0.0174}},
}

STREAK_SOURCE = ("measured on the 6,032-trade corrected-era random-entry control "
                 "(the real book's own per-trade sequence is not banked); the control hits "
                 "37.2% against the book's 35.3%, so these runs are if anything too SHORT")

#: Below this many closed trades no streak verdict is given at all. Ten is not arbitrary: it is
#: the smallest stretch the table measures, and under it the worst-run distribution is so wide
#: that every possible answer is "ordinary" — which would make the verdict decorative and, worse,
#: would hand a user three losses and a reassurance.
MIN_TRADES_FOR_VERDICT = 10

#: The clustering evidence, kept next to the table it justifies (see the module docstring).
CLUSTERING = {
    "design_effect": 2.667, "null_p95": 1.244, "null_median": 0.984, "shuffles": 1000,
    "p_value": "< 0.001",
    "runs_ge_10_observed": 58, "runs_ge_10_null_median": 21,
    "note": ("outcomes cluster in calendar time, so losing runs are LONGER than independence "
             "predicts; the verdict below therefore reads a measured table, not the formula"),
}

#: The measured R2 gap, as ONE constant, so the number a user reads and the number a test pins
#: cannot drift apart. CORRECTED 2026-08-11 (`U1-SPLIT`): it read -6.65pp until a
#: corporate-action defect was repaired -- option chains are as-traded and unadjusted for splits
#: while bars are adjusted, and the five-seed control was contaminated ~12x harder than the alert
#: book, so the artifact had been making this figure look WORSE than it is. The verdict is
#: unchanged: the alert still loses to random entry, and it still is not an edge.
R2_GAP_PP = -5.06
R2_SIGN_Z = -4.961

NOT_A_CLAIM = ("A normal-looking losing streak is a fact about the SHAPE of a convex payoff. It "
               "is not evidence the alerts work. Measured against random entry on the same "
               f"names, this book's day-selection subtracted value ({R2_GAP_PP:.2f}pp per trade, "
               "sign test p < 1e-5), so the alert is an idea generator, not a demonstrated "
               "edge.")

HEADLINE = (f"Most of these lose. The middle trade gives back {abs(MEDIAN_TRADE):.0%} of the "
            f"premium and {P_STOP_OUT:.0%} hit the stop, while {P_TAIL_WIN:.0%} at least double "
            f"- and those doubles are {TAIL_SHARE_OF_GROSS_WIN:.0%} of everything the winners "
            f"made. A run of losses is the texture of this payoff, not a fault in it.")


def _bracket(n_trades: int):
    """Which measured column applies. Returns (key, table_row, exact).

    Picks the largest measured stretch at or below the count, so a reader is always compared
    against a stretch no LONGER than the one they have actually taken — comparing 12 trades
    against the 30-trade column would borrow that column's longer runs and excuse a streak the
    record does not excuse. `exact` records whether the column matched the count exactly, so the
    sentence can say "at least" rather than implying a precision it does not have.

    THE COST OF THAT CHOICE, stated rather than hidden: it is discontinuous and it errs toward
    ALARM. A reader 19 trades in is judged against 10-trade stretches, whose runs are shorter,
    so a run of 10 reads `rare` for them and `ordinary` for the reader one trade later. That is
    the direction to err in — the failure this feature must not have is calling a genuinely bad
    run fine — and the verdict names the stretch it used, so the reader can see it happening.
    """
    keys = sorted(STREAK_TABLE)
    pick = keys[0]
    for k in keys:
        if n_trades >= k:
            pick = k
    return pick, STREAK_TABLE[pick], (n_trades == pick)


def p_run_at_least(n_trades: int, k: int) -> Optional[float]:
    """Share of measured n-trade stretches holding a losing run of at least k.

    None when k is off the measured range, rather than a zero — "never happened in this sample"
    and "cannot happen" are different statements and only one of them is true.
    """
    if k <= 0:
        return 1.0
    _, row, _ = _bracket(n_trades)
    return row["p_run_ge"].get(int(k))


def streak_verdict(n_trades: int, longest_loss_run: int) -> dict:
    """Is this losing run ordinary? Returns the verdict, the number behind it, and a sentence.

    THE RULE, stated so it can be argued with:
      * under 10 closed trades          -> `too_few`, no verdict
      * run <= the measured median      -> `ordinary`
      * run <= the measured 90th pct    -> `ordinary` (inside the usual range)
      * run <= the measured 95th pct    -> `unusual` (longer than 9 stretches in 10)
      * run <= the worst measured run   -> `rare` (longer than 19 in 20, but it has happened)
      * longer than anything measured   -> `beyond_record`

    The cuts are the distribution's own percentiles rather than round numbers, and the top two
    verdicts exist because a design that can only say "this is fine" is the failure this whole
    exercise is most likely to produce.
    """
    n = int(n_trades or 0)
    run = int(longest_loss_run or 0)
    if n < MIN_TRADES_FOR_VERDICT:
        return {"verdict": "too_few", "n_trades": n, "longest_loss_run": run,
                "compared_with": None, "share_of_stretches": None,
                "text": (f"{n} closed trade(s) is too few to say whether a losing run is "
                         f"unusual. The record only measures stretches of "
                         f"{MIN_TRADES_FOR_VERDICT} trades and up."),
                "not_a_claim": NOT_A_CLAIM}

    key, row, exact = _bracket(n)
    share = p_run_at_least(n, run)
    scale = (f"{key} trades" if exact else f"the nearest measured stretch, {key} trades")

    if run <= row["median"]:
        verdict, gloss = "ordinary", (f"the typical worst run over {key} trades is "
                                      f"{row['median']}")
    elif run <= row["p90"]:
        verdict, gloss = "ordinary", (f"still inside the usual range - 1 stretch in 10 runs "
                                      f"to {row['p90']} or worse")
    elif run <= row["p95"]:
        verdict, gloss = "unusual", (f"longer than 9 stretches in 10; the 95th percentile is "
                                     f"{row['p95']}")
    elif run <= row["worst"]:
        verdict, gloss = "rare", (f"longer than 19 stretches in 20 - it does happen, and the "
                                  f"worst in the record at this scale is {row['worst']}")
    else:
        verdict, gloss = "beyond_record", (f"longer than anything in the record, whose worst "
                                           f"at this scale is {row['worst']}")

    share_s = ("" if share is None
               else f" {share:.0%} of measured stretches contain a run this long.")
    return {
        "verdict": verdict, "n_trades": n, "longest_loss_run": run,
        "compared_with": key, "exact_scale": exact,
        "median": row["median"], "p90": row["p90"], "p95": row["p95"], "worst": row["worst"],
        "share_of_stretches": share,
        "text": (f"{run} losses in a row over {n} closed trades: {gloss}, measured against "
                 f"{scale}.{share_s}"),
        "source": STREAK_SOURCE,
        "not_a_claim": NOT_A_CLAIM,
    }


def longest_loss_run(outcomes) -> int:
    """Longest run of consecutive losses in a chronological sequence of win booleans.

    A trade with no scoreable return is neither a win nor a loss and does NOT break a run — it
    is skipped. Counting it as a win would silently reset a streak the user actually lived
    through, which is the one error this function must not make.
    """
    best = cur = 0
    for o in outcomes:
        if o is None:
            continue
        if o:
            cur = 0
        else:
            cur += 1
            best = max(best, cur)
    return best


def expectation_line(n_trades: int = 20) -> str:
    """The one sentence to show BEFORE anyone takes a trade, not after they are down."""
    _, row, _ = _bracket(n_trades)
    six = row["p_run_ge"].get(6)
    return (f"Expect losing streaks. Over {n_trades} trades the typical worst run is "
            f"{row['median']} in a row, "
            + (f"{six:.0%} of stretches contain a run of 6 or worse, " if six else "")
            + f"and the record's worst at this scale is {row['worst']}.")


def payoff_summary(n_trades_reference: int = 20) -> dict:
    """Everything a surface needs to show the distribution rather than the average."""
    _, row, _ = _bracket(n_trades_reference)
    return {
        "source": SOURCE, "n_trades": N_TRADES, "n_names": N_NAMES, "window": WINDOW,
        "hit_rate": HIT_RATE, "hit_rate_range": HIT_RATE_RANGE,
        "avg_win_pct": AVG_WIN, "avg_loss_pct": AVG_LOSS, "median_trade_pct": MEDIAN_TRADE,
        "expectancy_pct": EXPECTANCY, "profit_factor": PROFIT_FACTOR,
        "tail_share_of_gross_win": TAIL_SHARE_OF_GROSS_WIN,
        "buckets": outcome_buckets(),
        "headline": HEADLINE,
        "streaks": {
            "reference_n": n_trades_reference,
            "median": row["median"], "p90": row["p90"], "p95": row["p95"],
            "worst": row["worst"], "n_windows": row["n_windows"],
            "iid_median": row["iid_median"], "iid_p90": row["iid_p90"],
            "iid_p95": row["iid_p95"],
            "iid_note": ("derived from the hit rate assuming trades are independent; they are "
                         "not, and independence understates the tail"),
            "expectation": expectation_line(n_trades_reference),
            "source": STREAK_SOURCE,
        },
        "clustering": CLUSTERING,
        "not_a_claim": NOT_A_CLAIM,
        "basis": ("historical simulation on a licensed options panel, not an account and not a "
                  "return anyone earned"),
    }
