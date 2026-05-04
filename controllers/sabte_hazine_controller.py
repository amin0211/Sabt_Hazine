from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.parser_service import parse_expense
from services.supabase_service import (
    insert_cost_for_current_user,
    update_my_cost,
    get_hazine_id,
    get_my_cost_by_id,
    find_member_by_name,
    find_account_by_name,
    get_default_account,
)

tz = ZoneInfo("America/Vancouver")
# now = datetime.now(tz)
def now_local():
    return datetime.now(tz)

def today_local():
    return now_local().date()

def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = (text or "").lower()
    today = today_local()

    if "yesterday" in text or "دیروز" in text:
        return (today - timedelta(days=1)).isoformat()

    if "today" in text or "امروز" in text:
        return today.isoformat()

    return today.isoformat()

def extract_member_id(member_name):
    member_row = find_member_by_name(member_name)
    if member_row:
        return member_row.get("id")
    return None


def extract_account_id(account_name):
    # 1️⃣ اگر کاربر حساب گفته
    if account_name:
        account_row = find_account_by_name(account_name)
        if account_row:
            return account_row.get("id")

    # 2️⃣ fallback → حساب پیش‌فرض
    default_account = get_default_account()
    if default_account:
        return default_account.get("id")

    # 3️⃣ fallback نهایی (خیلی مهم)
    # اگر حتی default هم نداشت → اولین حساب کاربر
    from services.supabase_service import get_accounts

    accounts = get_accounts() or []
    if accounts:
        return accounts[0].get("id")

    return None


def process_expense(text):
    data = parse_expense(text) or {
        "title": "text 4",
        "price": None,
        "currency": None,
        "date": None,
        "member_name": None,
        "account_name": None,
    }

    return {
        "title": text,
        "price": data.get("price") or 0,
        "id_hazine": get_hazine_id(data.get("title")),
        "date_cost": normalize_date(data.get("date"), text),
        "temp_hazine": data.get("title"),
        "member_id": extract_member_id(data.get("member_name")),
        "account_id": extract_account_id(data.get("account_name")),
    }

def save_new(data_or_text):
    if isinstance(data_or_text, dict):
        text = data_or_text.get("text", "")
        data = {
            "title": text,
            "price": data_or_text.get("price") or 0,
            # "currency_id": get_currency_id(data_or_text.get("currency")),
            "id_hazine": data_or_text.get("category_id"),
            "date_cost": normalize_date(data_or_text.get("date"), text),
            "temp_hazine": data_or_text.get("title"),
            "member_id": extract_member_id(data_or_text.get("member_name")),
            "account_id": extract_account_id(data_or_text.get("account_name")),
        }
        # 999999
    else:
        data = process_expense(data_or_text)

    # print(f"aaaa = {text}")
    # print(f"aaaa1 = {data_or_text.get("member_id")}")
    # print(f"aaaa2 = {data_or_text.get("title")}")
    
    inserted = insert_cost_for_current_user(data)
    if not inserted:
        return None

    full_row = get_my_cost_by_id(inserted["id"])
    return full_row or inserted


def edit_cost(cost_id, updated_data):
    return update_my_cost(
        cost_id=cost_id,
        title=updated_data["title"],
        price=updated_data["price"],
        date_cost=updated_data["date_cost"],
        id_hazine=updated_data["id_hazine"],
        member_id=updated_data["member_id"],
        account_id=updated_data["account_id"],
    )