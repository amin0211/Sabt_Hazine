# flet clean
# flet build apk 

# taskkill /f /im java.exe
# taskkill /f /im dart.exe
# taskkill /f /im flutter.bat

# rmdir /s /q build
# flet clean
# flet build apk 

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

# git remote add origin https://github.com/amin0211/Sabt_Hazine.git
# git branch -M main
# git push -u origin main

# adb uninstall com.flet.python
# adb shell pm list packages | findstr amin



import flet as ft

from ui.sabte_hazine_ui import build_chat_ui
import controllers.sabte_hazine_controller as controller
import services.supabase_service as supabase_service
import services.voice_service as voice_service  # اگر لازم شد
from services.parser_service import parse_expense
from services.utils import normalize_date

import flet as ft

from ui.login_view import login_view
from ui.register_view import register_view
from ui.main_view import main_view


APP_BG = "#F5F7FB"
CARD = "#FFFFFF"
PRIMARY = "#4F46E5"
TEXT = "#111827"

theme={
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

    page.window.width = 390
    page.window.height = 844
    page.window.center()
    
    def apply_bg(view: ft.View):
        view.bgcolor = APP_BG
        return view    

    def route_change(e):
        page.views.clear()
        if page.route == "/login":
            view = login_view(page)
            view.route = "/login"
            page.views.append(apply_bg(view))

        elif page.route == "/register":
            view = register_view(page)
            view.route = "/register"
            page.views.append(apply_bg(view))

        elif page.route == "/main":
            view = main_view(page,
                            theme
                            )
            view.route = "/main"
            page.views.append(apply_bg(view))

        elif page.route == "/sabtehazine":
            view = build_chat_ui(
                    page=page,
                    supabase_service=supabase_service,
                    controller=controller,
                    parse_expense_=parse_expense,
                    normalize_date=normalize_date, theme=theme)
            view.route = "/sabtehazine"
            page.views.append(apply_bg(view))


        else:
            page.views.append(
                ft.View(
                    route="/",
                    controls=[ft.Text("404 Page")]
                )
            )
        # page.views[-1].scroll = "auto"
        page.update()

    page.on_route_change = route_change
    page.go("/login")


ft.app(target=main)

