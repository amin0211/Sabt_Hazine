from services.parser_service import parse_expense
from services.supabase_service import (
    insert_cost, update_cost,
    get_hazine_id, get_currency_id
)

from datetime import datetime, timedelta


def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = text.lower()

    if "yesterday" in text or "دیروز" in text:
        return (datetime.now() - timedelta(days=1)).date().isoformat()

    if "today" in text or "امروز" in text:
        return datetime.now().date().isoformat()

    return datetime.now().date().isoformat()


def process_expense(text):
    data = parse_expense(text)

    return {
        "title": text, # data.get("title"),
        "price": data.get("price") or 0,
        "currency_id": get_currency_id(data.get("currency")),
        "id_hazine": get_hazine_id(data.get("title")),
        "date_cost": normalize_date(data.get("date"), text),
    }


def save_new(text):
    return insert_cost(process_expense(text))


def edit_cost(cost_id, text):
    return update_cost(cost_id, process_expense(text))