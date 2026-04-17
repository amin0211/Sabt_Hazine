import flet as ft


def main_view(page: ft.Page, theme):
    def logout(e):
        try:
            page.client_storage.remove("user")
        except:
            pass

        page.go("/login")

    return ft.View(
        route="/main",
        controls=[
            ft.Container(
                expand=True,
                bgcolor=theme["APP_BG"],   # 👈 این مهمه
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("Main Page", size=25, color=theme["TEXT"]),
                        ft.ElevatedButton("Logout", on_click=logout),
                    ]
                )
            )
        ],
    )    