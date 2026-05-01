from datetime import datetime, timedelta
# from zoneinfo import ZoneInfo

from services.parser_service import parse_expense
from services.supabase_service import (
    insert_cost_for_current_user,
    update_my_cost,
    get_hazine_id,
    get_currency_id,
    get_my_cost_by_id,
    find_member_by_name,
)

# tz = ZoneInfo("America/Vancouver")
# now = datetime.now(tz)

def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = (text or "").lower()

    if "yesterday" in text or "دیروز" in text:
        return (datetime.now() - timedelta(days=1)).date().isoformat()

    if "today" in text or "امروز" in text:
        return datetime.now().date().isoformat()

    return datetime.now().date().isoformat()

def extract_member_id(member_name):
    member_row = find_member_by_name(member_name)
    if member_row:
        return member_row.get("id")
    return None

def process_expense(text):
    data = parse_expense(text) or {
        "title": "text 4",
        "price": None,
        "currency": None,
        "date": None,
        "member_name": None,
    }

    return {
        "title": text,
        "price": data.get("price") or 0,
        "currency_id": get_currency_id(data.get("currency")),
        "id_hazine": get_hazine_id(data.get("title")),
        "date_cost": normalize_date(data.get("date"), text),
        "temp_hazine": data.get("title"),
        "member_id": extract_member_id(data.get("member_name")),
    }


def save_new(data_or_text):
    if isinstance(data_or_text, dict):
        text = data_or_text.get("text", "")
        print(f"qqq = {text}")
        data = {
            "title": text,
            "price": data_or_text.get("price") or 0,
            "currency_id": get_currency_id(data_or_text.get("currency")),
            "id_hazine": data_or_text.get("category_id"),
            "date_cost": normalize_date(data_or_text.get("date"), text),
            "temp_hazine": data_or_text.get("title"),
            "member_id": extract_member_id(data_or_text.get("member_name")),
        }
        # 999999
        print(f"qqq1 = {data_or_text.get("member_name")}")
        print(f"member_id = {data.get('member_id')}")
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
    )