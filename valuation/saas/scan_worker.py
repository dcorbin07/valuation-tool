"""
Server-side weekly worker — run the market scan and email subscribers.

Meant to be triggered by your host's scheduler (Render/Railway cron, a systemd
timer, or plain cron):  `python -m valuation.saas.scan_worker`

On a hosted box this replaces the Windows Task Scheduler job: it refreshes the
snapshot the whole app reads, then sends the weekly digest to opted-in Pro/Premium
subscribers.
"""
from __future__ import annotations

from ..config import CONFIG
from ..screener.screen import run_scan
from ..screener.store import Store
from ..screener.sectors import sector_attractiveness
from .models import UserStore
from .emailer import send_email, weekly_digest_html


def run_weekly(cfg=CONFIG, scope="whole_market", limit=1500, dcf_top=12) -> dict:
    store = Store()
    res = run_scan(scope=scope, limit=limit, cfg=cfg, store=store, run_dcf_top=dcf_top, save=True)
    rows = store.load_snapshot()
    from . import tracker, notify
    tracker.log_hot(store, res["scan_date"], rows, cfg)   # log top-10 + update the paper account
    sectors = sector_attractiveness(rows)
    try:
        notify.post_hot_digest(cfg, store, res["scan_date"], rows, sectors)   # Discord daily top-10
    except Exception:
        pass

    # The Dip Detector digest. SHIPPED AT THE V6-B CLOSE-OUT and gated on that register inside
    # `post_dip_digest`, which refuses unless `dip_posture.RISK_STATUS` is POSITIVE — so this
    # call is safe to leave here permanently: if the risk verdict is ever revised the push stops
    # by itself rather than by someone remembering to delete a line.
    #
    # Wrapped like its neighbour. A digest that raises must not take the weekly email run down
    # with it; the scan and the subscriber mail below are the job, this is an extra.
    try:
        from ..web.app import _get_or_compute
        from ..web import dip as _dip
        _screen = _dip.screen_snapshot(store, _get_or_compute)
        notify.post_dip_digest(cfg, store, res["scan_date"], _screen.get("rows") or [])
    except Exception:
        pass

    users = UserStore(cfg.database_url)
    html = weekly_digest_html(res["scan_date"], rows, sectors)
    sent = 0
    for u in users.subscribers_opted_in():
        if send_email(cfg, u["email"], "🔥 Hot Stocks of the Day", html):
            sent += 1
    return {"scan_date": res["scan_date"], "scored": res["scored"],
            "universe_size": res["universe_size"], "emails_sent": sent}


if __name__ == "__main__":
    print(run_weekly())
