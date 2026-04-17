from datetime import datetime, timedelta
import hashlib


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password, hashed):
    return hashlib.sha256(password.encode()).hexdigest() == hashed


def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = text.lower()

    if "yesterday" in text or "دیروز" in text:
        return (datetime.now() - timedelta(days=1)).date().isoformat()

    if "today" in text or "امروز" in text:
        return datetime.now().date().isoformat()

    return datetime.now().date().isoformat()