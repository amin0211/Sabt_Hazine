import flet as ft
from services.supabase_service import get_members, add_member, update_member, delete_member
from services.i18n import t
import asyncio

def build_member_manager_content(
    page: ft.Page,
    selected_member: dict | None = None,
    on_member_selected=None,
    close_handler=None,
    picker_mode: bool = False,
):
    PRIMARY = "#2563EB"
    TEXT_MAIN = "#0F172A"
    TEXT_MUTED = "#64748B"
    BORDER = "#E2E8F0"
    BORDER_FOCUS = "#93C5FD"
    DANGER = "#DC2626"

    selected_member = selected_member or {
        "member_id": None,
        "member_name": "",
    }

    name_filter = ft.TextField(
        dense=True,
        height=42,
        border_radius=12,
        filled=True,
        bgcolor="#F8FAFC",
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        text_size=13,
        # expand=True,
    )

    relation_filter = ft.TextField(
        dense=True,
        height=42,
        border_radius=12,
        filled=True,
        bgcolor="#F8FAFC",
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        text_size=13,
        # expand=True,
    )

    member_table = ft.ListView(
        spacing=8,
        padding=0,
        expand=True,
        auto_scroll=False,
    )

    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    def small_action_btn(icon, color, tooltip, on_click):
        return ft.Container(
            width=24,
            height=24,
            border_radius=8,
            bgcolor="#F8FAFC",
            border=ft.border.all(1, BORDER),
            alignment=ft.Alignment.CENTER,
            ink=True,
            tooltip=tooltip,
            on_click=on_click,
            content=ft.Icon(icon, size=13, color=color),
        )

    def select_member(member):
        if not picker_mode:
            return

        selected_member["member_id"] = member["id"]
        selected_member["member_name"] = member["full_name"]

        if on_member_selected:
            on_member_selected(member)

        if close_handler:
            close_handler()

        safe_update()

    def open_add_member_dialog(ev=None):
        member_name = ft.TextField(
            label=t(page, "Member_LableName"),
            autofocus=True,
            border_radius=14,
            filled=True,
            bgcolor="#FFFFFF",
        )
        member_relation = ft.TextField(
            label=t(page, "Member_LableRelation"),
            border_radius=14,
            filled=True,
            bgcolor="#FFFFFF",
        )

        add_error = ft.Text("", size=11, color=DANGER, visible=False)

        add_dlg = ft.AlertDialog(
            modal=True,
            bgcolor="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=20),
        )

        def close_add(ev=None):
            add_dlg.open = False
            safe_update()

        def save_add(ev):
            add_error.visible = False
            add_error.value = ""

            if not (member_name.value or "").strip():
                add_error.value = t(page, "Member_Message_Enter_Name")
                add_error.visible = True
                safe_update()
                return

            new_member = add_member(member_name.value, member_relation.value)

            if new_member and picker_mode:
                selected_member["member_id"] = new_member["id"]
                selected_member["member_name"] = new_member["full_name"]
                if on_member_selected:
                    on_member_selected(new_member)

            refresh_member_table(False)

            add_dlg.open = False
            safe_update()

        add_dlg.title = ft.Text(t(page, "Member_Insert"))
        add_dlg.content = ft.Container(
            width=380,
            content=ft.Column(
                [member_name, member_relation, add_error],
                tight=True,
                spacing=12,
            ),
        )
        add_dlg.actions = [
            ft.TextButton(t(page, "Member_Cancel"), on_click=close_add),
            ft.ElevatedButton(t(page, "Member_Save"), on_click=save_add),
        ]

        if add_dlg not in page.overlay:
            page.overlay.append(add_dlg)

        add_dlg.open = True
        safe_update()

    def edit_member_dialog(member):
        name_field = ft.TextField(
            label=t(page, "Member_LableName"),
            value=member.get("full_name", ""),
            border_radius=14,
            filled=True,
            bgcolor="#FFFFFF",
        )
        relation_field = ft.TextField(
            label=t(page, "Member_LableRelation"),
            value=member.get("relation", "") or "",
            border_radius=14,
            filled=True,
            bgcolor="#FFFFFF",
        )
        edit_error = ft.Text("", size=11, color=DANGER, visible=False)

        edit_dlg = ft.AlertDialog(
            modal=True,
            bgcolor="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=20),
        )

        def close_edit(ev=None):
            edit_dlg.open = False
            safe_update()

        def save_edit(ev):
            edit_error.visible = False
            edit_error.value = ""

            if not (name_field.value or "").strip():
                edit_error.value = t(page,"Member_Message_Enter_Name")
                edit_error.visible = True
                safe_update()
                return

            updated = update_member(
                member["id"],
                name_field.value,
                relation_field.value,
            )

            if updated and picker_mode and selected_member["member_id"] == member["id"]:
                selected_member["member_name"] = updated.get("full_name", name_field.value.strip())
                if on_member_selected:
                    on_member_selected(updated)

            edit_dlg.open = False
            refresh_member_table(False)
            safe_update()

        edit_dlg.title = ft.Text(t(page, "Member_LableEdit"))
        edit_dlg.content = ft.Container(
            width=380,
            content=ft.Column(
                [name_field, relation_field, edit_error],
                tight=True,
                spacing=12,
            ),
        )
        edit_dlg.actions = [
            ft.TextButton(t(page, "Member_Cancel"), on_click=close_edit),
            ft.ElevatedButton(t(page, "Member_Save"), on_click=save_edit),
        ]

        if edit_dlg not in page.overlay:
            page.overlay.append(edit_dlg)

        edit_dlg.open = True
        safe_update()

    def delete_member_dialog(member):
        delete_dlg = ft.AlertDialog(
            modal=True,
            bgcolor="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=20),
        )

        def close_delete(ev=None):
            delete_dlg.open = False
            safe_update()

        def confirm_delete(ev):
            delete_member(member["id"])

            if picker_mode and selected_member["member_id"] == member["id"]:
                selected_member["member_id"] = None
                selected_member["member_name"] = ""
                if on_member_selected:
                    on_member_selected({
                        "id": None,
                        "full_name": "",
                    })

            delete_dlg.open = False
            refresh_member_table(False)
            safe_update()

        delete_dlg.title = ft.Text("Delete member")
        delete_dlg.content = ft.Text(
            f"Delete this member?  «{member.get('full_name', '')}» ",
            color=TEXT_MAIN,
            size=14,
        )
        delete_dlg.actions = [
            ft.TextButton(t(page, "Member_Cancel"), on_click=close_delete),
            ft.ElevatedButton(
                t(page, "Member_LableDelete"),
                bgcolor=DANGER,
                color="#FFFFFF",
                on_click=confirm_delete,
            ),
        ]

        if delete_dlg not in page.overlay:
            page.overlay.append(delete_dlg)

        delete_dlg.open = True
        safe_update()

    def build_row(member):
        is_selected = picker_mode and selected_member["member_id"] == member["id"]
        row_bg = "#EFF6FF" if is_selected else "#FFFFFF"
        row_border = "#BFDBFE" if is_selected else BORDER

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=16,
            bgcolor=row_bg,
            border=ft.border.all(1, row_border),
            ink=picker_mode,
            on_click=(lambda ev, m=member: select_member(m)) if picker_mode else None,
            content=ft.Row(
                [
                    ft.Container(
                        width=150,
                        content=ft.Text(
                            member.get("full_name", ""),
                            weight=ft.FontWeight.W_600,
                            color=TEXT_MAIN,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Text(
                            member.get("relation", "") or "-",
                            color=TEXT_MUTED,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ),
                    ft.Container(
                        width=72,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        content=ft.Row(
                            [
                                small_action_btn(
                                    ft.Icons.EDIT_OUTLINED,
                                    PRIMARY,
                                    t(page, "Member_LableEdit"),
                                    lambda ev, m=member: edit_member_dialog(m),
                                ),
                                small_action_btn(
                                    ft.Icons.DELETE_OUTLINE,
                                    DANGER,
                                    t(page, "Member_LableDelete"),
                                    lambda ev, m=member: delete_member_dialog(m),
                                ),
                            ],
                            spacing=3,
                            tight=True,
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def refresh_member_table(e=None):
        members = get_members(page) or []
        member_table.controls.clear()

        name_q = (name_filter.value or "").strip().lower()
        relation_q = (relation_filter.value or "").strip().lower()

        filtered_members = []
        for m in members:
            full_name = (m.get("full_name") or "").strip().lower()
            relation = (m.get("relation") or "").strip().lower()

            if name_q and name_q not in full_name:
                continue
            if relation_q and relation_q not in relation:
                continue

            filtered_members.append(m)

        if not members:
            member_table.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=16,
                    bgcolor="#F8FAFC",
                    border=ft.border.all(1, BORDER),
                    content=ft.Text(
                        t(page, "member_message_No_Member"),
                        color=TEXT_MAIN,
                        weight=ft.FontWeight.W_600,
                    ),
                )
            )
        elif not filtered_members:
            member_table.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=16,
                    bgcolor="#F8FAFC",
                    border=ft.border.all(1, BORDER),
                    content=ft.Text(
                        t(page, "Message_No_results_found"),
                        color=TEXT_MAIN,
                        weight=ft.FontWeight.W_600,
                    ),
                )
            )
        else:
            for m in filtered_members:
                member_table.controls.append(build_row(m))

        if e is not False:
            safe_update()

    async def refresh_member_table_async(do_update=True):
        try:
            members = await asyncio.to_thread(get_members, page)
            members = members or []

            member_table.controls.clear()

            name_q = (name_filter.value or "").strip().lower()
            relation_q = (relation_filter.value or "").strip().lower()

            filtered_members = []

            for m in members:
                full_name = (m.get("full_name") or "").strip().lower()
                relation = (m.get("relation") or "").strip().lower()

                if name_q and name_q not in full_name:
                    continue

                if relation_q and relation_q not in relation:
                    continue

                filtered_members.append(m)

            if not members:
                member_table.controls.append(
                    ft.Container(
                        padding=20,
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, BORDER),
                        content=ft.Text(
                            t(page, "member_message_No_Member"),
                            color=TEXT_MAIN,
                            weight=ft.FontWeight.W_600,
                        ),
                    )
                )

            elif not filtered_members:
                member_table.controls.append(
                    ft.Container(
                        padding=20,
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, BORDER),
                        content=ft.Text(
                            t(page, "Message_No_results_found"),
                            color=TEXT_MAIN,
                            weight=ft.FontWeight.W_600,
                        ),
                    )
                )

            else:
                for m in filtered_members:
                    member_table.controls.append(build_row(m))

            if do_update:
                safe_update()

        except Exception as ex:
            print("REFRESH_MEMBER_TABLE_ASYNC_ERROR:", ex)


            
    name_filter.on_change = refresh_member_table
    relation_filter.on_change = refresh_member_table
    # refresh_member_table()
    member_table.controls.append(
        ft.Container(
            padding=20,
            bgcolor="#F8FAFC",
            border_radius=16,
            border=ft.border.all(1, BORDER),
            content=ft.Text(
                "در حال بارگذاری...",
                color=TEXT_MUTED,
                size=13,
            ),
        )
    )

    actions = []
 
    content_inner = ft.Column(
        expand=True,
        spacing=10,
        controls=[

            ft.ElevatedButton(
                t(page, "Member_Insert"),
                icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                on_click=open_add_member_dialog,
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                ),
            ),

            ft.Row(
                controls=[
                    ft.Container(
                        width=150,
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    t(page, "Member_LableName"),
                                    size=10,
                                    color=TEXT_MUTED,
                                    weight=ft.FontWeight.W_600,
                                ),
                                name_filter,
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    t(page, "Member_LableRelation"),
                                    size=10,
                                    color=TEXT_MUTED,
                                    weight=ft.FontWeight.W_600,
                                ),
                                relation_filter,
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),

            ft.Container(
                expand=True,
                bgcolor="#FFFFFF",
                border_radius=12,
                content=member_table,
            ),
        ],
    )

    if picker_mode:
        content = ft.Container(
            width=620,
            height=470,
            padding=12,
            content=content_inner,
        )
    else:
        content = ft.Container(
            expand=True,
            bgcolor="#FFFFFF",
            border_radius=24,
            padding=16,
            content=content_inner,
        )


    return {
        "content": content,
        "actions": actions,
        "refresh": refresh_member_table,
        "refresh_async": refresh_member_table_async,
    }

def open_member_picker_dialog(
    page: ft.Page,
    selected_member: dict,
    on_member_selected,
):
    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#FFFFFF",
        inset_padding=20,
        shape=ft.RoundedRectangleBorder(radius=24),
    )

    def close_dlg():
        dlg.open = False
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    shared = build_member_manager_content(
        page=page,
        selected_member=selected_member,
        on_member_selected=on_member_selected,
        close_handler=close_dlg,
        picker_mode=True,
    )

    dlg.content = shared["content"]

    if dlg not in page.overlay:
        page.overlay.append(dlg)

    dlg.open = True
    page.update()