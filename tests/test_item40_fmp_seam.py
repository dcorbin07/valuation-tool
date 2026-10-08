# -*- coding: utf-8 -*-
"""ITEM 40 — the FMP seam is measured, and NOTHING is enabled.

`prices.py`'s FMP rung is fail-closed behind `PRICES_ALLOW_FMP` with a stated precondition:
*"its seam against the recorded series is unmeasured ... Measure the seam first."* Item 40 is
that measurement. The conclusion was **do not enable**, for three reasons that these tests pin:

* **the configured URL is dead** — FMP retired `/api/v3/`, so the rung would fail for every name;
* **the plan serves ~12% of names and 0 of 16 REITs / 0 of 10 regulated utilities**;
* **the allowance is ~250 requests/day with no bulk**, against a ~1,492-name universe.

WHAT THESE TESTS ARE REALLY FOR. The measurement is a snapshot; the DANGER is that somebody
reads "the seam is clean" (it is — 0.0000% on the names it serves) and enables the rung without
the coverage half. So:

* the gate must stay CLOSED in the shipped tree;
* the measurement must not be able to enable it, even by accident;
* the dead-v3 call sites are an ALLOWLIST OF TWO — a third cannot appear silently, and removing
  one is a deliberate change that shows in the diff;
* the key must never be printable.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from tests.source_bounds import code_only, function_source                 # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAM = os.path.join(REPO, "scripts", "fmp_seam.py")
DOC = os.path.join(REPO, "FMP_SEAM.md")


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def flowed(text):
    """Markdown with its line breaks collapsed, so a needle may span a wrap.

    THE CHARACTER-WINDOW DEFECT IN A NEW COSTUME: matching "0 of 10 regulated utilities" against
    raw markdown fails because the paragraph wraps between the last two words, so re-flowing a
    correct document takes the guard red. The PROPERTY is that the document states the figure,
    not that it states it on one line.
    """
    return " ".join(text.split())


def py_files():
    for base in ("valuation", "scripts"):
        for root, _d, files in os.walk(os.path.join(REPO, base)):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(root, f)


class TheGateStaysClosed(unittest.TestCase):
    """Measuring a seam is not a licence to open it. Don decides after reading the numbers."""

    def test_no_shipped_file_sets_the_fmp_price_gate(self):
        """`PRICES_ALLOW_FMP=1` must appear nowhere that could switch the rung on.

        A test that saves and RESTORES the variable is fine (`test_price_routing.py` does), so
        the ban is on ASSIGNING the enabling value in product code or a workflow.
        """
        offenders = []
        for p in py_files():
            if os.path.basename(p) == "fmp_seam.py":
                continue                    # its docstring explains the gate; it never sets it
            src = read(p)
            for form in ('PRICES_ALLOW_FMP"] = "1"', "PRICES_ALLOW_FMP'] = '1'",
                         'environ["PRICES_ALLOW_FMP"] = "true"'):
                if form in src:
                    offenders.append(os.path.relpath(p, REPO))
        self.assertEqual(offenders, [], "a shipped file enables the FMP price rung")

    def test_no_workflow_sets_it_either(self):
        wf = os.path.join(REPO, ".github", "workflows")
        if not os.path.isdir(wf):
            self.skipTest("no workflows directory in this checkout")
        for f in sorted(os.listdir(wf)):
            if not f.endswith(".yml"):
                continue
            src = read(os.path.join(wf, f))
            self.assertNotIn("PRICES_ALLOW_FMP", src,
                             "%s passes the FMP price gate to a job" % f)

    def test_the_measurement_cannot_enable_the_rung(self):
        """It calls FMP directly, so the shipped gate is never exercised and never set.

        Over `code_only`, because the docstring legitimately discusses the variable at length —
        a raw substring ban here would fire on the prose explaining why it is not set, which is
        this project's most-repeated guard defect.
        """
        code = code_only(read(SEAM))
        self.assertNotIn("PRICES_ALLOW_FMP ] =", code)
        self.assertNotIn("_fmp_history", code,
                         "the measurement must not route through the shipped gated function")
        # ...and the positive property, so the ban cannot pass by seeing nothing. NOTE the
        # SPACING: `code_only` separates tokens (item 39 made it, because joining them with
        # nothing let unrelated tokens fuse into a false match), so the unspaced form of this
        # needle can never match and the first cut of this assertion could not pass.
        self.assertIn("os . environ . get", code)


class TheDeadEndpointsAreAnAllowlist(unittest.TestCase):
    """FMP retired `/api/v3/`. Two of our files still call it; a THIRD must not appear."""

    #: Measured 2026-10-08: every `financialmodelingprep.com/api/v3/...` path answers 403
    #: "Legacy Endpoint". These two are KNOWN and are listed with their consequence rather than
    #: fixed, because repointing them is a behaviour change on a vendor whose coverage is ~12%
    #: and whose allowance is ~250/day -- `sector_resolve` alone would need 507 calls per scan.
    KNOWN_DEAD = {"valuation/screener/prices.py", "valuation/data/sector_resolve.py"}

    def test_exactly_the_known_files_call_the_retired_fmp_api(self):
        """SHRINKING this set is the good direction and must still show in a diff.

        A new one is the failure that matters: somebody adding an `api/v3` FMP call would be
        adding a call that cannot succeed, and it would fail silently behind a `try/except`
        exactly as these two do.
        """
        found = set()
        for p in py_files():
            if os.path.basename(p) == "fmp_seam.py":
                continue                    # it probes v3 deliberately, to show it is dead
            if "financialmodelingprep.com/api/v3" in read(p):
                found.add(os.path.relpath(p, REPO).replace("\\", "/"))
        self.assertEqual(
            found, self.KNOWN_DEAD,
            "the set of files calling FMP's RETIRED v3 API changed. Added one? It cannot "
            "succeed (403 Legacy). Fixed one? Update KNOWN_DEAD in the same commit, and read "
            "FMP_SEAM.md first -- repointing sector_resolve costs 507 requests per scan "
            "against a ~250/day allowance.")

    def test_the_sharadar_v3_urls_are_not_confused_with_fmps(self):
        """`data.nasdaq.com/api/v3/...` is SHARADAR and is alive. Different vendor, same path
        fragment -- a grep for `api/v3` hits both, and conflating them would either exempt a
        dead FMP call or condemn a working Sharadar one."""
        hits = [os.path.relpath(p, REPO) for p in py_files()
                if "data.nasdaq.com/api/v3" in read(p)]
        self.assertTrue(hits, "the Sharadar v3 URLs vanished; this guard now proves nothing")
        for p in hits:
            self.assertNotIn(p.replace("\\", "/"),
                             TheDeadEndpointsAreAnAllowlist.KNOWN_DEAD)


class TheKeyIsNeverPrintable(unittest.TestCase):
    """FMP puts the key in the QUERY STRING, so an exception carries it verbatim."""

    def test_the_measurement_scrubs_every_message_it_prints(self):
        src = read(SEAM)
        self.assertIn("def scrub(", src)
        body = function_source(SEAM, "scrub")
        self.assertIn("replace(key", body)

    def test_it_reads_the_key_from_the_environment_and_never_opens_dotenv(self):
        """The standing rule is never to read `.env`. The app's own loader populates the
        environment, which is a different thing from this file opening the file."""
        code = code_only(read(SEAM))
        self.assertNotIn(".env", code)
        self.assertIn("FMP_API_KEY", read(SEAM))
        self.assertIn("load_dotenv", read(SEAM),
                      "say WHERE the key comes from, or the next reader opens .env to find out")

    def test_the_key_is_not_in_the_committed_doc_or_the_script(self):
        """A 32-character hex-ish token would be the shape to look for; assert the obvious
        spelling is absent from both, so a paste cannot survive review."""
        for path in (SEAM, DOC):
            src = read(path)
            for marker in ("apikey=", "FMP_API_KEY="):
                for line in src.splitlines():
                    if marker in line and "<FMP_KEY>" not in line:
                        # A bare mention is fine; a mention followed by a long token is not.
                        tail = line.split(marker, 1)[1]
                        token = tail.strip().strip('"\'')[:40]
                        self.assertFalse(
                            len(token) >= 20 and token.isalnum(),
                            "%s may contain a pasted key: %r" % (os.path.basename(path),
                                                                 marker))


class TheMeasurementIsStatedAndReproducible(unittest.TestCase):

    def test_the_sample_contains_every_category_the_brief_named(self):
        """Banks, REITs, ADRs and recent splitters -- plus utilities, because item 38's group
        is about them. A random 200 from a megacap hot list does not reliably contain a REIT,
        and the REITs are where the answer was: 0 of 16 served."""
        import importlib
        m = importlib.import_module("scripts.fmp_seam")
        for name in ("BANKS", "REITS", "ADRS", "SPLITTERS", "UTILITIES"):
            self.assertTrue(getattr(m, name), "the %s block is empty" % name)
        # The categories must cover at least 60 names before any live call, so the sample is
        # not a hot-list snapshot wearing a category label.
        self.assertGreaterEqual(len(m.CATEGORY), 60)

    def test_the_sample_sizes_MATCH_the_figures_the_doc_publishes(self):
        """A CROSS-CHECK, not a threshold -- and mutation is why.

        The first cut asserted `len(REITS) >= 10`, so DROPPING a REIT passed while the document
        went on saying "16 REITs" and "0 of 16 REITs". A published figure that describes a
        sample which no longer exists is the `MA13` shape: two copies of one fact, and the
        quotable one drifts. These are the two copies, held together.
        """
        import importlib
        m = importlib.import_module("scripts.fmp_seam")
        doc = flowed(read(DOC))
        for n, label in ((len(m.BANKS), "banks"), (len(m.REITS), "REITs"),
                         (len(m.ADRS), "ADRs"),
                         (len(m.UTILITIES), "regulated utilities"),
                         (len(m.SPLITTERS), "recent splitters")):
            self.assertIn("%d %s" % (n, label), doc,
                          "the sample has %d %s and FMP_SEAM.md does not say so" % (n, label))
        # ...and the headline coverage figure names the REIT count, so it moves with the list.
        self.assertIn("0 of %d REITs" % len(m.REITS), doc)
        self.assertIn("0 of %d regulated utilities" % len(m.UTILITIES), doc)

    def test_every_splitter_carries_its_split_AND_its_date(self):
        """A split comparison that does not straddle a real corporate action measures nothing."""
        import importlib
        m = importlib.import_module("scripts.fmp_seam")
        for t, split, date in m.SPLITTERS:
            self.assertRegex(split, r"^\d+:\d+$", t)
            self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$", t)
            self.assertEqual(m.SPLIT_DATE[t], (split, date))

    def test_the_pull_aborts_on_a_quota_response_rather_than_hammering(self):
        """The allowance is shared with the nightly scan, so a measurement that exhausts it has
        broken its own subject. `quota_shaped` is the test, and it is checked BOTH ways."""
        import importlib
        m = importlib.import_module("scripts.fmp_seam")
        self.assertTrue(m.quota_shaped(429, ""))
        self.assertTrue(m.quota_shaped(200, 'Limit Reach . Please upgrade your plan'))
        self.assertTrue(m.quota_shaped(200, "quota exceeded"))
        # A SYMBOL refusal is NOT a quota refusal: treating 402 as quota would abort the pull
        # on the first REIT and report a coverage finding as an allowance finding.
        self.assertFalse(m.quota_shaped(402, "Premium Query Parameter: 'Special Endpoint"))
        self.assertFalse(m.quota_shaped(200, ""))

    def test_an_empty_200_is_told_apart_from_a_parse_failure_and_from_data(self):
        """FMP really returns an empty 200, and `r.json()` raises on it even with a JSON
        content-type -- which is how the ticker `O` first looked like a missing symbol."""
        src = read(SEAM)
        self.assertIn("EMPTY BODY", src)

    def test_the_doc_carries_the_measured_figures_and_the_verdict(self):
        """The conclusion must not be able to drift from the numbers it rests on."""
        doc = flowed(read(DOC))
        for needle in ("do not enable", "403", "Legacy", "0 of 16 REITs",
                       "0 of 10 regulated utilities", "250", "14 of 121", "0.0000%",
                       "6 of 6", "append-only"):
            self.assertIn(needle, doc, "FMP_SEAM.md no longer states %r" % needle)

    def test_the_doc_says_what_it_must_never_feed(self):
        doc = flowed(read(DOC)).lower()
        for needle in ("forward track record", "paper-track", "f-11"):
            self.assertIn(needle, doc)

    def test_the_doc_names_what_was_NOT_measured(self):
        """The symbol-vs-endpoint question is unresolved because the allowance ran out, and an
        unmeasured thing reported as measured is the failure this project pays for most."""
        doc = flowed(read(DOC))
        self.assertIn("could not measure", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
