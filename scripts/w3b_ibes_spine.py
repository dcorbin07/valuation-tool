"""W-3b -- IBES actuals into the earnings-date spine. EXECUTOR run of the scout's draft.

ZERO TRIALS, FIXED/instrument class. No hypothesis, no bar on any outcome, no verdict about
returns; the V1 agreement gate is an INSTRUMENT validation, and `MB1-SEL`'s rule is that a
control can only ever BLOCK, never produce, so it adds no degree of freedom to any published
claim. Precedent: `I-4` (0), `I-2`/`I-3` (0), `MB15` (0).

    python -m scripts.w3b_ibes_spine            # V2 coverage + V1 agreement + V3 reproduction
    python -m scripts.w3b_ibes_spine --json X   # artifact path

RUN ORDER IS THE `MB15` ONE: the instrument is validated BEFORE any consumer reads it, and the
coverage repair is measured against the SAME 186-name book the existing census used, so the
before/after is of one object rather than two.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import event_spine as ES                            # noqa: E402
from valuation.edge import ibes_events as IE                            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIMARY = r"C:\Users\donni\Downloads\valuation-tool"
BANKED_CENSUS = os.path.join(PRIMARY, "data", "free_analysis", "I4_EVENT_SPINE.json")
OUT = os.path.join(PRIMARY, "data", "free_analysis", "W3B_IBES_SPINE.json")

#: Agreement tolerance, in CALENDAR days, fixed by the draft's V1 ("within +/-1 session").
#: One session is at most 3 calendar days across a weekend, so the tolerance is stated in
#: calendar days and the looser reading is used -- a stricter one would manufacture
#: disagreements out of Fridays.
AGREE_DAYS = 3

#: V1's bar, quoted from the draft: ">= 95% of pairs agree within +/-1 session".
AGREE_BAR = 0.95


#: The last CRSP name interval is extended to this, because CRSP on this account is CUT AT
#: 2024-12-31 while our names are still trading and IBES still announces. Left unextended, every
#: 2025-2026 announcement falls outside every interval and is silently dropped -- the vendor's
#: cut-off masquerading as a coverage gap.
OPEN_END = "9999-12-31"


def _crsp_intervals(tickers):
    """ticker -> [(cusip8, from, to), ...] from CRSP's DATED name history.

    TWO SCOPING ERRORS ARE POSSIBLE AND THIS AVOIDS BOTH, HAVING COMMITTED EACH IN TURN:

    * Taking EVERY cusip a ticker ever carried re-imports ticker reuse through a second door --
      it returned MORE rows for TTE, SONY and BHP than the naive `oftic` route did, and the extra
      rows were other companies.
    * Taking only the CURRENT cusip truncates the history of a name whose cusip changed while the
      company continued -- reincorporations, holding-company reorganisations, spin-offs.
      Measured, that error is large and CONCENTRATED: it left HWM unmatched on 82.9% of its
      code-22 dates, STX 79.8%, MRVL 80.6%, GE 79.3%, which is what a per-NAME identifier failure
      looks like rather than a per-DATE one.

    The interval is the fix, because reuse and continuation are the same fact seen from two
    sides: a cusip is this ticker's identity **during a stated window**, and an announcement is
    ours if it falls inside the window of one of our cusips.
    """
    from valuation.edge import wrds_client as W
    db = W.connect()
    sn = db.raw_sql("select ticker, ncusip, cusip, namedt, nameenddt, comnam "
                    "from crsp.stocknames where ticker is not null")
    sn["ticker"] = sn["ticker"].astype(str).str.upper().str.strip()
    want = {str(t).upper() for t in tickers}
    sn = sn[sn["ticker"].isin(want)].copy()
    sn["c8"] = (sn["ncusip"].fillna(sn["cusip"]).astype(str).str[:8].str.upper())
    sn = sn[sn["c8"].str.len() == 8]
    iv, comnam = {}, {}
    for t, g in sn.groupby("ticker"):
        g = g.sort_values("namedt")
        rows = [(str(r.c8), str(r.namedt)[:10], str(r.nameenddt)[:10])
                for r in g.itertuples()]
        # merge adjacent rows carrying the same cusip so the intervals are per IDENTITY rather
        # than per CRSP name-change row (CRSP splits on any name/exchange edit).
        merged = []
        for c, a, b in rows:
            if merged and merged[-1][0] == c:
                merged[-1] = (c, merged[-1][1], max(merged[-1][2], b))
            else:
                merged.append((c, a, b))
        if merged:
            merged[-1] = (merged[-1][0], merged[-1][1], OPEN_END)
        iv[t] = merged
        comnam[t] = str(g.iloc[-1]["comnam"])
    return iv, comnam


def run(json_path: str = "") -> dict:
    banked = json.load(open(BANKED_CENSUS, encoding="utf-8"))
    names = sorted(banked["census"]["per_name_year"].keys())
    zero = sorted(banked["census"]["fail_closed_names"])
    print(f"[w3b] spine book: {len(names)} names, {len(zero)} FAIL_CLOSED")

    # THE EVENTS FILE IS RESOLVED FROM THE PRIMARY ROOT, NOT FROM THIS MODULE'S PARENT.
    # `event_spine.DEFAULT_EVENTS_CSV` walks up from the module, which inside a git worktree
    # lands on an EMPTY `data/bulk/`. The build then succeeds, returns zero dates for all 186
    # names, and every one reads FAIL_CLOSED -- a clean, plausible "coverage is nil" that would
    # have made the repair look like it recovered all 29 from nothing. `DEEPITM-FIN`'s
    # existence-is-not-population defect, and the assertion below is what caught it.
    events_csv = os.path.join(PRIMARY, "data", "bulk", "events.csv")
    if not os.path.exists(events_csv):
        raise FileNotFoundError(f"{events_csv} absent -- refusing to build a spine from nothing")
    base = ES.EventSpine.build(names=names, csv_path=events_csv)
    base_states = collections.Counter(base.coverage(t) for t in names)
    print(f"[w3b] rebuilt code-22 spine: {dict(base_states)}")
    assert sorted(base.zero_coverage) == zero or set(base.zero_coverage) == set(zero), (
        "the rebuilt code-22 spine does not reproduce the banked FAIL_CLOSED set; "
        "the before/after would be measured on two different objects")

    iv, comnam = _crsp_intervals(names)
    n_iv = sum(len(v) for v in iv.values())
    print(f"[w3b] CRSP resolves {len(iv)} of {len(names)} names to "
          f"{n_iv} dated cusip intervals")

    df = IE.load_announcements()
    print(f"[w3b] IBES EPS announcement rows: {len(df):,}")

    ibes = IE.dates_by_intervals(df, iv)
    print(f"[w3b] IBES supplies dates for {len(ibes)} of {len(names)} names")

    # ---------------------------------------------------------------- V2: the coverage repair
    #
    # THE REGISTERED PRECEDENCE RULE AND THE REGISTERED V3 ARE MUTUALLY INCONSISTENT, MEASURED.
    # The draft's section 2 fixes "IBES `anndats` where present; Sharadar code-22 where IBES is
    # absent"; its section 3 V3 requires the merge to "reproduce bit-identical on the unchanged
    # rows, so the repair is provably additive". Both cannot hold, because the two sources
    # genuinely disagree: applying the precedence rule DROPS 1,708 code-22 dates and leaves only
    # 8 of 157 covered names with their original dates intact.
    #
    # The union is shipped as the default and the precedence spine is built beside it, because
    # V3's additivity is the SAFETY property (no landed study's dates can vanish) while section
    # 2's precedence is an editorial claim about which source is right -- and the measurement
    # says neither simply is. `date_sources` makes the precedence view reachable by filtering
    # rather than by deletion, so nothing is lost either way.
    merged = base.merge_source(ibes, label="ibes", precedence="union")
    strict = base.merge_source(ibes, label="ibes", precedence="other")
    dropped = sum(len(set(base.by_ticker.get(t, [])) - set(strict.by_ticker.get(t, [])))
                  for t in names)
    strict_kept = sum(1 for t in names if base.by_ticker.get(t)
                      and set(base.by_ticker[t]).issubset(set(strict.by_ticker.get(t, []))))
    print(f"[w3b] precedence='other' would DROP {dropped:,} code-22 dates and leave "
          f"{strict_kept} of {sum(1 for t in names if base.by_ticker.get(t))} names additive")
    merged_states = collections.Counter(merged.coverage(t) for t in names)
    recovered = sorted(t for t in zero if merged.coverage(t) != ES.FAIL_CLOSED)
    still = sorted(t for t in zero if merged.coverage(t) == ES.FAIL_CLOSED)
    print(f"[w3b] V2 merged spine: {dict(merged_states)}")
    print(f"[w3b] V2 recovered {len(recovered)} of {len(zero)} FAIL_CLOSED names; "
          f"still unknown: {still}")

    # ---------------------------------------------------------------- V1: do they AGREE?
    pairs, agree, disagree = 0, 0, []
    for t in names:
        mine = [d for d in base.by_ticker.get(t, [])]
        theirs = ibes.get(t) or []
        if not mine or not theirs:
            continue
        tset = [ES._d(d) for d in theirs]
        tset = [d for d in tset if d]
        for d in mine:
            a = ES._d(d)
            if a is None:
                continue
            pairs += 1
            near = min((abs((a - b).days) for b in tset), default=10 ** 6)
            if near <= AGREE_DAYS:
                agree += 1
            else:
                disagree.append({"ticker": t, "code22": d, "nearest_ibes_days": int(near)})
    rate = agree / pairs if pairs else 0.0
    print(f"[w3b] V1 agreement: {agree:,} of {pairs:,} code-22 dates within "
          f"+/-{AGREE_DAYS}d of an IBES date = {100*rate:.2f}% (bar {100*AGREE_BAR:.0f}%)")

    # WHY V1 FAILS IS THE DELIVERABLE, and a bare rate cannot distinguish the two causes, which
    # imply opposite actions. Split it: a code-22 date in a year where IBES has NOTHING is a
    # coverage gap and no evidence about either source; a code-22 date in a year where IBES has
    # announcements and none is near is a genuine conflict about when the company reported.
    gap, conflict = 0, []
    for t in names:
        mine = sorted({ES._d(x) for x in base.by_ticker.get(t, []) if ES._d(x)})
        theirs = sorted({ES._d(x) for x in (ibes.get(t) or []) if ES._d(x)})
        if not mine or not theirs:
            continue
        yrs = collections.defaultdict(list)
        for b in theirs:
            yrs[b.year].append(b)
        for a in mine:
            if min((abs((a - b).days) for b in theirs), default=10 ** 6) <= AGREE_DAYS:
                continue
            if yrs.get(a.year):
                conflict.append({"ticker": t, "code22": a.isoformat()})
            else:
                gap += 1
    print(f"[w3b] V1 residual: {gap:,} coverage-gap + {len(conflict):,} real-conflict")

    # IS CODE 22 BROADER THAN EARNINGS? The direct test, because two anecdotes are not a finding.
    more = same = fewer = 0
    for t in names:
        c = collections.Counter(d[:4] for d in base.by_ticker.get(t, []))
        i = collections.Counter(d[:4] for d in (ibes.get(t) or []))
        for y in set(c) & set(i):
            if c[y] > i[y]:
                more += 1
            elif c[y] == i[y]:
                same += 1
            else:
                fewer += 1
    ny = more + same + fewer
    print(f"[w3b] code-22 vs IBES dates per name-year (n={ny:,}): "
          f"code22 MORE {100*more/max(1,ny):.1f}%, equal {100*same/max(1,ny):.1f}%, "
          f"code22 FEWER {100*fewer/max(1,ny):.1f}%")

    # ---------------------------------------------------------------- V3: additive on old rows
    unchanged, changed = 0, []
    for t in names:
        before = base.by_ticker.get(t, [])
        after = merged.by_ticker.get(t, [])
        if not before:
            continue
        if set(before).issubset(set(after)):
            unchanged += 1
        else:
            changed.append(t)
    print(f"[w3b] V3 additive: {unchanged} of {sum(1 for t in names if base.by_ticker.get(t))} "
          f"covered names keep every original date; violations: {changed}")

    res = {
        "item": "W-3b",
        "class": "collection-and-repair (instrument)",
        "trials": 0,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "n_names": len(names),
        "base_states": {k: int(v) for k, v in base_states.items()},
        "merged_states": {k: int(v) for k, v in merged_states.items()},
        "fail_closed_before": zero,
        "fail_closed_after": still,
        "recovered": recovered,
        "n_recovered": len(recovered),
        "ibes_names": len(ibes),
        "crsp_resolved": len(iv),
        "crsp_intervals": n_iv,
        "v1_agreement": {"pairs": pairs, "agree": agree,
                         "rate": round(rate, 6), "bar": AGREE_BAR,
                         "tolerance_calendar_days": AGREE_DAYS,
                         "pass": bool(rate >= AGREE_BAR),
                         "n_disagreements": len(disagree),
                         "disagreements": disagree[:200]},
        "v1_residual": {"coverage_gap": gap, "real_conflict": len(conflict),
                        "conflicts": conflict[:300]},
        "code22_breadth": {"name_years": ny, "code22_more": more, "equal": same,
                           "code22_fewer": fewer,
                           "pct_code22_more": round(100 * more / max(1, ny), 1),
                           "note": (
                               "SEC Item 2.02 is 'Results of Operations and Financial "
                               "Condition', which issuers also file for monthly sales, "
                               "preliminary results and guidance revisions. Where code 22 "
                               "emits MORE dates than IBES, the extras are those filings, not "
                               "missing IBES data -- ROST ran 8/yr until 2013 (monthly sales), "
                               "PNC 7.67/yr, NKE 6.20/yr, while MSFT, JPM and AAPL are exactly "
                               "4.00 against IBES's 4.00.")},
        "v3_additive": {"covered_names": sum(1 for t in names if base.by_ticker.get(t)),
                        "kept_all_dates": unchanged, "violations": changed,
                        "pass": not changed,
                        "strict_precedence_would_drop": dropped,
                        "strict_precedence_kept_all": strict_kept},
        "date_source_counts": dict(collections.Counter(merged.date_sources.values())),
    }
    p = json_path or OUT
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[w3b] wrote {p}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="W-3b: IBES actuals into the earnings-date spine")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    run(a.json)


if __name__ == "__main__":
    main()
