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


_CATEGORY_LEARNING_EXACT_CACHE = {}


def find_category_learning_exact_cached(title_n, ttl=60):
    import time

    now = time.time()
    key = title_n

    cached = _CATEGORY_LEARNING_EXACT_CACHE.get(key)

    if cached and now - cached["time"] < ttl:
        return cached["data"]

    data = find_category_learning_exact(title_n)

    # مهم:
    # اگر match نبود، None را cache نکن
    # چون ممکن است چند ثانیه بعد کاربر همان title را یاد بدهد.
    if data and data.get("category_id"):
        _CATEGORY_LEARNING_EXACT_CACHE[key] = {
            "data": data,
            "time": now,
        }

    return data


_LEAF_CATEGORIES_CACHE = {
    "data": None,
    "time": 0,
}


def load_leaf_hazineha_cached(ttl=300):
    import time

    now = time.time()

    if (
        _LEAF_CATEGORIES_CACHE["data"] is not None
        and now - _LEAF_CATEGORIES_CACHE["time"] < ttl
    ):
        return _LEAF_CATEGORIES_CACHE["data"]

    data = load_leaf_hazineha() or []

    _LEAF_CATEGORIES_CACHE["data"] = data
    _LEAF_CATEGORIES_CACHE["time"] = now

    return data


def perf_log(tag, t0=None, extra=""):
    import time

    now = time.perf_counter()

    if t0 is None:
        print(f"[PARSER PERF] {tag} START {extra}", flush=True)
        return now

    print(f"[PARSER PERF] {tag} = {now - t0:.3f}s {extra}", flush=True)
    return now


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"

DIGIT_MAP = {}

for i, d in enumerate(PERSIAN_DIGITS):
    DIGIT_MAP[d] = ENGLISH_DIGITS[i]

for i, d in enumerate(ARABIC_DIGITS):
    DIGIT_MAP[d] = ENGLISH_DIGITS[i]


PERSIAN_NUMBER_WORDS = {
    "صفر": 0,
    "یک": 1,
    "یه": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "چار": 4,
    "پنج": 5,
    "شش": 6,
    "شیش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,

    "ده": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "شانزده": 16,
    "هفده": 17,
    "هجده": 18,
    "نوزده": 19,

    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,

    "صد": 100,
    "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
    "ششصد": 600,
    "هفتصد": 700,
    "هشتصد": 800,
    "نهصد": 900,

    "هزار": 1000,
}

PERSIAN_NUMBER_WORD_RE = "|".join(
    sorted(
        (re.escape(k) for k in PERSIAN_NUMBER_WORDS.keys()),
        key=len,
        reverse=True,
    )
)

PERSIAN_NUMBER_PHRASE_RE = (
    rf"(?:{PERSIAN_NUMBER_WORD_RE})"
    rf"(?:\s+و\s+(?:{PERSIAN_NUMBER_WORD_RE})|\s+(?:{PERSIAN_NUMBER_WORD_RE}))*"
)

def extract_member_by_known_members(text: str, members: list[dict] | None = None):
    """
    Match member directly from a provided members list.
    No DB call here.
    """

    text_n = normalize_text(text)

    if not text_n or not members:
        return None, None, None

    best_match = None
    best_score = 0
    best_text = None

    for member in members:
        member_id = member.get("id")
        full_name = (
            member.get("full_name")
            or member.get("name")
            or member.get("title")
            or ""
        )

        if not full_name:
            continue

        name_n = normalize_text(full_name)

        candidates = []

        if name_n:
            candidates.append(name_n)

        name_parts = name_n.split()

        # "پرهام یاوری" -> "پرهام"
        if name_parts:
            candidates.append(name_parts[0])

        relation = member.get("relation")
        if relation:
            candidates.append(normalize_text(relation))

        for candidate in candidates:
            candidate = normalize_text(candidate)

            if not candidate or len(candidate) < 2:
                continue

            score = 0

            # exact word match
            if re.search(rf"(^|\s){re.escape(candidate)}($|\s)", text_n):
                score = 100

            # contained match
            elif candidate in text_n:
                score = 85

            # fuzzy match for voice/STT mistakes
            else:
                for token in text_n.split():
                    if len(token) >= 3:
                        ratio = similar(token, candidate)

                        if ratio >= 0.86:
                            score = max(score, int(ratio * 75))

            if score > best_score:
                best_score = score
                best_match = member
                best_text = candidate

    if best_match and best_score >= 70:
        return (
            best_match.get("id"),
            best_match.get("full_name")
            or best_match.get("name")
            or best_match.get("title"),
            best_text,
        )

    return None, None, None

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

    # تبدیل جداکننده‌های اعشاری پول به نقطه
    text = text.replace("/", ".")
    text = text.replace("٫", ".")
    text = text.replace(",", ".")
    text = text.replace("٬", ".")

    # حذف علائم اضافی
    text = re.sub(r"[^\w\s\u0600-\u06FF\-\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str):
    text_n = normalize_text(text)
    if not text_n:
        return []
    return [tok for tok in text_n.split() if tok]


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


def parse_persian_number(text: str, max_value=None):
    """
    Persian number words to int.

    Examples:
    - "چهل و پنج" -> 45
    - "دویست و چهل و پنج" -> 245
    - "هزار و دویست و پنجاه" -> 1250
    """

    text_n = normalize_text(text)

    if not text_n:
        return None

    # اگر خودش عدد دیجیتالی بود
    digit_match = re.search(r"\d+", text_n)
    if digit_match:
        value = int(digit_match.group(0))

        if max_value is None or value <= max_value:
            return value

        return None

    parts = [
        p.strip()
        for p in re.split(r"\s+و\s+|\s+", text_n)
        if p.strip()
    ]

    total = 0
    current = 0
    found = False

    for part in parts:
        value = PERSIAN_NUMBER_WORDS.get(part)

        if value is None:
            continue

        found = True

        if value == 1000:
            if current == 0:
                current = 1

            total += current * 1000
            current = 0
        else:
            current += value

    total += current

    if not found:
        return None

    if max_value is not None and total > max_value:
        return None

    return total


def parse_persian_number_under_100(text: str):
    return parse_persian_number(text, max_value=99)

def parse_number_phrase_mixed(text: str, max_value=None):
    """
    Parse either digit number or Persian number words.

    Examples:
    - "25" -> 25
    - "۲۵" -> 25
    - "بیست و پنج" -> 25
    - "سی و شش" -> 36
    """

    text_n = normalize_text(text)

    if not text_n:
        return None

    digit_match = re.search(r"\d+", text_n)
    if digit_match:
        value = int(digit_match.group(0))

        if max_value is None or value <= max_value:
            return value

        return None

    return parse_persian_number(text_n, max_value=max_value)

def extract_price_local(text: str):
    """
    Extract price locally, including numeric and Persian-word dollars/cents.

    Examples:
    - "۲۶۸ دلار و ۴۸ سنت" -> 268.48
    - "۲۴۸ دلار و چهل و پنج سنت" -> 248.45
    - "دویست و چهل و پنج دلار و ۴۵ سنت" -> 245.45
    - "دویست و چهل و پنج دلار و چهل و پنج سنت" -> 245.45
    - "268 dollars and 48 cents" -> 268.48
    """

    text_n = normalize_text(text)

    if not text_n:
        return None, None

    currency_words = r"(?:دلار|dollar|dollars|cad|usd)"
    cent_words = r"(?:سنت|cent|cents)"

    decimal_words = r"(?:ممیز|نقطه|point|dot)"

    # 0) عدد/کلمه + ممیز/نقطه/point + عدد/کلمه
    # Examples:
    # - "25 ممیز 36"
    # - "بیست و پنج ممیز سی و شش"
    # - "بیست و پنج نقطه سی و شش دلار"
    # - "25 point 36"
    number_part_re = rf"(?:\d+|{PERSIAN_NUMBER_PHRASE_RE})"

    pattern = (
        r"(" + number_part_re + r")\s*"
        + decimal_words +
        r"\s*"
        r"(" + number_part_re + r")"
        r"(?:\s*"

        + currency_words +
        r")?"
    )

    m = re.search(pattern, text_n)
    if m:
        whole_part = parse_number_phrase_mixed(m.group(1), max_value=999999)
        decimal_part = parse_number_phrase_mixed(m.group(2), max_value=99)

        if whole_part is not None and decimal_part is not None:
            # اگر کاربر گفت "پنج" بعد از ممیز، یعنی .05 یا .5؟
            # برای پول بهتر است یک رقمی را سنت حساب کنیم: 25 point 5 => 25.05
            # اگر می‌خواهی 25.5 شود، این بخش را تغییر بده.
            decimal_text = str(decimal_part).zfill(2)

            return float(f"{whole_part}.{decimal_text}"), m.group(0)
        
    # 1) عددی دلار + عددی سنت:
    # 248 دلار و 45 سنت
    pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        + currency_words +
        r"\s*(?:و|and)?\s*"
        r"(\d{1,2})\s*"
        + cent_words
    )

    m = re.search(pattern, text_n)
    if m:
        dollars = float(m.group(1))
        cents = int(m.group(2))

        if 0 <= cents <= 99:
            return dollars + cents / 100, m.group(0)

    # 2) عددی دلار + سنت نوشتاری:
    # 248 دلار و چهل و پنج سنت
    pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        + currency_words +
        r"\s*(?:و|and)?\s*"
        r"([\u0600-\u06FF\s]+?)\s*"
        + cent_words
    )

    m = re.search(pattern, text_n)
    if m:
        dollars = float(m.group(1))
        cents = parse_persian_number(m.group(2), max_value=99)

        if cents is not None:
            return dollars + cents / 100, m.group(0)

    # 3) دلار نوشتاری + عددی سنت:
    # دویست و چهل و پنج دلار و 45 سنت

    pattern = (
        r"(" + PERSIAN_NUMBER_PHRASE_RE + r")\s*"
        + currency_words +
        r"\s*(?:و|and)?\s*"
        r"(\d{1,2})\s*"
        + cent_words
    )

    m = re.search(pattern, text_n)
    if m:
        dollars = parse_persian_number(m.group(1), max_value=999999)
        cents = int(m.group(2))

        if dollars is not None and 0 <= cents <= 99:
            return dollars + cents / 100, m.group(0)

    # 4) دلار نوشتاری + سنت نوشتاری:
    # دویست و چهل و پنج دلار و چهل و پنج سنت

    pattern = (
        r"(" + PERSIAN_NUMBER_PHRASE_RE + r")\s*"
        + currency_words +
        r"\s*(?:و|and)?\s*"
        r"(" + PERSIAN_NUMBER_PHRASE_RE + r")\s*"
        + cent_words
    )

    m = re.search(pattern, text_n)
    if m:
        dollars = parse_persian_number(m.group(1), max_value=999999)
        cents = parse_persian_number(m.group(2), max_value=99)

        if dollars is not None and cents is not None:
            return dollars + cents / 100, m.group(0)

    # 5) عدد اعشاری مستقیم: 268.48
    decimal_match = re.search(r"\d+\.\d+", text_n)
    if decimal_match:
        return float(decimal_match.group(0)), decimal_match.group(0)

    # 6) عدد ساده: 268
    number_match = re.search(r"\d+", text_n)
    if number_match:
        return float(number_match.group(0)), number_match.group(0)

    # 7) فقط دلار نوشتاری بدون سنت:
    # دویست و چهل و پنج دلار
    pattern = r"(" + PERSIAN_NUMBER_PHRASE_RE + r")\s*" + currency_words

    m = re.search(pattern, text_n)
    if m:
        dollars = parse_persian_number(m.group(1), max_value=999999)

        if dollars is not None:
            return float(dollars), m.group(0)

    return None, None

def normalize_voice_money_text(text: str):
    """
    Normalize common STT money outputs before showing in TextField.

    Examples:
    - "شیر 14 دلار و 53" -> "شیر 14.53"
    - "شیر ۱۴ دلار و ۵۳" -> "شیر 14.53"
    - "شیر 14 دلار و 53 سنت" -> "شیر 14.53"
    - "coffee 14 dollars and 53" -> "coffee 14.53"
    """

    text_n = normalize_text(text)

    if not text_n:
        return text

    currency_words = r"(?:دلار|dollar|dollars|cad|usd)"
    cent_words = r"(?:سنت|cent|cents)"

    # عدد دلار + و/and + عدد سنت، با یا بدون کلمه سنت
    pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        + currency_words +
        r"\s*(?:و|and)\s*"
        r"(\d{1,2})"
        r"(?:\s*"
        + cent_words +
        r")?"
    )

    def repl(m):
        dollars = float(m.group(1))
        cents = int(m.group(2))

        if not (0 <= cents <= 99):
            return m.group(0)

        value = dollars + cents / 100

        if value.is_integer():
            return str(int(value))

        return f"{value:.2f}".rstrip("0").rstrip(".")

    text_n = re.sub(pattern, repl, text_n)

    # اگر فقط عدد فارسی/عربی داخل متن بوده، normalize_text خودش تبدیلش کرده
    text_n = re.sub(r"\s+", " ", text_n).strip()

    return text_n

def normalize_price_phrase_in_text(text: str):
    """
    Replace spoken/written price phrase with numeric decimal price.

    Example:
    - "ناهار بیست و پنج دلار و ۳۶ سنت"
      -> "ناهار 25.36"

    - "coffee 4 dollars and 75 cents"
      -> "coffee 4.75"
    """

    price, matched_price_text = extract_price_local(text)

    if price is None or not matched_price_text:
        return text, price, matched_price_text

    text_n = normalize_text(text)
    matched_n = normalize_text(matched_price_text)

    if isinstance(price, float) and price.is_integer():
        price_text = str(int(price))
    else:
        price_text = f"{float(price):.2f}".rstrip("0").rstrip(".")

    normalized_text = text_n.replace(matched_n, price_text, 1)
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()

    return normalized_text, price, matched_price_text

def detect_transaction_type_local(text: str) -> str:
    text_n = normalize_text(text)

    refund_words = [
        "refund",
        "refunded",
        "return",
        "returned",
        "cashback",
        "chargeback",
        "reversal",

        "مرجوع",
        "استرداد",
        "بازپرداخت",
        "پس داد",
        "برگشت پول",
        "پول برگشت",
        "برگردوندم",
        "برگرداندم",
        "ریترن",
        "ریفاند",
        "رفاند",
    ]

    income_words = [
        "salary",
        "income",
        "deposit",
        "received",
        "paycheck",

        "حقوق",
        "درامد",
        "درآمد",
        "واریز شد",
        "واریز",
        "دریافت کردم",
        "دریافت",
        "پول گرفتم",
    ]

    # transfer فقط وقتی دو طرف حساب مشخص باشد، نه فقط "از حساب"
    transfer_patterns = [
        "از حساب به حساب",
        "از کارت به کارت",
        "بین حساب",
        "بین حسابها",
        "بین حساب ها",
        "انتقال دادم",
        "منتقل کردم",
        "جابجا کردم",
        "جا به جا کردم",
        "transfer between",
        "transfer from",
    ]

    for w in refund_words:
        if normalize_text(w) in text_n:
            return "refund"

    for w in transfer_patterns:
        if normalize_text(w) in text_n:
            return "transfer"

    for w in income_words:
        if normalize_text(w) in text_n:
            return "income"

    return "expense"


def normalize_price_sign_by_type(price, transaction_type="expense"):
    if price is None:
        return None

    try:
        amount = float(price)
    except Exception:
        return None

    tx = (transaction_type or "expense").strip().lower()

    negative_types = {
        "refund",
        "return",
        "returned",
        "cashback",
        "chargeback",
        "reversal",
        "money_back",
    }

    if tx in negative_types:
        amount = -abs(amount)
    else:
        amount = abs(amount)

    if amount.is_integer():
        amount = int(amount)

    return amount



def try_fast_parse_expense(text, members=None):
    """
    Fast local parser for simple expense sentences.

    Handles:
    - "مبل خریدم 200 دلار"
    - "ناهار ۲۶۸ دلار و ۴۸ سنت"
    - "ناهار ۲۴۸ دلار و چهل و پنج سنت"
    - "ناهار دویست و چهل و پنج دلار و ۴۵ سنت"
    - "ناهار بیست و پنج دلار و ۳۶ سنت"
    - "coffee 4 dollars and 75 cents"
    """

    text_n = normalize_text(text)

    price, matched_price_text = extract_price_local(text_n)

    if price is None:
        return None

    member_id, member_name, matched_member_text = extract_member_by_known_members(
        text_n,
        members,
    )

    # نسخه‌ای از متن که عبارت قیمت داخلش به عدد تبدیل شده
    text_with_numeric_price, _, _ = normalize_price_phrase_in_text(text_n)

    title = text_with_numeric_price

    # حذف قیمت عددی‌شده از title
    if isinstance(price, float) and price.is_integer():
        price_text = str(int(price))
    else:
        price_text = f"{float(price):.2f}".rstrip("0").rstrip(".")

    title = title.replace(price_text, " ")

    # حذف عبارت قیمت اصلی هم برای اطمینان
    if matched_price_text:
        title = title.replace(normalize_text(matched_price_text), " ")

    # اگر چیزی باقی مانده بود، عددهای تنها را هم حذف کن
    title = re.sub(r"\d+(?:\.\d+)?", " ", title)

    if matched_member_text:
        title = re.sub(
            rf"(^|\s){re.escape(normalize_text(matched_member_text))}($|\s)",
            " ",
            title,
        )

    remove_words = [
        # currency
        "دلار",
        "سنت",
        "تومان",
        "ریال",
        "dollar",
        "dollars",
        "cent",
        "cents",
        "usd",
        "cad",

        # connectors
        "و",
        "and",

        # normal expense verbs
        "خریدم",
        "خرید کردم",
        "خرید",
        "پرداخت کردم",
        "پرداخت",
        "دادم",
        "برای",
        "واسه",
        "رو",
        "را",

        # refund / return words
        "ریترن کردم",
        "ریترن شد",
        "ریترن",
        "مرجوع کردم",
        "مرجوع شد",
        "مرجوع",
        "پس دادم",
        "پس داد",
        "برگردوندم",
        "برگرداندم",
        "استرداد",
        "بازپرداخت",
        "ریفاند",
        "رفاند",
        "refund",
        "refunded",
        "return",
        "returned",
        "cashback",
    ]

    for w in remove_words:
        title = title.replace(normalize_text(w), " ")

    title = re.sub(r"\s+", " ", title).strip()

    if not title:
        return None

    transaction_type = detect_transaction_type_local(text)

    return {
        "title": title,
        "price": price,
        "date": None,
        "member_id": member_id,
        "member_name": member_name,
        "account_name": None,
        "transaction_type": transaction_type,
        "normalized_text": text_with_numeric_price,
    }
    
    

def fallback_result(text):
    return {
        "title": text,
        "price": None,
        "date": None,
        "member_id": None,
        "member_name": None,
        "account_name": None,
        "transaction_type": "expense",
        "category_id": None,
        "category_title": None,
        "matched": False,
        "suggestions": [],
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
                    "source": "hazineha_keyword_exact",
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
    total_t0 = perf_log("RESOLVE_CATEGORY_FROM_TITLE", extra=f"title={title!r}")

    t0 = perf_log("NORMALIZE_CATEGORY_TITLE")
    title_n = normalize_text(title)
    perf_log("NORMALIZE_CATEGORY_TITLE", t0, extra=f"title_n={title_n!r}")

    # 1) learning exact
    t0 = perf_log("FIND_CATEGORY_LEARNING_EXACT_DB")
    exact_learning = find_category_learning_exact_cached(title_n)
    perf_log(
        "FIND_CATEGORY_LEARNING_EXACT_DB",
        t0,
        extra=f"matched={bool(exact_learning)}",
    )

    if exact_learning and exact_learning.get("category_id"):
        result = {
            "category_id": exact_learning["category_id"],
            "category_title": exact_learning.get("category_title"),
            "matched": True,
            "suggestions": [],
            "source": "learning_exact",
        }

        perf_log(
            "RESOLVE_CATEGORY_FROM_TITLE_TOTAL",
            total_t0,
            extra=f"source=learning_exact result={result}",
        )
        return result

    # 2) load categories
    t0 = perf_log("LOAD_LEAF_HAZINEHA_DB")
    categories = load_leaf_hazineha_cached()
    perf_log("LOAD_LEAF_HAZINEHA_DB", t0, extra=f"count={len(categories)}")

    # 3) exact keyword
    t0 = perf_log("FIND_EXACT_KEYWORD_MATCH")
    exact_keyword_match = find_exact_keyword_match(title_n, categories)
    perf_log(
        "FIND_EXACT_KEYWORD_MATCH",
        t0,
        extra=f"matched={bool(exact_keyword_match)}",
    )

    if exact_keyword_match:
        perf_log(
            "RESOLVE_CATEGORY_FROM_TITLE_TOTAL",
            total_t0,
            extra=f"source=keyword_exact result={exact_keyword_match}",
        )
        return exact_keyword_match

    # 4) shortlist
    t0 = perf_log("SHORTLIST_CATEGORIES")
    shortlisted = shortlist_categories(title_n, categories, limit=3)
    perf_log("SHORTLIST_CATEGORIES", t0, extra=f"count={len(shortlisted)}")

    if shortlisted:
        if len(shortlisted) == 1:
            cat = shortlisted[0]
            result = {
                "category_id": cat["id"],
                "category_title": cat["title"],
                "matched": True,
                "suggestions": [],
                "source": "hazineha_keywords",
            }

            perf_log(
                "RESOLVE_CATEGORY_FROM_TITLE_TOTAL",
                total_t0,
                extra=f"source=single_keyword result={result}",
            )
            return result

        result = {
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

        perf_log(
            "RESOLVE_CATEGORY_FROM_TITLE_TOTAL",
            total_t0,
            extra=f"source=suggestions count={len(result['suggestions'])}",
        )
        return result

    result = {
        "category_id": None,
        "category_title": None,
        "matched": False,
        "suggestions": [],
    }

    perf_log("RESOLVE_CATEGORY_FROM_TITLE_TOTAL", total_t0, extra="source=no_match")
    return result


def resolve_by_learning_embedding(title_n: str):
    total_t0 = perf_log("RESOLVE_BY_LEARNING_EMBEDDING", extra=f"title_n={title_n!r}")

    t0 = perf_log("GET_EMBEDDING_FOR_CATEGORY")
    embedding_vector = get_embedding(title_n)
    perf_log(
        "GET_EMBEDDING_FOR_CATEGORY",
        t0,
        extra=f"has_vector={bool(embedding_vector)}",
    )

    if not embedding_vector:
        perf_log("RESOLVE_BY_LEARNING_EMBEDDING_TOTAL", total_t0, extra="no_vector")
        return None

    t0 = perf_log("MATCH_CATEGORY_LEARNING_BY_EMBEDDING_DB")
    learning_match = match_category_learning_by_embedding(
        embedding_vector,
        threshold=0.60,
    )
    perf_log(
        "MATCH_CATEGORY_LEARNING_BY_EMBEDDING_DB",
        t0,
        extra=f"matched={bool(learning_match)}",
    )

    if learning_match and learning_match.get("category_id"):
        result = {
            "category_id": learning_match["category_id"],
            "category_title": learning_match.get("category_title"),
            "matched": True,
            "suggestions": [],
            "source": "learning_embedding",
        }

        perf_log(
            "RESOLVE_BY_LEARNING_EMBEDDING_TOTAL",
            total_t0,
            extra=f"result={result}",
        )
        return result

    perf_log("RESOLVE_BY_LEARNING_EMBEDDING_TOTAL", total_t0, extra="no_match")
    return None


def parse_expense(text, members=None):
    total_t0 = perf_log("PARSE_EXPENSE", extra=f"text={text!r}")

    result = fallback_result(text)

    try:
        t0 = perf_log("CHECK_OPENAI_AVAILABLE")
        openai_ok = is_openai_available()
        perf_log("CHECK_OPENAI_AVAILABLE", t0, extra=f"available={openai_ok}")

        t0 = perf_log("TRY_FAST_PARSE")
        extracted = try_fast_parse_expense(text, members=members)
        perf_log("TRY_FAST_PARSE", t0, extra=f"extracted={extracted}")

        if not extracted and openai_ok:
            t0 = perf_log("EXTRACT_FIELDS_WITH_OPENAI")
            extracted = extract_expense_fields_with_openai(text)
            perf_log("EXTRACT_FIELDS_WITH_OPENAI", t0, extra=f"extracted={extracted}")

        if not extracted:
            perf_log("PARSE_EXPENSE_TOTAL", total_t0, extra="fallback_no_extracted")
            return result

        t0 = perf_log("NORMALIZE_EXTRACTED_FIELDS")

        title = (extracted.get("title") or text).strip()

        transaction_type = (
            extracted.get("transaction_type")
            or detect_transaction_type_local(text)
            or "expense"
        )

        price = normalize_price_sign_by_type(
            extracted.get("price"),
            transaction_type,
        )

        date_value = extracted.get("date")
        member_name = extracted.get("member_name")
        account_name = extracted.get("account_name")
        member_id = extracted.get("member_id")

        perf_log(
            "NORMALIZE_EXTRACTED_FIELDS",
            t0,
            extra=(
                f"title={title!r} price={price} date={date_value} "
                f"member={member_name} account={account_name}"
            ),
        )

        t0 = perf_log("RESOLVE_CATEGORY")
        category_result = resolve_category_from_title(title)
        perf_log(
            "RESOLVE_CATEGORY",
            t0,
            extra=(
                f"matched={category_result.get('matched')} "
                f"source={category_result.get('source')} "
                f"suggestions={len(category_result.get('suggestions') or [])}"
            ),
        )

        final_result = {
            "title": title,
            "price": price,
            "date": date_value,
            "member_name": member_name,
            "member_id": member_id,
            "account_name": account_name,
            "transaction_type": transaction_type,
            "category_id": category_result.get("category_id"),
            "category_title": category_result.get("category_title"),
            "matched": category_result.get("matched", False),
            "suggestions": category_result.get("suggestions", []),
                # متن اصلاح‌شده برای ذخیره در DB
            "normalized_text": extracted.get("normalized_text"),
        }

        perf_log("PARSE_EXPENSE_TOTAL", total_t0, extra=f"final={final_result}")
        return final_result

    except Exception as e:
        print("Parser error:", type(e).__name__, e, flush=True)
        perf_log("PARSE_EXPENSE_ERROR_TOTAL", total_t0)
        return result