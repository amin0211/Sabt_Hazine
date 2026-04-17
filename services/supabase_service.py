from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ================= USERS =================
def get_user_by_username(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data


def register_user(data):
    return supabase.table("users").insert(data).execute()


# ================= COST =================
def insert_cost(data):
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