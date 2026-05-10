import flet as ft
from services.i18n import t
from services.supabase_service import (
    get_my_workspaces,
    create_workspace,
    update_workspace,
    delete_workspace,
    share_workspace_by_email,
    get_workspace_shared_users,
    remove_workspace_share,
)


def workspaces_view(page: ft.Page):

    workspaces_list = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)

    title_tf = ft.TextField(
        label="Workspace title",
        border_radius=14,
        height=48,
        text_size=13,
    )

    active_switch = ft.Switch(label="Active", value=True)

    selected_workspace = {"id": None}

    def snackbar(msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def open_workspace_dialog(mode="add", row=None):
        selected_workspace["id"] = row.get("id") if row else None
        title_tf.value = row.get("title", "") if row else ""
        active_switch.value = row.get("is_active", True) if row else True

        def save_click(e):
            title = (title_tf.value or "").strip()

            if not title:
                snackbar("Workspace title is required")
                return

            if mode == "add":
                create_workspace(title=title, is_active=active_switch.value)
            else:
                update_workspace(
                    workspace_id=selected_workspace["id"],
                    title=title,
                    is_active=active_switch.value,
                )

            close_dialog(dialog)
            load_workspaces()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Add Workspace" if mode == "add" else "Edit Workspace",
                size=16,
                weight=ft.FontWeight.W_700,
            ),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    [
                        title_tf,
                        active_switch,
                    ],
                    tight=True,
                    spacing=12,
                ),
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Cancel"),
                    on_click=lambda e: close_dialog(dialog),
                ),
                ft.ElevatedButton(
                    content=ft.Text("Save"),
                    on_click=save_click,
                ),
            ],
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def open_share_dialog(row):
        email_tf = ft.TextField(
            label="User email",
            border_radius=14,
            height=48,
            text_size=13,
            expand=True,
        )

        message_text = ft.Text(
            "",
            size=11,
            color="#DC2626",
            visible=False,
        )        

        shared_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

        def remove_share_click(e, user_id):
            remove_workspace_share(row["id"], user_id)
            load_shared_users()
            load_workspaces()
            page.update()
            
        def load_shared_users():
            shared_list.controls.clear()

            users = get_workspace_shared_users(row["id"])

            if not users:
                shared_list.controls.append(
                    ft.Text(
                        "Not shared with anyone yet.",
                        size=12,
                        color="#94A3B8",
                    )
                )
            else:
                for u in users:
                    shared_list.controls.append(
                        ft.Container(
                            padding=10,
                            border_radius=14,
                            bgcolor="#F8FAFC",
                            border=ft.border.all(1, "#E5E7EB"),
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.PERSON_OUTLINE,
                                        size=18,
                                        color="#2563EB",
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                u.get("email") or "",
                                                size=13,
                                                weight=ft.FontWeight.W_600,
                                                color="#0F172A",
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                                max_lines=1,
                                            ),
                                            ft.Text(
                                                "Shared user",
                                                size=10,
                                                color="#64748B",
                                            ),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_size=16,
                                        icon_color="#DC2626",
                                        width=30,
                                        height=30,
                                        style=ft.ButtonStyle(padding=0),
                                        tooltip="Remove share",
                                        on_click=lambda e, user_id=u["user_id"]: remove_share_click(e, user_id),
                                    ),
                                ],
                                spacing=8,
                            ),
                        )
                    )

            page.update()

        def share_click(e):
            email = (email_tf.value or "").strip()

            message_text.value = ""
            message_text.visible = False

            if not email:
                message_text.value = "Email is required."
                message_text.visible = True
                page.update()
                return

            result = share_workspace_by_email(
                workspace_id=row["id"],
                email=email,
            )


            if result.get("success"):
                email_tf.value = ""
                message_text.value = "Workspace shared successfully."
                message_text.color = "#16A34A"
                message_text.visible = True

                load_shared_users()
                load_workspaces()
            else:
                message_text.value = result.get(
                    "message",
                    "User not found."
                )
                message_text.color = "#DC2626"
                message_text.visible = True

            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                f"Share: {row.get('title', '')}",
                size=16,
                weight=ft.FontWeight.W_700,
            ),
            content=ft.Container(
                width=390,
                height=420,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                email_tf,
                                ft.IconButton(
                                    icon=ft.Icons.ADD,
                                    icon_color="#2563EB",
                                    bgcolor="#EFF6FF",
                                    width=42,
                                    height=42,
                                    tooltip="Share",
                                    on_click=share_click,
                                ),
                            ],
                            spacing=8,
                        ),
                        message_text,
                        
                        ft.Divider(height=16),

                        ft.Text(
                            "Shared with",
                            size=13,
                            weight=ft.FontWeight.W_700,
                            color="#0F172A",
                        ),

                        ft.Container(
                            expand=True,
                            content=shared_list,
                        ),
                    ],
                    spacing=8,
                    expand=True,
                ),
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Close"),
                    on_click=lambda e: close_dialog(dialog),
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        load_shared_users()
        page.update()


    def confirm_delete(row):
        def delete_click(e):
            delete_workspace(row["id"])
            close_dialog(dialog)
            load_workspaces()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Workspace?", size=16, weight=ft.FontWeight.W_700),
            content=ft.Text(
                "This action cannot be undone.",
                size=13,
                color="#64748B",
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Cancel"),
                    on_click=lambda e: close_dialog(dialog),
                ),
                ft.TextButton(
                    content=ft.Text("Delete", color="#DC2626"),
                    on_click=delete_click,
                ),
            ],
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()


    def workspace_card(row):
        is_active = row.get("is_active", True)
        shared_count = row.get("shared_count", 0) or 0
        has_share = shared_count > 0

        return ft.Container(
            bgcolor="#FFFFFF",
            border_radius=18,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.border.all(1, "#E5E7EB"),
            content=ft.Row(
                [
                    # متن‌ها
                    ft.Column(
                        [
                            # سطر اول: فقط عنوان
                            ft.Text(
                                row.get("title", ""),
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color="#0F172A",
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                            ),

                            # سطر دوم: Active + Shared
                            ft.Row(
                                [
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=7, vertical=2),
                                        border_radius=999,
                                        bgcolor="#DCFCE7" if is_active else "#F1F5F9",
                                        content=ft.Text(
                                            "Active" if is_active else "Inactive",
                                            size=9,
                                            color="#166534" if is_active else "#64748B",
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ),

                                    ft.Container(
                                        visible=has_share,
                                        padding=ft.padding.symmetric(horizontal=7, vertical=2),
                                        border_radius=999,
                                        bgcolor="#FEF3C7",
                                        content=ft.Text(
                                            f"Shared {shared_count}",
                                            size=9,
                                            color="#92400E",
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),

                    # دکمه‌ها
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.IOS_SHARE_OUTLINED,
                                icon_size=15,
                                tooltip="Share",
                                icon_color="#2563EB",
                                width=30,
                                height=30,
                                style=ft.ButtonStyle(padding=0),
                                on_click=lambda e: open_share_dialog(row),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_size=15,
                                tooltip="Edit",
                                icon_color="#475569",
                                width=30,
                                height=30,
                                style=ft.ButtonStyle(padding=0),
                                on_click=lambda e: open_workspace_dialog("edit", row),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=15,
                                tooltip="Delete",
                                icon_color="#DC2626",
                                width=30,
                                height=30,
                                style=ft.ButtonStyle(padding=0),
                                on_click=lambda e: confirm_delete(row),
                            ),
                        ],
                        spacing=0,
                        tight=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def load_workspaces():
        workspaces_list.controls.clear()

        rows = get_my_workspaces()

        if not rows:
            workspaces_list.controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    content=ft.Text(
                        "No workspace yet.",
                        size=13,
                        color="#94A3B8",
                    ),
                )
            )
        else:
            for row in rows:
                workspaces_list.controls.append(workspace_card(row))

        page.update()

    load_workspaces()

    return ft.View(
        route="/workspaces_view",
        bgcolor="#F8FAFC",
        controls=[
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    icon_color="#0F172A",
                                    icon_size=20,
                                    on_click=lambda e: page.app_go("sabtehazine"),
                                ),

                                ft.Text(
                                    "Workspaces",
                                    size=17,
                                    weight=ft.FontWeight.W_700,
                                    color="#0F172A",
                                    expand=True,
                                ),

                                ft.ElevatedButton(
                                    content=ft.Row(
                                        [
                                            ft.Icon(ft.Icons.ADD, size=16),
                                            ft.Text("Add", size=13),
                                        ],
                                        spacing=4,
                                        tight=True,
                                    ),
                                    style=ft.ButtonStyle(
                                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                    on_click=lambda e: open_workspace_dialog("add"),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=8, color="transparent"),

                        ft.Container(
                            expand=True,
                            bgcolor="#FFFFFF",
                            border_radius=24,
                            padding=16,
                            content=workspaces_list,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            )
        ],
    )