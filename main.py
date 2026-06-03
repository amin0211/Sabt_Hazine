# clear_hazineha_cache()
# flet clean
# flet build apk

# taskkill /f /im java.exe
# taskkill /f /im dart.exe
# taskkill /f /im flutter.bat

# rmdir /s /q build

# taskkill /F /IM python.exe
# python server.py
# curl http://127.0.0.1:10000
# https://github.com/amin0211/Sabt_Hazine.git
# pip install -r requirements.txt

# echo "# Sabt_Hazine" >> README.md
# git init
# git add README.md
# git commit -m "first commit"
# git branch -M main
# git remote add origin https://github.com/amin0211/Sabt_Hazine.git
# git push -u origin main

# git add .
# git commit -m "update project"
# git push

# adb uninstall com.flet.sabte_hazine
# adb shell pm list packages | findstr com.flet.sabte_hazine

import flet as ft
import asyncio
import os
import time


APP_BG = "#F5F7FB"
CARD = "#FFFFFF"
PRIMARY = "#4F46E5"
TEXT = "#111827"

theme = {
    "APP_BG": APP_BG,
    "CARD": CARD,
    "PRIMARY": PRIMARY,
    "TEXT": TEXT
}




def main(page: ft.Page):
    page.title = "Sabt Hazineha"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    page.window.maximized = False
    page.window.full_screen = False
    page.window.width = 420
    page.window.height = 800
    # page.window.center()

    if page.data is None:
        page.data = {}

    if "lang" not in page.data:
        page.data["lang"] = "fa"

    # page.rtl = (page.data["lang"] == "fa")

    async def apply_user_language():
        try:
            old_lang = page.data.get("lang")
            old_timezone = page.data.get("timezone")
            old_workspace_id = page.data.get("current_workspace_id")

            from services.supabase_service import get_my_profile_with_language

            profile = await asyncio.to_thread(get_my_profile_with_language)

            page.data = page.data or {}

            if not profile:
                return

            timezone = profile.get("timezone") or "America/Vancouver"
            workspace_id = profile.get("current_workspace_id")

            lang_data = profile.get("languages")

            if isinstance(lang_data, list) and lang_data:
                lang_data = lang_data[0]

            if lang_data:
                new_lang = lang_data.get("code", "fa")
                # is_rtl = bool(lang_data.get("is_rtl", new_lang == "fa"))
            else:
                new_lang = "fa"
                is_rtl = True

            page.data["lang"] = new_lang
            page.data["timezone"] = timezone
            page.data["current_workspace_id"] = workspace_id
            # page.rtl = is_rtl

            workspace_data = profile.get("workspaces")

            if isinstance(workspace_data, list) and workspace_data:
                workspace_data = workspace_data[0]

            root_hazine_id = None
            root_hazine_title = None

            if isinstance(workspace_data, dict):
                root_hazine_id = workspace_data.get("root_hazine_id")
                root_hazine_title = workspace_data.get("title")

            page.data["root_hazine_id"] = root_hazine_id
            page.data["root_hazine_title"] = root_hazine_title or "Uncategorized"

            if root_hazine_id:
                await page.shared_preferences.set("root_hazine_id", str(root_hazine_id))

            if root_hazine_title:
                await page.shared_preferences.set("root_hazine_title", root_hazine_title)
                
            await page.shared_preferences.set("lang", new_lang)
            await page.shared_preferences.set("timezone", timezone)

            if workspace_id:
                await page.shared_preferences.set("current_workspace_id", workspace_id)

            language_changed = old_lang and new_lang != old_lang
            timezone_changed = old_timezone and timezone != old_timezone
            workspace_changed = old_workspace_id and workspace_id != old_workspace_id

            if language_changed:
                page.data["sabtehazine_changed"] = True
                page.data["sabtehazine_loaded"] = False
                page.data.pop("sabtehazine_view_cache", None)

                if page.data.get("current_view") == "sabtehazine":
                    await render_view("sabtehazine")

        except Exception as ex:
            print("APPLY LANGUAGE ERROR:", ex, flush=True)
            
    def apply_bg(view: ft.View):
        view.bgcolor = APP_BG
        return view


    async def render_view(view_name: str):
        render_t0 = time.perf_counter()
        print(f"\n========== RENDER_VIEW START: {view_name} ==========", flush=True)

        page.views.clear()
        page.data = page.data or {}
        page.data["current_view"] = view_name

        user = page.data.get("user")
        logged_in = user is not None

        protected_views = [
            "main",
            "sabtehazine",
            "hazinaha_view",
            "GanttChart_view",
            "members",
            "profile",
            "accounts",
            "income",
            "fixed_expenses_view",
            "budget_view",
            "dashboard_view",
            "trend_view",
        ]

        if view_name in protected_views and not logged_in:
            view_name = "login"

        if view_name == "login":
            from ui.login_view import login_view

            view = login_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "register":
            from ui.register_view import register_view

            view = register_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "profile":
            from ui.profile_view import profile_view
            
            view = profile_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "subscription_view":
            from ui.subscription_view import subscription_view

            view = subscription_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "date_picker_test":
            from ui.date_picker_test_view import date_picker_test_view
            view = date_picker_test_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "main":
            from ui.main_view import main_view
            
            view = main_view(page, theme)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "workspaces_view":
            from ui.workspace_view import workspaces_view
            
            view = workspaces_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "hazinaha_view":
            from Hazineha import hazinaha_view

            view = hazinaha_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        
        elif view_name == "members":
            from ui.members_view import members_view
            
            view = members_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "accounts":
            from ui.accounts_view import accounts_view
            view = accounts_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "bank_reconcile_view":
            from ui.bank_reconcile_view import bank_reconcile_view
            view = bank_reconcile_view(page, theme)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "income":
            from ui.income_view import income_view
            view = income_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "fixed_expenses_view":
            from ui.fixed_expenses_view import fixed_expenses_view
            view = fixed_expenses_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "cost_report_view":
            from ui.cost_report_view import cost_report_view
            
            view = cost_report_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))
        
        elif view_name == "budget_view":
            from ui.budget_view import budget_view
            
            view = budget_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "trend_view":
            from ui.trend_view import trend_view

            view = trend_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "dashboard_view":
            from ui.dashboard_view import dashboard_view
            
            view = dashboard_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "sabtehazine":
            if page.data.get("sabtehazine_changed") or "sabtehazine_view_cache" not in page.data:
                t_import_all = time.perf_counter()

                t0 = time.perf_counter()
                from ui.sabte_hazine_ui import build_chat_ui
                t1 = time.perf_counter()
                print(f"[IMPORT SABTEH] ui.sabte_hazine_ui = {t1 - t0:.3f}s", flush=True)


                t0 = time.perf_counter()
                import services.supabase_service as supabase_service
                t1 = time.perf_counter()
                print(f"[IMPORT SABTEH] supabase_service = {t1 - t0:.3f}s", flush=True)

                # t0 = time.perf_counter()
                # from services.parser_service import parse_expense
                # t1 = time.perf_counter()
                # print(f"[IMPORT SABTEH] parser_service = {t1 - t0:.3f}s", flush=True)

                t0 = time.perf_counter()
                from services.utils import normalize_date
                t1 = time.perf_counter()
                print(f"[IMPORT SABTEH] utils = {t1 - t0:.3f}s", flush=True)

                t_import_end = time.perf_counter() 
                print(f"[RENDER SABTEH] imports total = {t_import_end - t_import_all:.3f}s", flush=True)

                t0 = time.perf_counter()
                view = build_chat_ui(
                    page=page,
                    supabase_service=supabase_service,
                    controller=None,
                    parse_expense_=None,
                    normalize_date=normalize_date,
                    theme=theme,
                )
                t1 = time.perf_counter()
                print(f"[RENDER SABTEH] build_chat_ui = {t1 - t0:.3f}s", flush=True)

                view.route = "/"
                page.data["sabtehazine_view_cache"] = apply_bg(view)
                page.data["sabtehazine_changed"] = False
            else:
                view = page.data["sabtehazine_view_cache"]

            view.route = "/"
            page.views.append(view)

        elif view_name == "GanttChart_view":
            from ui.GanttChart_view import GanttChart_view

            view = GanttChart_view(page, theme)
            view.route = "/"
            page.views.append(apply_bg(view))

        else:
            page.views.append(
                ft.View(
                    route="/",
                    controls=[
                        ft.Text("404 Page"),
                        ft.ElevatedButton(
                            "Go Login",
                            on_click=lambda e: page.app_go("login"),
                        ),
                    ],
                    bgcolor=APP_BG,
                )
            )
        before_update = time.perf_counter()
        print(f"[RENDER_VIEW] before page.update = {before_update - render_t0:.3f}s | view={view_name}", flush=True)

        page.update()

        render_t1 = time.perf_counter()
        print(f"[RENDER_VIEW] page.update time = {render_t1 - before_update:.3f}s", flush=True)
        print(f"========== RENDER_VIEW TOTAL: {view_name} = {render_t1 - render_t0:.3f}s ==========\n", flush=True)        

    async def app_go(view_name: str):
        page.data = page.data or {}
        page.data["current_view"] = view_name
        # await page.shared_preferences.set("last_view", view_name)
        await render_view(view_name)

    page.app_go = lambda view_name: page.run_task(app_go, view_name)


    def loading_view(text="Loading..."):
        return ft.View(
            route="/",
            bgcolor=APP_BG,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        controls=[
                            ft.ProgressRing(width=34, height=34, stroke_width=3),
                            ft.Text(text, size=13, color="#6B7280"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        tight=True,
                    ),
                )
            ],
        )

    def set_current_user_email(user=None):
        try:
            page.data = page.data or {}

            email = None

            if user:
                email = getattr(user, "email", None)

            if email:
                page.data["current_user_email"] = str(email)
                page.data["user_email"] = str(email)

                print(
                    "[CURRENT USER EMAIL SET]",
                    page.data.get("current_user_email"),
                    flush=True,
                )

        except Exception as ex:
            print("SET CURRENT USER EMAIL ERROR:", ex, flush=True)


    async def force_logout_to_login(reason=None):
        print("[FORCE LOGOUT START]", reason, flush=True)

        try:
            from services.supabase_service import sign_out_user
            await asyncio.to_thread(sign_out_user)
        except Exception as ex:
            print("[FORCE LOGOUT] sign_out error:", ex, flush=True)

        try:
            await page.shared_preferences.clear()
        except Exception as ex:
            print("[FORCE LOGOUT] shared_preferences clear error:", ex, flush=True)

        try:
            page.client_storage.clear()
        except Exception as ex:
            print("[FORCE LOGOUT] client_storage clear error:", ex, flush=True)

        page.data = {
            "lang": "fa",
            "user": None,
            "timezone": "America/Vancouver",
            "login_error_message": (
                reason.get("message")
                if isinstance(reason, dict)
                else "This account is not available."
            ),
        }

        try:
            page.views.clear()

            from ui.login_view import login_view

            view = login_view(page)
            view.route = "/"
            view.bgcolor = APP_BG

            page.views.append(view)
            page.update()

            print("[FORCE LOGOUT DONE] login rendered", flush=True)

        except Exception as ex:
            print("[FORCE LOGOUT RENDER LOGIN ERROR]", ex, flush=True)

            page.views.clear()
            page.views.append(
                ft.View(
                    route="/",
                    bgcolor=APP_BG,
                    controls=[
                        ft.Container(
                            expand=True,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
                                    ft.Text(
                                        "This account has been deleted or disabled.",
                                        color=ft.Colors.RED_400,
                                        size=14,
                                    ),
                                    ft.ElevatedButton(
                                        "Back to Login",
                                        on_click=lambda e: page.app_go("login"),
                                    ),
                                ],
                            ),
                        )
                    ],
                )
            )
            page.update()

    async def go_start():
        go_t0 = time.perf_counter()
        print("\n========== GO_START START ==========", flush=True)

        try:
            page.data = page.data or {}
            from services.auth_session import restore_session_from_storage

            t0 = time.perf_counter()
            user = await restore_session_from_storage(page)
            t1 = time.perf_counter()
            print(f"[GO_START 1] restore_session_from_storage = {t1 - t0:.3f}s | user={bool(user)}", flush=True)

            page.data["user"] = user
            set_current_user_email(user)
            if user:
                from services.supabase_service import is_current_user_allowed

                allowed = await asyncio.to_thread(is_current_user_allowed)

                print("[GO_START USER ALLOWED CHECK]", allowed, flush=True)

                if not allowed.get("ok"):
                    await force_logout_to_login(allowed)
                    return



            try:
                ws_id = await page.shared_preferences.get("current_workspace_id")
                tz = await page.shared_preferences.get("timezone")
                stored_lang = await page.shared_preferences.get("lang")
                root_hazine_id = await page.shared_preferences.get("root_hazine_id")
                if root_hazine_id:
                    page.data["root_hazine_id"] = root_hazine_id

                print(
                    f"[GO_START CACHE] current_workspace_id={ws_id} timezone={tz}",
                    flush=True,
                )

                if ws_id:
                    page.data["current_workspace_id"] = ws_id

                if tz:
                    page.data["timezone"] = tz
                else:
                    page.data["timezone"] = "America/Vancouver"

                if stored_lang:
                    page.data["lang"] = stored_lang
                else:
                    page.data["lang"] = page.data.get("lang") or "fa"

                # page.rtl = page.data["lang"] == "fa"

            except Exception as ex:
                print("LOAD SESSION CACHED DATA ERROR:", ex, flush=True)
                page.data["timezone"] = "America/Vancouver"
                            

            if user:
                t0 = time.perf_counter()
                page.data["lang"] = page.data.get("lang") or "fa"

                # page.run_task(apply_user_language)
                await apply_user_language()

                print(
                    "[GO_START ROOT AFTER APPLY]",
                    "workspace=", page.data.get("current_workspace_id"),
                    "root_hazine_id=", page.data.get("root_hazine_id"),
                    "root_hazine_title=", page.data.get("root_hazine_title"),
                    flush=True,
                )

                t1 = time.perf_counter()
                print(f"[GO_START 2] apply_user_language = {t1 - t0:.3f}s", flush=True)

                t0 = time.perf_counter()

                await render_view("sabtehazine")

                t1 = time.perf_counter()
                print(f"[GO_START 3] render_view sabtehazine = {t1 - t0:.3f}s", flush=True)
            else:
                page.data["lang"] = "fa"

                t0 = time.perf_counter()
                await render_view("login")
                t1 = time.perf_counter()
                print(f"[GO_START 3] render_view login = {t1 - t0:.3f}s", flush=True)

        except Exception as ex:
            print("GO_START ERROR:", ex, flush=True)
            page.data = page.data or {}
            page.data["user"] = None
            page.data["lang"] = "fa"

            t0 = time.perf_counter()
            await render_view("login")
            t1 = time.perf_counter()
            print(f"[GO_START ERROR FALLBACK] render_view login = {t1 - t0:.3f}s", flush=True)

        go_t1 = time.perf_counter()
        print(f"========== GO_START TOTAL = {go_t1 - go_t0:.3f}s ==========\n", flush=True)

    page.views.clear()
    page.views.append(loading_view("Preparing your workspace..."))
    page.update()

    page.run_task(go_start)

    page.title = "Sabt Hazineha"

    
# ft.app(
#     target=main,
#     view=ft.AppView.WEB_BROWSER,
#     host="0.0.0.0",
#     port=int(os.environ.get("PORT", 8080))
# )

ft.app(target=main)



