# PROMPT — app fixer — 2026-10-16 — item 65 addendum: the seam pull still 403s in the evening

Add this to item 65 as **part 5**. It is independent of parts 1–4.

Don ran `POST /admin/alpaca-seam?run=1` at about **22:00Z on 2026-10-16**, after item 64 was
deployed. The new code ran: its own "RE-RUNNING WILL NOT HELP" note came back. The result:

- `complete=False alpaca=0`;
- *"Alpaca refused the WHOLE request because the window reaches inside the free plan's 16-minute
  SIP delay. The window asked for was 2025-09-11 to 2026-10-16. This end is normally bounded
  automatically, so an explicit end= was probably supplied."*

No `end=` was supplied, because the door does not accept one.

**The manager's diagnosis. It is a hypothesis: verify it against Alpaca, not against the rule's own
definition.**

- `sip_safe_end` returns a **date**, and at 22:00Z it correctly returns today, because today's
  session closed more than 16 minutes earlier.
- Alpaca's docs say `end` is *"the inclusive end of the interval. Format: RFC-3339 or YYYY-MM-DD"*.
  A bare date is most likely read as the **whole calendar day**, which reaches past "now". So it
  is refused.
- That fits both observations: the ten runs that ended on today's date, and this one.
- It also predicts that the door works **before about 21:16Z on a weekday, and all weekend**,
  because then the end rolls back to an earlier, finished day.

The fix:

- Send `end` as an **RFC-3339 timestamp**: the earlier of that session's close instant and
  `now − 16 minutes`. Alternatively, never send today's date.
- Test it against a recorded Alpaca response for the evening case, not only against the rule.
- Correct the note: "an explicit end= was probably supplied" cannot be true at this door.
- Item 64 verified the rule "at every quarter-hour of a week against the rule's own definition".
  That is exactly why this was missed, so record it as such.
