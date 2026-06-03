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
from services.utils import is_valid_email, today_local, safe_picker_date


def register_view(page: ft.Page):
    page.data = page.data or {}

    email = ft.TextField(
        label="Email",
        width=320,
        keyboard_type=ft.KeyboardType.EMAIL,
    )

    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=320,
    )

    confirm_password = ft.TextField(
        label="Confirm Password",
        password=True,
        can_reveal_password=True,
        width=320,
    )

    name = ft.TextField(
        label="Name",
        width=320,
    )

    family = ft.TextField(
        label="Family",
        width=320,
    )


    birthdate = ft.TextField(
        label="Birthdate",
        hint_text="Select birthdate",
        width=320,
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
    )

    language_dropdown = ft.Dropdown(
        label="Language",
        width=320,
        options=[],
        value=None,
    )

    timezone_dropdown = ft.Dropdown(
        label="Timezone",
        width=320,
        options=[
            ft.dropdown.Option("America/Vancouver", "Vancouver"),
            ft.dropdown.Option("Asia/Dubai", "Dubai"),
            ft.dropdown.Option("Asia/Tehran", "Tehran"),
            ft.dropdown.Option("Europe/London", "London"),
            ft.dropdown.Option("America/Toronto", "Toronto"),
        ],
        value="America/Vancouver",
    )    

    birthdate_picker = ft.DatePicker(
        value=today_local(page),
    )

    if birthdate_picker not in page.overlay:
        page.overlay.append(birthdate_picker)

    def on_birthdate_change(e):
        if not birthdate_picker.value:
            return

        picked = safe_picker_date(birthdate_picker.value, page)
        birthdate_picker.value = picked
        birthdate.value = picked.isoformat()
        page.update()

    birthdate_picker.on_change = on_birthdate_change

    def open_birthdate_picker(e=None):
        if birthdate.value:
            try:
                birthdate_picker.value = safe_picker_date(birthdate.value, page)
            except Exception:
                birthdate_picker.value = today_local(page)

        birthdate_picker.open = True
        page.update()

    birthdate.on_click = open_birthdate_picker


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

    all_inputs = [
        email,
        password,
        confirm_password,
        name,
        family,
        birthdate,
        language_dropdown,
        timezone_dropdown,
    ]

    def set_loading(is_loading: bool):
        create_btn.disabled = is_loading
        back_btn.disabled = is_loading

        for control in all_inputs:
            control.disabled = is_loading

        if is_loading:
            status_text.value = "Creating account..."
            status_text.color = ft.Colors.BLUE_400

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
                            text=str(lang_name),
                        )
                    )

            language_dropdown.options = options

            if saved_language_id and any(
                opt.key == str(saved_language_id) for opt in options
            ):
                language_dropdown.value = str(saved_language_id)

            elif options:
                language_dropdown.value = options[0].key

            page.update()

        except Exception as ex:
            print("LOAD LANGUAGES ERROR:", ex)
            show_message(f"Could not load languages: {ex}")

    async def language_change_async(e):
        selected_language_id = language_dropdown.value
        page.data["language_id"] = selected_language_id

        try:
            await page.shared_preferences.set("language_id", selected_language_id)
        except Exception as ex:
            print("SAVE LANGUAGE ERROR:", ex)

        page.update()

    def on_language_change(e):
        page.run_task(language_change_async, e)

    language_dropdown.on_change = on_language_change

    def validate_register_form():
        em = (email.value or "").strip().lower()
        pwd = password.value or ""
        cpwd = confirm_password.value or ""
        first_name = (name.value or "").strip()
        last_name = (family.value or "").strip()
        bdate = (birthdate.value or "").strip()
        selected_language_id = language_dropdown.value
        selected_timezone = timezone_dropdown.value

        if not em:
            return False, "Email is required."

        if not is_valid_email(em):
            return False, "Email format is not valid."

        if not pwd:
            return False, "Password is required."

        if len(pwd) < 6:
            return False, "Password must be at least 6 characters."

        if pwd != cpwd:
            return False, "Passwords do not match."

        if not first_name:
            return False, "Name is required."

        if not last_name:
            return False, "Family is required."

        if not selected_language_id:
            return False, "Please select a language."
        
        if not selected_timezone:
            return False, "Please select a timezone."

        if bdate:
            parts = bdate.split("-")
            if len(parts) != 3:
                return False, "Birthdate format must be YYYY-MM-DD."

            yyyy, mm, dd = parts

            if not (yyyy.isdigit() and mm.isdigit() and dd.isdigit()):
                return False, "Birthdate format must be YYYY-MM-DD."

            if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2:
                return False, "Birthdate format must be YYYY-MM-DD."

        return True, ""

    async def register_async(e):
        user = None

        try:
            valid, message = validate_register_form()
            if not valid:
                show_message(message)
                return

            em = (email.value or "").strip().lower()
            pwd = password.value or ""

            first_name = (name.value or "").strip()
            last_name = (family.value or "").strip()
            bdate = (birthdate.value or "").strip()
            selected_language_id = language_dropdown.value

            selected_timezone = timezone_dropdown.value or "America/Vancouver"

            set_loading(True)

            # 1) Create auth user
            auth_res = await asyncio.to_thread(sign_up_user, em, pwd)
            user = auth_res.user

            if not user:
                raise Exception("Registration failed. Auth user was not created.")

            # 2) Update profile
            profile_data = {
                "name": first_name,
                "family": last_name,
                "email": em,
                "birthdate": bdate if bdate else None,
                "language_id": int(selected_language_id) if selected_language_id else None,
                "timezone": selected_timezone,
            }

            profile_res = await asyncio.to_thread(
                update_profile,
                user.id,
                profile_data,
            )

            if not profile_res:
                raise Exception("Profile was not updated.")

            # 3) Create default workspace
            workspace_id = await asyncio.to_thread(
                create_default_workspace_for_user,
                user.id,
            )

            if not workspace_id:
                raise Exception("Default workspace was not created.")

            # 4) Copy hazineha template
            hazineha_res = await asyncio.to_thread(
                copy_hazineha_template_for_user,
                user.id,
                workspace_id,
                int(selected_language_id),
            )


            if hazineha_res is None:
                raise Exception("Default categories were not created.")

            # 5) Create default account
            account_res = await asyncio.to_thread(
                create_default_account_for_user,
                user.id,
                workspace_id,
            )

            if not account_res:
                raise Exception("Default account was not created.")

            set_loading(False)
            show_message(
                "Account created successfully. Please login.",
                ft.Colors.GREEN_600,
            )

            page.app_go("login")

        except Exception as ex:
            print("REGISTER ERROR:", ex)

            # اگر هر مرحله بعد از ساخت Auth User خراب شد، کاربر ناقص پاک شود
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

    form_column = ft.Column(
        controls=[
            ft.Text("Register", size=24, weight=ft.FontWeight.BOLD),

            language_dropdown,
            timezone_dropdown,

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

            # مهم: فضای خالی آخر فرم تا دکمه پایین گیر نکند
            ft.Container(height=40),
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    view = ft.View(
        route="/register",
        padding=0,
        spacing=0,
        bgcolor="#FFFFFF",
        controls=[
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    alignment=ft.Alignment.TOP_CENTER,
                    padding=ft.padding.only(left=20, right=20, top=24, bottom=24),
                    content=ft.ListView(
                        expand=True,
                        spacing=0,
                        padding=0,
                        controls=[
                            ft.Container(
                                alignment=ft.Alignment.TOP_CENTER,
                                content=form_column,
                            )
                        ],
                    ),
                ),
            )
        ],
    )

    page.run_task(load_languages_async)

    return view