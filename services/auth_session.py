from services.supabase_service import set_session, get_current_user


async def restore_session_from_storage(page):
    try:
        access_token = await page.shared_preferences.get("access_token")
        refresh_token = await page.shared_preferences.get("refresh_token")

        if not access_token or not refresh_token:
            return None

        set_session(access_token, refresh_token)
        user = get_current_user()
        return user

    except Exception:
        return None


async def clear_session_storage(page):
    keys = [
        "access_token",
        "refresh_token",
        "user_id",
        "user_email",
        "username",
        "name",
        "family",
    ]

    for key in keys:
        try:
            await page.shared_preferences.remove(key)
        except Exception:
            pass