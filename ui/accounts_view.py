import flet as ft

from services.supabase_service import (
    get_accounts,
    create_account,
    update_account,
    delete_account,
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


    initial_balance = ft.TextField(
        label="Initial Balance",
        value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    currency = ft.Dropdown(
        label="Currency",
        value="CAD",
        options=[
            ft.dropdown.Option("CAD", "CAD"),
            ft.dropdown.Option("USD", "USD"),
            ft.dropdown.Option("IRR", "IRR"),
        ],
        expand=True,
    )

    is_default = ft.Checkbox(
        label="Default account",
        value=False,
    )

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
        currency.value = "CAD"
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

        for acc in accounts:
            account_id = acc.get("id")
            name = acc.get("account_name") or ""
            acc_type = acc.get("account_type") or "custom"
            balance = acc.get("initial_balance", 0)
            curr = acc.get("currency") or "CAD"
            default_value = bool(acc.get("is_default"))

            def edit_handler(e, account=acc):
                editing_account_id["value"] = account.get("id")
                account_type.value = account.get("account_type") or "custom"
                account_name.value = account.get("account_name") or ""
                initial_balance.value = str(account.get("initial_balance") or 0)
                currency.value = account.get("currency") or "CAD"
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
                                        f"{balance} {curr}",
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
                    currency=currency.value,
                    is_default=bool(is_default.value),
                )
                message.value = "Account updated."
            else:
                create_account(
                    account_type=account_type.value,
                    account_name=name,
                    initial_balance=balance,
                    currency=currency.value,
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
                currency,
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
                    on_click=lambda e: page.go("/sabtehazine"),
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