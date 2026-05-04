import flet as ft
from services.supabase_service import sign_in_user, get_profile


def login_view(page: ft.Page):
    email = ft.TextField(
        label="Email",
        width=320,
        autofocus=True,
    )

    password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=320,
    )

    status_text = ft.Text("", color=ft.Colors.RED_400)

    def show_message(text, color=ft.Colors.RED_400):
        status_text.value = text
        status_text.color = color
        page.update()

    async def login_async(e):
        try:
            em = (email.value or "").strip().lower()
            pwd = password.value or ""

            if not em or not pwd:
                show_message("Email and password are required.")
                return

            auth_res = sign_in_user(em, pwd)
            user = auth_res.user
            session = auth_res.session

            if not user or not session:
                show_message("Login failed.")
                return

            profile = get_profile(user.id)

            await page.shared_preferences.set("access_token", session.access_token)
            await page.shared_preferences.set("refresh_token", session.refresh_token)
            await page.shared_preferences.set("user_id", user.id)
            await page.shared_preferences.set("user_email", user.email or "")

            if profile:
                await page.shared_preferences.set("username", profile.get("username", ""))
                await page.shared_preferences.set("name", profile.get("name", ""))
                await page.shared_preferences.set("family", profile.get("family", ""))

            show_message("Login successful.", ft.Colors.GREEN_400)
            # page.app_go("sabtehazine")
            page.data["user"] = user   
            page.app_go("sabtehazine") 

        except Exception as ex:
            show_message(f"Error: {ex}")

    def login(e):
        page.run_task(login_async, e)

    password.on_submit = login

    return ft.View(
        route="/",
        controls=[
            ft.Container(height=30),
            ft.Text("Login", size=28, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            email,
            password,
            ft.Container(height=10),
            status_text,
            ft.Container(height=10),
            ft.ElevatedButton("Login", on_click=login, width=320),
            ft.TextButton("Register", on_click=lambda e: page.app_go("register")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )