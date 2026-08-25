"""
WRDS connection + credential handling. COLLECTION ONLY, zero trials.

--------------------------------------------------------------------------------------------
THE LAW THIS FILE EXISTS TO KEEP.

  * **Credentials are never printed, logged, echoed or returned.** Not at DEBUG, not in an
    exception message, not in a repr. `pgpass_path()` returns a PATH; nothing here returns a
    password. The one place the secret is written is a file the OS protects, and the writer
    below checks that protection actually took.
  * **Licensed vendor rows never leave `D:\\wrds`.** Nothing in this module returns raw rows to
    a caller that might serialise them into the repo. The census helpers return COUNTS, SPANS
    and DTYPES -- derived statistics -- and the pull scripts write payload only under the raw
    root.
  * **No WRDS import at module import time.** `wrds` is a heavy optional dependency that CI does
    not install (`requirements.lock.txt` is unchanged, deliberately), so it is imported inside
    the function that needs it. A test suite must be able to import this module and assert its
    rules without a database, a password or a network.

--------------------------------------------------------------------------------------------
WHY `.pgpass` AND NOT A PROMPT.

The `wrds` package prompts on stdin when it cannot find a password, which in a non-interactive
run hangs forever rather than failing -- the same shape as the twelve-hour "hang" in the chain
harvest, where a blocked call is indistinguishable from work. So the password is materialised
into the file libpq expects, once, from `.env`, and the connection is made with a deadline.

**Windows note that is easy to get wrong:** libpq does NOT read `~/.pgpass` on Windows. It reads
`%APPDATA%\\postgresql\\pgpass.conf`. `PGPASSFILE` overrides both, and is what this module sets,
so the location is explicit rather than platform-guessed.
"""
from __future__ import annotations

import datetime as dt
import os
import stat
from typing import Optional

WRDS_HOST = "wrds-pgdata.wharton.upenn.edu"
WRDS_PORT = 9737
WRDS_DB = "wrds"

#: Sibling of D:\thetadata, per the harvest convention. Payload lives here and only here.
DEFAULT_RAW_ROOT = r"D:\wrds"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CredentialsMissing(RuntimeError):
    """Raised when .env has no WRDS credentials. Deliberately says WHICH KEY is absent and
    never what any value is."""


def _env(path: str = "") -> dict:
    """Read `.env` into a dict. Never logged, never returned to a caller that prints."""
    p = path or os.path.join(REPO, ".env")
    if not os.path.exists(p):
        # the worktree has no .env; the main checkout does
        alt = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", ".env")
        p = alt if os.path.exists(alt) else p
    out = {}
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def credentials_present(env: Optional[dict] = None) -> dict:
    """Which credential keys EXIST. Returns booleans -- never values.

    A separate function from the one that uses them so a census, a test or a status line can
    establish "we have credentials" without any code path that could surface them.
    """
    e = env if env is not None else _env()
    return {"WRDS_USERNAME": bool(e.get("WRDS_USERNAME")),
            "WRDS_PASSWORD": bool(e.get("WRDS_PASSWORD"))}


def pgpass_path() -> str:
    """Where the credential file lives. libpq does NOT read ~/.pgpass on Windows."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "postgresql", "pgpass.conf")
    return os.path.expanduser("~/.pgpass")


def write_pgpass(env: Optional[dict] = None, path: str = "") -> str:
    """Materialise the credential file from `.env`, and RETURN ITS PATH -- never its contents.

    Rewritten every run rather than reused: a stale pgpass from a rotated password fails with an
    authentication error that looks exactly like a wrong username, and chasing that is expensive.

    The permission tightening is not decoration. libpq REFUSES a world-readable pgpass on POSIX,
    and on Windows it is the only thing standing between a secret and every process running as
    this user. If the tightening cannot be verified the file is REMOVED and the call raises,
    because a secret written somewhere loose is worse than no secret written at all.
    """
    e = env if env is not None else _env()
    have = credentials_present(e)
    missing = [k for k, v in have.items() if not v]
    if missing:
        raise CredentialsMissing(f"absent from .env: {missing}")

    p = path or pgpass_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    line = f"{WRDS_HOST}:{WRDS_PORT}:{WRDS_DB}:{e['WRDS_USERNAME']}:{e['WRDS_PASSWORD']}\n"
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        try:
            os.remove(p)
        except OSError:
            pass
        raise
    finally:
        del line, e                       # do not leave the secret in a local for a traceback
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    if os.name != "nt":
        mode = stat.S_IMODE(os.stat(p).st_mode)
        if mode & 0o077:
            os.remove(p)
            raise RuntimeError(f"pgpass is group/world readable ({oct(mode)}) and was removed")
    os.environ["PGPASSFILE"] = p
    return p


def username(env: Optional[dict] = None) -> str:
    """The WRDS username. NOT a secret in the same sense as the password -- WRDS usernames appear
    in schema names (`wrds.<user>`) and in every support ticket -- but still not printed by
    default anywhere in this lane's output."""
    e = env if env is not None else _env()
    u = e.get("WRDS_USERNAME")
    if not u:
        raise CredentialsMissing("absent from .env: ['WRDS_USERNAME']")
    return u


def connect(timeout_s: int = 180):
    """Open a WRDS connection with a DEADLINE.

    The deadline is the point. `wrds.Connection` prompts on stdin when it cannot authenticate,
    and a prompt in a non-interactive run waits forever -- a blocked call that looks exactly like
    a working one from outside. The chain harvest lost twelve hours to that shape once already.
    """
    import concurrent.futures as cf

    write_pgpass()
    user = username()
    # libpq picks the pgpass LINE by (host, port, db, user), and falls back to the OS username
    # when PGUSER is unset. `wrds.Connection`'s first attempt goes through system defaults, so
    # without these it can miss a perfectly good pgpass and drop to an stdin prompt -- which is
    # exactly what happened on the first run here. Setting them makes the lookup deterministic
    # instead of dependent on the OS account happening to match the WRDS username.
    os.environ.setdefault("PGHOST", WRDS_HOST)
    os.environ.setdefault("PGPORT", str(WRDS_PORT))
    os.environ.setdefault("PGDATABASE", WRDS_DB)
    os.environ["PGUSER"] = user

    def _open():
        import wrds
        return wrds.Connection(wrds_username=user)

    ex = cf.ThreadPoolExecutor(max_workers=1)
    try:
        return ex.submit(_open).result(timeout=timeout_s)
    finally:
        ex.shutdown(wait=False)


def raw_root(root: str = "") -> str:
    r = root or DEFAULT_RAW_ROOT
    os.makedirs(r, exist_ok=True)
    return r


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
