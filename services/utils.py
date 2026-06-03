from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import re


class AppDate(date):
    def isoformat(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


DEFAULT_TIMEZONE = "America/Vancouver"


def get_app_timezone(page=None):
    """
    Timezone اصلی اپ.
    اول از page.data می‌خواند.
    اگر نبود، Vancouver را پیش‌فرض می‌گیرد.
    """
    try:
        if page and isinstance(page.data, dict):
            tz = page.data.get("timezone") or page.data.get("user_timezone")
            if tz:
                return str(tz)
    except Exception:
        pass

    return DEFAULT_TIMEZONE


def make_app_date(d):
    return AppDate(d.year, d.month, d.day)


def today_local(page=None):
    """
    امروز بر اساس timezone کاربر/اپ.
    """
    tz_name = get_app_timezone(page)
    today = datetime.now(ZoneInfo(tz_name)).date()
    return make_app_date(today)


def safe_picker_date(value, page=None):
    """
    خروجی همیشه AppDate است.

    نکته مهم:
    اگر Flet DatePicker روی Android/iOS مقدار timezone-aware datetime بدهد،
    باید آن را به timezone کاربر تبدیل کنیم.
    مثل دبی:
    2026-05-19 20:00 UTC -> 2026-05-20 Asia/Dubai
    """
    if value is None:
        return today_local(page)

    tz_name = get_app_timezone(page)
    user_tz = ZoneInfo(tz_name)

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            local_date = value.astimezone(user_tz).date()
            return make_app_date(local_date)

        return AppDate(value.year, value.month, value.day)

    if isinstance(value, date):
        return AppDate(value.year, value.month, value.day)

    if isinstance(value, str):
        return AppDate.fromisoformat(value[:10])

    return value


def local_date_iso(page=None, value=None):
    """
    خروجی فقط YYYY-MM-DD است.
    """
    d = safe_picker_date(value, page) if value else today_local(page)
    return d.isoformat()


def normalize_date(date_str=None, text="", page=None):
    """
    برای parser:
    اگر تاریخ مشخص بود همان را برمی‌گرداند.
    اگر نبود، today/yesterday را بر اساس timezone کاربر/اپ حساب می‌کند.
    """
    if date_str:
        return local_date_iso(page, date_str)

    text = (text or "").lower()
    today = today_local(page)

    if "yesterday" in text or "دیروز" in text:
        return make_app_date(today - timedelta(days=1)).isoformat()

    if "today" in text or "امروز" in text:
        return today.isoformat()

    return today.isoformat()


def is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))