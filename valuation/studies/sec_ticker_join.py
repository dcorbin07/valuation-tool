# -*- coding: utf-8 -*-
"""Resolve an SEC filer to the corrected panel's own ticker, DATED, per filing date.

**THIS IS AN INSTRUMENT REPAIR, NOT A HYPOTHESIS.** `F23-SECID` measured its SEC-sourced cell
covering **608 tickers against SF2's 1,344, sharing only 335**, with a point-in-time market cap
resolved for **48.1%** of events against SF2's **83.3%** — so the arms were scored on a different
population from the registered one. `DECISIONS.md` 2026-10-15 and the follow-up brief call that an
instrument defect, and it is the same join F-23's live feed would use.

**WHY THE SYMBOL AS FILED FAILS, MEASURED RATHER THAN ASSUMED.** `SUBMISSION.ISSUERTRADINGSYMBOL`
is **FREE TEXT**, not a symbol field. On the 2009-2019 build era it carries 10,361 distinct values
of which only **46.0%** match the panel, and the misses are mostly punctuation rather than unknown
companies:

    '"NHF"'   '( EPG )'   '("SPAR")'   '(CALX)'   '(KO)'   '(NYSE:FBC)'   '(NONE)'   'N O G'

**774 of 5,595 missing values are non-alphabetic.** A separator-insensitive key rescues **3 of
5,595**, so normalising punctuation is *not* the fix — the symbol has to be **extracted** from the
text.

**AND THE SECOND HALF IS WHY THIS IS KEYED ON THE CIK.** In the build era **8,542 of 47,141 CIKs
(18.1%) file under MORE THAN ONE symbol**, covering **52.9% of rows**; of those, 6,601 have *some*
symbol in the panel and only 2,581 have *all* of them in it. So the same company is sometimes
`(KO)` and sometimes `KO`, and a per-filing symbol cannot repair that while a **CIK** can.

**EDGAR's `company_tickers.json` IS DELIBERATELY NOT USED.** It is a **current** snapshot, so
applying it to a 2009 filing is look-ahead and it omits every delisted name — `S25`'s measured
lesson about a snapshot wearing a date, and delisted names are exactly the ones an event study must
keep (`E-5`).

**THE RESOLUTION IS STRICTLY BACKWARD-LOOKING.** For a filing on date `d` by CIK `c`, the symbol is
the most recent symbol `c` filed under **at or before `d`** that resolves in the panel; failing
that, its most recent cleaned symbol at all. A future rename can never reach back. The
full-history variant is available as a declared SENSITIVITY and is not the primary.

**AN HONEST LIMIT, STATED RATHER THAN LEFT TO BE NOTICED: the PANEL MEMBERSHIP test is not dated.**
`_to_panel` asks whether a symbol appears in the panel's ticker set, which spans the whole panel
window — so a 2010 filing by a company that first enters the panel in 2020 resolves. That is
**exactly what the first read did** (`ticker.isin(panel)`), so it is not something this repair
introduces, and it is neutralised downstream rather than ignored: the arm needs a point-in-time
market cap, and `insider_wide_tier_choice.cap_at` returns one only where the panel carries a row at
or before the event date, so an event on a name the panel does not yet hold is dropped and counted.
Repairing it here would change the row set as well as the key.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

import pandas as pd

#: Values that mean "no symbol" rather than naming one. Matched after cleaning, exactly.
_NULL_SYMBOLS = frozenset({"", "NONE", "N/A", "NA", "NAN", "NULL", "NONE)", "NOTAPPLICABLE"})

#: `(NYSE:FBC)`, `NASDAQ: ABCD` — the exchange prefix is dropped, the symbol kept.
_EXCH = re.compile(r"^(?:NYSE|NASDAQ|AMEX|NYSEMKT|NYSEAMEX|OTC|OTCBB|BATS|ARCA|CBOE)\s*:\s*",
                   re.I)

#: A plausible US equity symbol after cleaning: 1-6 letters, optionally a class suffix.
_SYMBOL = re.compile(r"^[A-Z]{1,6}(?:[.\-][A-Z]{1,2})?$")


def clean_symbol(raw) -> str:
    """Extract a symbol from SEC free text. Returns `""` when there is none.

    Deliberately conservative: it strips wrappers and an exchange prefix, and then **requires the
    result to look like a symbol**. It does NOT guess — a value that does not match `_SYMBOL` comes
    back empty, so a bad parse shows up as an unresolved row that gets counted, never as a
    plausible-looking wrong ticker. That is the direction `MA31` warns about: a clean, confident,
    wrong number is worse than a missing one.
    """
    t = str(raw or "").strip().upper()
    if not t:
        return ""
    # wrappers: quotes, parens, brackets -- applied repeatedly because `("SPAR")` has both
    for _ in range(4):
        before = t
        t = t.strip().strip("()[]{}").strip().strip('"\'').strip()
        if t == before:
            break
    t = _EXCH.sub("", t).strip()
    # `N O G` -> `NOG`: interior single spaces between single letters only, so `FOO BAR CORP`
    # is NOT silently welded into a symbol.
    if " " in t and all(len(p) == 1 for p in t.split()):
        t = "".join(t.split())
    t = t.strip(".,;:")
    if t in _NULL_SYMBOLS:
        return ""
    return t if _SYMBOL.match(t) else ""


def panel_variants(panel_tickers: Iterable[str]) -> Dict[str, str]:
    """`{normalised: panel ticker}` so `BRKB` finds `BRK.B`.

    Separators only — this rescued 3 of 5,595 on its own and is kept because it costs nothing and
    is the *correct* handling of a class share. A normalised key colliding on two different panel
    tickers is DROPPED rather than resolved arbitrarily, because guessing which `BRK` was meant is
    exactly the wrong-object family.
    """
    seen: Dict[str, set] = {}
    for t in panel_tickers:
        k = re.sub(r"[.\-/ ]", "", str(t).upper())
        seen.setdefault(k, set()).add(str(t).upper())
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def repair(rows: pd.DataFrame, panel_tickers: Iterable[str], cik_col: str = "cik",
           sym_col: str = "ticker", date_col: str = "filingdate") -> pd.DataFrame:
    """A COPY of `rows` whose `sym_col` is the repaired, dated panel ticker.

    The one entry point every caller uses, so the repair cannot drift into two implementations
    (`B7`). The CIK symbol history is built from **all** of `rows`, which is why callers pass the
    whole pull rather than a window: truncating the history first would hide a symbol a filer used
    before the window and resolve fewer rows for a reason that has nothing to do with the date rule.
    """
    j = SecTickerJoin(rows, panel_tickers, cik_col, sym_col, date_col)
    out = rows.copy()
    out[sym_col] = j.repair_column(rows, cik_col, sym_col, date_col)
    return out


class SecTickerJoin(object):
    """CIK -> panel ticker, resolved at a filing date.

    Built from the SEC's OWN quarterly submissions, so the symbol history is dated by construction
    and no external snapshot is consulted.
    """

    def __init__(self, rows: pd.DataFrame, panel_tickers: Iterable[str],
                 cik_col: str = "cik", sym_col: str = "ticker",
                 date_col: str = "filingdate"):
        self.panel = {str(t).upper() for t in panel_tickers}
        self.variants = panel_variants(self.panel)
        hist: Dict[str, List[Tuple[str, str]]] = {}
        for cik, d, sym in zip(rows[cik_col].astype(str), rows[date_col].astype(str),
                               rows[sym_col]):
            s = self._to_panel(clean_symbol(sym))
            if s:
                hist.setdefault(cik, []).append((d, s))
        self.history = {c: sorted(set(v)) for c, v in hist.items()}

    def _to_panel(self, sym: str) -> str:
        """A cleaned symbol mapped onto the panel's own spelling, or `""`."""
        if not sym:
            return ""
        if sym in self.panel:
            return sym
        k = re.sub(r"[.\-/ ]", "", sym)
        return self.variants.get(k, "")

    def resolve(self, cik, date, as_filed=None) -> str:
        """The panel ticker for this filer on this date, or `""`.

        Order, and every step is backward-looking:
          1. the symbol **as filed on this row**, if it resolves — the most specific evidence;
          2. the most recent symbol this CIK filed under **at or before `date`** that resolves;
          3. **nothing.** A filer whose symbol never resolves returns `""` and is COUNTED as
             unresolved, never guessed at.

        Step 3 matters: the panel is a universe, so an unresolved filer is usually a company the
        panel does not contain, and inventing a ticker for it would put a foreign row into the cell.
        """
        direct = self._to_panel(clean_symbol(as_filed)) if as_filed is not None else ""
        if direct:
            return direct
        h = self.history.get(str(cik))
        if not h:
            return ""
        d = str(date)
        prior = [s for (dd, s) in h if dd <= d]
        return prior[-1] if prior else ""

    def resolve_frame(self, rows: pd.DataFrame, cik_col: str = "cik",
                      sym_col: str = "ticker", date_col: str = "filingdate") -> pd.Series:
        return pd.Series(
            [self.resolve(c, d, s) for c, d, s in
             zip(rows[cik_col].astype(str), rows[date_col].astype(str), rows[sym_col])],
            index=rows.index, dtype=object)

    def repair_column(self, rows: pd.DataFrame, cik_col: str = "cik",
                      sym_col: str = "ticker", date_col: str = "filingdate") -> pd.Series:
        """The repaired ticker column: the resolved panel ticker, else **the symbol as filed**.

        Falling back to the as-filed string rather than to `""` is deliberate and it is what makes
        the before/after comparable. An unresolved row keeps exactly the value the first read gave
        it, so it is filtered out downstream exactly as it was before; the ONLY rows that move are
        the ones the repair newly resolves. Dropping them instead would change the row set and the
        key at once, and neither could then be attributed — the confound `F23-SECID`'s own §1 was
        written to avoid.
        """
        res = self.resolve_frame(rows, cik_col, sym_col, date_col)
        raw = rows[sym_col].astype(str).str.strip().str.upper()
        return res.where(res != "", raw)

    def resolve_frame_full_history(self, rows: pd.DataFrame, cik_col: str = "cik",
                                   sym_col: str = "ticker",
                                   date_col: str = "filingdate") -> pd.Series:
        """DECLARED SENSITIVITY, not the primary: ignores the date and uses the CIK's whole symbol
        history. It can only resolve MORE rows, and it is reported so the cost of insisting on a
        backward-looking map is visible rather than assumed to be zero."""
        out = []
        for c, d, s in zip(rows[cik_col].astype(str), rows[date_col].astype(str), rows[sym_col]):
            v = self.resolve(c, d, s)
            if not v:
                h = self.history.get(str(c)) or []
                v = h[-1][1] if h else ""
            out.append(v)
        return pd.Series(out, index=rows.index, dtype=object)
