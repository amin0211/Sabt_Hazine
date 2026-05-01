from services.supabase_service import supabase


async def restore_session_from_storage(page):
    try:
        access_token = await page.shared_preferences.get("access_token")
        refresh_token = await page.shared_preferences.get("refresh_token")

        if not access_token or not refresh_token:
            print("RESTORE SESSION: no saved tokens")
            return None

        try:
            res = supabase.auth.set_session(access_token, refresh_token)

            if res and res.user:
                print("RESTORE SESSION: success with set_session")
                return res.user

        except Exception as ex:
            print("RESTORE SESSION set_session error:", ex)

        try:
            refresh_res = supabase.auth.refresh_session()

            if refresh_res and refresh_res.session:
                new_session = refresh_res.session
                new_user = refresh_res.user

                await page.shared_preferences.set("access_token", new_session.access_token)
                await page.shared_preferences.set("refresh_token", new_session.refresh_token)

                print("RESTORE SESSION: success with refresh_session")
                return new_user

        except Exception as ex:
            print("RESTORE SESSION refresh_session error:", ex)

        try:
            user_res = supabase.auth.get_user()

            if user_res and user_res.user:
                print("RESTORE SESSION: success with get_user")
                return user_res.user

        except Exception as ex:
            print("RESTORE SESSION get_user error:", ex)

        print("RESTORE SESSION: failed")
        return None

    except Exception as ex:
        print("RESTORE SESSION ERROR:", ex)
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
        "lang",
    ]

    for key in keys:
        try:
            await page.shared_preferences.remove(key)
        except Exception as ex:
            print(f"CLEAR SESSION ERROR for {key}:", ex)