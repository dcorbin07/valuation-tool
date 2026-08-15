"""
Self-learning — a monthly, out-of-sample-gated re-tune of the screener's factor
weights, learned from the tool's OWN accumulated snapshots and realized forward
returns. This is the honest version of "it gets smarter over time":

  1. Build a factor panel from stored daily snapshots (each name's value / quality
     / growth / momentum / insider z-scores on each scan date) + that name's
     realized forward return over `horizon` days.
  2. For each bucket, search weights IN-SAMPLE and validate OUT-OF-SAMPLE.
  3. Adopt the change ONLY if it beats the current weights out-of-sample. That grid
     search + hold-out test is the ENTIRE decision — no LLM in the loop. (An LLM adds
     nothing here: it can't see the data, and the grid already tries every weighting,
     so having it judge or "propose" a weighting is redundant. Where an LLM genuinely
     helps is proposing brand-new FACTORS to implement and test — a separate, on-demand
     research aid, not this loop.) Persist adopted weights for the live scorer and log
     every run (adopted or not) for a full audit trail.

Early on there isn't enough accrued history, so it correctly declines to change
anything until the track record is deep enough — which is exactly right.
"""
from __future__ import annotations

from ..screener import settings as S

# One source of truth for which factors each bucket scores on (settings.py).
_BUCKETS = [
    ("established", S.BUCKET_FACTORS["established"], S.WEIGHTS_ESTABLISHED),
    ("speculative", S.BUCKET_FACTORS["speculative"], S.WEIGHTS_SPECULATIVE),
]

# Legacy snapshots stored only these five as dedicated z_* columns; newer factors
# live in extra["factors"]. We read the dict first and fall back to the columns.
_LEGACY_Z = {"value": "z_value", "quality": "z_quality", "growth": "z_growth",
             "momentum": "z_momentum", "insider": "z_insider"}


def _normalize(w: dict) -> dict:
    tot = sum(max(0.0, v) for v in w.values()) or 1.0
    return {k: round(max(0.0, v) / tot, 3) for k, v in w.items()}


def build_panel_from_snapshots(store, price_fn, top_per_date=60, horizon=21,
                               source_key="factors", columns=None, cache=None):
    """Panel of point-in-time factor/number values + realized forward return, built
    from stored snapshots. source_key selects extra['factors'] (themes) or
    extra['numbers'] (individual numbers). `cache` (dict) can be shared to avoid
    re-fetching prices across two builds."""
    import pandas as pd
    columns = columns or S.FACTORS_ALL
    rows = []
    for s in store.list_scans():
        date = s["scan_date"]
        for r in store.load_snapshot(date, top=top_per_date):
            vals = (r.get("extra") or {}).get(source_key) or {}
            row = {"date": date, "ticker": r["ticker"], "bucket": r.get("bucket")}
            for f in columns:
                v = vals.get(f)
                if v is None and source_key == "factors" and f in _LEGACY_Z:
                    v = r.get(_LEGACY_Z[f])          # legacy snapshots kept the 5 as z_* columns
                row[f] = v
            rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if cache is None:
        cache = {}

    def series(t):
        if t not in cache:
            try:
                d, c = price_fn(t)
                cache[t] = pd.Series(c, index=pd.to_datetime(d)) if (d and c) else None
            except Exception:
                cache[t] = None
        return cache[t]

    fwd = []
    for _, r in df.iterrows():
        sr = series(r["ticker"])
        val = None
        if sr is not None and len(sr):
            i = sr.index.searchsorted(pd.to_datetime(r["date"]))
            if 0 <= i and i + horizon < len(sr) and sr.iloc[i] > 0:
                val = float(sr.iloc[i + horizon] / sr.iloc[i] - 1)
        fwd.append(val)
    df["fwd_ret"] = fwd
    return df.dropna(subset=["fwd_ret"])


def run_learning(cfg, store, price_fn=None, panel=None) -> dict:
    from ..backtest.optimize import optimize_weights
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=1500)
    if panel is None:
        panel = build_panel_from_snapshots(store, price_fn,
                                           top_per_date=cfg.learn_top_per_date,
                                           horizon=cfg.learn_horizon_days)
    report = {"panel_rows": int(len(panel)) if panel is not None else 0,
              "dates": int(panel["date"].nunique()) if (panel is not None and not panel.empty) else 0,
              "buckets": {}}
    if panel is None or panel.empty or panel["date"].nunique() < cfg.learn_min_dates:
        report["status"] = "insufficient data — kept current weights"
        return report

    for bucket, factors, default in _BUCKETS:
        bp = panel[panel["bucket"] == bucket]
        base = store.latest_learned_weights(bucket) or dict(default)
        if bp.empty or bp["date"].nunique() < cfg.learn_min_dates:
            store.save_learned(bucket, base, {"reason": "insufficient bucket data"}, False,
                               "Not enough accrued data for this bucket — kept current weights.")
            report["buckets"][bucket] = {"adopted": False, "note": "insufficient data",
                                         "weights": base, "previous": base}
            continue
        opt = optimize_weights(bp, factors, default_weights=base)
        stats = {k: opt.get(k) for k in ("accepted", "in_sample_ic", "out_sample_ic",
                                         "equal_weight_oos_ic", "n_periods", "verdict")}
        accepted = bool(opt.get("accepted"))       # out-of-sample test is the ENTIRE decision
        rec = _normalize(opt.get("recommended_weights") or base)
        note = opt.get("verdict") or ("adopted out-of-sample" if accepted else "no robust improvement — kept current")
        # MASTER AUDIT MA1 -- THE AMENDMENT 1 GATE. Passing the out-of-sample test is necessary
        # and NOT sufficient. Adopting weights changes the composite the live product scores
        # with, which Amendment 1 defines as a VINTAGE EVENT: it closes the open vintage and
        # opens the next. `VINTAGES` is a literal tuple in Python source and `save_learned`
        # writes a SQLite row, so without this check an adoption would move the live model while
        # the forward track kept accruing under a vintage whose model had already changed --
        # exactly what vintage 1 was voided for.
        #
        # The refusal is RECORDED, not silent: it writes an `adopted=False` row carrying the
        # statistics that would have been adopted, so `learning_history` shows that the learner
        # found an improvement and was refused. A gate whose firing leaves no trace is
        # indistinguishable from a learner that never found anything.
        authorisation = None
        if accepted:
            try:
                from .track_meter import learned_weight_authorisation
                authorisation = learned_weight_authorisation(bucket)
            except Exception:
                authorisation = None          # cannot read the register -> refuse
        if accepted and authorisation is None:
            refusal = ("REFUSED by the Amendment 1 gate: this would change the live composite, "
                       "which is a vintage event, and no OPEN vintage in track_meter.VINTAGES "
                       "authorises learned weights for this bucket. The out-of-sample test "
                       "PASSED; that is necessary and not sufficient. Ship it the S14 way -- "
                       "register it, gate it, get sign-off, open a vintage whose reason is the "
                       "adoption and mark it authorising -- then this run will adopt.")
            store.save_learned(bucket, base, {**stats, "refused_by": "amendment_1_vintage_gate",
                                              "would_have_adopted": rec}, False, refusal)
            report["buckets"][bucket] = {"adopted": False, "refused": True, "weights": base,
                                         "previous": base, "would_have_adopted": rec,
                                         "out_sample_ic": opt.get("out_sample_ic"),
                                         "note": refusal}
        elif accepted:
            store.save_learned(bucket, rec, stats, True,
                               f"{note} [authorised by vintage {authorisation.get('vintage')}]")
            report["buckets"][bucket] = {"adopted": True, "weights": rec, "previous": base,
                                         "out_sample_ic": opt.get("out_sample_ic"), "note": note,
                                         "authorised_by_vintage": authorisation.get("vintage")}
        else:
            store.save_learned(bucket, base, stats, False, note)
            report["buckets"][bucket] = {"adopted": False, "weights": base, "previous": base, "note": note}
    report["status"] = "ok"
    return report
