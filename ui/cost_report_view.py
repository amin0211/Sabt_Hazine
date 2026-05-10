import flet as ft
from datetime import datetime
from zoneinfo import ZoneInfo

from services.supabase_service import (
    load_my_costs_by_date,
    load_active_hazineha,
    get_descendant_category_ids,
    get_members,
)

TZ = ZoneInfo("America/Vancouver")


def today_local():
    return datetime.now(TZ).date()


def money(v):
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


def cost_report_view(page: ft.Page):
    APP_BG = "#F3F4F6"
    CARD_BG = "#FFFFFF"
    PRIMARY = "#4F46E5"
    TEXT_MAIN = "#111827"
    TEXT_MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    CARD_GRAY = "#F0F0F3"

    if not isinstance(page.data, dict):
        page.data = {}

    start_date = today_local().replace(day=1)
    end_date = today_local()

    selected_category = page.data.get("report_selected_category") or {
        "category_id": None,
        "category_title": "All categories",
    }

    selected_member = {
        "member_id": None,
        "member_name": "All members",
    }

    title_filter = {"value": ""}

    list_holder = ft.Container(expand=True)

    def safe_update():
        try:
            page.update()
        except Exception as ex:
            print("REPORT UPDATE ERROR:", ex)

    def build_filter_button(label, icon):
        return ft.Container(
            border=ft.border.all(1, BORDER),
            border_radius=14,
            bgcolor=CARD_GRAY,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=PRIMARY),
                    ft.Text(
                        label,
                        size=10,
                        color=TEXT_MAIN,
                        weight=ft.FontWeight.W_500,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        )

    # ---------------- Date Pickers ----------------

    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)

    if start_picker not in page.overlay:
        page.overlay.append(start_picker)

    if end_picker not in page.overlay:
        page.overlay.append(end_picker)

    start_btn = ft.GestureDetector()
    end_btn = ft.GestureDetector()

    def refresh_date_buttons():
        start_btn.content = build_filter_button(
            f"Fr: {start_date}",
            ft.Icons.CALENDAR_MONTH,
        )
        end_btn.content = build_filter_button(
            f"To: {end_date}",
            ft.Icons.DATE_RANGE,
        )

    def open_start(e=None):
        start_picker.open = True
        safe_update()

    def open_end(e=None):
        end_picker.open = True
        safe_update()

    def update_start(e):
        nonlocal start_date

        picked = start_picker.value
        if not picked:
            return

        if isinstance(picked, datetime):
            picked = picked.date()

        start_date = picked
        refresh_date_buttons()
        refresh()

    def update_end(e):
        nonlocal end_date

        picked = end_picker.value
        if not picked:
            return

        if isinstance(picked, datetime):
            picked = picked.date()

        end_date = picked
        refresh_date_buttons()
        refresh()

    start_btn.on_tap = open_start
    end_btn.on_tap = open_end
    start_picker.on_change = update_start
    end_picker.on_change = update_end

    refresh_date_buttons()

    # ---------------- Category Picker ----------------

    category_btn = ft.GestureDetector()

    def refresh_category_button():
        category_btn.content = build_filter_button(
            selected_category["category_title"],
            ft.Icons.ACCOUNT_TREE_OUTLINED,
        )

    def on_category_selected(result: dict):
        selected_category["category_id"] = result.get("category_id")
        selected_category["category_title"] = (
            result.get("category_title") or "All categories"
        )

        page.data["report_selected_category"] = selected_category

        refresh_category_button()
        refresh()

    def choose_category(e=None):
        page.data["without_edit"] = True
        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = selected_category["category_id"]
        page.data["category_picker_on_selected"] = on_category_selected
        page.data["from"] = "cost_report_view"

        page.app_go("hazinaha_view")

    category_btn.on_tap = choose_category
    refresh_category_button()

    # ---------------- Member Picker ----------------

    members_data = get_members(page)
    member_search_query = {"value": ""}

    member_btn = ft.GestureDetector()

    member_list_column = ft.Column(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    member_search_field = ft.TextField(
        hint_text="Search member",
        prefix_icon=ft.Icons.SEARCH,
        text_size=13,
        border_radius=14,
    )

    def refresh_member_button():
        member_btn.content = build_filter_button(
            selected_member["member_name"],
            ft.Icons.PERSON_OUTLINE,
        )

    def close_member_dialog(e=None):
        member_dialog.open = False
        safe_update()

    def clear_member_filter(e=None):
        selected_member["member_id"] = None
        selected_member["member_name"] = "All members"

        refresh_member_button()
        member_dialog.open = False
        refresh()

    def on_member_selected(member_id, member_name):
        selected_member["member_id"] = member_id
        selected_member["member_name"] = member_name or "No name"

        refresh_member_button()
        member_dialog.open = False
        refresh()

    def rebuild_member_list():
        member_list_column.controls.clear()

        q = (member_search_query["value"] or "").strip().lower()

        member_list_column.controls.append(
            ft.Container(
                bgcolor="#F8FAFC",
                border=ft.border.all(1, BORDER),
                border_radius=12,
                padding=10,
                on_click=clear_member_filter,
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.GROUP_OUTLINED, size=17, color=PRIMARY),
                        ft.Text(
                            "All members",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
            )
        )

        for m in members_data:
            name = m.get("full_name") or ""
            relation = m.get("relation") or ""
            mid = m.get("id")

            search_text = f"{name} {relation}".lower()

            if q and q not in search_text:
                continue

            member_list_column.controls.append(
                ft.Container(
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, BORDER),
                    border_radius=12,
                    padding=10,
                    on_click=lambda e, member_id=mid, member_name=name: on_member_selected(
                        member_id,
                        member_name,
                    ),
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.PERSON_OUTLINE,
                                size=17,
                                color=TEXT_MUTED,
                            ),
                            ft.Text(
                                name or "No name",
                                size=13,
                                color=TEXT_MAIN,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                            ft.Text(
                                relation or "-",
                                size=12,
                                color=TEXT_MUTED,
                                width=90,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

    def on_member_search_change(e):
        member_search_query["value"] = e.control.value or ""
        rebuild_member_list()
        safe_update()

    member_search_field.on_change = on_member_search_change

    member_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Select member", size=16, weight=ft.FontWeight.W_700),
        content=ft.Container(
            width=360,
            height=520,
            content=ft.Column(
                [
                    member_search_field,
                    member_list_column,
                ],
                spacing=10,
                expand=True,
            ),
        ),
        actions=[
            ft.TextButton("Close", on_click=close_member_dialog),
        ],
    )

    if member_dialog not in page.overlay:
        page.overlay.append(member_dialog)

    def open_member_dialog(e=None):
        member_search_query["value"] = ""
        member_search_field.value = ""
        rebuild_member_list()
        member_dialog.open = True
        safe_update()

    member_btn.on_tap = open_member_dialog
    refresh_member_button()

    # ---------------- Title Filter ----------------

    title_tf = ft.TextField(
        hint_text="Search expense title",
        prefix_icon=ft.Icons.SEARCH,
        height=42,
        text_size=13,
        border_radius=14,
        bgcolor="#FFFFFF",
        border_color=BORDER,
    )

    def on_title_change(e):
        title_filter["value"] = e.control.value or ""
        refresh()

    title_tf.on_change = on_title_change

    # ---------------- Data Filter ----------------

    def load_filtered_costs():
        costs = load_my_costs_by_date(
            page, 
            start_date.isoformat(),
            end_date.isoformat(),
        )


        if selected_category.get("category_id"):
            categories = load_active_hazineha()

            valid_ids = get_descendant_category_ids(
                categories,
                selected_category["category_id"],
            )

            costs = [
                c for c in costs
                if c.get("id_hazine") in valid_ids
            ]

        if selected_member.get("member_id"):
            costs = [
                c for c in costs
                if c.get("member_id") == selected_member["member_id"]
            ]

        q = (title_filter["value"] or "").strip().lower()

        if q:
            costs = [
                c for c in costs
                if q in (c.get("title") or "").lower()
            ]

        costs = sorted(
            costs,
            key=lambda x: x.get("date_cost") or "",
            reverse=True,
        )

        return costs

    # ---------------- Message Card Like Sabte Hazine ----------------

    def create_report_message(row):
        is_invalid = not row.get("id_hazine")

        title = row.get("title") or "Untitled"
        date_text = row.get("date_cost") or ""
        category_title = row.get("category_title") or ""
        temp_hazine = row.get("temp_hazine") or ""
        member_name = (row.get("member_name") or "").strip()
        price_text = money(row.get("price"))

        shown_category = category_title or temp_hazine

        container = ft.Container(
            padding=12,
            border_radius=16,
            bgcolor="#FEF2F2" if is_invalid else "#FFFFFF",
            border=ft.border.all(
                1,
                "#FCA5A5" if is_invalid else "#E5E7EB",
            ),
            content=ft.Row(
                [
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=12,
                        bgcolor="#ECFDF5" if not is_invalid else "#FEE2E2",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(
                            ft.Icons.RECEIPT,
                            color="#DC2626" if is_invalid else "#16A34A",
                            size=18,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color="#111827",
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.SCHEDULE,
                                                size=11,
                                                color="#6B7280",
                                            ),
                                            ft.Text(
                                                date_text,
                                                size=11,
                                                color="#6B7280",
                                            ),
                                            ft.Text(
                                                "•",
                                                size=10,
                                                color="#9CA3AF",
                                            ) if shown_category else ft.Container(),
                                            ft.Text(
                                                shown_category,
                                                size=11,
                                                color="#DC2626" if is_invalid else "#6B7280",
                                                weight=ft.FontWeight.W_600 if is_invalid else ft.FontWeight.NORMAL,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ) if shown_category else ft.Text(
                                                "No category",
                                                size=11,
                                                color="#DC2626",
                                                weight=ft.FontWeight.W_600,
                                            ),
                                        ],
                                        spacing=4,
                                        tight=True,
                                    ),
                                    ft.Text(
                                        f"{price_text} / {member_name}" if member_name else price_text,
                                        size=10,
                                        color="#6B7280",
                                        weight=ft.FontWeight.W_500,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        container.data = row.get("id")
        return container

    # ---------------- Report List ----------------

    def build_report_list():
        costs = load_filtered_costs()
        total = sum(float(c.get("price") or 0) for c in costs)

        list_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        if not costs:
            list_column.controls.append(
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.RECEIPT_LONG_OUTLINED,
                                size=46,
                                color="#9CA3AF",
                            ),
                            ft.Text(
                                "No expenses found",
                                size=14,
                                color="#9CA3AF",
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                )
            )
        else:
            for row in costs:
                list_column.controls.append(create_report_message(row))

        return ft.Container(
            bgcolor=CARD_BG,
            border=ft.border.all(1, BORDER),
            border_radius=18,
            padding=12,
            expand=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Expense Report",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                                expand=True,
                            ),
                            ft.Text(
                                f"{len(costs)} items",
                                size=12,
                                color=TEXT_MUTED,
                            ),
                            ft.Text(
                                money(total),
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color="#DC2626",
                            ),
                        ],
                        spacing=8,
                    ),
                    list_column,
                ],
                spacing=12,
                expand=True,
            ),
        )

    def refresh():
        saved = page.data.get("report_selected_category")
        if saved:
            selected_category.update(saved)
            refresh_category_button()

        list_holder.content = build_report_list()
        safe_update()

    # ---------------- Layout ----------------

    header = ft.Row(
        [
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                icon_color=TEXT_MAIN,
                icon_size=18,
                width=34,
                height=34,
                on_click=lambda e: page.app_go("sabtehazine"),
            ),
            ft.Text(
                "Expense Report",
                size=22,
                weight=ft.FontWeight.BOLD,
                color=TEXT_MAIN,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    filter_bar = ft.Container(
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(expand=True, content=start_btn),
                        ft.Container(expand=True, content=end_btn),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        ft.Container(expand=True, content=category_btn),
                        ft.Container(expand=True, content=member_btn),
                    ],
                    spacing=8,
                ),
                title_tf,
            ],
            spacing=8,
        ),
    )

    body = ft.Column(
        [
            header,
            filter_bar,
            list_holder,
        ],
        spacing=10,
        expand=True,
    )

    view = ft.View(
        route="/cost_report_view",
        bgcolor=APP_BG,
        controls=[
            ft.Container(
                expand=True,
                padding=10,
                content=body,
            )
        ],
    )

    refresh()
    return view