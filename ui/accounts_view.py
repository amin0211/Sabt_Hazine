import flet as ft
from datetime import date, datetime

from services.supabase_service import (
    get_accounts,
    create_account,
    update_account,
    delete_account,
    create_transfer,
    get_account_balances,
    get_account_transactions,
    get_members,
    get_descendant_category_ids,
    load_active_hazineha,
)


DEFAULT_ACCOUNT_NAMES = {
    "bank": "Bank",
    "cash": "Cash",
    "credit": "Credit Card",
    "savings": "Savings",
    "wallet": "Wallet",
    "custom": "",
}


ACCOUNT_TYPE_LABELS = {
    "bank": "Bank Account",
    "cash": "Cash",
    "credit": "Credit Card",
    "savings": "Savings",
    "wallet": "Wallet",
    "custom": "Custom",
}


ACCOUNT_TYPE_ICONS = {
    "bank": ft.Icons.ACCOUNT_BALANCE_OUTLINED,
    "cash": ft.Icons.PAYMENTS_OUTLINED,
    "credit": ft.Icons.CREDIT_CARD,
    "savings": ft.Icons.SAVINGS_OUTLINED,
    "wallet": ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
    "custom": ft.Icons.WALLET_OUTLINED,
}


ACCOUNT_TYPE_COLORS = {
    "bank": "#2563EB",
    "cash": "#16A34A",
    "credit": "#9333EA",
    "savings": "#EA580C",
    "wallet": "#0891B2",
    "custom": "#475569",
}


def accounts_view(page: ft.Page):
    accounts_column = ft.Column(spacing=12, expand=True)
    editing_account_id = {"value": None}

    message = ft.Text("", size=12, color="#64748B")
    transfer_message = ft.Text("", size=12, color="#DC2626")

    from_account_dd = ft.Dropdown(label="From Account", expand=True)
    to_account_dd = ft.Dropdown(label="To Account", expand=True)

    transfer_amount = ft.TextField(
        label="Amount",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        border_radius=14,
    )

    transfer_date = ft.TextField(
        label="Date",
        value=date.today().isoformat(),
        expand=True,
        border_radius=14,
    )

    transfer_note = ft.TextField(
        label="Description",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_radius=14,
    )

    account_name = ft.TextField(
        label="Account Name",
        value="Bank",
        expand=True,
        border_radius=14,
    )

    initial_balance = ft.TextField(
        label="Initial Balance",
        value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        border_radius=14,
    )

    is_default = ft.Checkbox(
        label="Default account",
        value=False,
    )

    account_type = ft.Dropdown(
        label="Account Type",
        value="bank",
        options=[
            ft.dropdown.Option("bank", "Bank"),
            ft.dropdown.Option("cash", "Cash"),
            ft.dropdown.Option("credit", "Credit Card"),
            ft.dropdown.Option("savings", "Savings"),
            ft.dropdown.Option("wallet", "Wallet"),
            ft.dropdown.Option("custom", "Custom"),
        ],
        expand=True,
        border_radius=14,
    )

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def money(value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"

    def reset_form():
        editing_account_id["value"] = None
        account_type.value = "bank"
        account_name.value = "Bank"
        initial_balance.value = "0"
        is_default.value = False
        message.value = ""

    def sync_account_name(e=None):
        selected_type = account_type.value or "custom"
        account_name.value = DEFAULT_ACCOUNT_NAMES.get(selected_type, "")
        safe_update()

    def on_type_change(e):
        selected_type = account_type.value or "custom"
        account_name.value = DEFAULT_ACCOUNT_NAMES.get(selected_type, "")
        safe_update()

    account_type.on_change = on_type_change

    def show_add_form(e=None):
        reset_form()
        form_title.value = "Add New Account"
        form_subtitle.value = "Create a new account to track your money."
        form_icon.content = ft.Icon(ft.Icons.ADD, color="#2563EB", size=24)
        form_card.visible = True
        safe_update()

    def hide_form(e=None):
        reset_form()
        form_card.visible = False
        safe_update()

    def close_account_transactions_dialog(dialog):
        dialog.open = False
        safe_update()

    def load_transfer_accounts():
        accounts = get_accounts()

        options = [
            ft.dropdown.Option(acc.get("id"), acc.get("account_name") or "")
            for acc in accounts
        ]

        from_account_dd.options = options
        to_account_dd.options = options

        if accounts:
            from_account_dd.value = accounts[0].get("id")
            to_account_dd.value = accounts[1].get("id") if len(accounts) > 1 else None

    def save_transfer(e):
        transfer_message.value = ""

        if not from_account_dd.value or not to_account_dd.value:
            transfer_message.value = "Please select both accounts."
            safe_update()
            return

        if from_account_dd.value == to_account_dd.value:
            transfer_message.value = "From and To accounts cannot be the same."
            safe_update()
            return

        try:
            amount = float(transfer_amount.value or 0)
        except ValueError:
            transfer_message.value = "Amount must be a number."
            safe_update()
            return

        if amount <= 0:
            transfer_message.value = "Amount must be greater than zero."
            safe_update()
            return

        try:
            create_transfer(
                from_account_id=from_account_dd.value,
                to_account_id=to_account_dd.value,
                amount=amount,
                transfer_date=transfer_date.value,
                note=transfer_note.value,
            )

            transfer_amount.value = ""
            transfer_note.value = ""
            transfer_date.value = date.today().isoformat()

            load_accounts()
            transfer_dialog.open = False

        except Exception as ex:
            transfer_message.value = f"Transfer error: {ex}"

        safe_update()

    def close_transfer_dialog():
        transfer_dialog.open = False
        safe_update()

    transfer_dialog = ft.AlertDialog(
        modal=True,
        title=None,
        content=ft.Container(
            width=420,
            padding=20,
            border_radius=24,
            bgcolor="#FFFFFF",
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=50,
                                height=50,
                                border_radius=16,
                                bgcolor="#DBEAFE",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.SWAP_HORIZ,
                                    color="#2563EB",
                                    size=26,
                                ),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Transfer Money",
                                        size=20,
                                        weight=ft.FontWeight.W_700,
                                        color="#0F172A",
                                    ),
                                    ft.Text(
                                        "Move money between your accounts.",
                                        size=12,
                                        color="#64748B",
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Divider(height=18, color="#E2E8F0"),
                    from_account_dd,
                    to_account_dd,
                    ft.Row([transfer_amount, transfer_date], spacing=10),
                    transfer_note,
                    transfer_message,
                ],
                spacing=12,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=lambda e: close_transfer_dialog(),
            ),
            ft.ElevatedButton(
                "Save Transfer",
                icon=ft.Icons.CHECK,
                on_click=save_transfer,
                bgcolor="#2563EB",
                color="#FFFFFF",
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(transfer_dialog)

    def open_transfer_dialog(e=None):
        try:
            load_transfer_accounts()
            transfer_message.value = ""
            transfer_dialog.open = True
        except Exception as ex:
            message.value = f"Transfer form error: {ex}"

        safe_update()

    confirm_delete_dialog = ft.AlertDialog(
        modal=True,
        title=None,
        content=ft.Container(width=360),
        actions=[],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    page.overlay.append(confirm_delete_dialog)

    def open_account_transactions(account, balance):
        selected_category = {
            "category_id": None,
            "category_title": "All categories",
        }

        saved_category = page.data.get("account_statement_selected_category")
        if saved_category:
            selected_category.update(saved_category)

        selected_member = {
            "member_id": None,
            "member_name": "All members",
        }

        filter_values = {
            "from_date": None,
            "to_date": None,
            "min_amount": None,
            "max_amount": None,
        }

        try:
            account_id = account.get("id")
            account_name_text = account.get("account_name") or "Account"
            account_type_text = account.get("account_type") or "custom"

            all_transactions = get_account_transactions(account_id)
            tx_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)

            def build_items(transactions):
                tx_list.controls.clear()

                if not transactions:
                    tx_list.controls.append(
                        ft.Container(
                            padding=30,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                [
                                    ft.Icon(
                                        ft.Icons.RECEIPT_LONG_OUTLINED,
                                        size=48,
                                        color="#CBD5E1",
                                    ),
                                    ft.Text(
                                        "No transactions found.",
                                        size=14,
                                        color="#64748B",
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=8,
                            ),
                        )
                    )
                    return

                for tx in transactions:
                    amount = float(tx.get("amount") or 0)
                    is_positive = amount >= 0

                    category_text = tx.get("category") or tx.get("category_title") or ""
                    member_text = tx.get("member") or tx.get("member_name") or ""

                    subtitle_parts = [
                        tx.get("date") or "",
                        tx.get("type") or "",
                    ]

                    if category_text:
                        subtitle_parts.append(category_text)

                    if member_text:
                        subtitle_parts.append(member_text)

                    tx_list.controls.append(
                        ft.Container(
                            padding=12,
                            border_radius=16,
                            bgcolor="#F8FAFC",
                            border=ft.border.all(1, "#E2E8F0"),
                            content=ft.Row(
                                [
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=14,
                                        bgcolor="#DCFCE7" if is_positive else "#FEE2E2",
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.ARROW_DOWNWARD if is_positive else ft.Icons.ARROW_UPWARD,
                                            size=18,
                                            color="#16A34A" if is_positive else "#DC2626",
                                        ),
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                tx.get("title") or "",
                                                size=13,
                                                weight=ft.FontWeight.W_600,
                                                color="#0F172A",
                                            ),
                                            ft.Text(
                                                " • ".join([x for x in subtitle_parts if x]),
                                                size=10,
                                                color="#64748B",
                                            ),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        f"{amount:+,.2f}",
                                        size=13,
                                        weight=ft.FontWeight.W_700,
                                        color="#16A34A" if is_positive else "#DC2626",
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )

            def apply_statement_filters():
                filtered = []
                valid_category_ids = None

                if selected_category["category_id"]:
                    categories = load_active_hazineha()
                    valid_category_ids = get_descendant_category_ids(
                        categories,
                        selected_category["category_id"],
                    )

                for tx in all_transactions:
                    tx_date = tx.get("date") or ""
                    amount = abs(float(tx.get("amount") or 0))

                    if filter_values["from_date"] and tx_date < filter_values["from_date"]:
                        continue

                    if filter_values["to_date"] and tx_date > filter_values["to_date"]:
                        continue

                    if filter_values["min_amount"] is not None and amount < filter_values["min_amount"]:
                        continue

                    if filter_values["max_amount"] is not None and amount > filter_values["max_amount"]:
                        continue

                    if valid_category_ids is not None:
                        if tx.get("category_id") not in valid_category_ids:
                            continue

                    if selected_member["member_id"]:
                        if tx.get("member_id") != selected_member["member_id"]:
                            continue

                    filtered.append(tx)

                build_items(filtered)
                safe_update()

            def open_statement_filter_dialog():
                from_date_value = {"value": filter_values["from_date"]}
                to_date_value = {"value": filter_values["to_date"]}

                from_date_text = ft.Text(
                    from_date_value["value"] or "From date",
                    size=13,
                    expand=True,
                    color="#334155",
                )

                to_date_text = ft.Text(
                    to_date_value["value"] or "To date",
                    size=13,
                    expand=True,
                    color="#334155",
                )

                min_amount_tf = ft.TextField(
                    label="Min Amount",
                    value="" if filter_values["min_amount"] is None else str(filter_values["min_amount"]),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=True,
                    border_radius=14,
                )

                max_amount_tf = ft.TextField(
                    label="Max Amount",
                    value="" if filter_values["max_amount"] is None else str(filter_values["max_amount"]),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=True,
                    border_radius=14,
                )

                category_text = ft.Text(
                    selected_category["category_title"],
                    size=13,
                    expand=True,
                    color="#334155",
                    overflow=ft.TextOverflow.ELLIPSIS,
                )

                member_text = ft.Text(
                    selected_member["member_name"],
                    size=13,
                    expand=True,
                    color="#334155",
                    overflow=ft.TextOverflow.ELLIPSIS,
                )

                from_picker = ft.DatePicker()
                to_picker = ft.DatePicker()

                page.overlay.append(from_picker)
                page.overlay.append(to_picker)

                def refresh_filter_dialog():
                    from_date_text.value = from_date_value["value"] or "From date"
                    to_date_text.value = to_date_value["value"] or "To date"
                    category_text.value = selected_category["category_title"]
                    member_text.value = selected_member["member_name"]
                    safe_update()

                def clear_category_filter(e=None):
                    selected_category["category_id"] = None
                    selected_category["category_title"] = "All categories"
                    page.data["account_statement_selected_category"] = selected_category.copy()
                    refresh_filter_dialog()

                def clear_member_filter(e=None):
                    selected_member["member_id"] = None
                    selected_member["member_name"] = "All members"
                    refresh_filter_dialog()

                def on_from_change(e):
                    picked = from_picker.value
                    if isinstance(picked, datetime):
                        picked = picked.date()
                    from_date_value["value"] = picked.isoformat() if picked else None
                    refresh_filter_dialog()

                def on_to_change(e):
                    picked = to_picker.value
                    if isinstance(picked, datetime):
                        picked = picked.date()
                    to_date_value["value"] = picked.isoformat() if picked else None
                    refresh_filter_dialog()

                from_picker.on_change = on_from_change
                to_picker.on_change = on_to_change

                def open_from_picker(e=None):
                    from_picker.open = True
                    safe_update()

                def open_to_picker(e=None):
                    to_picker.open = True
                    safe_update()

                def choose_category(e=None):
                    page.data["without_edit"] = True
                    page.data["category_picker_mode"] = True
                    page.data["category_picker_current_id"] = selected_category["category_id"]
                    page.data["from"] = "accounts"
                    page.data["account_filter_context"] = {
                        "account": account,
                        "balance": balance,
                    }

                    def on_category_selected(result):
                        selected_category["category_id"] = result.get("category_id")
                        selected_category["category_title"] = (
                            result.get("category_title") or "All categories"
                        )
                        page.data["account_statement_selected_category"] = {
                            "category_id": selected_category["category_id"],
                            "category_title": selected_category["category_title"],
                        }
                        refresh_filter_dialog()

                    page.data["category_picker_on_selected"] = on_category_selected

                    filter_dialog.open = False

                    try:
                        statement_dialog.open = False
                    except Exception:
                        pass

                    safe_update()
                    page.app_go("hazinaha_view")

                members_data = get_members()
                member_list = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
                member_search = ft.TextField(
                    hint_text="Search member",
                    prefix_icon=ft.Icons.SEARCH,
                    border_radius=14,
                )

                def select_member(member_id, member_name):
                    selected_member["member_id"] = member_id
                    selected_member["member_name"] = member_name
                    member_dialog.open = False
                    refresh_filter_dialog()

                def rebuild_members(q=""):
                    member_list.controls.clear()

                    member_list.controls.append(
                        ft.Container(
                            padding=12,
                            border_radius=14,
                            bgcolor="#F8FAFC",
                            border=ft.border.all(1, "#E2E8F0"),
                            on_click=lambda e: select_member(None, "All members"),
                            content=ft.Text("All members", color="#0F172A"),
                        )
                    )

                    for member in members_data:
                        name = member.get("full_name") or ""
                        relation = member.get("relation") or ""
                        member_id = member.get("id")

                        if q and q.lower() not in f"{name} {relation}".lower():
                            continue

                        member_list.controls.append(
                            ft.Container(
                                padding=12,
                                border_radius=14,
                                bgcolor="#F8FAFC",
                                border=ft.border.all(1, "#E2E8F0"),
                                on_click=lambda e, mid=member_id, mname=name: select_member(mid, mname),
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.PERSON_OUTLINE, size=17, color="#64748B"),
                                        ft.Text(name, expand=True, color="#0F172A"),
                                        ft.Text(relation or "-", size=12, color="#64748B"),
                                    ]
                                ),
                            )
                        )

                def on_member_search(e):
                    rebuild_members(e.control.value or "")
                    safe_update()

                member_search.on_change = on_member_search

                def close_member_dialog():
                    member_dialog.open = False
                    safe_update()

                member_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Select Member", size=18, weight=ft.FontWeight.W_700),
                    content=ft.Container(
                        width=360,
                        height=500,
                        content=ft.Column([member_search, member_list], spacing=10),
                    ),
                    actions=[
                        ft.TextButton("Close", on_click=lambda e: close_member_dialog()),
                    ],
                )

                page.overlay.append(member_dialog)

                def open_member_dialog(e=None):
                    member_search.value = ""
                    rebuild_members()
                    member_dialog.open = True
                    safe_update()

                def apply_filter(e=None):
                    filter_values["from_date"] = from_date_value["value"]
                    filter_values["to_date"] = to_date_value["value"]

                    try:
                        filter_values["min_amount"] = (
                            float(min_amount_tf.value) if min_amount_tf.value else None
                        )
                    except Exception:
                        filter_values["min_amount"] = None

                    try:
                        filter_values["max_amount"] = (
                            float(max_amount_tf.value) if max_amount_tf.value else None
                        )
                    except Exception:
                        filter_values["max_amount"] = None

                    filter_dialog.open = False
                    apply_statement_filters()

                def clear_filter(e=None):
                    filter_values["from_date"] = None
                    filter_values["to_date"] = None
                    filter_values["min_amount"] = None
                    filter_values["max_amount"] = None

                    selected_category["category_id"] = None
                    selected_category["category_title"] = "All categories"

                    selected_member["member_id"] = None
                    selected_member["member_name"] = "All members"

                    filter_dialog.open = False
                    build_items(all_transactions)
                    safe_update()

                def selector_row(icon, text_control, clear_visible, clear_fn, choose_fn):
                    return ft.Container(
                        padding=12,
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        content=ft.Row(
                            [
                                ft.Icon(icon, size=18, color="#64748B"),
                                text_control,
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=16,
                                    tooltip="Clear",
                                    visible=clear_visible,
                                    on_click=lambda e: clear_fn(),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CHEVRON_RIGHT,
                                    icon_size=16,
                                    tooltip="Choose",
                                    on_click=choose_fn,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )

                filter_dialog = ft.AlertDialog(
                    modal=True,
                    title=None,
                    content=ft.Container(
                        width=430,
                        padding=18,
                        border_radius=24,
                        bgcolor="#FFFFFF",
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(
                                            width=46,
                                            height=46,
                                            border_radius=15,
                                            bgcolor="#DBEAFE",
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(
                                                ft.Icons.FILTER_ALT_OUTLINED,
                                                color="#2563EB",
                                                size=24,
                                            ),
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    "Filter Statement",
                                                    size=19,
                                                    weight=ft.FontWeight.W_700,
                                                    color="#0F172A",
                                                ),
                                                ft.Text(
                                                    "Narrow transactions by date, amount, category, or member.",
                                                    size=12,
                                                    color="#64748B",
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                ft.Divider(height=18, color="#E2E8F0"),
                                ft.Row(
                                    [
                                        ft.Container(
                                            expand=True,
                                            padding=12,
                                            border_radius=16,
                                            bgcolor="#F8FAFC",
                                            border=ft.border.all(1, "#E2E8F0"),
                                            on_click=open_from_picker,
                                            content=ft.Row(
                                                [
                                                    ft.Icon(ft.Icons.CALENDAR_MONTH, size=17, color="#64748B"),
                                                    from_date_text,
                                                ],
                                            ),
                                        ),
                                        ft.Container(
                                            expand=True,
                                            padding=12,
                                            border_radius=16,
                                            bgcolor="#F8FAFC",
                                            border=ft.border.all(1, "#E2E8F0"),
                                            on_click=open_to_picker,
                                            content=ft.Row(
                                                [
                                                    ft.Icon(ft.Icons.DATE_RANGE, size=17, color="#64748B"),
                                                    to_date_text,
                                                ],
                                            ),
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                ft.Row([min_amount_tf, max_amount_tf], spacing=8),
                                selector_row(
                                    ft.Icons.ACCOUNT_TREE_OUTLINED,
                                    category_text,
                                    selected_category["category_id"] is not None,
                                    clear_category_filter,
                                    choose_category,
                                ),
                                selector_row(
                                    ft.Icons.PERSON_OUTLINE,
                                    member_text,
                                    selected_member["member_id"] is not None,
                                    clear_member_filter,
                                    open_member_dialog,
                                ),
                            ],
                            spacing=10,
                            tight=True,
                        ),
                    ),
                    actions=[
                        ft.TextButton("Clear", on_click=clear_filter),
                        ft.ElevatedButton(
                            "Apply",
                            icon=ft.Icons.CHECK,
                            on_click=apply_filter,
                            bgcolor="#2563EB",
                            color="#FFFFFF",
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )

                page.overlay.append(filter_dialog)
                filter_dialog.open = True
                safe_update()

            color = ACCOUNT_TYPE_COLORS.get(account_type_text, "#475569")
            icon = ACCOUNT_TYPE_ICONS.get(account_type_text, ft.Icons.WALLET_OUTLINED)

            header = ft.Container(
                padding=16,
                border_radius=20,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=[color, "#0F172A"],
                ),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=46,
                                    height=46,
                                    border_radius=16,
                                    bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.WHITE),
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(icon, size=25, color="#FFFFFF"),
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            account_name_text,
                                            size=18,
                                            weight=ft.FontWeight.W_700,
                                            color="#FFFFFF",
                                        ),
                                        ft.Text(
                                            ACCOUNT_TYPE_LABELS.get(account_type_text, account_type_text),
                                            size=11,
                                            color="#E2E8F0",
                                        ),
                                    ],
                                    spacing=1,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.FILTER_ALT_OUTLINED,
                                    icon_color="#FFFFFF",
                                    tooltip="Filter",
                                    on_click=lambda e: open_statement_filter_dialog(),
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=16, color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE)),
                        ft.Row(
                            [
                                ft.Text("Current Balance", size=12, color="#E2E8F0"),
                                ft.Text(
                                    money(balance),
                                    size=21,
                                    weight=ft.FontWeight.W_700,
                                    color="#FFFFFF",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=6,
                ),
            )

            build_items(all_transactions)

            statement_dialog = ft.AlertDialog(
                modal=True,
                title=None,
                content=ft.Container(
                    width=500,
                    height=600,
                    padding=4,
                    content=ft.Column(
                        [
                            header,
                            ft.Text(
                                "Transaction History",
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color="#0F172A",
                            ),
                            tx_list,
                        ],
                        spacing=12,
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Close",
                        on_click=lambda e: close_account_transactions_dialog(statement_dialog),
                    )
                ],
            )

            page.overlay.append(statement_dialog)
            statement_dialog.open = True
            safe_update()

            if page.data.get("open_filter_after_account_statement"):
                page.data["open_filter_after_account_statement"] = False
                open_statement_filter_dialog()

        except Exception as ex:
            print("ACCOUNT TRANSACTIONS ERROR:", ex)
            message.value = f"Error loading transactions: {ex}"
            safe_update()

    def save_account(e):
        name = (account_name.value or "").strip()

        if not name:
            message.value = "Account name is required."
            message.color = "#DC2626"
            safe_update()
            return

        try:
            balance = float(initial_balance.value or 0)
        except ValueError:
            message.value = "Initial balance must be a number."
            message.color = "#DC2626"
            safe_update()
            return

        try:
            if editing_account_id["value"]:
                update_account(
                    account_id=editing_account_id["value"],
                    account_type=account_type.value,
                    account_name=name,
                    initial_balance=balance,
                    is_default=bool(is_default.value),
                )
                message.value = "Account updated."
            else:
                create_account(
                    account_type=account_type.value,
                    account_name=name,
                    initial_balance=balance,
                    is_default=bool(is_default.value),
                )
                message.value = "Account created."

            message.color = "#16A34A"
            reset_form()
            form_card.visible = False
            load_accounts()

        except Exception as ex:
            message.value = f"Save error: {ex}"
            message.color = "#DC2626"

        safe_update()

    def cancel_edit(e):
        hide_form()

    form_title = ft.Text(
        "Add New Account",
        size=18,
        weight=ft.FontWeight.W_700,
        color="#0F172A",
    )

    form_subtitle = ft.Text(
        "Create a new account to track your money.",
        size=12,
        color="#64748B",
    )

    form_icon = ft.Container(
        width=48,
        height=48,
        border_radius=16,
        bgcolor="#DBEAFE",
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(ft.Icons.ADD, color="#2563EB", size=24),
    )

    form_card = ft.Container(
        visible=False,
        padding=18,
        border_radius=24,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E2E8F0"),
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        form_icon,
                        ft.Column(
                            [
                                form_title,
                                form_subtitle,
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip="Close",
                            on_click=cancel_edit,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Divider(height=16, color="#E2E8F0"),
                ft.Row(
                    [
                        account_type,
                        ft.Container(
                            width=48,
                            height=48,
                            border_radius=14,
                            bgcolor="#F1F5F9",
                            alignment=ft.Alignment.CENTER,
                            content=ft.IconButton(
                                icon=ft.Icons.SYNC,
                                tooltip="Use type as name",
                                on_click=sync_account_name,
                            ),
                        ),
                    ],
                    spacing=8,
                ),
                account_name,
                initial_balance,
                is_default,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Save Account",
                            icon=ft.Icons.SAVE_OUTLINED,
                            on_click=save_account,
                            bgcolor="#2563EB",
                            color="#FFFFFF",
                        ),
                        ft.TextButton(
                            "Cancel",
                            on_click=cancel_edit,
                        ),
                    ],
                    spacing=10,
                ),
                message,
            ],
            spacing=10,
        ),
    )

    def load_accounts():
        accounts_column.controls.clear()

        try:
            accounts = get_accounts()
        except Exception as ex:
            accounts_column.controls.append(
                ft.Text(f"Error loading accounts: {ex}", color="#DC2626")
            )
            return

        try:
            balances = get_account_balances()
        except Exception:
            balances = []

        balance_map = {}
        for b in balances:
            account_id = b.get("account_id") or b.get("out_account_id")
            balance_value = b.get("balance")
            if balance_value is None:
                balance_value = b.get("out_balance")
            if account_id:
                balance_map[account_id] = balance_value

        total_balance = 0
        for acc in accounts:
            acc_id = acc.get("id")
            total_balance += float(balance_map.get(acc_id, acc.get("initial_balance", 0)) or 0)

        total_balance_text.value = money(total_balance)
        account_count_text.value = str(len(accounts))

        if not accounts:
            accounts_column.controls.append(
                ft.Container(
                    padding=28,
                    border_radius=24,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#E2E8F0"),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Container(
                                width=64,
                                height=64,
                                border_radius=22,
                                bgcolor="#EFF6FF",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                                    size=34,
                                    color="#2563EB",
                                ),
                            ),
                            ft.Text(
                                "No accounts yet",
                                size=18,
                                weight=ft.FontWeight.W_700,
                                color="#0F172A",
                            ),
                            ft.Text(
                                "Add your first account to start tracking balances.",
                                size=13,
                                color="#64748B",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.ElevatedButton(
                                "Add Account",
                                icon=ft.Icons.ADD,
                                on_click=show_add_form,
                                bgcolor="#2563EB",
                                color="#FFFFFF",
                            ),
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            return

        for acc in accounts:
            account_id = acc.get("id")
            name = acc.get("account_name") or ""
            acc_type = acc.get("account_type") or "custom"
            balance = balance_map.get(account_id, acc.get("initial_balance", 0))
            default_value = bool(acc.get("is_default"))

            color = ACCOUNT_TYPE_COLORS.get(acc_type, "#475569")
            icon = ACCOUNT_TYPE_ICONS.get(acc_type, ft.Icons.WALLET_OUTLINED)
            label = ACCOUNT_TYPE_LABELS.get(acc_type, acc_type)

            def edit_handler(e, account=acc):
                editing_account_id["value"] = account.get("id")
                account_type.value = account.get("account_type") or "custom"
                account_name.value = account.get("account_name") or ""
                initial_balance.value = str(account.get("initial_balance") or 0)
                is_default.value = bool(account.get("is_default"))
                message.value = ""
                form_title.value = "Edit Account"
                form_subtitle.value = "Update account details and default status."
                form_icon.bgcolor = "#FEF3C7"
                form_icon.content = ft.Icon(ft.Icons.EDIT_OUTLINED, color="#D97706", size=24)
                form_card.visible = True
                safe_update()

            def delete_handler(e, account=acc):
                account_name_text = account.get("account_name") or "this account"

                def confirm_delete(e):
                    try:
                        delete_account(account.get("id"))
                        reset_form()
                        form_card.visible = False
                        load_accounts()
                    except Exception as ex:
                        message.value = f"Delete error: {ex}"
                        message.color = "#DC2626"

                    confirm_delete_dialog.open = False
                    safe_update()

                def cancel_delete(e):
                    confirm_delete_dialog.open = False
                    safe_update()


                confirm_delete_dialog.content = ft.Container(
                    width=300,
                    padding=16,
                    border_radius=20,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        [
                            ft.Container(
                                width=44,
                                height=44,
                                border_radius=14,
                                bgcolor="#FEE2E2",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.DELETE_OUTLINE,
                                    color="#DC2626",
                                    size=22,
                                ),
                            ),
                            ft.Text(
                                "Delete Account?",
                                size=17,
                                weight=ft.FontWeight.W_700,
                                color="#0F172A",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                f'Are you sure you want to delete "{account_name_text}"?',
                                size=12,
                                color="#475569",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "This action cannot be undone.",
                                size=11,
                                color="#DC2626",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                )

                confirm_delete_dialog.actions = [
                    ft.TextButton(
                        "Cancel",
                        on_click=cancel_delete,
                    ),
                    ft.ElevatedButton(
                        "Delete",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=confirm_delete,
                        bgcolor="#DC2626",
                        color="#FFFFFF",
                    ),
                ]

                confirm_delete_dialog.open = True
                safe_update()

            default_badge = ft.Container(
                padding=ft.padding.symmetric(horizontal=9, vertical=4),
                border_radius=20,
                bgcolor="#DCFCE7",
                content=ft.Text("Default", size=10, color="#15803D", weight=ft.FontWeight.W_600),
                visible=default_value,
            )

            accounts_column.controls.append(
                ft.Container(
                    padding=16,
                    border_radius=24,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#E2E8F0"),
                    shadow=ft.BoxShadow(
                        blur_radius=14,
                        spread_radius=0,
                        color=ft.Colors.with_opacity(0.055, ft.Colors.BLACK),
                        offset=ft.Offset(0, 6),
                    ),
                    content=ft.Row(
                        [
                            ft.Container(
                                width=44,
                                height=44,
                                border_radius=18,
                                bgcolor=ft.Colors.with_opacity(0.12, color),
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icon, color=color, size=27),
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(
                                                name,
                                                size=16,
                                                weight=ft.FontWeight.W_700,
                                                color="#0F172A",
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            default_badge,
                                        ],
                                        spacing=8,
                                    ),
                                    ft.Text(
                                        label,
                                        size=12,
                                        color="#64748B",
                                    ),
                                    ft.Text(
                                        money(balance),
                                        size=18,
                                        weight=ft.FontWeight.W_700,
                                        color=color,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                border_radius=14,
                                bgcolor="#F8FAFC",
                                content=ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.Icons.LIST_ALT,
                                            icon_size=18,
                                            icon_color="#334155",
                                            tooltip="Account Transactions",
                                            on_click=lambda e, account=acc, bal=balance: open_account_transactions(account, bal),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT_OUTLINED,
                                            icon_size=18,
                                            icon_color="#2563EB",
                                            tooltip="Edit",
                                            on_click=edit_handler,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_size=18,
                                            icon_color="#DC2626",
                                            tooltip="Delete",
                                            on_click=delete_handler,
                                        ),
                                    ],
                                    spacing=0,
                                ),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    total_balance_text = ft.Text(
        "0.00",
        size=22,
        weight=ft.FontWeight.W_800,
        color="#FFFFFF",
    )

    account_count_text = ft.Text(
        "0",
        size=18,
        weight=ft.FontWeight.W_700,
        color="#0F172A",
    )

    header_card = ft.Container(
        padding=14,
        border_radius=28,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#2563EB", "#0F172A"],
        ),
        shadow=ft.BoxShadow(
            blur_radius=20,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.14, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=44,
                            height=44,
                            border_radius=18,
                            bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.WHITE),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                                color="#FFFFFF",
                                size=22,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Accounts",
                                    size=20,
                                    weight=ft.FontWeight.W_800,
                                    color="#FFFFFF",
                                ),
                                ft.Text(
                                    "Manage balances, accounts, and transfers.",
                                    size=11,
                                    color="#DBEAFE",
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Divider(height=12, color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE)),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Total Balance", size=12, color="#BFDBFE"),
                                total_balance_text,
                            ],
                            spacing=2,
                        ),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=14, vertical=10),
                            border_radius=18,
                            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
                            content=ft.Column(
                                [
                                    ft.Text("Accounts", size=11, color="#DBEAFE"),
                                    account_count_text,
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=6,
        ),
    )

    top_actions = ft.Row(
        [
            ft.ElevatedButton(
                "Add Account",
                icon=ft.Icons.ADD,
                on_click=show_add_form,
                bgcolor="#2563EB",
                color="#FFFFFF",
                height=44,
            ),
            ft.OutlinedButton(
                "Transfer",
                icon=ft.Icons.SWAP_HORIZ,
                on_click=open_transfer_dialog,
                height=44,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    load_accounts()

    if page.data.get("reopen_account_filter_dialog"):
        page.data["reopen_account_filter_dialog"] = False
        page.data["open_filter_after_account_statement"] = True

        ctx = page.data.get("account_filter_context")
        if ctx:
            open_account_transactions(ctx["account"], ctx["balance"])

    return ft.View(
        route="/accounts",
        bgcolor="#F8FAFC",
        controls=[
            ft.AppBar(
                bgcolor="#F8FAFC",
                elevation=0,
                title=ft.Text(
                    "Accounts",
                    color="#0F172A",
                    weight=ft.FontWeight.W_700,
                ),
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color="#0F172A",
                    on_click=lambda e: page.app_go("sabtehazine"),
                ),
            ),
            ft.Container(
                padding=ft.padding.only(top=4, left=16, right=16, bottom=10),
                expand=True,
                content=ft.Column(
                    [
                        header_card,
                        top_actions,
                        form_card,
                        ft.Row(
                            [
                                ft.Text(
                                    "Your Accounts",
                                    size=17,
                                    weight=ft.FontWeight.W_700,
                                    color="#0F172A",
                                ),
                                ft.Text(
                                    "Tap list icon for statement",
                                    size=11,
                                    color="#64748B",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        accounts_column,
                    ],
                    spacing=14,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        ],
    )