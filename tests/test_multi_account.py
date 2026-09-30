"""MULTI-ACCOUNT ALERT ROUTING — the hard guard, the order guard, and the scoring boundary.

Three of these tests are the ones that matter, and they are the three that would let something
bad ship if they were absent:

  * **ZERO ACCOUNTS IS TODAY, BYTE FOR BYTE.** Not "behaves similarly" — the payload handed to
    `send_discord` and the key handed to `mark_alerted` are asserted EQUAL to what the composer
    and the literal produce. A routing layer that quietly re-worded every card on a deployment
    where nobody asked for routing would be a change to a live surface disguised as a no-op.

  * **THE ROUTING PATH HOLDS NO TOKEN.** The standing rule is data/sandbox only, no order
    endpoint added or called. This is NOT tested by banning the word `orders` — that fires
    against `valuation/edge/paper_broker.py`, which places sandbox orders legitimately under
    its own register, and the substring-ban family has cost this project six sessions already.
    It is tested structurally: the module returns no token, imports no HTTP client, and nothing
    that imports it can reach an order call. You cannot place an order with a credential you
    do not have.

  * **PORTFOLIO VISIBILITY MAY NEVER REACH SCORING.** Nothing is built yet, which is exactly
    when the boundary is cheap to pin. A screen that can see what you already hold is a screen
    that can be nudged by it, and that failure would surface as a slightly better backtest
    rather than as an error.

And one that is easy to miss: an account LABEL is operator-supplied text flowing into a card
whose copy this project refuses to let drift. `test_a_label_cannot_smuggle_a_banned_framing`
is the check that a label like "Recovery Fund" is refused rather than published.

Run: python tests/test_multi_account.py
"""
from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.saas import accounts as ACCT                              # noqa: E402
from valuation.saas import notify as N                                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "saas", "accounts.py")

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def env(**kw):
    """A bare env dict — never `os.environ`, so a test cannot leak into the process."""
    return dict(kw)


def acct_env(slot, label="Main", token="tok", ident="ACC1"):
    return {ACCT.var_name(slot, "LABEL"): label,
            ACCT.var_name(slot, "TOKEN"): token,
            ACCT.var_name(slot, "ID"): ident}


class FakeStore:
    def __init__(self):
        self.marked = []
        self.already = set()

    def alerted_today(self, key):
        return key in self.already

    def mark_alerted(self, key, when):
        self.marked.append((key, when))


class FakeCfg:
    discord_webhook_url = "https://example.invalid/hook"


# =======================================================================================
# THE HARD GUARD — zero accounts is today, byte for byte
# =======================================================================================
def test_no_account_configured_yields_exactly_one_unlabelled_pass():
    assert ACCT.accounts(env()) == [], ACCT.accounts(env())
    assert ACCT.fanout(env()) == [None], ACCT.fanout(env())
    assert ACCT.configured(env()) is False


def test_tag_and_dedup_key_are_identity_with_no_account():
    body = "\U0001f525 **Valquo** — some card\n```\nx\n```"
    assert ACCT.tag(body, None) == body
    assert ACCT.tag(body) == body
    assert ACCT.dedup_key("__HOTDIGEST__", None) == "__HOTDIGEST__"
    assert ACCT.dedup_key("__HOTDIGEST__") == "__HOTDIGEST__"


def test_the_hot_digest_payload_is_byte_identical_with_no_routing_configured():
    """The strong form: what SENDS equals what the composer produced, and the dedup key is
    the literal it always was. Anything weaker would let a re-worded card ship as a no-op."""
    rows = [{"rank": 1, "ticker": "AAPL", "hot_score": 91, "sector": "Tech", "price": 210.5}]
    expected = N.hot_digest_text("2026-08-27", rows, None)

    sent = []
    real_send, real_fanout = N.send_discord, ACCT.fanout
    N.send_discord = lambda cfg, text: (sent.append(text), True)[1]
    ACCT.fanout = lambda e=None: [None]                    # as if the env carried nothing
    try:
        store = FakeStore()
        out = N.post_hot_digest(FakeCfg(), store, "2026-08-27", rows, None)
    finally:
        N.send_discord, ACCT.fanout = real_send, real_fanout

    assert out is True, out
    assert len(sent) == 1, sent
    assert sent[0] == expected, "the card was altered on a deployment with no routing set up"
    assert store.marked == [("__HOTDIGEST__", "2026-08-27")], store.marked


# =======================================================================================
# EXISTENCE — both fields, and nothing inferred from a gap
# =======================================================================================
def test_an_account_exists_only_when_label_and_token_are_both_non_empty():
    cases = [
        ("both set", acct_env(1), 1),
        ("token missing", {ACCT.var_name(1, "LABEL"): "Main"}, 0),
        ("label missing", {ACCT.var_name(1, "TOKEN"): "tok"}, 0),
        ("label blank", acct_env(1, label="   "), 0),
        ("token blank", acct_env(1, token="  "), 0),
        ("id may be absent", {ACCT.var_name(1, "LABEL"): "Main",
                              ACCT.var_name(1, "TOKEN"): "tok"}, 1),
    ]
    for name, e, n in cases:
        got = len(ACCT.accounts(e))
        assert got == n, "%s: expected %d account(s), got %d" % (name, n, got)


def test_a_gap_in_the_numbering_does_not_renumber_the_rest():
    """Deleting slot 2 must not silently promote slot 3 into its dedup key or its ordering."""
    e = {}
    e.update(acct_env(1, label="Main", ident="A1"))
    e.update(acct_env(3, label="Roth", ident="A3"))
    got = ACCT.accounts(e)
    assert [a["slot"] for a in got] == [1, 3], got
    assert [a["label"] for a in got] == ["Main", "Roth"], got
    assert ACCT.dedup_key("__HOTDIGEST__", got[1]) == "__HOTDIGEST__:3"


def test_slots_beyond_the_declared_ceiling_are_ignored_rather_than_promoted():
    e = dict(acct_env(11, label="Eleven"))
    assert ACCT.accounts(e) == [], "slot 11 was read; raising the ceiling must be a visible edit"


def test_the_dedup_key_follows_the_slot_and_not_the_label():
    """Renaming an account in the env must not reset its once-a-day dedup and re-post."""
    a = ACCT.accounts(acct_env(2, label="Main"))[0]
    b = ACCT.accounts(acct_env(2, label="Renamed"))[0]
    assert ACCT.dedup_key("__HOTDIGEST__", a) == ACCT.dedup_key("__HOTDIGEST__", b)


# =======================================================================================
# ROUTING — one labelled card per account, on one shared webhook
# =======================================================================================
def test_each_account_gets_one_labelled_card_and_the_bodies_are_unchanged():
    rows = [{"rank": 1, "ticker": "AAPL", "hot_score": 91, "sector": "Tech", "price": 210.5}]
    body = N.hot_digest_text("2026-08-27", rows, None)
    e = {}
    e.update(acct_env(1, label="Main"))
    e.update(acct_env(2, label="Roth"))

    sent = []
    real_send, real_fanout = N.send_discord, ACCT.fanout
    N.send_discord = lambda cfg, text: (sent.append(text), True)[1]
    ACCT.fanout = lambda _e=None: ACCT.accounts(e)
    try:
        store = FakeStore()
        out = N.post_hot_digest(FakeCfg(), store, "2026-08-27", rows, None)
    finally:
        N.send_discord, ACCT.fanout = real_send, real_fanout

    assert out is True
    assert len(sent) == 2, sent
    assert "Main" in sent[0] and "Roth" in sent[1], sent
    # The CARD is untouched -- routing decides who is told, never what was found.
    for text in sent:
        assert text.endswith(body), "the card body was rewritten by routing"
    assert [k for k, _ in store.marked] == ["__HOTDIGEST__:1", "__HOTDIGEST__:2"], store.marked


def test_an_account_already_posted_today_is_skipped_and_the_others_still_send():
    rows = [{"rank": 1, "ticker": "AAPL", "hot_score": 91, "sector": "Tech", "price": 1.0}]
    e = {}
    e.update(acct_env(1, label="Main"))
    e.update(acct_env(2, label="Roth"))

    sent = []
    real_send, real_fanout = N.send_discord, ACCT.fanout
    N.send_discord = lambda cfg, text: (sent.append(text), True)[1]
    ACCT.fanout = lambda _e=None: ACCT.accounts(e)
    try:
        store = FakeStore()
        store.already.add("__HOTDIGEST__:1")
        N.post_hot_digest(FakeCfg(), store, "2026-08-27", rows, None)
    finally:
        N.send_discord, ACCT.fanout = real_send, real_fanout

    assert len(sent) == 1 and "Roth" in sent[0], sent


def test_a_label_cannot_smuggle_a_banned_framing_into_the_dip_card():
    """An account label is OPERATOR TEXT entering a card whose copy is registered.

    The dip digest is gated on `dip_posture.violations`, and the label is tagged on BEFORE that
    gate runs. A label carrying a recovery framing must therefore be refused rather than
    published -- and refused for that account only.
    """
    from valuation.web import dip_posture as DP
    banned = next((x for x in getattr(DP, "BANNED", ()) if isinstance(x, str) and x.strip()),
                  None)
    assert banned, "the copy gate has no vocabulary, so this test would pass vacuously"

    rows = [{"ticker": "AAPL", "drawdown": -0.24, "hot_score": 88, "price": 210.5}]
    e = {}
    e.update(acct_env(1, label="Fund %s" % banned))       # the smuggler
    e.update(acct_env(2, label="Roth"))                   # the innocent bystander

    sent = []
    real_send, real_fanout, real_posture = N.send_discord, ACCT.fanout, DP.posture
    N.send_discord = lambda cfg, text: (sent.append(text), True)[1]
    ACCT.fanout = lambda _e=None: ACCT.accounts(e)
    # The dip register is NULL, so `digest_eligible` is False and the real path returns before
    # reaching the gate -- which would make this test pass while measuring nothing. Force the
    # eligible branch so the gate is actually exercised.
    DP.posture = lambda: dict(real_posture(), digest_eligible=True)
    try:
        N.post_dip_digest(FakeCfg(), FakeStore(), "2026-08-27", rows)
    finally:
        N.send_discord, ACCT.fanout, DP.posture = real_send, real_fanout, real_posture

    joined = "\n".join(sent)
    assert banned not in joined, (
        "a banned framing inside an account label was PUBLISHED: %r" % banned)
    assert len(sent) == 1 and "Roth" in sent[0], (
        "the refusal must be per account -- the clean account still gets its card: %r" % sent)


# =======================================================================================
# THE ORDER GUARD — structural, not a substring ban
# =======================================================================================
def test_no_function_here_returns_a_token():
    """The routing path holds no credential, so it cannot reach an order endpoint.

    Asserted on the SYNTAX TREE and on behaviour, not by grepping for `orders` -- that word
    appears legitimately in `paper_broker`, which places sandbox orders under its own register.
    """
    e = dict(acct_env(1, label="Main", token="SECRET-TOKEN-VALUE", ident="A1"))
    got = ACCT.accounts(e)
    flat = repr(got) + repr(ACCT.describe(e)) + ACCT.tag("card", got[0])
    assert "SECRET-TOKEN-VALUE" not in flat, "a token escaped the routing layer: %s" % flat
    for a in got:
        assert set(a) == {"slot", "label", "account_id"}, a


def test_the_routing_module_cannot_make_a_network_call_at_all():
    tree = ast.parse(open(MODULE, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("requests", "urllib", "http", "httpx", "socket"):
        assert banned not in imported, (
            "%s imports %s -- the routing path must hold no way to call an endpoint" % (
                MODULE, banned))


def test_the_routing_module_does_not_reach_the_order_placing_broker():
    src = open(MODULE, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        mod = None
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
        elif isinstance(node, ast.Import):
            mod = ",".join(n.name for n in node.names)
        if mod and "paper_broker" in mod:
            raise AssertionError("the routing layer imports the order-placing broker")


# =======================================================================================
# THE SCORING BOUNDARY — pinned before anything crosses it
# =======================================================================================
def test_no_scoring_module_imports_the_accounts_layer():
    """Portfolio visibility may never become an input to scoring.

    Nothing reads a portfolio yet, which is exactly when this is cheap to pin: the day somebody
    wires balances into a score, this fails, rather than the change surfacing as a marginally
    better backtest that nobody can attribute.
    """
    scoring_dirs = [os.path.join(ROOT, "valuation", "screener"),
                    os.path.join(ROOT, "valuation", "edge"),
                    os.path.join(ROOT, "valuation", "engine")]
    offenders = []
    for d in scoring_dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(d, name)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and "accounts" in (node.module or ""):
                    offenders.append(path)
                elif isinstance(node, ast.Import):
                    for n in node.names:
                        if n.name.endswith("saas.accounts"):
                            offenders.append(path)
    assert not offenders, ("a scoring module imports the accounts layer: %s" % offenders)


def test_the_guard_above_can_actually_fire():
    """A boundary check that could never fail is not a boundary. Positive control."""
    src = "from ..saas.accounts import accounts\n"
    tree = ast.parse(src)
    hits = [n for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and "accounts" in (n.module or "")]
    assert hits, "the import shape the boundary test looks for is not detected"


def run():
    global PASSED, FAILED
    print("MULTI-ACCOUNT ALERT ROUTING")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
