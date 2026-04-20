from functools import lru_cache
from openai import OpenAI
import os
import json
from flask import Flask, request, jsonify
from services.supabase_service import insert_log, load_leaf_hazineha

app = Flask(__name__)

api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None


def normalize_price_sign(text, price):
    if price is None:
        return None

    try:
        price = float(price)
    except:
        return None

    text = (text or "").strip().lower()

    negative_keywords = [
        "پس دادم",
        "پس داد",
        "برگردوندم",
        "برگردونده شد",
        "مرجوع کردم",
        "مرجوع",
        "refund",
        "returned",
        "return",
        "cashback",
    ]

    if any(k in text for k in negative_keywords):
        return -abs(price)

    return abs(price)


def normalize_output(data, text):
    return {
        "title": data.get("category_title") or data.get("title") or text,
        "price": data.get("price"),
        "currency": data.get("currency"),
        "date": data.get("date"),
        "category_id": data.get("category_id"),
        "category_title": data.get("category_title"),
        "matched": bool(data.get("matched", False)),
        "suggestions": data.get("suggestions", []),
    }


def shortlist_categories(text, categories, limit=40):
    text_l = (text or "").lower().strip()
    if not text_l:
        return categories[:limit]

    keywords = text_l.split()
    scored = []

    for cat in categories:
        title_l = cat["title"].lower()
        score = 0

        for kw in keywords:
            if kw and kw in title_l:
                score += 3

        if score > 0:
            scored.append((score, cat))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return [cat for _, cat in scored[:limit]]

    return categories[:limit]

def safe_json_load(text):
    try:
        return json.loads(text)
    except:
        return None




@lru_cache(maxsize=512)
def parse_expense_with_openai(text):
    # insert_log(text, "parse_expense_with_openai 1")

    fallback = {
        "title": text,
        "price": None,
        "currency": None,
        "date": None,
        "category_id": None,
        "category_title": None,
        "matched": False,
        "suggestions": []
    }

    if client is None:
        return fallback   
    try:
        categories = load_leaf_hazineha()
        # print(f"categories = {categories}")
        
        shortlisted = shortlist_categories(text, categories, limit=40)
        # print(f"shortlisted = {shortlisted}")

        categories_json = json.dumps(shortlisted, ensure_ascii=False)
        # print(f"categories_json = {categories_json}")

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Return ONLY valid JSON.

Keys:
- title (string)
- price (number or null)
- currency (string or null)
- date (YYYY-MM-DD or null)
- category_id (number or null)
- category_title (string or null)
- matched (boolean)
- suggestions (array)

Rules:
- Extract expense title from the text.
- Extract numeric amount if present.
- If the text contains Persian money words like "تومن", "تومان", "ریال", set currency properly.
- If no price exists, return null for price.
- If no date exists, return null for date.
- NEVER guess missing values.

- If the text indicates refund or money returned
  (e.g. "پس دادم", "برگردوندم", "مرجوع کردم", "refund", "returned"),
  the price MUST be negative.

Category matching rules:
- You MUST choose category only from the provided categories.
- If there is a confident match:
  matched = true
  category_id = chosen category id
  category_title = chosen category title
  suggestions = []

- If there is NOT a confident match:
  matched = false
  category_id = null
  category_title = null
  suggestions = up to 3 closest categories from the provided list

- Never invent a category.
- suggestions must be an array of objects like:
  {"category_id": 123, "category_title": "..."}

Do NOT include markdown or explanation.
"""
                },
                {
                    "role": "user",
                    "content": f"""Text:
                    {text}

                    Available categories:
                    {categories_json}
                    """
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=400,
            reasoning_effort="minimal",
        )

        # insert_log(text, "parse_expense_with_openai 2")
    
        raw = response.choices[0].message.content

        # insert_log(raw, "parse_expense_with_openai 3")
    

        data = safe_json_load(raw)
        # insert_log(data.get("price"), "parse_expense_with_openai 4")  
        if not data:
            return fallback


        data["price"] = normalize_price_sign(text, data.get("price"))

        valid_ids = {c["id"] for c in shortlisted}
        valid_map = {c["id"]: c["title"] for c in shortlisted}
        # print(f"111 = {valid_ids}")
        # print(f"222 = {valid_map}")
        # print(f"333 = {data.get("category_id")}")
        
        category_id = data.get("category_id")
        if category_id not in valid_ids:
            # print(f"666 = ")
            data["category_id"] = None
            data["category_title"] = None
            data["matched"] = False
        else:
            data["category_title"] = valid_map.get(category_id)
            # print(f"777 = {valid_map.get(category_id)}")
        
        suggestions = data.get("suggestions", [])
        
        # print(f"555 = {suggestions}")

        cleaned_suggestions = []

        if isinstance(suggestions, list):
            for item in suggestions[:3]:
                if not isinstance(item, dict):
                    continue
                sid = item.get("category_id")
                if sid in valid_ids:
                    cleaned_suggestions.append({
                        "category_id": sid,
                        "category_title": valid_map[sid]
                    })

        data["suggestions"] = cleaned_suggestions

        # print(f"444 = {suggestions}")
        # print(f"555a = {categories}")
        return normalize_output(data, text)
    
    except Exception as e:
        print("OpenAI error:", e)

        return fallback
    

    
# ---------------- ROUTE ----------------
@app.route("/parse", methods=["POST"])
def parse_route():
    try:
        data = request.get_json()
        text = data.get("text", "")

        result = parse_expense_with_openai(text)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- HOME TEST ----------------
@app.route("/")
def home():
    return "🚀 Server is running"

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

#print("🔥 SERVER IS STARTING...")

