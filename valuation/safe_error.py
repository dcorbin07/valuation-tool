"""One place that turns an exception into text safe to hand an anonymous caller.

Why this module exists
----------------------
Both paid data providers put their credential in the QUERY STRING —
`screener/providers.py` sets `params["apikey"]` and `edge/data_providers.py` sets
`params["api_key"]`. `requests.raise_for_status()` raises an `HTTPError` whose text is
the full request URL, query string included. So `jsonify({"error": str(e)})` in any
route sitting above the fetcher stack can publish a live API key to whoever asked.

That exact bug shipped once via the public `/api/hotstocks` health block. It was fixed
with a `_redact()` local to `screener/providers.py` and called from four places in that
one file, while 23 other handlers kept returning raw exception text (SECURITY_AUDIT.md
H2). This module is that fix promoted to the whole codebase, so the class is closed
rather than the instance.

Two functions, deliberately:
  redact(msg)      -- scrub credentials only. Use where the text is already bounded
                      and you want it otherwise intact (health notes, log lines).
  safe_error(exc)  -- scrub credentials AND absolute filesystem paths, then truncate.
                      Use for anything returned to an HTTP caller.

Ordering matters: redaction happens BEFORE truncation. Truncating first can cut a URL
mid-key and strand a usable prefix of the credential in the output.
"""
from __future__ import annotations

import re

# Credential carried in a URL query string: ?apikey=... / &api_key=... / &token=...
_QS_KEY = re.compile(r"(?i)([?&](?:apikey|api_key|apiKey|token|access_token|key|auth)=)[^&\s]+")
# Authorization: Bearer <token>
_BEARER = re.compile(r"(?i)(bearer\s+)\S+")
# A credential assigned in text/JSON/kwargs: api_key='...', "token": "...", secret=...
# The `["']?` after the NAME matters: in JSON the key is quoted, so the closing quote sits
# between the name and the colon ({"api_key": "..."}) and a name-then-separator pattern
# misses it entirely.
_ASSIGN = re.compile(
    r"(?i)\b((?:api[_-]?key|access[_-]?token|secret[_-]?key|auth[_-]?token|password|token|secret)"
    r"[\"']?\s*[:=]\s*)[\"']?([A-Za-z0-9._\-]{8,})[\"']?")
# Known vendor key shapes, in case one reaches us outside any of the shapes above.
_KEY_SHAPES = re.compile(r"(?i)\b(sk-ant-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9]{20,}|"
                         r"sk_live_[A-Za-z0-9]{8,}|whsec_[A-Za-z0-9]{8,}|"
                         r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")

# Absolute filesystem paths. Anchored on a drive letter (Windows) or one of the usual
# POSIX roots, so ordinary URL paths are left alone -- the `(?<![\w:/])` guard keeps this
# off the "//" in "https://host/...". The basename is kept: which file is missing is
# useful, where it lives on the server is not.
_WIN_PATH = re.compile(r"[A-Za-z]:[\\/](?:[^\\/\s\"'<>|]+[\\/])+([^\\/\s\"'<>|]*)")
_NIX_PATH = re.compile(r"(?<![\w:/])/(?:home|Users|app|var|tmp|opt|srv|root|mnt|etc|usr)"
                       r"/(?:[^/\s\"'<>|]+/)*([^/\s\"'<>|]*)")

_REDACTED = "<redacted>"


def redact(msg) -> str:
    """Strip credentials out of a message. Safe to call on anything, including None."""
    s = str(msg)
    s = _QS_KEY.sub(r"\1" + _REDACTED, s)
    s = _BEARER.sub(r"\1" + _REDACTED, s)
    s = _ASSIGN.sub(r"\1" + _REDACTED, s)
    s = _KEY_SHAPES.sub(_REDACTED, s)
    return s


def strip_paths(msg) -> str:
    """Replace absolute server paths with `<path>/basename` (SECURITY_AUDIT.md L4)."""
    s = str(msg)
    s = _WIN_PATH.sub(lambda m: "<path>/" + m.group(1), s)
    s = _NIX_PATH.sub(lambda m: "<path>/" + m.group(1), s)
    return s


def log_exception(prefix: str = "") -> None:
    """Print the current traceback to stderr with credentials scrubbed.

    Drop-in for `traceback.print_exc()` on the routes that handle provider errors
    (SECURITY_AUDIT.md L3). The audit called these "server-side only, so not a direct
    disclosure" — true, but the traceback's exception line is the same ?apikey=... URL
    that M1 was about, and Render/Actions logs are not a safe home for a live credential
    either. Everything useful survives: full stack, files, line numbers. Only the key goes.
    """
    import sys
    import traceback
    sys.stderr.write(prefix + redact(traceback.format_exc()))
    sys.stderr.flush()


def safe_error(exc, limit: int = 200) -> str:
    """Exception -> a string that is safe to put in an HTTP response body.

    Scrubs credentials and absolute paths, collapses newlines (so a multi-line repr
    can't smuggle a traceback into a JSON field), then truncates. The full, unedited
    exception still goes to the server log via the caller's traceback.print_exc().
    """
    s = strip_paths(redact(exc))
    s = " ".join(s.split())
    if len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s or exc.__class__.__name__
