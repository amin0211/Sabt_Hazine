import os
from datetime import datetime, timezone

import stripe
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from supabase import create_client

app = Flask(__name__)
CORS(app)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_MONTHLY_PRICE_ID = os.getenv("STRIPE_MONTHLY_PRICE_ID")
STRIPE_YEARLY_PRICE_ID = os.getenv("STRIPE_YEARLY_PRICE_ID")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

SUCCESS_URL = os.getenv("SUCCESS_URL", "https://example.com/success")
CANCEL_URL = os.getenv("CANCEL_URL", "https://example.com/cancel")
PORTAL_RETURN_URL = os.getenv("PORTAL_RETURN_URL", SUCCESS_URL)

if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is required")

if not STRIPE_WEBHOOK_SECRET:
    raise RuntimeError("STRIPE_WEBHOOK_SECRET is required")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

stripe.api_key = STRIPE_SECRET_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_price_id(plan: str) -> str:
    if plan == "monthly":
        if not STRIPE_MONTHLY_PRICE_ID:
            raise RuntimeError("STRIPE_MONTHLY_PRICE_ID is missing")
        return STRIPE_MONTHLY_PRICE_ID

    if plan == "yearly":
        if not STRIPE_YEARLY_PRICE_ID:
            raise RuntimeError("STRIPE_YEARLY_PRICE_ID is missing")
        return STRIPE_YEARLY_PRICE_ID

    raise ValueError("Invalid plan. Use monthly or yearly.")


def plan_from_price_id(price_id: str | None) -> str | None:
    if price_id == STRIPE_MONTHLY_PRICE_ID:
        return "monthly"
    if price_id == STRIPE_YEARLY_PRICE_ID:
        return "yearly"
    return None


def unix_to_iso(value):
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


def get_or_create_customer(user_id: str, email: str | None = None) -> str:
    rows = (
        supabase.table("user_subscriptions")
        .select("stripe_customer_id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )

    for row in rows:
        customer_id = row.get("stripe_customer_id")
        if customer_id:
            return customer_id

    customer = stripe.Customer.create(
        email=email,
        metadata={"user_id": user_id},
    )
    return customer.id


def upsert_subscription_from_stripe_subscription(subscription_id: str):
    subscription = stripe.Subscription.retrieve(
        subscription_id,
        expand=["items.data.price", "customer"],
    )

    metadata = subscription.get("metadata") or {}
    user_id = metadata.get("user_id")
    workspace_id = metadata.get("workspace_id") or None

    customer_obj = subscription.get("customer")
    customer_id = customer_obj

    if isinstance(customer_obj, dict):
        customer_id = customer_obj.get("id")
        customer_metadata = customer_obj.get("metadata") or {}
        if not user_id:
            user_id = customer_metadata.get("user_id")

    if not user_id:
        raise RuntimeError("Missing user_id in Stripe subscription metadata")

    items = subscription.get("items", {}).get("data", [])
    if not items:
        raise RuntimeError("Stripe subscription has no items")

    price_id = items[0]["price"]["id"]
    plan_type = plan_from_price_id(price_id)

    payload = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "plan_type": plan_type,
        "status": subscription.get("status"),
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription.get("id"),
        "current_period_start": unix_to_iso(subscription.get("current_period_start")),
        "current_period_end": unix_to_iso(subscription.get("current_period_end")),
        "cancel_at_period_end": bool(subscription.get("cancel_at_period_end")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = (
        supabase.table("user_subscriptions")
        .upsert(payload, on_conflict="stripe_subscription_id")
        .execute()
    )

    return result.data


@app.get("/")
def health():
    return jsonify(
        {
            "ok": True,
            "service": "sabt-hazine-stripe-backend",
        }
    )


@app.get("/success")
def success():
    return "Payment successful. You can close this page."


@app.get("/cancel")
def cancel():
    return "Payment canceled."


@app.get("/create-checkout-session")
def create_checkout_session():
    plan = request.args.get("plan", "monthly")
    user_id = request.args.get("user_id")
    workspace_id = request.args.get("workspace_id")
    email = request.args.get("email")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        price_id = get_price_id(plan)
        customer_id = get_or_create_customer(user_id, email)

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            client_reference_id=user_id,
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "workspace_id": workspace_id or "",
                    "plan_type": plan,
                }
            },
            metadata={
                "user_id": user_id,
                "workspace_id": workspace_id or "",
                "plan_type": plan,
            },
        )

        return redirect(session.url, code=303)

    except Exception as ex:
        print("CREATE CHECKOUT ERROR:", ex, flush=True)
        return jsonify({"error": str(ex)}), 500


@app.get("/create-customer-portal")
def create_customer_portal():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    rows = (
        supabase.table("user_subscriptions")
        .select("stripe_customer_id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )

    customer_id = None
    for row in rows:
        if row.get("stripe_customer_id"):
            customer_id = row["stripe_customer_id"]
            break

    if not customer_id:
        return jsonify({"error": "No Stripe customer found for this user"}), 404

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=PORTAL_RETURN_URL,
        )
        return redirect(portal_session.url, code=303)

    except Exception as ex:
        print("CUSTOMER PORTAL ERROR:", ex, flush=True)
        return jsonify({"error": str(ex)}), 500


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event["type"]
    obj = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            subscription_id = obj.get("subscription")
            if subscription_id:
                upsert_subscription_from_stripe_subscription(subscription_id)

        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            subscription_id = obj.get("id")
            if subscription_id:
                upsert_subscription_from_stripe_subscription(subscription_id)

        elif event_type == "invoice.paid":
            subscription_id = obj.get("subscription")
            if subscription_id:
                upsert_subscription_from_stripe_subscription(subscription_id)

        elif event_type == "invoice.payment_failed":
            subscription_id = obj.get("subscription")
            if subscription_id:
                upsert_subscription_from_stripe_subscription(subscription_id)

    except Exception as ex:
        print("WEBHOOK ERROR:", ex, flush=True)
        return jsonify({"error": str(ex)}), 500

    return jsonify({"received": True}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)