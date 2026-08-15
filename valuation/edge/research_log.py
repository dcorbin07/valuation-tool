"""research_log.py — the project's trial counter.  [AUDIT M1]

Every multiple-testing claim in this project has been computed against a denominator of **8**:
the eight weight schemes `_deflated_sharpe` is handed. The external audit reconstructed roughly
**146** distinct tests across the handoff corpus. Both numbers cannot inform the same claim, and
the smaller one is the one that has been shipping.

This module reads `RESEARCH_LOG.md`'s table and returns the number of TRIALS — the number of
times the data has been interrogated — so `_deflated_sharpe` and `_trials_haircut` can be fed a
real `N`.

TWO SCHEMA DECISIONS, both of which change the count and both of which are deliberate:

1. **A trial does not have to have been pre-committed to count.** The log's original rule was
   "a test earns a row when its threshold was committed before its run". That is the right rule
   for deciding whether a RESULT is credible; it is the wrong rule for a multiple-testing
   DENOMINATOR. What inflates the best-looking result is how many times the data was searched,
   not how virtuously each search was documented. Excluding undocumented searches would
   systematically understate `N` and therefore OVERSTATE significance — the exact error M1
   exists to fix. Rows carry `pre_committed` (`yes` / `retro`) for the credibility question and
   both count toward `N`.

2. **`FIXED` rows do not count.** Repairing a bug is not a search over the data. Inflating the
   denominator with correctness fixes would understate the evidence rather than overstate it,
   which is an error in the opposite direction and just as dishonest.

   **REPAIRED 2026-08-08 (session 12): the verdict is read from THE VERDICT COLUMN, not from the
   row.** For three sessions this test ran against every cell joined together, so a row whose
   hypothesis, threshold, source or note merely contained the word "fixed" was dropped from `N`
   even where its verdict read `REJECTED`. Understating `N` overstates the significance of every
   DSR-gated claim in the project — M1's own error, inside M1's own parser. Three sessions worked
   around it by choosing synonyms, which means the shipped denominator was being protected by
   authors' word choice rather than by code. The grid multiplier and the domain were read the
   same loose way (whole line / first matching cell) and are fixed with it.

3. **A row may represent a pre-registered GRID via `n_trials`.** The lazy-prices study ran a
   28-cell grid of measures × horizons as ONE pre-registered sweep. Writing 28 near-identical
   rows would be fabricated precision; writing one row and counting it once would undercount a
   28-way search by a factor of 28. The row records `n=28` and the counter sums it.

`N` is a MEASURED FLOOR, never a guess. If the reconstruction recovers fewer trials than the
audit's ~146, the smaller honest number is what gets used and the gap is reported.
"""
from __future__ import annotations

import os
import re

# The eight weight schemes. `_deflated_sharpe` has always used this as N; it is the floor below
# which the counter must never fall, because those trials genuinely happened too.
WEIGHT_SCHEME_TRIALS = 8

_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "RESEARCH_LOG.md")

_CACHE: dict = {}
_PARSED: dict = {}       # AUDIT MA6 — the raw parse, memoised on (path, mtime, size)


DOMAINS = ("equity", "options", "unified", "infra")


# Fields resolved from each table's own header. The first four drive the COUNT; the rest are
# read for surfaces that need the RECORD rather than the denominator (see `rows()`), and are
# resolved by the same rule so there is never a second parser to disagree with this one.
_FIELDS = ("id", "verdict", "n", "domain", "date", "hypothesis", "metric", "threshold",
           "source", "pre", "universe")


def _header_map(cells):
    """If this row is a table header, return {field: column index}; else None.  [SESSION 12]

    `RESEARCH_LOG.md` holds TWO tables with DIFFERENT column layouts — the original
    (`id date domain hypothesis universe metric threshold verdict source`, verdict at 7) and the
    retrospective reconstruction (`id date domain pre hypothesis metric verdict n source`, verdict
    at 6 and `n` at 7). Any counter that hard-codes an index is wrong on one of them, so each
    table's columns are resolved from its own header.
    """
    low = [c.strip().lower() for c in cells]
    if "id" not in low or "verdict" not in low:
        return None                                   # not a row-table header
    # EXACT match only. A `startswith` rule would let a future `notes` column be resolved as
    # `n`, silently multiplying that row's trials by whatever prose it contained — the same
    # class of defect as the session-12 whole-row grep this parser exists to have fixed.
    m = {f: low.index(f) for f in _FIELDS if f in low}
    if "threshold" not in m:                          # the one real header with a suffix
        for i, c in enumerate(low):
            if c.startswith("threshold"):
                m["threshold"] = i
                break
    m["_width"] = len(cells)
    return m


def _cell(cells, hdr, field):
    """The named field's own cell, or None if this table has no such column."""
    i = (hdr or {}).get(field)
    return cells[i] if i is not None and i < len(cells) else None


def _emit(out, cells, hdr, rid, aligned, vcell, k):
    """Record one row for surfaces that render the RECORD rather than the denominator.

    Collected inside the one parse, so the public research page and the trial counter can
    never disagree about what the log says. This project has been bitten twice by a second
    reader of the same fact — session 12's `\\bFIXED\\b` whole-row grep, and the two
    forward-track recorders that put a false claim into Discord — so there is deliberately no
    second parser here.

    Cells are handed over RAW. Deciding what may be PUBLISHED is the surface's job: the log
    records thresholds and result figures that the public page is not allowed to show, and a
    parser that pre-censored them would make the counter depend on a publishing rule.
    """
    row = {"id": rid, "n_trials": k, "aligned": aligned,
           "verdict": (vcell or "").strip()}
    for f in ("date", "hypothesis", "metric", "threshold", "source", "pre", "universe"):
        row[f] = ((_cell(cells, hdr, f) if aligned else None) or "").strip()
    out.append(row)


def _parse(path):
    """Parse the markdown tables. Returns totals plus a per-domain breakdown.

    SESSION 12 — every field is read from ITS OWN COLUMN. The previous implementation tested
    `\\bFIXED\\b` against every cell of the row joined together, so any row whose free-text note
    happened to contain the word "fixed" was silently dropped from `N`. An understated `N`
    OVERSTATES the significance of every DSR-gated claim in the project — the exact error M1
    exists to prevent, committed inside M1's own parser. The grid multiplier (`n=<k>`) and the
    domain were read the same loose way and are fixed alongside it.

    Where a field cannot be resolved, the row is resolved toward a LARGER `N` (the less
    favourable direction): an unreadable or absent verdict counts as a trial, never as `FIXED`.
    """
    trials = fixed = counted = 0
    ids = []
    rows_out = []                                     # the record, for `rows()`
    changed = []                                      # rows whose treatment differs from legacy
    malformed = []                                    # rows whose columns do not line up
    unresolved = []                                   # AUDIT MA6 — rows charged to no domain
    misfiled = []                                     # AUDIT MA6 — rows under the wrong table
    by_domain = {d: 0 for d in DOMAINS}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None
    hdr = None
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        maybe = _header_map(cells)
        if maybe is not None:
            hdr = maybe                               # a new table starts here
            continue
        rid = cells[0]
        if not rid or rid.lower() in ("id", "field") or set(rid) <= set("-: "):
            continue                                  # stray header or separator

        # A cell containing an unescaped `|` splits into extra cells and shifts every column
        # after it, so this row's indices no longer mean what the header says. It is a real
        # defect in the log (O16 writes `|Spearman(a, b)|` for an absolute value), and it must
        # NOT be allowed to silently drop trials: a misaligned row resolves toward a LARGER `N`
        # on every field, which is the less favourable direction.
        aligned = hdr is not None and len(cells) == hdr.get("_width")
        if hdr is not None and not aligned:
            malformed.append({"id": rid, "header_width": hdr.get("_width"),
                              "row_width": len(cells),
                              "reason": "unescaped `|` in a cell shifts the columns"})

        # --- verdict: THE VERDICT CELL ALONE ---------------------------------------------
        vcell = _cell(cells, hdr, "verdict") if aligned else None
        is_fixed = bool(vcell) and vcell.strip().upper().startswith("FIXED")
        legacy_fixed = bool(re.search(r"\bFIXED\b", " ".join(cells).upper()))
        if is_fixed != legacy_fixed:
            changed.append({"id": rid, "field": "verdict", "was": "FIXED" if legacy_fixed
                            else "counted", "now": "FIXED" if is_fixed else "counted",
                            "verdict_cell": vcell})
        if is_fixed:
            fixed += 1
            # Emitted with ZERO trials, not skipped. A `FIXED` row is not a search over the
            # data — that is why it does not count toward `N` — but it IS part of the record,
            # and the public research page renders it as such. The two questions are
            # different and this is the only place that says so.
            _emit(rows_out, cells, hdr, rid, aligned, vcell, 0)
            continue

        # --- grid multiplier: THE `n` CELL ALONE ------------------------------------------
        # On a misaligned row the column cannot be located, so fall back to the whole-line
        # scan and take whichever is LARGER — never the smaller.
        ncell = _cell(cells, hdr, "n") if aligned else None
        m = re.search(r"\bn=(\d+)\b", ncell) if ncell else None
        lm = re.search(r"\bn=(\d+)\b", ln)
        lk = int(lm.group(1)) if lm else 1
        k = int(m.group(1)) if m else (1 if aligned else lk)
        if k != lk:
            changed.append({"id": rid, "field": "n", "was": lk, "now": k, "n_cell": ncell})

        trials += k
        counted += 1
        ids.append(rid)
        _emit(rows_out, cells, hdr, rid, aligned, vcell, k)

        # --- misfiled row: a table-2 row sitting under table-1's header  [AUDIT MA6] ------
        # THE WIDTH GUARD CANNOT SEE THIS. `aligned` compares `len(cells)` to the header width
        # and BOTH tables are NINE columns wide, so a row appended under the wrong header is
        # "aligned" and every field is read from the wrong column. The two layouts differ from
        # index 3 onward — table 1 ends `... threshold verdict source`, table 2 ends
        # `... verdict n source` — so a table-2 row read under table-1's header has its VERDICT
        # taken from index 7, which for that row is the grid multiplier.
        #
        # THE RULE IS NARROW ON PURPOSE AND HAS ZERO FALSE POSITIVES ON THE LOG AS IT STANDS:
        # a verdict cell of the exact form `n=<k>` cannot be a verdict. The reverse direction (a
        # table-1 row under table-2's header) is NOT detected, and that is a deliberate limit
        # rather than an oversight — catching it would need a vocabulary of what counts as a
        # verdict word, which is a second definition of "verdict" that would cry wolf the first
        # time someone wrote a new one. Reported in the handoff, not papered over.
        if aligned and vcell and re.fullmatch(r"n=\d+", vcell.strip()):
            misfiled.append({"id": rid, "verdict_cell": vcell.strip(),
                             "reason": "verdict cell is a grid multiplier — this row is almost "
                                       "certainly appended under the WRONG table's header; both "
                                       "tables are 9 columns wide so the width guard cannot see it"})

        # --- domain: THE DOMAIN CELL ALONE ------------------------------------------------
        dcell = ((_cell(cells, hdr, "domain") if aligned else None) or "").lower()
        dom = dcell if dcell in DOMAINS else None
        if dom is None:                               # no domain column: best available guess
            for d in DOMAINS:
                if any(c.lower() == d for c in cells):
                    dom = d
                    break
        legacy_dom = next((d for d in DOMAINS if any(c.lower() == d for c in cells)), None)
        if dom != legacy_dom:
            changed.append({"id": rid, "field": "domain", "was": legacy_dom, "now": dom})
        if dom:
            by_domain[dom] += k
        else:
            # AUDIT MA6 — THE ONE SILENT PATH THAT UNDERSTATED `N`, AND IT WAS THE ONLY
            # DEGRADATION IN THIS PARSER ROUTED TOWARD A *SMALLER* DENOMINATOR.
            #
            # A row whose domain cell is not exactly one of DOMAINS (a typo, "equities", a blank
            # cell, a new domain name nobody registered) was added to `trials` and to NO bucket —
            # and `trial_count(domain=...)` reads the bucket. So the row was a real search over
            # the data that no family was charged for. Understating `N` OVERSTATES the
            # significance of every DSR- and HLZ-gated claim: it is M1's own stated error,
            # committed inside M1's own parser, for the second time after session 12's
            # whole-row `FIXED` grep.
            #
            # It is COUNTED here and CHARGED in `trial_count`, which is the only place the
            # direction can be fixed without lying about what the log says. `by_domain` keeps
            # meaning "rows that resolved to this family" — so `sum(by_domain) + unresolved ==
            # trials` stays an invariant a reader can check, and MA13's committed-literal stamp
            # still pins the same quantity it always pinned.
            unresolved.append({"id": rid, "n_trials": k, "domain_cell": dcell or None,
                               "aligned": aligned,
                               "reason": "domain cell is not one of %s" % (DOMAINS,)})
    return {"trials": trials, "rows_counted": counted, "rows_fixed": fixed, "ids": ids,
            "by_domain": by_domain, "rows_changed_by_parser_fix": changed,
            "rows_malformed": malformed, "rows": rows_out,
            "rows_domain_unresolved": unresolved,
            "trials_domain_unresolved": sum(u["n_trials"] for u in unresolved),
            "rows_misfiled_table": misfiled}


def _stamp(path):
    """(mtime_ns, size), or None if the file cannot be stat'd.  [AUDIT MA6]

    The cache key carries this so a file that CHANGES on disk re-parses instead of serving a
    stale count. The previous key was the path alone, which is fine for the one real log read
    once per process and wrong for a test that rewrites a fixture at the same path — exactly
    the case `use_cache` exists for.
    """
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _parsed(path, use_cache=True):
    """`_parse`, memoised on (path, mtime, size). ONE parse behind every reader.  [AUDIT MA6]"""
    key = (path, _stamp(path))
    if use_cache and key in _PARSED:
        return _PARSED[key]
    out = _parse(path)
    if use_cache:
        _PARSED[key] = out
    return out


def trial_count(path=None, use_cache=True, domain="equity"):
    """The number of trials to use as `N`. Never below WEIGHT_SCHEME_TRIALS.

    DOMAIN-SCOPED BY DEFAULT, and this is a real statistical choice rather than a convenience.
    The Deflated Sharpe corrects for the size of the search that produced THIS strategy. The
    options programme's 126-feature autopsy is a different search over different data for a
    different product; charging the equity composite for it would over-penalise, exactly as
    charging it for nothing but its own eight weight schemes under-penalises. The log's own
    schema already says BH-FDR families are formed within a domain, so the same rule applies
    here. `domain=None` returns the whole-project count.

    AUDIT MA6 — UNRESOLVED-DOMAIN ROWS ARE CHARGED TO EVERY FAMILY. A row whose domain cell
    resolves to no bucket is still a search over the data; it simply cannot be attributed. The
    two available treatments are to drop it (understating `N`, which OVERSTATES significance)
    or to charge it everywhere (overstating `N`, which understates significance). This module's
    opening argument fixes the direction: every other degradation here is routed toward a LARGER
    `N` and reported, and this was the only one routed the other way. So it is added, and
    `detail()["rows_domain_unresolved"]` names the rows so the charge is auditable rather than
    absorbed. It is ZERO on the log as it stands, so nothing moves today.
    """
    d = detail(path=path, use_cache=use_cache)
    extra = int(d.get("trials_domain_unresolved") or 0)
    if domain and (d.get("by_domain") or {}).get(domain) is not None:
        return int(max(WEIGHT_SCHEME_TRIALS, d["by_domain"][domain] + extra))
    return int(max(WEIGHT_SCHEME_TRIALS, d.get("trials_logged") or 0))


def rows(path=None, use_cache=True) -> list:
    """Every logged row, in file order, for surfaces that render the RECORD.

    Same parse as `trial_count`/`detail` — see `_emit`. `FIXED` rows are INCLUDED and carry
    `n_trials == 0`, because "is this part of the record" and "was this a search over the data"
    are different questions and only the second one sets `N`.

    Returns raw cells. Callers that publish must apply their own rule about what may be shown;
    `valuation/web/research_record.py` is the one that does, and it withholds figures.

    AUDIT MA6 — `use_cache` is now HONOURED. It was accepted and ignored: this function called
    `_parse` unconditionally, so the parameter was a lie and a caller passing `use_cache=False`
    to force a re-read got the same behaviour as one that did not. Harmless in outcome (it
    always re-read, which is the safe direction) and worth closing because a parameter that
    does nothing is indistinguishable from one that stopped working.
    """
    parsed = _parsed(path or _LOG, use_cache)
    return list((parsed or {}).get("rows") or [])


def detail(path=None, use_cache=True):
    """Everything a reader needs to audit the denominator, for the results file."""
    p = path or _LOG
    key = (p, _stamp(p))                              # AUDIT MA6 — see `_stamp`
    if use_cache and key in _CACHE:
        return _CACHE[key]
    parsed = _parsed(p, use_cache)
    if parsed is None:
        out = {"available": False, "path": p, "trials_logged": None,
               "n_used": WEIGHT_SCHEME_TRIALS,
               "source": "weight_schemes_only — RESEARCH_LOG.md not readable",
               "audit_estimate": 146}
    else:
        # AUDIT MA6 — the unresolved rows are charged here too, so `n_used` and
        # `trial_count(domain="equity")` cannot drift apart. Zero on the log as it stands.
        unres_n = int(parsed.get("trials_domain_unresolved") or 0)
        n = max(WEIGHT_SCHEME_TRIALS, parsed["by_domain"].get("equity", 0) + unres_n)
        out = {"available": True, "path": os.path.basename(p),
               "trials_logged": parsed["trials"],
               "by_domain": parsed["by_domain"],
               "n_scope": "equity — the family this composite was searched within",
               "rows_counted": parsed["rows_counted"],
               "rows_fixed_not_counted": parsed["rows_fixed"],
               # Rows the PRE-SESSION-12 parser would have treated differently. Non-zero means
               # the column-wise read is load-bearing on the log as it stands today, so a silent
               # revert to the whole-row read would move `N`. Kept visible for that reason.
               "rows_rescued_by_parser_fix": len(parsed.get("rows_changed_by_parser_fix") or []),
               "parser_fix_detail": parsed.get("rows_changed_by_parser_fix") or [],
               # Rows whose columns do not line up with their table header — an unescaped `|`
               # inside a cell. Their fields cannot be read by column, so they are counted the
               # conservative way and listed HERE rather than absorbed silently.
               "rows_malformed": parsed.get("rows_malformed") or [],
               # AUDIT MA6 — THE COUNTER THAT DID NOT EXIST. Rows counted in `trials_logged`
               # but charged to no domain bucket. This was the parser's one degradation routed
               # toward a SMALLER `N`, and it was reported nowhere; `trial_count` now charges
               # them to whichever family is asked for, and they are named here so that charge
               # is auditable. NON-ZERO means some row's domain cell needs fixing in the log.
               "rows_domain_unresolved": parsed.get("rows_domain_unresolved") or [],
               "trials_domain_unresolved": unres_n,
               # AUDIT MA6 — rows that look appended under the WRONG table's header. Both
               # tables are nine columns wide, so `rows_malformed`'s width check cannot see
               # this. Reported only: it does not move `N`.
               "rows_misfiled_table": parsed.get("rows_misfiled_table") or [],
               # The invariant a reader can check by hand, stated rather than implied.
               "by_domain_plus_unresolved_equals_trials": bool(
                   sum(parsed["by_domain"].values()) + unres_n == parsed["trials"]),
               "n_used": n,
               "weight_scheme_floor": WEIGHT_SCHEME_TRIALS,
               "source": "RESEARCH_LOG.md (audit M1)",
               "audit_estimate": 146,
               "gap_to_audit_estimate": 146 - parsed["trials"],
               "counting_rule": "all non-FIXED rows count, pre-committed or retrospective; "
                                "`n=<k>` marks a pre-registered grid of k cells"}
    if use_cache:
        _CACHE[key] = out
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(detail(), indent=2))
