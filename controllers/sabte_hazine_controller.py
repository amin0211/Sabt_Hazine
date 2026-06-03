from services.parser_service import parse_expense
from services.utils import normalize_date, local_date_iso
from services.supabase_service import (
    insert_cost_for_current_user,
    update_my_cost,
    get_hazine_id,
    get_my_cost_by_id,
    find_member_by_name,
    find_account_by_name,
    get_default_account,
)



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


def process_expense(text, page=None):
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
        "date_cost": normalize_date(data.get("date"), text, page),
        "temp_hazine": data.get("title"),
        "member_id": extract_member_id(data.get("member_name")),
        "account_id": extract_account_id(data.get("account_name")),
    }

def save_new(data_or_text, page=None):
    if isinstance(data_or_text, dict):
        text = data_or_text.get("text", "")
        
        workspace_id = None
        root_hazine_id = None

        if page and isinstance(page.data, dict):
            workspace_id = page.data.get("current_workspace_id")
            root_hazine_id = page.data.get("root_hazine_id")

        member_id = data_or_text.get("member_id")
        if not member_id and data_or_text.get("member_name"):
            member_id = extract_member_id(data_or_text.get("member_name"))

        account_id = data_or_text.get("account_id")
        if not account_id:
            account_id = extract_account_id(data_or_text.get("account_name"))

        # ✅ مهم‌ترین قسمت: اگر کتگوری پیدا نشد، root workspace بخورد
        category_id = data_or_text.get("category_id")

        if not category_id:
            category_id = root_hazine_id

        data = {
            "title": text,
            "price": data_or_text.get("price") or 0,
            "id_hazine": category_id,
            "date_cost": local_date_iso(page, data_or_text.get("date")),
            "temp_hazine": data_or_text.get("title"),
            "member_id": member_id,
            "account_id": account_id,
            "workspace_id": workspace_id,
        }

        parsed_source = data_or_text

    else:
        data = process_expense(data_or_text, page)
        parsed_source = {}
        member_id = data.get("member_id")
        account_id = data.get("account_id")

        # ✅ برای حالت متنی قدیمی هم fallback بگذار
        if not data.get("id_hazine") and page and isinstance(page.data, dict):
            data["id_hazine"] = page.data.get("root_hazine_id")

    inserted = insert_cost_for_current_user(data)

    if not inserted:
        return None

    inserted["category_title"] = parsed_source.get("category_title") or ""
    inserted["member_id"] = member_id
    inserted["member_name"] = parsed_source.get("member_name") or ""
    inserted["account_id"] = account_id
    inserted["account_name"] = parsed_source.get("account_name") or ""
    inserted["account_type"] = parsed_source.get("account_type") or ""

    return inserted

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