import asyncio
import flet as ft
from ui.member_manager_shared import build_member_manager_content
from services.i18n import t


def members_view(page: ft.Page):
    page.data = page.data or {}

    def close_page():
        page.app_go("sabtehazine")

    shared = build_member_manager_content(
        page=page,
        selected_member={"member_id": None, "member_name": ""},
        on_member_selected=None,
        close_handler=None,
        picker_mode=False,
    )

    async def load_after_mount():
        await asyncio.sleep(0.05)

        try:
            await shared["refresh_async"](do_update=False)
            page.update()
        except Exception as ex:
            print("MEMBERS LOAD AFTER MOUNT ERROR:", ex)
            

    page.run_task(load_after_mount)

    return ft.View(
        route="/members",
        bgcolor="#F8FAFC",
        appbar=ft.AppBar(
            bgcolor="#F8FAFC",
            elevation=0,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW,
                icon_color="#0F172A",
                on_click=lambda e: close_page(),
            ),
            title=ft.Text(t(page, "Member_Title")),
        ),
        controls=[
            ft.Container(
                expand=True,
                padding=ft.padding.only(left=16, right=16, top=12, bottom=16),
                bgcolor="#F8FAFC",
                content=shared["content"],
            )
        ],
    )