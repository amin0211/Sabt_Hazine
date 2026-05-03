import flet as ft
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()


from services.supabase_service import (
    get_accounts,

    get_income_transactions_by_month,
    create_income_transaction,
    update_income_transaction,
    delete_income_transaction,
    carry_monthly_income_to_current_month,
)


def income_view(page: ft.Page):
    selected_year_month = {"value": today_local().strftime("%Y-%m")}
    accounts_cache = {"data": []}

    tx_list = ft.Column(spacing=10)
    message = ft.Text("", size=12, color="#6B7280")

    month_tf = ft.TextField(
        label="Month (YYYY-MM)",
        value=selected_year_month["value"],
        expand=True,
    )

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    def money(v):
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

    def load_accounts():
        try:
            accounts_cache["data"] = get_accounts()
        except Exception as ex:
            message.value = f"Load accounts error: {ex}"

    def account_options():
        return [
            ft.dropdown.Option(acc["id"], acc.get("account_name", ""))
            for acc in accounts_cache["data"]
        ]

    def default_account_id():
        default = next((a for a in accounts_cache["data"] if a.get("is_default")), None)
        if default:
            return default["id"]
        if accounts_cache["data"]:
            return accounts_cache["data"][0]["id"]
        return None

    def validate_month():
        ym = (month_tf.value or "").strip()

        if len(ym) != 7 or ym[4] != "-":
            message.value = "Month format must be YYYY-MM."
            safe_update()
            return None

        try:
            y, m = ym.split("-")
            y = int(y)
            m = int(m)
            if m < 1 or m > 12:
                raise ValueError()
        except Exception:
            message.value = "Month format must be YYYY-MM."
            safe_update()
            return None

        selected_year_month["value"] = ym
        return ym

    def make_card(content):
        return ft.Container(
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
            content=content,
        )

    # ---------- Dialog: Transaction ----------
    def open_transaction_form(tx=None):
        editing = tx is not None

        title_tf = ft.TextField(
            label="Title",
            value=(tx or {}).get("title", ""),
        )

        amount_tf = ft.TextField(
            label="Amount",
            value=str((tx or {}).get("amount", "")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        income_type_dd = ft.Dropdown(
            label="Income Type",
            value=(tx or {}).get("income_type", "one_time"),
            options=[
                ft.dropdown.Option("monthly", "Monthly"),
                ft.dropdown.Option("one_time", "One Time"),
            ],
        )

        date_tf = ft.TextField(
            label="Date (YYYY-MM-DD)",
            value=(tx or {}).get("transaction_date") or str(today_local()),
        )

        account_dd = ft.Dropdown(
            label="Account",
            options=account_options(),
            value=(tx or {}).get("account_id") or default_account_id(),
        )

        status_dd = ft.Dropdown(
            label="Status",
            value=(tx or {}).get("status", "confirmed"),
            options=[
                ft.dropdown.Option("confirmed", "Confirmed"),
                ft.dropdown.Option("pending", "Pending"),
                ft.dropdown.Option("missed", "Missed"),
                ft.dropdown.Option("cancelled", "Cancelled"),
            ],
        )

        note_tf = ft.TextField(
            label="Note",
            value=(tx or {}).get("note", "") or "",
            multiline=True,
            min_lines=2,
            max_lines=3,
        )

        dlg_msg = ft.Text("", size=12, color="#DC2626")
        dlg = ft.AlertDialog(modal=True)

        def close_dialog(e=None):
            dlg.open = False
            page.update()

        def save_tx(e):
            title = (title_tf.value or "").strip()

            if not title:
                dlg_msg.value = "Title is required."
                page.update()
                return

            try:
                amount = float(amount_tf.value or 0)
            except ValueError:
                dlg_msg.value = "Amount must be a number."
                page.update()
                return

            if amount <= 0:
                dlg_msg.value = "Amount must be > 0."
                page.update()
                return

            acc_id = account_dd.value
            if not acc_id:
                dlg_msg.value = "Select an account."
                page.update()
                return

            income_type = income_type_dd.value or "one_time"

            try:
                y, m, d = [int(x) for x in (date_tf.value or "").split("-")]
                tx_date = date(y, m, d).isoformat()
            except Exception:
                dlg_msg.value = "Date format must be YYYY-MM-DD."
                page.update()
                return

            try:
                if editing:
                    update_income_transaction(
                        tx_id=tx["id"],
                        title=title,
                        amount=amount,
                        income_type=income_type,
                        transaction_date=tx_date,
                        account_id=acc_id,
                        status=status_dd.value or "confirmed",
                        note=(note_tf.value or "").strip() or None,
                    )
                    message.value = "Income updated."
                else:
                    create_income_transaction(
                        title=title,
                        amount=amount,
                        income_type=income_type,
                        transaction_date=tx_date,
                        account_id=acc_id,
                        status=status_dd.value or "confirmed",
                        note=(note_tf.value or "").strip() or None,
                    )
                    message.value = "Income created."

                close_dialog()
                reload_all()

            except Exception as ex:
                dlg_msg.value = f"Save error: {ex}"
                page.update()

        dlg.title = ft.Text("Edit Income" if editing else "Add Income")
        dlg.content = ft.Column(
            controls=[
                title_tf,
                amount_tf,
                income_type_dd,
                date_tf,
                account_dd,
                status_dd,
                note_tf,
                dlg_msg,
            ],
            tight=True,
            spacing=10,
            width=360,
        )
        dlg.actions = [
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton("Save", icon=ft.Icons.SAVE, on_click=save_tx),
        ]

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        page.update()

    # ---------- Transactions List ----------
    def load_transactions():
        tx_list.controls.clear()

        ym = validate_month()
        if not ym:
            return

        try:
            rows = get_income_transactions_by_month(ym)
        except Exception as ex:
            tx_list.controls.append(
                ft.Text(f"Error loading income: {ex}", color=ft.Colors.RED)
            )
            return

        if not rows:
            tx_list.controls.append(ft.Text("No income for this month."))
            return

        for tx in rows:
            status = tx.get("status", "confirmed")
            income_type = tx.get("income_type", "one_time")

            def edit_tx(e, t=tx):
                open_transaction_form(tx=t)

            def delete_tx(e, t=tx):
                try:
                    delete_income_transaction(t["id"])
                    message.value = "Income deleted."
                    reload_all()
                except Exception as ex:
                    message.value = f"Delete error: {ex}"
                    safe_update()

            status_badge = ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=20,
                bgcolor="#DCFCE7" if status == "confirmed" else "#FEF3C7",
                content=ft.Text(
                    status,
                    size=10,
                    color="#166534" if status == "confirmed" else "#92400E",
                ),
            )

            type_badge = ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=20,
                bgcolor="#DBEAFE" if income_type == "monthly" else "#F3F4F6",
                content=ft.Text(
                    "Monthly" if income_type == "monthly" else "One Time",
                    size=10,
                    color="#1D4ED8" if income_type == "monthly" else "#374151",
                ),
            )

            tx_list.controls.append(
                make_card(
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    # ردیف بالا
                                    ft.Row(
                                        controls=[
                                            ft.Text(
                                                tx.get("title", ""),
                                                size=15,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            type_badge,
                                            status_badge,
                                        ],
                                        spacing=8,
                                    ),

                                    # ردیف پایین
                                    ft.Row(
                                        controls=[
                                            # 👈 سمت چپ (date + amount)
                                            ft.Row(
                                                controls=[
                                                    ft.Text(
                                                        tx.get("transaction_date", ""),
                                                        size=11,
                                                        color="#6B7280",
                                                    ),
                                                    ft.Text(
                                                        f"+{money(tx.get('amount'))}",
                                                        size=13,
                                                        color="#16A34A",
                                                    ),
                                                ],
                                                spacing=10,
                                            ),

                                            # 👈 فاصله‌ساز واقعی
                                            ft.Container(expand=True),

                                            # 👉 دکمه‌ها سمت راست
                                            ft.Row(
                                                controls=[
                                                    ft.IconButton(
                                                        icon=ft.Icons.EDIT_OUTLINED,
                                                        icon_size=15,
                                                        tooltip="Edit",
                                                        on_click=edit_tx,
                                                        style=ft.ButtonStyle(padding=0),
                                                    ),
                                                    ft.IconButton(
                                                        icon=ft.Icons.DELETE_OUTLINE,
                                                        icon_size=15,
                                                        tooltip="Delete",
                                                        icon_color="#DC2626",
                                                        on_click=delete_tx,
                                                        style=ft.ButtonStyle(padding=0),
                                                    ),
                                                ],
                                                spacing=2,
                                            ),
                                        ],
                                        expand=True,  # 👈 خیلی مهم
                                    ),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
            )           
           

 
    def reload_all():
        load_accounts()

        try:
            carry_monthly_income_to_current_month()
        except Exception as ex:
            message.value = f"Monthly carry error: {ex}"

        load_transactions()
        safe_update()
        
    def change_month(e=None):
        if validate_month():
            load_transactions()
            safe_update()

    month_tf.on_submit = change_month
    month_tf.on_blur = change_month

    header_card = ft.Container(
        padding=14,
        border_radius=16,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Back",
                    on_click=lambda e: page.app_go("sabtehazine"),
                ),
                month_tf,
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Refresh month",
                    on_click=change_month,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    transactions_section = ft.Container(
        padding=14,
        border_radius=18,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Income This Month",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            expand=True,
                        ),
                        ft.ElevatedButton(
                            "Add Income",
                            icon=ft.Icons.ADD,
                            on_click=lambda e: open_transaction_form(),
                        ),
                    ],
                ),
                tx_list,
            ],
            spacing=12,
        ),
    )

    reload_all()

    return ft.View(
        route="/income",
        controls=[
            ft.Container(
                padding=15,
                expand=True,
                content=ft.Column(
                    controls=[
                        header_card,
                        transactions_section,
                        message,
                    ],
                    spacing=15,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
        ],
    )