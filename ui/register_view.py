import flet as ft

from services.supabase_service import register_user
from services.utils import hash_password


def register_view(page: ft.Page):
    username = ft.TextField(label="Username")
    name = ft.TextField(label="Name")
    family = ft.TextField(label="Family")
    birthdate = ft.TextField(label="Birthdate (YYYY-MM-DD)")
    password = ft.TextField(label="Password", password=True)

    def register(e):
        try:
            hashed = hash_password(password.value)

            register_user({
                "username": username.value,
                "password_hash": hashed,
                "name": name.value,
                "family": family.value,
                "birthdate": birthdate.value
            })

            page.go("/login")

        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
            page.snack_bar.open = True
            page.update()

    return ft.View(
        route="/register",
        controls=[
            ft.Text("Register", size=25),
            username,
            name,
            family,
            birthdate,
            password,
            ft.ElevatedButton("Create Account", on_click=register),
            ft.TextButton("Back", on_click=lambda e: page.go("/login")),
        ],
    )