from datetime import datetime, timedelta


def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = (text or "").lower()

    if "yesterday" in text or "دیروز" in text:
        return (datetime.now() - timedelta(days=1)).date().isoformat()

    if "today" in text or "امروز" in text:
        return datetime.now().date().isoformat()

    return datetime.now().date().isoformat()


def is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    return "@" in email and "." in email and len(email) >= 6