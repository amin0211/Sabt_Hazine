import flet as ft
from services.supabase_service import (
    sign_in_user,
    sign_out_user,
    get_my_profile_with_language,
    update_my_profile,
)
import asyncio
import time


def login_view(page: ft.Page):
    email = ft.TextField(
        label="Email",
        width=320,
        autofocus=True,
    )

    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=320,
    )

    status_text = ft.Text("", color=ft.Colors.RED_400)

    initial_error = None

    try:
        if isinstance(page.data, dict):
            initial_error = page.data.pop("login_error_message", None)
    except Exception:
        initial_error = None

    if initial_error:
        status_text.value = initial_error
        status_text.color = ft.Colors.RED_400

    def show_message(text, color=ft.Colors.RED_400):
        status_text.value = text
        status_text.color = color
        page.update()

    async def login_async(e):
        login_t0 = time.perf_counter()
        print("\n========== LOGIN START ==========", flush=True)

        try:
            # 0) Read inputs
            t0 = time.perf_counter()
            em = (email.value or "").strip().lower()
            pwd = password.value or ""
            t1 = time.perf_counter()
            print(f"[LOGIN 0] read inputs = {t1 - t0:.3f}s", flush=True)

            if not em or not pwd:
                show_message("Email and password are required.")
                return

            # 1) Sign in
            t0 = time.perf_counter()
            auth_res = await asyncio.to_thread(sign_in_user, em, pwd)
            t1 = time.perf_counter()
            print(f"[LOGIN 1] sign_in_user = {t1 - t0:.3f}s", flush=True)

            user = auth_res.user
            session = auth_res.session

            if not user or not session:
                show_message("Login failed.")
                return

            # 2) Read profile ONCE from DB
            t0 = time.perf_counter()
            profile = await asyncio.to_thread(get_my_profile_with_language)
            t1 = time.perf_counter()
            print(f"[LOGIN 2] get profile = {t1 - t0:.3f}s profile={bool(profile)}", flush=True)

            if not profile:
                await asyncio.to_thread(sign_out_user)

                try:
                    await page.shared_preferences.clear()
                except Exception:
                    pass

                try:
                    page.client_storage.clear()
                except Exception:
                    pass

                page.data = {}

                show_message("This account is not available.")
                return

            print(
                "[LOGIN PROFILE STATUS]",
                "is_active=", profile.get("is_active"),
                "status=", profile.get("status"),
                "deleted_at=", profile.get("deleted_at"),
                flush=True,
            )

            if (
                profile.get("is_active") is False
                or profile.get("status") == "deleted"
                or profile.get("deleted_at")
            ):
                await asyncio.to_thread(sign_out_user)

                try:
                    await page.shared_preferences.clear()
                except Exception:
                    pass

                try:
                    page.client_storage.clear()
                except Exception:
                    pass

                page.data = {}

                show_message("This account has been deleted or disabled.")
                return
            # 3) Save auth tokens
            t0 = time.perf_counter()

            await page.shared_preferences.set("access_token", session.access_token)
            await page.shared_preferences.set("refresh_token", session.refresh_token)
            await page.shared_preferences.set("user_id", user.id)
            await page.shared_preferences.set("user_email", user.email or "")
            await page.shared_preferences.set("current_user_email", user.email or "")

            t1 = time.perf_counter()
            print(f"[LOGIN 3] save auth shared_preferences = {t1 - t0:.3f}s", flush=True)

            # 4) Save profile fields locally
            if profile:
                t0 = time.perf_counter()

                lang_row = profile.get("languages") or {}
                lang_code = lang_row.get("code") or "fa"

                await page.shared_preferences.set(
                    "username",
                    profile.get("username") or "",
                )

                await page.shared_preferences.set(
                    "name",
                    profile.get("name") or "",
                )

                await page.shared_preferences.set(
                    "family",
                    profile.get("family") or "",
                )

                await page.shared_preferences.set(
                    "current_workspace_id",
                    profile.get("current_workspace_id") or "",
                )

                await page.shared_preferences.set(
                    "timezone",
                    profile.get("timezone") or "America/Vancouver",
                )

                await page.shared_preferences.set("lang", lang_code)

                if profile.get("language_id") is not None:
                    await page.shared_preferences.set(
                        "language_id",
                        str(profile.get("language_id")),
                    )

                t1 = time.perf_counter()
                print(f"[LOGIN 4] save profile shared_preferences = {t1 - t0:.3f}s", flush=True)
                
            # 5) Show success
            t0 = time.perf_counter()
            show_message("Login successful.", ft.Colors.GREEN_400)
            t1 = time.perf_counter()
            print(f"[LOGIN 5] show success message = {t1 - t0:.3f}s", flush=True)

            # 6) Save runtime page.data
            page.data = page.data or {}

            page.data["user"] = user
            page.data["user_id"] = user.id
            page.data["user_email"] = user.email or ""
            page.data["current_user_email"] = user.email or ""

            if profile:
                lang_row = profile.get("languages") or {}
                lang_code = lang_row.get("code") or "fa"

                page.data["lang"] = lang_code
                page.data["language_id"] = profile.get("language_id")

                page.data["username"] = profile.get("username") or ""
                page.data["name"] = profile.get("name") or ""
                page.data["family"] = profile.get("family") or ""

                page.data["current_workspace_id"] = profile.get("current_workspace_id")
                page.data["timezone"] = profile.get("timezone") or "America/Vancouver"

                workspace_data = profile.get("workspaces")

                if isinstance(workspace_data, list) and workspace_data:
                    workspace_data = workspace_data[0]

                if isinstance(workspace_data, dict):
                    root_hazine_id = workspace_data.get("root_hazine_id")
                    root_hazine_title = workspace_data.get("title") or "Uncategorized"

                    page.data["root_hazine_id"] = root_hazine_id
                    page.data["root_hazine_title"] = root_hazine_title

                    if root_hazine_id:
                        await page.shared_preferences.set(
                            "root_hazine_id",
                            str(root_hazine_id),
                        )

                    await page.shared_preferences.set(
                        "root_hazine_title",
                        root_hazine_title,
                    )

            else:
                page.data["lang"] = "fa"
                page.data["timezone"] = "America/Vancouver"

            # 7) Reset sabtehazine cache flags
            page.data["sabtehazine_changed"] = True
            page.data["sabtehazine_loaded"] = False
            page.data.pop("sabtehazine_view_cache", None)

            # اگر members cache داری، بعد از login بهتر است پاک شود
            # چون user/workspace عوض شده ممکن است members فرق کند
            page.data.pop("sabtehazine_members_cache", None)

            # 8) Always go to sabtehazine
            # اینجا دیگر کاربر را به profile نمی‌فرستیم
            t0 = time.perf_counter()
            page.app_go("sabtehazine")
            t1 = time.perf_counter()

            print(f"[LOGIN 6] page.app_go sabtehazine call = {t1 - t0:.3f}s", flush=True)

        except Exception as ex:
            print("LOGIN ERROR:", ex, flush=True)
            show_message(f"Error: {ex}")

        finally:
            login_t1 = time.perf_counter()
            print(f"========== LOGIN TOTAL = {login_t1 - login_t0:.3f}s ==========\n", flush=True)

    def login(e):
        page.run_task(login_async, e)

    password.on_submit = login

    return ft.View(
        route="/",
        controls=[
            ft.Container(height=30),
            ft.Text("Login", size=28, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            email,
            password,
            ft.Container(height=10),
            status_text,
            ft.Container(height=10),
            ft.ElevatedButton("Login", on_click=login, width=320),
            ft.TextButton("Register", on_click=lambda e: page.app_go("register")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )