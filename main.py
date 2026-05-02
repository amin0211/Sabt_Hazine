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
from flet import AppView
import asyncio
import os

from ui.sabte_hazine_ui import build_chat_ui
import controllers.sabte_hazine_controller as controller
import services.supabase_service as supabase_service
from services.supabase_service import get_my_profile_with_language

from services.parser_service import parse_expense
from services.utils import normalize_date

from ui.login_view import login_view
from ui.register_view import register_view
from ui.main_view import main_view

from Hazineha import hazinaha_view
from ui.GanttChart_view import GanttChart_view
from ui.profile_view import profile_view


from services.auth_session import restore_session_from_storage
from ui.members_view import members_view
from ui.accounts_view import accounts_view
from ui.income_view import income_view
from ui.budget_view import budget_view
from ui.dashboard_view import dashboard_view




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
    page.window.center()

    if page.data is None:
        page.data = {}

    if "lang" not in page.data:
        page.data["lang"] = "fa"

    # page.rtl = (page.data["lang"] == "fa")

    async def apply_user_language():
        try:
            profile = await asyncio.to_thread(get_my_profile_with_language)

            page.data = page.data or {}

            if not profile:
                page.data["lang"] = "fa"
                # page.rtl = True
                return

            lang_data = profile.get("languages")

            if isinstance(lang_data, list) and lang_data:
                lang_data = lang_data[0]

            if lang_data:
                page.data["lang"] = lang_data.get("code", "fa")
                # page.rtl = bool(lang_data.get("is_rtl", True))
            else:
                page.data["lang"] = "fa"
                # page.rtl = True

        except Exception as ex:
            print("APPLY LANGUAGE ERROR:", ex)
            page.data = page.data or {}
            page.data["lang"] = "fa"
            # page.rtl = True



    def apply_bg(view: ft.View):
        view.bgcolor = APP_BG
        return view

    async def go_start():
        user = await restore_session_from_storage(page)

        page.data = page.data or {}

        if user:
            await apply_user_language()
            page.go("/sabtehazine")
        else:
            page.data["lang"] = "fa"
            # page.rtl = True
            page.go("/login")
 
 
    async def handle_route_change(e):
        page.views.clear()

        user = await restore_session_from_storage(page)
        logged_in = user is not None
        
        page.data = page.data or {}

        if logged_in:
            await apply_user_language()
        else:
            saved_lang = await page.shared_preferences.get("lang")
            page.data["lang"] = saved_lang or page.data.get("lang", "fa")


        protected_routes = [
            "/main",
            "/sabtehazine",
            "/hazinaha_view",
            "/GanttChart_view",
            "/members",
            "/profile",
            "/accounts",
            "/income",
            "/budget_view",
            "/dashboard_view",
        ]

        if page.route in protected_routes and not logged_in:
            page.go("/login")
            return



        
        if page.route == "/login":
            if logged_in:
                page.go("/sabtehazine")
                return
            view = login_view(page)
            view.route = "/login"
            page.views.append(apply_bg(view))

        elif page.route == "/register":
            view = register_view(page)
            view.route = "/register"
            page.views.append(apply_bg(view))

        elif page.route == "/profile":
            view = profile_view(page)
            view.route = "/profile"
            page.views.append(apply_bg(view))
                    
        elif page.route == "/main":
            view = main_view(page, theme)
            page.views.append(apply_bg(view))

        elif page.route == "/hazinaha_view":
            view = hazinaha_view(page)
            page.views.append(apply_bg(view))

        elif page.route == "/members":
            page.views.append(members_view(page))

        elif page.route == "/accounts":
            page.views.append(accounts_view(page))


        elif page.route == "/income":
            page.views.append(income_view(page))

        elif page.route == "/budget_view":
            page.views.clear()
            page.views.append(budget_view(page))

        # elif page.route == "/budget_view":
        #     page.views.append(budget_view(page))

        elif page.route == "/dashboard_view":
            page.views.append(dashboard_view(page))


        elif page.route == "/sabtehazine":
            view = build_chat_ui(
                page=page,
                supabase_service=supabase_service,
                controller=controller,
                parse_expense_=parse_expense,
                normalize_date=normalize_date,
                theme=theme,
            )
            view.route = "/sabtehazine"
            page.views.append(apply_bg(view))

        elif page.route == "/GanttChart_view":
            view = GanttChart_view(page, theme)
            page.views.append(apply_bg(view))

        else:
            page.views.append(ft.View(route="/", controls=[ft.Text("404 Page")]))

        page.update()

    def route_change(e):
        page.run_task(handle_route_change, e)

    page.on_route_change = route_change
    page.run_task(go_start)

    page.title = "Sabt Hazineha"
    # page.add(ft.Text("Hello from Web"))



def main(page: ft.Page):
    # print("MAIN STARTED")
    page.title = "Sabt Hazineha"
    # page.add(ft.Text("Loading main app..."))
    # page.update()

ft.app(
    target=main,
    view=ft.AppView.WEB_BROWSER,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8080))
)


# port = int(os.environ.get("PORT", 8000))

# ft.app(
#     target=main,
#     view=AppView.WEB_BROWSER,
#     host="0.0.0.0",
#     port=port,
# )

# ft.app(target=main)