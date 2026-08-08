"""Freeze the option-chain inputs a banked result stands on (audit O16 follow-on).

WHY THIS EXISTS. O16's blocking reproduction gate measured the authoritative options book,
`state_r2_corrected.pkl`, at **86.435% reproducible** against the chain store it was built
from. The attribution was unambiguous: rows whose ticker-year file had NOT been rewritten
since the book was banked reproduced at 100.00% (3,127 of 3,127, zero exceptions), while rows
whose file HAD been rewritten reproduced at 30.47% (231 of 758). The store is mutable, the
miner re-pulls and deepens years in place, and 19.5% of the ticker-year files the book consumed
were rewritten after it was banked on 2026-08-05 19:51.

The consequence is not that a number moved. It is that **every banked options verdict is
currently pinned to a store that no longer exists**, so any recompute-based audit silently
disagrees with the record and reads as a code bug. The equity lane already solved this — a
verdict's inputs are frozen (`data/backtest_freeze_2026-08`, audit D10) or the verdict has no
referent. Options had no equivalent.

--------------------------------------------------------------------------------------------
THE CHOICE, AND THE NUMBER IT WAS MADE ON.

The brief named two candidate designs and required (a) be MEASURED before being rejected:

  (a) freeze a COPY of the chain rows a banked result consumed
  (b) fingerprint each symbol-year and refuse a mismatched read on replay

Measured on the real R2 corrected book (2026-08-08, `scripts/options_freeze_cost.py`): the
trade-scope frozen copy is **157.88 MB** as a plain pickle, **27.44 MB gzipped**, over
**2,870,079 chain rows** (2,717,072 alert-day slice rows + 158,702 contract-history rows,
deduplicated) — against a **26.98 GB** live store of 5,063 symbol-years.

**That is 0.585% of the store as a pickle and 0.102% gzipped.** The intuition this measurement
was there to check — "freezing chains for 3,885 trades must be huge, the store is 27 GB" — is
wrong by more than two orders of magnitude, because a book is SPARSE in the store: it reads one
day out of ~250 per symbol-year, not the year.

THE ARTIFACT ACTUALLY BANKED IS SMALLER STILL: `data/options_freeze/R2_CORRECTED_2026-08-08/`
is **23,296,080 bytes (23.30 MB) over 2,870,811 rows**, i.e. **0.086% of the store**. It is
smaller than the 27.44 MB probe despite carrying 732 MORE rows and an extra `symbol` column,
and the difference is worth knowing rather than glossing: the probe kept the concatenation's
non-contiguous index (a 2.87M-entry int64 array), `freeze_book` calls `reset_index(drop=True)`
and drops it. The extra rows come from that same `symbol` column — rows identical across two
symbols no longer collapse into one another under `drop_duplicates`, which is correct.

**So (a) is NOT rejected. It is adopted, and (b) is adopted alongside it**, because the
measurement also showed why neither is sufficient alone:

  * (a) is cheap for a BANKED BOOK because a book is sparse in the store — 3,885 trades touch
    one chain slice per alert date plus one contract's history, not whole years. It is the
    right artifact for defending a verdict, and it is self-contained: the frozen copy replays
    even if the store is deleted.
  * (a) does NOT cover the whole run, and this is the limit to carry. `chain_on` is called on
    every CANDIDATE day the scan looks at — **33,254** of them for this book, against 3,885
    alerts — so a trade-scope freeze replays every per-trade statistic but CANNOT re-derive
    WHICH ALERTS FIRE. Run-scope is ESTIMATED at ~1,280 MB (mean measured day-slice of 699.6
    rows x 33,254 candidate days x 55.01 bytes/row). That is an extrapolation, not a
    measurement, and it is labelled as one wherever it is quoted.
  * (b) costs one hash per symbol-year and is the only thing that can tell you a replay is
    reading DIFFERENT bytes than the bank did. It is what makes the drift LOUD instead of
    silent, which is the failure that actually happened.

Adopting both is not belt-and-braces: they answer different questions. (a) answers "can this
verdict still be checked"; (b) answers "is what I am reading now what was read then".

--------------------------------------------------------------------------------------------
TWO-LEVEL FINGERPRINT, AND WHY A BYTE HASH ALONE WOULD CRY WOLF.

A sha256 over file bytes is cheap and catches everything, but it is too sensitive: re-pickling
identical rows under a different pandas version changes the bytes and nothing else. A stamp
that fires on that trains the reader to ignore it, which is worse than no stamp.

So the check is two-level, and the expensive level only runs on a mismatch:

  BYTE      sha256 of the file. Cached in a `.sha256` sidecar keyed by (size, mtime_ns), so a
            27 GB store is not rehashed on every read.
  CONTENT   sha256 over the KEEP columns, row-sorted (`content_digest`). Separates the two
            cases the record needs told apart:
                `repickled` - bytes moved, data identical. Benign, reported, not blocking.
                `changed`   - the rows themselves differ. This is the O16 failure.

That distinction is the same one `theta_bulk` already draws between `.empty` and `.missing`:
two states that look identical downstream and have opposite correct responses.

**BUT `deepen_stamp` IS NOT RUN AT BANK TIME, AND THE REASON IS A CORRECTION.** The first
version of this module did run it, and it was both slow (tens of minutes to digest 1,429 whole
year-frames) and — the real objection — OVER-BROAD. A whole-year digest reports `changed` when
a re-mine rewrites rows on dates the book never read, which is not a fact about the book's
inputs. `verify_against_frozen()` asks the precise question instead: are the rows this book
ACTUALLY CONSUMED still identical in the live store? The frozen copy is already that content
record, so the expensive whole-year digest buys nothing the freeze does not already provide.
`content_digest`/`deepen_stamp` remain available for whole-year comparisons and are pinned by
tests, but the banking path is byte-stamp + frozen copy.

--------------------------------------------------------------------------------------------
THE GATE IS DESCRIPTIVE AT BANK TIME AND BLOCKING ONLY FOR REPLAYS (session-5 stamp
convention, extended from `optuniv_run.py`'s no-overwrite guard).

  bank time   `stamp_years()` records the fingerprints of every symbol-year consumed. Purely
              descriptive. It cannot fail a run, because a stamp that can fail the thing it is
              describing would just get switched off.
  replay      `replay_pin()` installs the banked stamp; `theta_bulk._year_frame` then REFUSES
              to serve a symbol-year whose fingerprint differs. Opt-in and scoped to a context
              manager, so no live path and no miner run changes behaviour by default.

`set_replay_pin(None)` is the unpinned default and costs one `is not None` test per frame load.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import pickle
from typing import Iterable, Optional

from . import theta_bulk as TB

FREEZE_ROOT = os.path.join(TB.REPO_ROOT, "data", "options_freeze")
KEEP = list(TB.KEEP)
_CHUNK = 1 << 20


# ------------------------------------------------------------------------------------------
#  Fingerprints
# ------------------------------------------------------------------------------------------

def _sidecar(path: str) -> str:
    return path + ".sha256"


def file_sha256(path: str, use_cache: bool = True) -> Optional[str]:
    """sha256 of a file's bytes, optionally memoised in a `.sha256` sidecar.

    THE CACHE IS TRUSTED FOR BULK STAMPING AND NEVER FOR THE BLOCKING CHECK, and that split is
    a correctness requirement rather than a tuning choice. The sidecar key is (size, mtime_ns),
    which is what the OS updates on a write — but a rewrite that produces a file of the SAME
    SIZE within the filesystem's timestamp granularity collides with its own cache entry, and
    the stale hash is served. A cached-hash false NEGATIVE is precisely the silent failure this
    module exists to prevent, and it is not hypothetical: it was caught by
    `test_a_same_size_rewrite_that_keeps_its_mtime_is_still_detected`, which reproduces it
    deterministically with `os.utime`.

    So: `use_cache=True` where a miss only costs time (stamping 1,429 symbol-years at bank
    time), `use_cache=False` on every path whose answer decides whether data is trustworthy —
    the replay pin and `verify_stamp`. Under a pin each symbol-year is hashed once and then
    memoised by `theta_bulk._year_frame`, so the honest cost is one pass, not one per read.
    """
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = "%d %d" % (st.st_size, st.st_mtime_ns)
    sc = _sidecar(path)
    if use_cache:
        try:
            with open(sc, encoding="utf-8") as f:
                cached_key, cached_sha = f.read().strip().split("|", 1)
            if cached_key == key:
                return cached_sha
        except (OSError, ValueError):
            pass
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(_CHUNK)
                if not b:
                    break
                h.update(b)
    except OSError:
        return None
    sha = h.hexdigest()
    if use_cache:
        try:
            with open(sc, "w", encoding="utf-8") as f:
                f.write("%s|%s" % (key, sha))
        except OSError:
            pass
    return sha


def content_digest(path: str) -> Optional[str]:
    """sha256 over the KEEP columns, row-sorted — invariant to pickling and to row order.

    The stronger level, and the one that separates a re-pickle from a data change.

    HASHED FROM THE COLUMN BUFFERS, NOT FROM CSV. The first version rendered each frame with
    `DataFrame.to_csv` and it made banking unusable: a symbol-year is ~200k rows, so a single
    book's 1,429 years is ~285M rows of text formatting, and the bank step ran for tens of
    minutes. Hashing each column's raw numpy buffer is the same guarantee at a fraction of the
    cost. That matters beyond convenience — a freeze step slow enough to be annoying is a
    freeze step that gets skipped, which is how the store came to move under the book in the
    first place.

    Object columns (dates, the C/P right) have no numpy buffer to hash, so those fall back to
    a compact string rendering. The digest is therefore stable for a given pandas/numpy dtype
    layout, which is what it is compared against: the SAME file, later.
    """
    try:
        with open(path, "rb") as f:
            df = pickle.load(f)
    except Exception:                                                    # noqa: BLE001
        return None
    cols = [c for c in KEEP if c in getattr(df, "columns", [])]
    if not cols:
        return None
    try:
        sub = df[cols].sort_values(cols)
        h = hashlib.sha256()
        h.update(("|".join(cols) + "|%d" % len(sub)).encode())
        for c in cols:
            s = sub[c]
            if s.dtype == object:
                h.update(("\x1f".join(map(str, s.to_numpy()))).encode("utf-8", "replace"))
            else:
                h.update(str(s.dtype).encode())
                h.update(s.to_numpy().tobytes())
    except Exception:                                                    # noqa: BLE001
        return None
    return h.hexdigest()


def year_key(symbol: str, year: int) -> str:
    return "%s-%d" % (str(symbol).upper(), int(year))


def stamp_years(pairs: Iterable, root: str = None) -> dict:
    """Fingerprint every (symbol, year) a run consumed. Descriptive; never raises on a gap.

    A symbol-year that is absent is recorded with `present: false` rather than omitted — "we
    read nothing here" and "we forgot to record this" must not look the same later.
    """
    root = root or TB.CACHE_ROOT
    out = {}
    for sym, yr in sorted(set((str(s).upper(), int(y)) for s, y in pairs)):
        p = TB.year_path(sym, yr, root)
        k = year_key(sym, yr)
        if not os.path.exists(p):
            out[k] = {"present": False, "sha256": None, "bytes": None}
            continue
        st = os.stat(p)
        out[k] = {"present": True, "sha256": file_sha256(p), "bytes": st.st_size,
                  "mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(
                      timespec="seconds")}
    return out


def verify_stamp(stamp: dict, root: str = None, deep: bool = True) -> dict:
    """Compare a banked stamp against the store as it is NOW.

    Buckets: `ok`, `repickled` (bytes moved, content identical), `changed` (rows differ),
    `missing` (was present at bank, absent now), `appeared` (absent at bank, present now).
    `deep=False` skips the content digest, in which case every byte mismatch is reported as
    `changed_or_repickled` rather than being silently promoted to `changed`.
    """
    root = root or TB.CACHE_ROOT
    res = {"ok": [], "repickled": [], "changed": [], "missing": [], "appeared": [],
           "changed_or_repickled": []}
    for k, rec in sorted(stamp.items()):
        sym, yr = k.rsplit("-", 1)
        p = TB.year_path(sym, int(yr), root)
        here = os.path.exists(p)
        was = bool(rec.get("present"))
        if was and not here:
            res["missing"].append(k)
            continue
        if not was and here:
            res["appeared"].append(k)
            continue
        if not was and not here:
            res["ok"].append(k)
            continue
        if file_sha256(p, use_cache=False) == rec.get("sha256"):
            res["ok"].append(k)
            continue
        if not deep:
            res["changed_or_repickled"].append(k)
            continue
        cd_now = content_digest(p)
        cd_then = rec.get("content_sha256")
        if cd_then is None:
            # No content digest was banked, so "repickled" is not decidable. Say so rather
            # than guessing in either direction.
            res["changed_or_repickled"].append(k)
        elif cd_now == cd_then:
            res["repickled"].append(k)
        else:
            res["changed"].append(k)
    n = max(len(stamp), 1)
    res["n"] = len(stamp)
    res["n_ok"] = len(res["ok"])
    res["frac_ok"] = round(len(res["ok"]) / n, 6)
    res["clean"] = not (res["changed"] or res["missing"] or res["changed_or_repickled"])
    return res


def deepen_stamp(stamp: dict, root: str = None) -> dict:
    """Add content digests to an existing stamp. Expensive; run once at bank time.

    Kept separate from `stamp_years` so banking stays cheap by default and a caller chooses to
    pay for the stronger record.
    """
    root = root or TB.CACHE_ROOT
    out = {}
    for k, rec in stamp.items():
        rec = dict(rec)
        if rec.get("present"):
            sym, yr = k.rsplit("-", 1)
            rec["content_sha256"] = content_digest(TB.year_path(sym, int(yr), root))
        out[k] = rec
    return out


# ------------------------------------------------------------------------------------------
#  The replay pin (blocking, opt-in)
# ------------------------------------------------------------------------------------------

class ChainDrift(RuntimeError):
    """A pinned replay tried to read a symbol-year whose bytes differ from the banked stamp."""


class replay_pin:
    """Context manager: inside it, `theta_bulk` refuses to serve a drifted symbol-year.

    Deliberately NOT the default. A miner run must be free to rewrite years; only a replay
    that claims to reproduce a banked number needs the store held still underneath it.
    """

    def __init__(self, stamp: dict, root: str = None):
        self.stamp = stamp
        self.root = root or TB.CACHE_ROOT
        self._prev = None

    def __enter__(self):
        self._prev = getattr(TB, "_REPLAY_PIN", None)
        TB.set_replay_pin({k: v.get("sha256") for k, v in self.stamp.items()
                           if v.get("present")})
        return self

    def __exit__(self, *exc):
        TB.set_replay_pin(self._prev)
        return False


# ------------------------------------------------------------------------------------------
#  Frozen copies (option (a))
# ------------------------------------------------------------------------------------------

def _d(x):
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x)[:10])


def consumed_pairs(rows) -> set:
    """The (symbol, year) set a banked book's trades touched — alert year through expiry year."""
    out = set()
    for r in rows:
        t = str(r.get("ticker") or "").upper()
        if not t:
            continue
        try:
            a = _d(r.get("alert_ts"))
        except (TypeError, ValueError):
            continue
        try:
            e = _d(r.get("expiry"))
        except (TypeError, ValueError):
            e = a
        for yr in range(a.year, e.year + 1):
            out.add((t, yr))
    return out


def _contract_key(exp, strike, right) -> str:
    return "%s|%.3f|%s" % (exp, round(float(strike), 3), str(right)[0].upper())


def _contract_rows(df, cols, sym: str, contracts) -> list:
    """Every requested contract's rows, in ONE pass over the year frame.

    WHY THIS IS NOT A LOOP OF MASKS. The first version filtered the frame once PER CONTRACT.
    That is fine for a 3,885-trade book (19 minutes) and hopeless for the five pooled control
    seeds: 29,785 contracts x a ~200k-row scan each, which ran for ~45 minutes without
    producing a row before the process was killed. Keying once and joining turns 29,785 scans
    into one per symbol-year.

    Each contract keeps its OWN date window rather than a pooled min/max, because a pooled
    window would freeze rows the book never read — a superset is safe for replay but would
    misreport what the book actually consumed, and that number is the whole point of the
    cost measurement.
    """
    import pandas as pd

    want = {}
    for (exp, strike, right, s, e) in contracts:
        want.setdefault(_contract_key(exp, strike, right), []).append((s, e))

    key = (df["expiration"].astype(str) + "|"
           + df["strike"].astype(float).round(3).map(lambda v: "%.3f" % v) + "|"
           + df["right"].astype(str).str[0].str.upper())
    hit = key.isin(want)
    if not hit.any():
        return []
    sub = df[hit]
    ks = key[hit]

    # THE SAME CONTRACT CAN BE REQUESTED BY TWO TRADES WITH DISJOINT WINDOWS. Collapsing those
    # to a single [min, max] span would include the GAP between them — rows the book never read.
    #
    # HONEST NOTE ON WHY THIS IS WRITTEN THIS WAY: an interim version did collapse them, and on
    # the R2 book it produced a frozen copy 14,231 bytes larger, which I first read as evidence
    # of exactly that over-inclusion. It was not. Checked properly, the two agree at
    # 2,870,811 rows and are content-identical after sorting — the byte difference is gzip
    # compressing a different ROW ORDER. So the collapse was harmless HERE and is still unsound
    # IN GENERAL, and the per-window predicate below is kept because it matches the original
    # loop exactly rather than by luck of this book's contract mix. The common single-window
    # case stays fully vectorised; only genuinely multi-window keys pay a loop.
    single = {k: v[0] for k, v in want.items() if len(v) == 1}
    multi = {k: v for k, v in want.items() if len(v) > 1}

    is_single = ks.isin(single)
    keep = is_single & False                       # a False mask of the right index
    if is_single.any():
        kk = ks[is_single]
        lo = kk.map(lambda k: single[k][0])
        hi = kk.map(lambda k: single[k][1])
        ok = (sub.loc[is_single, "date"] >= lo) & (sub.loc[is_single, "date"] <= hi)
        keep = keep | ok.reindex(ks.index, fill_value=False)
    for k, windows in multi.items():
        rows_k = ks == k
        if not rows_k.any():
            continue
        d = sub.loc[rows_k, "date"]
        any_win = None
        for (s, e) in windows:
            m = (d >= s) & (d <= e)
            any_win = m if any_win is None else (any_win | m)
        keep = keep | any_win.reindex(ks.index, fill_value=False)

    sub = sub[keep]
    return [sub[cols].assign(symbol=sym)] if len(sub) else []


def freeze_book(rows, out_path: str, root: str = None, overwrite: bool = False,
                progress: bool = False) -> dict:
    """Write the trade-scope frozen copy: every alert-date chain slice + every contract history.

    Refuses to overwrite an existing freeze unless asked, on the `optuniv_run.guard_bank`
    principle — no path through this module destroys a banked artifact.
    """
    import pandas as pd

    root = root or TB.CACHE_ROOT
    if os.path.exists(out_path) and not overwrite:
        raise FileExistsError(
            "%s exists; a freeze is a banked artifact. Pass overwrite=True deliberately."
            % out_path)
    need = {}
    for r in rows:
        t = str(r.get("ticker") or "").upper()
        a, e = _d(r.get("alert_ts")), _d(r.get("expiry"))
        need.setdefault((t, a.year), {"dates": set(), "contracts": []})
        need[(t, a.year)]["dates"].add(a)
        for yr in range(a.year, e.year + 1):
            need.setdefault((t, yr), {"dates": set(), "contracts": []})
            need[(t, yr)]["contracts"].append(
                (e, float(r.get("strike")), str(r.get("opt_right"))[0].upper(), a, e))
    frames = []
    keys = sorted(need)
    for n, (sym, yr) in enumerate(keys, 1):
        job = need[(sym, yr)]
        p = TB.year_path(sym, yr, root)
        if not os.path.exists(p):
            continue
        try:
            with open(p, "rb") as f:
                df = pickle.load(f)
        except Exception:                                                # noqa: BLE001
            continue
        cols = [c for c in KEEP if c in df.columns]
        if job["dates"]:
            sl = df[df["date"].isin(job["dates"])]
            if len(sl):
                frames.append(sl[cols].assign(symbol=sym))
        if job["contracts"]:
            frames.extend(_contract_rows(df, cols, sym, job["contracts"]))
        if progress and (n % 100 == 0 or n == len(keys)):
            print("[freeze] %d/%d symbol-years, %d frames" % (n, len(keys), len(frames)),
                  flush=True)
    frozen = pd.concat(frames).drop_duplicates().reset_index(drop=True) if frames \
        else pd.DataFrame(columns=KEEP + ["symbol"])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = out_path + ".tmp"
    with gzip.open(tmp, "wb", compresslevel=6) as f:
        pickle.dump(frozen, f, protocol=4)
    os.replace(tmp, out_path)
    return {"path": out_path, "rows": int(len(frozen)),
            "bytes": os.path.getsize(out_path),
            "symbol_years": len(need)}


def load_frozen(path: str):
    with gzip.open(path, "rb") as f:
        return pickle.load(f)


def verify_against_frozen(frozen_path: str, rows, root: str = None) -> dict:
    """Are the rows this book actually CONSUMED still identical in the live store?

    This is the precise question, and it is why `deepen_stamp` is not run at bank time.

    A whole-year content digest is both expensive and OVER-BROAD: a re-mine that rewrote rows
    on dates the book never read would report the year as `changed` even though every input
    the book used is intact. The frozen copy already records exactly the consumed rows, so
    comparing against IT answers "are this verdict's inputs unchanged" rather than "did
    anything anywhere in these years move".

    Returns per-symbol-year counts plus the overall row-level match rate. Cheap relative to a
    full deepen because it only slices the years the book touched, on the dates it read.
    """
    import pandas as pd

    root = root or TB.CACHE_ROOT
    frozen = load_frozen(frozen_path)
    if "symbol" not in getattr(frozen, "columns", []):
        return {"ok": False, "reason": "frozen copy carries no symbol column"}
    cols = [c for c in KEEP if c in frozen.columns]
    want = {}
    for sym, g in frozen.groupby("symbol"):
        for yr, gg in g.groupby(g["date"].map(lambda d: _d(d).year)):
            want[(str(sym), int(yr))] = gg[cols].sort_values(cols).reset_index(drop=True)

    matched = differing = absent = 0
    rows_same = rows_total = 0
    detail = []
    for (sym, yr), fdf in sorted(want.items()):
        p = TB.year_path(sym, yr, root)
        if not os.path.exists(p):
            absent += 1
            detail.append({"key": year_key(sym, yr), "state": "absent"})
            continue
        try:
            with open(p, "rb") as f:
                live = pickle.load(f)
        except Exception:                                                # noqa: BLE001
            absent += 1
            continue
        dates = set(fdf["date"])
        sl = live[live["date"].isin(dates)][cols].sort_values(cols).reset_index(drop=True)
        merged = fdf.merge(sl, on=cols, how="inner")
        same = len(merged)
        rows_same += same
        rows_total += len(fdf)
        if same == len(fdf):
            matched += 1
        else:
            differing += 1
            detail.append({"key": year_key(sym, yr), "state": "rows_differ",
                           "frozen_rows": int(len(fdf)), "still_present": int(same)})
    n = max(len(want), 1)
    return {"ok": True, "symbol_years": len(want), "identical": matched,
            "differing": differing, "absent": absent,
            "frac_symbol_years_identical": round(matched / n, 6),
            "rows_frozen": rows_total, "rows_still_identical": rows_same,
            "frac_rows_identical": round(rows_same / max(rows_total, 1), 6),
            "detail": detail[:50]}


def write_manifest(path: str, book: str, stamp: dict, extra: dict = None) -> str:
    man = {"book": book,
           "written": dt.datetime.now().isoformat(timespec="seconds"),
           "n_symbol_years": len(stamp),
           "stamp": stamp}
    if extra:
        man.update(extra)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    os.replace(tmp, path)
    return path


def stamp_run(out_dir: str, book_name: str, rows, quiet: bool = False) -> Optional[str]:
    """Stamp the chain symbol-years a finished run consumed. Used by every options runner.

    DESCRIPTIVE, and deliberately incapable of failing the run. It executes after the scoring
    is already done, and a stamp that could destroy twenty minutes of finished work would be
    switched off within a week. The READ side (`replay_pin`) is what blocks, and only for a
    replay claiming to reproduce a banked book.

    `rows` may be a flat list of trade dicts or a dict of such lists (the entry lab banks its
    arms that way), because the alternative is three subtly different call sites.
    """
    try:
        flat = []
        if isinstance(rows, dict):
            for v in rows.values():
                if isinstance(v, (list, tuple)):
                    flat.extend(v)
        else:
            flat = list(rows or [])
        stamp = stamp_years(consumed_pairs(flat))
        p = os.path.join(out_dir, "CHAIN_STAMP.json")
        write_manifest(p, book_name, stamp, extra={
            "n_trades": len(flat),
            "scope": "TRADE SCOPE: symbol-years the banked trades consumed (alert year "
                     "through expiry year). Candidate days that produced no alert are NOT "
                     "covered, so this pins per-trade replay, not alert selection.",
            "how_to_replay": "options_freeze.replay_pin(json.load(open(path))['stamp'])",
        })
        if not quiet:
            print("[freeze] chain stamp: %d symbol-years from %d trades -> %s"
                  % (len(stamp), len(flat), p), flush=True)
        return p
    except Exception as e:                                               # noqa: BLE001
        if not quiet:
            print("[freeze] WARNING: chain stamp failed (%s: %s). The book is banked but its "
                  "inputs are NOT pinned." % (type(e).__name__, e), flush=True)
        return None


def read_manifest(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
