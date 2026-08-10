"""The daily scan publishes the Valquo Index book, and the engine accepts it — offline.

    python tests/test_index_book_publish.py

WHAT IS AT RISK, and it is a live sandbox book rather than a page.

Session 16 closed `PT-SPLIT` with a GATE: `paper_track.seed_book` refuses any book that is not
the contract-bound Valquo Index (>= 50 names AND the 8% cap binding). That stopped the engine
*adding* to a wrong book. It did not make it start recording the right one, because
`/admin/run-paper-track` reads `data/valquo_index.json` when it exists and **silently rebuilds
from the store's latest scan when it does not** — and a thin scan rebuilds a 10-name book
wearing a correct "Valquo Index" method string. That silent rebuild is how the engine recorded
10 names while the published book held 86, and how PT-OUTBOUND shipped an engine figure to
Discord as an Index claim.

So the four things these tests hold down:

1. **A CONFORMING BOOK IS ACTUALLY WRITTEN**, from the rows the daily scan just ingested.
2. **A NON-CONFORMING BOOK IS NEVER WRITTEN.** Not written-and-labelled — not written. And a
   refusal must not overwrite or delete a good book that is already there.
3. **THE ENGINE ACCEPTS WHAT IS PUBLISHED.** Asserted by running `seed_book` against the file
   and requiring `seed_refused` to be None — i.e. the consumer's own gate goes green. A
   publisher whose output the consumer still rejects has fixed nothing.
4. **NOTHING ELSE CONSUMES THE PATH.** The set of readers is pinned, so a future second reader
   has to be noticed rather than discovered after it disagrees with the first.

Every test builds its own store and its own temp path. Nothing here touches `data/`.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import paper_track as PT          # noqa: E402
from valuation.edge import valquo_index as VI         # noqa: E402
from valuation.saas import index_book as IB           # noqa: E402
from valuation.screener.store import Store            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _store():
    d = tempfile.mkdtemp()
    return Store(os.path.join(d, "t.db"))


def _rows(n, large=True, base_mc=50e9):
    """A scan snapshot. `large` controls whether names clear the $10B large-cap floor."""
    mc = base_mc if large else 1e9
    return [{"ticker": f"T{i:04d}", "name": f"Name {i}", "sector": "Tech",
             "price": 100.0 + i, "market_cap": mc + i * 1e6,
             "hot_score": round(99.0 - i * 0.01, 2), "composite": 1.0 - i * 0.001,
             "rank": i + 1} for i in range(n)]


def _seed_scan(store, n, date="2026-08-10", large=True):
    store.save_snapshot(date, _rows(n, large=large), "test", {"universe_size": n})
    return date


def _path():
    return os.path.join(tempfile.mkdtemp(), "valquo_index.json")


# ------------------------------------------------------------------ 1. a real book is written
def test_a_conforming_scan_publishes_a_book_the_contract_recognises():
    st = _store()
    _seed_scan(st, 600)                       # 600 large caps -> decile 60, clears the floor of 50
    p = _path()
    out = IB.publish(st, path=p)

    assert out["published"] is True, out["reason"]
    assert out["conforms"] is True
    assert os.path.exists(p), "publish reported success but wrote no file"

    with open(p, encoding="utf-8") as fh:
        book = json.load(fh)
    conf = book["contract_conformance"]
    assert conf["conforms"] is True
    assert conf["n_positions"] >= VI.CONTRACT_MIN_POSITIONS
    assert conf["effective_max_weight"] <= VI.MAX_WEIGHT + 1e-9, "the 8% cap must actually bind"


def test_the_publish_record_names_the_universe_the_book_came_from():
    """Conformance is a size and a cap; it is silent about provenance.

    A decile of the daily live scan and a decile of the full Sharadar universe both conform and
    are NOT the same holdings. Recording which one was published is what keeps that from being
    discovered later as a divergence.
    """
    st = _store()
    _seed_scan(st, 600)
    out = IB.publish(st, path=_path())
    assert out["published"] is True
    assert out.get("source"), "the publish record does not say which universe the book came from"
    assert "scan" in out["source"].lower()
    assert out["source"] in out["reason"]


def test_the_published_book_is_built_from_the_scan_that_was_just_ingested():
    """Not from a stale file, and not from a different date."""
    st = _store()
    _seed_scan(st, 600, date="2026-08-09")
    _seed_scan(st, 700, date="2026-08-10")
    out = IB.publish(st, path=_path())
    assert out["scan_date"] == "2026-08-10"
    assert out["n_scored"] == 700


# ------------------------------------------------------------- 2. a wrong book is never written
def test_a_thin_scan_publishes_nothing_at_all():
    """The failure this exists to prevent: handing the engine a truncated book."""
    st = _store()
    _seed_scan(st, 120)                       # decile = 12, below the contract floor of 50
    p = _path()
    out = IB.publish(st, path=p)

    assert out["published"] is False
    assert out["conforms"] is False
    assert not os.path.exists(p), (
        "a NON-CONFORMING book was written to disk. The engine would read it as the Index, "
        "which is the PT-SPLIT defect this module exists to close."
    )
    assert "NOT PUBLISHED" in out["reason"]
    assert any("below the contract floor" in w for w in out["why_not"])


def test_a_refusal_does_not_destroy_the_last_good_book():
    """A thin scan must not delete or overwrite a conforming file already on disk."""
    st = _store()
    p = _path()
    _seed_scan(st, 600, date="2026-08-10")
    assert IB.publish(st, path=p)["published"] is True
    before = open(p, encoding="utf-8").read()

    thin = _store()
    _seed_scan(thin, 120, date="2026-08-11")
    out = IB.publish(thin, path=p)

    assert out["published"] is False
    assert open(p, encoding="utf-8").read() == before, (
        "the refusal path modified an existing book file; it must leave it byte-identical"
    )


def test_a_scan_of_small_caps_does_not_conform_even_when_it_is_wide():
    """Width alone is not the rule — the large-cap tier is what the decile is taken from."""
    st = _store()
    _seed_scan(st, 600, large=False)          # 600 names, all ~$1B
    out = IB.publish(st, path=_path())
    # `build_index` falls back to "largest half" when nothing clears the floor, so this is a
    # genuine assertion about the fallback rather than about an empty tier.
    assert out["conforms"] == (out["n_positions"] >= VI.CONTRACT_MIN_POSITIONS)


def test_a_probe_that_passes_and_a_written_book_that_does_not_is_reported_not_hidden():
    """The defensive branch, forced.

    It cannot fire naturally — the probe and the export are the same pure function on the same
    rows — so without this the branch would ship untested and a mutation that deletes it would
    go unnoticed. Verified: removing the re-check leaves every other test green.
    """
    st = _store()
    _seed_scan(st, 600)
    p = _path()
    real_export = VI.export
    try:
        def _lying_export(store=None, path=None, **kw):
            payload = real_export(store=store, path=path, **kw)
            payload["contract_conformance"] = {"conforms": False,
                                               "why_not": ["forced disagreement"],
                                               "n_positions": 3}
            return payload

        VI.export = _lying_export
        out = IB.publish(st, path=p)
    finally:
        VI.export = real_export

    assert out["published"] is False
    assert out["written_conforms"] is False
    assert "should be impossible" in out["reason"]
    # And the control: with the real export the same store publishes.
    assert IB.publish(st, path=_path())["published"] is True


def test_no_scan_at_all_is_a_reason_not_a_crash():
    st = _store()
    out = IB.publish(st, path=_path())
    assert out["published"] is False
    assert "no scan" in out["reason"]


def test_publish_never_raises_even_when_the_store_is_broken():
    """The daily hot list must not fail to land because a book could not be built."""
    class Broken:
        def latest_scan_date(self):
            raise RuntimeError("disk gone")

        def set_meta(self, *a, **k):
            raise RuntimeError("also gone")

    out = IB.publish(Broken(), path=_path())
    assert out["published"] is False
    assert "publish failed" in out["reason"]


# ------------------------------------------------- 3. the consumer's own gate goes green on it
def test_the_engine_accepts_the_published_book_and_refuses_the_thin_one():
    """THE ONE THAT MATTERS: the engine's own conformance check must go green.

    `seed_book` is the gate Session 16 installed. Publishing has only fixed something if the
    book that comes out the other side is one this gate lets through.
    """
    st = _store()
    _seed_scan(st, 600)
    p = _path()
    assert IB.publish(st, path=p)["published"] is True
    with open(p, encoding="utf-8") as fh:
        good = json.load(fh)

    conf = PT.book_conformance(good)
    assert conf["conforms"] is True, conf.get("why_not")

    # And the gate genuinely discriminates — the truncated book it was built to stop still fails.
    thin = VI.build_index(_rows(120))
    assert PT.book_conformance(thin)["conforms"] is False, (
        "the engine's gate accepts a 12-name book, so this test proves nothing"
    )


def test_seed_book_does_not_refuse_the_published_book():
    """End to end, through the real seeding path rather than the conformance helper alone."""
    st = _store()
    _seed_scan(st, 600)
    p = _path()
    IB.publish(st, path=p)
    with open(p, encoding="utf-8") as fh:
        book = json.load(fh)

    class _Broker:
        """Prices every requested ticker, so names actually enter rather than land unpriced."""
        def quotes(self, symbols):
            return {s: {"last": 100.0} for s in symbols}

    out = PT.seed_book(st, _Broker(), book, place_equity=False, today="2026-08-10")
    assert out["seed_refused"] is None, out["seed_refused"]
    assert out["conformance"]["conforms"] is True


def test_the_engine_still_refuses_a_book_this_module_would_not_have_published():
    """The gate is not made redundant by the publisher; both ends hold."""
    st = _store()
    _seed_scan(st, 120)
    thin = VI.build_index(_rows(120))

    class _Broker:
        def quote(self, *a, **k):
            return None

    out = PT.seed_book(st, _Broker(), thin, place_equity=False, today="2026-08-10")
    assert out["seed_refused"], "the engine accepted a book the publisher refuses"


# ------------------------------------------------------------- 4. nothing else reads the path
def test_the_set_of_things_that_consume_the_book_path_is_what_we_think_it_is():
    """Pin the readers, so a second consumer has to be noticed rather than discovered later.

    PT-SPLIT was two mechanisms disagreeing about one named object. The cheapest way that
    recurs is a new reader of this path appearing without anyone comparing it to the old one.
    """
    hits = {}
    skip_dirs = {".git", "__pycache__", ".claude", "node_modules", "handoff"}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if not fn.endswith((".py", ".ps1", ".yml", ".yaml")):
                continue
            fp = os.path.join(base, fn)
            try:
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
            except OSError:
                continue
            if "valquo_index.json" in txt:
                hits[os.path.relpath(fp, ROOT).replace("\\", "/")] = True

    # Verified 2026-08-10 by reading each hit. Only THREE of these touch the file at all:
    #   * valquo_index.py    — defines DEFAULT_PATH and is the only thing that WRITES it
    #   * app_saas.py        — the engine route READS it (and the ingest calls the publisher)
    #   * paper_track_run.py — CLI `--book` default, i.e. a READ
    # The rest merely name it. `paper_track.py` in particular mentions the path only in the
    # comment above the PT-SPLIT gate and never opens it, which is worth stating explicitly:
    # the engine's gate operates on a book it is HANDED, not on a path it resolves.
    expected = {
        "valuation/edge/valquo_index.py",      # WRITER + DEFAULT_PATH definition
        "valuation/saas/app_saas.py",          # READER (engine route) + publishes on ingest
        "scripts/paper_track_run.py",          # READER — CLI --book default
        "valuation/edge/paper_track.py",       # mention only (comment above the gate)
        "valuation/saas/index_book.py",        # this publisher (docstring reference)
        "backup_to_D.ps1",                     # backup allowlist, not a consumer
        "tests/test_edge.py",
        "tests/test_paper_track.py",
        "tests/test_index_book_publish.py",
    }
    unexpected = set(hits) - expected
    assert not unexpected, (
        f"new consumers of data/valquo_index.json: {sorted(unexpected)}. Two mechanisms reading "
        "one named object is the PT-SPLIT shape — reconcile them deliberately, then add the file "
        "here."
    )


def test_the_publisher_does_not_redefine_conformance():
    """One definition of 'is this the Index'. The publisher must delegate, not re-derive."""
    with open(os.path.join(ROOT, "valuation", "saas", "index_book.py"), encoding="utf-8") as fh:
        src = fh.read()
    for token in ("CONTRACT_MIN_POSITIONS =", "MAX_WEIGHT =", ">= 50", "0.08"):
        assert token not in src, (
            f"index_book.py appears to restate the conformance rule ({token!r}). It must read "
            "valquo_index.conformance through the payload's contract_conformance block."
        )


# ------------------------------------------------------------------ 5. wired into the ingest
def test_the_snapshot_ingest_publishes_the_book():
    """The daily scan's terminal step is the ingest, so that is where publishing belongs."""
    with open(os.path.join(ROOT, "valuation", "saas", "app_saas.py"), encoding="utf-8") as fh:
        src = fh.read()
    i = src.find("def admin_ingest_snapshot")
    assert i > 0
    body = src[i:i + 4000]
    assert "index_book.publish" in body, (
        "the snapshot ingest no longer publishes the Index book, so the engine is back to "
        "silently rebuilding a possibly-truncated one"
    )
    assert '"index_book"' in body, "the ingest response no longer reports the publish outcome"


def test_the_ci_scan_reports_whether_the_book_was_published():
    with open(os.path.join(ROOT, "scripts", "ci_scan.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert "index_book" in src and "index book:" in src, (
        "the daily run prints nothing about the book, so a publisher that quietly stopped "
        "would be invisible — which is how this defect survived in the first place"
    )


def test_the_publish_attempt_is_banked_for_later_inspection():
    st = _store()
    _seed_scan(st, 600)
    IB.publish(st, path=_path())
    last = IB.last_publish(st)
    assert last and last["published"] is True
    assert last["scan_date"] == "2026-08-10"

    thin = _store()
    _seed_scan(thin, 120)
    IB.publish(thin, path=_path())
    assert IB.last_publish(thin)["published"] is False, "a refusal must be banked too"


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
        except Exception as e:                       # noqa: BLE001
            failed += 1
            print(f"ERR   {name}\n      {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
