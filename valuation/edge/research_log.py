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


def _parse(path):
    """Parse the markdown table. Returns totals plus a per-domain breakdown."""
    trials = fixed = counted = 0
    ids = []
    by_domain = {d: 0 for d in DOMAINS}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        rid = cells[0]
        if not rid or rid.lower() in ("id", "field") or set(rid) <= set("-: "):
            continue                                  # header or separator
        verdict = " ".join(cells).upper()
        if re.search(r"\bFIXED\b", verdict):
            fixed += 1
            continue
        # `n=<k>` anywhere in the row marks a pre-registered grid of k cells.
        m = re.search(r"\bn=(\d+)\b", ln)
        k = int(m.group(1)) if m else 1
        trials += k
        counted += 1
        ids.append(rid)
        for d in DOMAINS:
            if any(c.lower() == d for c in cells):
                by_domain[d] += k
                break
    return {"trials": trials, "rows_counted": counted, "rows_fixed": fixed, "ids": ids,
            "by_domain": by_domain}


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
