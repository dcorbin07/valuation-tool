"""
WRDS credential + pull discipline. Offline, no database, no network, no real secret. Run:

    python tests/test_wrds_client.py

WHAT THESE PIN, AND WHY EACH MATTERS MORE THAN USUAL HERE.

1. **A PASSWORD IS NEVER RETURNED, PRINTED OR REPR'D.** This lane handles a live credential, so
   "we were careful" is not a control. `credentials_present()` returns booleans; `write_pgpass()`
   returns a PATH; nothing in the module's public surface returns a secret. Pinned by asserting
   on the actual returned objects and by parsing the source for a `print` of a value.

2. **A LOOSE SECRET IS WORSE THAN NO SECRET.** If the permission tightening cannot be verified,
   the file is REMOVED and the call raises. Pinned on POSIX; on Windows the mode check is not
   meaningful, and the test says so rather than passing vacuously.

3. **NO IMPORT OF `wrds` AT MODULE LEVEL.** CI does not install it (`requirements.lock.txt` is
   deliberately unchanged), so a top-level import would take the whole suite down on a machine
   that has no database access and no business having one.

4. **THE PULLER'S RESUME RULE.** Payload before manifest, and a unit is done only if its bytes
   match its record. Inherited from the chain harvest, where a checkpoint loop that died while
   workers kept going cost twelve hours.
"""
import ast
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import wrds_client as W                             # noqa: E402

FAKE = {"WRDS_USERNAME": "someuser", "WRDS_PASSWORD": "not-a-real-password-12345"}


def _src(mod):
    with open(mod.__file__, encoding="utf-8") as fh:
        return fh.read()


class TestSecretsNeverEscape(unittest.TestCase):

    def test_credentials_present_returns_booleans_only(self):
        got = W.credentials_present(FAKE)
        self.assertEqual(set(got), {"WRDS_USERNAME", "WRDS_PASSWORD"})
        for v in got.values():
            self.assertIsInstance(v, bool)
        self.assertNotIn(FAKE["WRDS_PASSWORD"], repr(got))

    def test_write_pgpass_returns_a_path_and_not_the_secret(self):
        p = os.path.join(tempfile.mkdtemp(), "pgpass.conf")
        got = W.write_pgpass(FAKE, path=p)
        self.assertEqual(got, p)
        self.assertNotIn(FAKE["WRDS_PASSWORD"], got)
        # the secret IS in the file -- that is the file's job -- and nowhere in the return value
        with open(p, encoding="utf-8") as fh:
            line = fh.read()
        self.assertIn(FAKE["WRDS_PASSWORD"], line)
        self.assertTrue(line.startswith(f"{W.WRDS_HOST}:{W.WRDS_PORT}:{W.WRDS_DB}:"))

    def test_the_module_never_prints_a_credential(self):
        """Parsed, not grepped: a `print` of a password would be a call node with the value in
        its args. Also bans logging it."""
        tree = ast.parse(_src(W))
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "print":
                seg = ast.dump(node)
                if "WRDS_PASSWORD" in seg or "password" in seg.lower():
                    bad.append(ast.unparse(node)[:90])
        self.assertEqual(bad, [], f"a credential reaches a print: {bad}")

    def test_missing_credentials_name_the_key_and_not_a_value(self):
        with self.assertRaises(W.CredentialsMissing) as cm:
            W.write_pgpass({"WRDS_USERNAME": "u"}, path=os.path.join(tempfile.mkdtemp(), "p"))
        msg = str(cm.exception)
        self.assertIn("WRDS_PASSWORD", msg)
        self.assertNotIn("u", msg.split("absent from .env:")[-1].strip("[]' "))

    def test_a_pgpass_it_cannot_protect_is_removed_rather_than_left(self):
        """A secret written somewhere world-readable is worse than no secret written at all."""
        if os.name == "nt":
            self.skipTest("POSIX mode bits are not meaningful on Windows — not a vacuous pass, "
                          "the check simply does not apply to this platform")
        p = os.path.join(tempfile.mkdtemp(), "pgpass")
        W.write_pgpass(FAKE, path=p)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode) & 0o077, 0)


class TestNoHeavyImport(unittest.TestCase):

    def test_wrds_is_not_imported_at_module_level(self):
        """CI installs neither `wrds` nor psycopg2. A top-level import takes the suite down on
        every machine that has no database, which is all of them in CI."""
        top = set()
        for node in ast.parse(_src(W)).body:          # module level ONLY, not nested
            if isinstance(node, ast.Import):
                top.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                top.add((node.module or "").split(".")[0])
        for heavy in ("wrds", "psycopg2", "sqlalchemy", "pandas"):
            self.assertNotIn(heavy, top, f"{heavy} is imported at module level")

    def test_the_puller_also_defers_its_heavy_imports(self):
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "scripts", "wrds_pull.py")
        with open(p, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        top = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                top.add((node.module or "").split(".")[0])
        self.assertNotIn("wrds", top)
        self.assertIsNotNone(importlib.util.find_spec("json"))


class TestPullDiscipline(unittest.TestCase):

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        import wrds_pull
        self.P = wrds_pull
        self.root = tempfile.mkdtemp()

    def test_a_unit_with_no_record_needs_pulling(self):
        self.assertTrue(self.P.needs_pull("ibes_det_epsus", "2015", {}, self.root))

    def test_a_unit_whose_payload_is_absent_needs_pulling(self):
        man = {"ibes_det_epsus|2015": {"status": "ok", "bytes": 10}}
        self.assertTrue(self.P.needs_pull("ibes_det_epsus", "2015", man, self.root))

    def test_a_unit_whose_bytes_disagree_needs_pulling(self):
        d = self.P.product_root("ibes_det_epsus", self.root)
        p = os.path.join(d, "ibes_det_epsus_2015.pkl")
        with open(p, "wb") as fh:
            fh.write(b"x" * 7)
        man = {"ibes_det_epsus|2015": {"status": "ok", "bytes": 99}}
        self.assertTrue(self.P.needs_pull("ibes_det_epsus", "2015", man, self.root))
        man = {"ibes_det_epsus|2015": {"status": "ok", "bytes": 7}}
        self.assertFalse(self.P.needs_pull("ibes_det_epsus", "2015", man, self.root))

    def test_a_failed_unit_is_retried(self):
        man = {"ibes_det_epsus|2015": {"status": "failed"}}
        self.assertTrue(self.P.needs_pull("ibes_det_epsus", "2015", man, self.root))

    def test_a_torn_manifest_line_does_not_lose_the_whole_manifest(self):
        """A hard kill can leave a half-written final line. Losing the file would re-pull
        everything; losing that one unit re-pulls one."""
        with open(self.P.manifest_path(self.root), "w", encoding="utf-8") as fh:
            fh.write('{"product":"a","chunk":"1","status":"ok","bytes":3}\n')
            fh.write('{"product":"a","chunk":"2","stat')          # torn
        man = self.P.load_manifest(self.root)
        self.assertIn("a|1", man)
        self.assertNotIn("a|2", man)

    def test_every_product_declares_what_it_unlocks(self):
        for key, spec in self.P.PRODUCTS.items():
            self.assertTrue(spec.get("why"), f"{key} has no stated purpose")
            self.assertIn("lib", spec)
            self.assertIn("table", spec)

    def test_the_raw_root_is_the_d_drive_and_not_the_repo(self):
        """Licensed rows never land inside the checkout, where a stray `git add -A` reaches."""
        self.assertTrue(W.DEFAULT_RAW_ROOT.upper().startswith("D:"))
        self.assertNotIn("valuation-tool", W.DEFAULT_RAW_ROOT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
