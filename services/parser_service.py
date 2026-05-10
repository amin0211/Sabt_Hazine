import re
from difflib import SequenceMatcher
from datetime import datetime

from services.supabase_service import (
    load_leaf_hazineha,
    find_category_learning_exact,
    match_category_learning_by_embedding,
)

from services.openai_service import (
    extract_expense_fields_with_openai,
    is_openai_available,
    get_embedding,
)


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"

DIGIT_MAP = {}
for i, d in enumerate(PERSIAN_DIGITS):
    DIGIT_MAP[d] = ENGLISH_DIGITS[i]
for i, d in enumerate(ARABIC_DIGITS):
    DIGIT_MAP[d] = ENGLISH_DIGITS[i]


NEGATIVE_KEYWORDS = [
    "پس دادم",
    "پس داد",
    "برگردوندم",
    "برگردونده شد",
    "مرجوع کردم",
    "مرجوع",
    "استرداد",
    "refund",
    "returned",
    "return",
    "cashback",
]


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def fuzzy_token_match_score(tokens: list[str], candidate_text: str, threshold=0.78) -> int:
    score = 0
    candidate_tokens = normalize_text(candidate_text).split()

    for tok in tokens:
        for ctok in candidate_tokens:
            if len(tok) < 3 or len(ctok) < 3:
                continue
            if similar(tok, ctok) >= threshold:
                score += 3

    return score


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).strip().lower()

    # عربی/فارسی یکدست‌سازی
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("ة", "ه")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ؤ", "و")
    text = text.replace("‌", " ")  # ZWNJ

    # اعداد فارسی/عربی → انگلیسی
    text = "".join(DIGIT_MAP.get(ch, ch) for ch in text)

    # حذف علائم اضافی
    text = re.sub(r"[^\w\s\u0600-\u06FF\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str):
    text_n = normalize_text(text)
    if not text_n:
        return []
    return [tok for tok in text_n.split() if tok]


def normalize_price_sign(text, price):
    if price is None:
        return None

    try:
        price = float(price)
    except Exception:
        return None

    text_n = normalize_text(text)

    if any(normalize_text(k) in text_n for k in NEGATIVE_KEYWORDS):
        return -abs(price)

    return abs(price)


# def detect_currency(text: str):
#     text_n = normalize_text(text)

#     toman_words = ["تومن", "تومان", "tom an", "toman"]
#     rial_words = ["ریال", "rial", "iranian rial", "irr"]
#     dollar_words = ["دلار", "دالر", "usd", "dollar", "$"]
#     euro_words = ["یورو", "euro", "eur", "€"]

#     if any(w in text_n for w in toman_words):
#         return "TOMAN"
#     if any(w in text_n for w in rial_words):
#         return "RIAL"
#     if any(w in text_n for w in dollar_words):
#         return "USD"
#     if any(w in text_n for w in euro_words):
#         return "EUR"

#     return None


def fallback_result(text):
    return {
        "title": text,
        "price": None,
        # "currency": detect_currency(text),
        "date": None,
        "member_name": None,
        "category_id": None,
        "category_title": None,
        "matched": False,
        "suggestions": []
    }


def _score_title(text_n: str, tokens: list[str], title_n: str) -> int:
    score = 0

    if not title_n:
        return 0

    if title_n == text_n:
        score += 20

    if title_n in text_n:
        score += 10

    title_tokens = title_n.split()
    overlap = len(set(tokens) & set(title_tokens))
    score += overlap * 3

    for token in tokens:
        if token and token in title_n:
            score += 2

    score += fuzzy_token_match_score(tokens, title_n, threshold=0.78)

    return score

def find_exact_keyword_match(title: str, categories: list[dict]):
    title_n = normalize_text(title)

    for cat in categories:
        for kw in (cat.get("keywords", []) or []):
            kw_n = normalize_text(kw)

            if not kw_n:
                continue

            # تطابق دقیق
            if kw_n == title_n:
                return {
                    "category_id": cat["id"],
                    "category_title": cat["title"],
                    "matched": True,
                    "suggestions": [],
                    "source": "hazineha_keyword_exact"
                }

    return None

def _score_keywords(text_n: str, tokens: list[str], keywords: list[str]) -> int:
    score = 0
    matched_keywords = 0

    for kw in keywords or []:
        kw_n = normalize_text(kw)
        if not kw_n:
            continue

        if kw_n == text_n:
            score += 18
            matched_keywords += 1
            continue

        if kw_n in text_n:
            score += 8
            matched_keywords += 1
            continue

        kw_tokens = kw_n.split()
        overlap = len(set(tokens) & set(kw_tokens))
        if overlap > 0:
            score += overlap * 4
            matched_keywords += 1

        fuzzy_score = fuzzy_token_match_score(tokens, kw_n, threshold=0.78)
        if fuzzy_score > 0:
            score += fuzzy_score + 2
            matched_keywords += 1

    if matched_keywords >= 2:
        score += 6

    return score


def shortlist_categories(text, categories, limit=20):
    """
    دسته‌بندی‌ها را بر اساس title + keywords امتیازدهی می‌کند.
    """
    text_n = normalize_text(text)
    tokens = tokenize(text)

    if not categories:
        return []

    scored = []

    for cat in categories:
        title_n = normalize_text(cat.get("title", ""))
        keywords = cat.get("keywords", []) or []

        score = 0
        score += _score_title(text_n, tokens, title_n)
        score += _score_keywords(text_n, tokens, keywords)

        if title_n and any(tok == title_n for tok in tokens):
            score += 5

        if score > 0:
            scored.append((score, cat))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return [cat for _, cat in scored[:limit]]

    return []

def resolve_category_from_title(title: str):
    title_n = normalize_text(title)

    # 1) learning exact - سریع
    exact_learning = find_category_learning_exact(title_n)

    if exact_learning and exact_learning.get("category_id"):
        return {
            "category_id": exact_learning["category_id"],
            "category_title": exact_learning.get("category_title"),
            "matched": True,
            "suggestions": [],
            "source": "learning_exact",
        }

    # 2) keyword exact - سریع
    categories = load_leaf_hazineha() or []

    exact_keyword_match = find_exact_keyword_match(title_n, categories)

    if exact_keyword_match:
        return exact_keyword_match

    # 3) keyword / fuzzy shortlist - سریع
    shortlisted = shortlist_categories(title_n, categories, limit=3)

    if shortlisted:
        # اگر فقط یک نتیجه داریم، مستقیم match کن
        if len(shortlisted) == 1:
            cat = shortlisted[0]
            return {
                "category_id": cat["id"],
                "category_title": cat["title"],
                "matched": True,
                "suggestions": [],
                "source": "hazineha_keywords",
            }

        # اگر چند پیشنهاد داریم، اینجا embedding را به عنوان آخرین تلاش تست کن
        embedding_match = resolve_by_learning_embedding(title_n)

        if embedding_match:
            return embedding_match

        # اگر embedding هم نتیجه نداد، پیشنهادها را نشان بده
        return {
            "category_id": None,
            "category_title": None,
            "matched": False,
            "suggestions": [
                {
                    "category_id": c["id"],
                    "category_title": c["title"],
                }
                for c in shortlisted[:3]
            ],
            "source": "hazineha_keywords",
        }

    # 4) اگر هیچ keyword/fuzzy پیدا نشد، آخرین شانس: embedding
    embedding_match = resolve_by_learning_embedding(title_n)

    if embedding_match:
        return embedding_match

    # 5) هیچ نتیجه‌ای پیدا نشد
    return {
        "category_id": None,
        "category_title": None,
        "matched": False,
        "suggestions": [],
    }


def resolve_by_learning_embedding(title_n: str):
    embedding_vector = get_embedding(title_n)

    if not embedding_vector:
        return None

    learning_match = match_category_learning_by_embedding(
        embedding_vector,
        threshold=0.60,
    )


    if learning_match and learning_match.get("category_id"):
        return {
            "category_id": learning_match["category_id"],
            "category_title": learning_match.get("category_title"),
            "matched": True,
            "suggestions": [],
            "source": "learning_embedding",
        }

    return None

def parse_expense(text):
    result = fallback_result(text)

    try:
        # print("========== PARSE START ==========")
        # print("INPUT =", repr(text))

        extracted = None
        if is_openai_available():
            extracted = extract_expense_fields_with_openai(text)


        if not extracted:
            return result

        title = (extracted.get("title") or text).strip()
        price = normalize_price_sign(text, extracted.get("price"))
        # currency = extracted.get("currency") or detect_currency(text)
        date_value = extracted.get("date")
        member_name = extracted.get("member_name")
        account_name = extracted.get("account_name")
        # print("TITLE =", repr(title))
        # print("TITLE_N =", repr(normalize_text(title)))


        category_result = resolve_category_from_title(title)


        final_result = {
            "title": title,
            "price": price,
            # "currency": currency,
            "date": date_value,
            "member_name": member_name,
            "account_name": account_name,
            "category_id": category_result.get("category_id"),
            "category_title": category_result.get("category_title"),
            "matched": category_result.get("matched", False),
            "suggestions": category_result.get("suggestions", []),
        }

        # print("========== PARSE END ==========")

        return final_result

    except Exception as e:
        print("Parser error:", e)
        return result