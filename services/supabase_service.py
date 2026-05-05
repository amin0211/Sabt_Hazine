from supabase import create_client
import os
import json
from dotenv import load_dotenv
from functools import lru_cache
from datetime import datetime, date, timedelta
import calendar
from collections import defaultdict
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def now_local():
    return datetime.now(TZ)

def today_local():
    return now_local().date()

load_dotenv()

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY is not set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_languages():
    res = supabase.table("languages").select("*").order("id").execute()
    return res.data or []


def get_my_profile():
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    res = (
        supabase.table("profiles")
        .select("id, email, name, family, birthdate, language_id")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return res.data if res.data else None

def get_my_profile_with_language():
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    res = (
        supabase.table("profiles")
        .select("id, name, family, birthdate, language_id, languages(code, name, is_rtl)")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return res.data if res.data else None

def update_my_profile(data: dict):
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    res = (
        supabase.table("profiles")
        .update(data)
        .eq("id", user_id)
        .execute()
    )
    return res.data


def get_my_profile():
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data if res.data else None

def update_my_profile(data: dict):
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    res = supabase.table("profiles").update(data).eq("id", user_id).execute()
    return res.data

def get_account_balances():
    user = get_current_user()
    res = supabase.rpc("get_account_balances", {"p_user_id": user.id}).execute()
    return res.data or []

def get_account_transactions(account_id):
    user = get_current_user()
    if not user:
        return []

    rows = []

    # هزینه‌ها
    costs = (
        supabase.table("cost")
        .select("id,title,price,date_cost")
        .eq("user_id", user.id)
        .eq("account_id", account_id)
        .execute()
        .data
    ) or []

    for c in costs:
        rows.append({
            "date": c.get("date_cost"),
            "title": c.get("title") or "Expense",
            "amount": -float(c.get("price") or 0),
            "type": "expense",
        })

    # درآمدها
    incomes = (
        supabase.table("income_transactions")
        .select("id,title,amount,transaction_date,status")
        .eq("user_id", user.id)
        .eq("account_id", account_id)
        .eq("is_active", True)
        .execute()
        .data
    ) or []

    for i in incomes:
        rows.append({
            "date": i.get("transaction_date"),
            "title": i.get("title") or "Income",
            "amount": float(i.get("amount") or 0),
            "type": "income",
        })

    # انتقال‌ها - خروجی از حساب
    transfers_out = (
        supabase.table("transfer_transactions")
        .select("id,amount,transfer_date,note")
        .eq("user_id", user.id)
        .eq("from_account_id", account_id)
        .execute()
        .data
    ) or []

    for t in transfers_out:
        rows.append({
            "date": t.get("transfer_date"),
            "title": t.get("note") or "Transfer Out",
            "amount": -float(t.get("amount") or 0),
            "type": "transfer_out",
        })

    # انتقال‌ها - ورودی به حساب
    transfers_in = (
        supabase.table("transfer_transactions")
        .select("id,amount,transfer_date,note")
        .eq("user_id", user.id)
        .eq("to_account_id", account_id)
        .execute()
        .data
    ) or []

    for t in transfers_in:
        rows.append({
            "date": t.get("transfer_date"),
            "title": t.get("note") or "Transfer In",
            "amount": float(t.get("amount") or 0),
            "type": "transfer_in",
        })

    rows.sort(key=lambda x: x.get("date") or "", reverse=True)
    return rows

def create_transfer(from_account_id, to_account_id, amount, transfer_date, note=None):
    user = get_current_user()
    if not user:
        raise Exception("User not logged in")

    data = {
        "user_id": user.id,
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "amount": amount,
        "transfer_date": transfer_date,
        "note": note,
    }

    res = supabase.table("transfer_transactions").insert(data).execute()
    return res.data

# ================= FAMILY MEMBERS =================
def find_member_by_name(member_name: str):
    print("sssss")
    user = get_current_user()
    if not user:
        return None

    if not member_name or not member_name.strip():
        return None

    name = member_name.strip()

    # اول exact match
    exact = (
        supabase.table("members")
        .select("id, full_name, relation")
        .eq("user_id", user.id)
        .eq("full_name", name)
        .limit(1)
        .execute()
    )

    if exact.data:
        return exact.data[0]

    # بعد contains / ilike
    fuzzy = (
        supabase.table("members")
        .select("id, full_name, relation")
        .eq("user_id", user.id)
        .ilike("full_name", f"%{name}%")
        .limit(1)
        .execute()
    )

    return fuzzy.data[0] if fuzzy.data else None

def get_members():
    user = get_current_user()
    if not user:
        return []

    res = (
        supabase.table("members")
        .select("*")
        .eq("user_id", user.id)
        .order("id")
        .execute()
    )
    return res.data or []


def add_member(full_name, relation=None):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    payload = {
        "user_id": user.id,
        "full_name": full_name.strip(),
        "relation": relation.strip() if relation else None,
    }

    print("333")
    res = supabase.table("members").insert(payload).execute()
    print("444")
    return res.data[0] if res.data else None

def update_member(member_id, full_name, relation=None):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    payload = {
        "full_name": full_name.strip(),
        "relation": relation.strip() if relation else None,
    }

    res = (
        supabase.table("members")
        .update(payload)
        .eq("id", member_id)
        .eq("user_id", user.id)
        .execute()
    )

    return res.data[0] if res.data else None

def delete_member(member_id):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("members") \
        .delete() \
        .eq("id", member_id) \
        .eq("user_id", user.id) \
        .execute()
    
# ================= LOG =================
def insert_log(message, tag=None, extra=None):
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


# ================= HELPERS =================
def _normalize_keywords_field(raw_keywords):
    if raw_keywords is None:
        return []

    if isinstance(raw_keywords, list):
        return [str(x).strip() for x in raw_keywords if str(x).strip()]

    if isinstance(raw_keywords, str):
        raw_keywords = raw_keywords.strip()
        if not raw_keywords:
            return []

        try:
            parsed = json.loads(raw_keywords)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass

        if "," in raw_keywords:
            return [x.strip() for x in raw_keywords.split(",") if x.strip()]

        return [raw_keywords]

    return []


def _normalize_embedding(raw_embedding):
    if raw_embedding is None:
        return None

    if isinstance(raw_embedding, list):
        try:
            return [float(x) for x in raw_embedding]
        except Exception:
            return None

    return raw_embedding


def _vector_to_sql(vector):
    if not vector:
        return None
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


def clear_hazineha_cache():
    _load_all_hazineha_for_user.cache_clear()
    _load_active_hazineha_for_user.cache_clear()
    _load_leaf_hazineha_for_user.cache_clear()


# ================= AUTH =================
def sign_up_user(email: str, password: str):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
    })


def sign_in_user(email: str, password: str):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })


def sign_out_user():
    return supabase.auth.sign_out()


def get_current_session():
    result = supabase.auth.get_session()
    return result.session


def get_current_user():
    try:
        result = supabase.auth.get_user()
        return result.user
    except Exception as e:
        print(f"get_current_user error: {e}")
        return None


def set_session(access_token: str, refresh_token: str):
    return supabase.auth.set_session(access_token, refresh_token)


# ================= PROFILE =================
def get_profile(user_id: str):
    try:
        result = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"get_profile error: {e}")
        return None


# def get_profile_by_username(username: str):
#     try:
#         result = (
#             supabase.table("profiles")
#             .select("*")
#             .eq("username", username)
#             .execute()
#         )
#         return result.data or []
#     except Exception as e:
#         print(f"get_profile_by_username error: {e}")
#         return []


def update_profile(user_id: str, data: dict):
    try:
        result = (
            supabase.table("profiles")
            .update(data)
            .eq("id", user_id)
            .execute()
        )
        return result.data
    except Exception as e:
        print(f"update_profile error: {e}")
        return None

def refresh_hazineha_titles_for_user(user_id: str, language_id: int):
    try:
        if not user_id:
            raise Exception("user_id is required")

        # همه دسته‌بندی‌های کاربر که از template آمده‌اند
        hazine_rows = (
            supabase.table("hazineha")
            .select("id,template_id")
            .eq("user_id", user_id)
            .execute()
            .data
        ) or []

        if not hazine_rows:
            return True

        template_ids = [row["template_id"] for row in hazine_rows if row.get("template_id")]
        if not template_ids:
            return True

        # title اصلی template برای fallback
        template_rows = (
            supabase.table("hazineha_template")
            .select("id,title")
            .in_("id", template_ids)
            .execute()
            .data
        ) or []

        template_map = {row["id"]: row.get("title") or "" for row in template_rows}

        # ترجمه‌های زبان جدید
        dic_rows = (
            supabase.table("hazineha_dic")
            .select("hazine_id,title")
            .eq("language_id", language_id)
            .in_("hazine_id", template_ids)
            .execute()
            .data
        ) or []

        dic_map = {row["hazine_id"]: row.get("title") or "" for row in dic_rows}

        # آپدیت رکوردها
        for row in hazine_rows:
            template_id = row.get("template_id")
            if not template_id:
                continue

            new_title = dic_map.get(template_id) or template_map.get(template_id) or ""

            (
                supabase.table("hazineha")
                .update({"title": new_title})
                .eq("id", row["id"])
                .eq("user_id", user_id)
                .execute()
            )

        clear_hazineha_cache()
        return True

    except Exception as e:
        print(f"refresh_hazineha_titles_for_user error: {e}")
        raise

def create_default_account_for_user(user_id: str):
    data = {
        "user_id": user_id,
        "account_type": "bank",
        "account_name": "حساب اصلی",
        "initial_balance": 0,
        "is_default": True,
        "is_active": True,
    }

    return supabase.table("accounts").insert(data).execute()

def copy_hazineha_template_for_user(user_id: str):
    return supabase.rpc(
        "copy_hazineha_template_for_user",
        {"p_user_id": user_id}
    ).execute()


# ================= HAZINEHA / CATEGORY =================
@lru_cache(maxsize=256)
def _load_all_hazineha_for_user(user_id: str):
    try:
        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id")
            .eq("user_id", user_id)
            .order("id")
            .execute()
        )

        rows = res.data or []

        cleaned = []
        for row in rows:
            cleaned.append({
                "id": row.get("id"),
                "id_parent": row.get("id_parent"),
                "title": row.get("title") or "",
                "keywords": _normalize_keywords_field(row.get("keywords")),
                "embedding_text": row.get("embedding_text") or "",
                "updated_at": row.get("updated_at"),
                "is_active": bool(row.get("is_active", True)),
                "user_id": row.get("user_id"),
                "template_id": row.get("template_id"),
            })

        return cleaned

    except Exception as e:
        print(f"_load_all_hazineha_for_user error: {e}")
        return []


def load_all_hazineha():
    try:
        user = get_current_user()
        if not user:
            return []
        return _load_all_hazineha_for_user(user.id)
    except Exception as e:
        print(f"load_all_hazineha error: {e}")
        return []


@lru_cache(maxsize=256)
def _load_active_hazineha_for_user(user_id: str):
    rows = _load_all_hazineha_for_user(user_id)
    return [row for row in rows if row.get("is_active", True)]


def load_active_hazineha():
    try:
        user = get_current_user()
        if not user:
            return []
        return _load_active_hazineha_for_user(user.id)
    except Exception as e:
        print(f"load_active_hazineha error: {e}")
        return []


@lru_cache(maxsize=256)
def _load_leaf_hazineha_for_user(user_id: str):
    rows = _load_active_hazineha_for_user(user_id)

    parent_ids = {
        row["id_parent"]
        for row in rows
        if row.get("id_parent") is not None
    }

    selected_rows = []
    for row in rows:
        is_leaf = row["id"] not in parent_ids
        has_keywords = bool(row.get("keywords"))
        has_embedding_text = bool((row.get("embedding_text") or "").strip())

        if is_leaf or has_keywords or has_embedding_text:
            selected_rows.append(row)

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "keywords": row.get("keywords", []),
            "embedding_text": row.get("embedding_text", ""),
            "is_active": row.get("is_active", True),
            "user_id": row.get("user_id"),
            "template_id": row.get("template_id"),
        }
        for row in selected_rows
    ]


def load_leaf_hazineha():
    try:
        user = get_current_user()
        if not user:
            return []
        return _load_leaf_hazineha_for_user(user.id)
    except Exception as e:
        print(f"load_leaf_hazineha error: {e}")
        return []


@lru_cache(maxsize=1)
def load_leaf_hazineha():
    rows = load_active_hazineha()

    parent_ids = {
        row["id_parent"]
        for row in rows
        if row.get("id_parent") is not None
    }

    selected_rows = []
    for row in rows:
        is_leaf = row["id"] not in parent_ids
        has_keywords = bool(row.get("keywords"))
        has_embedding_text = bool((row.get("embedding_text") or "").strip())

        if is_leaf or has_keywords or has_embedding_text:
            selected_rows.append(row)

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "keywords": row.get("keywords", []),
            "embedding_text": row.get("embedding_text", ""),
            "is_active": row.get("is_active", True),
        }
        for row in selected_rows
    ]


def get_hazine_by_id(category_id):
    try:
        user = get_current_user()
        if not user:
            return None

        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id")
            .eq("id", category_id)
            .eq("user_id", user.id)
            .single()
            .execute()
        )

        row = res.data
        if not row:
            return None

        return {
            "id": row.get("id"),
            "id_parent": row.get("id_parent"),
            "title": row.get("title") or "",
            "keywords": _normalize_keywords_field(row.get("keywords")),
            "embedding_text": row.get("embedding_text") or "",
            "updated_at": row.get("updated_at"),
            "is_active": bool(row.get("is_active", True)),
            "user_id": row.get("user_id"),
            "template_id": row.get("template_id"),
        }

    except Exception as e:
        print(f"get_hazine_by_id error: {e}")
        return None

def get_hazine_by_title(title):
    try:
        user = get_current_user()
        if not user:
            return None

        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id")
            .eq("user_id", user.id)
            .eq("title", title)
            .limit(1)
            .execute()
        )

        rows = res.data or []
        if not rows:
            return None

        row = rows[0]
        return {
            "id": row.get("id"),
            "id_parent": row.get("id_parent"),
            "title": row.get("title") or "",
            "keywords": _normalize_keywords_field(row.get("keywords")),
            "embedding_text": row.get("embedding_text") or "",
            "updated_at": row.get("updated_at"),
            "is_active": bool(row.get("is_active", True)),
            "user_id": row.get("user_id"),
            "template_id": row.get("template_id"),
        }

    except Exception as e:
        print(f"get_hazine_by_title error: {e}")
        return None


def create_hazine(title, id_parent=None, keywords=None, embedding_text=None, is_active=True):
    try:
        user = get_current_user()
        if not user:
            raise Exception("User is not logged in")

        payload = {
            "user_id": user.id,
            "title": title,
            "id_parent": id_parent,
            "keywords": keywords if isinstance(keywords, list) else [],
            "embedding_text": embedding_text or "",
            "is_active": bool(is_active),
            "template_id": None,
        }

        result = supabase.table("hazineha").insert(payload).execute()
        clear_hazineha_cache()

        return result.data[0] if result.data else None

    except Exception as e:
        print(f"create_hazine error: {e}")
        return None
    
def update_hazine(category_id, title=None, id_parent=None, keywords=None, embedding_text=None, is_active=None):
    try:
        user = get_current_user()
        if not user:
            raise Exception("User is not logged in")

        payload = {}

        if title is not None:
            payload["title"] = title

        if id_parent is not None:
            payload["id_parent"] = id_parent

        if keywords is not None:
            payload["keywords"] = keywords if isinstance(keywords, list) else []

        if embedding_text is not None:
            payload["embedding_text"] = embedding_text

        if is_active is not None:
            payload["is_active"] = bool(is_active)

        if not payload:
            return get_hazine_by_id(category_id)

        result = (
            supabase.table("hazineha")
            .update(payload)
            .eq("id", category_id)
            .eq("user_id", user.id)
            .execute()
        )

        clear_hazineha_cache()
        return result.data[0] if result.data else get_hazine_by_id(category_id)

    except Exception as e:
        print(f"update_hazine error: {e}")
        return None
    
def update_hazine_embedding(category_id, embedding_vector):
    try:
        if not embedding_vector:
            return False

        supabase.rpc(
            "set_hazineha_embedding",
            {
                "p_category_id": category_id,
                "p_embedding": embedding_vector,
            }
        ).execute()

        clear_hazineha_cache()
        return True

    except Exception as e:
        print(f"update_hazine_embedding error: {e}")
        return False

def load_hazineha_with_embeddings(active_only=True):
    try:
        user = get_current_user()
        if not user:
            return []

        q = supabase.table("hazineha").select(
            "id,id_parent,title,keywords,embedding_text,embedding,is_active,updated_at,user_id,template_id"
        ).eq("user_id", user.id)

        if active_only:
            q = q.eq("is_active", True)

        res = q.order("id").execute()
        rows = res.data or []

        cleaned = []
        for row in rows:
            cleaned.append({
                "id": row.get("id"),
                "id_parent": row.get("id_parent"),
                "title": row.get("title") or "",
                "keywords": _normalize_keywords_field(row.get("keywords")),
                "embedding_text": row.get("embedding_text") or "",
                "embedding": _normalize_embedding(row.get("embedding")),
                "is_active": bool(row.get("is_active", True)),
                "updated_at": row.get("updated_at"),
                "user_id": row.get("user_id"),
                "template_id": row.get("template_id"),
            })

        return cleaned

    except Exception as e:
        print(f"load_hazineha_with_embeddings error: {e}")
        return []
    
# ================= CATEGORY LEARNING =================
def get_learned_category_exact(normalized_text):
    try:
        user = get_current_user()
        if not user:
            return None

        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at")
            .eq("user_id", user.id)
            .eq("normalized_text", normalized_text)
            .order("use_count", desc=True)
            .limit(1)
            .execute()
        )

        rows = res.data or []
        return rows[0] if rows else None

    except Exception as e:
        print(f"get_learned_category_exact error: {e}")
        return None


def load_category_learning_rows():
    try:
        user = get_current_user()
        if not user:
            return None

        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at,embedding_text,embedding")
            .eq("user_id", user.id)
            .order("use_count", desc=True)
            .execute()
        )

        rows = res.data or []
        cleaned = []
        for row in rows:
            cleaned.append({
                "id": row.get("id"),
                "raw_text": row.get("raw_text") or "",
                "normalized_text": row.get("normalized_text") or "",
                "category_id": row.get("category_id"),
                "source": row.get("source"),
                "confidence": row.get("confidence"),
                "use_count": row.get("use_count", 1),
                "last_used_at": row.get("last_used_at"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "embedding_text": row.get("embedding_text") or "",
                "embedding": _normalize_embedding(row.get("embedding")),
            })
        return cleaned

    except Exception as e:
        print(f"load_category_learning_rows error: {e}")
        return []

def upsert_category_learning(
    raw_text,
    normalized_text,
    category_id,
    source="user_corrected",
    embedding_text=None,
):
    user = supabase.auth.get_user()
    user_id = user.user.id

    data = {
        "user_id": user_id,
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "category_id": category_id,
        "source": source,
        "embedding_text": embedding_text or normalized_text,
        "updated_at": "now()",
    }

    res = (
        supabase
        .table("category_learning")
        .upsert(
            data,
            on_conflict="user_id,normalized_text"
        )
        .execute()
    )

    if res.data:
        return res.data[0]

    return None


def update_category_learning_embedding(learning_id, embedding_vector):
    try:
        if not embedding_vector:
            return False

        supabase.rpc(
            "set_category_learning_embedding",
            {
                "p_learning_id": learning_id,
                "p_embedding": embedding_vector,
            }
        ).execute()

        return True

    except Exception as e:
        print(f"update_category_learning_embedding error: {e}")
        return False


def find_category_learning_exact(normalized_text: str):
    try:
        user = get_current_user()
        if not user:
            return None
        
        res = (
            supabase.table("category_learning")
            .select("id, raw_text, normalized_text, category_id, hazineha(title)")
            .eq("user_id", user.id)
            .eq("normalized_text", normalized_text)
            .limit(1)
            .execute()
        )

        rows = res.data or []
        if not rows:
            return None

        row = rows[0]
        return {
            "id": row.get("id"),
            "raw_text": row.get("raw_text"),
            "normalized_text": row.get("normalized_text"),
            "category_id": row.get("category_id"),
            "category_title": (row.get("hazineha") or {}).get("title"),
        }

    except Exception as e:
        print("find_category_learning_exact error:", e)
        return None


def match_category_learning_by_embedding(embedding_vector, threshold=0.78):
    try:
       
        res = supabase.rpc(
            "match_category_learning",
            {
                "query_embedding": embedding_vector,
                "match_threshold": threshold,
                "match_count": 1,
            }
        ).execute()

        rows = res.data or []
        if not rows:
            return None

        row = rows[0]
        return {
            "id": row.get("id"),
            "raw_text": row.get("raw_text"),
            "normalized_text": row.get("normalized_text"),
            "category_id": row.get("category_id"),
            "category_title": row.get("category_title"),
            "score": row.get("similarity"),
        }

    except Exception as e:
        print("match_category_learning_by_embedding error:", e)
        return None


# ================= COST =================
def load_all_costs():
    return supabase.table("cost").select("*").execute().data


def load_my_costs():
    user = get_current_user()
    if not user:
        return []

    return (
        supabase.table("cost")
        .select("*")
        .eq("user_id", user.id)
        .order("id", desc=True)
        .execute()
        .data
    ) or []


def get_cost_by_id(cost_id):
    try:
        res = (
            supabase.table("cost")
            .select("*")
            .eq("id", cost_id)
            .single()
            .execute()
        )

        row = res.data
        if not row:
            return None

        category_title = ""
        category_id = row.get("id_hazine")

        if category_id:
            cat_res = (
                supabase.table("hazineha")
                .select("title")
                .eq("id", category_id)
                .single()
                .execute()
            )
            cat_row = cat_res.data or {}
            category_title = cat_row.get("title", "")

        row["category_title"] = category_title
        return row

    except Exception as e:
        print("get_cost_by_id error:", e)
        return None


def get_my_cost_by_id(cost_id):
    try:
        user = get_current_user()
        if not user:
            return None

        res = (
            supabase.table("cost")
            .select("""
                *,
                hazineha:id_hazine(title),
                members:member_id(full_name),
                accounts:account_id(account_name, account_type)
            """)
            .eq("id", cost_id)
            .single()
            .execute()
        )

        row = res.data
        if not row:
            return None

        category_title = ""
        category_id = row.get("id_hazine")

        if category_id:
            cat_res = (
                supabase.table("hazineha")
                .select("title")
                .eq("id", category_id)
                .eq("user_id", user.id)
                .single()
                .execute()
            )
            cat_row = cat_res.data or {}
            category_title = cat_row.get("title", "")

        member_name = ""
        member_id = row.get("member_id")

        if member_id:
            member_res = (
                supabase.table("members")
                .select("full_name")
                .eq("id", member_id)
                .eq("user_id", user.id)
                .single()
                .execute()
            )

        member_row = member_res.data or {}
        member_name = member_row.get("full_name", "")

        account_name = ""
        account_type = ""
        account_id = row.get("account_id")

        if account_id:
            acc = find_account_by_id(account_id)
            if acc:
                account_name = acc.get("account_name", "")
                account_type = acc.get("account_type", "")

        row["category_title"] = category_title
        row["member_name"] = member_name
        row["account_name"] = account_name
        row["account_type"] = account_type


        return row

    except Exception as e:
        print("get_my_cost_by_id error:", e)
        return None

def insert_cost(data):
    return supabase.table("cost").insert(data).execute().data[0]


def insert_cost_for_current_user(data):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    payload = dict(data)
    payload["user_id"] = user.id

    result = supabase.table("cost").insert(payload).execute()
    return result.data[0] if result.data else None

def update_cost(cost_id, title, price, date_cost, id_hazine, member_id=None):
    supabase.table("cost").update({
        "price": price,
        "title": title,
        "date_cost": date_cost,
        "id_hazine": id_hazine,
        "member_id": member_id,
    }).eq("id", cost_id).execute()

    row = (
        supabase.table("cost")
        .select("*")
        .eq("id", cost_id)
        .single()
        .execute()
        .data
    )

    cat = (
        supabase.table("hazineha")
        .select("title")
        .eq("id", id_hazine)
        .single()
        .execute()
        .data
    )

    row["category_title"] = cat.get("title", "") if cat else ""
    return row

def update_my_cost(cost_id, title, price, date_cost, id_hazine, member_id=None, account_id=None):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("cost").update({
        "price": price,
        "title": title,
        "date_cost": date_cost,
        "id_hazine": id_hazine,
        "member_id": member_id,
        "account_id": account_id,
    }).eq("id", cost_id).eq("user_id", user.id).execute()

    row = (
        supabase.table("cost")
        .select("*")
        .eq("id", cost_id)
        .eq("user_id", user.id)
        .single()
        .execute()
        .data
    )

    cat = (
        supabase.table("hazineha")
        .select("title")
        .eq("id", id_hazine)
        .eq("user_id", user.id)
        .single()
        .execute()
        .data
    )

    member_name = ""
    if member_id:
        member = (
            supabase.table("members")
            .select("full_name")
            .eq("id", member_id)
            .eq("user_id", user.id)
            .single()
            .execute()
            .data
        )
        member_name = member.get("full_name", "") if member else ""

    row["category_title"] = cat.get("title", "") if cat else ""
    row["member_name"] = member_name

    account_name = ""
    account_type = ""

    if account_id:
        acc = find_account_by_id(account_id)
        if acc:
            account_name = acc.get("account_name", "")
            account_type = acc.get("account_type", "")

    row["account_name"] = account_name
    row["account_type"] = account_type

    return row

def delete_cost(cost_id):
    supabase.table("cost").delete().eq("id", cost_id).execute()


def delete_my_cost(cost_id):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("cost").delete().eq("id", cost_id).eq("user_id", user.id).execute()


def load_costs(start_date, end_date):
    cost_rows = (
        supabase.table("cost")
        .select("*")
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
        .order("id", desc=True)
        .execute()
        .data
    ) or []

    categories = (
        supabase.table("hazineha")
        .select("id,title")
        .execute()
        .data
    ) or []

    category_map = {c["id"]: c["title"] for c in categories}

    for row in cost_rows:
        row["category_title"] = category_map.get(row.get("id_hazine"), "")

    return cost_rows

def load_my_costs_by_date(start_date, end_date):
    user = get_current_user()
    if not user:
        return []

    cost_rows = (
        supabase.table("cost")
        .select("*")
        .eq("user_id", user.id)
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
        .order("id", desc=True)
        .execute()
        .data
    ) or []

    categories = (
        supabase.table("hazineha")
        .select("id,title")
        .eq("user_id", user.id)
        .execute()
        .data
    ) or []

    members = (
        supabase.table("members")
        .select("id,full_name")
        .eq("user_id", user.id)
        .execute()
        .data
    ) or []

    category_map = {c["id"]: c["title"] for c in categories}
    member_map = {m["id"]: m["full_name"] for m in members}

    for row in cost_rows:
        row["category_title"] = category_map.get(row.get("id_hazine"), "")
        row["member_name"] = member_map.get(row.get("member_id"), "")

    return cost_rows

def get_hazine_id(title):
    user = get_current_user()
    if not user:
        return 0

    res = (
        supabase.table("hazineha")
        .select("id")
        .eq("user_id", user.id)
        .eq("title", title)
        .limit(1)
        .execute()
    )
    return res.data[0]["id"] if res.data else 0

# def get_currency_id(currency):
#     res = (
#         supabase.table("currency")
#         .select("id")
#         .eq("currency_type", currency)
#         .execute()
#     )
#     return res.data[0]["id"] if res.data else 1


# --------------َAccounts ----------
def find_account_by_name(account_name):
    if not account_name:
        return None

    user = get_current_user()
    if not user:
        return None

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("user_id", user.id)
        .ilike("account_name", account_name)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def find_account_by_id(account_id):
    if not account_id:
        return None

    user = get_current_user()
    if not user:
        return None

    res = (
        supabase.table("accounts")
        .select("id, account_name, account_type")
        .eq("id", account_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def get_default_account():
    user = get_current_user()
    if not user:
        return None

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("user_id", user.id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def get_accounts():
    user = get_current_user()
    if not user:
        return []

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .order("created_at")
        .execute()
    )

    return res.data or []

def create_account(account_type, account_name, initial_balance, #currency, 
                   is_default):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    if is_default:
        supabase.table("accounts") \
            .update({"is_default": False}) \
            .eq("user_id", user.id) \
            .execute()

    keywords = generate_account_keywords(account_type, account_name)

    payload = {
        "user_id": user.id,
        "account_type": account_type,
        "account_name": account_name,
        "keywords": keywords,
        "initial_balance": initial_balance,
        # "currency": currency,
        "is_default": is_default,
        "is_active": True,
    }

    res = supabase.table("accounts").insert(payload).execute()
    return res.data[0] if res.data else None

def update_account(account_id, account_type, account_name, initial_balance,# currency,
                    is_default):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    if is_default:
        supabase.table("accounts") \
            .update({"is_default": False}) \
            .eq("user_id", user.id) \
            .execute()

    keywords = generate_account_keywords(account_type, account_name)

    payload = {
        "account_type": account_type,
        "account_name": account_name,
        "keywords": keywords,
        "initial_balance": initial_balance,
        # "currency": currency,
        "is_default": is_default,
    }

    res = (
        supabase.table("accounts")
        .update(payload)
        .eq("id", account_id)
        .eq("user_id", user.id)
        .execute()
    )

    return res.data[0] if res.data else None

def delete_account(account_id):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("accounts") \
        .update({"is_active": False}) \
        .eq("id", account_id) \
        .eq("user_id", user.id) \
        .execute()
    
def generate_account_keywords(account_type, account_name):
    base = {
        "bank": ["bank", "card", "debit", "atm"],
        "cash": ["cash", "money", "wallet"],
        "credit": ["credit", "visa", "mastercard"],
        "savings": ["saving"],
        "wallet": ["wallet"],
        "custom": []
    }

    name = (account_name or "").lower().strip()

    keywords = []
    if name:
        keywords.append(name)
        keywords.extend(name.split())

    keywords.extend(base.get(account_type, []))

    return list(dict.fromkeys(keywords))


# --------------َAccounts ----------
# --------------transaction------------

def create_transaction(
    type,
    title,
    amount,
    transaction_date,
    account_id,
    is_template=False,
    repeat_type="none",
    repeat_day=None,
    is_active=True,
):
    user = get_current_user()
    if not user:
        raise Exception("User not logged in")

    payload = {
        "user_id": user.id,
        "type": type,
        "title": title,
        "amount": amount,
        "transaction_date": transaction_date,
        "account_id": account_id,
        "is_template": bool(is_template),
        "repeat_type": repeat_type,
        "repeat_day": repeat_day,
        "is_auto_created": False,
        "is_active": bool(is_active),
    }

    res = supabase.table("transactions").insert(payload).execute()
    return res.data[0] if res.data else None


def get_transactions(type=None):
    user = get_current_user()
    if not user:
        return []

    q = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user.id)
        .eq("is_active", True)
    )

    if type:
        q = q.eq("type", type)

    res = q.order("transaction_date", desc=True).execute()
    return res.data or []


def update_transaction(
    tx_id,
    title,
    amount,
    transaction_date,
    account_id,
    is_template=False,
    repeat_type="none",
    repeat_day=None,
    is_active=True,
):
    user = get_current_user()
    if not user:
        raise Exception("User not logged in")

    payload = {
        "title": title,
        "amount": amount,
        "transaction_date": transaction_date,
        "account_id": account_id,
        "is_template": bool(is_template),
        "repeat_type": repeat_type,
        "repeat_day": repeat_day,
        "is_active": bool(is_active),
    }

    res = (
        supabase.table("transactions")
        .update(payload)
        .eq("id", tx_id)
        .eq("user_id", user.id)
        .execute()
    )

    return res.data[0] if res.data else None





# ================= INCOME TRANSACTIONS =================

def get_income_transactions_by_month(year_month):
    user = get_current_user()
    if not user:
        return []

    res = (
        supabase.table("income_transactions")
        .select("*")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .eq("year_month", year_month)
        .order("transaction_date", desc=True)
        .execute()
    )
    return res.data or []

def create_income_transaction(
    title,
    amount,
    transaction_date,
    account_id,
    income_type="one_time",
    status="confirmed",
    note=None,
):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    year_month = transaction_date[:7]

    payload = {
        "user_id": user.id,
        "title": title,
        "amount": amount,
        "transaction_date": transaction_date,
        "account_id": account_id,
        "income_type": income_type,   # ✅ اضافه شد
        "status": status,
        "year_month": year_month,
        "note": note,
        "is_active": True,
    }

    res = supabase.table("income_transactions").insert(payload).execute()
    return res.data[0] if res.data else None

def update_income_transaction(
    tx_id,
    title,
    amount,
    transaction_date,
    account_id,
    income_type="one_time",
    status="confirmed",
    note=None,
):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    year_month = transaction_date[:7]

    payload = {
        "title": title,
        "amount": amount,
        "transaction_date": transaction_date,
        "account_id": account_id,
        "income_type": income_type,   # ✅ اضافه شد
        "status": status,
        "year_month": year_month,
        "note": note,
    }

    res = (
        supabase.table("income_transactions")
        .update(payload)
        .eq("id", tx_id)
        .eq("user_id", user.id)
        .execute()
    )
    return res.data[0] if res.data else None


def delete_income_transaction(tx_id):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("income_transactions") \
        .update({"is_active": False}) \
        .eq("id", tx_id) \
        .eq("user_id", user.id) \
        .execute()


# --------------transaction------------
def get_financial_summary(start_date, end_date):
    user = get_current_user()
    if not user:
        return {
            "balance": 0,
            "income": 0,
            "expense": 0,
            "left": 0,
        }

    accounts = (
        supabase.table("accounts")
        .select("initial_balance")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .execute()
        .data
    ) or []

    initial_balance = sum(
        float(a.get("initial_balance") or 0)
        for a in accounts
    )

    # ✅ درآمد از جدول جدید income_transactions
    income_rows = (
        supabase.table("income_transactions")
        .select("amount")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .eq("status", "confirmed")
        .gte("transaction_date", start_date)
        .lte("transaction_date", end_date)
        .execute()
        .data
    ) or []

    income = sum(
        float(r.get("amount") or 0)
        for r in income_rows
    )



    today = today_local()
    start_month = today.replace(day=1)

    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)

    cost_rows = (
        supabase.table("cost")
        .select("price")
        .eq("user_id", user.id)
        .gte("date_cost", start_month.isoformat())
        .lt("date_cost", next_month.isoformat())   # 👈 بهتر از lte
        .execute()
        .data
    ) or []

    expense = sum(
        float(r.get("price") or 0)
        for r in cost_rows
    )

    balance = initial_balance + income - expense
    left = income - expense

    return {
        "balance": balance,
        "income": income,
        "expense": expense,
        "left": left,
    }




def carry_monthly_income_to_current_month():
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    today = today_local()
    current_ym = today.strftime("%Y-%m")
    today_iso = today.isoformat()

    monthly_rows = (
        supabase.table("income_transactions")
        .select("*")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .eq("income_type", "monthly")
        .neq("status", "cancelled")
        .eq("carried_forward", False)
        .execute()
        .data
    ) or []

    created = []

    for row in monthly_rows:
        # جلوگیری از duplicate برای ماه جاری
        exists = (
            supabase.table("income_transactions")
            .select("id")
            .eq("user_id", user.id)
            .eq("income_type", "monthly")
            .eq("year_month", current_ym)
            .eq("title", row.get("title"))
            .eq("account_id", row.get("account_id"))
            .limit(1)
            .execute()
            .data
        ) or []

        if exists:
            continue

        payload = {
            "user_id": user.id,
            "title": row.get("title"),
            "amount": row.get("amount"),
            "transaction_date": today_iso,
            "account_id": row.get("account_id"),
            "income_type": "monthly",
            "status": "pending",
            "year_month": current_ym,
            "note": row.get("note"),
            "is_active": True,
            "carried_forward": False,  # رکورد جدید هنوز برای ماه بعد منتقل نشده
        }

        res = supabase.table("income_transactions").insert(payload).execute()

        if res.data:
            created.append(res.data[0])

            # رکورد قبلی تیک بخورد که منتقل شده
            supabase.table("income_transactions").update({
                "carried_forward": True,
            }).eq("id", row["id"]).eq("user_id", user.id).execute()

    return created

# ---------- Budget --------------
# ================= BUDGETS =================

def get_month_start(date_text: str):
    # input: "2026-04-15" or "2026-04"
    if len(date_text) == 7:
        return f"{date_text}-01"
    return date_text[:7] + "-01"


def get_budgets_by_month(year_month: str):
    user = get_current_user()
    if not user:
        return []

    period_start = get_month_start(year_month)

    res = (
        supabase.table("budgets")
        .select("*")
        .eq("user_id", user.id)
        .eq("period_start", period_start)
        .order("created_at")
        .execute()
    )

    return res.data or []


def get_budget_page_data(year_month: str):
    """
    برای صفحه بودجه:
    - categories از hazineha
    - budgets از budgets
    - spent از cost
    """

    user = get_current_user()
    print("BUDGET USER:", user)    
    if not user:
        return {
            "categories": [],
            "budgets": [],
            "costs": [],
        }

    period_start = get_month_start(year_month)

    year = int(period_start[:4])
    month = int(period_start[5:7])

    start_date = date(year, month, 1)

    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    
    categories = load_active_hazineha()

    budgets = (
        supabase.table("budgets")
        .select("*")
        .eq("user_id", user.id)
        .eq("period_start", period_start)
        .execute()
        .data
    ) or []

    costs = (
        supabase.table("cost")
        .select("id, price, id_hazine, date_cost")
        .eq("user_id", user.id)
        .gte("date_cost", start_date.isoformat())
        .lt("date_cost", end_date.isoformat())
        .execute()
        .data
    ) or []

    return {
        "categories": categories,
        "budgets": budgets,
        "costs": costs,
    }


def get_descendant_category_ids(categories, category_id):
    result = [category_id]

    children = [
        c for c in categories
        if c.get("id_parent") == category_id
    ]

    for child in children:
        result.extend(
            get_descendant_category_ids(categories, child["id"])
        )

    return result


def get_ancestor_category_ids(categories, category_id):
    result = []

    current = next(
        (c for c in categories if c.get("id") == category_id),
        None
    )

    while current and current.get("id_parent"):
        parent_id = current.get("id_parent")
        result.append(parent_id)

        current = next(
            (c for c in categories if c.get("id") == parent_id),
            None
        )

    return result


def has_budget_conflict(category_id, year_month: str):
    """
    جلوگیری از این حالت:
    مسکن budget داشته باشد
    و تعمیرات هم budget جدا داشته باشد
    """

    categories = load_active_hazineha()
    budgets = get_budgets_by_month(year_month)

    budget_category_ids = {
        b.get("category_id")
        for b in budgets
        if b.get("category_id")
    }

    ancestor_ids = set(
        get_ancestor_category_ids(categories, category_id)
    )

    descendant_ids = set(
        get_descendant_category_ids(categories, category_id)
    )
    descendant_ids.discard(category_id)

    conflict_ids = ancestor_ids.union(descendant_ids)

    for cid in conflict_ids:
        if cid in budget_category_ids:
            return True

    return False


def upsert_budget(category_id, amount, year_month: str):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    period_start = get_month_start(year_month)

    if has_budget_conflict(category_id, year_month):
        raise Exception("Budget conflict: parent or child already has budget")

    payload = {
        "user_id": user.id,
        "category_id": category_id,
        "amount": float(amount),
        "period_type": "monthly",
        "period_start": period_start,
    }

    res = (
        supabase.table("budgets")
        .upsert(
            payload,
            on_conflict="user_id,category_id,period_start"
        )
        .execute()
    )

    return res.data[0] if res.data else None


def delete_budget(category_id, year_month: str):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    period_start = get_month_start(year_month)

    supabase.table("budgets") \
        .delete() \
        .eq("user_id", user.id) \
        .eq("category_id", category_id) \
        .eq("period_start", period_start) \
        .execute()


def calculate_budget_spent(categories, costs, category_id):
    category_ids = get_descendant_category_ids(categories, category_id)

    total = 0

    for row in costs:
        if row.get("id_hazine") in category_ids:
            total += float(row.get("price") or 0)

    return total

def carry_budgets_to_current_month():
    user = get_current_user()
    if not user:
        return []


    today = today_local()
    current_ym = today.strftime("%Y-%m")
    current_start = f"{current_ym}-01"

    # ماه قبل
    if today.month == 1:
        prev_year = today.year - 1
        prev_month = 12
    else:
        prev_year = today.year
        prev_month = today.month - 1

    prev_ym = f"{prev_year}-{prev_month:02d}"
    prev_start = f"{prev_ym}-01"

    # گرفتن بودجه‌های ماه قبل
    prev_budgets = (
        supabase.table("budgets")
        .select("*")
        .eq("user_id", user.id)
        .eq("period_start", prev_start)
        .eq("carried_forward", False)
        .execute()
        .data
    ) or []

    created = []

    for row in prev_budgets:
        # جلوگیری از duplicate
        exists = (
            supabase.table("budgets")
            .select("id")
            .eq("user_id", user.id)
            .eq("category_id", row["category_id"])
            .eq("period_start", current_start)
            .limit(1)
            .execute()
            .data
        ) or []

        if exists:
            continue

        payload = {
            "user_id": user.id,
            "category_id": row["category_id"],
            "amount": row["amount"],
            "period_type": "monthly",
            "period_start": current_start,
            "carried_forward": False,
        }

        res = supabase.table("budgets").insert(payload).execute()

        if res.data:
            created.append(res.data[0])

            # تیک بزن که منتقل شده
            supabase.table("budgets").update({
                "carried_forward": True
            }).eq("id", row["id"]).eq("user_id", user.id).execute()

    return created

#  ---------- dashboard -----------



def get_current_month_dashboard_data(year_month=None):
    user = get_current_user()
    if not user:
        return None

    today = today_local()

    if not year_month:
        year_month = today.strftime("%Y-%m")

    year = int(year_month[:4])
    month = int(year_month[5:7])

    start_date = date(year, month, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    end_date = date(year, month, days_in_month)

    if year == today.year and month == today.month:
        days_passed = today.day
    else:
        days_passed = days_in_month

    # ---------- Income ----------
    income_rows = (
        supabase.table("income_transactions")
        .select("amount")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .eq("status", "confirmed")
        .eq("year_month", year_month)
        .execute()
        .data
    ) or []

    total_income = sum(float(r.get("amount") or 0) for r in income_rows)

    # ---------- Costs ----------
    cost_rows = (
        supabase.table("cost")
        .select("id,title,price,date_cost,id_hazine")
        .eq("user_id", user.id)
        .gte("date_cost", start_date.isoformat())
        .lte("date_cost", end_date.isoformat())
        .execute()
        .data
    ) or []

    total_expense = sum(float(r.get("price") or 0) for r in cost_rows)
    balance = total_income - total_expense

    # ---------- Previous month ----------
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    prev_ym = f"{prev_year}-{prev_month:02d}"
    prev_start = date(prev_year, prev_month, 1)
    prev_days = calendar.monthrange(prev_year, prev_month)[1]
    prev_end = date(prev_year, prev_month, prev_days)

    prev_cost_rows = (
        supabase.table("cost")
        .select("price")
        .eq("user_id", user.id)
        .gte("date_cost", prev_start.isoformat())
        .lte("date_cost", prev_end.isoformat())
        .execute()
        .data
    ) or []

    previous_expense = sum(float(r.get("price") or 0) for r in prev_cost_rows)
    expense_vs_last_month = total_expense - previous_expense

    # ---------- Budget ----------
    budget_data = get_budget_page_data(year_month)
    categories = budget_data["categories"]
    budgets = budget_data["budgets"]
    costs_for_budget = budget_data["costs"]

    budget_total = sum(float(b.get("amount") or 0) for b in budgets)

    budget_used_percent = (
        total_expense / budget_total
        if budget_total > 0
        else 0
    )

    income_used_percent = (
        total_expense / total_income
        if total_income > 0
        else 0
    )

    # ---------- Category spending ----------
    category_map = {
        c["id"]: c.get("title") or ""
        for c in categories
    }

    category_spending = defaultdict(float)

    for row in cost_rows:
        category_id = row.get("id_hazine")
        if category_id:
            category_spending[category_id] += float(row.get("price") or 0)

    # ---------- Over budget ----------
    over_budget_items = []

    for b in budgets:
        category_id = b.get("category_id")
        amount = float(b.get("amount") or 0)
        spent = calculate_budget_spent(
            categories,
            costs_for_budget,
            category_id,
        )

        if amount > 0 and spent > amount:
            over_budget_items.append({
                "category_id": category_id,
                "category": category_map.get(category_id, "Unknown"),
                "budget": amount,
                "spent": spent,
                "over_amount": spent - amount,
            })

    over_budget_items.sort(
        key=lambda x: x["over_amount"],
        reverse=True,
    )

    # ---------- Biggest expense ----------
    biggest_expense = None
    if cost_rows:
        biggest_row = max(
            cost_rows,
            key=lambda r: float(r.get("price") or 0)
        )
        biggest_expense = {
            "title": biggest_row.get("title") or "",
            "amount": float(biggest_row.get("price") or 0),
            "category": category_map.get(biggest_row.get("id_hazine"), ""),
        }

    # ---------- Forecast ----------
    avg_daily_spending = (
        total_expense / days_passed
        if days_passed > 0
        else 0
    )

    projected_end_month_expense = avg_daily_spending * days_in_month

    # ---------- Quick insights ----------
    insights = []

    if over_budget_items:
        item = over_budget_items[0]
        insights.append(
            f"⚠️ {item['category']} +{item['over_amount']:,.0f} over budget"
        )

    if expense_vs_last_month > 0:
        insights.append(
            f"📈 +{expense_vs_last_month:,.0f} vs last month"
        )
    elif expense_vs_last_month < 0:
        insights.append(
            f"📉 {abs(expense_vs_last_month):,.0f} less than last month"
        )

    if biggest_expense:
        insights.append(
            f"💸 {biggest_expense['title']} = biggest expense"
        )

    return {
        "month": year_month,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,

        "budget_total": budget_total,
        "budget_used_percent": budget_used_percent,
        "income_used_percent": income_used_percent,

        "days_passed": days_passed,
        "days_in_month": days_in_month,

        "avg_daily_spending": avg_daily_spending,
        "projected_end_month_expense": projected_end_month_expense,

        "previous_month": prev_ym,
        "previous_expense": previous_expense,
        "expense_vs_last_month": expense_vs_last_month,

        "over_budget_categories": over_budget_items[:3],
        "biggest_expense": biggest_expense,
        "insights": insights[:3],
    }
