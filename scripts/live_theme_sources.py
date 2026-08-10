"""
V2G — free, public LIVE sources for the three dead themes. MEASURED ONLY.

Pre-registered in `PREREG_v2g_live_theme_sources.md`, committed alone at `66310e7` before this
file existed. Read that first; every constant below is fixed there.

Part 12 measured, on 500 real served rows, that three themes carrying **42.9% of the deployed
weight** reach no live score: `capital_discipline` and `institutional` are null on 500/500 rows,
and `insider` is 100% non-null with exactly ONE distinct value. This module builds a live source
for each from free public data and reports coverage. It builds *instruments*, not product.

--------------------------------------------------------------------------------------------
NOTHING HERE REACHES THE COMPOSITE, AND THAT IS ENFORCED RATHER THAN PROMISED.

No file under `valuation/**` is edited by this work. The theme columns are computed here and
reported here; they are never handed to `build_frame`, `_decompose`, or any shipped path. So:
no composite change, no weight flip, and — per Amendment 1, which closes a vintage only on an
**ADOPTED** change, i.e. one that ships in the live scoring path — **no vintage event**. Vintage 2
stays open and its clock does not reset. `tests/test_live_theme_sources.py` asserts the scope
against the repository itself, so a later edit that quietly wires one of these in fails a test.

ADOPTION IS A SEPARATE, LATER, FAR MORE EXPENSIVE DECISION. Coverage is necessary, not
sufficient. See PREREG §1: it needs the pipeline builder's cost measurement, the held-out gate at
the standing margins in BOTH directions, and the acceptance that under Rule 6 it resets the entire
accrued forward clock to zero for no statistical gain. Do not shortcut it from a green number.

--------------------------------------------------------------------------------------------
THE THREE SOURCES — all free, all public, none licensed.

The distinction the brief drew is real and is what makes this buildable: SF3 is a licensed
*aggregation* of 13F; the underlying filings are public record.

  institutional        SEC Form 13F structured data sets (quarterly zips). Aggregated per CUSIP
                       into holder breadth / share accumulation, then combined exactly as
                       `factors.py:267` combines them.

  capital_discipline   Share issuance from XBRL company facts. NOTE, and this correction is in
                       the register rather than discovered here: the brief also asked for
                       accruals under this theme, and `factors.py:254` is `neg_issuance` ALONE.
                       Accruals is a `quality` input (`factors.py:227`). It is built and reported
                       — labelled against `quality`, where it actually goes.

  insider              The repo's ALREADY-FIXED Form 4 scraper, imported and called unmodified,
                       including its refusal contract (score None when filings were found and
                       none could be read — which is not a neutral 50).

--------------------------------------------------------------------------------------------
THE JOIN, WHICH IS THE HARD PART, AND ITS ANCHOR.

13F identifies issuers by CUSIP; the served universe identifies them by ticker; no free CUSIP
master exists. The key is built on a two-rung ladder and the rung is RECORDED PER NAME, like the
beta ladder in `live_cache.py`:

  cusip_13g   authoritative. The company's own SC 13D/G filings carry its CUSIP on the cover.
              Every candidate must pass the CUSIP mod-10 check digit, which makes a false
              positive essentially impossible, and the modal validated value across up to
              MAX_13G_DOCS filings wins.
  name_exact  fallback. Normalised exact match on NAMEOFISSUER. A name matching MORE THAN ONE
              CUSIP is a FAILURE, not a coin flip.

Over both rungs sits an anchor that a fuzzy match cannot fake: institutional dollars held divided
by market cap must land in (0, ANCHOR_MAX]. A join that hit the wrong issuer produces an absurd
ratio. Outside the band the name is EXCLUDED from coverage and listed, never silently kept.

--------------------------------------------------------------------------------------------
RATE LIMITS — the V2F lesson, applied to a different vendor.

V2F's finding was "batch what batches, pace what does not". SEC is friendlier than Yahoo (it
publishes a ~10 req/s ceiling and asks for a descriptive User-Agent) and, better, the 13F leg
BATCHES ALL THE WAY: two ~100MB quarterly zips replace what would otherwise be tens of thousands
of per-filer fetches. Only the per-ticker legs (13G cover, XBRL facts, Form 4) are paced, and all
three cache to disk with the miner's tri-state manifest rule: only TERMINAL outcomes are
recorded, so a throttled or failed unit is retried and coverage can never inflate by running
into a wall.

Usage:
    python -m scripts.live_theme_sources fetch      # paced, resumable; safe to re-run
    python -m scripts.live_theme_sources report     # offline; zero network calls
    python -m scripts.live_theme_sources status
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import math
import os
import random
import re
import statistics
import sys
import time
import zipfile

# --------------------------------------------------------------------------------------------
# Constants. Every one of these is pinned in PREREG_v2g_live_theme_sources.md; changing one
# after a number has been seen voids the run (PREREG §8).
# --------------------------------------------------------------------------------------------

DEFAULT_ROOT = os.path.join("data", "live_themes")
SNAPSHOT = os.path.join("data", "live_cache", "snapshot_2026-08-08.json")

# PREREG §4.2 — two consecutive complete periods. The 01jun2026-31aug2026 window is not
# published (Q2-2026 13Fs are due 2026-08-14), so these are the two most recent complete ones.
PERIOD_CURR = "31-MAR-2026"
PERIOD_PRIOR = "31-DEC-2025"
WINDOW_CURR = "01mar2026-31may2026"
WINDOW_PRIOR = "01dec2025-28feb2026"
DATASET_URL = ("https://www.sec.gov/files/structureddata/data/form-13f-data-sets/"
               "{window}_form13f.zip")

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

MAX_13G_DOCS = 6            # PREREG §4.4
MAX_FORM4_PER_NAME = 40     # PREREG §4.6 — recorded per name when it bites
INSIDER_DAYS = 90           # the scraper's own default window
ANCHOR_MAX = 1.50           # PREREG §4.4 — institutional value / market cap

# TIGHTENING, recorded 2026-08-10 AFTER the first full-universe report and published alongside
# the pre-registered number rather than replacing it (PREREG §8 permits tightening; both figures
# are in HANDOFF_live_data_bugs.md Part 13).
#
# THE PRE-REGISTERED ANCHOR IS ONE-SIDED IN EFFECT. `0 < frac <= 1.50` rejects implausibly HIGH
# institutional ownership and waves through implausibly LOW: a join onto a stale or wrong CUSIP
# that essentially nobody reports holding lands at frac ~1e-6, comfortably inside the band. It
# passed 12 names, including CMCSA, RIO, BTI and HSBC — megacaps credited with ONE reporting
# institution. The floor below is structural rather than tuned: `sm_breadth` is the GROWTH IN
# HOLDER COUNT, and a holder count of one cannot express breadth or its change at all. It is not
# chosen to hit a coverage number — it is the smallest count at which the measure is defined.
MIN_HOLDERS = 2

# PREREG §5 — pre-existing project constants, applied unchanged.
COVERAGE_FLOOR = 0.05       # fundamental_panel.py:3833 — "effectively empty"
MIN_COVERAGE = 0.30         # pead.py:121, elite13f.py:90 — the adoption-relevant bar
MIN_DISTINCT = 2            # theme_health.MIN_DISTINCT_VALUES — carries ranking information

# SEC asks for <= 10 requests/second. Pace under it and never near it.
SEC_MIN_INTERVAL_S = 0.13
SEC_JITTER_S = 0.05
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 5.0
BACKOFF_MAX_S = 120.0
THROTTLE_BUDGET = 40

# Only positive outcomes are durable (mine_options_cache.py:332-336). A unit that failed or was
# throttled is simply absent, so the next run retries it and coverage cannot inflate.
TERMINAL_STATUSES = ("complete", "no_data")

_SUFFIXES = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "SA",
             "NV", "AG", "LP", "HOLDINGS", "GROUP", "THE"}


# --------------------------------------------------------------------------------------------
# Small shared plumbing (mirrors scripts/live_cache.py; kept local so this script has no
# dependency on that one's internals).
# --------------------------------------------------------------------------------------------

def _ensure(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def log(root: str, msg: str) -> None:
    """Print AND append to an on-disk log.

    A backgrounded run's stdout is buffered until the pipe closes, which cost V2F real time;
    the file is readable while the run is still going.
    """
    line = time.strftime("%H:%M:%S") + "  " + msg
    print(line, flush=True)
    try:
        _ensure(root)
        with open(os.path.join(root, "PROGRESS.txt"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _atomic_write_json(path: str, obj) -> None:
    _ensure(os.path.dirname(path) or ".")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, sort_keys=True)
    os.replace(tmp, path)


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


class Manifest:
    """Per-unit terminal outcomes, saved after every unit.

    Refuses a non-terminal status by construction: the one way this pattern fails is a caller
    banking "throttled" as though it were an answer, and then never retrying it.
    """

    def __init__(self, path: str):
        self.path = path
        self.data = _read_json(path) or {}

    def done(self, key: str) -> bool:
        return self.data.get(key, {}).get("status") in TERMINAL_STATUSES

    def mark(self, key: str, status: str, **extra) -> None:
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"non-terminal status {status!r} may not be recorded")
        rec = {"status": status}
        rec.update(extra)
        self.data[key] = rec
        _atomic_write_json(self.path, self.data)

    def count(self, status: str) -> int:
        return sum(1 for v in self.data.values() if v.get("status") == status)


class Throttled(Exception):
    """SEC pushed back. Never recorded as an outcome."""


class Guard:
    """Pacing plus a circuit breaker.

    Two full-universe runs died on a vendor quota in V2F because nothing counted the refusals.
    This counts them and stops the run rather than banking a truncated census as a result.
    """

    def __init__(self, min_interval=SEC_MIN_INTERVAL_S, budget=THROTTLE_BUDGET, sleeper=None):
        self.min_interval = min_interval
        self.budget = budget
        self.throttles = 0
        self.calls = 0
        self._last = 0.0
        self._sleep = sleeper or time.sleep

    def wait(self) -> None:
        gap = time.monotonic() - self._last
        need = self.min_interval + random.random() * SEC_JITTER_S - gap
        if need > 0:
            self._sleep(need)
        self._last = time.monotonic()
        self.calls += 1

    def throttled(self, attempt: int) -> None:
        self.throttles += 1
        if self.throttles > self.budget:
            raise SystemExit(f"throttle budget exhausted after {self.throttles} refusals — "
                             f"stopping rather than banking a partial census")
        self._sleep(min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** attempt)))


def _headers():
    from valuation.config import CONFIG
    ua = getattr(CONFIG, "sec_user_agent", "") or "valquo-research contact@example.com"
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def _get(url: str, guard: Guard, as_json: bool = False):
    """One paced SEC GET with retry. Raises Throttled only after the attempts are spent."""
    import requests
    for attempt in range(MAX_ATTEMPTS):
        guard.wait()
        try:
            r = requests.get(url, headers=_headers(), timeout=30)
        except Exception:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            guard.throttled(attempt)
            continue
        if r.status_code in (429, 403, 503):
            if attempt == MAX_ATTEMPTS - 1:
                raise Throttled(f"{r.status_code} on {url}")
            guard.throttled(attempt)
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json() if as_json else r.text
    raise Throttled(url)


# --------------------------------------------------------------------------------------------
# CUSIP validation. The check digit is what makes the authoritative rung authoritative: a
# nine-character token lifted out of an HTML page is only accepted if its arithmetic closes.
# --------------------------------------------------------------------------------------------

_CUSIP_ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cusip_check_digit(first8: str) -> str:
    """The standard CUSIP mod-10 check digit for the first eight characters."""
    total = 0
    for i, ch in enumerate(first8.upper()):
        if ch.isdigit():
            v = int(ch)
        elif ch == "*":
            v = 36
        elif ch == "@":
            v = 37
        elif ch == "#":
            v = 38
        elif "A" <= ch <= "Z":
            # Letters are valued A=10 ... Z=35. Indexing a "0-9A-Z" alphabet instead is the
            # obvious off-by-ten here and it silently rejects every CUSIP containing a letter,
            # which is most ADRs — caught by the KSPI fixture below.
            v = ord(ch) - ord("A") + 10
        else:
            v = -1
        if v < 0:
            raise ValueError(f"bad CUSIP character {ch!r}")
        if i % 2:
            v *= 2
        total += v // 10 + v % 10
    return str((10 - (total % 10)) % 10)


def valid_cusip(c: str) -> bool:
    c = (c or "").strip().upper()
    if len(c) != 9:
        return False
    if not all(ch in _CUSIP_ALPHA + "*@#" for ch in c):
        return False
    if not any(ch.isdigit() for ch in c):
        return False
    try:
        return cusip_check_digit(c[:8]) == c[8]
    except ValueError:
        return False


_TAG_RE = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"\b([0-9A-Z][0-9A-Z*@#]{8})\b")


def cusips_in_document(text: str) -> list:
    """Every check-digit-valid CUSIP token in an HTML/text filing, in order of appearance."""
    flat = _TAG_RE.sub(" ", text or "")
    flat = flat.replace("&nbsp;", " ")
    out = []
    for tok in _TOKEN_RE.findall(flat.upper()):
        if valid_cusip(tok):
            out.append(tok)
    return out


def normalise_name(s: str) -> str:
    """PREREG §4.4 — fixed before the run and not tuned afterwards."""
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    parts = [p for p in s.split() if p]
    # Corporate suffixes come off the END; only the article "THE" comes off the FRONT.
    # Stripping the whole suffix set from the front too turns "Group 1 Automotive" into
    # "1 Automotive" — harmless here (both sides normalise the same way, and a collision is
    # reported as `ambiguous` rather than resolved) but gratuitous, and gratuitous mangling
    # in a join key is how a mis-join eventually gets made.
    while parts and parts[-1] in _SUFFIXES:
        parts.pop()
    while parts and parts[0] == "THE":
        parts.pop(0)
    return " ".join(parts)


# --------------------------------------------------------------------------------------------
# The universe. Pinned in PREREG §4.1 to the snapshot Part 12 measured on.
# --------------------------------------------------------------------------------------------

def load_served(snapshot: str = SNAPSHOT) -> list:
    payload = _read_json(snapshot)
    if not payload:
        raise SystemExit(f"served snapshot not found: {snapshot} "
                         f"(run `python -m scripts.live_cache capture` first)")
    rows = payload.get("rows") or []
    return [{"ticker": r["ticker"], "name": r.get("name") or "",
             "market_cap": r.get("market_cap"), "sector": r.get("sector") or ""}
            for r in rows]


# --------------------------------------------------------------------------------------------
# 13F aggregation. Streams the TSVs — INFOTABLE is ~360MB uncompressed per quarter, so nothing
# here holds a row list; the accumulators are keyed by CUSIP (~20k) and by filer (~11k).
# --------------------------------------------------------------------------------------------

def dataset_path(root: str, window: str) -> str:
    return os.path.join(root, f"13f_{window}.zip")


def download_dataset(root: str, window: str, guard: Guard | None = None) -> str:
    """Fetch a quarterly zip once. Skip-existing, like the miner."""
    import requests
    path = dataset_path(root, window)
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    _ensure(root)
    url = DATASET_URL.format(window=window)
    r = requests.get(url, headers=_headers(), timeout=900, stream=True)
    r.raise_for_status()
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        for chunk in r.iter_content(1 << 20):
            fh.write(chunk)
    os.replace(tmp, path)
    return path


def _tsv_rows(zf: zipfile.ZipFile, member: str):
    with zf.open(member) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
        header = text.readline().rstrip("\n").split("\t")
        idx = {k: i for i, k in enumerate(header)}
        for line in text:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(header):
                continue
            yield idx, parts


def accessions_for_period(zf: zipfile.ZipFile, period: str) -> tuple:
    """PREREG §4.3 — which accessions count, and the amendment rule.

    Returns (accession -> filer CIK, shape) where shape records the filing counts this run
    actually saw, so the register's measured numbers are reproducible rather than remembered.
    """
    subs = {}
    for idx, p in _tsv_rows(zf, "SUBMISSION.tsv"):
        if p[idx["PERIODOFREPORT"]] != period:
            continue
        if p[idx["SUBMISSIONTYPE"]] not in ("13F-HR", "13F-HR/A"):
            continue
        subs[p[idx["ACCESSION_NUMBER"]]] = {
            "cik": p[idx["CIK"]],
            "filed": p[idx["FILING_DATE"]],
            "amend": p[idx["SUBMISSIONTYPE"]].endswith("/A"),
        }
    kinds = {}
    for idx, p in _tsv_rows(zf, "COVERPAGE.tsv"):
        acc = p[idx["ACCESSION_NUMBER"]]
        if acc in subs:
            kinds[acc] = p[idx["AMENDMENTTYPE"]].strip().upper()

    by_filer = collections.defaultdict(list)
    for acc, rec in subs.items():
        by_filer[rec["cik"]].append(acc)

    keep = {}
    multi = 0
    for cik, accs in by_filer.items():
        if len(accs) > 1:
            multi += 1
        restate = [a for a in accs if kinds.get(a) == "RESTATEMENT"]
        if restate:
            # Latest-filed restatement supersedes everything else for this filer.
            best = max(restate, key=lambda a: (subs[a]["filed"], a))
            keep[best] = cik
            continue
        for a in accs:
            # Original plus any NEW HOLDINGS amendment, which is additive by definition.
            keep[a] = cik
    shape = {"period": period, "filings": len(subs), "filers": len(by_filer),
             "filers_with_multiple_accessions": multi, "accessions_kept": len(keep),
             "restatements": sum(1 for v in kinds.values() if v == "RESTATEMENT"),
             "new_holdings": sum(1 for v in kinds.values() if v == "NEW HOLDINGS")}
    return keep, shape


def aggregate_13f(zip_path: str, period: str) -> dict:
    """Per-CUSIP holder breadth, dollars and shares for one reporting period."""
    with zipfile.ZipFile(zip_path) as zf:
        keep, shape = accessions_for_period(zf, period)
        holders = collections.defaultdict(set)
        value = collections.Counter()
        shares = collections.Counter()
        names = collections.defaultdict(collections.Counter)
        rows = 0
        for idx, p in _tsv_rows(zf, "INFOTABLE.tsv"):
            acc = p[idx["ACCESSION_NUMBER"]]
            cik = keep.get(acc)
            if cik is None:
                continue
            if p[idx["PUTCALL"]].strip():           # option position, not share ownership
                continue
            if p[idx["SSHPRNAMTTYPE"]].strip().upper() != "SH":
                continue
            cusip = p[idx["CUSIP"]].strip().upper()
            if len(cusip) != 9:
                continue
            rows += 1
            holders[cusip].add(cik)
            try:
                value[cusip] += float(p[idx["VALUE"]] or 0)
                shares[cusip] += float(p[idx["SSHPRNAMT"]] or 0)
            except ValueError:
                pass
            names[cusip][p[idx["NAMEOFISSUER"]].strip().upper()] += 1

    out = {}
    for cusip, hs in holders.items():
        common = names[cusip].most_common(1)
        out[cusip] = {"holders": len(hs), "value": value[cusip], "shares": shares[cusip],
                      "name": common[0][0] if common else ""}
    shape["infotable_rows_kept"] = rows
    shape["cusips"] = len(out)
    return {"period": period, "shape": shape, "cusips": out}


def build_13f(root: str = DEFAULT_ROOT, guard: Guard | None = None) -> dict:
    """Download (once) and aggregate both periods; cache the aggregate, not the 360MB TSV."""
    agg_path = os.path.join(root, "13f_aggregate.json")
    cached = _read_json(agg_path)
    if cached and cached.get("periods") == [PERIOD_PRIOR, PERIOD_CURR]:
        return cached
    out = {"periods": [PERIOD_PRIOR, PERIOD_CURR], "shape": {}, "by_period": {}}
    for period, window in ((PERIOD_PRIOR, WINDOW_PRIOR), (PERIOD_CURR, WINDOW_CURR)):
        log(root, f"13f: downloading {window}")
        path = download_dataset(root, window, guard)
        log(root, f"13f: aggregating {period} from {os.path.basename(path)}")
        agg = aggregate_13f(path, period)
        out["by_period"][period] = agg["cusips"]
        out["shape"][period] = agg["shape"]
        log(root, f"13f: {period} -> {agg['shape']['cusips']} CUSIPs, "
                  f"{agg['shape']['filers']} filers, "
                  f"{agg['shape']['infotable_rows_kept']} share rows")
    _atomic_write_json(agg_path, out)
    return out


# --------------------------------------------------------------------------------------------
# Per-ticker fetch legs. All three cache to disk and resume.
# --------------------------------------------------------------------------------------------

def cik_map(root: str = DEFAULT_ROOT, guard: Guard | None = None) -> dict:
    path = os.path.join(root, "cik_map.json")
    cached = _read_json(path)
    if cached:
        return cached
    guard = guard or Guard()
    data = _get(TICKERS_URL, guard, as_json=True) or {}
    out = {}
    for row in data.values():
        out[str(row["ticker"]).upper()] = {"cik": int(row["cik_str"]),
                                           "title": row.get("title") or ""}
    _atomic_write_json(path, out)
    return out


def submissions(root: str, ticker: str, cik: int, guard: Guard) -> dict | None:
    """Cached submissions JSON — shared by the CUSIP leg and the Form 4 leg."""
    path = os.path.join(root, "submissions", f"{ticker}.json")
    cached = _read_json(path)
    if cached is not None:
        return cached
    data = _get(SUBMISSIONS_URL.format(cik=cik), guard, as_json=True)
    if data is None:
        return None
    recent = data.get("filings", {}).get("recent", {})
    slim = {"cik": cik, "form": recent.get("form", []),
            "accessionNumber": recent.get("accessionNumber", []),
            "primaryDocument": recent.get("primaryDocument", []),
            "filingDate": recent.get("filingDate", [])}
    _atomic_write_json(path, slim)
    return slim


def fetch_cusip(root: str, ticker: str, cik: int, guard: Guard) -> dict:
    """Rung 1 of the join ladder: the company's own SC 13D/G filings carry its CUSIP."""
    sub = submissions(root, ticker, cik, guard)
    if not sub:
        return {"cusip": None, "rung": "no_submissions", "docs_read": 0}
    docs = [(a, d) for f, a, d in zip(sub["form"], sub["accessionNumber"],
                                      sub["primaryDocument"])
            if str(f).startswith("SC 13")]
    seen = collections.Counter()
    read = 0
    for acc, doc in docs[:MAX_13G_DOCS]:
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
               f"{acc.replace('-', '')}/{doc}")
        try:
            text = _get(url, guard)
        except Throttled:
            raise
        except Exception:
            continue
        if not text:
            continue
        read += 1
        found = cusips_in_document(text)
        if found:
            # One filing votes once, for the CUSIP it names most often — a cover page repeats
            # the subject's CUSIP in the header of every page, so frequency inside a document
            # is signal, but a single document should not outvote the others.
            seen[collections.Counter(found).most_common(1)[0][0]] += 1
    if not seen:
        return {"cusip": None, "rung": "no_cusip_in_13g", "docs_read": read,
                "sc13_filings": len(docs)}
    ranked = seen.most_common()
    # TIGHTENED 2026-08-10, before the full-universe run, and recorded as a tightening
    # (PREREG §8 permits tightening, not loosening). A company that is ITSELF an asset manager
    # files SC 13Gs ABOUT OTHER ISSUERS, and EDGAR's submissions feed for a CIK carries the
    # filings it MADE as well as the ones naming it as subject — this is edgar13d.py's
    # filer-vs-subject contamination in a new place. PFG came back with six candidate CUSIPs
    # holding one vote each, and `most_common(1)` would have resolved that six-way tie by
    # dictionary insertion order. A tie is not a mode: require the leader to out-poll the
    # runner-up strictly, otherwise fall through to the name rung and let the anchor judge.
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return {"cusip": None, "rung": "cusip_13g_tied", "docs_read": read,
                "sc13_filings": len(docs), "candidates": len(ranked),
                "votes": ranked[0][1]}
    return {"cusip": ranked[0][0], "rung": "cusip_13g", "docs_read": read,
            "sc13_filings": len(docs), "votes": ranked[0][1],
            "candidates": len(ranked)}


_XBRL_SHARES = ["EntityCommonStockSharesOutstanding",
                "WeightedAverageNumberOfDilutedSharesOutstanding"]
_XBRL_NI = ["NetIncomeLoss"]
_XBRL_CFO = ["NetCashProvidedByUsedInOperatingActivities",
             "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
_XBRL_ASSETS = ["Assets"]


def _annual(facts: dict, concepts, unit_hint=None) -> list:
    """Recent-first [(end, value)] for the first matching concept.

    Same shape as `valuation/data/edgar.py::_annual_series`, deliberately: this is a read-only
    reimplementation in a script rather than an edit to a shipped module (PREREG §1).
    """
    for ns in ("us-gaap", "dei", "ifrs-full"):
        block = facts.get("facts", {}).get(ns, {})
        for c in concepts:
            if c not in block:
                continue
            units = block[c].get("units", {})
            for uk in ([unit_hint] if unit_hint else []) + ["USD", "shares"] + list(units):
                if not uk or uk not in units:
                    continue
                rows = [x for x in units[uk]
                        if str(x.get("form", "")).startswith("10-K")
                        and x.get("fp") == "FY" and x.get("val") is not None and x.get("end")]
                if not rows:
                    rows = [x for x in units[uk] if x.get("val") is not None and x.get("end")]
                by_end = {}
                for x in rows:
                    by_end[x["end"]] = float(x["val"])
                series = sorted(by_end.items(), key=lambda kv: kv[0], reverse=True)
                if series:
                    return series
    return []


def extract_xbrl(facts: dict) -> dict:
    """PREREG §4.5 — issuance (capital_discipline) and accruals (quality, not this theme)."""
    out = {"share_issuance": None, "accruals_q": None, "shares_points": 0,
           "issuance_end": None, "accruals_end": None}
    shares = _annual(facts, _XBRL_SHARES, "shares")
    out["shares_points"] = len(shares)
    if len(shares) >= 2 and shares[1][1]:
        out["share_issuance"] = shares[0][1] / shares[1][1] - 1.0
        out["issuance_end"] = shares[0][0]

    ni = dict(_annual(facts, _XBRL_NI, "USD"))
    cfo = dict(_annual(facts, _XBRL_CFO, "USD"))
    assets = dict(_annual(facts, _XBRL_ASSETS, "USD"))
    common = sorted(set(ni) & set(cfo) & set(assets), reverse=True)
    if common:
        end = common[0]
        if assets[end]:
            # Sloan accruals, oriented higher = better, as fundamental_panel builds it.
            out["accruals_q"] = -((ni[end] - cfo[end]) / assets[end])
            out["accruals_end"] = end
    return out


def fetch_xbrl(root: str, ticker: str, cik: int, guard: Guard) -> dict:
    facts = _get(FACTS_URL.format(cik=cik), guard, as_json=True)
    if facts is None:
        return {"share_issuance": None, "accruals_q": None, "shares_points": 0,
                "issuance_end": None, "accruals_end": None, "no_facts": True}
    return extract_xbrl(facts)


def fetch_insider(root: str, ticker: str, guard: Guard, detail=None) -> dict:
    """The EXISTING fixed Form 4 scraper, called unmodified (PREREG §4.6).

    `guard.wait()` is called once before handing off, so the scraper's own bursts sit inside
    this run's overall pacing rather than beside it.
    """
    if detail is None:
        from valuation.screener import insider as _ins
        detail = _ins.insider_detail
    guard.wait()
    d = detail(ticker, days=INSIDER_DAYS)
    seen = int(d.get("form4_seen") or 0)
    return {"insider_score": d.get("score"), "form4_seen": seen,
            "parsed": int(d.get("parsed") or 0),
            "parse_failures": int(d.get("parse_failures") or 0),
            "fetch_failures": int(d.get("fetch_failures") or 0),
            "form4_truncated": bool(seen > MAX_FORM4_PER_NAME),
            "error": (d.get("error") or "")[:200]}


# --------------------------------------------------------------------------------------------
# The fetch driver.
# --------------------------------------------------------------------------------------------

_LEGS = ("cusip", "xbrl", "insider")


def leg_path(root: str, leg: str, ticker: str) -> str:
    return os.path.join(root, leg, f"{ticker}.json")


def fetch_all(root: str = DEFAULT_ROOT, legs=_LEGS, limit: int | None = None,
              guard: Guard | None = None, slice_i: int = 0, slice_n: int = 1) -> dict:
    """Fetch every leg for every served name, resumably.

    `slice_i/slice_n` splits the universe into disjoint interleaved shards so several
    processes can run at once. The cost here is LATENCY, not the rate limit: SEC publishes a
    ~10 req/s ceiling and one serial process only reaches ~3 req/s, so a shard runs at a
    higher per-process interval and the FLEET still sits under the ceiling. Shards never
    collide: each keeps its own manifest, and the durable cache is the per-leg payload file,
    written atomically — so `done` also accepts "the payload is already on disk", which makes
    a lost or racing manifest a slowdown rather than a correctness problem.
    """
    served = load_served()
    if limit:
        served = served[:limit]
    if slice_n > 1:
        served = [r for i, r in enumerate(served) if i % slice_n == slice_i]
    guard = guard or Guard()
    suffix = "" if slice_n == 1 else f"_{slice_i}_{slice_n}"
    manifest = Manifest(os.path.join(root, f"manifest{suffix}.json"))
    ciks = cik_map(root, guard)
    stats = {leg: {"done": 0, "fetched": 0, "skipped_no_cik": 0} for leg in legs}

    for i, row in enumerate(served):
        tkr = row["ticker"]
        info = ciks.get(tkr.upper())
        for leg in legs:
            key = f"{leg}:{tkr}"
            if manifest.done(key) or os.path.exists(leg_path(root, leg, tkr)):
                stats[leg]["done"] += 1
                continue
            if leg in ("cusip", "xbrl") and not info:
                # No EDGAR CIK at all — a real, terminal answer for a foreign issuer that does
                # not file with the SEC, not a failure to be retried forever.
                _atomic_write_json(leg_path(root, leg, tkr), {"no_cik": True})
                manifest.mark(key, "no_data", reason="no_cik")
                stats[leg]["skipped_no_cik"] += 1
                continue
            try:
                if leg == "cusip":
                    payload = fetch_cusip(root, tkr, info["cik"], guard)
                elif leg == "xbrl":
                    payload = fetch_xbrl(root, tkr, info["cik"], guard)
                else:
                    payload = fetch_insider(root, tkr, guard)
            except Throttled as e:
                log(root, f"{leg} {tkr}: THROTTLED ({e}) — not recorded, will retry")
                continue
            except SystemExit:
                raise
            except Exception as e:
                log(root, f"{leg} {tkr}: {type(e).__name__}: {e} — not recorded, will retry")
                continue
            _atomic_write_json(leg_path(root, leg, tkr), payload)
            manifest.mark(key, "complete")
            stats[leg]["fetched"] += 1
        if (i + 1) % 25 == 0:
            log(root, f"fetch: {i + 1}/{len(served)} names "
                      f"({', '.join(f'{k} {v['fetched']}+{v['done']}' for k, v in stats.items())}) "
                      f"calls={guard.calls} throttles={guard.throttles}")
    log(root, f"fetch: DONE {len(served)} names, calls={guard.calls}, "
              f"throttles={guard.throttles}")
    return {"names": len(served), "stats": stats, "calls": guard.calls,
            "throttles": guard.throttles}


# --------------------------------------------------------------------------------------------
# Measurement. Offline: `report` makes ZERO network calls, which is the V2F structural lesson —
# a measurement that consumes the resource it measures reports on its own exhaustion.
# --------------------------------------------------------------------------------------------

def _zscore(values: dict) -> dict:
    xs = [v for v in values.values() if v is not None and math.isfinite(v)]
    if len(xs) < 2:
        return {k: None for k in values}
    mu = statistics.fmean(xs)
    sd = statistics.pstdev(xs)
    if sd <= 0:
        return {k: None for k in values}     # a constant column zscores to nothing — by design
    return {k: ((v - mu) / sd if (v is not None and math.isfinite(v)) else None)
            for k, v in values.items()}


def join_13f(root: str, served: list, agg: dict) -> dict:
    """The two-rung ladder plus the anchor. Returns per-ticker join detail."""
    curr = agg["by_period"].get(PERIOD_CURR, {})
    prior = agg["by_period"].get(PERIOD_PRIOR, {})

    by_name = collections.defaultdict(set)
    for cusip, rec in curr.items():
        n = normalise_name(rec.get("name"))
        if n:
            by_name[n].add(cusip)

    ciks = _read_json(os.path.join(root, "cik_map.json")) or {}
    out = {}
    for row in served:
        tkr = row["ticker"]
        detail = {"rung": "unmatched", "cusip": None, "anchor": None, "holders": None,
                  "holders_prior": None, "sm_breadth": None, "inst_accum": None}
        cached = _read_json(leg_path(root, "cusip", tkr)) or {}
        cusip = cached.get("cusip")
        rung = "cusip_13g" if cusip and cusip in curr else None
        if cusip and cusip not in curr:
            # A valid CUSIP nobody reported holding is a real answer about the name, not a
            # broken join; it is recorded separately so it cannot be read as a fetch failure.
            detail["cusip_not_held"] = cusip
            cusip = None
        if not cusip:
            for cand in (row.get("name"), (ciks.get(tkr.upper()) or {}).get("title")):
                n = normalise_name(cand)
                if not n:
                    continue
                hits = by_name.get(n) or set()
                if len(hits) == 1:
                    cusip, rung = next(iter(hits)), "name_exact"
                    break
                if len(hits) > 1:
                    detail["rung"] = "ambiguous"          # a failure, never a coin flip
                    break
        if not cusip:
            out[tkr] = detail
            continue

        rec = curr[cusip]
        mc = row.get("market_cap")
        anchor = (rec["value"] / mc) if (mc and mc > 0) else None
        detail.update({"cusip": cusip, "rung": rung, "anchor": anchor,
                       "holders": rec["holders"], "issuer": rec["name"],
                       "value": rec["value"], "shares": rec["shares"]})
        if anchor is None or not (0 < anchor <= ANCHOR_MAX):
            detail["rung"] = "anchor_failed"
            out[tkr] = detail
            continue
        if rec["holders"] < MIN_HOLDERS:
            # A single reporting holder is not breadth, and on a megacap it is a mis-join.
            detail["rung"] = "too_few_holders"
            out[tkr] = detail
            continue
        p = prior.get(cusip)
        if p and p["holders"] > 0:
            detail["holders_prior"] = p["holders"]
            detail["sm_breadth"] = rec["holders"] / p["holders"] - 1.0
        if p and p["shares"] > 0:
            detail["inst_accum"] = rec["shares"] / p["shares"] - 1.0
        out[tkr] = detail
    return out


def build_columns(root: str = DEFAULT_ROOT) -> dict:
    """Every measured-only theme column for the 500 served rows. No network."""
    served = load_served()
    agg = _read_json(os.path.join(root, "13f_aggregate.json"))
    if not agg:
        raise SystemExit("13F aggregate missing — run `fetch` first")
    join = join_13f(root, served, agg)

    raw = {"inst_accum": {}, "sm_breadth": {}, "neg_issuance": {}, "accruals_q": {},
           "insider_score": {}}
    meta = {}
    for row in served:
        tkr = row["ticker"]
        j = join.get(tkr, {})
        raw["inst_accum"][tkr] = j.get("inst_accum")
        raw["sm_breadth"][tkr] = j.get("sm_breadth")

        x = _read_json(leg_path(root, "xbrl", tkr)) or {}
        si = x.get("share_issuance")
        raw["neg_issuance"][tkr] = (-si) if si is not None else None
        raw["accruals_q"][tkr] = x.get("accruals_q")

        ins = _read_json(leg_path(root, "insider", tkr)) or {}
        raw["insider_score"][tkr] = ins.get("insider_score")
        meta[tkr] = {"join_rung": j.get("rung"), "anchor": j.get("anchor"),
                     "holders": j.get("holders"),
                     "form4_seen": ins.get("form4_seen"),
                     "form4_truncated": ins.get("form4_truncated"),
                     "shares_points": x.get("shares_points")}

    z = {k: _zscore(v) for k, v in raw.items()}
    themes = {}
    tickers = [r["ticker"] for r in served]

    def _mean(*cols):
        out = {}
        for t in tickers:
            vals = [c.get(t) for c in cols]
            vals = [v for v in vals if v is not None and math.isfinite(v)]
            out[t] = (sum(vals) / len(vals)) if vals else None
        return out

    themes["institutional"] = _mean(z["inst_accum"], z["sm_breadth"])   # factors.py:267
    themes["capital_discipline"] = _mean(z["neg_issuance"])             # factors.py:254
    themes["insider"] = {t: ((raw["insider_score"][t] - 50.0) / 25.0
                             if raw["insider_score"][t] is not None else None)
                         for t in tickers}                              # factors.py:271
    # Reported against the theme it actually feeds, not the one the brief named.
    themes["quality_accruals_input"] = _mean(z["accruals_q"])
    return {"served": served, "join": join, "raw": raw, "z": z, "themes": themes,
            "meta": meta, "shape": agg.get("shape", {})}


def _cov(values: dict, n: int) -> dict:
    live = [v for v in values.values() if v is not None and math.isfinite(v)]
    distinct = len({round(v, 12) for v in live})
    frac = len(live) / n if n else 0.0
    return {"n": n, "covered": len(live), "coverage": frac, "distinct_values": distinct,
            "above_coverage_floor": frac >= COVERAGE_FLOOR,
            "above_min_coverage": frac >= MIN_COVERAGE,
            "usable": frac >= MIN_COVERAGE and distinct >= MIN_DISTINCT}


def _spearman(pairs: list) -> float | None:
    pairs = [(a, b) for a, b in pairs
             if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
    if len(pairs) < 3:
        return None

    def _rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = _rank([p[0] for p in pairs]), _rank([p[1] for p in pairs])
    n = len(pairs)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return (num / (da * db)) if da > 0 and db > 0 else None


def report(root: str = DEFAULT_ROOT, out: str | None = None) -> dict:
    built = build_columns(root)
    served = built["served"]
    n = len(served)
    themes = built["themes"]

    cov = {name: _cov(vals, n) for name, vals in themes.items()}
    inputs = {name: _cov(vals, n) for name, vals in built["raw"].items()}

    rungs = collections.Counter(j.get("rung") for j in built["join"].values())
    anchors = [j["anchor"] for j in built["join"].values()
               if j.get("anchor") is not None and j.get("cusip")]
    matched = sum(1 for j in built["join"].values() if j.get("cusip"))
    anchor_pass = sum(1 for a in anchors if 0 < a <= ANCHOR_MAX)

    holders = [(j.get("holders"), r.get("market_cap"))
               for r, j in ((r, built["join"].get(r["ticker"], {})) for r in served)]
    b3_rho = _spearman([(h, math.log(m)) for h, m in holders
                        if h and m and m > 0])
    max_holders = max([h for h, _ in holders if h] or [0])

    scores = [v for v in built["raw"]["insider_score"].values() if v is not None]
    at_neutral = sum(1 for v in scores if abs(v - 50.0) < 1e-9)
    truncated = sum(1 for m in built["meta"].values() if m.get("form4_truncated"))

    bounds = {
        "B1_institutional_coverage_ge_0.30": cov["institutional"]["coverage"] >= MIN_COVERAGE,
        "B2_anchor_pass_rate_ge_0.95": (anchor_pass / matched >= 0.95) if matched else False,
        "B3_external_validity": bool(max_holders >= 2000 and (b3_rho or 0) > 0.30),
        "B4_capital_discipline_usable": cov["capital_discipline"]["usable"],
        "B6_insider_distinct_ge_10": cov["insider"]["distinct_values"] >= 10,
    }
    payload = {
        "prereg": "PREREG_v2g_live_theme_sources.md",
        "snapshot": SNAPSHOT,
        "periods": {"current": PERIOD_CURR, "prior": PERIOD_PRIOR},
        "n_served": n,
        "floors": {"COVERAGE_FLOOR": COVERAGE_FLOOR, "MIN_COVERAGE": MIN_COVERAGE,
                   "MIN_DISTINCT": MIN_DISTINCT},
        "theme_coverage": cov,
        "input_coverage": inputs,
        "join": {"matched": matched, "rungs": dict(rungs),
                 "anchor_pass": anchor_pass,
                 "anchor_pass_rate": (anchor_pass / matched) if matched else None,
                 "anchor_median": statistics.median(anchors) if anchors else None},
        "external_validity": {"max_holders": max_holders,
                              "spearman_breadth_vs_log_mcap": b3_rho},
        "insider_shape": {"scored": len(scores), "exactly_neutral": at_neutral,
                          "neutral_share": (at_neutral / len(scores)) if scores else None,
                          "names_truncated_at_40_form4": truncated},
        "dataset_shape": built["shape"],
        "bounds": bounds,
    }
    if out:
        _atomic_write_json(out, payload)
    return payload


def render(p: dict) -> str:
    L = []
    A = L.append
    A("V2G — FREE LIVE SOURCES FOR THE THREE DEAD THEMES (measured only, nothing shipped)")
    A(f"pre-registration: {p['prereg']}")
    A(f"served universe : {p['n_served']} rows from {p['snapshot']}")
    A(f"13F periods     : {p['periods']['prior']} -> {p['periods']['current']}")
    A("")
    A("THEME COVERAGE vs the 500 served rows")
    A(f"  floors: coverage>={p['floors']['MIN_COVERAGE']:.2f} (adoption-relevant), "
      f">={p['floors']['COVERAGE_FLOOR']:.2f} (not-empty), "
      f"distinct>={p['floors']['MIN_DISTINCT']}")
    A(f"  {'theme':<26} {'covered':>9} {'coverage':>9} {'distinct':>9}  verdict")
    for name, c in p["theme_coverage"].items():
        verdict = "USABLE" if c["usable"] else (
            "DEGENERATE" if c["distinct_values"] < MIN_DISTINCT else "BELOW FLOOR")
        A(f"  {name:<26} {c['covered']:>9} {c['coverage']:>9.3f} "
          f"{c['distinct_values']:>9}  {verdict}")
    A("")
    A("INPUT COVERAGE (the columns the themes are built from)")
    for name, c in p["input_coverage"].items():
        A(f"  {name:<26} {c['covered']:>9} {c['coverage']:>9.3f} {c['distinct_values']:>9}")
    A("")
    j = p["join"]
    A(f"13F JOIN LADDER — {j['matched']} of {p['n_served']} names carry a CUSIP")
    for rung, k in sorted(j["rungs"].items(), key=lambda kv: -kv[1]):
        A(f"  {str(rung):<26} {k:>5}")
    if j["anchor_pass_rate"] is not None:
        A(f"  anchor (value/mktcap in (0,{ANCHOR_MAX}]): "
          f"{j['anchor_pass']}/{j['matched']} = {j['anchor_pass_rate']:.3f}, "
          f"median {j['anchor_median']:.3f}")
    ev = p["external_validity"]
    rho = ev["spearman_breadth_vs_log_mcap"]
    rho_s = "n/a" if rho is None else format(rho, "+.3f")
    A(f"  external validity: max holders {ev['max_holders']}, "
      f"Spearman(breadth, log mcap) {rho_s}")
    A("")
    ish = p["insider_shape"]
    share = ish["neutral_share"]
    share_s = "n/a" if share is None else format(share, ".1%")
    A(f"INSIDER SHAPE — {ish['scored']} scored, {ish['exactly_neutral']} exactly 50.0 "
      f"({share_s}), {ish['names_truncated_at_40_form4']} names truncated "
      f"at {MAX_FORM4_PER_NAME} filings")
    A("")
    A("PRE-COMMITTED BOUNDS")
    for k, v in p["bounds"].items():
        A(f"  {'HELD' if v else 'FAILED':<7} {k}")
    A("")
    A("Nothing above reaches the composite. Adoption is a separate decision that needs the cost")
    A("measurement and the held-out gate, and under Amendment 1 it would open a new vintage and")
    A("reset the entire accrued forward clock. See PREREG section 1.")
    return "\n".join(L)


def status(root: str = DEFAULT_ROOT) -> dict:
    m = Manifest(os.path.join(root, "manifest.json"))
    per = collections.Counter(k.split(":", 1)[0] for k in m.data)
    return {"units": len(m.data), "by_leg": dict(per),
            "complete": m.count("complete"), "no_data": m.count("no_data"),
            "aggregate_built": os.path.exists(os.path.join(root, "13f_aggregate.json"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("command", choices=["fetch", "thirteenf", "report", "status"])
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--legs", default=",".join(_LEGS))
    ap.add_argument("--slice", default="0/1", help="i/n — disjoint shard for parallel runs")
    ap.add_argument("--interval", type=float, default=None,
                    help="per-process pacing; raise it when running several shards")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.command == "thirteenf":
        agg = build_13f(a.root)
        print(json.dumps(agg["shape"], indent=2))
    elif a.command == "fetch":
        build_13f(a.root)
        legs = tuple(x for x in a.legs.split(",") if x)
        i, n = (int(x) for x in a.slice.split("/"))
        guard = Guard(min_interval=a.interval) if a.interval else None
        print(json.dumps(fetch_all(a.root, legs=legs, limit=a.limit, guard=guard,
                                   slice_i=i, slice_n=n), indent=2))
    elif a.command == "report":
        p = report(a.root, out=a.out or os.path.join("data", "free_analysis", "V2G_LIVE_THEMES.json"))
        print(render(p))
    else:
        print(json.dumps(status(a.root), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
