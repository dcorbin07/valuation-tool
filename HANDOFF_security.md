# HANDOFF_security.md

Read-only secret sweep done (2026-08-02), findings in `SECURITY_AUDIT.md`, no code touched: **no secret
has ever been committed to git (261 commits swept) — nothing to rotate**, but `/forgot` hands the
password-reset link back in the response whenever SMTP is unconfigured or failing
(`valuation/saas/auth.py:102`), which is account takeover including the owner account, and the FMP
`_redact()` fix never got applied beyond `screener/providers.py` — 23 other handlers still return raw
exception text to unauthenticated callers while both paid providers put their key in the query string.
