# PROMPT — app fixer — 2026-10-23 late evening — item 80b (URGENT, same rebalance): the door cannot find the 10-22 row the site is serving

Item 80 is live (`/api/health` reads `6625005`), and the conformance refusal is gone. Don re-sent
the same command and got the NEXT refusal:

```
HTTP 422  2026-10-22 has no recorded row, so a rebalance anchored there has no level to compound onto
```

But the 10-22 row IS recorded. `https://valquo.co/api/index-track` serves it right now, as the last
`series` point: `{"date":"2026-10-22","valquo":1.4735,"spy":3.2584,...}`.

## The likely cause (verify it, don't trust it)

1. `append_rebalance` defaults ONLY `meta_path`:
   ```
   meta_path, _h = index_track.default_paths()
   ```
   It discards `_h`, so `history_path` stays `None`. `_recorded_level(d, None)` then calls
   `_read_history(None)`, whose `open(None)` fails into the generic `except`, and the door reads no
   rows at all.
2. Even with the path fixed, `index_track._unpriced_block`'s own note says *"the live service holds
   the record in its STORE rather than in the CSV `index_mark` would otherwise read."* So on Render
   the anchor must be read from **the same recorded series `/api/index-track` serves**, not from a
   CSV that may be stale or absent.
3. Check the `meta`/book side the same way. The appended event must land where the service reads the
   book in force, or the next daily row will not see it.

## The fix

- The door reads the recorded series from the same source `/api/index-track` uses.
- `history_path` is defaulted properly.
- Add a test that runs through the real app route against a store-backed record and fails on
  today's code.
- Keep every refusal intact. In particular, "a recorded row already exists after the event date"
  must still refuse.
- Grep for any other caller of `_read_history` or `_recorded_level` with the same `None` default.

## Timing

The 2026-10-23 row is scheduled for 03:07 UTC and usually lands hours late. Once it exists, a 10-22
event is refused by design.

- Land as fast as safely possible, and confirm via `/api/health`'s commit.
- If the 10-23 row lands first, STOP and say so in one line. Dating the event 10-23 is Don's
  decision.

Don authorises landing tonight. Do not edit `DECISIONS.md`. No key, no `.github` change.

## Done

One line to Don: "deployed at <commit>, re-run the same --send".
