import flet as ft
import asyncio
from app_config import APP_VERSION, BUILD_NUMBER
from services.supabase_service import (
    get_my_profile,
    update_my_profile,
    get_languages,
    refresh_hazineha_titles_for_user,
    update_user_password,
    delete_my_account,
)


def profile_view(page: ft.Page):
    state = {
        "old_language_id": None,
        "old_timezone": None,
    }    
    # username = ft.TextField(label="Username", width=320)
    name = ft.TextField(label="Name", width=320)
    family = ft.TextField(label="Family", width=320)
    birthdate = ft.TextField(label="Birthdate (YYYY-MM-DD)", width=320)
    email = ft.TextField(label="Email", width=320, read_only=True)

    language_dropdown = ft.Dropdown(
        label="Language",
        width=320,
        options=[],
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

    new_password = ft.TextField(
        label="New Password",
        width=320,
        password=True,
        can_reveal_password=True,
    )

    confirm_password = ft.TextField(
        label="Confirm Password",
        width=320,
        password=True,
        can_reveal_password=True,
    )

    password_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Change Password"),
        content=ft.Column(
            [
                new_password,
                confirm_password,
            ],
            tight=True,
            spacing=10,
        ),
        actions=[],
    )

    if password_dialog not in page.overlay:
        page.overlay.append(password_dialog)

    delete_account_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Delete Account"),
        content=ft.Text(
            "Are you sure you want to delete your Costio account? "
            "This will delete or anonymize your account data. "
            "This action cannot be undone."
        ),
        actions=[],
    )

    if delete_account_dialog not in page.overlay:
        page.overlay.append(delete_account_dialog)

    def open_password_dialog(e=None):
        new_password.value = ""
        confirm_password.value = ""
        password_dialog.open = True
        page.update()

    def close_password_dialog(e=None):
        password_dialog.open = False
        page.update()

    def save_password(e=None):
        try:
            p1 = (new_password.value or "").strip()
            p2 = (confirm_password.value or "").strip()

            if len(p1) < 6:
                show_message("Password must be at least 6 characters.")
                return

            if p1 != p2:
                show_message("Passwords do not match.")
                return

            update_user_password(p1)

            password_dialog.open = False
            show_message("Password changed successfully.", ft.Colors.GREEN_400)

        except Exception as ex:
            show_message(f"Password error: {ex}")



    def open_delete_account_dialog(e=None):
        delete_account_dialog.open = True
        page.update()


    def close_delete_account_dialog(e=None):
        delete_account_dialog.open = False
        page.update()


    async def do_delete_account(e=None):
        try:
            delete_account_dialog.open = False
            set_form_disabled(True)
            show_message("Deleting account...", ft.Colors.BLUE_400)
            page.update()

            await asyncio.sleep(0.1)

            print("[PROFILE DELETE] before delete_my_account", flush=True)

            result = await asyncio.to_thread(delete_my_account)

            print("[PROFILE DELETE] result:", result, flush=True)

            if not result.get("ok"):
                set_form_disabled(False)
                show_message(result.get("error", "Account deletion failed."))
                page.update()
                return

            show_message("Account deletion confirmed.", ft.Colors.GREEN_400)
            page.update()

            await asyncio.sleep(2.0)

            try:
                await page.shared_preferences.clear()
            except Exception as ex:
                print("[PROFILE DELETE] shared_preferences clear error:", ex, flush=True)

            try:
                page.client_storage.clear()
            except Exception as ex:
                print("[PROFILE DELETE] client_storage clear error:", ex, flush=True)

            try:
                page.data = {}
            except Exception as ex:
                print("[PROFILE DELETE] page.data clear error:", ex, flush=True)

            page.app_go("login")
        except Exception as ex:
            set_form_disabled(False)
            show_message(f"Delete account error: {ex}")
            page.update()


    def delete_account(e=None):
        page.run_task(do_delete_account, e)
        

    password_dialog.actions = [
        ft.TextButton("Cancel", on_click=close_password_dialog),
        ft.ElevatedButton("Save Password", on_click=save_password),
    ]

    delete_account_dialog.actions = [
        ft.TextButton("Cancel", on_click=close_delete_account_dialog),
        ft.ElevatedButton(
            "Delete Account",
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            on_click=delete_account,
        ),
    ]

    status_text = ft.Text("", color=ft.Colors.RED_400)

    def show_message(text, color=ft.Colors.RED_400):
        status_text.value = text
        status_text.color = color
        # page.update()

    def load_languages():
        langs = get_languages() or []

        language_dropdown.options = [
            ft.dropdown.Option(
                key=str(lang["id"]),
                text=lang["name"],
            )
            for lang in langs
        ]

        return langs

    def apply_language_ui(language_id, langs):
        selected_lang = None

        for lang in langs:
            if str(lang["id"]) == str(language_id):
                selected_lang = lang
                break

        if not selected_lang:
            return

        page.data = page.data or {}
        page.data["lang"] = selected_lang.get("code", "fa")
        # page.rtl = bool(selected_lang.get("is_rtl", False))

    def load_profile():
        langs = load_languages()
        profile = get_my_profile()

        if not profile:
            show_message("Profile not found.")
            return

        # username.value = profile.get("username", "") or ""
        name.value = profile.get("name", "") or ""
        family.value = profile.get("family", "") or ""
        birthdate.value = profile.get("birthdate", "") or ""
        email.value = profile.get("email", "") or ""


        language_id = profile.get("language_id")
        state["old_language_id"] = int(language_id) if language_id is not None else None

        if language_id is not None:
            language_dropdown.value = str(language_id)
            apply_language_ui(language_id, langs)

        timezone_dropdown.value = profile.get("timezone") or "America/Vancouver"
        state["old_timezone"] = timezone_dropdown.value        

        page.data = page.data or {}
        page.data["timezone"] = timezone_dropdown.value

        page.update()

    def set_form_disabled(value: bool):
        email.disabled = value
        name.disabled = value
        family.disabled = value
        birthdate.disabled = value
        language_dropdown.disabled = value
        timezone_dropdown.disabled = value
        save_button.disabled = value
        back_button.disabled = value
        change_password_button.disabled = value
        delete_account_button.disabled = value
        page.update()

    async def do_save_profile(e=None):
        try:
            set_form_disabled(True)
            show_message("Saving...", ft.Colors.BLUE_400)
            page.update()

            await asyncio.sleep(0.1)

            if not language_dropdown.value:
                show_message("Please select a language.")
                set_form_disabled(False)
                page.update()
                return

            selected_language_id = int(language_dropdown.value)
            selected_timezone = timezone_dropdown.value or "America/Vancouver"

            language_changed = selected_language_id != state.get("old_language_id")
            timezone_changed = selected_timezone != state.get("old_timezone")

            await asyncio.to_thread(
                update_my_profile,
                {
                    "name": (name.value or "").strip(),
                    "family": (family.value or "").strip(),
                    "birthdate": (birthdate.value or "").strip() or None,
                    "language_id": selected_language_id,
                    "timezone": selected_timezone,
                }
            )

            workspace_id = page.data.get("current_workspace_id")

            if language_changed:
                if workspace_id:
                    await asyncio.to_thread(
                        refresh_hazineha_titles_for_user,
                        workspace_id,
                        selected_language_id,
                    )

                langs = await asyncio.to_thread(get_languages)
                apply_language_ui(selected_language_id, langs or [])
                await page.shared_preferences.set("lang", page.data.get("lang", "fa"))

                page.data["sabtehazine_changed"] = True
                page.data.pop("sabtehazine_view_cache", None)
                page.data["sabtehazine_loaded"] = False

            if timezone_changed:
                page.data["timezone"] = selected_timezone
                await page.shared_preferences.set("timezone", selected_timezone)
            
            state["old_language_id"] = selected_language_id
            state["old_timezone"] = selected_timezone

            show_message("Profile updated successfully.", ft.Colors.GREEN_400)
            page.update()

            await asyncio.sleep(0.2)
            page.app_go("sabtehazine")

        except Exception as ex:
            show_message(f"Error: {ex}")
            set_form_disabled(False)
            page.update()


    def save_profile(e):
        page.run_task(do_save_profile, e)



    load_profile()

    change_password_button = ft.IconButton(
        icon=ft.Icons.LOCK_RESET,
        tooltip="Change Password",
        on_click=open_password_dialog,
    )

    save_button = ft.ElevatedButton(
        "Save Changes",
        on_click=save_profile,
        width=320,
    )

    back_button = ft.TextButton(
        "Back",
        on_click=lambda e: page.app_go("sabtehazine"),
    )

    delete_account_button = ft.ElevatedButton(
        "Delete Account",
        icon=ft.Icons.DELETE_FOREVER,
        width=320,
        bgcolor=ft.Colors.RED,
        color=ft.Colors.WHITE,
        on_click=open_delete_account_dialog,
    )

    profile_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=ft.padding.only(
            left=16,
            right=16,
            top=24,
            bottom=20 if page.platform != ft.PagePlatform.ANDROID else 6,
        ),
        auto_scroll=False,
        controls=[
            ft.Row(
                [
                    ft.Text("Profile", size=28, weight=ft.FontWeight.BOLD),
                    change_password_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),

            email,
            name,
            family,
            birthdate,
            language_dropdown,
            timezone_dropdown,

            # status_text,
            ft.Container(height=2),

            save_button,
            back_button,

            ft.Container(height=3),

            ft.Divider(),

            ft.Text(
                "Danger Zone",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.RED_700,
                text_align=ft.TextAlign.CENTER,
            ),

            delete_account_button,

            ft.Container(height=6),

            ft.Text(
                f"Version {APP_VERSION} ({BUILD_NUMBER})",
                size=11,
                color="#9CA3AF",
                text_align=ft.TextAlign.CENTER,
            ),

        ],
    )

    profile_body = ft.Container(
        expand=True,
        alignment=ft.Alignment.TOP_CENTER,
        content=ft.Container(
            width=360,
            expand=True,
            content=profile_list,
        ),
    )

    if page.platform == ft.PagePlatform.ANDROID:
        profile_body = ft.SafeArea(
            expand=True,
            avoid_intrusions_top=False,
            avoid_intrusions_left=False,
            avoid_intrusions_right=False,
            avoid_intrusions_bottom=True,
            content=profile_body,
        )


    return ft.View(
        route="/profile",
        controls=[
            profile_body,
        ],
        bgcolor="#FFFFFF",
        padding=0,
        spacing=0,
    )