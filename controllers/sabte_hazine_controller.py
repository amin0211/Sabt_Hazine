from services.parser_service import parse_expense
from services.supabase_service import (
    insert_cost, update_cost,
    get_hazine_id, get_currency_id, insert_log
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

    # insert_log(text, "process_expense 1")

    data = parse_expense(text) or {
        # "title": text,
        "title": "text 4",
        "price": None,
        "currency": None,
        "date": None
        }   
        
    # insert_log(data.get("price"), "process_expense 1")

    return {
        "title": text, # data.get("title"),
        "price": data.get("price") or 0,
        "currency_id": get_currency_id(data.get("currency")),
        "id_hazine": get_hazine_id(data.get("title")),
        "date_cost": normalize_date(data.get("date"), text),
    }

def save_new(data_or_text):
    if isinstance(data_or_text, dict):
        data = data_or_text
        text = data.get("text", "")
        data = {
            "title": text, # data.get("title"),
            "price": data.get("price") or 0,
            "currency_id": get_currency_id(data.get("currency")),
            "id_hazine": data.get("category_id"),
            "date_cost": normalize_date(data.get("date"), text),
            }
        print("DB DATA 11 =", data)
            
    else:
        data = process_expense(data_or_text)
    
    print("DB DATA =", data)
    
    new_row = insert_cost(data)
    return new_row

# def save_new(text):
#     data = process_expense(text)
    
#     new_row = insert_cost(data)
    
#     return new_row


def edit_cost(cost_id, text):
    return update_cost(cost_id, process_expense(text))