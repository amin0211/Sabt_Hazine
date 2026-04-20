from supabase import create_client
import os
from dotenv import load_dotenv
from functools import lru_cache
from datetime import datetime


load_dotenv()

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from datetime import datetime

# فرض: client از قبل در همین فایل ساخته شده
# مثلا:
# from supabase import create_client
# client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_log(message, tag=None, extra=None):
    """
    message: متن اصلی لاگ
    tag: دسته‌بندی مثل 'save_new' یا 'openai'
    extra: اطلاعات اضافه به صورت dict
    """
    try:
        payload = {
            "message": str(message),
            "tag": str(tag) if tag is not None else None,
            "extra": extra if isinstance(extra, dict) else None,
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("log").insert(payload).execute()
        return result.data

    except Exception as e:
        print(f"insert_log error: {e}")
        return None
    
@lru_cache(maxsize=1)
def load_all_hazineha():
    res = supabase.table("hazineha").select("id,id_parent,title").execute()
    return res.data or []


@lru_cache(maxsize=1)
def load_leaf_hazineha():
    rows = load_all_hazineha()

    parent_ids = {row["id_parent"] for row in rows if row.get("id_parent") is not None}

    leaf_rows = [row for row in rows if row["id"] not in parent_ids]

    return [
        {
            "id": row["id"],
            "title": row["title"]
        }
        for row in leaf_rows
    ]


def clear_hazineha_cache():
    load_all_hazineha.cache_clear()
    load_leaf_hazineha.cache_clear()
    
    
# ================= USERS =================
def get_user_by_username(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data


def register_user(data):
    return supabase.table("users").insert(data).execute()

def load_all_costs():
    return supabase.table("cost").select("*").execute().data

# ================= COST =================
def insert_cost(data):
    print("SAVE DATA =", data)
    insert_log(data.get("price"), "insert_cost 1")
    return supabase.table("cost").insert(data).execute().data[0]


def update_cost(cost_id, data):
    return supabase.table("cost").update(data).eq("id", cost_id).execute().data[0]


def delete_cost(cost_id):
    supabase.table("cost").delete().eq("id", cost_id).execute()


def load_costs(start_date, end_date):
    return (
        supabase.table("cost")
        .select("*")
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
        .order("id", desc=True)
        .execute()
        .data
    )


def get_hazine_id(title):
    res = supabase.table("hazineha").select("id").eq("title", title).execute()
    return res.data[0]["id"] if res.data else 0


def get_currency_id(currency):
    res = supabase.table("currency").select("id").eq("currency_type", currency).execute()
    return res.data[0]["id"] if res.data else 1