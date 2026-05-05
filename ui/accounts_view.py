import flet as ft
from datetime import date

from services.supabase_service import (
    get_accounts,
    create_account,
    update_account,
    delete_account,
    create_transfer,
    get_account_balances,
    get_account_transactions,
)


# ACCOUNT_TYPE_OPTIONS = [
#     ("bank", "Bank"),
#     ("cash", "Cash"),
#     ("credit", "Credit Card"),
#     ("savings", "Savings"),
#     ("wallet", "Wallet"),
#     ("custom", "Custom"),
# ]

DEFAULT_ACCOUNT_NAMES = {
    "bank": "Bank",
    "cash": "Cash",
    "credit": "Credit Card",
    "savings": "Savings",
    "wallet": "Wallet",
    "custom": "",
}


def accounts_view(page: ft.Page):
    accounts_column = ft.Column(spacing=10, expand=True)
    editing_account_id = {"value": None}

    message = ft.Text("", size=12)

    transfer_message = ft.Text("", size=12, color=ft.Colors.RED)

    from_account_dd = ft.Dropdown(label="From Account", expand=True)
    to_account_dd = ft.Dropdown(label="To Account", expand=True)

    transfer_amount = ft.TextField(
        label="Amount",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    transfer_date = ft.TextField(
        label="Date",
        value=date.today().isoformat(),
        expand=True,
    )

    transfer_note = ft.TextField(
        label="Description",
        multiline=True,
        min_lines=2,
        max_lines=4,
    )

    initial_balance = ft.TextField(
        label="Initial Balance",
        value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    # currency = ft.Dropdown(
    #     label="Currency",
    #     value="CAD",
    #     options=[
    #         ft.dropdown.Option("CAD", "CAD"),
    #         ft.dropdown.Option("USD", "USD"),
    #         ft.dropdown.Option("IRR", "IRR"),
    #     ],
    #     expand=True,
    # )

    is_default = ft.Checkbox(
        label="Default account",
        value=False,
    )

    def close_account_transactions_dialog(dialog):
        dialog.open = False
        safe_update()


    def open_account_transactions(account_id):
        try:
            transactions = get_account_transactions(account_id)

            items = []

            if not transactions:
                items.append(ft.Text("No transactions found."))
            else:
                for t in transactions:
                    amount = float(t.get("amount") or 0)

                    items.append(
                        ft.Container(
                            padding=8,
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                            content=ft.Row(
                                controls=[
                                    ft.Text(t.get("date") or "", size=11, width=90),
                                    ft.Column(
                                        controls=[
                                            ft.Text(t.get("title") or "", size=13),
                                            ft.Text(t.get("type") or "", size=10, color=ft.Colors.GREY),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        f"{amount:,.2f}",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        )
                    )

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Account Transactions"),
                content=ft.Container(
                    width=420,
                    height=420,
                    content=ft.Column(
                        controls=items,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=8,
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Close",
                        on_click=lambda e: close_account_transactions_dialog(dialog),
                    )
                ],
            )

            page.overlay.append(dialog)
            dialog.open = True
            safe_update()

        except Exception as ex:
            message.value = f"Error loading transactions: {ex}"
            safe_update()


    def close_dialog(dialog):
        dialog.open = False
        page.update()

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def reset_form():
        editing_account_id["value"] = None
        account_type.value = "bank"
        account_name.value = "Bank"
        initial_balance.value = "0"
        # currency.value = "CAD"
        is_default.value = False
        message.value = ""

    account_name = ft.TextField(
        label="Account Name",
        value="Bank",
        expand=True,
    )

    def sync_account_name(e=None):
        selected_type = account_type.value or "custom"
        account_name.value = DEFAULT_ACCOUNT_NAMES.get(selected_type, "")
        page.update()
        
    def on_type_change(e):
        selected_type = account_type.value or "custom"
        account_name.value = DEFAULT_ACCOUNT_NAMES.get(selected_type, "")
        safe_update()
                
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
    )


    account_type.on_blur = on_type_change

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
            message.value = "Transfer saved."
            transfer_dialog.open = False

        except Exception as ex:
            transfer_message.value = f"Transfer error: {ex}"

        safe_update()


    transfer_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Transfer Money"),
        content=ft.Column(
            controls=[
                from_account_dd,
                to_account_dd,
                transfer_amount,
                transfer_date,
                transfer_note,
                transfer_message,
            ],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=lambda e: close_transfer_dialog(),
            ),
            ft.ElevatedButton("Save Transfer", icon=ft.Icons.SWAP_HORIZ, on_click=save_transfer),
        ],
    )
    print("CLICKED TRANSFER")
    page.overlay.append(transfer_dialog)
    print("CLICKED TRANSFER")

    def open_transfer_dialog(e):
        try:
            load_transfer_accounts()
            transfer_message.value = ""

            page.dialog = transfer_dialog
            transfer_dialog.open = True

        except Exception as ex:
            message.value = f"Transfer form error: {ex}"

        safe_update()
        
    def close_transfer_dialog():
        transfer_dialog.open = False
        safe_update()
        
    def load_accounts():
        accounts_column.controls.clear()

        try:
            accounts = get_accounts()
        except Exception as ex:
            accounts_column.controls.append(
                ft.Text(f"Error loading accounts: {ex}", color=ft.Colors.RED)
            )
            return

        if not accounts:
            accounts_column.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                    content=ft.Text("No accounts yet. Add your first account."),
                )
            )
            return


        balances = get_account_balances()
        balance_map = {b["out_account_id"]: b["out_balance"] for b in balances}


        for acc in accounts:
            account_id = acc.get("id")
            name = acc.get("account_name") or ""
            acc_type = acc.get("account_type") or "custom"
            balance = balance_map.get(account_id, acc.get("initial_balance", 0))
            # curr = acc.get("currency") or "CAD"
            default_value = bool(acc.get("is_default"))

            def edit_handler(e, account=acc):
                editing_account_id["value"] = account.get("id")
                account_type.value = account.get("account_type") or "custom"
                account_name.value = account.get("account_name") or ""
                initial_balance.value = str(account.get("initial_balance") or 0)
                # currency.value = account.get("currency") or "CAD"
                is_default.value = bool(account.get("is_default"))
                message.value = "Editing account..."
                safe_update()

            def delete_handler(e, account=acc):
                try:
                    delete_account(account.get("id"))
                    reset_form()
                    load_accounts()
                    message.value = "Account deleted."
                except Exception as ex:
                    message.value = f"Delete error: {ex}"
                safe_update()

            default_badge = ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=20,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.GREEN),
                content=ft.Text("Default", size=10, color=ft.Colors.GREEN),
                visible=default_value,
            )

            accounts_column.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=14,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Text(
                                                name,
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            default_badge,
                                        ],
                                        spacing=8,
                                    ),
                                    ft.Text(
                                        acc_type,
                                        size=12,
                                        color=ft.Colors.GREY,
                                    ),
                                    ft.Text(
                                        f"{balance} ",
                                        size=13,
                                    ),
                                ],
                                spacing=3,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Edit",
                                on_click=edit_handler,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete",
                                on_click=delete_handler,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LIST_ALT,
                                tooltip="Account Transactions",
                                on_click=lambda e, acc_id=account_id: open_account_transactions(acc_id),
                            ),                            
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    def save_account(e):
        name = (account_name.value or "").strip()

        if not name:
            message.value = "Account name is required."
            safe_update()
            return

        try:
            balance = float(initial_balance.value or 0)
        except ValueError:
            message.value = "Initial balance must be a number."
            safe_update()
            return

        try:
            if editing_account_id["value"]:
                update_account(
                    account_id=editing_account_id["value"],
                    account_type=account_type.value,
                    account_name=name,
                    initial_balance=balance,
                    # currency=currency.value,
                    is_default=bool(is_default.value),
                )
                message.value = "Account updated."
            else:
                create_account(
                    account_type=account_type.value,
                    account_name=name,
                    initial_balance=balance,
                    # currency=currency.value,
                    is_default=bool(is_default.value),
                )
                message.value = "Account created."

            reset_form()
            load_accounts()

        except Exception as ex:
            message.value = f"Save error: {ex}"

        safe_update()

    def cancel_edit(e):
        reset_form()
        safe_update()

    form_card = ft.Container(
        padding=15,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        content=ft.Column(
            controls=[
                ft.Text(
                    "Add / Edit Account",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(
                    controls=[
                        account_type,
                        ft.IconButton(
                            icon=ft.Icons.SYNC,
                            tooltip="Use type as name",
                            on_click=sync_account_name,
                        ),
                    ],
                ),
                account_name,
                initial_balance,
                # currency,
                is_default,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save",
                            icon=ft.Icons.SAVE,
                            on_click=save_account,
                        ),
                        ft.TextButton(
                            "Cancel",
                            on_click=cancel_edit,
                        ),
                        ft.ElevatedButton(
                            "Transfer",
                            icon=ft.Icons.SWAP_HORIZ,
                            on_click=open_transfer_dialog,
                        ),

                    ],
                    spacing=10,
                ),
                message,
            ],
            spacing=10,
        ),
    )

    load_accounts()

    return ft.View(
        route="/accounts",
        controls=[
            ft.AppBar(
                title=ft.Text("Accounts"),
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.app_go("sabtehazine"),
                ),
            ),
            ft.Container(
                padding=15,
                expand=True,
                content=ft.Column(
                    controls=[
                        form_card,
                        ft.Text(
                            "Your Accounts",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                        accounts_column,
                    ],
                    spacing=15,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        ],
    )