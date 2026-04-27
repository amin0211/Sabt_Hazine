from supabase import create_client
import os
import json
from dotenv import load_dotenv
from functools import lru_cache
from datetime import datetime

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
        .select("id, email, username, name, family, birthdate, language_id")
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
        .select("id, username, name, family, birthdate, language_id, languages(code, name, is_rtl)")
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

    
def copy_hazineha_template_for_user(user_id: str):
    try:
        if not user_id:
            raise Exception("user_id is required")

        # اگر قبلاً ساخته شده، خروج
        existing = (
            supabase.table("hazineha")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return True

        # گرفتن زبان کاربر
        profile = (
            supabase.table("profiles")
            .select("language_id")
            .eq("id", user_id)
            .single()
            .execute()
            .data
        )
        language_id = profile.get("language_id") if profile else None

        # گرفتن template ها
        template_rows = (
            supabase.table("hazineha_template")
            .select("id,id_parent,title,keywords,embedding_text,is_active")
            .order("id")
            .execute()
            .data
        ) or []

        if not template_rows:
            return True

        # گرفتن ترجمه‌ها
        dic_rows = []
        if language_id:
            dic_rows = (
                supabase.table("hazineha_dic")
                .select("hazine_id,title")
                .eq("language_id", language_id)
                .execute()
                .data
            ) or []

        # ساخت map ترجمه
        dic_map = {row["hazine_id"]: row["title"] for row in dic_rows}

        template_to_new_id = {}

        # مرحله 1: insert بدون parent
        for row in template_rows:
            translated_title = dic_map.get(row["id"]) or row.get("title") or ""

            payload = {
                "user_id": user_id,
                "id_parent": None,
                "title": translated_title,
                "template_id": row.get("id"),
                "keywords": row.get("keywords") if isinstance(row.get("keywords"), list) else [],
                "embedding_text": row.get("embedding_text") or "",
                "is_active": bool(row.get("is_active", True)),
            }

            inserted = supabase.table("hazineha").insert(payload).execute().data
            if not inserted:
                raise Exception(f"Failed to copy template row {row.get('id')}")

            new_row = inserted[0]
            template_to_new_id[row["id"]] = new_row["id"]

        # مرحله 2: تنظیم parent
        for row in template_rows:
            old_parent_id = row.get("id_parent")
            if old_parent_id is None:
                continue

            new_child_id = template_to_new_id.get(row["id"])
            new_parent_id = template_to_new_id.get(old_parent_id)

            if new_child_id and new_parent_id:
                supabase.table("hazineha").update({
                    "id_parent": new_parent_id
                }).eq("id", new_child_id).eq("user_id", user_id).execute()

        clear_hazineha_cache()
        return True

    except Exception as e:
        print(f"copy_hazineha_template_for_user error: {e}")
        raise


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
def load_active_hazineha():
    try:
        rows = load_all_hazineha()
        return [row for row in rows if row.get("is_active", True)]
    except Exception as e:
        print(f"load_active_hazineha error: {e}")
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
        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at")
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
        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at,embedding_text,embedding")
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


def upsert_category_learning(raw_text, normalized_text, category_id, source="user_confirmed", confidence=None, embedding_text=None):
    try:
        existing = (
            supabase.table("category_learning")
            .select("id,use_count")
            .eq("normalized_text", normalized_text)
            .eq("category_id", category_id)
            .limit(1)
            .execute()
        )

        rows = existing.data or []

        if rows:
            row_id = rows[0]["id"]
            current_count = rows[0].get("use_count", 1) or 1

            payload = {
                "raw_text": raw_text,
                "source": source,
                "confidence": confidence,
                "use_count": current_count + 1,
                "last_used_at": datetime.utcnow().isoformat(),
            }

            if embedding_text is not None:
                payload["embedding_text"] = embedding_text

            result = (
                supabase.table("category_learning")
                .update(payload)
                .eq("id", row_id)
                .execute()
            )

            return result.data[0] if result.data else None

        payload = {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "category_id": category_id,
            "source": source,
            "confidence": confidence,
            "use_count": 1,
            "last_used_at": datetime.utcnow().isoformat(),
            "embedding_text": embedding_text or normalized_text,
        }

        result = supabase.table("category_learning").insert(payload).execute()
        return result.data[0] if result.data else None

    except Exception as e:
        print(f"upsert_category_learning error: {e}")
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
        res = (
            supabase.table("category_learning")
            .select("id, raw_text, normalized_text, category_id, hazineha(title)")
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
            .select("*")
            .eq("id", cost_id)
            .eq("user_id", user.id)
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

        row["category_title"] = category_title
        row["member_name"] = member_name

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

def update_my_cost(cost_id, title, price, date_cost, id_hazine, member_id=None):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    supabase.table("cost").update({
        "price": price,
        "title": title,
        "date_cost": date_cost,
        "id_hazine": id_hazine,
        "member_id": member_id,
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

def get_currency_id(currency):
    res = (
        supabase.table("currency")
        .select("id")
        .eq("currency_type", currency)
        .execute()
    )
    return res.data[0]["id"] if res.data else 1