
import flet as ft
from services.utils import today_local, safe_picker_date
import asyncio



def normalize_amount_text(value: str, allow_negative: bool = False) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    digits_map = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬,−–—",
        "01234567890123456789...---"
    )
    text = text.translate(digits_map)

    cleaned = []
    has_dot = False
    has_minus = False

    for ch in text:
        if ch.isdigit():
            cleaned.append(ch)

        elif ch == "." and not has_dot:
            cleaned.append(".")
            has_dot = True

        elif ch == "-" and allow_negative and not has_minus and len(cleaned) == 0:
            cleaned.append("-")
            has_minus = True

    return "".join(cleaned)


def parse_amount(value: str, allow_negative: bool = False):
    text = normalize_amount_text(value, allow_negative=allow_negative)

    if text in ("", "-", ".", "-."):
        raise ValueError("Amount is empty")

    return float(text)


from services.supabase_service import (
    get_accounts,

    get_income_transactions_by_month,
    create_income_transaction,
    update_income_transaction,
    delete_income_transaction,
    carry_monthly_income_to_current_month,

)


def income_view(page: ft.Page):
    page.data = page.data or {}

    selected_year_month = {"value": today_local(page).strftime("%Y-%m")}
    
    accounts_cache = {"data": []}
    tx_list = ft.ListView(
        spacing=10,
        expand=True,
        padding=0,
        auto_scroll=False,
    )

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
            width=float("inf"),
            content=content,
        )

    # ---------- Dialog: Transaction ----------
    def open_transaction_form(tx=None):
        def mobile_dialog_width():
            return min((page.width or 390) * 0.92, 420)


        def mobile_dialog_height():
            return min((page.height or 800) * 0.78, 570)
        editing = tx is not None

        title_tf = ft.TextField(
            label="Title",
            value=(tx or {}).get("title", ""),
        )

        amount_tf = ft.TextField(
            label="Amount",
            value=str((tx or {}).get("amount", "")),
            keyboard_type=ft.KeyboardType.TEXT,
            hint_text="Example: 123.45",
        )

        income_type_dd = ft.Dropdown(
            label="Income Type",
            value=(tx or {}).get("income_type", "one_time"),
            options=[
                ft.dropdown.Option("monthly", "Monthly"),
                ft.dropdown.Option("one_time", "One Time"),
            ],
        )

        def parse_date_safe(value):
            try:
                return safe_picker_date(value, page)
            except Exception:
                return today_local(page)

        current_date = parse_date_safe(
            (tx or {}).get("transaction_date") or today_local(page).isoformat()
        )

        date_picker = ft.DatePicker(value=current_date)

        if date_picker not in page.overlay:
            page.overlay.append(date_picker)

        date_tf = ft.TextField(
            label="Date",
            value=current_date.isoformat(),
            read_only=True,
            expand=True,
        )

        def open_date_picker(e=None):
            date_picker.value = parse_date_safe(date_tf.value)
            date_picker.open = True
            safe_update()

        def on_date_change(e):
            if not date_picker.value:
                return

            picked = safe_picker_date(date_picker.value, page)
            date_picker.value = picked
            date_tf.value = picked.isoformat()
            safe_update()

        date_picker.on_change = on_date_change

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

        saving_state = {"saving": False}
        save_btn = ft.ElevatedButton(
            "Save",
            icon=ft.Icons.SAVE,
            on_click=None,
        )

        def close_dialog(e=None):
            dlg.open = False
            page.update()

        def save_tx(e):
            # جلوگیری قطعی از چند بار کلیک
            if saving_state["saving"]:
                return

            saving_state["saving"] = True
            save_btn.disabled = True
            save_btn.on_click = None
            dlg_msg.value = "Saving..."
            page.update()

            title = (title_tf.value or "").strip()

            if not title:
                dlg_msg.value = "Title is required."
                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
                page.update()
                return

            try:
                amount_tf.value = normalize_amount_text(
                    amount_tf.value,
                    allow_negative=False,
                )
                amount = parse_amount(
                    amount_tf.value,
                    allow_negative=False,
                )
            except ValueError:
                dlg_msg.value = "Amount must be a valid number."
                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
                page.update()
                return

            if amount <= 0:
                dlg_msg.value = "Amount must be > 0."
                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
                page.update()
                return

            acc_id = account_dd.value
            if not acc_id:
                dlg_msg.value = "Select an account."
                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
                page.update()
                return

            income_type = income_type_dd.value or "one_time"

            try:
                tx_date = safe_picker_date(date_tf.value, page).isoformat()
            except Exception:
                dlg_msg.value = "Date format must be YYYY-MM-DD."
                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
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

                selected_year_month["value"] = tx_date[:7]
                month_tf.value = tx_date[:7]

                dlg.open = False
                reload_all()

            except Exception as ex:
                dlg_msg.value = f"Save error: {ex}"

                saving_state["saving"] = False
                save_btn.disabled = False
                save_btn.on_click = save_tx
                page.update()

        dlg.title = ft.Text(
            "Edit Income" if editing else "Add Income",
            size=18,
            weight=ft.FontWeight.W_700,
        )

        dlg.content = ft.Container(
            width=mobile_dialog_width(),
            height=mobile_dialog_height(),
            padding=0,
            content=ft.ListView(
                controls=[
                    title_tf,
                    amount_tf,
                    income_type_dd,

                    ft.Row(
                        controls=[
                            ft.Container(
                                expand=True,
                                content=date_tf,
                                on_click=open_date_picker,
                            ),
                            ft.Container(
                                width=54,
                                height=54,
                                border_radius=14,
                                bgcolor="#EFF6FF",
                                border=ft.border.all(1, "#DBEAFE"),
                                alignment=ft.Alignment.CENTER,
                                ink=True,
                                on_click=open_date_picker,
                                tooltip="Select date",
                                content=ft.Icon(
                                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                                    size=20,
                                    color="#2563EB",
                                ),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),

                    account_dd,
                    status_dd,
                    note_tf,
                    dlg_msg,
                ],
                spacing=10,
                padding=0,
                auto_scroll=False,
            ),
        )

        dlg.inset_padding = 10


        save_btn.on_click = save_tx

        dlg.actions = [
            ft.TextButton("Cancel", on_click=close_dialog),
            save_btn,
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
            rows = get_income_transactions_by_month(ym, page=page)
        except Exception as ex:
            tx_list.controls.append(
                ft.Text(f"Error loading income: {ex}", color=ft.Colors.RED)
            )
            return
        # message.value = f"{len(rows)} rows found. Building list..."
        
        if not rows:
            tx_list.controls.append(ft.Text("No income for this month."))
            return

        for tx in rows:
            try:
                tx_title = str(tx.get("title") or "Untitled")
                tx_date = str(tx.get("transaction_date") or "")
                tx_amount = tx.get("amount") or 0
                status = str(tx.get("status") or "confirmed")
                income_type = str(tx.get("income_type") or "one_time")

                def edit_tx(e, t=tx):
                    open_transaction_form(tx=t)

                def delete_tx(e, t=tx):
                    confirm_dlg = ft.AlertDialog(modal=True)

                    def close_confirm(e=None):
                        confirm_dlg.open = False
                        page.update()

                    def confirm_delete(e=None):
                        try:
                            confirm_dlg.open = False
                            delete_income_transaction(t["id"])
                            message.value = "Income deleted."
                            reload_all()
                        except Exception as ex:
                            message.value = f"Delete error: {ex}"
                            safe_update()

                    confirm_dlg.title = ft.Text("Delete Income?")
                    confirm_dlg.content = ft.Text(
                        f"Are you sure you want to delete '{tx_title}'?"
                    )
                    confirm_dlg.actions = [
                        ft.TextButton("Cancel", on_click=close_confirm),
                        ft.ElevatedButton(
                            "Delete",
                            icon=ft.Icons.DELETE_OUTLINE,
                            bgcolor="#DC2626",
                            color="#FFFFFF",
                            on_click=confirm_delete,
                        ),
                    ]

                    if confirm_dlg not in page.overlay:
                        page.overlay.append(confirm_dlg)

                    confirm_dlg.open = True
                    page.update()

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
                        ft.Column(
                            controls=[
                                # title row فقط عنوان
                                ft.Text(
                                    tx_title,
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),

                                # date + amount + buttons
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            tx_date,
                                            size=11,
                                            color="#6B7280",
                                        ),
                                        ft.Text(
                                            f"+{money(tx_amount)}",
                                            size=13,
                                            color="#16A34A",
                                            expand=True,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            max_lines=1,
                                        ),
                                        ft.Container(
                                            width=30,
                                            content=ft.IconButton(
                                                icon=ft.Icons.EDIT_OUTLINED,
                                                icon_size=16,
                                                tooltip="Edit",
                                                on_click=edit_tx,
                                                style=ft.ButtonStyle(padding=0),
                                            ),
                                        ),
                                        ft.Container(
                                            width=30,
                                            content=ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                icon_size=16,
                                                tooltip="Delete",
                                                icon_color="#DC2626",
                                                on_click=delete_tx,
                                                style=ft.ButtonStyle(padding=0),
                                            ),
                                        ),
                                    ],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),

                                # badges
                                ft.Row(
                                    controls=[
                                        type_badge,
                                        status_badge,
                                    ],
                                    spacing=8,
                                    wrap=True,
                                ),
                            ],
                            spacing=7,
                        )
                    )
                )            
            
            except Exception as ex:
                print(f"[INCOME_VIEW] build row error: {ex} | tx={tx}")
                tx_list.controls.append(
                    ft.Text(f"Row build error: {ex}", color=ft.Colors.RED)
                )
        
 
    monthly_carry_done = {"value": False}

    def reload_all():
        load_accounts()
        load_transactions()
        safe_update()
      
    def change_month(e=None):
        load_transactions()
        safe_update()
        
    month_tf.on_submit = change_month
    month_tf.on_blur = change_month

    def go_back(e=None):
        page.data = page.data or {}

        page.data["sabtehazine_changed"] = False
        page.data["sabtehazine_loaded"] = True

        page.app_go("sabtehazine")

        fn = page.data.get("sabtehazine_request_summary_refresh")
        if callable(fn):
            fn()
        else:
            print("SUMMARY REFRESH FUNCTION NOT FOUND")

    header_card = ft.Container(
        padding=14,
        border_radius=16,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=56,
                    height=56,
                    alignment=ft.Alignment.CENTER,
                    content=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_size=32,
                        width=56,
                        height=56,
                        tooltip="Back",
                        style=ft.ButtonStyle(padding=0),
                        on_click=go_back,
                    ),
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
        expand=True,
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
            expand=True,
        ),
    )

    # reload_all()


    async def load_after_mount():
        await asyncio.sleep(0.15)

        try:
            try:
                created = await asyncio.to_thread(
                    carry_monthly_income_to_current_month,
                    page,
                )

                print(
                    "[INCOME CARRY] checked | created:",
                    len(created or []),
                    flush=True,
                )

            except Exception as ex:
                print("[INCOME CARRY ERROR]", ex, flush=True)

            reload_all()

        except Exception as ex:
            message.value = f"Load error: {ex}"
            safe_update()
            
    view = ft.View(
        route="/income",
        padding=0,
        spacing=0,
        bgcolor="#F8FAFC",
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.SafeArea(
                        avoid_intrusions_top=True,
                        avoid_intrusions_bottom=False,
                        content=ft.Container(
                            padding=ft.padding.only(
                                left=15,
                                right=15,
                                top=8,
                                bottom=8,
                            ),
                            bgcolor="#F8FAFC",
                            content=header_card,
                        ),
                    ),

                    ft.Container(
                        expand=True,
                        padding=ft.padding.only(
                            left=15,
                            right=15,
                            top=8,
                            bottom=12,
                        ),
                        bgcolor="#F8FAFC",
                        content=ft.Column(
                            controls=[
                                transactions_section,
                                message,
                            ],
                            spacing=12,
                            expand=True,
                        ),
                    ),
                ],
            ),
        ],
    )

    page.run_task(load_after_mount)

    return view