import os
import json
from openai import OpenAI
from services.supabase_service import get_members, get_accounts


def perf_log(tag, t0=None, extra=""):
    import time
    now = time.perf_counter()

    if t0 is None:
        print(f"[OPENAI PERF] {tag} START {extra}", flush=True)
        return now

    print(f"[OPENAI PERF] {tag} = {now - t0:.3f}s {extra}", flush=True)
    return now

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def is_openai_available():
    return client is not None


def safe_json_load(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def get_embedding(text: str):
    total_t0 = perf_log("GET_EMBEDDING", extra=f"text={text!r}")

    try:
        if client is None:
            print("[OPENAI PERF] GET_EMBEDDING skipped: client is None", flush=True)
            return None

        if not text:
            print("[OPENAI PERF] GET_EMBEDDING skipped: empty text", flush=True)
            return None

        t0 = perf_log("EMBEDDING_API_CALL")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        perf_log("EMBEDDING_API_CALL", t0)

        vector = response.data[0].embedding

        perf_log("GET_EMBEDDING_TOTAL", total_t0, extra=f"vector_len={len(vector) if vector else 0}")
        return vector

    except Exception as e:
        print("get_embedding error:", type(e).__name__, e, flush=True)
        perf_log("GET_EMBEDDING_ERROR_TOTAL", total_t0)
        return None   

_MEMBERS_CACHE = {
    "names": None,
    "time": 0,
}


def get_member_names_cached(ttl=60):
    import time

    total_t0 = perf_log("GET_MEMBER_NAMES_CACHED")

    now = time.time()

    if _MEMBERS_CACHE["names"] is not None and now - _MEMBERS_CACHE["time"] < ttl:
        perf_log(
            "GET_MEMBER_NAMES_CACHED_TOTAL",
            total_t0,
            extra=f"source=cache count={len(_MEMBERS_CACHE['names'])}"
        )
        return _MEMBERS_CACHE["names"]

    t0 = perf_log("GET_MEMBERS_DB")
    members = get_members()
    perf_log("GET_MEMBERS_DB", t0, extra=f"rows={len(members or [])}")

    names = [m["full_name"] for m in members]

    _MEMBERS_CACHE["names"] = names
    _MEMBERS_CACHE["time"] = now

    perf_log("GET_MEMBER_NAMES_CACHED_TOTAL", total_t0, extra=f"source=db count={len(names)}")
    return names

_ACCOUNTS_CACHE = {
    "names": None,
    "time": 0,
}

def get_account_names_cached(ttl=60):
    import time

    total_t0 = perf_log("GET_ACCOUNT_NAMES_CACHED")

    t = time.time()

    if _ACCOUNTS_CACHE["names"] is not None and t - _ACCOUNTS_CACHE["time"] < ttl:
        perf_log(
            "GET_ACCOUNT_NAMES_CACHED_TOTAL",
            total_t0,
            extra=f"source=cache count={len(_ACCOUNTS_CACHE['names'])}"
        )
        return _ACCOUNTS_CACHE["names"]

    t0 = perf_log("GET_ACCOUNTS_DB")
    accounts = get_accounts()
    perf_log("GET_ACCOUNTS_DB", t0, extra=f"rows={len(accounts or [])}")

    names = [a["account_name"] for a in accounts if a.get("account_name")]

    _ACCOUNTS_CACHE["names"] = names
    _ACCOUNTS_CACHE["time"] = t

    perf_log("GET_ACCOUNT_NAMES_CACHED_TOTAL", total_t0, extra=f"source=db count={len(names)}")
    return names

def normalize_expense(data: dict) -> dict:
    if not data:
        data = {}

    transaction_type = data.get("transaction_type") or "expense"

    transaction_type = str(transaction_type).strip().lower()

    allowed_types = {
        "expense",
        "refund",
        "income",
        "transfer",
        "unknown",
    }

    if transaction_type not in allowed_types:
        transaction_type = "expense"

    return {
        "title": data.get("title"),
        "price": data.get("price"),
        "date": data.get("date"),
        "member_name": data.get("member_name"),
        "account_name": data.get("account_name"),
        "transaction_type": transaction_type,
    }


def extract_expense_fields_with_openai(text):
    total_t0 = perf_log("EXTRACT_EXPENSE_OPENAI", extra=f"text={text!r}")

    if client is None:
        print("[OPENAI PERF] EXTRACT skipped: client is None", flush=True)
        return None

    try:
        t0 = perf_log("LOAD_MEMBER_NAMES")
        names = get_member_names_cached()
        perf_log("LOAD_MEMBER_NAMES", t0, extra=f"count={len(names or [])}")

        t0 = perf_log("LOAD_ACCOUNT_NAMES")
        account_names = get_account_names_cached()
        perf_log("LOAD_ACCOUNT_NAMES", t0, extra=f"count={len(account_names or [])}")

        text_n = (text or "").strip()

        t0 = perf_log("FILTER_KNOWN_NAMES_ACCOUNTS")

        possible_names = [
            n for n in names
            if n and (n in text_n or text_n in n)
        ]

        known_names = possible_names[:10]

        possible_accounts = [
            a for a in account_names
            if a and (a in text_n or text_n in a)
        ]

        known_accounts = possible_accounts[:10]

        perf_log(
            "FILTER_KNOWN_NAMES_ACCOUNTS",
            t0,
            extra=f"known_names={len(known_names)} known_accounts={len(known_accounts)}"
        )

        known_context = ""

        if known_names:
            known_context += "\nknown_names: " + ", ".join(known_names)

        if known_accounts:
            known_context += "\nknown_accounts: " + ", ".join(known_accounts)
            
        system_prompt = f"""
        Return ONLY valid JSON with keys:
        title, price, date, member_name, account_name, transaction_type

        transaction_type must be one of:
        expense, refund, income, transfer, unknown

        Rules:
        - Extract only explicit information. Do not guess.
        - title: short clean item/service name; remove verbs/currency/filler.
        - price: positive number or null. Combine cents: "۲۶۸ دلار و ۴۸ سنت" => 268.48.
        - date: YYYY-MM-DD only if explicit, else null.
        - member_name: explicit only; "خودم" => "self"; use exact known_names match if close.
        - account_name: explicit only; use exact known_accounts match if close.
        - refund/return/cashback/مرجوع/ریترن/پول برگشت => refund.
        - salary/income/deposit/حقوق/درآمد/واریز => income.
        - moving money between own accounts => transfer.
        - normal spending/buying/paying => expense.
        {known_context}
        """

        t0 = perf_log("CHAT_COMPLETION_API_CALL")
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": text_n},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=90,
            temperature=0,
        )
        perf_log("CHAT_COMPLETION_API_CALL", t0)

        t0 = perf_log("PARSE_OPENAI_JSON")
        raw = response.choices[0].message.content
        parsed = safe_json_load(raw)
        normalized = normalize_expense(parsed)
        perf_log("PARSE_OPENAI_JSON", t0, extra=f"raw={raw!r}")

        perf_log("EXTRACT_EXPENSE_OPENAI_TOTAL", total_t0, extra=f"result={normalized}")
        return normalized

    except Exception as ex:
        print("OPENAI EXTRACT ERROR:", type(ex).__name__, ex, flush=True)
        perf_log("EXTRACT_EXPENSE_OPENAI_ERROR_TOTAL", total_t0)
        return None

# def extract_expense_fields_with_openai(text):
#     if client is None:
#         return None

    
#     now = now
#     print("qqq = ")
#     print(now.strftime("%H:%M:%S.%f")[:-3])

#     members = get_members()
#     member_name = [m["full_name"] for m in members]
#     try:
#         response = client.chat.completions.create(
#             model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
#             messages = [
#                 {
#                     "role": "system",
#                     "content": f"""
#             Return ONLY valid JSON.

#             Keys:
#             - title (string)
#             - price (number or null)
#             - currency (string or null)
#             - date (YYYY-MM-DD or null)
#             - member_name (string or null)

#             Rules:
#             - Extract the expense title only.
#             - The title must be short and clean.
#             - Remove filler words and unrelated sentence parts.

#             Examples:
#             "من رفتم بازار و تخته پاک کن 20 دلار خریدم" -> "تخته پاک کن"
#             "دیروز برای مدرسه ماژیک وایت برد 50 خریدم" -> "ماژیک وایت برد"

#             Price rules:
#             - Extract numeric amount if present.
#             - If no price exists, return null.

#             Date rules:
#             - If a date exists, convert it to YYYY-MM-DD.
#             - If no date exists, return null.
#             - NEVER guess missing values.

#             Member/entity rules:
#             - Extract the related person or entity ONLY if explicitly mentioned.
#             - This can be a family member, a person, a company, an organization, a customer, or any named party.
#             - Examples:
#             "برای مامان" -> "مامان"
#             "برای آقای حسینی" -> "آقای حسینی"
#             "برای شرکت ساختمانی" -> "شرکت ساختمانی"
#             "مال علی" -> "علی"
#             "واسه شرکت پارس" -> "شرکت پارس"

#             - Do NOT guess.
#             - If no related person/entity is explicitly mentioned, return null.
#             - If "خودم" or "برای خودم" is mentioned, return "self".

#             Known names/entities list:
#             {member_name}

#             - If the text contains a name similar to one of the known names/entities, return the exact name from the list.
#             - Otherwise return the extracted name as-is.

#             Strict output:
#             - Return ONLY JSON.
#             - No explanation.
#             - No markdown.
#             """
#                 },
#                 {
#                     "role": "user",
#                     "content": text
#                 }
#             ],
#             response_format={"type": "json_object"},
#             max_completion_tokens=300,
#             reasoning_effort="minimal",
#         )

#         now = now
#         print("www = ")
#         print(now.strftime("%H:%M:%S.%f")[:-3])
#         raw = response.choices[0].message.content

#         return safe_json_load(raw)

#     except Exception as e:
#         print("extract_expense_fields_with_openai error:", e)
#         return None
    
    
    