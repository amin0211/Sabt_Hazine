from services.supabase_service import supabase


SESSION_KEYS = [
    "access_token",
    "refresh_token",
    "user_id",
    "user_email",
    "current_user_email",
    "username",
    "name",
    "family",
    "lang",
    "language_id",
    "timezone",
    "current_workspace_id",
    "root_hazine_id",
    "root_hazine_title",
]


async def clear_session_storage(page):
    """
    فقط برای logout واقعی استفاده شود.
    داخل restore_session_from_storage صدا زده نشود.
    """
    for key in SESSION_KEYS:
        try:
            await page.shared_preferences.remove(key)
        except Exception as ex:
            print(f"CLEAR SESSION ERROR for {key}:", ex, flush=True)

    try:
        if isinstance(page.data, dict):
            page.data["user"] = None
            page.data.pop("user_id", None)
            page.data.pop("user_email", None)
            page.data.pop("current_user_email", None)
    except Exception as ex:
        print("CLEAR PAGE DATA ERROR:", ex, flush=True)


async def restore_session_from_storage(page):
    """
    تلاش برای restore کردن session از shared_preferences.

    قانون مهم:
    اگر restore شکست خورد، tokenها را پاک نکن.
    چون ممکن است خطای موقت اینترنت، Supabase، یا refresh باشد.
    فقط logout حق پاک کردن tokenها را دارد.
    """
    try:
        page.data = page.data or {}

        access_token = await page.shared_preferences.get("access_token")
        refresh_token = await page.shared_preferences.get("refresh_token")

        print(
            "[RESTORE SESSION] tokens:",
            "access=", bool(access_token),
            "refresh=", bool(refresh_token),
            flush=True,
        )

        if not access_token or not refresh_token:
            print("[RESTORE SESSION] no tokens found", flush=True)
            return None

        # 1) Restore Supabase session
        try:
            res = supabase.auth.set_session(access_token, refresh_token)
            print("[RESTORE SESSION] set_session ok", flush=True)

        except Exception as ex:
            print("RESTORE SESSION set_session error:", ex, flush=True)
            print("[RESTORE SESSION] keeping stored tokens for next retry", flush=True)
            return None

        user = None
        session = None

        if res:
            user = getattr(res, "user", None)
            session = getattr(res, "session", None)

        # 2) اگر set_session مستقیم user نداد، get_user را امتحان کن
        if not user:
            try:
                user_res = supabase.auth.get_user()
                user = user_res.user if user_res and user_res.user else None
                print("[RESTORE SESSION] get_user user=", bool(user), flush=True)

            except Exception as ex:
                print("RESTORE SESSION get_user error:", ex, flush=True)
                print("[RESTORE SESSION] keeping stored tokens for next retry", flush=True)
                return None

        if not user:
            print("[RESTORE SESSION] no user after restore", flush=True)
            print("[RESTORE SESSION] keeping stored tokens for next retry", flush=True)
            return None

        # 3) اگر Supabase token جدید داد، ذخیره کن
        if session:
            new_access_token = getattr(session, "access_token", None)
            new_refresh_token = getattr(session, "refresh_token", None)

            if new_access_token:
                await page.shared_preferences.set("access_token", new_access_token)

            if new_refresh_token:
                await page.shared_preferences.set("refresh_token", new_refresh_token)

            print("[RESTORE SESSION] refreshed tokens saved", flush=True)

        # 4) ذخیره runtime/cache
        user_email = getattr(user, "email", None) or ""

        await page.shared_preferences.set("user_id", user.id)
        await page.shared_preferences.set("user_email", user_email)
        await page.shared_preferences.set("current_user_email", user_email)

        page.data["user"] = user
        page.data["user_id"] = user.id
        page.data["user_email"] = user_email
        page.data["current_user_email"] = user_email

        print(
            "[RESTORE SESSION] success:",
            user.id,
            user_email,
            flush=True,
        )

        return user

    except Exception as ex:
        print("RESTORE SESSION ERROR:", ex, flush=True)
        print("[RESTORE SESSION] unexpected error; keeping stored tokens", flush=True)
        return None