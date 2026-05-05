import flet as ft
from datetime import datetime, date
from zoneinfo import ZoneInfo
from collections import defaultdict


from services.supabase_service import (
    load_my_costs_by_date,
    load_active_hazineha,
    get_descendant_category_ids,
    get_members,
)

TZ = ZoneInfo("America/Vancouver")


def money(v):
    try:
        return f"${float(v):,.2f}"
    except:
        return "$0.00"


def _summary_cards(costs, from_date, to_date):
    total = _total_expense(costs)

    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        days = max((end - start).days + 1, 1)
    except:
        days = 1

    avg_daily = total / days
    count = len(costs)

    return ft.Row(
        [
            _mini_card("Total Spending", money(total), ft.Icons.PAID_OUTLINED),
            _mini_card("Transactions", str(count), ft.Icons.RECEIPT_LONG_OUTLINED),
            _mini_card("Avg / Day", money(avg_daily), ft.Icons.TRENDING_UP),
        ],
        spacing=8,
    )


def _mini_card(title, value, icon):
    return ft.Container(
        expand=True,
        bgcolor="#FFFFFF",
        border_radius=16,
        padding=12,
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon, size=16, color="#2563EB"),
                        ft.Text(title, size=11, color="#6B7280"),
                    ],
                    spacing=5,
                ),
                ft.Text(
                    value,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color="#111827",
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=6,
        ),
    )

def _category_trends_box(costs):
    category_totals = defaultdict(float)

    for row in costs:
        title = row.get("category_title") or "Unknown"
        category_totals[title] += float(row.get("price") or 0)

    top_items = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:6]

    total = sum(category_totals.values())

    rows = []

    for title, amount in top_items:
        percent = 0 if total == 0 else amount / total

        rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                title,
                                size=12,
                                expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                            ),
                            ft.Text(
                                money(amount),
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                    ),
                    ft.ProgressBar(
                        value=percent,
                        height=6,
                        bgcolor="#E5E7EB",
                        color="#16A34A",
                    ),
                ],
                spacing=3,
            )
        )

    if not rows:
        rows = [ft.Text("No category data", color="#6B7280", size=12)]

    return _card(
        "Category Spending",
        ft.Column(rows, spacing=8),
    )


def _member_spending_box(costs):
    member_totals = defaultdict(float)

    for row in costs:
        name = row.get("member_name") or "No member"
        member_totals[name] += float(row.get("price") or 0)

    top_items = sorted(
        member_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:6]

    rows = []

    for name, amount in top_items:
        rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.PERSON_OUTLINE, size=15, color="#6B7280"),
                    ft.Text(
                        name,
                        size=12,
                        expand=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    ft.Text(
                        money(amount),
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=6,
            )
        )

    if not rows:
        rows = [ft.Text("No member data", color="#6B7280", size=12)]

    return _card(
        "Member Spending",
        ft.Column(rows, spacing=8),
    )


def _recent_transactions_box(costs):
    sorted_costs = sorted(
        costs,
        key=lambda x: x.get("date_cost") or "",
        reverse=True,
    )[:8]

    rows = []

    for row in sorted_costs:
        title = row.get("title") or "Untitled"
        member = row.get("member_name") or "No member"
        amount = float(row.get("price") or 0)
        d = row.get("date_cost") or ""

        rows.append(
            ft.Container(
                padding=10,
                border_radius=12,
                bgcolor="#F9FAFB",
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.RECEIPT_OUTLINED, size=16, color="#DC2626"),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=12,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    f"{d} • {member}",
                                    size=10,
                                    color="#6B7280",
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Text(
                            money(amount),
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

    if not rows:
        rows = [ft.Text("No transactions", color="#6B7280", size=12)]

    return _card(
        "Recent Transactions",
        ft.Column(rows, spacing=8),
    )


def _forecast_box(costs, from_date, to_date):
    total = _total_expense(costs)

    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        days = max((end - start).days + 1, 1)
    except Exception:
        days = 1

    avg_daily = total / days
    projected_30_days = avg_daily * 30

    return _card(
        "Forecast",
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Average daily spending", expand=True, size=12),
                        ft.Text(money(avg_daily), weight=ft.FontWeight.W_600),
                    ],
                ),
                ft.Row(
                    [
                        ft.Text("Projected 30-day spending", expand=True, size=12),
                        ft.Text(money(projected_30_days), weight=ft.FontWeight.W_600),
                    ],
                ),
            ],
            spacing=8,
        ),
    )


def _daily_spending_box(costs):
    daily_totals = {}

    for row in costs:
        d = str(row.get("date_cost") or "Unknown")[:10]
        daily_totals[d] = daily_totals.get(d, 0) + float(row.get("price") or 0)

    def sort_date(item):
        d, _ = item
        try:
            return date.fromisoformat(d)
        except:
            return date.min

    items = sorted(daily_totals.items(), key=sort_date, reverse=True)
    max_amount = max([amount for _, amount in items], default=0)

    daily_list = ft.ListView(
        height=245,
        spacing=10,
        padding=ft.padding.only(right=4),
        auto_scroll=False,
    )

    if not items:
        daily_list.controls.append(
            ft.Container(
                height=120,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("No daily spending yet", color="#9CA3AF", size=12),
            )
        )
    else:
        for index, (d, amount) in enumerate(items):
            percent = 0 if max_amount == 0 else amount / max_amount

            try:
                parsed_date = date.fromisoformat(d)
                day_label = parsed_date.strftime("%a")
            except:
                day_label = ""

            is_today = d == today_local().isoformat()

            daily_list.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=14,
                    bgcolor="#EFF6FF" if is_today else "#F9FAFB",
                    border=ft.border.all(
                        1,
                        "#93C5FD" if is_today else "#E5E7EB",
                    ),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=12,
                                        bgcolor="#2563EB" if is_today else "#FFFFFF",
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    day_label,
                                                    size=9,
                                                    color="#FFFFFF" if is_today else "#6B7280",
                                                    weight=ft.FontWeight.W_600,
                                                ),
                                                ft.Text(
                                                    d[-2:] if d != "Unknown" else "?",
                                                    size=13,
                                                    color="#FFFFFF" if is_today else "#111827",
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                            ],
                                            spacing=0,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                    ),

                                    ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.Text(
                                                        "Today" if is_today else d,
                                                        size=13,
                                                        weight=ft.FontWeight.W_700,
                                                        color="#111827",
                                                        expand=True,
                                                    ),
                                                    ft.Text(
                                                        money(amount),
                                                        size=13,
                                                        weight=ft.FontWeight.BOLD,
                                                        color="#DC2626",
                                                    ),
                                                ],
                                            ),
                                            ft.ProgressBar(
                                                value=percent,
                                                height=7,
                                                bgcolor="#E5E7EB",
                                                color="#2563EB",
                                            ),
                                        ],
                                        spacing=7,
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                    ),
                )
            )

    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=18,
        padding=14,
        border=ft.border.all(1, "#E5E7EB"),
        shadow=ft.BoxShadow(
            blur_radius=14,
            spread_radius=0,
            color="#12000000",
            offset=ft.Offset(0, 4),
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=36,
                            height=36,
                            border_radius=12,
                            bgcolor="#EFF6FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.CALENDAR_MONTH_OUTLINED,
                                size=18,
                                color="#2563EB",
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Daily Spending",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color="#111827",
                                ),
                                ft.Text(
                                    "Newest days first",
                                    size=11,
                                    color="#6B7280",
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),

                daily_list,
            ],
            spacing=12,
        ),
    )

def _spending_page(filters):
    costs = _filter_costs(filters)

    return ft.Container(
        padding=12,
        content=ft.Column(
            [
                _summary_cards(
                    costs,
                    filters["from_date"],
                    filters["to_date"],
                ),
                _daily_spending_box(costs),
                _category_trends_box(costs),
                _member_spending_box(costs),
                _forecast_box(
                    costs,
                    filters["from_date"],
                    filters["to_date"],
                ),
                _recent_transactions_box(costs),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

def today_local():
    return datetime.now(TZ).date()


def _total_expense(costs):
    return sum(float(row.get("price") or 0) for row in costs)


def _filter_costs(filters):
    costs = load_my_costs_by_date(
        filters["from_date"],
        filters["to_date"],
    )

    if filters.get("category_id"):
        categories = load_active_hazineha()
        valid_ids = get_descendant_category_ids(
            categories,
            filters["category_id"],
        )

        costs = [
            c for c in costs
            if c.get("id_hazine") in valid_ids
        ]

    if filters.get("member_id"):
        costs = [
            c for c in costs
            if c.get("member_id") == filters["member_id"]
        ]

    return costs


def _card(title, content):
    return ft.Container(
        bgcolor="#FFFFFF",
        border_radius=16,
        padding=12,
        content=ft.Column(
            [
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                content,
            ],
            spacing=8,
        ),
    )

def _category_trends_box(costs):
    category_totals = {}

    for row in costs:
        title = row.get("category_title") or "Unknown"
        category_totals[title] = category_totals.get(title, 0) + float(row.get("price") or 0)

    top_items = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    rows = []

    for title, amount in top_items:
        rows.append(
            ft.Row(
                [
                    ft.Text(title, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{amount:,.0f}"),
                ],
                spacing=8,
            )
        )

    if not rows:
        rows = [ft.Text("No category data", color="#6B7280")]

    return _card(
        "Category Trends",
        ft.Container(
            height=180,
            bgcolor="#F9FAFB",
            border_radius=12,
            padding=10,
            content=ft.Column(rows, spacing=6),
        ),
    )


def _forecast_box(costs, from_date, to_date):
    total = _total_expense(costs)

    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        days = max((end - start).days + 1, 1)
    except Exception:
        days = 1

    avg_daily = total / days
    projected_30_days = avg_daily * 30

    return _card(
        "Forecast",
        ft.Column(
            [
                ft.Text(f"Average daily spending: {avg_daily:,.0f}"),
                ft.Text(f"Projected 30-day spending: {projected_30_days:,.0f}"),
            ],
            spacing=6,
        ),
    )



def _budget_page():
    return ft.Container(
        padding=20,
        content=ft.Text("Budget trends will be added later."),
    )


def _insights_page():
    return ft.Container(
        padding=20,
        content=ft.Text("Insights will be added later."),
    )


def trend_view(page: ft.Page):
    APP_BG = "#F3F4F6"
    CARD_BG = "#FFFFFF"
    PRIMARY = "#2563EB"
    TEXT_MAIN = "#111827"
    TEXT_MUTED = "#6B7280"
    BORDER = "#E5E7EB"

    if not isinstance(page.data, dict):
        page.data = {}

    start_date = today_local().replace(day=1)
    end_date = today_local()

    selected_tab = {"value": "spending"}

    selected_category = page.data.get("trend_selected_category") or {
        "category_id": None,
        "category_title": "All categories",
    }

    selected_member = {
        "member_id": None,
        "member_name": "All members",
    }

    filters = {
        "from_date": start_date.isoformat(),
        "to_date": end_date.isoformat(),
        "category_id": None,
        "member_id": None,
    }

    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    def read_filters():
        filters["from_date"] = start_date.isoformat()
        filters["to_date"] = end_date.isoformat()
        filters["category_id"] = selected_category["category_id"]
        filters["member_id"] = selected_member["member_id"]

    def build_filter_button(label, icon):
        return ft.Container(
            expand=True,
            height=42,
            border=ft.border.all(1, BORDER),
            border_radius=14,
            bgcolor="#FFFFFF",
            padding=ft.padding.symmetric(horizontal=14),
            alignment=ft.Alignment.CENTER_LEFT,
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=PRIMARY),
                    ft.Text(
                        label,
                        size=13,
                        color=TEXT_MAIN,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                        expand=True,
                    ),
                ],
                spacing=8,
            ),
        )

    content_container = ft.Container(expand=True)
    tabs_holder = ft.Container()

    # ---------------- Date Pickers ----------------

    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)

    if start_picker not in page.overlay:
        page.overlay.append(start_picker)

    if end_picker not in page.overlay:
        page.overlay.append(end_picker)

    def open_start_picker(e=None):
        start_picker.open = True
        safe_update()

    def open_end_picker(e=None):
        end_picker.open = True
        safe_update()

    start_btn = ft.GestureDetector(
        on_tap=open_start_picker,
        content=build_filter_button(
            f"Fr: {start_date}",
            ft.Icons.CALENDAR_MONTH,
        ),
    )

    end_btn = ft.GestureDetector(
        on_tap=open_end_picker,
        content=build_filter_button(
            f"To: {end_date}",
            ft.Icons.DATE_RANGE,
        ),
    )

    def update_start(e):
        nonlocal start_date

        if not start_picker.value:
            return

        picked = start_picker.value

        if isinstance(picked, datetime):
            picked = picked.date()

        start_date = picked

        start_btn.content = build_filter_button(
            f"From: {start_date}",
            ft.Icons.CALENDAR_MONTH,
        )

        refresh()

    def update_end(e):
        nonlocal end_date

        if not end_picker.value:
            return

        picked = end_picker.value

        if isinstance(picked, datetime):
            picked = picked.date()

        end_date = picked

        end_btn.content = build_filter_button(
            f"To: {end_date}",
            ft.Icons.DATE_RANGE,
        )

        refresh()

    start_picker.on_change = update_start
    end_picker.on_change = update_end

    # ---------------- Category Picker ----------------

    category_btn = ft.GestureDetector(
        content=build_filter_button(
            selected_category["category_title"],
            ft.Icons.ACCOUNT_TREE_OUTLINED,
        )
    )
    # restore UI

    def refresh_category_button():
        category_btn.content = build_filter_button(
            selected_category["category_title"],
            ft.Icons.ACCOUNT_TREE_OUTLINED,
        )

    refresh_category_button()

    def on_category_selected(result: dict):
        selected_category["category_id"] = result.get("category_id")
        selected_category["category_title"] = result.get("category_title") or "All categories"

        # ✅ ذخیره در state
        page.data["trend_selected_category"] = selected_category

        refresh_category_button()
        refresh()
        
    def choose_category(e=None):
        page.data["without_edit"] = True
        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = selected_category["category_id"]
        page.data["category_picker_on_selected"] = on_category_selected
        page.data["from"] = "trend_view"

        page.app_go("hazinaha_view")

    category_btn.on_tap = choose_category

    # ---------------- Member Picker ----------------

    members_data = get_members()
    member_search_query = {"value": ""}

    member_list_column = ft.Column(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    member_search_field = ft.TextField(
        hint_text="Search member",
        prefix_icon=ft.Icons.SEARCH,
        text_size=13,
    )

    member_btn = ft.GestureDetector(
        content=build_filter_button(
            selected_member["member_name"],
            ft.Icons.PERSON_OUTLINE,
        )
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
        selected_member["member_name"] = member_name

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
                        ft.Text(
                            "-",
                            size=12,
                            color=TEXT_MUTED,
                            width=90,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
                            ft.Icon(ft.Icons.PERSON_OUTLINE, size=17, color=TEXT_MUTED),
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
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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

    # ---------------- Tabs Without ft.Tabs ----------------

    def build_current_page():
        if selected_tab["value"] == "spending":
            return _spending_page(filters)

        if selected_tab["value"] == "budget":
            return _budget_page()

        return _insights_page()

    def change_tab(key):
        selected_tab["value"] = key
        refresh()

    def build_tab_button(title, key):
        is_selected = selected_tab["value"] == key

        return ft.Container(
            content=ft.Text(
                title,
                color="#FFFFFF" if is_selected else TEXT_MAIN,
                weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.W_500,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=10),
            border_radius=20,
            bgcolor="#111827" if is_selected else "#E5E7EB",
            on_click=lambda e: change_tab(key),
        )

    def build_tabs_row():
        return ft.Row(
            [
                build_tab_button("Spending", "spending"),
                build_tab_button("Budget", "budget"),
                build_tab_button("Insights", "insights"),
            ],
            spacing=8,
            wrap=True,
        )
    
    def refresh():
        # ✅ restore category
        saved = page.data.get("trend_selected_category")
        if saved:
            selected_category.update(saved)
            refresh_category_button()

        read_filters()
        tabs_holder.content = build_tabs_row()
        content_container.content = build_current_page()
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
                on_click=lambda e: page.app_go("dashboard_view"),
            ),
            ft.Text("Trends", size=22, weight=ft.FontWeight.BOLD),
        ],
        alignment=ft.MainAxisAlignment.START,
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
            ],
            spacing=8,
        ),
    )

    body = ft.Column(
        [
            header,
            filter_bar,
            tabs_holder,
            content_container,
        ],
        spacing=10,
        expand=True,
    )

    view = ft.View(
        route="/trend_view",
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