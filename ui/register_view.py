import flet as ft
import asyncio

from services.supabase_service import (
    sign_up_user,
    update_profile,
    # get_profile_by_username,
    copy_hazineha_template_for_user,
    get_languages,
)
from services.utils import is_valid_email


def register_view(page: ft.Page):
    page.data = page.data or {}

    email = ft.TextField(label="Email", width=320)

    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=320
    )

    confirm_password = ft.TextField(
        label="Confirm Password",
        password=True,
        can_reveal_password=True,
        width=320
    )

    username = ft.TextField(label="Username", width=320)
    name = ft.TextField(label="Name", width=320)
    family = ft.TextField(label="Family", width=320)

    birthdate = ft.TextField(
        label="Birthdate (YYYY-MM-DD)",
        hint_text="مثال: 2006-04-18",
        width=320
    )

    language_dropdown = ft.Dropdown(
        label="Language",
        width=320,
        options=[],
        value=None,
    )

    status_text = ft.Text("", color=ft.Colors.RED_400)

    def show_message(text, color=ft.Colors.RED_400):
        status_text.value = text
        status_text.color = color
        page.update()

    async def load_languages_async():
        try:
            rows = await asyncio.to_thread(get_languages)
            print("LANG ROWS =", rows)

            options = []
            saved_language_id = page.data.get("language_id")

            for row in rows or []:
                lang_id = row.get("id")
                lang_name = row.get("name")

                if lang_id is not None and lang_name:
                    options.append(
                        ft.dropdown.Option(
                            key=str(lang_id),
                            text=str(lang_name)
                        )
                    )

            language_dropdown.options = options

            if saved_language_id and any(opt.key == str(saved_language_id) for opt in options):
                language_dropdown.value = str(saved_language_id)
            elif options:
                language_dropdown.value = options[0].key

            page.update()

        except Exception as ex:
            print("LOAD LANGUAGES ERROR:", ex)

    async def language_change_async(e):
        selected_language_id = language_dropdown.value
        page.data["language_id"] = selected_language_id
        await page.shared_preferences.set("language_id", selected_language_id)
        page.update()

    def on_language_change(e):
        page.run_task(language_change_async, e)

    language_dropdown.on_change = on_language_change

    def register(e):
        try:
            em = (email.value or "").strip().lower()
            pwd = password.value or ""
            cpwd = confirm_password.value or ""
            uname = (username.value or "").strip()
            first_name = (name.value or "").strip()
            last_name = (family.value or "").strip()
            bdate = (birthdate.value or "").strip()
            selected_language_id = language_dropdown.value

            if not em or not pwd or not cpwd:
                show_message("Email, password and confirm password are required.")
                return

            if not is_valid_email(em):
                show_message("Invalid email format.")
                return

            if pwd != cpwd:
                show_message("Passwords do not match.")
                return

            if len(pwd) < 6:
                show_message("Password must be at least 6 characters.")
                return

            # existing_username = get_profile_by_username(uname)
            # if existing_username:
            #     show_message("Username already exists.")
            #     return

            auth_res = sign_up_user(em, pwd)
            user = auth_res.user
            # print(f"11 = {user}")

            if not user:
                show_message("Registration failed.")
                return

            update_profile(user.id, {
                "username": uname,
                "name": first_name,
                "family": last_name,
                "birthdate": bdate if bdate else None,
                "language_id": int(selected_language_id) if selected_language_id else None,
            })

            print("11111")
            copy_hazineha_template_for_user(user.id)

            page.go("/login")

        except Exception as ex:
            print("REGISTER ERROR:", ex)
            show_message(f"Error: {ex}")

    view = ft.View(
        route="/register",
        controls=[
            # ft.Container(height=10),
            ft.Text("Register", size=24, weight=ft.FontWeight.BOLD),

            # ft.Container(height=4),
            language_dropdown,

            ft.Container(height=4),
            email,
            password,
            confirm_password,
            # username,
            name,
            family,
            birthdate,

            # ft.Container(height=10),
            status_text,

            ft.Container(height=10),
            ft.ElevatedButton("Create Account", on_click=register, width=320),
            ft.TextButton("Back to Login", on_click=lambda e: page.go("/login")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.run_task(load_languages_async)

    return view