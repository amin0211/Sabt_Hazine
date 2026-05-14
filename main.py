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
from ui.trend_view import trend_view
from ui.cost_report_view import cost_report_view
from ui.workspace_view import workspaces_view
from ui.subscription_view import subscription_view



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


    async def render_view(view_name: str):

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
            "budget_view",
            "dashboard_view",
            "trend_view",
        ]

        if view_name in protected_views and not logged_in:
            view_name = "login"

        if view_name == "login":
            view = login_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "register":
            view = register_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "profile":
            view = profile_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "subscription_view":
            view = subscription_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "main":
            view = main_view(page, theme)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "workspaces_view":
            view = workspaces_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "hazinaha_view":
            view = hazinaha_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "members":
            view = members_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "accounts":
            view = accounts_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "income":
            view = income_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "cost_report_view":
            view = cost_report_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))
        
        elif view_name == "budget_view":
            view = budget_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "trend_view":
            view = trend_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "dashboard_view":
            view = dashboard_view(page)
            view.route = "/"
            page.views.append(apply_bg(view))

        elif view_name == "sabtehazine":
            if page.data.get("sabtehazine_changed") or "sabtehazine_view_cache" not in page.data:
                view = build_chat_ui(
                    page=page,
                    supabase_service=supabase_service,
                    controller=controller,
                    parse_expense_=parse_expense,
                    normalize_date=normalize_date,
                    theme=theme,
                )
                view.route = "/"
                page.data["sabtehazine_view_cache"] = apply_bg(view)
                page.data["sabtehazine_changed"] = False
            else:
                view = page.data["sabtehazine_view_cache"]

            view.route = "/"
            page.views.append(view)

        elif view_name == "GanttChart_view":
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

        page.update()

    async def app_go(view_name: str):
        page.data = page.data or {}
        page.data["current_view"] = view_name
        # await page.shared_preferences.set("last_view", view_name)
        await render_view(view_name)

    page.app_go = lambda view_name: page.run_task(app_go, view_name)


    # async def go_start():
        # page.data = page.data or {}
        # # await page.shared_preferences.remove("last_view")
        # user = await restore_session_from_storage(page)
        # page.data["user"] = user

        # if user:
        #     await apply_user_language()
            
        #     await render_view("sabtehazine")
        # else:
        #     page.data["lang"] = "fa"
        #     await render_view("login")

    async def go_start():
        try:

            page.data = page.data or {}

            user = await restore_session_from_storage(page)

            page.data["user"] = user

            if user:
                await apply_user_language()
                await render_view("sabtehazine")
            else:
                page.data["lang"] = "fa"
                await render_view("login")


        except Exception as ex:
            print("GO_START ERROR:", ex, flush=True)
            page.data = page.data or {}
            page.data["user"] = None
            page.data["lang"] = "fa"
            await render_view("login")
            
    # async def handle_route_change(e):
    #     page.views.clear()

    #     # user = await restore_session_from_storage(page)
    #     # logged_in = user is not None


    #     user = page.data.get("user")
    #     logged_in = user is not None

    #     page.data = page.data or {}

    #     if logged_in:
    #         await apply_user_language()
    #     else:
    #         saved_lang = await page.shared_preferences.get("lang")
    #         page.data["lang"] = saved_lang or page.data.get("lang", "fa")


    #     protected_routes = [
    #         "/main",
    #         "/sabtehazine",
    #         "/hazinaha_view",
    #         "/GanttChart_view",
    #         "/members",
    #         "/profile",
    #         "/accounts",
    #         "/income",
    #         "/budget_view",
    #         "/dashboard_view",
    #         "/trend_view",
    #     ]

    #     if page.route in protected_routes and not logged_in:
    #         page.go("/login")
    #         return
        
    #     if logged_in and page.route in protected_routes:
    #         await page.shared_preferences.set("last_route", page.route)


        
    #     if page.route == "/login":
    #         if logged_in:
    #             page.go("/sabtehazine")
    #             return
    #         view = login_view(page)
    #         view.route = "/login"
    #         page.views.append(apply_bg(view))

    #     elif page.route == "/register":
    #         view = register_view(page)
    #         view.route = "/register"
    #         page.views.append(apply_bg(view))

    #     elif page.route == "/profile":
    #         view = profile_view(page)
    #         view.route = "/profile"
    #         page.views.append(apply_bg(view))
                    
    #     elif page.route == "/main":
    #         view = main_view(page, theme)
    #         page.views.append(apply_bg(view))

    #     elif page.route == "/hazinaha_view":
    #         view = hazinaha_view(page)
    #         page.views.append(apply_bg(view))

    #     elif page.route == "/members":
    #         page.views.append(members_view(page))

    #     elif page.route == "/accounts":
    #         page.views.append(accounts_view(page))


    #     elif page.route == "/income":
    #         page.views.append(income_view(page))

    #     elif page.route == "/budget_view":
    #         page.views.clear()
    #         page.views.append(budget_view(page))

    #     elif page.route == "/trend_view":
    #         page.views.append(trend_view(page))

    #     elif page.route == "/dashboard_view":
    #         page.views.append(dashboard_view(page))


    #     elif page.route == "/sabtehazine":
    #         view = build_chat_ui(
    #             page=page,
    #             supabase_service=supabase_service,
    #             controller=controller,
    #             parse_expense_=parse_expense,
    #             normalize_date=normalize_date,
    #             theme=theme,
    #         )
    #         view.route = "/sabtehazine"
    #         page.views.append(apply_bg(view))

    #     elif page.route == "/GanttChart_view":
    #         view = GanttChart_view(page, theme)
    #         page.views.append(apply_bg(view))

    #     else:
    #         page.views.append(ft.View(route="/", controls=[ft.Text("404 Page")]))

    #     page.update()

    # def route_change(e):
    #     page.run_task(handle_route_change, e)

    # page.on_route_change = route_change

    page.run_task(go_start)

    page.title = "Sabt Hazineha"
    # page.add(ft.Text("Hello from Web"))


    
# ft.app(
#     target=main,
#     view=ft.AppView.WEB_BROWSER,
#     host="0.0.0.0",
#     port=int(os.environ.get("PORT", 8080))
# )

ft.app(target=main)