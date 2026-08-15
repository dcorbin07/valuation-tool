r"""One validator for every redirect target that comes from the request. [MA51]

WHY THIS MODULE EXISTS
----------------------
`auth.py` finished a successful login with

    return redirect(request.args.get("next") or "/app")

raw, with no same-origin check. `/login?next=https://evil.example` therefore sent the victim
to an attacker's page **immediately after a real login on the real, trusted site** — which is
the whole value of an open redirect. It is not a hole that leaks data by itself; it is a
phishing primitive that borrows this domain's credibility, and it is most convincing at
exactly the moment this one fires, when the user has just proved the site is genuine.

WHY A MODULE AND NOT AN `if`
----------------------------
Only one route reads `next` today (measured: `redirect(` appears 23 times under `valuation/`,
and `auth.py:99` is the only one whose argument comes from the request — the other four `next`
values are server-written literals like `"/login?next=/account"`). A single call site argues
for an inline check. The sweep test argues against it: a guard that lives inside one view
cannot be asserted over the *codebase*, so the second such route would be written the same
raw way and nothing would notice. This is audit B7's defect class, which this repository has
already paid for three times — three composite functions, one repair.

WHAT IT GUARANTEES
------------------
The return value is always a path on THIS origin, or the default. It is never attacker-chosen.
There is no input for which it raises.

THE REJECTIONS THAT ARE NOT OBVIOUS, each of which is a real bypass of the naive rule:

  * `//evil.example`  — a PROTOCOL-RELATIVE url. It begins with a single `/` by the letter of
    the audit's prescription and browsers resolve it as `https://evil.example`. The audit
    names this one; it is the reason the rule is not simply `startswith("/")`.
  * `/\evil.example`  — `\` is not a path separator in RFC 3986, so `urlsplit` reports an empty
    netloc and a path of `/\evil.example`, which LOOKS same-origin. Browsers disagree: they
    normalise `\` to `/` in the authority position, so this reaches the same place as `//`.
    A validator that trusts the parser here is correct about the standard and wrong about the
    thing that actually performs the navigation.
  * `https://evil.example`, `javascript:...`, `data:...` — anything with a scheme.
  * Anything carrying a control character, `\r` or `\n` included. Werkzeug already refuses to
    build a header out of those, so this is defence in depth rather than the only guard — but
    the failure it prevents (response splitting) is worse than the one it duplicates.

A rejected value degrades to `default`. It is never an error page: the caller has just logged
in successfully, and failing their login because their `next` was malformed would punish the
victim for the attacker's parameter.
"""
from __future__ import annotations

from urllib.parse import urlsplit

__all__ = ["safe_next_path"]


def safe_next_path(raw, default: str = "/app") -> str:
    """Return `raw` if it is a same-origin path, else `default`.

    `raw` is whatever `request.args.get("next")` handed back: a string, or None.

    Same-origin here means a ROOT-RELATIVE path — it must begin with `/` and carry neither a
    scheme nor an authority. A bare `app` (no leading slash) is rejected rather than accepted
    and prefixed: resolving it relative to the current path is how `next=evil.example` becomes
    plausible on some frameworks, and this project has no route that needs it.

    A query string and a fragment on the value itself are preserved (`/app?tab=holdings`).
    Stripping them would silently drop half of where the caller asked to go, and they cannot
    change the ORIGIN, which is the only thing being defended here.
    """
    if not isinstance(raw, str):
        return default
    value = raw.strip()
    if not value:
        return default
    # Control characters first: everything below this line reasons about structure, and a
    # newline makes "structure" mean whatever the next parser in the chain decides.
    if any(ch < " " or ch == "\x7f" for ch in value):
        return default
    # THE AUTHORITY POSITION, refused textually rather than by the parser. Both of these are
    # cases where `urlsplit` and a browser disagree, so the parser cannot be the authority:
    #   "/\evil.example"   -> urlsplit says path, empty netloc; browsers normalise \ to / and
    #                         navigate off-origin.
    #   "///evil.example"  -> urlsplit says EMPTY netloc and path "/evil.example", i.e. it
    #                         reads as same-origin, and this was caught only by a test failing
    #                         when an earlier draft delegated it.
    if value[:1] == "\\" or value[:2] in ("//", "/\\"):
        return default
    # Everything else is delegated to the parser, which is better at this than a prefix test.
    #
    # WHAT IS DELIBERATELY *NOT* CHECKED HERE: `parts.netloc`. An earlier draft tested it, and
    # mutation testing showed the branch was UNREACHABLE — a netloc requires either a scheme
    # (caught below) or a leading "//" (caught above), so nothing could ever reach it. It read
    # as defence in depth and was dead code: the mutant that deleted it passed every test.
    # Both branches below ARE reachable, and each is pinned by its own case. Note which is
    # which, because getting it wrong is what let a mutant survive here: "https://evil.example"
    # is caught by the PATH branch, not the scheme one, since it parses to an EMPTY path. The
    # scheme branch is load-bearing only for the SINGLE-slash form, which browsers resolve
    # off-origin just the same:
    #   scheme -> "https:/evil.example", "javascript:alert(1)", "data:text/html,..."
    #   path   -> "evil.example" (relative), "https://evil.example" (empty path)
    parts = urlsplit(value)
    if parts.scheme:
        return default
    if not parts.path.startswith("/"):
        return default
    return value
