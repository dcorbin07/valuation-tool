"""robots.txt and the sitemap follow the posture (audit 6, D5 — Don, 2026-09-29).

Public: allow everything, point at a sitemap, never name the portfolio path. Private: the
blanket Disallow that tests/test_private.py already pins. And the two pages built to be
found — /proof and /methodology — are in the sitemap, while the portfolio page is not (it
keeps itself out with its own noindex header, which a crawler can only honour if allowed to
fetch it — the reason the old blanket Disallow was backwards)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — temp state only, before `valuation`
from valuation.config import CONFIG                                 # noqa: E402
from valuation.saas.app_saas import app as APP                      # noqa: E402

PORTFOLIO = CONFIG.resolved_portfolio_path


def test_public_posture_allows_crawling_and_points_at_the_sitemap():
    assert not CONFIG.private_mode, "this suite tests the PUBLIC posture; private is in test_private.py"
    with APP.test_client() as c:
        r = c.get("/robots.txt", base_url="http://valquo.co")   # what Render's proxy passes
        assert r.status_code == 200 and r.mimetype == "text/plain"
        txt = r.get_data(as_text=True)
        assert "Allow: /" in txt and "Disallow: /" not in txt, txt
        assert re.search(r"^Sitemap: https://[^\s]+/sitemap\.xml$", txt, re.M), txt
        assert PORTFOLIO.strip("/") not in txt, "robots.txt names the portfolio path"


def test_the_sitemap_lists_the_public_pages_and_not_the_portfolio():
    with APP.test_client() as c:
        r = c.get("/sitemap.xml", base_url="http://valquo.co")
        assert r.status_code == 200 and "xml" in r.mimetype, (r.status_code, r.mimetype)
        body = r.get_data(as_text=True)
        locs = re.findall(r"<loc>([^<]+)</loc>", body)
        assert locs, body
        assert all(u.startswith("https://") for u in locs), locs
        paths = {u.split("/", 3)[3] if u.count("/") >= 3 else "" for u in locs}
        for want in ("proof", "methodology", "app"):
            assert want in paths, (want, paths)
        assert PORTFOLIO.strip("/") not in paths, "the sitemap invites crawlers to the portfolio page"


def test_the_canonical_url_is_https_on_the_real_host():
    """Render's proxy hands Flask http://; a canonical that says http:// on an https-only
    site is the wrong address (MC16). Simulated with the Host header the proxy would pass."""
    with APP.test_client() as c:
        r = c.get("/methodology", base_url="http://valquo.co")
        html = r.get_data(as_text=True)
        m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        assert m, "no canonical on /methodology"
        assert m.group(1).startswith("https://valquo.co"), m.group(1)
        # localhost is left alone so a dev server's canonical is not a lie about itself
        r2 = c.get("/methodology", base_url="http://localhost:5000")
        m2 = re.search(r'<link rel="canonical" href="([^"]+)"', r2.get_data(as_text=True))
        assert m2 and m2.group(1).startswith("http://localhost"), m2 and m2.group(1)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:                                          # noqa: BLE001
            failed += 1; print(f"  ERR  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
