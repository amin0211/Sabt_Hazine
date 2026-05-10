import flet as ft
import asyncio

from services.supabase_service import (
    sign_up_user,
    update_profile,
    create_default_workspace_for_user,
    copy_hazineha_template_for_user,
    create_default_account_for_user,
    get_languages,
    delete_auth_user,
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

    create_btn = ft.ElevatedButton(
        content=ft.Text("Create Account"),
        on_click=None,
        width=320,
    )

    back_btn = ft.TextButton(
        content=ft.Text("Back to Login"),
        on_click=lambda e: page.app_go("login"),
    )

    def set_loading(is_loading: bool):
        create_btn.disabled = is_loading
        back_btn.disabled = is_loading

        if is_loading:
            status_text.value = "Creating account..."
            status_text.color = ft.Colors.BLUE_400
        else:
            status_text.value = ""

        page.update()

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

    async def register_async(e):

        user = None  # 👈 مهم

        try:
            em = (email.value or "").strip().lower()
            pwd = password.value or ""
            cpwd = confirm_password.value or ""

            first_name = (name.value or "").strip()
            last_name = (family.value or "").strip()
            bdate = (birthdate.value or "").strip()
            selected_language_id = language_dropdown.value
            # validation...
            print(em)
            set_loading(True)

            auth_res = await asyncio.to_thread(sign_up_user, em, pwd)
            user = auth_res.user

            if not user:
                raise Exception("Registration failed")

            # ✅ پروفایل
            await asyncio.to_thread(
                update_profile,
                user.id,
                {
                    "name": first_name,
                    "family": last_name,
                    "email": em,
                    "birthdate": bdate if bdate else None,
                    "language_id": int(selected_language_id) if selected_language_id else None,
                }
            )

            # ✅ workspace
            workspace_id = await asyncio.to_thread(
                create_default_workspace_for_user,
                user.id
            )

            # ✅ hazineha
            await asyncio.to_thread(
                copy_hazineha_template_for_user,
                user.id,
                workspace_id
            )

            # ✅ account (اینجا اگر fail کنه باید rollback بشه)
            await asyncio.to_thread(
                create_default_account_for_user,
                user.id,
                workspace_id
            )

            set_loading(False)
            page.app_go("login")

 
        except Exception as ex:
            print("REGISTER ERROR:", ex)

            if user and user.id:
                try:
                    await asyncio.to_thread(delete_auth_user, user.id)
                    print("ROLLBACK USER DELETED:", user.id)
                except Exception as delete_ex:
                    print("DELETE USER ERROR:", delete_ex)

            set_loading(False)
            show_message(f"Error: {ex}")

    def register(e):
        page.run_task(register_async, e)

    create_btn.on_click = register


    view = ft.View(
        route="/register",
        controls=[
            ft.Text("Register", size=24, weight=ft.FontWeight.BOLD),

            language_dropdown,

            ft.Container(height=4),
            email,
            password,
            confirm_password,
            name,
            family,
            birthdate,

            status_text,

            ft.Container(height=10),
            create_btn,
            back_btn,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.run_task(load_languages_async)

    return view