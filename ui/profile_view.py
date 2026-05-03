import flet as ft
from services.supabase_service import (
    get_my_profile,
    update_my_profile,
    get_languages,
    refresh_hazineha_titles_for_user,
)


def profile_view(page: ft.Page):
    username = ft.TextField(label="Username", width=320)
    name = ft.TextField(label="Name", width=320)
    family = ft.TextField(label="Family", width=320)
    birthdate = ft.TextField(label="Birthdate (YYYY-MM-DD)", width=320)
    email = ft.TextField(label="Email", width=320, read_only=True)

    language_dropdown = ft.Dropdown(
        label="Language",
        width=320,
        options=[],
    )

    status_text = ft.Text("", color=ft.Colors.RED_400)

    def show_message(text, color=ft.Colors.RED_400):
        status_text.value = text
        status_text.color = color
        page.update()

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

        username.value = profile.get("username", "") or ""
        name.value = profile.get("name", "") or ""
        family.value = profile.get("family", "") or ""
        birthdate.value = profile.get("birthdate", "") or ""
        email.value = profile.get("email", "") or ""

        language_id = profile.get("language_id")
        if language_id is not None:
            language_dropdown.value = str(language_id)
            apply_language_ui(language_id, langs)

        page.update()

    def save_profile(e):
        try:
            if not language_dropdown.value:
                show_message("Please select a language.")
                return
            
            selected_language_id = int(language_dropdown.value)

            update_my_profile({
                "username": (username.value or "").strip(),
                "name": (name.value or "").strip(),
                "family": (family.value or "").strip(),
                "birthdate": (birthdate.value or "").strip() or None,
                "language_id": selected_language_id,
            })

            profile = get_my_profile()
            if profile and profile.get("id"):
                refresh_hazineha_titles_for_user(profile["id"], selected_language_id)

            langs = get_languages() or []
            apply_language_ui(selected_language_id, langs)

            show_message("Profile updated successfully.", ft.Colors.GREEN_400)
            # page.app_go("profile")



        except Exception as ex:
            show_message(f"Error: {ex}")

    load_profile()

    return ft.View(
        route="/profile",
        controls=[
            ft.Container(height=20),
            ft.Text("Profile", size=28, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),

            email,
            username,
            name,
            family,
            birthdate,
            language_dropdown,

            ft.Container(height=10),
            status_text,

            ft.Container(height=10),
            ft.ElevatedButton("Save Changes", on_click=save_profile, width=320),
            ft.TextButton("Back", on_click=lambda e: page.app_go("sabtehazine")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )