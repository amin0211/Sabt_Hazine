import flet as ft
from ui.member_manager_shared import build_member_manager_content
from services.i18n import t

def members_view(page: ft.Page):
    def close_page():
        page.app_go("sabtehazine")

    shared = build_member_manager_content(
        page=page,
        selected_member={"member_id": None, "member_name": ""},
        on_member_selected=None,
        close_handler=close_page,
        picker_mode=False,
    )

    return ft.View(
        route="/members",
        bgcolor="#F8FAFC",
        controls=[
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=42,
                                    height=42,
                                    border_radius=14,
                                    bgcolor="#EFF6FF",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        ft.Icons.GROUPS_2_OUTLINED,
                                        color="#2563EB",
                                        size=22,
                                    ),
                                ),
                                ft.Text(
                                    t(page, "Member_Title"),
                                    size=18,
                                    weight=ft.FontWeight.W_700,
                                    color="#0F172A",
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=8, color="transparent"),
                        ft.Container(
                            expand=True,
                            bgcolor="#FFFFFF",
                            border_radius=24,
                            padding=16,
                            content=ft.Column(
                                [
                                    ft.Container(
                                        expand=True,
                                        content=shared["content"],
                                    ),
                                    # ft.Row(
                                    #     shared["actions"],
                                    #     alignment=ft.MainAxisAlignment.START,  # مثل gantt
                                    # ),
                                ],
                                expand=True,
                            ),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            )
        ],
    )