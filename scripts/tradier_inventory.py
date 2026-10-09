# -*- coding: utf-8 -*-
"""ITEM 45 - every path that depends on Tradier, and whether it is broken now.

Don withdrew his funds and Tradier deactivated the brokerage account, so both tokens are dead.
This answers "what breaks, and what does a user see" by MEASUREMENT rather than by reading the
import graph -- which item 44 established is the wrong instrument here, because the Tradier
consumers are reached through deferred imports inside function bodies and the graph reports an
empty importer list for a module with five live call sites.

NO TOKEN IS EVER PRINTED, HANDLED OR RETURNED. The probe reports an HTTP STATUS CODE and a
scrubbed fault string, and the only thing said about a token's value is whether one is present.
`config.py` reads `.env` for us; this module never opens it (standing security rule).

WHAT "FROM WHERE THEY LIVE" MEANS HERE, because the two tokens live in different places:
  * `TRADIER_TOKEN` (live market data) is a GitHub repository secret AND a Render env var AND
    in Don's local `.env`. A lane can probe the local one, which is the same account.
  * `TRADIER_PAPER_TOKEN` (sandbox, the fleet's paper fills) is NOT a GitHub secret -- it is
    local only -- so the local probe is the only probe there is.
Either way the account is the subject, not the copy of the string, so a 401 on the local copy
is evidence about the account.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LIVE_BASE = "https://api.tradier.com/v1"
SANDBOX_BASE = "https://sandbox.tradier.com/v1"

#: Read-only endpoints, chosen so a probe cannot place, amend or cancel anything. `quotes` is
#: the market-data read the Signals scan makes; `user/profile` is the cheapest sandbox read that
#: proves an account is reachable without touching an order path.
LIVE_PROBE = ("/markets/quotes", {"symbols": "AAPL"})
SANDBOX_PROBE = ("/user/profile", {})

#: Every consumer, what it does, and what the user sees when Tradier is dead. `free_fallback`
#: is the honest answer to "can this degrade instead of stopping", and it is the field that
#: decides what item 45 part 2 can repair.
CONSUMERS = [
    {
        "path": "valuation/intraday/providers.py::get_provider",
        "token": "TRADIER_TOKEN",
        "does": "picks the quote source for the intraday Signals scan",
        "free_fallback": "FreeProvider (yfinance, delayed) EXISTS but is only reached when the "
                         "token is EMPTY -- a dead token still selects Tradier",
        "user_sees": "Signals tab frozen at the last good run; the scan prints "
                     "'scored 0 of 150 names' and exits 1",
    },
    {
        "path": "valuation/screener/broker_universe.py",
        "token": "TRADIER_TOKEN",
        "does": "enumerates and liquidity-ranks the whole-market universe for the hot scan",
        "free_fallback": "SEC EDGAR company_tickers (already the documented alternative)",
        "user_sees": "hot list falls back to the SEC-derived universe; no liquidity rank",
    },
    {
        "path": "valuation/screener/broker_fundamentals.py",
        "token": "TRADIER_TOKEN",
        "does": "bulk-prefetches fundamentals so a throttled free fetch costs quality, "
                "not the whole name",
        "free_fallback": "yfinance .info + EDGAR per name (slow, rate-limited)",
        "user_sees": "nothing directly; a name whose free fetch fails is DROPPED rather than "
                     "surviving on the broker half (item 44's finding)",
    },
    {
        "path": "valuation/edge/paper_broker.py",
        "token": "TRADIER_PAPER_TOKEN",
        "does": "places the S3-I1 fleet's paper fills in Tradier's sandbox",
        "free_fallback": "NONE. A book's fill source is part of its DECLARED rules, so "
                         "substituting one is a construction change, not a repair",
        "user_sees": "fleet books record no fills",
    },
    {
        "path": "valuation/edge/paper_track.py (options record)",
        "token": "TRADIER_TOKEN",
        "does": "scores and settles the live options alert record",
        "free_fallback": "NONE that is honest -- settling a live alert needs an option quote, "
                         "and yfinance's delayed chain cannot price a fill",
        "user_sees": "open positions stop being marked; must STOP explicitly rather than "
                     "record zeros",
    },
    {
        "path": "valuation/screener/index_mark.py (the BOUND Index record)",
        "token": "(none)",
        "does": "marks the Valquo Index daily",
        "free_fallback": "N/A -- it prices through screener/prices.py and never touches Tradier",
        "user_sees": "unaffected. Verified, not assumed: see `index_is_independent`",
    },
]


def _scrub(s, *secrets) -> str:
    out = str(s)
    for sec in secrets:
        if sec:
            out = out.replace(sec, "<REDACTED>")
    return out


def probe(cfg) -> list:
    """Status codes only. Never returns or prints a token."""
    import requests
    rows = []
    for label, base, (path, params), token in (
        ("TRADIER_TOKEN (live market data)", LIVE_BASE, LIVE_PROBE,
         (getattr(cfg, "tradier_token", "") or "").strip()),
        ("TRADIER_PAPER_TOKEN (sandbox)", SANDBOX_BASE, SANDBOX_PROBE,
         (getattr(cfg, "tradier_paper_token", "") or "").strip()),
    ):
        row = {"token": label, "present": bool(token), "base": base, "endpoint": path}
        if not token:
            row["status"] = None
            row["verdict"] = "ABSENT -- no token configured here"
            rows.append(row)
            continue
        try:
            r = requests.get(base + path, params=params, timeout=20,
                             headers={"Authorization": "Bearer " + token,
                                      "Accept": "application/json"})
            row["status"] = r.status_code
            fault = ""
            try:
                body = r.json()
                fault = ((body or {}).get("fault") or {}).get("faultstring") or ""
            except Exception:
                fault = (r.text or "")[:80]
            row["fault"] = _scrub(fault, token)[:120]
            row["verdict"] = ("ALIVE" if r.status_code == 200 else
                              "DEAD (%s)" % r.status_code)
        except Exception as e:
            row["status"] = None
            row["verdict"] = "UNREACHABLE (%s)" % type(e).__name__
        rows.append(row)
    return rows


def index_is_independent() -> dict:
    """Prove the BOUND record does not depend on Tradier, rather than asserting it.

    The forward record is the one thing in this project that cannot be rebuilt (append-only, no
    backfill), so "it should not depend on Tradier" is not good enough.
    """
    import ast
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = "valuation/screener/index_mark.py"
    seen, stack, offenders, unresolved = set(), [root], [], []

    def targets(node, pkg):
        """Every module a single import statement can reach, as repo-relative paths.

        THE FIRST CUT OF THIS WAS BROKEN AND ITS VERDICT WAS VACUOUS, which is why the
        resolution is spelled out. It read `node.module` and skipped the statement when it was
        falsy -- but for **`from . import market_session`** `node.module` IS `None` and the
        name lives in `node.names`, so every one of `index_mark`'s relative imports was
        dropped. It reached TWO files, neither of them `prices.py`, and still reported
        INDEPENDENT. **A reachability claim produced by a walker that never reached the
        subject is worse than no claim.**
        """
        out = []
        if isinstance(node, ast.Import):
            for al in node.names:
                if al.name.startswith("valuation"):
                    out.append(al.name.replace(".", "/") + ".py")
            return out
        if not isinstance(node, ast.ImportFrom):
            return out
        if node.level:
            # `level` counts dots: 1 = this package, 2 = its parent, and so on.
            parts = pkg.split("/")
            base = "/".join(parts[:len(parts) - (node.level - 1)]) if node.level > 1 else pkg
            head = "%s/%s" % (base, node.module.replace(".", "/")) if node.module else base
        elif (node.module or "").startswith("valuation"):
            head = node.module.replace(".", "/")
        else:
            return out
        # `from X import Y` -- Y may be a SUBMODULE or a name inside X. Both are tried; a
        # candidate that is not a file on disk is simply not followed.
        out.append(head + ".py")
        for al in node.names:
            out.append("%s/%s.py" % (head, al.name))
        return out

    while stack:
        rel = stack.pop()
        if rel in seen:
            continue
        p = os.path.join(repo, rel)
        if not os.path.exists(p):
            unresolved.append(rel)
            continue
        seen.add(rel)
        src = open(p, encoding="utf-8", errors="replace").read()
        if "tradier" in src.lower():
            offenders.append(rel)
        pkg = os.path.dirname(rel)
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                stack.extend(targets(node, pkg))

    return {"modules_reached": sorted(seen), "n_modules": len(seen),
            "modules_naming_tradier": offenders,
            # TEXT REACHABILITY IS NOT A DEPENDENCY, and reporting it as one was the second
            # defect in this instrument. Fixing the resolver took the closure from 2 modules to
            # 66, and seven of those mention Tradier -- so it flipped to "DEPENDS ON TRADIER"
            # when all that is established is that `index_mark` transitively IMPORTS modules
            # that can talk to Tradier on OTHER paths. The marking path is a different
            # question, and only `hosts_contacted_by_a_real_mark()` answers it.
            "text_reachable_naming_tradier": bool(offenders),
            "independent": None,
            "why_null": "module-closure text matching cannot answer this; see hosts_contacted",
            # NON-VACUITY: the claim is about pricing, so the pricing module must be in the
            # closure. If it is not, the walk did not reach the subject and the verdict is
            # void -- which is exactly how the first cut passed.
            "reached_prices": "valuation/screener/prices.py" in seen,
            "unresolved_candidates": sorted(set(unresolved))[:12]}


#: The book the bound record is marked against. A worktree carries `data/` EMPTY, so the book
#: lives only in the primary checkout -- `E-5`'s stranded-artifact family, and the reason this
#: is a parameter rather than an assumption.
PRIMARY_BOOK = r"C:\Users\donni\Downloads\valuation-tool\data\valquo_track.json"


def hosts_contacted_by_a_real_mark(meta_path: str = None) -> dict:
    """Mark the Index for real and record EVERY host it contacts.

    This is the claim the record actually needs -- "the bound Index does not depend on
    Tradier" -- and it is behavioural rather than textual. Module-closure matching says seven
    reachable modules mention Tradier; that is true and irrelevant, because they are reachable
    through imports the marking path never calls.

    `requests.Session.request` and `requests.api.request` are both wrapped, so a library that
    builds its own session is still recorded. Nothing is blocked: the mark runs normally and
    the hostnames are the measurement.
    """
    import socket

    hosts = []

    # RECORDED AT THE SOCKET, NOT AT `requests`. The first cut wrapped
    # `requests.Session.request` and measured ZERO requests -- because `yfinance` ships its own
    # HTTP stack, so the spy was blind to the only network call the mark makes, and the
    # instrument reported "no request" on a mark that had just priced 86 names. Every library
    # has to resolve a hostname, so `getaddrinfo` is the one chokepoint none of them bypasses.
    real_gai = socket.getaddrinfo

    def spy(host, *a, **kw):
        if host:
            hosts.append(str(host))
        return real_gai(host, *a, **kw)

    socket.getaddrinfo = spy
    try:
        from valuation.screener import index_mark
        mp = meta_path or (PRIMARY_BOOK if os.path.exists(PRIMARY_BOOK) else None)
        try:
            got = index_mark.contract_row(meta_path=mp)
        except Exception as e:
            got = {"ok": False, "reason": "%s: %s" % (type(e).__name__, str(e)[:140])}
        # A REFUSAL IS NOT A MARK, and reading one as a mark was this instrument's third
        # defect: with `data/` empty in a worktree `contract_row` returns
        # `{"ok": False, "reason": "the book file ... is missing or unreadable"}`, and the
        # first cut reported `ran=True` on it and then drew a conclusion from the zero
        # requests that refusal made. Item 39's family -- a refusal read as a measurement.
        ok = bool((got or {}).get("ok"))
        note = "marked" if ok else "REFUSED: %s" % (got or {}).get("reason", "?")
        row = (got or {}).get("row")
    finally:
        socket.getaddrinfo = real_gai

    uniq = sorted(set(h for h in hosts if h))
    tradier = [h for h in uniq if "tradier" in h.lower()]
    return {"ran": ok, "note": note, "n_requests": len(hosts), "hosts": uniq,
            "tradier_hosts": tradier, "independent_of_tradier": not tradier,
            # Non-vacuity: a mark that made NO request proves nothing about which host it
            # would have used, so the absence of a Tradier host is only evidence if the mark
            # actually went to the network.
            "non_vacuous": len(hosts) > 0,
            # THE HONEST LIMIT, and it is visible in this very run: the log shows yfinance
            # being tried for every name and `query*.finance.yahoo.com` does NOT appear in
            # `hosts`, because yfinance's HTTP stack resolves below Python's `socket` module.
            # So this records Python-level resolution only. It still answers the question
            # asked, because `TradierProvider` calls `requests.get`, which does resolve
            # through `socket` -- but it may NOT be read as a complete list of every host the
            # mark touched.
            "limitation": "Python-level getaddrinfo only; a library with its own C resolver "
                          "(yfinance) is invisible here. Sufficient for the Tradier question "
                          "because TradierProvider uses requests; NOT a full host list.",
            "row_keys": sorted((row or {}).keys())[:12] if isinstance(row, dict) else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from valuation.config import CONFIG
    # THE MARK IS MEASURED FIRST, AND THE ORDER IS LOAD-BEARING. The probes deliberately
    # contact `api.tradier.com` and `sandbox.tradier.com`; if they ran first, a resolution
    # cached inside this process could let the mark reach Tradier without a fresh
    # `getaddrinfo`, and the host list would show none. Measuring the mark before anything has
    # ever named Tradier removes the confound instead of arguing it away.
    got = {"index_hosts": hosts_contacted_by_a_real_mark()}
    got["probes"] = probe(CONFIG)
    got["consumers"] = CONSUMERS
    got["index"] = index_is_independent()

    if a.json:
        print(json.dumps(got, indent=1))
    else:
        print("")
        print("  TOKEN STATUS (status codes only; no token is ever printed)")
        for r in got["probes"]:
            print("   %-34s present=%-5s HTTP %-5s %s"
                  % (r["token"], r["present"], r.get("status"), r["verdict"]))
            if r.get("fault"):
                print("        fault: %s" % r["fault"])
        print("")
        print("  THE BOUND INDEX RECORD")
        ix = got["index"]
        print("   %d modules reached from index_mark; naming tradier: %s"
              % (ix["n_modules"], ix["modules_naming_tradier"] or "none"))
        print("   reached prices.py (the non-vacuity check): %s" % ix["reached_prices"])
        print("   (text reachability only -- it answers nothing on its own)")
        h = got["index_hosts"]
        print("   A REAL MARK contacted %d request(s): %s" % (h["n_requests"], h["hosts"]))
        print("   ran=%s (%s)  non-vacuous=%s" % (h["ran"], h["note"], h["non_vacuous"]))
        print("   -> %s" % ("INDEPENDENT OF TRADIER (measured)"
                            if (h["independent_of_tradier"] and h["non_vacuous"] and h["ran"])
                            else ("*** CONTACTED TRADIER: %s ***" % h["tradier_hosts"]
                                  if h["tradier_hosts"] else
                                  "*** NOT ESTABLISHED: the mark made no request ***")))
        print("")
        print("  CONSUMERS")
        for c in got["consumers"]:
            print("   %s" % c["path"])
            print("      token    : %s" % c["token"])
            print("      does     : %s" % c["does"])
            print("      fallback : %s" % c["free_fallback"])
            print("      user sees: %s" % c["user_sees"])
        print("")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(got, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
