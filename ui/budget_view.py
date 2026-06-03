import flet as ft
from services.i18n import t
import asyncio
from services.utils import today_local

from services.supabase_service import (
    get_budget_page_data,
    upsert_budget,
    delete_budget,
    calculate_budget_spent,
    get_descendant_category_ids,
    carry_budgets_to_current_month,
    clear_hazineha_cache,
)


def budget_view(page: ft.Page, year_month: str | None = None):
    page.data = page.data or {}

    if not year_month:
        year_month = today_local(page).strftime("%Y-%m")



    editing_category_id = {"value": None}
    editing_value = {"value": ""}

    selected_id = {"value": None}
    row_controls = {}

    tree_column = ft.ListView(
        spacing=6,
        expand=True,
        padding=0,
        auto_scroll=False,
    )


    tree_column.controls.append(
        ft.Container(
            height=220,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                [
                    ft.ProgressRing(width=28, height=28, stroke_width=3),
                    ft.Text(t(page, "Budget_Loading"), size=12, color="#6B7280"),
                ],
                spacing=10,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
    )


    summary_row = ft.Row(spacing=10)

    data = {"categories": [], "budgets": [], "costs": []}
    budgets = {}

    spent_cache = {}
    children_budget_cache = {}

    expanded_nodes = {"ids": set()}

    # def get_from_route():
    #     if page.data.get("from") == "dashboard_view":
    #         return "/dashboard_view"

    #     return "/sabtehazine"

    def get_from_view():
        if page.data.get("from") == "dashboard_view":
            return "dashboard_view"

        return "sabtehazine"
    
    def go_back(e):
        page.app_go(get_from_view())   # یا هر صفحه‌ای که می‌خوای برگرده

    def is_expanded(category_id):
        return category_id in expanded_nodes["ids"]

    def apply_row_style(row_control, category_id):
        is_selected = selected_id["value"] == category_id

        row_control.bgcolor = "#EAF2FF" if is_selected else "#FFFFFF"

        if is_selected:
            row_control.border = ft.border.all(1, "#93C5FD")
        else:
            row_control.border = None


    def refresh_selected_row_styles():
        for cid, row_control in row_controls.items():
            apply_row_style(row_control, cid)

        page.update()

    def build_unbudgeted_spent_info(category_id):
        amount = 0
        spent = get_category_spent(category_id)
        remaining = amount - spent
        color = status_color(amount, spent)

        info = ft.Column(
            [
                ft.Text(
                    f"{spent:,.0f} / {amount:,.0f}",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.ProgressBar(
                    value=0,
                    width=110,
                    height=5,
                    color=color,
                    bgcolor="#E5E7EB",
                ),
                ft.Text(
                    f"{t(page, 'Budget_Remaining')}: {remaining:,.0f}",
                    size=10,
                    color=color,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        actions = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_size=15,
                    width=26,
                    height=26,
                    style=ft.ButtonStyle(padding=0),
                    on_click=lambda e, cid=category_id: start_edit(cid),
                ),
            ],
            spacing=2,
            tight=True,
        )

        return build_budget_right_layout(
            info,
            actions,
            show_actions=is_row_selected(category_id),
        )

    def select_category(category_id):
        if selected_id["value"] == category_id:
            return

        selected_id["value"] = category_id
        refresh_selected_row_styles()


    def toggle_expand(category_id):
        if category_id in expanded_nodes["ids"]:
            expanded_nodes["ids"].remove(category_id)
        else:
            expanded_nodes["ids"].add(category_id)

        rebuild()

    budget_carried = {"done": False}

    def refresh_data():
        nonlocal data, budgets, spent_cache, children_budget_cache
    
        spent_cache.clear()

        children_budget_cache.clear()
        
        if page.data.get("hazineha_changed"):
            clear_hazineha_cache()
            page.data["hazineha_changed"] = False

        carry_key = f"budget_carried_{year_month}"

        if not page.data.get(carry_key):
            try:
                carry_budgets_to_current_month(page)
            except Exception as ex:
                print("BUDGET_CARRY_ERROR:", ex)

            page.data[carry_key] = True
            
        data = get_budget_page_data(year_month)

        categories = data["categories"]
        costs = data["costs"]

        budgets = {}

        for row in data["budgets"]:
            category_id = row["category_id"]
            amount = float(row.get("amount") or 0)

            spent = calculate_budget_spent(
                categories,
                costs,
                category_id,
            )

            spent_cache[category_id] = spent

            budgets[category_id] = {
                "amount": amount,
                "spent": spent,
            }


        # ریشه‌ها باز باشند
        expanded_nodes["ids"].clear()
        for root in get_budget_roots():
            expanded_nodes["ids"].add(root["id"])

    def get_children(parent_id):
        if parent_id is None:
            return [
                c for c in data["categories"]
                if c.get("id_parent") in (None, 0)
            ]

        return [
            c for c in data["categories"]
            if c.get("id_parent") == parent_id
        ]

    def get_category_title(category_id):
        for c in data["categories"]:
            if c.get("id") == category_id:
                return c.get("title") or ""
        return ""

    def get_category_spent(category_id):
        if category_id in spent_cache:
            return spent_cache[category_id]

        spent = calculate_budget_spent(
            data["categories"],
            data["costs"],
            category_id,
        )

        spent_cache[category_id] = spent
        return spent


    def has_spending_in_category_or_children(category_id):
        return get_category_spent(category_id) > 0

    def has_budget_in_parent(category_id):
        current = next(
            (c for c in data["categories"] if c.get("id") == category_id),
            None,
        )

        while current and current.get("id_parent"):
            parent_id = current.get("id_parent")

            if parent_id in budgets:
                return parent_id

            current = next(
                (c for c in data["categories"] if c.get("id") == parent_id),
                None,
            )

        return None

    def has_budget_in_children(category_id):
        for child in get_children(category_id):
            child_id = child["id"]

            if child_id in budgets:
                return True

            if has_budget_in_children(child_id):
                return True

        return False


    def get_children_budget_total(category_id):
        if category_id in children_budget_cache:
            return children_budget_cache[category_id]

        total_amount = 0

        descendant_ids = get_descendant_category_ids(
            data["categories"],
            category_id,
        )

        for cid in descendant_ids:
            if cid in budgets:
                total_amount += budgets[cid]["amount"]

        total_spent = get_category_spent(category_id)

        result = {
            "amount": total_amount,
            "spent": total_spent,
        }

        children_budget_cache[category_id] = result
        return result 
 


    def get_budget_roots():
        return [
            c for c in data["categories"]
            if c.get("id_parent") in (None, 0)
        ]
    
    def start_edit(category_id):
        selected_id["value"] = category_id
        editing_category_id["value"] = category_id

        if category_id in budgets:
            editing_value["value"] = str(budgets[category_id]["amount"])
        else:
            editing_value["value"] = ""

        rebuild()

    def cancel_edit():
        editing_category_id["value"] = None
        editing_value["value"] = ""
        rebuild()

    def save_budget(category_id):
        raw = (editing_value["value"] or "").strip()

        try:
            amount = float(raw)
        except Exception:
            page.snack_bar = ft.SnackBar(
                ft.Text("Please enter a valid budget amount.")
            )
            page.snack_bar.open = True
            page.update()
            return

        if amount < 0:
            page.snack_bar = ft.SnackBar(
                ft.Text("Budget amount cannot be negative.")
            )
            page.snack_bar.open = True
            page.update()
            return

        try:
            upsert_budget(category_id, amount, year_month)
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(str(ex))
            )
            page.snack_bar.open = True
            page.update()
            return

        categories = data["categories"]
        costs = data["costs"]

        budgets[category_id] = {
            "amount": amount,
            "spent": calculate_budget_spent(
                categories,
                costs,
                category_id,
            ),
        }

        editing_category_id["value"] = None
        editing_value["value"] = ""
        selected_id["value"] = category_id
        
        rebuild()
        
    def remove_budget(category_id):
        delete_budget(category_id, year_month)

        budgets.pop(category_id, None)

        editing_category_id["value"] = None
        editing_value["value"] = ""

        rebuild()

    def progress_value(amount, spent):
        try:
            amount = float(amount or 0)
            spent = float(spent or 0)
        except Exception:
            return 0

        if amount <= 0:
            return 0

        value = spent / amount

        if value < 0:
            return 0

        if value > 1:
            return 1

        return value


    def status_color(amount, spent):
        try:
            amount = float(amount or 0)
            spent = float(spent or 0)
        except Exception:
            return "#6B7280"

        if spent < 0:
            return "#16A34A"

        if amount <= 0:
            return "#DC2626" if spent > 0 else "#6B7280"

        percent = spent / amount

        if percent < 0.7:
            return "#16A34A"

        if percent <= 1:
            return "#D97706"

        return "#DC2626"



    def is_row_selected(category_id):
        return selected_id["value"] == category_id

    def build_budget_right_layout(info_control, actions_control=None, show_actions=False):
        if show_actions and actions_control:
            return ft.Row(
                [
                    ft.Container(
                        content=info_control,
                        width=95,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.Container(
                        content=actions_control,
                        width=54,
                        alignment=ft.Alignment.CENTER_RIGHT,
                    ),
                ],
                spacing=2,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        return ft.Container(
            content=info_control,
            width=135,
            alignment=ft.Alignment.CENTER_RIGHT,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )



    def build_budget_info(category_id):
        amount = budgets[category_id]["amount"]
        spent = budgets[category_id]["spent"]
        remaining = amount - spent
        percent = progress_value(amount, spent)
        color = status_color(amount, spent)

        info = ft.Column(
            [
                ft.Text(
                    f"{spent:,.0f} / {amount:,.0f}",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.ProgressBar(
                    value=percent,
                    width=95,
                    height=5,
                    color=color,
                    bgcolor="#E5E7EB",
                ),
                ft.Text(
                    f"{t(page, 'Budget_Remaining')}: {remaining:,.0f}",
                    size=10,
                    color=color,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        actions = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_size=15,
                    width=26,
                    height=26,
                    style=ft.ButtonStyle(padding=0),
                    on_click=lambda e, cid=category_id: start_edit(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=15,
                    width=26,
                    height=26,
                    style=ft.ButtonStyle(padding=0),
                    on_click=lambda e, cid=category_id: remove_budget(cid),
                ),
            ],
            spacing=2,
            tight=True,
        )

        return build_budget_right_layout(
            info,
            actions,
            show_actions=is_row_selected(category_id),
        )

    def build_children_budget_info(category_id):
        total = get_children_budget_total(category_id)

        amount = total["amount"]
        spent = total["spent"]
        remaining = amount - spent

        percent = progress_value(amount, spent)
        color = status_color(amount, spent)

        info = ft.Column(
            [
                ft.Text(
                    f"{spent:,.0f} / {amount:,.0f}",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.RIGHT,
                ),
                ft.ProgressBar(
                    value=percent,
                    width=90,
                    height=5,
                    color=color,
                    bgcolor="#E5E7EB",
                ),
                ft.Text(
                    f"{t(page, 'Budget_Remaining')}: {remaining:,.0f}",
                    size=10,
                    color=color,
                    text_align=ft.TextAlign.RIGHT,
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        return build_budget_right_layout(
            info,
            None,
            show_actions=False,
        )



    def build_edit_box(category_id):
        return ft.Row(
            [
                ft.TextField(
                    value=editing_value["value"],
                    width=82,
                    height=34,
                    text_size=12,
                    dense=True,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    hint_text=t(page, "edit_cost_price"),
                    content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    on_change=lambda e: editing_value.update(
                        {"value": e.control.value}
                    ),
                    on_submit=lambda e, cid=category_id: save_budget(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    icon_size=17,
                    width=30,
                    height=30,
                    style=ft.ButtonStyle(padding=0),
                    tooltip="ذخیره",
                    on_click=lambda e, cid=category_id: save_budget(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=17,
                    width=30,
                    height=30,
                    style=ft.ButtonStyle(padding=0),
                    tooltip=t(page, "edit_cost_regect"),
                    on_click=lambda e: cancel_edit(),
                ),
            ],
            spacing=2,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )



    def build_category_rows(category, level=0):
        category_id = category["id"]
        title = category.get("title") or ""

        children = get_children(category_id)
        has_children = len(children) > 0

        is_editing = editing_category_id["value"] == category_id
        has_own_budget = category_id in budgets
        parent_budget_id = has_budget_in_parent(category_id)
        child_has_budget = has_budget_in_children(category_id)
        has_own_spending = has_spending_in_category_or_children(category_id)

        left_padding = level * 18

        expand_button = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_DOWN if is_expanded(category_id) else ft.Icons.KEYBOARD_ARROW_RIGHT,
            icon_size=16,
            width=28,
            height=28,
            on_click=lambda e, cid=category_id: toggle_expand(cid),
        ) if has_children else ft.Container(width=28)

        title_part = ft.Row(
            [
                ft.Container(width=left_padding),
                expand_button,
                ft.Container(
                    expand=True,
                    content=ft.Text(
                        title,
                        size=12 if is_editing else 13,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                        tooltip=title,
                    )
                )                

            ],
            spacing=2,
            expand=True,
        )

        right_width = 145

        if is_editing:
            right_part = build_edit_box(category_id)
            right_width = 150
            
        elif parent_budget_id and not has_own_budget:
            right_part = ft.Text(
                f"Included in {get_category_title(parent_budget_id)}",
                size=10,
                color="#9CA3AF",
            )
        elif has_own_budget:
            right_part = build_budget_info(category_id)

        elif child_has_budget or has_own_spending:
            right_part = build_children_budget_info(category_id)

        else:
            right_part = ft.TextButton(
                content=ft.Text(t(page, "Budget_Budget"), size=12),
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=8, vertical=0),
                ),
                on_click=lambda e, cid=category_id: start_edit(cid),
            )

        row = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=title_part,
                        expand=True,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.Container(
                        content=right_part,
                        width=right_width,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            border_radius=9,
            bgcolor="#FFFFFF",
            on_click=lambda e, cid=category_id: select_category(cid),
            on_hover=lambda e, cid=category_id: (
                setattr(
                    e.control,
                    "bgcolor",
                    "#F3F7FF" if e.data == "true" and selected_id["value"] != cid
                    else "#EAF2FF" if selected_id["value"] == cid
                    else "#FFFFFF"
                ),
                e.control.update()
            ),
        )


        row_controls[category_id] = row
        apply_row_style(row, category_id)

        rows = [row]

        if has_children and is_expanded(category_id):
            for child in children:
                rows.extend(build_category_rows(child, level + 1))

        return rows


    def rebuild_summary():
        summary_row.controls.clear()

        total_budget = sum(b["amount"] for b in budgets.values())

        total_spent = sum(
            float(row.get("price") or 0)
            for row in data["costs"]
        )

        total_remaining = total_budget - total_spent

        summary_row.controls.extend(
            [
                build_summary_chip(
                    "Budget",
                    f"{total_budget:,.0f}",
                    ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    "#2563EB",
                ),
                build_summary_chip(
                    "Spent",
                    f"{total_spent:,.0f}",
                    ft.Icons.TRENDING_UP_ROUNDED,
                    "#DC2626",
                ),
                build_summary_chip(
                    "Left",
                    f"{total_remaining:,.0f}",
                    ft.Icons.SAVINGS_OUTLINED,
                    "#16A34A" if total_remaining >= 0 else "#DC2626",
                ),
            ]
        )


    def rebuild(do_update=True):
        try:
            new_controls = []
            row_controls.clear()

            rebuild_summary()

            root_categories = get_budget_roots()

            for root in root_categories:
                new_controls.extend(build_category_rows(root, 0))

            tree_column.controls.clear()
            tree_column.controls.extend(new_controls)

            if do_update:
                page.update()

        except Exception as ex:
            print("BUDGET_REBUILD_ERROR:", ex)
    # refresh_data()

    def build_summary_chip(label, value, icon, color):
        return ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E5E7EB"),
            content=ft.Row(
                [
                    ft.Container(
                        width=28,
                        height=28,
                        border_radius=9,
                        bgcolor="#F8FAFC",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, size=15, color=color),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                label,
                                size=9,
                                color="#64748B",
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                value,
                                size=13,
                                weight=ft.FontWeight.W_800,
                                color="#0F172A",
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=0,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    header = ft.Container(
        padding=ft.padding.only(left=10, right=10, top=8, bottom=10),
        border_radius=18,
        bgcolor="#F8FAFC",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=52,
                            height=52,
                            border_radius=16,
                            bgcolor="#FFFFFF",
                            border=ft.border.all(1, "#E5E7EB"),
                            alignment=ft.Alignment.CENTER,
                            ink=True,
                            on_click=go_back,
                            content=ft.Icon(
                                ft.Icons.ARROW_BACK_IOS_NEW,
                                size=22,
                                color="#0F172A",
                            ),
                        ),

                        ft.Container(
                            width=38,
                            height=38,
                            border_radius=13,
                            bgcolor="#EEF2FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.PIE_CHART_OUTLINE_ROUNDED,
                                size=20,
                                color="#2563EB",
                            ),
                        ),

                        ft.Column(
                            [
                                ft.Text(
                                    "Budget",
                                    size=16,
                                    weight=ft.FontWeight.W_800,
                                    color="#0F172A",
                                ),
                                ft.Text(
                                    year_month,
                                    size=11,
                                    color="#64748B",
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=0,
                            tight=True,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),

                summary_row,
            ],
            spacing=8,
            tight=True,
        ),
    )

    content = ft.Column(
        [
            header,
            ft.Container(
                content=tree_column,
                padding=8,
                border_radius=16,
                bgcolor="#F3F4F6",
                expand=True,
            ),
        ],
        spacing=8,
        expand=True,
    )

    async def load_after_mount():
        await asyncio.sleep(0.05)

        try:
            await asyncio.to_thread(refresh_data)
            rebuild(do_update=True)
        except Exception as ex:
            print("BUDGET_LOAD_AFTER_MOUNT_ERROR:", ex)
            

    page.run_task(load_after_mount)
    
    
    body_content = ft.Container(
        content=content,
        expand=True,
        padding=ft.padding.only(
            top=48,
            left=10,
            right=10,
            bottom=4 if page.platform == ft.PagePlatform.ANDROID else 10,
        ),
    )

    if page.platform == ft.PagePlatform.ANDROID:
        page_body = ft.SafeArea(
            expand=True,
            avoid_intrusions_top=False,
            avoid_intrusions_left=False,
            avoid_intrusions_right=False,
            avoid_intrusions_bottom=True,
            content=body_content,
        )
    else:
        page_body = body_content


    return ft.View(
        route="/budget_view",
        controls=[
            page_body,
        ],
        bgcolor="#FFFFFF",
        padding=0,
        spacing=0,
    )