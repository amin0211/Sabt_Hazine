import flet as ft
import json

from services.supabase_service import get_user_by_username
from services.utils import check_password


def login_view(page: ft.Page):
    username = ft.TextField(label="Username")
    password = ft.TextField(label="Password", password=True)

    def login(e):
        try:
            users = get_user_by_username(username.value)

            page.go("/sabtehazine")
            # if users:
            #     user = users[0]
            #     with open("user.json", "w") as f:
            #         json.dump(user, f)
            #     page.go("/sabtehazine")


              

            #     # اگر خواستی پسورد هم چک شود این قسمت فعال بماند
            #     if check_password(password.value, user["password_hash"]):
            #         with open("user.json", "w") as f:
            #             json.dump(user, f)

            #         page.go("/sabtehazine")
            #     else:
            #         page.snack_bar = ft.SnackBar(ft.Text("Wrong password"))
            #         page.snack_bar.open = True
            #         page.update()

            # else:
            #     page.snack_bar = ft.SnackBar(ft.Text("User not found"))
            #     page.snack_bar.open = True
            #     page.update()

        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
            page.snack_bar.open = True
            page.update()

    return ft.View(
        route="/login",
        controls=[
            ft.Text("Login", size=25),
            username,
            password,
            ft.ElevatedButton("Login", on_click=login),
            ft.TextButton("Register", on_click=lambda e: page.go("/register")),
        ],
    )