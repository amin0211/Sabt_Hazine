import flet as ft
from datetime import datetime, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()


from services.supabase_service import (
    get_budget_page_data,
    upsert_budget,
    delete_budget,
    calculate_budget_spent,
    carry_budgets_to_current_month,
)


def budget_view(page: ft.Page, year_month: str | None = None):
    if not year_month:
        year_month = today_local().strftime("%Y-%m")

    if not year_month:
        year_month = today_local().strftime("%Y-%m")



    editing_category_id = {"value": None}
    editing_value = {"value": ""}

    tree_column = ft.Column(
        spacing=5,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )   
    summary_row = ft.Row(spacing=10)

    data = {"categories": [], "budgets": [], "costs": []}
    budgets = {}

    expanded_nodes = {"ids": set()}

    def get_from_route():
        if page.data.get("from") == "dashboard_view":
            return "/dashboard_view"

        return "/sabtehazine"

    def go_back(e):
        page.go(get_from_route())   # یا هر صفحه‌ای که می‌خوای برگرده

    def is_expanded(category_id):
        return category_id in expanded_nodes["ids"]


    def toggle_expand(category_id):
        if category_id in expanded_nodes["ids"]:
            expanded_nodes["ids"].remove(category_id)
        else:
            expanded_nodes["ids"].add(category_id)

        rebuild()

    def refresh_data():
        nonlocal data, budgets

        carry_budgets_to_current_month()


        data = get_budget_page_data(year_month)
        print("BUDGET DATA:", data)
        print("CATEGORIES COUNT:", len(data.get("categories", [])))
        print("FIRST CATEGORIES:", data.get("categories", [])[:5])



        for root in get_budget_roots():
            expanded_nodes["ids"].add(root["id"])
            
        # print("CATEGORIES:", data["categories"][:5])
        categories = data["categories"]
        costs = data["costs"]

        budgets = {
            row["category_id"]: {
                "amount": float(row.get("amount") or 0),
                "spent": calculate_budget_spent(
                    categories,
                    costs,
                    row["category_id"],
                ),
            }
            for row in data["budgets"]
        }

    # def get_children(parent_id):
    #     return [
    #         c for c in data["categories"]
    #         if c.get("id_parent") == parent_id
    #     ]


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

    def get_budget_roots():
        return [
            c for c in data["categories"]
            if c.get("id_parent") in (None, 0)
        ]
    
    def start_edit(category_id):
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
                ft.Text("مبلغ بودجه معتبر نیست")
            )
            page.snack_bar.open = True
            page.update()
            return

        if amount < 0:
            page.snack_bar = ft.SnackBar(
                ft.Text("مبلغ بودجه نمی‌تواند منفی باشد")
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

        editing_category_id["value"] = None
        editing_value["value"] = ""

        refresh_data()
        rebuild()

    def remove_budget(category_id):
        delete_budget(category_id, year_month)

        editing_category_id["value"] = None
        editing_value["value"] = ""

        refresh_data()
        rebuild()

    def status_color(amount, spent):
        if amount <= 0:
            return "#6B7280"

        percent = spent / amount

        if percent < 0.7:
            return "#16A34A"

        if percent <= 1:
            return "#D97706"

        return "#DC2626"

    def build_budget_info(category_id):
        amount = budgets[category_id]["amount"]
        spent = budgets[category_id]["spent"]
        remaining = amount - spent
        percent = 0 if amount <= 0 else min(spent / amount, 1)
        color = status_color(amount, spent)

        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            f"{spent:,.0f} / {amount:,.0f}",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.ProgressBar(
                            value=percent,
                            width=105,
                            height=5,
                            color=color,
                            bgcolor="#E5E7EB",
                        ),
                        ft.Text(
                            f"مانده: {remaining:,.0f}",
                            size=10,
                            color=color,
                        ),
                    ],
                    spacing=2,
                ),
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_size=17,
                    tooltip="ویرایش بودجه",
                    on_click=lambda e, cid=category_id: start_edit(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=17,
                    tooltip="حذف بودجه",
                    on_click=lambda e, cid=category_id: remove_budget(cid),
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def build_edit_box(category_id):
        return ft.Row(
            [
                ft.TextField(
                    value=editing_value["value"],
                    width=95,
                    height=36,
                    text_size=12,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    hint_text="مبلغ",
                    on_change=lambda e: editing_value.update(
                        {"value": e.control.value}
                    ),
                    on_submit=lambda e, cid=category_id: save_budget(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    icon_size=18,
                    tooltip="ذخیره",
                    on_click=lambda e, cid=category_id: save_budget(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_size=18,
                    tooltip="لغو",
                    on_click=lambda e: cancel_edit(),
                ),
            ],
            spacing=0,
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
                ft.Text(title, size=13, weight=ft.FontWeight.W_500),
            ],
            spacing=2,
            expand=True,
        )

        if is_editing:
            right_part = build_edit_box(category_id)

        elif parent_budget_id and not has_own_budget:
            right_part = ft.Text(
                f"Included in {get_category_title(parent_budget_id)}",
                size=10,
                color="#9CA3AF",
            )

        elif has_own_budget:
            right_part = build_budget_info(category_id)

        elif child_has_budget:
            right_part = ft.Text(
                "بودجه در زیرمجموعه دارد",
                size=10,
                color="#9CA3AF",
            )

        else:
            right_part = ft.TextButton(
                content=ft.Text("+ بودجه", size=12),
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=8, vertical=0),
                ),
                on_click=lambda e, cid=category_id: start_edit(cid),
            )

        row = ft.Container(
            content=ft.Row(
                [title_part, right_part],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=5),
            border_radius=9,
            bgcolor="#FFFFFF",
        )

        rows = [row]

        if has_children and is_expanded(category_id):
            for child in children:
                rows.extend(build_category_rows(child, level + 1))

        return rows

    def rebuild_summary():
        summary_row.controls.clear()

        total_budget = sum(b["amount"] for b in budgets.values())
        total_spent = sum(b["spent"] for b in budgets.values())
        total_remaining = total_budget - total_spent

        summary_row.controls.extend(
            [
                ft.Column(
                    [
                        ft.Text("Total Budget", size=11, color="#6B7280"),
                        ft.Text(
                            f"{total_budget:,.0f}",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Text("Spent", size=11, color="#6B7280"),
                        ft.Text(
                            f"{total_spent:,.0f}",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Text("Remaining", size=11, color="#6B7280"),
                        ft.Text(
                            f"{total_remaining:,.0f}",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    expand=True,
                ),
            ]
        )

    def rebuild():
        tree_column.controls.clear()
        rebuild_summary()

        

        root_categories = get_budget_roots()

        for root in root_categories:
            for row in build_category_rows(root, 0):
                tree_column.controls.append(row)

        page.update()

    # refresh_data()

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_size=20,
                            tooltip="Back",
                            on_click=go_back,
                        ),
                        ft.Text(
                            f"Budget - {year_month}",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                summary_row,
            ],
            spacing=10,
        ),
        padding=14,
        border_radius=14,
        bgcolor="#F9FAFB",
    )

    content = ft.Column(
        [
            header,
            ft.Container(
                content=tree_column,
                padding=8,
                border_radius=14,
                bgcolor="#F3F4F6",
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
    )

    refresh_data()
    rebuild()

    return ft.View(
        route="/budget_view",
        controls=[content],
        bgcolor="#FFFFFF",
        padding=0,
    )