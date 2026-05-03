import flet as ft

from services.supabase_service import sign_out_user
from services.auth_session import clear_session_storage


def main_view(page: ft.Page, theme):
    APP_BG = theme["APP_BG"]
    CARD = theme["CARD"]
    PRIMARY = theme["PRIMARY"]
    TEXT = theme["TEXT"]

    async def logout(e):
        try:
            sign_out_user()
        except Exception:
            pass

        clear_session_storage(page)
        page.app_go("login")

    return ft.View(
        route="/main",
        bgcolor=APP_BG,
        controls=[
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    [
                        ft.Text(
                            "Main Page",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT,
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "خوش آمدی",
                            size=16,
                            color=TEXT,
                        ),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            "Go to Expenses",
                            on_click=lambda e: page.app_go("sabtehazine"),
                            style=ft.ButtonStyle(
                                bgcolor=PRIMARY,
                                color="#FFFFFF",
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.padding.symmetric(horizontal=20, vertical=14),
                            ),
                        ),
                        ft.Container(height=10),
                        ft.OutlinedButton(
                            "Go to Categories",
                            on_click=lambda e: page.app_go("hazinaha_view"),
                        ),
                        ft.Container(height=20),
                        ft.TextButton(
                            "Logout",
                            on_click=logout,
                        ),
                    ],
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
            )
        ],
    )