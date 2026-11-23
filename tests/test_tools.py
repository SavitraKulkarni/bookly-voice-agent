"""Guardrails are enforced in code, so they can be tested without the model."""
import pytest

from bookly import db
from bookly.state import CallState
from bookly.tools import ToolContext, faq_search, run_tool
from data.seed import UNKNOWN_PHONE, seed

MAYA = "+14155550101"


@pytest.fixture
def make_ctx(tmp_path):
    path = tmp_path / "t.db"
    seed(path)

    def _make(caller_id=None):
        return ToolContext(conn=db.connect(path), state=CallState(call_id="t", caller_id=caller_id))
    return _make


def call(ctx, name, **args):
    return run_tool(ctx, name, args)


def test_caller_id_lookup_hides_statuses(make_ctx):
    ctx = make_ctx(MAYA)
    r, err = call(ctx, "lookup_customer", method="caller_id")
    assert not err and r["found"] and len(r["orders"]) == 3
    assert all("status" not in o for o in r["orders"])


def test_unknown_caller_identified_by_order_is_scoped(make_ctx):
    ctx = make_ctx(UNKNOWN_PHONE)
    r, _ = call(ctx, "lookup_customer", method="caller_id")
    assert r["found"] is False
    r, err = call(ctx, "lookup_order", order_number="420044")
    assert not err and ctx.state.identified_via == "order_number"
    # Another valid order number before verification = a correction: access moves to that ONE order,
    # never to the account, and the account holder's name isn't returned.
    r, err = call(ctx, "lookup_order", order_number="418027")
    assert not err and "customer_name" not in r
    assert ctx.state.identified_via == "order_number" and ctx.state.scoped_order == "418027"
    # after verifying, the call is pinned: other customers' orders look "not found"
    call(ctx, "verify_zip", zip="94110")
    _, err = call(ctx, "lookup_order", order_number="420044")
    assert err


def test_write_needs_zip_then_two_phase(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    args = dict(order_number="418027", item_id=1, reason="duplicate gift", resolution="refund")
    r, err = call(ctx, "start_return", **args)
    assert err and r["error"] == "zip_required"
    r, _ = call(ctx, "verify_zip", zip="94110")
    assert r["verified"]
    r, err = call(ctx, "start_return", **args)
    assert not err and r["status"] == "needs_confirmation"
    # confirming in the same caller turn is refused: the caller must answer first
    r, err = call(ctx, "start_return", **args, confirmed=True)
    assert err and r["error"] == "awaiting_caller"
    ctx.state.caller_turns += 1
    # confirming different details than were read back is refused
    r, err = call(ctx, "start_return", **{**args, "resolution": "store_credit"}, confirmed=True)
    assert err and r["error"] == "not_read_back"
    r, err = call(ctx, "start_return", **args, confirmed=True)
    assert not err and r["status"] == "return_started"
    # idempotent
    r, err = call(ctx, "start_return", **args, confirmed=True)
    assert not err and r["status"] == "already_exists"
    assert ctx.conn.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 1


def test_outside_window_is_policy_error(make_ctx):
    ctx = make_ctx("+12065550177")
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="98103")
    r, err = call(ctx, "start_return", order_number="416881", item_id=6, reason="didn't like it",
                  resolution="refund")
    assert err and r["error"] == "outside_policy"


def test_zip_locks_after_two_failures(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="11111")
    r, _ = call(ctx, "verify_zip", zip="22222")
    assert r["attempts_left"] == 0
    r, err = call(ctx, "verify_zip", zip="94110")
    assert err and r["error"] == "verification_locked"


def test_store_credit_idempotent(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="94110")
    args = dict(order_number="418027", item_id=2, reason="changed mind", resolution="store_credit")
    call(ctx, "start_return", **args)
    ctx.state.caller_turns += 1
    r, _ = call(ctx, "start_return", **args, confirmed=True)
    rid = r["return_id"]  # credit is issued as part of the confirmed return
    r1, _ = call(ctx, "issue_store_credit", return_id=rid)
    assert r1["status"] == "already_issued"
    bal = ctx.conn.execute("SELECT store_credit_cents FROM customers WHERE id=1").fetchone()[0]
    assert bal == 2799


def test_cancel_only_processing(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="94110")
    r, err = call(ctx, "cancel_order", order_number="418355")
    assert err and r["error"] == "not_cancellable"


def test_sms_goes_only_to_caller_id(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "lookup_order", order_number="418355")
    r, err = call(ctx, "send_confirmation", kind="tracking", channel="sms")
    assert not err and r["to"].endswith("0101")


@pytest.mark.parametrize("q,topic", [
    ("how long does shipping take", "Shipping times and costs"),
    ("do you ship to Canada", "International shipping"),
    ("reset my password", "Password reset"),
    ("what's the return policy", "Return policy"),
])
def test_faq_hits(q, topic):
    assert faq_search(q)[0]["topic"] == topic


def test_faq_miss():
    assert faq_search("do you have a loyalty program for students") == []


def test_end_call_rejects_junk_goodbye_and_pending_change(make_ctx):
    ctx = make_ctx(MAYA)
    r, err = call(ctx, "end_call", reason="resolved", goodbye="placeholder")
    assert err and r["error"] == "bad_spoken_line" and not ctx.state.ended
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="94110")
    call(ctx, "start_return", order_number="418027", item_id=1, reason="gift", resolution="refund")
    r, err = call(ctx, "end_call", reason="resolved", goodbye="Thanks for calling Bookly, goodbye!")
    assert err and r["error"] == "change_pending" and not ctx.state.ended


def test_transfer_rejects_junk_line(make_ctx):
    ctx = make_ctx(MAYA)
    r, err = call(ctx, "transfer_to_human", reason="other", caller_wants="x", summary="y", say_to_caller="[line]")
    assert err and r["error"] == "bad_spoken_line" and not ctx.state.ended


def _readback_return(ctx, **over):
    args = dict(order_number="418027", item_id=1, reason="duplicate gift", resolution="refund", **over)
    return args, call(ctx, "start_return", **args)


def _maya_verified(make_ctx):
    ctx = make_ctx(MAYA)
    call(ctx, "lookup_customer", method="caller_id")
    call(ctx, "verify_zip", zip="94110")
    return ctx


def test_yes_must_answer_the_readback_itself(make_ctx):
    ctx = _maya_verified(make_ctx)
    args, _ = _readback_return(ctx)
    ctx.state.caller_turns += 2  # caller said no / asked something else, then "yes" later
    r, err = call(ctx, "start_return", **args, confirmed=True)
    assert err and r["error"] == "read_back_expired"
    assert ctx.conn.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 0


def test_reason_is_part_of_what_is_confirmed(make_ctx):
    ctx = _maya_verified(make_ctx)
    args, _ = _readback_return(ctx)
    ctx.state.caller_turns += 1
    r, err = call(ctx, "start_return", **{**args, "reason": "damaged"}, confirmed=True)
    assert err and r["error"] == "not_read_back"


def test_return_label_is_actually_sent_and_credit_is_atomic(make_ctx):
    ctx = _maya_verified(make_ctx)
    args = dict(order_number="418027", item_id=2, reason="didn't like it", resolution="store_credit")
    call(ctx, "start_return", **args)
    ctx.state.caller_turns += 1
    r, err = call(ctx, "start_return", **args, confirmed=True)
    assert not err
    assert ctx.conn.execute("SELECT COUNT(*) FROM outbox WHERE kind='return_label'").fetchone()[0] == 1
    assert ctx.conn.execute("SELECT store_credit_cents FROM customers WHERE id=1").fetchone()[0] == 2799


def test_shipping_zip_alone_does_not_verify(make_ctx):
    ctx = make_ctx(UNKNOWN_PHONE)
    ctx.conn.execute("UPDATE orders SET ship_zip='10001' WHERE order_number='420044'")
    call(ctx, "lookup_order", order_number="420044")
    r, _ = call(ctx, "verify_zip", zip="10001")
    assert r["verified"] is False
    r, _ = call(ctx, "verify_zip", zip="11215")
    assert r["verified"] is True


def test_order_number_guesses_are_capped(make_ctx):
    ctx = make_ctx(UNKNOWN_PHONE)
    for n in ("111111", "222222", "333333"):
        _, err = call(ctx, "lookup_order", order_number=n)
        assert err
    r, err = call(ctx, "lookup_order", order_number="420044")  # even a real one is refused now
    assert err and r["error"] == "identification_locked" and ctx.state.verified_customer is None


def test_corrected_order_number_reidentifies_and_hides_name(make_ctx):
    ctx = make_ctx(UNKNOWN_PHONE)
    r, _ = call(ctx, "lookup_order", order_number="418355")  # Maya's, said by mistake
    assert "customer_name" not in r
    r, err = call(ctx, "lookup_order", order_number="419120")  # caller corrects to their own
    assert not err and ctx.state.verified_customer["name"] == "James Okafor"
    assert ctx.state.scoped_order == "419120"


def test_no_reidentify_after_verification(make_ctx):
    ctx = make_ctx(UNKNOWN_PHONE)
    call(ctx, "lookup_order", order_number="420044")
    call(ctx, "verify_zip", zip="11215")
    _, err = call(ctx, "lookup_order", order_number="419120")
    assert err and ctx.state.verified_customer["name"] == "Sofia Alvarez"


def test_short_and_non_english_goodbyes_are_fine(make_ctx):
    ctx = make_ctx(MAYA)
    _, err = call(ctx, "end_call", reason="resolved", goodbye="Thanks, goodbye!")
    assert not err
    ctx2 = make_ctx(MAYA)
    _, err = call(ctx2, "end_call", reason="resolved", goodbye="Gracias por llamar, que tengan todos un buen día.")
    assert not err


def test_day_30_is_still_returnable(make_ctx):
    ctx = make_ctx("+17735550144")
    call(ctx, "lookup_customer", method="caller_id")
    r, _ = call(ctx, "lookup_order", order_number="417950")
    assert r["order"]["items"][0]["returnable"] is True
