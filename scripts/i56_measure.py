"""ITEM 56: measure both candidate headline routes, the way item 55 did.

Found / naming the company / kept by the conclusions filter, on NVDA, TSLA, KO, APLD and OCTV.
Route 1 is SEC 8-K press-release exhibits; route 2 is GDELT. Neither is kept unless it earns it.

    python -m scripts.i56_measure
"""
from __future__ import annotations

import sys
import time
import urllib.parse

sys.path.insert(0, ".")

from valuation.data.press_releases import press_releases          # noqa: E402
from valuation.data.recent import SEC_UA                          # noqa: E402

# CIKs, from EDGAR. OCTV is the thin name item 54 left carrying no momentum, so it is the one
# that says whether either route does anything for a small company.
NAMES = [("NVDA", 1045810, "NVIDIA"), ("TSLA", 1318605, "Tesla"),
         ("KO", 21344, "Coca-Cola"), ("APLD", 1144879, "Applied Digital"),
         ("OCTV", None, "Octave Intelligence")]


def _cik_for(ticker):
    """EDGAR's own ticker->CIK map, so OCTV is looked up rather than assumed absent."""
    import requests
    r = requests.get("https://www.sec.gov/files/company_tickers.json",
                     headers={"User-Agent": SEC_UA}, timeout=45)
    if r.status_code != 200:
        return None
    for row in (r.json() or {}).values():
        if str(row.get("ticker", "")).upper() == ticker.upper():
            return int(row.get("cik_str"))
    return None


def route1():
    print("=" * 74)
    print("ROUTE 1 -- press releases filed as 8-K exhibits (SEC EDGAR)")
    print("=" * 74)
    print("%-6s %8s %9s %9s %7s %6s %5s" % ("", "filings", "exhibits", "headings",
                                             "found", "kept", "reqs"))
    tot = {"found": 0, "kept": 0, "reqs": 0}
    for tkr, cik, _name in NAMES:
        if cik is None:
            cik = _cik_for(tkr)
            print("   (%s CIK looked up on EDGAR: %s)" % (tkr, cik))
        d = press_releases(cik)
        print("%-6s %8d %9d %9d %7d %6d %5d"
              % (tkr, d["filings_scanned"], d["exhibits_found"], d["headings_read"],
                 d["n_found"], d["n_shown"], d["requests_spent"]))
        tot["found"] += d["n_found"]
        tot["kept"] += d["n_shown"]
        tot["reqs"] += d["requests_spent"]
        for it in d["items"]:
            print("        [%s] %s" % (it["date"], it["title"][:88]))
            print("                 item %s - %s" % (it["sec_item"], it["sec_item_label"]))
        if d["n_excluded"]:
            print("        excluded %d: %s" % (d["n_excluded"], d["excluded_by_kind"]))
            # WHICH ones, because this is the test of Don's own argument that a filed release
            # is a conclusion by construction. If the filter drops real company announcements,
            # one of the two is wrong and only the titles can say which.
            from valuation.data.headline_rules import classify
            for it in d.get("_all", []):
                c = classify(it["title"])
                if not c["show"]:
                    print("          DROPPED (%s): %s" % (c["kind"], it["title"][:72]))
        if not d["items"]:
            print("        NOTHING: %s" % d["reason"])
    print("\n  TOTAL found %d, kept %d, EDGAR requests %d"
          % (tot["found"], tot["kept"], tot["reqs"]))
    return tot


def route2():
    print("\n" + "=" * 74)
    print("ROUTE 2 -- GDELT DOC 2.0, one cold request per name at 20s spacing")
    print("=" * 74)
    import requests

    from valuation.data.headline_rules import filter_titles

    tot = {"found": 0, "on": 0, "kept": 0, "reachable": 0}
    for tkr, _cik, name in NAMES:
        q = urllib.parse.urlencode({
            "query": '"%s" sourcelang:english' % name, "mode": "artlist",
            "format": "json", "maxrecords": "75", "sort": "datedesc", "timespan": "7d"})
        try:
            r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc?" + q,
                             headers={"User-Agent": SEC_UA}, timeout=60)
        except Exception as e:                                              # noqa: BLE001
            print("  %-6s UNREACHABLE (%s)" % (tkr, type(e).__name__))
            time.sleep(20)
            continue
        if r.status_code != 200:
            print("  %-6s HTTP %s -- %s" % (tkr, r.status_code, r.text.strip()[:58]))
            time.sleep(20)
            continue
        try:
            arts = (r.json() or {}).get("articles") or []
        except Exception:                                                   # noqa: BLE001
            print("  %-6s non-JSON reply" % tkr)
            time.sleep(20)
            continue
        tot["reachable"] += 1
        stem = name.lower().split()[0]
        on = [{"title": str(a.get("title") or ""), "url": a.get("url"),
               "date": str(a.get("seendate") or "")[:8],
               "publisher": str(a.get("domain") or "")}
              for a in arts if stem in str(a.get("title") or "").lower()]
        kept = filter_titles(on)
        doms = sorted({str(a.get("domain")) for a in arts})
        print("  %-6s %3d found | %3d name it | %3d kept by the filter | %d domains"
              % (tkr, len(arts), len(on), kept["n_shown"], len(doms)))
        for it in kept["shown"][:4]:
            print("          %-26s %s" % (it["publisher"][:26], it["title"][:54]))
        if doms:
            print("          domains: %s" % ", ".join(doms[:10]))
        tot["found"] += len(arts)
        tot["on"] += len(on)
        tot["kept"] += kept["n_shown"]
        time.sleep(20)
    print("\n  TOTAL reachable for %d of %d names | found %d, naming the company %d, kept %d"
          % (tot["reachable"], len(NAMES), tot["found"], tot["on"], tot["kept"]))
    return tot


if __name__ == "__main__":
    a = route1()
    b = route2()
    print("\n" + "=" * 74)
    print("VERDICT INPUTS")
    print("  route 1 (SEC 8-K exhibits): %d kept across 5 names, %d EDGAR requests"
          % (a["kept"], a["reqs"]))
    print("  route 2 (GDELT):            %d kept across 5 names, reachable for %d of 5"
          % (b["kept"], b["reachable"]))
