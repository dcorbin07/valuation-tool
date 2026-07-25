"""
Stripe billing — Checkout, customer portal, and the webhook that keeps each
user's tier in sync with their subscription. Only active when STRIPE_SECRET_KEY
is set; otherwise the buttons explain that billing isn't configured yet.
"""
from __future__ import annotations

from flask import request, redirect, jsonify

from .auth import current_user


def _price_to_tier(cfg, price_id):
    if price_id and price_id in (cfg.stripe_price_premium, cfg.stripe_price_premium_annual):
        return "premium"
    if price_id and price_id in (cfg.stripe_price_pro, cfg.stripe_price_pro_annual):
        return "pro"
    return "free"


def register(app, store, cfg):
    @app.route("/billing/checkout", methods=["POST"])
    def checkout():
        user = current_user(store)
        if not user:
            return redirect("/login?next=/pricing")
        if not cfg.billing_enabled:
            return jsonify({"error": "Billing isn't configured (set STRIPE_SECRET_KEY)."}), 400
        plan = request.form.get("plan", "pro")
        cycle = request.form.get("cycle", "monthly")
        if plan == "premium":
            price = cfg.stripe_price_premium_annual if cycle == "annual" else cfg.stripe_price_premium
        else:
            price = cfg.stripe_price_pro_annual if cycle == "annual" else cfg.stripe_price_pro
        if not price:
            return jsonify({"error": f"No Stripe price configured for {plan} ({cycle})."}), 400
        try:
            import stripe
            stripe.api_key = cfg.stripe_secret_key
            cust = user.get("stripe_customer_id")
            if not cust:
                cust = stripe.Customer.create(email=user["email"]).id
                store.link_stripe_customer(user["id"], cust)
            sess = stripe.checkout.Session.create(
                mode="subscription", customer=cust,
                line_items=[{"price": price, "quantity": 1}],
                success_url=cfg.public_base_url + "/account?welcome=1",
                cancel_url=cfg.public_base_url + "/pricing",
                metadata={"user_id": str(user["id"]), "plan": plan})
            return redirect(sess.url, code=303)
        except Exception as e:
            return jsonify({"error": f"Stripe error: {e}"}), 500

    @app.route("/billing/portal", methods=["POST"])
    def portal():
        user = current_user(store)
        if not user or not user.get("stripe_customer_id"):
            return redirect("/account")
        try:
            import stripe
            stripe.api_key = cfg.stripe_secret_key
            ps = stripe.billing_portal.Session.create(
                customer=user["stripe_customer_id"], return_url=cfg.public_base_url + "/account")
            return redirect(ps.url, code=303)
        except Exception as e:
            return jsonify({"error": f"Stripe error: {e}"}), 500

    @app.route("/billing/webhook", methods=["POST"])
    def webhook():
        if not cfg.billing_enabled:
            return "", 200
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                request.data, request.headers.get("Stripe-Signature"), cfg.stripe_webhook_secret)
        except Exception as e:
            return f"bad signature: {e}", 400

        t = event["type"]
        obj = event["data"]["object"]
        try:
            if t == "checkout.session.completed":
                cust = obj.get("customer")
                plan = (obj.get("metadata") or {}).get("plan", "pro")
                u = store.get_by_stripe_customer(cust)
                if u:
                    store.set_subscription(u["id"], tier=plan, status="active",
                                           stripe_subscription_id=obj.get("subscription"))
            elif t in ("customer.subscription.updated", "customer.subscription.created"):
                cust = obj.get("customer")
                status = obj.get("status")
                price_id = (((obj.get("items") or {}).get("data") or [{}])[0].get("price") or {}).get("id")
                u = store.get_by_stripe_customer(cust)
                if u:
                    tier = _price_to_tier(cfg, price_id)
                    store.set_subscription(u["id"], tier=tier if status == "active" else "free",
                                           status=status, stripe_subscription_id=obj.get("id"))
            elif t == "customer.subscription.deleted":
                u = store.get_by_stripe_customer(obj.get("customer"))
                if u:
                    store.set_subscription(u["id"], tier="free", status="canceled")
        except Exception as e:
            return f"handler error: {e}", 500
        return "", 200
