from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

tz = ZoneInfo("America/Vancouver")
now = datetime.now(tz)

def normalize_date(date_str, text):
    if date_str:
        return date_str

    text = (text or "").lower()

    if "yesterday" in text or "دیروز" in text:
        return (now - timedelta(days=1)).date().isoformat()

    if "today" in text or "امروز" in text:
        return now.date().isoformat()

    return now.date().isoformat()


def is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    return "@" in email and "." in email and len(email) >= 6