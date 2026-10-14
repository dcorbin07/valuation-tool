"""RETRY A FAILED FREE FETCH, AND NEVER MISTAKE A THROTTLED ONE FOR DATA.  [item 54 part 2]

WHY THIS EXISTS
---------------
Item 53 part 7 measured that `T`, `VZ`, `MGM`, `RNR`, `NVDA` and `KO` all return 400 sessions of
price history and full momentum from yfinance **right now**, while the live scan carries nothing
for them. Nothing was broken in the arithmetic — of the top 500 served rows, **zero** had the
momentum inputs present with a null factor. The inputs simply never arrived: FMP returned 402 on
every call and disabled itself, Tradier closed so there is no broker prefill, and 1,440 names
were left depending on one per-name Yahoo fetch each. One attempt, no retry.

THE DANGEROUS HALF IS NOT THE FAILURE, IT IS THE SILENT DEGRADATION
-------------------------------------------------------------------
r1 reported that a throttled feed degrades quietly — *"betas go missing, WACCs collapse to the
cost of debt"* — and a retry that accepts whatever comes back second would write that damage into
the scan as though it were measurement. So this module's main job is the detector, not the loop.

**MEASURED ON THE REAL `compute_wacc`, so the detector keys on the mechanism rather than on the
symptom's name:**

| what is missing | WACC | equity weight |
|---|---|---|
| nothing | 0.0941 | 0.833 |
| beta | 0.0858 (−0.83pp) | 0.833 |
| price only | 0.0941 (unchanged) | 0.833 |
| market cap only | 0.0941 (unchanged) | 0.833 |
| **price AND market cap** | **0.0498 = the after-tax cost of debt, exactly** | **0.000** |

So r1's sentence is **literally** true and it needs **both** gone: either one alone still yields
an equity value (`price × shares`, or the cap directly), and only losing both drives the equity
weight to zero and the WACC to `kd`. That conjunction is exactly what a throttled `.info`
produces, because both fields come out of the same payload.

THE DISCRIMINATOR: A THIN NAME IS NOT A THROTTLED FEED
------------------------------------------------------
A genuinely data-poor foreign issuer legitimately has no beta, and refusing it would be a
different defect. So one absent field is DATA; a **hard tell**, or **two soft tells at once**, is
a THROTTLE. That is the whole rule, and it is stated here rather than buried in a threshold.

**A DEGRADED FETCH IS COUNTED AS A FAILURE AND ITS CONTENT IS DISCARDED** — `MA6`'s rule, err
toward the state that refuses. The alternative is a scan that looks complete and is wrong, which
is the shape this project loses the most time to.

PACING, AND WHY THE BUDGET IS SHARED
------------------------------------
A retry is only ever spent on a name that failed, which on the live scan is a small minority —
momentum was absent on 2.6% of the top 500. But the scan has ~1,440 names inside a 60-minute
workflow, so an unbounded retry could cost the run. The budget is a single object threaded
through the whole scan: it caps the number of retries, the pause between them and the total time
spent retrying, and when it is exhausted it says so instead of quietly stopping.

**IT PACES RATHER THAN HAMMERS, on purpose.** Retrying a throttled host immediately is how a
soft throttle becomes a hard block for the rest of the run, which would cost far more names than
it rescues.
"""
from __future__ import annotations

import threading
import time

#: Pause before a retry. Short enough that a few hundred of them fit inside the scan's hour,
#: long enough not to look like a hammer to the far end.
RETRY_SLEEP_S = 0.35

#: How many names may be retried in one scan. 300 against a live failure count in the low tens
#: -- deliberately far above what is needed, because the binding constraint is meant to be the
#: wall clock below, not this.
MAX_RETRIES = 300

#: Total wall clock a scan may spend retrying, including the pauses. The scan's workflow allows
#: 60 minutes for everything, so this is a bound on the share of it a rescue may take.
MAX_RETRY_SECONDS = 420.0

#: One retry per name. A second has never been measured to help and multiplies the cost; if a
#: name fails twice the honest answer is that it had no data on this run.
ATTEMPTS_PER_NAME = 2


class RetryBudget:
    """How much retrying this scan may still do. Thread-safe; one instance per scan.

    **IT REPORTS EXHAUSTION RATHER THAN JUST STOPPING.** A scan that silently stopped retrying
    halfway would look like a scan with fewer failures, which is the reporting defect this
    project keeps finding -- so `detail()` carries why it stopped.
    """

    def __init__(self, max_retries: int = MAX_RETRIES,
                 max_seconds: float = MAX_RETRY_SECONDS,
                 sleep_s: float = RETRY_SLEEP_S, clock=time.monotonic, sleep=time.sleep):
        self.max_retries = int(max_retries)
        self.max_seconds = float(max_seconds)
        self.sleep_s = float(sleep_s)
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._spent = 0
        self._elapsed = 0.0
        self._exhausted_reason = ""
        self.recovered = 0
        self.still_failed = 0
        self.degraded_discarded = 0

    def take(self) -> bool:
        """Claim one retry, pausing first. False when the budget is gone."""
        with self._lock:
            if self._spent >= self.max_retries:
                self._exhausted_reason = ("the per-scan retry count (%d) was reached"
                                          % self.max_retries)
                return False
            if self._elapsed >= self.max_seconds:
                self._exhausted_reason = ("the per-scan retry time budget (%.0fs) was spent"
                                          % self.max_seconds)
                return False
            self._spent += 1
        t0 = self._clock()
        self._sleep(self.sleep_s)
        with self._lock:
            self._elapsed += self._clock() - t0
        return True

    def note(self, *, recovered=False, degraded=False, failed=False) -> None:
        with self._lock:
            if recovered:
                self.recovered += 1
            if degraded:
                self.degraded_discarded += 1
            if failed:
                self.still_failed += 1

    def detail(self) -> dict:
        with self._lock:
            return {"retries_spent": self._spent, "retries_allowed": self.max_retries,
                    "seconds_spent": round(self._elapsed, 2),
                    "seconds_allowed": self.max_seconds,
                    "exhausted": bool(self._exhausted_reason),
                    "exhausted_reason": self._exhausted_reason,
                    "recovered": self.recovered,
                    "degraded_discarded": self.degraded_discarded,
                    "still_failed": self.still_failed}


def _missing(cd, name) -> bool:
    v = getattr(cd, name, None)
    return v is None or (isinstance(v, (int, float)) and not v)


def degradation(cd, quote=None) -> dict:
    """Did this fetch come back THROTTLED rather than merely thin?

    Returns `{"degraded": bool, "hard": [...], "soft": [...], "why": str}`. Never raises --
    a detector that can raise would turn a bad fetch into a dropped name.

    **HARD TELLS** are states a throttled payload produces and a real company does not:
      * no price AND no market cap -- measured above to drive the equity weight to zero and
        the WACC to the after-tax cost of debt exactly;
      * no company name at all, when `.info` answered with essentially nothing;
      * none of the three momentum inputs. `SUN`, the one genuinely short-history name item
        53 found, has 61 sessions and still returns `high_prox`, so a thin-but-real name
        yields at least one and none at all is a throttle.

    **SOFT TELLS** are each individually legitimate for some real name, so one is data and two
    together are a throttle:
      * no beta (worth 0.83pp of WACC on its own);
      * no revenue.
    """
    hard, soft = [], []
    try:
        if _missing(cd, "price") and _missing(cd, "market_cap"):
            hard.append("no price and no market cap: the equity weight goes to zero and the "
                        "WACC collapses to the after-tax cost of debt")
        if not str(getattr(cd, "name", "") or "").strip() and _missing(cd, "price"):
            hard.append("the profile came back with neither a name nor a price")
        q = quote or {}
        if not any(q.get(k) is not None for k in ("ret_12_1", "ret_6_1", "high_prox")):
            # A HARD TELL, PROMOTED FROM SOFT ON MEASURED EVIDENCE -- and the first cut had
            # it soft, which would have left the very failure this module exists for
            # unretried: a healthy profile with no quote scored "not degraded".
            #
            # `get_quote` returns None only when the history is absent or under 30 sessions,
            # so ZERO of the three inputs means essentially no price history came back. For a
            # US-listed name the screen has already admitted, that is a fetch failure rather
            # than a fact: `SUN`, the one genuinely short-history name item 53 found, has 61
            # sessions and STILL returns `high_prox`. A thin-but-real name yields at least
            # one input; none at all is the throttle.
            hard.append("no momentum inputs at all, so essentially no price history came "
                        "back -- under 30 sessions for a name the screen already admitted")
        if _missing(cd, "beta"):
            soft.append("no beta")
        if _missing(cd, "revenue"):
            soft.append("no revenue")
    except Exception:                                                       # noqa: BLE001
        return {"degraded": False, "hard": [], "soft": [],
                "why": "the degradation check could not run"}
    degraded = bool(hard) or len(soft) >= 2
    why = ""
    if degraded:
        why = ("; ".join(hard) if hard else
               "two independent signs of a throttled feed at once: " + "; ".join(soft))
    return {"degraded": degraded, "hard": hard, "soft": soft, "why": why}


def fetch_free(ticker: str, cfg, *, get_company, get_quote, budget: RetryBudget = None) -> dict:
    """One name's free fetch, retried once if it fails or comes back degraded.

    `get_company` and `get_quote` are injected so this module neither imports the fetcher nor
    the price layer -- and so a test can drive every branch without a network.

    Returns a report. `cd` and `quote` are `None` unless the fetch was **usable**: a degraded
    payload is discarded rather than handed back, because the caller cannot tell the difference
    and would merge it.
    """
    out = {"ticker": str(ticker or "").upper(), "cd": None, "quote": None,
           "attempts": 0, "ok": False, "retried": False, "recovered": False,
           "degraded": False, "why": "", "tells": []}
    for attempt in range(1, ATTEMPTS_PER_NAME + 1):
        if attempt > 1:
            if budget is None or not budget.take():
                out["why"] = out["why"] or "no retry budget left"
                break
            out["retried"] = True
        out["attempts"] = attempt
        cd = quote = None
        try:
            cd = get_company(ticker, cfg)
            if getattr(cd, "fx_unresolved", False):
                # A currency mismatch is a DATA fact about this filing, not a throttle, so it
                # is not retried -- the second attempt would return the same thing.
                out["why"] = "the statement and price currencies could not be reconciled"
                break
            quote = get_quote(ticker)
        except Exception as e:                                              # noqa: BLE001
            out["why"] = "the fetch raised %s" % type(e).__name__
            continue
        d = degradation(cd, quote)
        if not d["degraded"]:
            out["cd"], out["quote"] = cd, quote
            out["ok"] = True
            out["recovered"] = attempt > 1
            out["why"] = ""
            out["tells"] = []
            break
        # DEGRADED: discarded, counted as a failure, and retried if there is budget.
        out["degraded"] = True
        out["why"] = d["why"]
        out["tells"] = list(d["hard"]) + list(d["soft"])
    if budget is not None:
        if out["ok"]:
            if out["recovered"]:
                budget.note(recovered=True)
        elif out["degraded"]:
            budget.note(degraded=True, failed=True)
        else:
            budget.note(failed=True)
    return out
