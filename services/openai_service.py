from functools import lru_cache
from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def safe_json_load(text):
    try:
        return json.loads(text)
    except:
        return None


def normalize_output(data, text):
    return {
        "title": data.get("title") or text,
        "price": data.get("price"),
        "currency": data.get("currency"),
        "date": data.get("date"),
    }


@lru_cache(maxsize=512)
def parse_expense_with_openai(text):
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "developer",
                    "content": "Extract title, price, currency, date. Return JSON only."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=60,
        )

        raw = response.choices[0].message.content

        data = safe_json_load(raw)

        if not data:
            return {
                "title": text,
                "price": None,
                "currency": None,
                "date": None
            }

        return normalize_output(data, text)

    except Exception as e:
        print("OpenAI error:", e)

        return {
            "title": text,
            "price": None,
            "currency": None,
            "date": None
        }