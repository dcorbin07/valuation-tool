"""
WRDS PULL — chunked, resumable, manifested. Collection only, ZERO TRIALS.

    python -m scripts.wrds_pull --product ibes_det_epsus
    python -m scripts.wrds_pull --product crsp_delist
    python -m scripts.wrds_pull --product comp_pit
    python -m scripts.wrds_pull --verify

--------------------------------------------------------------------------------------------
THE LAW.

Licensed vendor rows are written under `D:\\wrds` and NOWHERE else. Nothing under this root is
ever committed, mirrored into the repo, or rendered on a public surface. What leaves this lane
is derived statistics -- row counts, spans, byte sizes, sha256 -- in `WRDS_CENSUS.md` and the
manifest summary. That is the same split the ThetaData harvest ran under and it is not
negotiable here either.

--------------------------------------------------------------------------------------------
RESUMABLE OR IT IS WORTHLESS -- the harvest's rule, inherited whole.

One unit = one (product, chunk). The payload is written atomically (tmp + os.replace) BEFORE its
manifest line is appended and fsynced, so a kill can lose a unit's RECORD but can never leave a
half-written payload recorded as complete. Re-running re-does any unit whose payload is absent or
whose size disagrees with its record. The chain harvest lost twelve hours to a checkpoint loop
that died while workers kept going; the shape of the fix is copied deliberately.

Chunking is by YEAR for the large products. That is not arbitrary: WRDS enforces query limits and
a 34.5M-row single SELECT is the kind of request that gets killed server-side an hour in, which
is the most expensive way to discover a limit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import wrds_client as W                            # noqa: E402

SCHEMA = 1

#: product -> how to chunk it. `year_col` None means a single unchunked pull (small tables).
PRODUCTS = {
    "ibes_det_epsus": {
        "lib": "ibes", "table": "det_epsus", "year_col": "anndats",
        "why": "IBES DETAIL estimates: per-analyst, per-revision, with announce/revision dates. "
               "This is the D6 unpark -- point-in-time estimate revisions.",
    },
    "ibes_actu_epsus": {
        "lib": "ibes", "table": "actu_epsus", "year_col": "anndats",
        "why": "IBES actuals (UNADJUSTED) -- pairs with detu_epsus, NOT with det_epsus.",
    },
    # THE PULL WAS INTERNALLY INCONSISTENT UNTIL THIS ROW EXISTED, and the D6 ledger note had
    # already written down the exact hazard: "det_epsus (split-adjusted) and detu_epsus
    # (unadjusted) are NOT interchangeable -- an adjusted estimate against an unadjusted actual
    # is a units error that reads as a surprise". The pull then took `det_epsus` (ADJUSTED) and
    # `actu_epsus` (UNADJUSTED), i.e. the warned-against pairing, because the two file names
    # differ by ONE LETTER and only one of the four names carries the `u`.
    #
    # Nothing was computed from it, so nothing is retracted -- but a surprise built from the pull
    # as it stood would have been wrong by every split in the sample, silently, in a direction
    # that varies by name. `act_epsus` is the ADJUSTED actual and is the counterpart `det_epsus`
    # needs; `actu_epsus` is kept because it is the counterpart `detu_epsus` would need.
    # A register must still DECLARE which pair it uses.
    # ---- W-28: Peters-Taylor Total Q, and the two tables its DATED join needs.
    #
    # `totalq.total_q` is ANNUAL by construction -- Peters-Taylor perpetual inventory on annual
    # flows with annual depreciation -- so the quarterly `comp_pit` already on disk is NOT a
    # substitute, and W-28's own deviation rule forbids substituting for a frozen parameter.
    #
    # The other two are pulled BECAUSE the join must be dated. `crsp.ccmxpf_lnkhist` and every
    # CCM variant are DENIED on this account, and `comp.security.tic` is an UNDATED ticker map --
    # the hazard `W-3b` measured when it found `oftic` is a lease and 17.7% of its rows are a
    # different company. `crsp.stocknames` supplies the dated first hop; `comp.security` supplies
    # the cusip -> gvkey second hop, which needs no dating because a cusip is stable.
    "totalq_total_q": {
        "lib": "totalq", "table": "total_q", "year_col": "datadate",
        "why": "Peters-Taylor Total Q -- ANNUAL. q_tot plus the intangible-capital components.",
    },
    "crsp_stocknames": {
        "lib": "crsp", "table": "stocknames", "year_col": "",
        "why": "DATED ticker -> cusip/permno history. The first hop, and the only one a ticker "
               "being a lease can corrupt.",
    },
    "comp_security": {
        "lib": "comp", "table": "security", "year_col": "",
        "why": "cusip -> gvkey. Undated by design: a cusip is a stable security identifier, so "
               "only the ticker hop needs dating.",
    },
    "ibes_act_epsus": {
        "lib": "ibes", "table": "act_epsus", "year_col": "anndats",
        "why": "IBES actuals (ADJUSTED) -- the counterpart det_epsus needs; see the note above.",
    },
    "ibes_statsum_epsus": {
        "lib": "ibes", "table": "statsum_epsus", "year_col": "statpers",
        "why": "IBES summary by statistical period -- consensus level and dispersion.",
    },
    "ibes_id": {
        "lib": "ibes", "table": "id", "year_col": None,
        "why": "IBES identifier table -- the ticker/cusip bridge any join needs.",
    },
    "crsp_delist": {
        "lib": "crsp_a_stock", "table": "dsedelist", "year_col": None,
        "why": "CRSP delisting returns -- the survivorship cross-check against our ACTIONS mask.",
    },
    "crsp_msedelist": {
        "lib": "crsp_a_stock", "table": "msedelist", "year_col": None,
        "why": "CRSP monthly delisting returns.",
    },
    "crsp_dsenames": {
        "lib": "crsp_a_stock", "table": "dsenames", "year_col": None,
        "why": "CRSP name history -- PERMNO/ticker over time, the identity spine.",
    },
    "comp_pit": {
        "lib": "comp", "table": "co_ifndq", "year_col": "datadate",
        "why": "Compustat point-in-time quarterly (unrestated, with _dc data codes) -- "
               "preliminary vs final filings.",
    },
    # ---- OOS1: the pre-2009 holdout's three tables. Two new optional spec keys below.
    #
    # `cols` and `years` are ADDITIVE and default to the historical behaviour, so every product
    # above is bit-identical. They exist because these three tables cannot be pulled with
    # `select *` over every year:
    #
    #   * `comp.fundq` carries **648 columns**. `select *` would bank a multiple of what the
    #     five-theme model reads, and the point of `fundq` over the already-banked `co_ifndq` is
    #     ONE column -- `rdq`, the earnings announcement date, which is the availability date
    #     `MC12` measured `co_ifndq` to lack entirely.
    #   * `crsp_a_stock.dsf` is **62,672,078 rows for 1972-2008 alone** (measured, not estimated).
    #     Unscoped that is every column of every US daily price since 1925.
    #
    # `cols` is INTERSECTED with the table's real column list rather than trusted, so a renamed
    # or absent field is reported instead of raising mid-pull -- and the intersection is recorded
    # in the manifest so a reader can see what was actually banked.
    "comp_fundq": {
        "lib": "comp", "table": "fundq", "year_col": "datadate",
        "years": (1971, 2026),
        "cols": ["gvkey", "datadate", "rdq", "fyearq", "fqtr", "datacqtr", "datafqtr",
                 "indfmt", "datafmt", "popsrc", "consol", "cusip", "tic", "conm", "curcdq",
                 "atq", "ceqq", "seqq", "ibq", "ibcomq", "niq", "piq", "xrdq", "revtq", "saleq", "cogsq",
                 "xsgaq", "xintq", "xoprq", "oiadpq", "oibdpq", "dpq", "txtq", "dlttq", "dlcq",
                 "ppentq", "ppegtq", "invtq", "rectq", "cheq", "actq", "lctq", "ltq", "pstkq",
                 "mibq", "icaptq", "gpq", "cshoq", "cshprq", "prccq", "ajexq", "epspxq",
                 "oancfy", "capxy", "dvy", "sstky", "prstkcy", "ivncfy", "fincfy"],
        "why": "OOS1: quarterly fundamentals WITH `rdq`, the availability date `co_ifndq` has "
               "none of. 1,234,665 rows in 1972-2008, of which 835,478 carry a non-null `rdq`.",
    },
    "crsp_dsf": {
        "lib": "crsp_a_stock", "table": "dsf", "year_col": "date",
        "years": (1971, 2024),
        "cols": ["permno", "date", "prc", "ret", "retx", "vol", "shrout", "cfacpr", "cfacshr"],
        "why": "OOS1: daily prices. DAILY rather than `msf` because `high_prox` is proximity to "
               "a 252-day DAILY high -- on monthly data it becomes a 12-month approximation and "
               "the frozen model is no longer frozen for that column.",
    },
    "crsp_dsp500list": {
        "lib": "crsp_a_indexes", "table": "dsp500list", "year_col": None,
        "why": "OOS1: S&P 500 membership spells, for the pre-SPY benchmark. 2,064 rows carrying "
               "EXACTLY `start`, `ending`, `permno` -- effective dates and NO announcement date, "
               "which is W-17's K1 firing condition confirmed at source.",
    },
}


def product_root(product: str, root: str = "") -> str:
    p = os.path.join(W.raw_root(root), product)
    os.makedirs(p, exist_ok=True)
    return p


def manifest_path(root: str = "") -> str:
    return os.path.join(W.raw_root(root), "manifest.jsonl")


def load_manifest(root: str = "") -> dict:
    out = {}
    p = manifest_path(root)
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue            # torn final line: that unit simply re-pulls
            out[f"{r['product']}|{r['chunk']}"] = r
    return out


def append_manifest(rec: dict, root: str = "") -> None:
    with open(manifest_path(root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())        # the checkpoint must survive a hard kill


def _replace_retry(tmp: str, dst: str, tries: int = 8) -> None:
    """os.replace, retried on the Windows AV race.

    Measured here 2026-08-24: `comp_pit` 2003 failed with
    `PermissionError [WinError 32] ... being used by another process` on a freshly written .pkl,
    which is the scanner still holding the temp file, not corruption and not a data problem.

    THIRD TIME THIS EXACT RACE HAS BEEN HIT IN THIS PROJECT and the second time in this lane --
    `freeze_chain_store.py` already carries the identical helper, written after the same failure
    ~3,000 files into the first chain freeze. It did not travel with the code. Any writer on this
    machine that does tmp + os.replace needs it.

    It RAISES rather than skipping if the file still will not land: a skipped chunk is a silent
    hole in a pull whose whole point is completeness.

    A MISSING tmp is a DIFFERENT failure and is deliberately NOT retried here: retrying
    `os.replace` on a file that no longer exists can only fail eight more times. It is raised
    straight through to the caller's retry loop, which re-fetches the chunk.

    A CORRECTION AGAINST THIS DOCSTRING'S OWN FIRST DRAFT, kept because the error is the useful
    part. It said `FileNotFoundError [WinError 2]` on `comp_pit` 2022 was "the same scanner,
    quarantining rather than merely holding". **THAT CAUSE WAS ASSERTED, NOT MEASURED, AND THE
    MEASURED CAUSE IS AN OPERATOR ERROR OF MINE: two `wrds_pull` processes were running against
    the same product at once**, so one replaced the tmp the other was about to replace. WinError 2
    and WinError 32 are exactly what that looks like from either side. The 2003 WinError 32 that
    prompted this helper WAS single-process and is still the scanner race; the later ones were
    not. **A file-layer symptom does not identify its cause, and "the antivirus did it" is the
    most available explanation rather than the demonstrated one.** The concurrency hole itself is
    closed by `_acquire_lock` rather than by tolerating it here.
    """
    for k in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.25 * (k + 1))


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def needs_pull(product: str, chunk: str, man: dict, root: str = "") -> bool:
    rec = man.get(f"{product}|{chunk}")
    if not rec or rec.get("status") != "ok":
        return True
    p = os.path.join(product_root(product, root), f"{product}_{chunk}.pkl")
    if not os.path.exists(p):
        return True
    return os.path.getsize(p) != rec.get("bytes")


#: Chunk key for rows whose chunk column is NULL. Not a year, deliberately -- naming it "0000"
#: or similar would let it sort in among the years and read as a data range.
NULLDATE = "nulldate"


def chunks_for(db, product: str) -> list:
    """Chunk keys, derived from the DATA rather than assumed.

    A hard-coded year range would silently drop a year the vendor added, and silently spend
    queries on years that do not exist. Ask.

    AND A ROW WITH NO DATE BELONGS TO NO YEAR, WHICH COST 102,213 ROWS BEFORE IT WAS CAUGHT.
    Every chunk predicate is `>= Jan 1 and < Jan 1`, so a NULL date satisfies neither and the row
    is dropped by EVERY chunk. Measured on `ibes.actu_epsus`: the census counted 1,323,271 rows,
    the 51 year-chunks summed to 1,221,058, and the gap is exactly the 102,213 rows whose
    `anndats` is NULL. **The hole is silent and it is in the flattering direction -- a pull that
    looks complete, with a manifest full of `ok`.**

    It was found by RECONCILING the summed chunk rows against the census `count(*)`, not by
    anything raising, and the mechanism was then confirmed by control rather than assumed:
    `det_epsus` and `statsum_epsus` reconcile EXACTLY and carry ZERO nulls on their own chunk
    columns. A `nulldate` chunk closes it, and it is emitted only where such rows actually exist,
    so no product acquires an empty chunk it does not need.
    """
    spec = PRODUCTS[product]
    if not spec["year_col"]:
        return ["all"]
    yc, lib, tbl = spec["year_col"], spec["lib"], spec["table"]
    df = db.raw_sql(f"select distinct extract(year from {yc})::int as y "
                    f"from {lib}.{tbl} where {yc} is not null order by 1")
    keys = [str(int(y)) for y in df["y"].tolist()]
    # OPTIONAL `years` window, additive: a product without it behaves exactly as before. These
    # tables run to 1925 and the holdout needs a slice, so pulling every year would spend hours
    # on data no register reads.
    span = spec.get("years")
    if span:
        lo, hi = int(span[0]), int(span[1])
        keys = [k for k in keys if lo <= int(k) <= hi]
    n = db.raw_sql(f"select count(*) as n from {lib}.{tbl} where {yc} is null")
    if int(n["n"].iloc[0]):
        keys.append(NULLDATE)
    return keys


def resolve_projection(db, product: str):
    """The SELECT projection for a product, resolved ONCE against the table's real columns.

    Returns `(projection, missing)`. A product with no `cols` spec gets `("*", [])`, i.e. the
    historical behaviour. The declared list is INTERSECTED with what the table actually carries
    rather than trusted, so a renamed or absent field is REPORTED in the manifest instead of
    raising halfway through a 54-chunk pull.
    """
    spec = PRODUCTS[product]
    want = spec.get("cols")
    if not want:
        return "*", []
    lib, tbl = spec["lib"], spec["table"]
    have = set(db.raw_sql(f"select * from {lib}.{tbl} limit 1").columns)
    sel = [c for c in want if c in have]
    missing = [c for c in want if c not in have]
    if not sel:
        raise RuntimeError("none of the %d declared columns exist on %s.%s"
                           % (len(want), lib, tbl))
    return ", ".join(sel), missing


def pull_chunk(db, product: str, chunk: str, root: str = "",
               projection: str = "", missing_cols=None) -> dict:
    spec = PRODUCTS[product]
    lib, tbl, yc = spec["lib"], spec["table"], spec["year_col"]
    t0 = time.time()
    # OPTIONAL projection, resolved ONCE PER PRODUCT by the caller and passed in -- see
    # `resolve_projection`. Absent -> `select *`, exactly the historical behaviour, so every
    # product without a `cols` spec is bit-identical and a direct `pull_chunk` call still works.
    #
    # IT IS THE CALLER'S JOB BECAUSE OF A DEFECT AN EXISTING GUARD CAUGHT. The first cut probed
    # the column list INSIDE `pull_chunk`, which (a) issued a `select * limit 1` on EVERY chunk --
    # 54 wasted round trips for `crsp_dsf` alone -- and (b) broke
    # `test_the_nulldate_chunk_selects_exactly_the_rows_no_year_chunk_can`, whose contract is that
    # `pull_chunk` issues ONE query whose predicate is the chunk's. Resolving once upstream fixes
    # both, and the guard now passes for the right reason rather than being adjusted to suit.
    proj = projection or "*"
    missing = list(missing_cols or [])
    if chunk == "all":
        sql = f"select {proj} from {lib}.{tbl}"
    elif chunk == NULLDATE:
        sql = f"select {proj} from {lib}.{tbl} where {yc} is null"
    else:
        y = int(chunk)
        sql = (f"select {proj} from {lib}.{tbl} where {yc} >= '{y}-01-01' "
               f"and {yc} < '{y + 1}-01-01'")
    df = db.raw_sql(sql)
    fetch_s = time.time() - t0

    p = os.path.join(product_root(product, root), f"{product}_{chunk}.pkl")
    tmp = p + ".tmp"
    df.to_pickle(tmp, compression="gzip")
    _replace_retry(tmp, p)           # payload lands BEFORE its manifest line
    rec = {"schema": SCHEMA, "product": product, "chunk": chunk,
           "library": lib, "table": tbl, "rows": int(len(df)),
           "columns": int(df.shape[1]), "bytes": os.path.getsize(p),
           "sha256": sha256(p), "fetch_seconds": round(fetch_s, 1),
           "total_seconds": round(time.time() - t0, 1),
           "status": "ok" if len(df) else "empty",
           "utc": W.stamp()}
    declared = spec.get("cols")
    if declared:
        rec["columns_requested"] = len(declared)
        rec["columns_absent"] = missing
    return rec


#: How many times a chunk is retried on a CONNECTION failure, each on a fresh connection.
def _acquire_lock(product: str, root: str = "") -> str:
    """Refuse to run while another process is pulling the same product.

    MEASURED, NOT ANTICIPATED (2026-08-24). Two `wrds_pull --product comp_pit` processes were
    started against the same tree, both computed the same `todo` list from the same manifest, and
    both wrote `comp_pit_<year>.pkl.tmp`. Three chunks then failed with WinError 32 and WinError 2
    -- symptoms that read as antivirus and were briefly written up as antivirus. Nothing was
    corrupted, because the payload write is atomic and the manifest is append-only, so between
    them the two runs finished the product. **It was luck: the loser of the race could equally
    have replaced a truncated file, and a resume design whose safety depends on who wins is not a
    safe design.**

    Deliberately a plain lock file with the owning pid, not a lease: it fails CLOSED and a stale
    lock is removed by hand after looking at the pid, which on a data pull is the right way round.
    """
    p = os.path.join(root or W.DEFAULT_RAW_ROOT, f".pull.{product}.lock")
    if os.path.exists(p):
        try:
            who = open(p, encoding="utf-8").read().strip()
        except Exception:                                               # noqa: BLE001
            who = "unreadable"
        raise SystemExit(
            f"[wrds] REFUSED: {product} is already being pulled ({who}).\n"
            f"       Two pullers on one product race on the same .tmp path.\n"
            f"       If that process is gone, delete {p} and re-run.")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(f"pid={os.getpid()} started={W.stamp()}")
    return p


MAX_RECONNECTS = 3

#: Substrings that mean "the SESSION is unusable", not "the query was wrong". Only these are
#: retried -- retrying a genuine SQL error just burns the same error three times.
#:
#: THE SECOND GROUP IS THE ONE THAT COST A RUN, and it is the first group's defect wearing a
#: different message. Measured 2026-08-24: after `comp_pit` 2022 failed at the file layer, every
#: remaining chunk came back "Can't reconnect until invalid transaction is rolled back" -- a
#: POISONED transaction rather than a dead socket, so `_is_dead_connection` did not match, the
#: retry never fired, and 2024/2025/2026 failed in a row for a reason none of them caused.
#: Identical shape to the original one-connection defect: ONE bad chunk silently condemns the
#: rest. A recovery rule keyed on one spelling of "the session is gone" is not a recovery rule.
#: EVERY NEEDLE MUST BE LOWERCASE -- the haystack is lowercased and the needles are not, so a
#: capitalised entry can never match. That is not hypothetical: "SSL connection has been closed"
#: and "EOF detected" were carried over verbatim from a version that lowercased both sides, and
#: were dead for exactly as long as it took the two-directional test below to run. A guard that
#: silently cannot fire is the failure family this project has now hit six times.
_DEAD_CONN = ("server closed the connection", "connection already closed",
              "terminating connection", "ssl connection has been closed",
              "could not receive data", "connection not open", "eof detected",
              # poisoned session: the handle is alive and refuses to do any further work
              "invalid transaction is rolled back", "can't reconnect until",
              "current transaction is aborted", "connection is closed")

#: A tmp file that vanished between write and replace. Not a connection fault at all, but the
#: recoverable action is the same one -- re-fetch and rewrite the chunk -- so it joins the
#: retryable set rather than getting a second, parallel retry loop.
_TRANSIENT_FS = ("cannot find the file specified", "winerror 2",
                 "being used by another process", "winerror 32")


def _is_retryable(err: str) -> bool:
    low = err.lower()
    return any(s in low for s in _DEAD_CONN) or any(s in low for s in _TRANSIENT_FS)


def run(product: str, root: str = "", limit: int = 0, years=None) -> dict:
    lock = _acquire_lock(product, root)
    try:
        return _run_locked(product, root, limit, years)
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def _run_locked(product: str, root: str = "", limit: int = 0, years=None) -> dict:
    # ONE connection reused across every chunk was a real defect, measured 2026-08-24: WRDS
    # closed the connection during `comp_pit`'s 2002 chunk and the SAME dead handle was then used
    # for every remaining chunk, so 25 of 66 failed in a row with
    # "server closed the connection unexpectedly". None of them was a data problem.
    #
    # This is the ThetaData miner's dead-channel defect in a second costume -- that lane already
    # carries the comment "force a fresh channel; a dead one stays dead" -- and the lesson did not
    # travel with the code. A long pull WILL be disconnected by the server; that is normal
    # operation for a shared database, not an incident, so the puller reconnects and retries the
    # affected chunk rather than recording a failure it could have avoided.
    db = W.connect()
    man = load_manifest(root)
    keys = chunks_for(db, product)
    # `--years` NARROWS an already-derived chunk list; it never widens it, so it cannot reach a
    # year the spec's own window excludes. It exists to REORDER a long pull: `crsp_dsf` runs in
    # year order, which puts Gate B's 2007-2024 years LAST and blocks the gate that decides
    # whether the holdout may be opened. Narrowing lets those years be pulled first and the
    # remainder resumed afterwards -- `needs_pull` skips what is already banked, so nothing is
    # re-fetched. A FLAG rather than a temporary edit to the spec: the ordering choice is then
    # visible in the command that made it, and there is no diff to forget to revert.
    if years:
        lo, hi = int(years[0]), int(years[1])
        keys = [k for k in keys if (not k.isdigit()) or (lo <= int(k) <= hi)]
    # ONCE PER PRODUCT, not once per chunk. See `resolve_projection` and `pull_chunk` for why:
    # probing inside `pull_chunk` cost 54 wasted round trips on `crsp_dsf` and broke the guard
    # that pins the chunk predicate.
    proj, missing = resolve_projection(db, product)
    if missing:
        print("[wrds] %s: %d declared columns ABSENT from the table: %s"
              % (product, len(missing), ", ".join(missing)), flush=True)
    todo = [c for c in keys if needs_pull(product, c, man, root)]
    if limit:
        todo = todo[:limit]
    print(f"[wrds] {product}: {len(keys)} chunks, {len(todo)} to pull", flush=True)
    print(f"[wrds] {PRODUCTS[product]['why']}", flush=True)

    done, gb = 0, 0.0
    t0 = time.time()
    for c in todo:
        rec = None
        for attempt in range(MAX_RECONNECTS + 1):
            try:
                rec = pull_chunk(db, product, c, root,
                                 projection=proj, missing_cols=missing)
                if attempt:
                    rec["reconnects"] = attempt
                break
            except Exception as e:                                      # noqa: BLE001
                err = f"{type(e).__name__}: {str(e)[:240]}"
                if attempt < MAX_RECONNECTS and _is_retryable(str(e)):
                    wait = 5 * (attempt + 1)
                    print(f"[wrds] {product} {c}: session unusable ({type(e).__name__}) "
                          f"(attempt {attempt + 1}/{MAX_RECONNECTS}), reconnecting in {wait}s",
                          flush=True)
                    time.sleep(wait)
                    try:
                        db.close()
                    except Exception:                                   # noqa: BLE001
                        pass                     # a dead handle may refuse to close; irrelevant
                    db = W.connect()
                    continue
                rec = {"schema": SCHEMA, "product": product, "chunk": c,
                       "status": "failed", "error": err,
                       "attempts": attempt + 1, "utc": W.stamp()}
                print(f"[wrds] {product} {c}: FAILED {err[:120]}", flush=True)
                # A chunk that gives up may leave the session poisoned, and the NEXT chunk then
                # fails for a reason it did not cause -- which is exactly how 25 chunks and then
                # 3 more went down in this lane. One failure must cost ONE chunk, so the handle
                # is replaced unconditionally before moving on. A fresh connect is ~2s against a
                # multi-minute chunk, so the cost of doing this when it was not needed is nil.
                try:
                    db.close()
                except Exception:                                       # noqa: BLE001
                    pass
                db = W.connect()
                break
        append_manifest(rec, root)
        done += 1
        gb += rec.get("bytes", 0) / 1e9
        el = time.time() - t0
        eta = (len(todo) - done) * (el / max(1, done))
        print(f"[wrds] {product} {c}: {rec.get('rows', 0):,} rows "
              f"{rec.get('bytes', 0)/1e6:.1f}MB {rec.get('status')} | "
              f"{done}/{len(todo)} {gb:.2f}GB {el/60:.0f}m elapsed "
              f"{eta/60:.0f}m left", flush=True)
    print(f"[wrds] {product} finished: {done} chunks, {gb:.2f} GB, "
          f"{(time.time()-t0)/60:.0f} min", flush=True)
    return {"product": product, "chunks": done, "gb": round(gb, 3)}


def reconcile(db, product: str, root: str = "") -> dict:
    """Do the pulled chunks sum to the table's own `count(*)`?

    THE CHECK THAT WOULD HAVE CAUGHT THE NULL-DATE HOLE ON DAY ONE, and it exists because
    nothing else could: every chunk reported `ok`, every hash verified, every byte count matched,
    and 102,213 rows were missing. **File-level integrity checks confirm that what was written is
    intact; they cannot see what was never fetched.** A completeness check has to compare against
    the SOURCE, so this asks the server.

    Reported per product rather than raised: a legitimate mismatch exists the moment the vendor
    adds rows after a pull, and a checker that cries wolf on ordinary staleness gets ignored.
    """
    spec = PRODUCTS[product]
    lib, tbl = spec["lib"], spec["table"]
    # THE SOURCE COUNT MUST BE TAKEN OVER THE SAME WINDOW THAT WAS PULLED, or this check reports
    # a false shortfall for every windowed product -- which is the failure mode the last
    # paragraph above warns about, caused by the `years` key being added without updating it.
    # Measured when it happened: `crsp_dsf` read "SHORT BY 13,544,293" and `comp_fundq` "SHORT BY
    # 59,055", and both differences were exactly the pre-window years that were deliberately
    # never requested. A completeness check that cries wolf on a deliberate scope is worse than
    # none, because the one real hole it exists to catch then looks like more of the same.
    span = spec.get("years")
    where, scope = "", "all"
    if span and spec.get("year_col"):
        yc = spec["year_col"]
        lo, hi = int(span[0]), int(span[1])
        # `or {yc} is null` because a NULL-date row belongs to no year and IS pulled, by the
        # `nulldate` chunk -- so excluding it here would re-open the hole from the other side.
        where = (f" where ({yc} >= '{lo}-01-01' and {yc} < '{hi + 1}-01-01') "
                 f"or {yc} is null")
        scope = "%d-%d plus null-dated" % (lo, hi)
    n = int(db.raw_sql(f"select count(*) as n from {lib}.{tbl}{where}")["n"].iloc[0])
    man = load_manifest(root)
    got = sum(r.get("rows", 0) for k, r in man.items()
              if r.get("product") == product and r.get("status") in ("ok", "empty"))
    res = {"product": product, "source_rows": n, "pulled_rows": got,
           "source_scope": scope,
           "difference": n - got,
           "reconciles": n == got}
    print(f"[wrds] {product}: source {n:,} vs pulled {got:,} "
          f"-> {'RECONCILES' if res['reconciles'] else f'SHORT BY {n-got:,}'}", flush=True)
    return res


def verify(root: str = "", full: bool = False) -> dict:
    man = load_manifest(root)
    missing = bad_size = bad_hash = 0
    for k, rec in man.items():
        if rec.get("status") != "ok":
            continue
        p = os.path.join(product_root(rec["product"], root),
                         f"{rec['product']}_{rec['chunk']}.pkl")
        if not os.path.exists(p):
            missing += 1
            continue
        if os.path.getsize(p) != rec.get("bytes"):
            bad_size += 1
            continue
        if full and sha256(p) != rec.get("sha256"):
            bad_hash += 1
    res = {"records": len(man), "missing": missing, "wrong_size": bad_size,
           "wrong_hash": bad_hash, "full_hash": full}
    print(json.dumps(res, indent=1))
    return res


def summarise(root: str = "") -> dict:
    man = load_manifest(root)
    per = {}
    for rec in man.values():
        p = per.setdefault(rec["product"], {"chunks": 0, "rows": 0, "bytes": 0,
                                            "failed": 0, "empty": 0})
        if rec.get("status") == "failed":
            p["failed"] += 1
            continue
        if rec.get("status") == "empty":
            p["empty"] += 1
        p["chunks"] += 1
        p["rows"] += rec.get("rows", 0)
        p["bytes"] += rec.get("bytes", 0)
    out = {"generated_utc": W.stamp(), "trials": 0, "raw_root": W.raw_root(root),
           "products": per,
           "total_rows": sum(v["rows"] for v in per.values()),
           "total_bytes": sum(v["bytes"] for v in per.values())}
    out["total_gb"] = round(out["total_bytes"] / 1e9, 3)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="WRDS chunked pull (collection only)")
    ap.add_argument("--product", default="", choices=sorted(PRODUCTS) + [""])
    ap.add_argument("--root", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="compare pulled row counts against the server's own count(*)")
    ap.add_argument("--full-hash", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--years", nargs=2, type=int, metavar=("LO", "HI"), default=None,
                    help="NARROW the derived chunk list to [LO, HI] inclusive. Never widens it, "
                         "so it cannot reach a year the product's own window excludes. For "
                         "REORDERING a long pull; resume the remainder with no flag.")
    a = ap.parse_args(argv)

    if a.reconcile:
        db = W.connect()
        man = load_manifest(a.root)
        seen = sorted({r["product"] for r in man.values() if r.get("product") in PRODUCTS})
        out = [reconcile(db, p, a.root) for p in ([a.product] if a.product else seen)]
        print(json.dumps({"reconcile": out,
                          "all_reconcile": all(r["reconciles"] for r in out)}, indent=1))
        return
    if a.verify:
        verify(a.root, a.full_hash)
        return
    if a.summary or not a.product:
        print(json.dumps(summarise(a.root), indent=1))
        return
    run(a.product, a.root, a.limit, a.years)
    print(json.dumps(summarise(a.root), indent=1))


if __name__ == "__main__":
    main()
