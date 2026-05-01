import os
import json
from openai import OpenAI
from services.supabase_service import get_members
from datetime import datetime


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
    try:
        if client is None:
            return None
        if not text:
            return None

        now = datetime.now()
        print("ssssssss 311 = ")
        print(now.strftime("%H:%M:%S.%f")[:-3])

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        now = datetime.now()
        print("ssssssss 312 = ")
        print(now.strftime("%H:%M:%S.%f")[:-3])

        return response.data[0].embedding

    except Exception as e:
        print("get_embedding error:", e)
        return None
    

_MEMBERS_CACHE = {
    "names": None,
    "time": 0,
}

def get_member_names_cached(ttl=60):
    import time

    now = time.time()

    if _MEMBERS_CACHE["names"] is not None and now - _MEMBERS_CACHE["time"] < ttl:
        return _MEMBERS_CACHE["names"]

    members = get_members()
    names = [m["full_name"] for m in members]

    _MEMBERS_CACHE["names"] = names
    _MEMBERS_CACHE["time"] = now

    return names

def normalize_expense(data: dict) -> dict:
    if not data:
        data = {}

    return {
        "title": data.get("title"),
        "price": data.get("price"),
        "date": data.get("date"),
        "member_name": data.get("member_name"),
        # 👇 سازگاری با کدهای قدیمی
        "currency": data.get("currency", None),
    }

def extract_expense_fields_with_openai(text):
    if client is None:
        return None

    names = get_member_names_cached()

    text_n = (text or "").strip()

    # فقط اسم‌های مرتبط با متن
    possible_names = [
        n for n in names
        if n and (n in text_n or text_n in n)
    ]

    known_names = possible_names[:10]

    system_prompt = f"""
Extract expense data. Return ONLY valid JSON.

Keys:
title, price, date, member_name

Rules:
- title: short clean name.
- price: number only or null.
- date: YYYY-MM-DD only if explicitly mentioned, else null.
- member_name: explicit only, else null.
- "خودم" => "self".
- If close to known_names, return exact match.
- Do not guess.

known_names:
{known_names}
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": text_n},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=70,
            temperature=0,
        )

        raw = response.choices[0].message.content
        parsed = safe_json_load(raw)
        return normalize_expense(parsed)

    except Exception as ex:
        print("OPENAI EXTRACT ERROR:", type(ex).__name__, ex)
        return None



# def extract_expense_fields_with_openai(text):
#     if client is None:
#         return None

    
#     now = datetime.now()
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

#         now = datetime.now()
#         print("www = ")
#         print(now.strftime("%H:%M:%S.%f")[:-3])
#         raw = response.choices[0].message.content

#         return safe_json_load(raw)

#     except Exception as e:
#         print("extract_expense_fields_with_openai error:", e)
#         return None
    
    
    