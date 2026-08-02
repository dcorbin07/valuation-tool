"""
insider_poller.py — intraday near-real-time insider-buy flags.

Runs every 30–60 min during market hours (separate cron from the daily pipeline).
Pulls EDGAR's recent Form-4 firehose, parses each filing, and posts an alert for
open-market BUYS at or above the configured dollar threshold — throttled, and
de-duplicated against filings already seen.

Run:
    python insider_poller.py
    python insider_poller.py --dry-run
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import config as C
import edgar
import discord_alerts as discord
from store import Store

DRY_RUN = "--dry-run" in sys.argv  # run fully but print instead of posting (no trading here)
DB_PATH = os.getenv("SCREENER_DB", "screener.db")


def run():
    store = Store(DB_PATH)
    throttle_rows = store.recent_alerts()
    from decisions import AlertThrottle
    throttle = AlertThrottle(throttle_rows)

    seen = _load_seen(store)
    for item in edgar.recent_form4(max_items=100):
        url = item.get("url")
        if not url or url in seen:
            continue
        _mark_seen(store, url)
        try:
            # the atom link points to the filing index; fetch and find the .xml doc
            txns = _parse_from_index(url)
        except Exception:
            continue
        for t in txns:
            if t.get("code") == "P" and float(t.get("value_usd") or 0) >= C.INSIDER_ALERT_USD:
                tkr = t.get("ticker") or "?"
                if throttle.allow(tkr, datetime.now()):
                    discord.post(
                        "insider_flags",
                        f"🟢 Insider buy — {tkr}",
                        f"{t.get('role','insider')} {t.get('person','')} bought "
                        f"~${int(t['value_usd']):,} (open market).", dry_run=DRY_RUN)
                    store.log_alert(datetime.now(), tkr, "insider_buy", url)


def _parse_from_index(index_url):
    """From a filing index URL, locate the Form 4 XML and parse it."""
    import requests
    base = index_url.rsplit("/", 1)[0]
    r = requests.get(index_url, headers=edgar.HEADERS, timeout=20)
    r.raise_for_status()
    # find the primary .xml document referenced in the index page
    import re
    m = re.search(r'href="([^"]+\.xml)"', r.text)
    if not m:
        return []
    doc = m.group(1)
    xml_url = doc if doc.startswith("http") else f"{base}/{doc.split('/')[-1]}"
    xr = requests.get(xml_url, headers=edgar.HEADERS, timeout=20)
    xr.raise_for_status()
    return edgar._parse_form4_xml(xr.text)


# tiny dedup store reusing the alerts table's detail column
def _load_seen(store):
    rows = store.db.execute("SELECT detail FROM alerts WHERE kind='seen_f4'").fetchall()
    return {r[0] for r in rows}


def _mark_seen(store, url):
    store.db.execute("INSERT INTO alerts VALUES (?,?,?,?)",
                     (datetime.now().isoformat(), "", "seen_f4", url))
    store.db.commit()


if __name__ == "__main__":
    run()
