import os
import requests
from dotenv import load_dotenv

from services.supabase_service import supabase


load_dotenv()

TTS_BACKEND_URL = os.getenv(
    "TTS_BACKEND_URL",
    "https://sabthazine-production.up.railway.app/tts-financial-insight",
)


def _get_page_dict_value(page, key):
    try:
        if hasattr(page, "data") and isinstance(page.data, dict):
            value = page.data.get(key)
            if value:
                return value
    except Exception:
        pass

    try:
        value = page.session.get(key)
        if value:
            return value
    except Exception:
        pass

    return None


def get_current_user_id_from_page(page):
    """
    تلاش می‌کند user_id را از page.data یا page.session پیدا کند.
    اگر ساختار پروژه فرق داشت، بعداً همین تابع را دقیق‌تر می‌کنیم.
    """
    direct_keys = [
        "user_id",
        "current_user_id",
        "auth_user_id",
    ]

    for key in direct_keys:
        value = _get_page_dict_value(page, key)
        if value:
            return value

    for key in ["user", "auth_user", "current_user"]:
        user_obj = _get_page_dict_value(page, key)
        if isinstance(user_obj, dict):
            return user_obj.get("id") or user_obj.get("user_id")

    return None


def get_current_workspace_id_from_page(page):
    direct_keys = [
        "current_workspace_id",
        "workspace_id",
        "active_workspace_id",
    ]

    for key in direct_keys:
        value = _get_page_dict_value(page, key)
        if value:
            return value

    for key in ["current_workspace", "workspace", "active_workspace"]:
        workspace_obj = _get_page_dict_value(page, key)
        if isinstance(workspace_obj, dict):
            return workspace_obj.get("id") or workspace_obj.get("workspace_id")

    return None


def load_latest_financial_insight_for_page(page, insight_type="daily"):
    user_id = get_current_user_id_from_page(page)
    workspace_id = get_current_workspace_id_from_page(page)

    if not user_id:
        return {
            "ok": False,
            "error": "کاربر شناسایی نشد.",
            "insight": None,
        }

    try:
        query = (
            supabase
            .table("financial_insights")
            .select("*")
            .eq("user_id", user_id)
            .eq("insight_type", insight_type)
            .order("insight_date", desc=True)
            .order("created_at", desc=True)
            .limit(1)
        )

        if workspace_id:
            query = query.eq("workspace_id", workspace_id)

        result = query.execute()
        rows = result.data or []

        if not rows:
            return {
                "ok": False,
                "error": "هنوز تحلیلی برای پخش وجود ندارد.",
                "insight": None,
            }

        return {
            "ok": True,
            "error": None,
            "insight": rows[0],
            "user_id": user_id,
            "workspace_id": workspace_id,
        }

    except Exception as ex:
        print("[TTS SERVICE] load insight error:", ex, flush=True)
        return {
            "ok": False,
            "error": f"خطا در دریافت تحلیل مالی: {ex}",
            "insight": None,
        }


def load_or_create_financial_insight_audio(page, insight_type="daily"):
    loaded = load_latest_financial_insight_for_page(page, insight_type=insight_type)

    if not loaded.get("ok"):
        return loaded

    insight = loaded["insight"]
    user_id = loaded["user_id"]

    audio_url = insight.get("audio_url")
    if audio_url:
        return {
            "ok": True,
            "audio_url": audio_url,
            "from_cache": True,
            "insight": insight,
        }

    text = (
        insight.get("speech_text")
        or insight.get("analysis_text")
        or ""
    ).strip()

    if not text:
        return {
            "ok": False,
            "error": "متن تحلیل خالی است.",
            "insight": insight,
        }

    try:
        response = requests.post(
            TTS_BACKEND_URL,
            json={
                "insight_id": insight["id"],
                "user_id": user_id,
                "text": text,
            },
            timeout=90,
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"خطا از backend صدا: {response.status_code} - {response.text}",
                "insight": insight,
            }

        data = response.json()

        if not data.get("ok"):
            return {
                "ok": False,
                "error": data.get("error") or "ساخت صدا ناموفق بود.",
                "insight": insight,
            }

        audio_url = data.get("audio_url")

        if not audio_url:
            return {
                "ok": False,
                "error": "backend لینک فایل صوتی را برنگرداند.",
                "insight": insight,
            }

        return {
            "ok": True,
            "audio_url": audio_url,
            "from_cache": False,
            "insight": insight,
        }

    except Exception as ex:
        print("[TTS SERVICE] create audio error:", ex, flush=True)
        return {
            "ok": False,
            "error": f"خطا در ساخت صدای تحلیل: {ex}",
            "insight": insight,
        }
