from flask import Flask, request, jsonify
import tempfile
import os
import json
from datetime import datetime, timezone

from openai import OpenAI
from supabase import create_client

from google.oauth2 import service_account
from googleapiclient.discovery import build

from services.parser_service import parse_expense


app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ===============================
# 🔐 SUPABASE ADMIN CLIENT
# ===============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set")

supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ===============================
# 🧾 GOOGLE PLAY HELPERS
# ===============================
def get_android_publisher_service():
    service_account_json = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")

    if not service_account_json:
        raise Exception("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is not set")

    info = json.loads(service_account_json)

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )

    return build(
        "androidpublisher",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def parse_google_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).isoformat()
    except Exception:
        return None


# ===============================
# ✅ VERIFY GOOGLE PLAY PURCHASE
# ===============================
@app.route("/verify-google-play-purchase", methods=["POST"])
def verify_google_play_purchase():
    try:
        data = request.get_json(force=True) or {}

        package_name = data.get("package_name") or "com.pps.costio"
        product_id = data.get("product_id")
        purchase_token = data.get("purchase_token")
        order_id = data.get("order_id")
        user_id = data.get("user_id")
        workspace_id = data.get("workspace_id")
        plan_type = data.get("plan_type")

        if not product_id or not purchase_token or not user_id:
            return jsonify({
                "success": False,
                "error": "product_id, purchase_token, and user_id are required",
            }), 400

        service = get_android_publisher_service()

        google_result = (
            service.purchases()
            .subscriptionsv2()
            .get(
                packageName=package_name,
                token=purchase_token,
            )
            .execute()
        )

        subscription_state = google_result.get("subscriptionState")
        latest_order_id = google_result.get("latestOrderId") or order_id

        line_items = google_result.get("lineItems") or []

        expiry_time = None
        auto_renewing = False

        if line_items:
            first_item = line_items[0]

            expiry_time = first_item.get("expiryTime")

            auto_renewing_plan = first_item.get("autoRenewingPlan") or {}
            auto_renewing = bool(
                auto_renewing_plan.get("autoRenewEnabled")
            )

        current_period_end = parse_google_time(expiry_time)

        active_states = [
            "SUBSCRIPTION_STATE_ACTIVE",
            "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
        ]

        is_active = subscription_state in active_states
        status = "active" if is_active else "inactive"

        if not plan_type:
            if product_id == "costio_monthly":
                plan_type = "monthly"
            elif product_id == "costio_yearly":
                plan_type = "yearly"
            else:
                plan_type = "unknown"

        payload = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "provider": "google_play",
            "plan_type": plan_type,
            "status": status,
            "google_product_id": product_id,
            "google_purchase_token": purchase_token,
            "google_order_id": latest_order_id,
            "current_period_end": current_period_end,
            "auto_renewing": auto_renewing,
            "acknowledged": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = (
            supabase_admin.table("user_subscriptions")
            .upsert(
                payload,
                on_conflict="user_id,workspace_id",
            )
            .execute()
        )

        return jsonify({
            "success": True,
            "status": status,
            "subscription_state": subscription_state,
            "current_period_end": current_period_end,
            "subscription": result.data,
        }), 200

    except Exception as e:
        print("VERIFY GOOGLE PLAY ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# ===============================
# 🎤 VOICE → TEXT
# ===============================
@app.route("/voice-to-text", methods=["POST"])
def voice_to_text():
    try:
        file = request.files["file"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            file.save(temp.name)
            path = temp.name

        with open(path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio
            )

        os.remove(path)

        return jsonify({"text": transcript.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# 🧠 TEXT → PARSE EXPENSE
# ===============================
@app.route("/parse", methods=["POST"])
def parse_text():
    try:
        data = request.get_json()
        text = data.get("text", "")

        result = parse_expense(text)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# 🔄 VOICE → TEXT → PARSE
# ===============================
@app.route("/voice-parse", methods=["POST"])
def voice_parse():
    try:
        file = request.files["file"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            file.save(temp.name)
            path = temp.name

        with open(path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio
            )

        os.remove(path)

        text = transcript.text
        parsed = parse_expense(text)

        return jsonify({
            "text": text,
            "parsed": parsed
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# ❤️ HEALTH CHECK
# ===============================
@app.route("/")
def home():
    return "🚀 Server is running"


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "supabase": bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "google_play": bool(os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")),
    })


# ===============================
# ▶ RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)