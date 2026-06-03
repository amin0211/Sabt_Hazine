from supabase import create_client
import os
import json
from dotenv import load_dotenv
from functools import lru_cache
import calendar
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from services.utils import today_local, safe_picker_date



load_dotenv()

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY is not set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --------------WorkSpace ------------------
def load_my_costs_by_date(page, start_date, end_date):

    workspace_id = get_current_workspace_id(page)

    q = (
        supabase.table("cost")
        .select("id,title,price,date_cost,id_hazine,member_id,account_id,temp_hazine")
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
        .order("id", desc=True)
    )

    if workspace_id:
        q = q.eq("workspace_id", workspace_id)

    res = q.execute()
    rows = res.data or []

    # ---------- Category map ----------
    category_ids = list({
        r.get("id_hazine")
        for r in rows
        if r.get("id_hazine")
    })

    category_map = {}

    if category_ids:
        cat_res = (
            supabase.table("hazineha")
            .select("id,title")
            .in_("id", category_ids)
            .execute()
        )

        category_map = {
            c["id"]: c.get("title") or ""
            for c in (cat_res.data or [])
        }

    # ---------- Member map ----------
    member_ids = list({
        r.get("member_id")
        for r in rows
        if r.get("member_id")
    })

    member_map = {}

    if member_ids:
        member_res = (
            supabase.table("members")
            .select("id,full_name")
            .in_("id", member_ids)
            .execute()
        )

        member_map = {
            m["id"]: m.get("full_name") or ""
            for m in (member_res.data or [])
        }

    # ---------- Account map, optional ----------
    account_ids = list({
        r.get("account_id")
        for r in rows
        if r.get("account_id")
    })

    account_map = {}

    if account_ids:
        acc_res = (
            supabase.table("accounts")
            .select("id,account_name,account_type")
            .in_("id", account_ids)
            .execute()
        )

        account_map = {
            a["id"]: a
            for a in (acc_res.data or [])
        }

    for r in rows:
        r["category_title"] = category_map.get(r.get("id_hazine"), "")
        r["member_name"] = member_map.get(r.get("member_id"), "")

        acc = account_map.get(r.get("account_id")) or {}
        r["account_name"] = acc.get("account_name", "")
        r["account_type"] = acc.get("account_type", "")

    return rows

    workspace_id = get_current_workspace_id(page)

    q = (
        supabase.table("cost")
        .select("*")
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
        .order("id", desc=True)
    )

    if workspace_id:
        q = q.eq("workspace_id", workspace_id)

    res = q.execute()
    rows = res.data or []

    # ✅ اضافه کردن category_title
    category_ids = list({
        r.get("id_hazine")
        for r in rows
        if r.get("id_hazine")
    })

    category_map = {}

    if category_ids:
        cat_res = (
            supabase.table("hazineha")
            .select("id,title")
            .in_("id", category_ids)
            .execute()
        )

        category_map = {
            c["id"]: c["title"]
            for c in (cat_res.data or [])
        }

    for r in rows:
        r["category_title"] = category_map.get(r.get("id_hazine"), "")

    return rows

def add_user_to_workspace(workspace_id, email, role="member"):
    profile_res = (
        supabase.table("profiles")
        .select("id, email")
        .eq("email", email)
        .maybe_single()
        .execute()
    )

    if not profile_res.data:
        return {
            "success": False,
            "message": "User not found. They need to register first."
        }

    user_id = profile_res.data["id"]

    supabase.table("workspace_members").upsert({
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role": role,
        "is_active": True,
    }, on_conflict="workspace_id,user_id").execute()

    return {
        "success": True,
        "message": "User added successfully."
    }

def create_workspace(title, is_active=True, description=None):
    user = get_current_user()
    if not user:
        return None

    res = supabase.table("workspaces").insert({
        "title": title,
        "description": description,
        "owner_user_id": user.id,
        "is_active": is_active,
    }).execute()

    workspace = res.data[0]
    workspace_id = workspace["id"]

    root_hazine_id = None

    try:
        root_res = supabase.table("hazineha").insert({
            "user_id": user.id,
            "workspace_id": workspace_id,
            "title": title,
            "id_parent": None,
            "keywords": [],
            "embedding_text": "",
            "is_active": True,
            "template_id": None,
        }).execute()

        root_row = root_res.data[0] if root_res.data else None
        root_hazine_id = root_row.get("id") if root_row else None

        if root_hazine_id:
            supabase.table("workspaces").update({
                "root_hazine_id": root_hazine_id
            }).eq("id", workspace_id).execute()

            workspace["root_hazine_id"] = root_hazine_id

    except Exception as ex:
        print("create root hazineha error:", ex)

    create_default_account_for_user(user.id, workspace_id)

    return workspace


def get_my_workspaces():
    user = get_current_user()

    print("========== GET MY WORKSPACES DEBUG ==========", flush=True)
    print("[WORKSPACES] current user:", user.id if user else None, flush=True)

    if not user:
        print("[WORKSPACES] ERROR: no authenticated user", flush=True)
        print("============================================", flush=True)
        return []

    user_id = user.id

    owned = []
    shared = []

    # 1) Workspace هایی که خود کاربر owner است
    try:
        owned_res = (
            supabase.table("workspaces")
            .select("id, title, owner_user_id, is_active, root_hazine_id")
            .eq("owner_user_id", user_id)
            .eq("is_active", True)
            .execute()
        )

        owned = owned_res.data or []

        print("[WORKSPACES] owned count:", len(owned), flush=True)
        print("[WORKSPACES] owned rows:", owned, flush=True)

        for w in owned:
            w["access_type"] = "owner"
            w["shared_by_name"] = None
            w["shared_by_email"] = None
            w["shared_count"] = 0

    except Exception as ex:
        print("[WORKSPACES] owned query error:", repr(ex), flush=True)
        owned = []

    # 2) Workspace هایی که با کاربر share شده
    # بدون join با profiles، چون RLS روی profiles ممکن است join را خالی کند
    try:
        shared_res = (
            supabase.table("workspace_members")
            .select("workspace_id, role, invited_by")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )

        shared_rows = shared_res.data or []

        print("[WORKSPACES] shared membership count:", len(shared_rows), flush=True)
        print("[WORKSPACES] shared membership rows:", shared_rows, flush=True)

        for row in shared_rows:
            workspace_id = row.get("workspace_id")

            if not workspace_id:
                continue

            try:
                workspace_res = (
                    supabase.table("workspaces")
                    .select("id, title, owner_user_id, is_active, root_hazine_id")
                    .eq("id", workspace_id)
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

                workspace_rows = workspace_res.data or []

                if not workspace_rows:
                    continue

                workspace = workspace_rows[0]

                shared.append({
                    "id": workspace.get("id"),
                    "title": workspace.get("title"),
                    "owner_user_id": workspace.get("owner_user_id"),
                    "root_hazine_id": workspace.get("root_hazine_id"),
                    "is_active": workspace.get("is_active", True),
                    "access_type": "shared",
                    "role": row.get("role"),
                    "shared_by_name": "Shared workspace",
                    "shared_by_email": None,
                    "shared_count": 0,
                })

            except Exception as ex:
                print("[WORKSPACES] shared workspace read error:", repr(ex), flush=True)

    except Exception as ex:
        print("[WORKSPACES] shared query error:", repr(ex), flush=True)
        shared = []

    result = owned + shared

    print("[WORKSPACES] total result count:", len(result), flush=True)
    print("[WORKSPACES] total result:", result, flush=True)
    print("============================================", flush=True)

    return result


def update_workspace(workspace_id, title, is_active=True):
    res = (
        supabase.table("workspaces")
        .update({
            "title": title,
            "is_active": is_active,
        })
        .eq("id", workspace_id)
        .execute()
    )

    return res.data


def delete_workspace(workspace_id):
    res = (
        supabase.table("workspaces")
        .update({"is_active": False})
        .eq("id", workspace_id)
        .execute()
    )

    return res.data


def get_workspace_shared_users(workspace_id):
    user = get_current_user()
    if not user:
        return []

    # workspace_id = get_current_workspace_id()

    try:
        members_res = (
            supabase.table("workspace_members")
            .select("user_id, role")
            .eq("workspace_id", workspace_id)
            .eq("is_active", True)
            .neq("user_id", user.id)
            .execute()
        )
    except Exception as ex:
        print("GET WORKSPACE MEMBERS ERROR:", ex)
        return []

    members = members_res.data if members_res and members_res.data else []

    rows = []

    for item in members:
        member_user_id = item.get("user_id")

        try:
            profile_res = (
                supabase.table("profiles")
                .select("id, email, name, family")
                .eq("id", member_user_id)
                .limit(1)
                .execute()
            )

            profiles = profile_res.data if profile_res and profile_res.data else []
            profile = profiles[0] if profiles else {}

        except Exception as ex:
            print("GET SHARED USER PROFILE ERROR:", ex)
            profile = {}

        display_name = " ".join(
            [
                profile.get("name") or "",
                profile.get("family") or "",
            ]
        ).strip()

        rows.append(
            {
                "user_id": member_user_id,
                "email": profile.get("email") or "",
                # "username": profile.get("username") or "",
                "display_name": display_name,
                "role": item.get("role"),
            }
        )

    return rows


def remove_workspace_share(workspace_id, user_id):
    res = (
        supabase.table("workspace_members")
        .update({"is_active": False})
        .eq("workspace_id", workspace_id)
        .eq("user_id", user_id)
        .execute()
    )

    return res.data

def share_workspace_by_email(workspace_id, email):
    email = (email or "").strip().lower()

    if not email:
        return {
            "success": False,
            "message": "Email is required.",
        }

    current_user = get_current_user()
    if not current_user:
        return {
            "success": False,
            "message": "User is not logged in.",
        }

    try:
        profile_res = (
            supabase.table("profiles")
            .select("id, email")
            .eq("email", email)
            .limit(1)
            .execute()
        )
            
    except Exception as ex:
        print("SHARE PROFILE SEARCH ERROR:", ex)
        return {
            "success": False,
            "message": "Could not search user profile.",
        }

    profiles = profile_res.data if profile_res and profile_res.data else []

    if not profiles:
        return {
            "success": False,
            "message": "User not found. They need to register first.",
        }

    user_id = profiles[0]["id"]

    if user_id == current_user.id:
        return {
            "success": False,
            "message": "You cannot share a workspace with yourself.",
        }

    try:
        supabase.table("workspace_members").upsert(
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": "member",
                "is_active": True,
                "invited_by": current_user.id,
            },
            on_conflict="workspace_id,user_id",
        ).execute()

    except Exception as ex:
        print("SHARE WORKSPACE ERROR:", ex)
        return {
            "success": False,
            "message": "Could not share workspace.",
        }

    return {
        "success": True,
        "message": "Workspace shared successfully.",
    }


def set_current_workspace(workspace_id):
    user = get_current_user()
    if not user:
        return False

    res = (
        supabase.table("profiles")
        .update({"current_workspace_id": workspace_id})
        .eq("id", user.id)
        .execute()
    )

    return bool(res.data)

# -------------- workspace ----------------


def get_languages():
    res = supabase.table("languages").select("*").order("id").execute()
    return res.data or []

def get_my_profile_with_language():
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    try:
        res = (
            supabase.table("profiles")
            .select("""
                id,
                name,
                family,
                birthdate,
                language_id,
                timezone,
                current_workspace_id,
                is_active,
                status,
                deleted_at,
                deletion_requested_at,
                languages(code, name, is_rtl),
                workspaces:current_workspace_id (
                    id,
                    title,
                    root_hazine_id
                )
            """)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        return res.data if res and res.data else None

    except Exception as ex:
        print("GET MY PROFILE WITH LANGUAGE ERROR:", ex)
        return None
    

def get_my_profile():
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    try:
        res = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        return res.data if res and res.data else None

    except Exception as ex:
        print("GET MY PROFILE ERROR:", ex)
        return None
        
def update_my_profile(data: dict):
    user = supabase.auth.get_user()
    if not user or not user.user:
        return None

    user_id = user.user.id

    payload = dict(data or {})


    res = (
        supabase
        .table("profiles")
        .update(payload)
        .eq("id", user_id)
        .execute()
    )

    return res.data

def update_user_password(new_password: str):
    if not new_password or len(new_password) < 6:
        raise Exception("Password must be at least 6 characters.")

    res = supabase.auth.update_user({
        "password": new_password
    })

    return res

def get_opening_balance_total(page=None):
    workspace_id = get_current_workspace_id(page)

    if not workspace_id:
        return 0

    rows = (
        supabase.table("accounts")
        .select("initial_balance")
        .eq("workspace_id", workspace_id)
        .eq("is_active", True)
        .execute()
        .data
    ) or []

    return sum(float(r.get("initial_balance") or 0) for r in rows)

def get_account_balances():
    user = get_current_user()
    res = supabase.rpc("get_account_balances", {"p_user_id": user.id}).execute()
    return res.data or []

def get_account_transactions(account_id):
    workspace_id = get_current_workspace_id()

    rows = []

    categories = (
        supabase.table("hazineha")
        .select("id,title")
        .eq("workspace_id", workspace_id)
        .execute()
        .data
    ) or []

    members = (
        supabase.table("members")
        .select("id,full_name")
        .eq("workspace_id", workspace_id)
        .execute()
        .data
    ) or []

    category_map = {c["id"]: c.get("title") or "" for c in categories}
    member_map = {m["id"]: m.get("full_name") or "" for m in members}

    costs = (
        supabase.table("cost")
        .select("id,title,price,date_cost,id_hazine,member_id,created_at")
        .eq("workspace_id", workspace_id)
        .eq("account_id", account_id)
        .execute()
        .data
    ) or []

    for c in costs:
        rows.append({
            "date": c.get("date_cost"),
            "created_at": c.get("created_at"),
            "title": c.get("title") or "Expense",
            "amount": -float(c.get("price") or 0),
            "type": "expense",
            "category_id": c.get("id_hazine"),
            "category_title": category_map.get(c.get("id_hazine"), ""),
            "member_id": c.get("member_id"),
            "member_name": member_map.get(c.get("member_id"), ""),
        })

    incomes = (
        supabase.table("income_transactions")
        .select("id,title,amount,transaction_date,status,created_at")
        .eq("workspace_id", workspace_id)
        .eq("account_id", account_id)
        .eq("is_active", True)
        .execute()
        .data
    ) or []

    for i in incomes:
        rows.append({
            "date": i.get("transaction_date"),
            "created_at": i.get("created_at"),
            "title": i.get("title") or "Income",
            "amount": float(i.get("amount") or 0),
            "type": "income",
            "category_id": None,
            "category_title": "",
            "member_id": None,
            "member_name": "",
        })

    transfers_out = (
        supabase.table("transfer_transactions")
        .select("id,amount,transfer_date,note,created_at")
        .eq("workspace_id", workspace_id)
        .eq("from_account_id", account_id)
        .execute()
        .data
    ) or []

    for t in transfers_out:
        rows.append({
            "date": t.get("transfer_date"),
            "created_at": t.get("created_at"),
            "title": t.get("note") or "Transfer Out",
            "amount": -float(t.get("amount") or 0),
            "type": "transfer_out",
            "category_id": None,
            "category_title": "Transfer",
            "member_id": None,
            "member_name": "",
        })

    transfers_in = (
        supabase.table("transfer_transactions")
        .select("id,amount,transfer_date,note,created_at")
        .eq("workspace_id", workspace_id)
        .eq("to_account_id", account_id)
        .execute()
        .data
    ) or []

    for t in transfers_in:
        rows.append({
            "date": t.get("transfer_date"),
            "created_at": t.get("created_at"),
            "title": t.get("note") or "Transfer In",
            "amount": float(t.get("amount") or 0),
            "type": "transfer_in",
            "category_id": None,
            "category_title": "Transfer",
            "member_id": None,
            "member_name": "",
        })

    rows.sort(
        key=lambda x: (
            x.get("date") or "",
            x.get("created_at") or "",
        ),
        reverse=True,
    )

    return rows


def create_transfer(from_account_id, to_account_id, amount, transfer_date, note=None):
    user = get_current_user()
    if not user:
        raise Exception("User not logged in")
    workspace_id = get_current_workspace_id()

    data = {
        "user_id": user.id,
        "workspace_id": workspace_id,
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
    workspace_id = get_current_workspace_id()
    # user = get_current_user()
    # if not user:
    #     return None

    if not member_name or not member_name.strip():
        return None

    name = member_name.strip()

    # اول exact match
    exact = (
        supabase.table("members")
        .select("id, full_name, relation")
        .eq("workspace_id", workspace_id)
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
        .eq("workspace_id", workspace_id)
        .ilike("full_name", f"%{name}%")
        .limit(1)
        .execute()
    )

    return fuzzy.data[0] if fuzzy.data else None

def get_members(page=None):

    workspace_id = get_current_workspace_id(page)
    # user = get_current_user()
    # if not user:
    #     return []

    res = (
        supabase.table("members")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("id")
        .execute()
    )
    return res.data or []


def add_member(full_name, relation=None):

    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()
    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
        "full_name": full_name.strip(),
        "relation": relation.strip() if relation else None,
    }

    res = supabase.table("members").insert(payload).execute()
    return res.data[0] if res.data else None

def update_member(member_id, full_name, relation=None):
    workspace_id = get_current_workspace_id()
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")

    payload = {
        "full_name": full_name.strip(),
        "relation": relation.strip() if relation else None,
    }

    res = (
        supabase.table("members")
        .update(payload)
        .eq("id", member_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None

def delete_member(member_id):
    workspace_id = get_current_workspace_id()    
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")

    supabase.table("members") \
        .delete() \
        .eq("id", member_id) \
        .eq("workspace_id", workspace_id) \
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
    for fn in [
        _load_all_hazineha_for_workspace,
        _load_active_hazineha_for_workspace,
        _load_leaf_hazineha_for_workspace,
    ]:
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()
            
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

def get_current_workspace_id(page=None):
    # 1️⃣ اول از page.data بخون (سریع‌ترین)
    if page and isinstance(page.data, dict):
        ws_id = page.data.get("current_workspace_id")
        if ws_id and str(ws_id) != "None":
            return ws_id

    # 2️⃣ fallback به DB (profile)
    profile = get_my_profile()
    if not profile:
        return None

    ws_id = profile.get("current_workspace_id")

    if not ws_id or str(ws_id) == "None":
        return None

    return ws_id


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
    if not user_id:
        raise Exception("user_id is required")

    payload = dict(data or {})



    result = (
        supabase
        .table("profiles")
        .update(payload)
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        raise Exception("Profile update failed. No profile row was updated.")

    return result.data



def refresh_hazineha_titles_for_user(workspace_id: str, language_id: int):
    try:
        if not workspace_id:
            raise ValueError("workspace_id is required")

        if not language_id:
            raise ValueError("language_id is required")

        res = supabase.rpc(
            "refresh_hazineha_titles_for_workspace",
            {
                "p_workspace_id": workspace_id,
                "p_language_id": int(language_id),
            }
        ).execute()

        clear_hazineha_cache()
        return res.data if res.data is not None else True

    except Exception as e:
        print(f"refresh_hazineha_titles_for_user error: {e}")
        raise

def delete_auth_user(user_id):
    if not user_id:
        return

    supabase_admin.auth.admin.delete_user(user_id)


def get_user_language_code(user_id):
    rows = (
        supabase.table("profiles")
        .select("language_id, languages(code)")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
    ) or []

    if not rows:
        return "fa"

    lang = rows[0].get("languages") or {}
    return lang.get("code") or "fa"


def create_default_account_for_user(user_id: str, workspace_id: str):
    workspace_id = workspace_id or get_current_workspace_id()

    lang_code = get_user_language_code(user_id)

    if lang_code == "en":
        account_name = "Main Account"
    elif lang_code == "fa":
        account_name = "حساب اصلی"

    data = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "account_type": "bank",
        "account_name": account_name,
        "initial_balance": 0,
        "is_default": True,
        "is_active": True,
    }

    return supabase.table("accounts").insert(data).execute()


def create_default_workspace_for_user(user_id):
    if not user_id:
        raise ValueError("user_id is required")

    res = supabase.rpc(
        "create_default_workspace_for_user",
        {
            "p_user_id": user_id,
        }
    ).execute()

    if not res.data:
        raise Exception("Workspace was not created")

    return res.data

def copy_hazineha_template_for_user(user_id, workspace_id, language_id):
    if not user_id:
        raise ValueError("user_id is required")

    if not workspace_id:
        raise ValueError("workspace_id is required")

    if not language_id:
        raise ValueError("language_id is required")

    res = supabase.rpc(
        "copy_hazineha_template_for_user",
        {
            "p_user_id": user_id,
            "p_workspace_id": workspace_id,
            "p_language_id": int(language_id),
        }
    ).execute()

    return res.data
# ================= HAZINEHA / CATEGORY =================
@lru_cache(maxsize=256)
def _load_all_hazineha_for_workspace(workspace_id: str):
    try:
        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id,workspace_id")
            .eq("workspace_id", workspace_id)
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
                "workspace_id": row.get("workspace_id"),
            })

        return cleaned

    except Exception as e:
        print(f"_load_all_hazineha_for_workspace error: {e}")
        return []


def load_all_hazineha(workspace_id=None):
    try:
        workspace_id = workspace_id or get_current_workspace_id()
        if not workspace_id:
            return []

        return _load_all_hazineha_for_workspace(workspace_id)

    except Exception as e:
        print(f"load_all_hazineha error: {e}")
        return []


@lru_cache(maxsize=256)
def _load_active_hazineha_for_workspace(workspace_id: str):
    rows = _load_all_hazineha_for_workspace(workspace_id)
    return [row for row in rows if row.get("is_active", True)]


def load_active_hazineha(workspace_id=None):
    try:
        workspace_id = workspace_id or get_current_workspace_id()
        if not workspace_id:
            return []

        return _load_active_hazineha_for_workspace(workspace_id)

    except Exception as e:
        print(f"load_active_hazineha error: {e}")
        return []


@lru_cache(maxsize=256)
def _load_leaf_hazineha_for_workspace(workspace_id: str):
    rows = _load_active_hazineha_for_workspace(workspace_id)

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

    return selected_rows


def load_leaf_hazineha(workspace_id=None):
    workspace_id = workspace_id or get_current_workspace_id()
    if not workspace_id:
        return []

    return _load_leaf_hazineha_for_workspace(workspace_id)


def get_hazine_by_id(category_id):
    try:
        workspace_id = get_current_workspace_id()
        # user = get_current_user()
        # if not user:
        #     return None

        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id")
            .eq("id", category_id)
            .eq("workspace_id", workspace_id)
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
            "workspace_id": row.get("workspace_id"),
            "template_id": row.get("template_id"),
        }

    except Exception as e:
        print(f"get_hazine_by_id error: {e}")
        return None

def get_hazine_by_title(title):
    try:
        workspace_id = get_current_workspace_id()
        # user = get_current_user()
        # if not user:
        #     return None

        res = (
            supabase.table("hazineha")
            .select("id,id_parent,title,keywords,embedding_text,updated_at,is_active,user_id,template_id")
            .eq("workspace_id", workspace_id)
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
            "workspace_id": row.get("workspace_id"),
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

        workspace_id = get_current_workspace_id()

        payload = {
            "user_id": user.id,
            "workspace_id": workspace_id,
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
        workspace_id = get_current_workspace_id()
        # user = get_current_user()
        # if not user:
        #     raise Exception("User is not logged in")

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
            .eq("workspace_id", workspace_id)
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
        workspace_id = get_current_workspace_id()        
        # user = get_current_user()
        # if not user:
        #     return []

        q = supabase.table("hazineha").select(
            "id,id_parent,title,keywords,embedding_text,embedding,is_active,updated_at,user_id,template_id"
        ).eq("workspace_id", workspace_id)

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
                "workspace_id": row.get("workspace_id"),
                "template_id": row.get("template_id"),
            })

        return cleaned

    except Exception as e:
        print(f"load_hazineha_with_embeddings error: {e}")
        return []
    
# ================= CATEGORY LEARNING =================
def get_learned_category_exact(normalized_text):
    try:

        workspace_id = get_current_workspace_id()        
        # user = get_current_user()
        # if not user:
        #     return None

        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at")
            .eq("workspace_id", workspace_id)
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
        workspace_id = get_current_workspace_id()        
        # user = get_current_user()
        # if not user:
        #     return None

        res = (
            supabase.table("category_learning")
            .select("id,raw_text,normalized_text,category_id,source,confidence,use_count,last_used_at,created_at,updated_at,embedding_text,embedding")
            .eq("workspace_id", workspace_id)
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

    workspace_id = get_current_workspace_id()

    data = {
        "user_id": user_id,
        "workspace_id": workspace_id,
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
        workspace_id = get_current_workspace_id()
        # user = get_current_user()
        # if not user:
        #     return None
        
        res = (
            supabase.table("category_learning")
            .select("id, raw_text, normalized_text, category_id, hazineha(title)")
            .eq("workspace_id", workspace_id)
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


def load_my_costs(workspace_id=None):
    workspace_id = workspace_id or get_current_workspace_id()

    if not workspace_id:
        return []

    return (
        supabase.table("cost")
        .select("*")
        .eq("workspace_id", workspace_id)
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

        # user = get_current_user()
        # if not user:
        #     return None
        workspace_id = get_current_workspace_id()

        row = (
            supabase.table("cost")
            .select("*")
            .eq("id", cost_id)
            .eq("workspace_id", workspace_id)
            .single()
            .execute()
            .data
        )

        if not row:
            return None

        category_title = ""
        category_id = row.get("id_hazine")

        if category_id:
            cat = (
                supabase.table("hazineha")
                .select("title")
                .eq("id", category_id)
                .eq("workspace_id", workspace_id)
                .limit(1)
                .execute()
                .data
            )
            category_title = cat[0].get("title", "") if cat else ""

        member_name = ""
        member_id = row.get("member_id")

        if member_id:
            member = (
                supabase.table("members")
                .select("full_name")
                .eq("id", member_id)
                .eq("workspace_id", workspace_id)
                .limit(1)
                .execute()
                .data
            )
            member_name = member[0].get("full_name", "") if member else ""

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

    workspace_id = data.get("workspace_id") or get_current_workspace_id()

    payload = dict(data)
    payload["user_id"] = user.id
    payload["workspace_id"] = workspace_id

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

    workspace_id = get_current_workspace_id()

    supabase.table("cost").update({
        "price": price,
        "title": title,
        "date_cost": date_cost,
        "id_hazine": id_hazine,
        "member_id": member_id,
        "account_id": account_id,
    }).eq("id", cost_id).eq("workspace_id", workspace_id).execute()

    row = (
        supabase.table("cost")
        .select("*")
        .eq("id", cost_id)
        .eq("workspace_id", workspace_id)
        .single()
        .execute()
        .data
    )

    return row

def delete_cost(cost_id):
    supabase.table("cost").delete().eq("id", cost_id).execute()


def delete_my_cost(cost_id):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        return

    supabase.table("cost") \
        .delete() \
        .eq("id", cost_id) \
        .eq("workspace_id", workspace_id) \
        .execute()

def load_costs(start_date, end_date):

    workspace_id = get_current_workspace_id()
    cost_rows = (
        supabase.table("cost")
        .select("*")
        .eq("workspace_id", workspace_id)
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


def get_hazine_id(title):
    # user = get_current_user()
    # if not user:
    #     return 0

    workspace_id = get_current_workspace_id()
    res = (
        supabase.table("hazineha")
        .select("id")
        .eq("workspace_id", workspace_id)
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

    # user = get_current_user()
    # if not user:
    #     return None
    workspace_id = get_current_workspace_id()

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("workspace_id", workspace_id)
        .ilike("account_name", account_name)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def find_account_by_id(account_id):
    if not account_id:
        return None

    # user = get_current_user()
    # if not user:
    #     return None
    workspace_id = get_current_workspace_id()

    res = (
        supabase.table("accounts")
        .select("id, account_name, account_type")
        .eq("id", account_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def get_default_account():
    # user = get_current_user()
    # if not user:
    #     return None
    workspace_id = get_current_workspace_id()

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )

    return res.data[0] if res.data else None

def get_accounts():
    # user = get_current_user()
    # if not user:
    #     return []
    workspace_id = get_current_workspace_id()

    res = (
        supabase.table("accounts")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("is_active", True)
        .order("created_at")
        .execute()
    )

    return res.data or []

def create_account(account_type, account_name, initial_balance, #currency, 
                   is_default):
    workspace_id = get_current_workspace_id()
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    if is_default:
        supabase.table("accounts") \
            .update({"is_default": False}) \
            .eq("workspace_id", workspace_id) \
            .execute()

    keywords = generate_account_keywords(account_type, account_name)

    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
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
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")
    workspace_id = get_current_workspace_id()

    if is_default:
        supabase.table("accounts") \
            .update({"is_default": False}) \
            .eq("workspace_id", workspace_id) \
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
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None

def delete_account(account_id):
    if not account_id:
        raise Exception("account_id is required")

    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    res = (
        supabase.table("accounts")
        .update({"is_active": False})
        .eq("id", account_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    if not res.data:
        raise Exception("Account was not deleted. No row was updated.")

    return res.data[0]

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
    
    workspace_id = get_current_workspace_id()
    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
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
    # user = get_current_user()
    # if not user:
    #     return []
    workspace_id = get_current_workspace_id()

    q = (
        supabase.table("transactions")
        .select("*")
        .eq("workspace_id", workspace_id)
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
    # user = get_current_user()
    # if not user:
    #     raise Exception("User not logged in")
    workspace_id = get_current_workspace_id()

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
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None





# ================= INCOME TRANSACTIONS =================

def get_income_transactions_by_month(year_month, workspace_id=None, page=None):
    if not workspace_id:
        workspace_id = get_current_workspace_id(page)

    if not workspace_id:
        return []

    res = (
        supabase.table("income_transactions")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("year_month", year_month)
        .eq("is_active", True)
        .order("id", desc=True)
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

    workspace_id = get_current_workspace_id()

    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
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
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()
    
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
        .eq("workspace_id", workspace_id)
        .execute()
    )
    return res.data[0] if res.data else None


def delete_income_transaction(tx_id):
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")
    workspace_id = get_current_workspace_id()

    supabase.table("income_transactions") \
        .delete() \
        .eq("id", tx_id) \
        .eq("workspace_id", workspace_id) \
        .execute()


# --------------transaction------------
def get_financial_summary(start_date, end_date, workspace_id=None, page=None):
    if not workspace_id:
        workspace_id = get_current_workspace_id(page)

    if not workspace_id:
        return {"expense": 0}

    q = (
        supabase.table("cost")
        .select("price")
        .eq("workspace_id", workspace_id)
        .gte("date_cost", start_date)
        .lte("date_cost", end_date)
    )

    res = q.execute()

    expense = sum(float(r.get("price") or 0) for r in (res.data or []))

    return {"expense": expense}

def carry_monthly_income_to_current_month(page=None):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id(page)

    today = today_local(page)
    current_ym = today.strftime("%Y-%m")
    today_iso = today.isoformat()

    monthly_rows = (
        supabase.table("income_transactions")
        .select("*")
        .eq("workspace_id", workspace_id)
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
            .eq("workspace_id", workspace_id)
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
            "workspace_id": workspace_id,
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
            }).eq("id", row["id"]).eq("workspace_id", workspace_id).execute()

    return created

# ---------- Budget --------------
# ================= BUDGETS =================

def get_month_start(date_text: str):
    # input: "2026-04-15" or "2026-04"
    if len(date_text) == 7:
        return f"{date_text}-01"
    return date_text[:7] + "-01"


def get_budgets_by_month(year_month: str):
    # user = get_current_user()
    # if not user:
    #     return []

    workspace_id = get_current_workspace_id()

    period_start = get_month_start(year_month)

    res = (
        supabase.table("budgets")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("period_start", period_start)
        .order("created_at")
        .execute()
    )

    return res.data or []


def get_budget_page_data(year_month: str, page=None):
    """
    برای صفحه بودجه:
    - categories از hazineha
    - budgets از budgets
    - spent از cost
    """

    # user = get_current_user()
    # print("BUDGET USER:", user)    
    # if not user:
    #     return {
    #         "categories": [],
    #         "budgets": [],
    #         "costs": [],
    #     }

    workspace_id = get_current_workspace_id()
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
        .eq("workspace_id", workspace_id)
        .eq("period_start", period_start)
        .execute()
        .data
    ) or []

    costs = (
        supabase.table("cost")
        .select("id, price, id_hazine, date_cost")
        .eq("workspace_id", workspace_id)
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

    workspace_id = get_current_workspace_id()

    period_start = get_month_start(year_month)

    if has_budget_conflict(category_id, year_month):
        raise Exception("Budget conflict: parent or child already has budget")

    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
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
    # user = get_current_user()
    # if not user:
    #     raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()

    period_start = get_month_start(year_month)

    supabase.table("budgets") \
        .delete() \
        .eq("workspace_id", workspace_id) \
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

def carry_budgets_to_current_month(page=None):
    workspace_id = get_current_workspace_id(page)

    today = today_local(page)
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
        .eq("workspace_id", workspace_id)
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
            .eq("workspace_id", workspace_id)
            .eq("category_id", row["category_id"])
            .eq("period_start", current_start)
            .limit(1)
            .execute()
            .data
        ) or []

        if exists:
            continue

        payload = {
            # "user_id": user.id,
            "workspace_id": workspace_id,
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
            }).eq("id", row["id"]).eq("workspace_id", workspace_id).execute()

    return created

#  ---------- dashboard -----------



def get_current_month_dashboard_data(year_month=None, page=None):
    workspace_id = get_current_workspace_id(page)

    today = today_local(page)

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
        .eq("workspace_id", workspace_id)
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
        .eq("workspace_id", workspace_id)
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
        .eq("workspace_id", workspace_id)
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


# ================= SUBSCRIPTION =================

def get_my_subscription():
    user = get_current_user()
    if not user:
        return None

    res = (
        supabase.table("user_subscriptions")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    rows = res.data or []
    return rows[0] if rows else None


def is_user_pro():
    sub = get_my_subscription()

    if not sub:
        return False

    if sub.get("status") != "active":
        return False

    end = sub.get("current_period_end")
    if not end:
        return False

    return True


# -------------fixed_expenses -----------------


def get_fixed_expenses(page=None):
    workspace_id = get_current_workspace_id(page)

    if not workspace_id:
        return []

    rows = (
        supabase.table("fixed_expenses")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("next_run_date", desc=False)
        .execute()
        .data
    ) or []

    category_ids = list({
        r.get("id_hazine")
        for r in rows
        if r.get("id_hazine")
    })

    category_map = {}

    if category_ids:
        cat_rows = (
            supabase.table("hazineha")
            .select("id,title")
            .eq("workspace_id", workspace_id)
            .in_("id", category_ids)
            .execute()
            .data
        ) or []

        category_map = {
            c["id"]: c.get("title") or ""
            for c in cat_rows
        }

    for r in rows:
        r["category_title"] = category_map.get(r.get("id_hazine"), "")

    return rows

def create_fixed_expense(
    title,
    amount,
    id_hazine,
    frequency,
    next_run_date,
    account_id,
    status="active",
    auto_create=True,
    note=None,
):
    user = get_current_user()

    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()

    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not id_hazine:
        raise Exception("Category is required")

    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
        "title": title,
        "amount": float(amount),
        "id_hazine": id_hazine,
        "frequency": frequency,
        "next_run_date": next_run_date,
        "account_id": account_id,
        "status": status,
        "auto_create": bool(auto_create),
        "note": note,
    }

    res = supabase.table("fixed_expenses").insert(payload).execute()

    return res.data[0] if res.data else None


def update_fixed_expense(
    fixed_expense_id,
    title,
    amount,
    id_hazine,
    frequency,
    next_run_date,
    account_id,
    status="active",
    auto_create=True,
    note=None,
):
    workspace_id = get_current_workspace_id()

    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not fixed_expense_id:
        raise Exception("fixed_expense_id is required")

    if not id_hazine:
        raise Exception("Category is required")

    payload = {
        "title": title,
        "amount": float(amount),
        "id_hazine": id_hazine,
        "frequency": frequency,
        "next_run_date": next_run_date,
        "account_id": account_id,
        "status": status,
        "auto_create": bool(auto_create),
        "note": note,
    }

    res = (
        supabase.table("fixed_expenses")
        .update(payload)
        .eq("id", fixed_expense_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None


def delete_fixed_expense(fixed_expense_id):
    workspace_id = get_current_workspace_id()

    if not workspace_id:
        raise Exception("Workspace is not selected")

    res = (
        supabase.table("fixed_expenses")
        .delete()
        .eq("id", fixed_expense_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data

def add_months_to_date(d: date, months: int = 1) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1

    day = min(d.day, calendar.monthrange(year, month)[1])

    return date(year, month, day)


def calculate_next_fixed_expense_date(current_date: date, frequency: str) -> date:
    if frequency == "weekly":
        return current_date + timedelta(days=7)

    if frequency == "biweekly":
        return current_date + timedelta(days=14)

    if frequency == "monthly":
        return add_months_to_date(current_date, 1)

    if frequency == "yearly":
        return add_months_to_date(current_date, 12)

    return add_months_to_date(current_date, 1)


def process_due_fixed_expenses(page=None):
    user = get_current_user()

    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id(page)

    if not workspace_id:
        return {
            "ok": False,
            "created_count": 0,
            "checked_count": 0,
            "message": "Workspace is not selected",
        }

    today = today_local(page)
    today_iso = today.isoformat()

    fixed_rows = (
        supabase.table("fixed_expenses")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .eq("auto_create", True)
        .lte("next_run_date", today_iso)
        .execute()
        .data
    ) or []

    created_count = 0

    for item in fixed_rows:
        try:
            fixed_id = item.get("id")
            title = item.get("title") or "Fixed Expense"
            amount = float(item.get("amount") or 0)
            id_hazine = item.get("id_hazine")
            account_id = item.get("account_id")
            frequency = item.get("frequency") or "monthly"
            run_date_raw = item.get("next_run_date")

            if not fixed_id:
                continue

            if amount <= 0:
                continue

            if not id_hazine:
                print("[FIXED EXPENSE SKIPPED] missing id_hazine:", item, flush=True)
                continue

            if not account_id:
                print("[FIXED EXPENSE SKIPPED] missing account_id:", item, flush=True)
                continue

            if not run_date_raw:
                print("[FIXED EXPENSE SKIPPED] missing next_run_date:", item, flush=True)
                continue

            run_date = safe_picker_date(run_date_raw, page)

            duplicate = (
                supabase.table("cost")
                .select("id")
                .eq("workspace_id", workspace_id)
                .eq("fixed_expense_id", fixed_id)
                .eq("date_cost", run_date.isoformat())
                .limit(1)
                .execute()
                .data
            ) or []

            next_date = calculate_next_fixed_expense_date(run_date, frequency)

            if duplicate:
                supabase.table("fixed_expenses").update({
                    "next_run_date": next_date.isoformat(),
                }).eq("id", fixed_id).eq("workspace_id", workspace_id).execute()

                continue

            cost_payload = {
                "user_id": user.id,
                "workspace_id": workspace_id,
                "title": title,
                "price": amount,
                "date_cost": run_date.isoformat(),
                "id_hazine": id_hazine,
                "account_id": account_id,
                "fixed_expense_id": fixed_id,
                "temp_hazine": None,
            }

            supabase.table("cost").insert(cost_payload).execute()

            supabase.table("fixed_expenses").update({
                "next_run_date": next_date.isoformat(),
            }).eq("id", fixed_id).eq("workspace_id", workspace_id).execute()

            created_count += 1

        except Exception as ex:
            print("[PROCESS FIXED EXPENSE ERROR]", ex, "| item=", item, flush=True)

    return {
        "ok": True,
        "created_count": created_count,
        "checked_count": len(fixed_rows),
    }
    
# ================= BANK IMPORT / RECONCILIATION =================

def create_bank_import(
    account_id,
    file_name=None,
    file_type=None,
    detected_format=None,
    date_from=None,
    date_to=None,
):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not account_id:
        raise Exception("Account is required")

    payload = {
        "user_id": user.id,
        "workspace_id": workspace_id,
        "account_id": account_id,
        "file_name": file_name,
        "file_type": file_type,
        "detected_format": detected_format,
        "date_from": date_from,
        "date_to": date_to,
        "status": "draft",
    }

    res = supabase.table("bank_imports").insert(payload).execute()
    return res.data[0] if res.data else None


def get_bank_imports(page=None):
    workspace_id = get_current_workspace_id(page)
    if not workspace_id:
        return []

    rows = (
        supabase.table("bank_imports")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .execute()
        .data
    ) or []

    account_ids = list({
        r.get("account_id")
        for r in rows
        if r.get("account_id")
    })

    account_map = {}

    if account_ids:
        acc_rows = (
            supabase.table("accounts")
            .select("id,account_name,account_type")
            .eq("workspace_id", workspace_id)
            .in_("id", account_ids)
            .execute()
            .data
        ) or []

        account_map = {
            a["id"]: a
            for a in acc_rows
        }

    for r in rows:
        acc = account_map.get(r.get("account_id")) or {}
        r["account_name"] = acc.get("account_name", "")
        r["account_type"] = acc.get("account_type", "")

    return rows


def get_bank_import_by_id(import_id, page=None):
    workspace_id = get_current_workspace_id(page)
    if not workspace_id:
        return None

    rows = (
        supabase.table("bank_imports")
        .select("*")
        .eq("id", import_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
        .data
    ) or []

    return rows[0] if rows else None


def add_bank_import_rows(import_id, account_id, rows):
    user = get_current_user()
    if not user:
        raise Exception("User is not logged in")

    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not import_id:
        raise Exception("import_id is required")

    payloads = []

    for index, row in enumerate(rows or []):
        payloads.append({
            "import_id": import_id,
            "user_id": user.id,
            "workspace_id": workspace_id,
            "account_id": account_id,
            "row_index": row.get("row_index", index + 1),
            "bank_date": row.get("bank_date"),
            "bank_description": row.get("bank_description"),
            "raw_text": row.get("raw_text"),
            "amount": row.get("amount"),
            "currency": row.get("currency") or "CAD",
            "transaction_type": row.get("transaction_type") or "unknown",
            "match_status": row.get("match_status") or "new",
            "confidence_score": row.get("confidence_score") or 0,
            "matched_cost_id": row.get("matched_cost_id"),
            "matched_income_id": row.get("matched_income_id"),
            "matched_transfer_id": row.get("matched_transfer_id"),
            "suggested_category_id": row.get("suggested_category_id"),
            "suggested_member_id": row.get("suggested_member_id"),
            "note": row.get("note"),
        })

    if not payloads:
        return []

    res = supabase.table("bank_import_rows").insert(payloads).execute()

    refresh_bank_import_counts(import_id)

    return res.data or []


def get_bank_import_rows(import_id, status=None, page=None):
    workspace_id = get_current_workspace_id(page)
    if not workspace_id:
        return []

    q = (
        supabase.table("bank_import_rows")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("import_id", import_id)
        .order("bank_date", desc=True)
        .order("id", desc=True)
    )

    if status:
        q = q.eq("match_status", status)

    rows = q.execute().data or []

    category_ids = list({
        r.get("suggested_category_id")
        for r in rows
        if r.get("suggested_category_id")
    })

    category_map = {}

    if category_ids:
        cat_rows = (
            supabase.table("hazineha")
            .select("id,title")
            .eq("workspace_id", workspace_id)
            .in_("id", category_ids)
            .execute()
            .data
        ) or []

        category_map = {
            c["id"]: c.get("title") or ""
            for c in cat_rows
        }

    for r in rows:
        r["suggested_category_title"] = category_map.get(
            r.get("suggested_category_id"),
            "",
        )

    return rows


def update_bank_import_row_decision(
    row_id,
    user_decision,
    match_status=None,
    matched_cost_id=None,
    matched_income_id=None,
    matched_transfer_id=None,
    suggested_category_id=None,
    suggested_member_id=None,
    note=None,
):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    payload = {
        "user_decision": user_decision,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if match_status is not None:
        payload["match_status"] = match_status

    if matched_cost_id is not None:
        payload["matched_cost_id"] = matched_cost_id

    if matched_income_id is not None:
        payload["matched_income_id"] = matched_income_id

    if matched_transfer_id is not None:
        payload["matched_transfer_id"] = matched_transfer_id

    if suggested_category_id is not None:
        payload["suggested_category_id"] = suggested_category_id

    if suggested_member_id is not None:
        payload["suggested_member_id"] = suggested_member_id

    if note is not None:
        payload["note"] = note

    res = (
        supabase.table("bank_import_rows")
        .update(payload)
        .eq("id", row_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None


def refresh_bank_import_counts(import_id):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        return None

    rows = (
        supabase.table("bank_import_rows")
        .select("match_status")
        .eq("workspace_id", workspace_id)
        .eq("import_id", import_id)
        .execute()
        .data
    ) or []

    total_rows = len(rows)

    matched_count = 0
    possible_count = 0
    new_count = 0
    review_count = 0
    ignored_count = 0

    for r in rows:
        status = r.get("match_status")

        if status in ("matched", "confirmed"):
            matched_count += 1
        elif status == "possible_match":
            possible_count += 1
        elif status == "new":
            new_count += 1
        elif status in ("needs_review", "error"):
            review_count += 1
        elif status == "ignored":
            ignored_count += 1

    payload = {
        "total_rows": total_rows,
        "matched_count": matched_count,
        "possible_count": possible_count,
        "new_count": new_count,
        "review_count": review_count,
        "ignored_count": ignored_count,
        "updated_at": datetime.utcnow().isoformat(),
    }

    res = (
        supabase.table("bank_imports")
        .update(payload)
        .eq("id", import_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None


def update_bank_import_status(import_id, status, error_message=None):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    payload = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if error_message is not None:
        payload["error_message"] = error_message

    res = (
        supabase.table("bank_imports")
        .update(payload)
        .eq("id", import_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return res.data[0] if res.data else None

def find_possible_bank_matches(account_id, bank_date, amount, day_window=2, page=None):
    workspace_id = get_current_workspace_id(page)
    if not workspace_id:
        return []

    if not account_id or not bank_date or amount is None:
        return []

    try:
        amount_float = float(amount)
    except Exception:
        return []

    try:
        d = safe_picker_date(bank_date, page)
    except Exception:
        try:
            d = safe_picker_date(datetime.strptime(str(bank_date), "%Y-%m-%d"), page)
        except Exception:
            return []

    start_date = (d - timedelta(days=day_window)).isoformat()
    end_date = (d + timedelta(days=day_window)).isoformat()

def prepare_bank_import_rows_for_save(account_id, parsed_rows, page=None):
    prepared = []

    for row in parsed_rows or []:
        bank_date = row.get("bank_date")
        amount = row.get("amount")

        matches = find_possible_bank_matches(
            account_id=account_id,
            bank_date=bank_date,
            amount=amount,
            day_window=2,
        )

        new_row = dict(row)

        if matches:
            best = matches[0]

            # مهم:
            # match سیستمی نباید نهایی حساب شود.
            # فقط یعنی سیستم مشابه پیدا کرده و کاربر باید بررسی کند.
            new_row["match_status"] = "possible_match"

            if best.get("type") == "expense":
                new_row["matched_cost_id"] = best.get("id")
            elif best.get("type") == "income":
                new_row["matched_income_id"] = best.get("id")
            elif best.get("type") in ("transfer", "transfer_in", "transfer_out"):
                new_row["matched_transfer_id"] = best.get("id")

            new_row["confidence_score"] = max(
                float(new_row.get("confidence_score") or 0),
                float(best.get("score") or 0),
            )
        else:
            if not bank_date or amount is None:
                new_row["match_status"] = "needs_review"
            else:
                new_row["match_status"] = "new"

        prepared.append(new_row)

    return prepared



def mark_bank_row_as_created_cost(bank_row_id, cost_id):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not bank_row_id:
        raise Exception("bank_row_id is required")

    if not cost_id:
        raise Exception("cost_id is required")

    res = (
        supabase.table("bank_import_rows")
        .update({
            "created_cost_id": cost_id,
            "matched_cost_id": cost_id,
            "match_status": "confirmed",
            "user_decision": "create_expense",
            "updated_at": datetime.utcnow().isoformat(),
        })
        .eq("id", bank_row_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    updated_row = res.data[0] if res.data else None

    if updated_row and updated_row.get("import_id"):
        refresh_bank_import_counts(updated_row.get("import_id"))

    return updated_row

def get_income_transaction_by_id(tx_id):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        return None

    rows = (
        supabase.table("income_transactions")
        .select("*")
        .eq("id", tx_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
        .data
    ) or []

    return rows[0] if rows else None


def mark_bank_row_as_created_income(bank_row_id, income_id):
    workspace_id = get_current_workspace_id()
    if not workspace_id:
        raise Exception("Workspace is not selected")

    if not bank_row_id:
        raise Exception("bank_row_id is required")

    if not income_id:
        raise Exception("income_id is required")

    res = (
        supabase.table("bank_import_rows")
        .update({
            "created_income_id": income_id,
            "matched_income_id": income_id,
            "match_status": "confirmed",
            "user_decision": "create_income",
            "updated_at": datetime.utcnow().isoformat(),
        })
        .eq("id", bank_row_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    updated_row = res.data[0] if res.data else None

    if updated_row and updated_row.get("import_id"):
        refresh_bank_import_counts(updated_row.get("import_id"))

    return updated_row

def delete_my_account():
    try:
        print("[DELETE MY ACCOUNT] called", flush=True)

        user = get_current_user()

        if not user:
            print("[DELETE MY ACCOUNT] no user", flush=True)
            return {
                "ok": False,
                "error": "User is not logged in."
            }

        print("[DELETE MY ACCOUNT] user_id:", user.id, flush=True)

        res = supabase.rpc("delete_my_account_data").execute()

        print("[DELETE MY ACCOUNT RPC RESULT]", res.data, flush=True)

        if not res.data:
            return {
                "ok": False,
                "error": "Delete account RPC returned no data."
            }

        if isinstance(res.data, dict) and not res.data.get("ok"):
            return {
                "ok": False,
                "error": res.data.get("error", "Delete account failed.")
            }

        try:
            clear_hazineha_cache()
        except Exception:
            pass

        try:
            supabase.auth.sign_out()
        except Exception as ex:
            print("[DELETE ACCOUNT] sign_out:", ex, flush=True)

        return {
            "ok": True,
            "data": res.data
        }

    except Exception as ex:
        print("[DELETE MY ACCOUNT ERROR]", repr(ex), flush=True)
        return {
            "ok": False,
            "error": str(ex),
        }


def is_current_user_allowed():
    try:
        profile = get_my_profile()

        if not profile:
            return {
                "ok": False,
                "reason": "profile_not_found",
                "message": "This account is not available.",
            }

        print(
            "[USER ALLOWED PROFILE]",
            "is_active=", profile.get("is_active"),
            "status=", profile.get("status"),
            "deleted_at=", profile.get("deleted_at"),
            flush=True,
        )

        if profile.get("is_active") is False:
            return {
                "ok": False,
                "reason": "inactive",
                "message": "This account has been disabled.",
            }

        if profile.get("status") == "deleted" or profile.get("deleted_at"):
            return {
                "ok": False,
                "reason": "deleted",
                "message": "This account has been deleted and can no longer be used.",
            }

        return {
            "ok": True,
            "profile": profile,
        }

    except Exception as ex:
        print("[USER ALLOWED CHECK ERROR]", ex, flush=True)
        return {
            "ok": False,
            "reason": "error",
            "message": "Could not verify this account.",
        }
    