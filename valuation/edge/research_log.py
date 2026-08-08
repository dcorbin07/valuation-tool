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


DOMAINS = ("equity", "options", "unified", "infra")


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
    m = {k: low.index(k) for k in ("id", "verdict", "n", "domain") if k in low}
    m["_width"] = len(cells)
    return m


def _cell(cells, hdr, field):
    """The named field's own cell, or None if this table has no such column."""
    i = (hdr or {}).get(field)
    return cells[i] if i is not None and i < len(cells) else None


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
    changed = []                                      # rows whose treatment differs from legacy
    malformed = []                                    # rows whose columns do not line up
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
    return {"trials": trials, "rows_counted": counted, "rows_fixed": fixed, "ids": ids,
            "by_domain": by_domain, "rows_changed_by_parser_fix": changed,
            "rows_malformed": malformed}


def trial_count(path=None, use_cache=True, domain="equity"):
    """The number of trials to use as `N`. Never below WEIGHT_SCHEME_TRIALS.

    DOMAIN-SCOPED BY DEFAULT, and this is a real statistical choice rather than a convenience.
    The Deflated Sharpe corrects for the size of the search that produced THIS strategy. The
    options programme's 126-feature autopsy is a different search over different data for a
    different product; charging the equity composite for it would over-penalise, exactly as
    charging it for nothing but its own eight weight schemes under-penalises. The log's own
    schema already says BH-FDR families are formed within a domain, so the same rule applies
    here. `domain=None` returns the whole-project count.
    """
    d = detail(path=path, use_cache=use_cache)
    if domain and (d.get("by_domain") or {}).get(domain) is not None:
        return int(max(WEIGHT_SCHEME_TRIALS, d["by_domain"][domain]))
    return int(max(WEIGHT_SCHEME_TRIALS, d.get("trials_logged") or 0))


def detail(path=None, use_cache=True):
    """Everything a reader needs to audit the denominator, for the results file."""
    p = path or _LOG
    if use_cache and p in _CACHE:
        return _CACHE[p]
    parsed = _parse(p)
    if parsed is None:
        out = {"available": False, "path": p, "trials_logged": None,
               "n_used": WEIGHT_SCHEME_TRIALS,
               "source": "weight_schemes_only — RESEARCH_LOG.md not readable",
               "audit_estimate": 146}
    else:
        n = max(WEIGHT_SCHEME_TRIALS, parsed["by_domain"].get("equity", 0))
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
               "n_used": n,
               "weight_scheme_floor": WEIGHT_SCHEME_TRIALS,
               "source": "RESEARCH_LOG.md (audit M1)",
               "audit_estimate": 146,
               "gap_to_audit_estimate": 146 - parsed["trials"],
               "counting_rule": "all non-FIXED rows count, pre-committed or retrospective; "
                                "`n=<k>` marks a pre-registered grid of k cells"}
    if use_cache:
        _CACHE[p] = out
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(detail(), indent=2))
