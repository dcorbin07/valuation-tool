# PROMPT — app fixer — 2026-10-13 — item 51: the fleet re-certifies itself

Read `DECISIONS.md` first — Don ruled (2026-10-13) on the change you routed in item 50.

1. **Automatic re-certification.** When the daily fleet cycle finds the certificate stale or absent
   because the harness fingerprint changed (SELFCHECK_STALE / SELFCHECK_ABSENT), it runs the
   self-check itself (you measured the budget: ~37s against the 280s ceiling). Rules:
   - a self-check that FAILS keeps every book shut and alerts Don — never retried into a pass;
   - SELFCHECK_FAILING and any state the self-check cannot fix are untouched by this change;
   - each automatic re-certification is RECORDED (when, why, fingerprint before and after), so the
     certificate still means "the harness was verified after it changed";
   - the manual FLEET SELF-CHECK workflow stays as the fallback.
   Prove it by test, including that a failing self-check leaves `may_fill` refusing.
2. **2026-10-14 (due tomorrow):** the intraday delivery re-measurement, beside item 37's 72.2%.
3. The options lane is about to add entry rules (F-21, F-22) and retire or re-declare other books.
   Confirm after its changes deploy that the cycle re-certified itself and the books are breathing.

Done means on origin/main, verified on the service, with a plain-words summary for Don.
