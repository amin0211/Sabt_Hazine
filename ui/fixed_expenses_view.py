# ui/fixed_expenses_view.py

import flet as ft
import asyncio

from services.utils import today_local, safe_picker_date

from services.supabase_service import (
    get_accounts,
    get_fixed_expenses,
    create_fixed_expense,
    update_fixed_expense,
    delete_fixed_expense,
)


# ---------------- Amount Helpers ----------------

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


# ---------------- View ----------------

def fixed_expenses_view(page: ft.Page):
    page.data = page.data or {}

    APP_BG = "#F8FAFC"
    CARD_BG = "#FFFFFF"
    FIELD_BG = "#FFFFFF"

    PRIMARY = "#2563EB"
    PRIMARY_SOFT = "#EFF6FF"

    TEXT_MAIN = "#0F172A"
    TEXT_MUTED = "#64748B"

    BORDER = "#E2E8F0"
    BORDER_FOCUS = "#BFDBFE"

    DANGER = "#DC2626"

    accounts_cache = {"data": []}

    fixed_list = ft.ListView(
        spacing=10,
        expand=True,
        padding=0,
        auto_scroll=False,
    )

    message = ft.Text("", size=12, color=TEXT_MUTED)

    initial_reopen_mode = bool(page.data.get("reopen_fixed_expense_dialog"))

    temp_cover = ft.Container(
        visible=initial_reopen_mode,
        expand=True,
        bgcolor=APP_BG,
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            tight=True,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ProgressRing(width=34, height=34, stroke_width=3, color=PRIMARY),
                ft.Text(
                    "در حال باز کردن فرم ویرایش..." if initial_reopen_mode else "در حال باز کردن...",
                    size=13,
                    color=TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    async def go_to_category_picker_after_cover():
        await asyncio.sleep(0.25)
        page.app_go("hazinaha_view")
            
    # ---------------- General Helpers ----------------

    def safe_update():
        try:
            page.update()
        except Exception as ex:
            print("[FIXED EXPENSES SAFE UPDATE SKIPPED]", ex, flush=True)



    def show_temp_cover(message_text="در حال باز کردن..."):
        try:
            temp_cover.visible = True
            main_content.opacity = 0
            temp_cover.content.controls[1].value = message_text
            safe_update()
        except Exception as ex:
            print("[FIXED EXPENSE SHOW TEMP COVER ERROR]", ex, flush=True)

    def hide_temp_cover():
        try:
            temp_cover.visible = False
            main_content.opacity = 1
            safe_update()
        except Exception as ex:
            print("[FIXED EXPENSE HIDE TEMP COVER ERROR]", ex, flush=True)

    def money(v):
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

    def load_accounts():
        try:
            accounts_cache["data"] = get_accounts() or []
            print(
                "[FIXED EXPENSES] accounts loaded:",
                len(accounts_cache["data"]),
                flush=True,
            )
        except Exception as ex:
            accounts_cache["data"] = []
            message.value = f"Load accounts error: {ex}"
            print("[FIXED EXPENSES] load accounts error:", ex, flush=True)

    def account_options():
        return [
            ft.dropdown.Option(acc["id"], acc.get("account_name", ""))
            for acc in accounts_cache["data"]
        ]

    def default_account_id():
        default = next(
            (a for a in accounts_cache["data"] if a.get("is_default")),
            None,
        )

        if default:
            return default["id"]

        if accounts_cache["data"]:
            return accounts_cache["data"][0]["id"]

        return None

    def frequency_label(value):
        labels = {
            "weekly": "Weekly",
            "biweekly": "Every 2 Weeks",
            "monthly": "Monthly",
            "yearly": "Yearly",
        }

        return labels.get(value, value or "-")

    def frequency_color(value):
        if value == "monthly":
            return "#DBEAFE", "#1D4ED8"

        if value == "weekly":
            return "#DCFCE7", "#166534"

        if value == "biweekly":
            return "#FEF3C7", "#92400E"

        if value == "yearly":
            return "#EDE9FE", "#6D28D9"

        return "#F3F4F6", "#374151"

    def status_color(value):
        if value == "active":
            return "#DCFCE7", "#166534"

        if value == "paused":
            return "#FEF3C7", "#92400E"

        return "#FEE2E2", "#991B1B"

    def get_category_name_from_row(row):
        if not row:
            return ""

        nested = row.get("hazineha")

        if isinstance(nested, dict):
            nested_title = nested.get("title")
        else:
            nested_title = ""

        return (
            row.get("category_title")
            or row.get("hazineha_title")
            or row.get("category_name")
            or nested_title
            or ""
        )

    def clear_fixed_expense_form_state():
        page.data.pop("fixed_expense_form_state", None)
        page.data.pop("fixed_expense_editing_id", None)
        page.data["reopen_fixed_expense_dialog"] = False

    def save_form_state(
        *,
        item,
        editing,
        title_tf,
        amount_tf,
        selected_category,
        frequency_dd,
        next_date_tf,
        account_dd,
        status_dd,
        auto_create_switch,
        note_tf,
    ):
        page.data = page.data or {}

        page.data["fixed_expense_form_state"] = {
            "editing": bool(editing),
            "id": (item or {}).get("id"),
            "title": title_tf.value or "",
            "amount": amount_tf.value or "",
            "id_hazine": selected_category.get("id"),
            "category_title": selected_category.get("name") or "",
            "frequency": frequency_dd.value or "monthly",
            "next_run_date": next_date_tf.value or today_local(page).isoformat(),
            "account_id": account_dd.value,
            "status": status_dd.value or "active",
            "auto_create": bool(auto_create_switch.value),
            "note": note_tf.value or "",
        }

        page.data["fixed_expense_editing_id"] = (item or {}).get("id")

        print(
            "[FIXED EXPENSE FORM STATE SAVED]",
            page.data["fixed_expense_form_state"],
            flush=True,
        )

    def get_form_state_for_open(item=None):
        state = page.data.get("fixed_expense_form_state")

        if isinstance(state, dict):
            return state

        return {
            "editing": item is not None,
            "id": (item or {}).get("id"),
            "title": (item or {}).get("title", ""),
            "amount": str((item or {}).get("amount", "")),
            "id_hazine": (item or {}).get("id_hazine"),
            "category_title": get_category_name_from_row(item),
            "frequency": (item or {}).get("frequency", "monthly"),
            "next_run_date": (item or {}).get("next_run_date") or today_local(page).isoformat(),
            "account_id": (item or {}).get("account_id") or default_account_id(),
            "status": (item or {}).get("status", "active"),
            "auto_create": (item or {}).get("auto_create", True),
            "note": (item or {}).get("note", "") or "",
        }

    def make_badge(text, bg, color):
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=20,
            bgcolor=bg,
            content=ft.Text(
                text,
                size=10,
                color=color,
                weight=ft.FontWeight.W_600,
            ),
        )

    def make_card(content):
        return ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=CARD_BG,
            border=ft.border.all(1, BORDER),
            width=float("inf"),
            content=content,
        )

    def build_professional_text_field(
        *,
        label,
        value="",
        hint_text="",
        multiline=False,
        min_lines=1,
        max_lines=1,
        keyboard_type=ft.KeyboardType.TEXT,
    ):
        return ft.TextField(
            label=label,
            value=value,
            hint_text=hint_text,
            multiline=multiline,
            min_lines=min_lines,
            max_lines=max_lines,
            keyboard_type=keyboard_type,
            text_size=14,
            border_radius=16,
            border_color=BORDER,
            focused_border_color=BORDER_FOCUS,
            bgcolor=FIELD_BG,
            cursor_color=PRIMARY,
            content_padding=ft.padding.only(left=14, right=14, top=13, bottom=13),
        )

    def build_professional_dropdown(
        *,
        label,
        value,
        options,
    ):
        return ft.Dropdown(
            label=label,
            value=value,
            options=options,
            text_size=14,
            border_radius=16,
            border_color=BORDER,
            focused_border_color=BORDER_FOCUS,
            bgcolor=FIELD_BG,
            content_padding=ft.padding.only(left=14, right=14, top=10, bottom=10),
        )

    # ---------------- Dialog: Fixed Expense ----------------

    def open_fixed_expense_form(item=None, from_reopen=False):
        print("[FIXED EXPENSE FORM] open", item, "from_reopen=", from_reopen, flush=True)

        def mobile_dialog_width():
            return min((page.width or 390) * 0.92, 440)

        def mobile_dialog_height():
            return min((page.height or 800) * 0.74, 620)

        state = get_form_state_for_open(item=item)

        editing = bool(state.get("editing") or item is not None)
        editing_id = state.get("id") or ((item or {}).get("id"))

        selected_category = {
            "id": state.get("id_hazine"),
            "name": state.get("category_title") or (
                f"Category #{state.get('id_hazine')}"
                if state.get("id_hazine")
                else ""
            ),
        }

        title_tf = build_professional_text_field(
            label="Title",
            value=state.get("title") or "",
            hint_text="Example: Rent, Netflix, Insurance",
        )

        amount_tf = build_professional_text_field(
            label="Amount",
            value=str(state.get("amount") or ""),
            hint_text="Example: 120.00",
            keyboard_type=ft.KeyboardType.TEXT,
        )

        frequency_dd = build_professional_dropdown(
            label="Repeat",
            value=state.get("frequency") or "monthly",
            options=[
                ft.dropdown.Option("weekly", "Weekly"),
                ft.dropdown.Option("biweekly", "Every 2 Weeks"),
                ft.dropdown.Option("monthly", "Monthly"),
                ft.dropdown.Option("yearly", "Yearly"),
            ],
        )


        def parse_date_safe(value):
            try:
                return safe_picker_date(value, page)
            except Exception:
                return today_local(page)

        current_next_date = parse_date_safe(
            state.get("next_run_date") or today_local(page).isoformat()
        )

        next_date_picker = ft.DatePicker(value=current_next_date)

        if next_date_picker not in page.overlay:
            page.overlay.append(next_date_picker)

        next_date_tf = build_professional_text_field(
            label="Next Withdrawal Date",
            value=current_next_date.isoformat(),
            hint_text="YYYY-MM-DD",
        )

        next_date_tf.read_only = True

        def open_next_date_picker(e=None):
            next_date_picker.value = parse_date_safe(next_date_tf.value)
            next_date_picker.open = True
            safe_update()

        def on_next_date_change(e):
            if not next_date_picker.value:
                return

            picked = safe_picker_date(next_date_picker.value, page)
            next_date_picker.value = picked
            next_date_tf.value = picked.isoformat()
            safe_update()

        next_date_picker.on_change = on_next_date_change


        account_dd = build_professional_dropdown(
            label="Withdraw From Account",
            options=account_options(),
            value=state.get("account_id") or default_account_id(),
        )

        status_dd = build_professional_dropdown(
            label="Status",
            value=state.get("status") or "active",
            options=[
                ft.dropdown.Option("active", "Active"),
                ft.dropdown.Option("paused", "Paused"),
                ft.dropdown.Option("cancelled", "Cancelled"),
            ],
        )

        auto_create_switch = ft.Switch(
            label=None,
            value=bool(state.get("auto_create", True)),
            active_color=PRIMARY,
        )

        note_tf = build_professional_text_field(
            label="Note",
            value=state.get("note") or "",
            multiline=True,
            min_lines=2,
            max_lines=3,
        )

        dlg_msg = ft.Text("", size=12, color=DANGER)

        dlg = ft.AlertDialog(modal=True)
        saving_state = {"saving": False}

        save_btn = ft.ElevatedButton(
            "Save",
            icon=ft.Icons.SAVE_ROUNDED,
            on_click=None,
            style=ft.ButtonStyle(
                bgcolor=PRIMARY,
                color="#FFFFFF",
                elevation=3,
                shadow_color="#33000000",
                shape=ft.RoundedRectangleBorder(radius=18),
                padding=ft.padding.symmetric(horizontal=24, vertical=15),
            ),
        )

        category_title_text = ft.Text(
            selected_category["name"] or "Select category",
            size=14,
            color=TEXT_MAIN if selected_category["id"] else TEXT_MUTED,
            weight=ft.FontWeight.W_600 if selected_category["id"] else ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )

        def open_category_picker(e=None):
            page.data = page.data or {}

            save_form_state(
                item={"id": editing_id} if editing_id else item,
                editing=editing,
                title_tf=title_tf,
                amount_tf=amount_tf,
                selected_category=selected_category,
                frequency_dd=frequency_dd,
                next_date_tf=next_date_tf,
                account_dd=account_dd,
                status_dd=status_dd,
                auto_create_switch=auto_create_switch,
                note_tf=note_tf,
            )

            def on_category_selected(category):
                try:
                    category_id = (
                        category.get("category_id")
                        or category.get("id")
                        or category.get("id_hazine")
                    )

                    category_title = (
                        category.get("category_title")
                        or category.get("title")
                        or category.get("name")
                        or category.get("hazineha_title")
                        or f"Category #{category_id}"
                    )

                    form_state = page.data.get("fixed_expense_form_state") or {}

                    form_state["id_hazine"] = category_id
                    form_state["category_title"] = category_title

                    page.data["fixed_expense_form_state"] = form_state
                    page.data["reopen_fixed_expense_dialog"] = True

                    print(
                        "[FIXED EXPENSE CATEGORY SELECTED]",
                        form_state,
                        flush=True,
                    )

                except Exception as ex:
                    print("[FIXED EXPENSE CATEGORY SELECT ERROR]", ex, flush=True)

            page.data["from"] = "fixed_expenses_view"
            page.data["category_picker_mode"] = True
            page.data["category_picker_current_id"] = selected_category.get("id")
            page.data["category_picker_on_selected"] = on_category_selected
            page.data["without_edit"] = True
            page.data["reopen_fixed_expense_dialog"] = True

            print(
                "[FIXED EXPENSE OPEN CATEGORY PICKER]",
                page.data.get("fixed_expense_form_state"),
                flush=True,
            )

            dlg.open = False
            show_temp_cover("در حال باز کردن دسته‌بندی...")
            safe_update()

            page.run_task(go_to_category_picker_after_cover)           

        def build_category_field():
            selected = bool(selected_category.get("id"))

            category_tf = build_professional_text_field(
                label="Category",
                value=selected_category["name"] or "Select category",
                hint_text="Select category",
            )

            category_tf.read_only = True
            category_tf.color = TEXT_MAIN if selected else TEXT_MUTED

            return ft.Row(
                controls=[
                    ft.Container(
                        expand=True,
                        content=ft.GestureDetector(
                            on_tap=open_category_picker,
                            mouse_cursor=ft.MouseCursor.CLICK,
                            content=category_tf,
                        ),
                    ),

                    ft.Container(
                        width=58,
                        height=58,
                        border_radius=18,
                        bgcolor=PRIMARY_SOFT,
                        border=ft.border.all(1, "#DBEAFE"),
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=open_category_picker,
                        content=ft.Icon(
                            ft.Icons.ACCOUNT_TREE_OUTLINED,
                            size=22,
                            color=PRIMARY,
                        ),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        category_field = build_category_field()

        def close_dialog(e=None):
            dlg.open = False

            if not from_reopen:
                clear_fixed_expense_form_state()

            safe_update()

        def reset_save_button():
            saving_state["saving"] = False
            save_btn.disabled = False
            save_btn.on_click = save_fixed_expense
            safe_update()

        def save_fixed_expense(e=None):
            print("[FIXED EXPENSE SAVE CLICKED]", flush=True)

            if saving_state["saving"]:
                print("[FIXED EXPENSE SAVE] ignored: already saving", flush=True)
                return

            saving_state["saving"] = True
            save_btn.disabled = True
            save_btn.on_click = None
            dlg_msg.value = "Saving..."
            safe_update()

            title = (title_tf.value or "").strip()

            if not title:
                dlg_msg.value = "Title is required."
                reset_save_button()
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

            except Exception:
                dlg_msg.value = "Amount must be a valid number."
                reset_save_button()
                return

            if amount <= 0:
                dlg_msg.value = "Amount must be > 0."
                reset_save_button()
                return

            category_id = selected_category.get("id")

            if not category_id:
                category_id = (
                    page.data.get("fixed_expense_form_state") or {}
                ).get("id_hazine")

            if not category_id:
                print("[FIXED EXPENSE SAVE] missing category", flush=True)
                dlg_msg.value = "Select a category."
                reset_save_button()
                return

            acc_id = account_dd.value

            if not acc_id:
                print("[FIXED EXPENSE SAVE] missing account", flush=True)
                dlg_msg.value = "Select an account."
                reset_save_button()
                return

            frequency = frequency_dd.value or "monthly"

            try:
                next_run_date = safe_picker_date(next_date_tf.value, page).isoformat()
            except Exception:
                dlg_msg.value = "Date format must be YYYY-MM-DD."
                reset_save_button()
                return

            payload = {
                "title": title,
                "amount": amount,
                "id_hazine": category_id,
                "frequency": frequency,
                "next_run_date": next_run_date,
                "account_id": acc_id,
                "status": status_dd.value or "active",
                "auto_create": bool(auto_create_switch.value),
                "note": (note_tf.value or "").strip() or None,
            }

            print("[FIXED EXPENSE PAYLOAD]", payload, flush=True)

            try:
                if editing:
                    if not editing_id:
                        raise Exception("Editing id is missing.")

                    update_fixed_expense(
                        fixed_expense_id=editing_id,
                        **payload,
                    )

                    message.value = "Fixed expense updated."

                else:
                    create_fixed_expense(**payload)
                    message.value = "Fixed expense created."

                print("[FIXED EXPENSE SAVE SUCCESS]", flush=True)

                dlg.open = False
                clear_fixed_expense_form_state()
                reload_all()

            except Exception as ex:
                print("[FIXED EXPENSE SAVE ERROR]", ex, flush=True)
                dlg_msg.value = f"Save error: {ex}"
                reset_save_button()

        title_row = ft.Row(
            [
                ft.Container(
                    width=52,
                    height=52,
                    border_radius=18,
                    bgcolor=PRIMARY_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.EVENT_REPEAT_ROUNDED,
                        size=26,
                        color=PRIMARY,
                    ),
                ),

                ft.Column(
                    [
                        ft.Text(
                            "Edit Fixed Expense" if editing else "Add Fixed Expense",
                            size=20,
                            weight=ft.FontWeight.W_800,
                            color=TEXT_MAIN,
                        ),
                        ft.Text(
                            "Manage recurring withdrawals",
                            size=12,
                            color=TEXT_MUTED,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        form_card = ft.Container(
            bgcolor="#FFFFFF",
            border_radius=28,
            padding=ft.padding.only(left=16, right=16, top=18, bottom=18),
            border=ft.border.all(1, "#E5E7EB"),
            content=ft.Column(
                [
                    ft.Text(
                        "Basic Information",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color=TEXT_MUTED,
                    ),

                    title_tf,
                    amount_tf,

                    category_field,

                    frequency_dd,
                    status_dd,

                    ft.Row(
                        controls=[
                            ft.Container(
                                expand=True,
                                content=next_date_tf,
                                on_click=open_next_date_picker,
                            ),
                            ft.Container(
                                width=58,
                                height=58,
                                border_radius=18,
                                bgcolor=PRIMARY_SOFT,
                                border=ft.border.all(1, "#DBEAFE"),
                                alignment=ft.Alignment.CENTER,
                                ink=True,
                                on_click=open_next_date_picker,
                                tooltip="Select date",
                                content=ft.Icon(
                                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                                    size=22,
                                    color=PRIMARY,
                                ),
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),

                   

                    account_dd,

                    ft.Container(height=4),

                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border_radius=18,
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=38,
                                    height=38,
                                    border_radius=13,
                                    bgcolor="#ECFDF5",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        ft.Icons.AUTORENEW_ROUNDED,
                                        size=20,
                                        color="#16A34A",
                                    ),
                                ),

                                ft.Container(
                                    expand=True,
                                    content=ft.Column(
                                        controls=[
                                            ft.Text(
                                                "Auto create",
                                                size=13,
                                                weight=ft.FontWeight.W_700,
                                                color=TEXT_MAIN,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                "Create expense when due",
                                                size=10,
                                                color=TEXT_MUTED,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                        ],
                                        spacing=1,
                                        tight=True,
                                    ),
                                ),

                                ft.Container(
                                    width=54,
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                    content=auto_create_switch,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),

                    note_tf,
                    dlg_msg,
                ],
                spacing=12,
                tight=True,
            ),
        )

        dlg.title = title_row

        dlg.content = ft.Container(
            width=mobile_dialog_width(),
            height=mobile_dialog_height(),
            padding=0,
            content=ft.ListView(
                controls=[
                    form_card,
                ],
                spacing=0,
                padding=ft.padding.only(right=2),
                auto_scroll=False,
            ),
        )
        dlg.inset_padding = 10

        save_btn.on_click = save_fixed_expense

        dlg.actions = [
            ft.Container(
                padding=ft.padding.only(left=8, right=8, bottom=4),
                content=ft.Row(
                    [
                        ft.TextButton(
                            "Cancel",
                            on_click=close_dialog,
                            style=ft.ButtonStyle(
                                color=TEXT_MUTED,
                                shape=ft.RoundedRectangleBorder(radius=16),
                                padding=ft.padding.symmetric(horizontal=20, vertical=14),
                            ),
                        ),
                        ft.Container(expand=True),
                        save_btn,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        ]

        dlg.actions_alignment = ft.MainAxisAlignment.CENTER


        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        safe_update()

        print("[FIXED EXPENSE ADD DIALOG OPENED]", flush=True)

    # ---------------- List ----------------

    def load_fixed_expenses():
        fixed_list.controls.clear()

        try:
            rows = get_fixed_expenses(page=page) or []
            print("[FIXED EXPENSES] rows loaded:", len(rows), flush=True)
        except Exception as ex:
            fixed_list.controls.append(
                ft.Text(
                    f"Error loading fixed expenses: {ex}",
                    color=ft.Colors.RED,
                )
            )
            print("[FIXED EXPENSES] load error:", ex, flush=True)
            return

        if not rows:
            fixed_list.controls.append(
                ft.Container(
                    height=220,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.EVENT_REPEAT_OUTLINED,
                                size=42,
                                color="#CBD5E1",
                            ),
                            ft.Text(
                                "No fixed expenses yet.",
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=TEXT_MUTED,
                            ),
                            ft.Text(
                                "Add rent, subscriptions, insurance, or other recurring payments.",
                                size=11,
                                color="#94A3B8",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            return

        for item in rows:
            try:
                item_title = str(item.get("title") or "Untitled")
                item_amount = item.get("amount") or 0
                frequency = str(item.get("frequency") or "monthly")
                status = str(item.get("status") or "active")
                next_run_date = str(item.get("next_run_date") or "")
                auto_create = bool(item.get("auto_create", True))
                category_name = get_category_name_from_row(item)

                if not category_name and item.get("id_hazine"):
                    category_name = f"Category #{item.get('id_hazine')}"

                freq_bg, freq_text = frequency_color(frequency)
                status_bg, status_text = status_color(status)

                def edit_item(e, selected=item):
                    clear_fixed_expense_form_state()
                    open_fixed_expense_form(item=selected)

                def delete_item(e, selected=item):
                    confirm_dlg = ft.AlertDialog(modal=True)

                    def close_confirm(e=None):
                        confirm_dlg.open = False
                        safe_update()

                    def confirm_delete(e=None):
                        try:
                            confirm_dlg.open = False
                            delete_fixed_expense(selected["id"])
                            message.value = "Fixed expense deleted."
                            reload_all()
                        except Exception as ex:
                            message.value = f"Delete error: {ex}"
                            safe_update()

                    confirm_dlg.title = ft.Text("Delete Fixed Expense?")
                    confirm_dlg.content = ft.Text(
                        f"Are you sure you want to delete '{item_title}'?"
                    )

                    confirm_dlg.actions = [
                        ft.TextButton("Cancel", on_click=close_confirm),
                        ft.ElevatedButton(
                            "Delete",
                            icon=ft.Icons.DELETE_OUTLINE,
                            bgcolor=DANGER,
                            color="#FFFFFF",
                            on_click=confirm_delete,
                        ),
                    ]

                    if confirm_dlg not in page.overlay:
                        page.overlay.append(confirm_dlg)

                    confirm_dlg.open = True
                    safe_update()

                auto_bg = "#ECFDF5" if auto_create else "#F3F4F6"
                auto_text_color = "#047857" if auto_create else "#374151"

                action_buttons = ft.Row(
                    controls=[
                        ft.Container(
                            width=34,
                            height=34,
                            border_radius=11,
                            bgcolor="#EFF6FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_size=17,
                                tooltip="Edit",
                                icon_color=PRIMARY,
                                width=34,
                                height=34,
                                style=ft.ButtonStyle(padding=0),
                                on_click=edit_item,
                            ),
                        ),

                        ft.Container(
                            width=34,
                            height=34,
                            border_radius=11,
                            bgcolor="#FEF2F2",
                            alignment=ft.Alignment.CENTER,
                            content=ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=17,
                                tooltip="Delete",
                                icon_color=DANGER,
                                width=34,
                                height=34,
                                style=ft.ButtonStyle(padding=0),
                                on_click=delete_item,
                            ),
                        ),
                    ],
                    spacing=6,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )

                badges_row = ft.Row(
                    controls=[
                        make_badge(frequency_label(frequency), freq_bg, freq_text),
                        make_badge(status, status_bg, status_text),
                        make_badge(
                            "Auto" if auto_create else "Manual",
                            auto_bg,
                            auto_text_color,
                        ),
                    ],
                    spacing=6,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )

                fixed_list.controls.append(
                    make_card(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            width=44,
                                            height=44,
                                            border_radius=15,
                                            bgcolor=PRIMARY_SOFT,
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(
                                                ft.Icons.EVENT_REPEAT_ROUNDED,
                                                size=21,
                                                color=PRIMARY,
                                            ),
                                        ),

                                        ft.Column(
                                            controls=[
                                                ft.Text(
                                                    item_title,
                                                    size=15,
                                                    weight=ft.FontWeight.W_800,
                                                    color=TEXT_MAIN,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    max_lines=1,
                                                ),

                                                ft.Text(
                                                    f"Next: {next_run_date}",
                                                    size=11,
                                                    color=TEXT_MUTED,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    max_lines=1,
                                                ),

                                                ft.Text(
                                                    category_name or "No category",
                                                    size=11,
                                                    color=TEXT_MUTED,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    max_lines=1,
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text(
                                                    f"-{money(item_amount)}",
                                                    size=14,
                                                    color=DANGER,
                                                    weight=ft.FontWeight.W_800,
                                                    text_align=ft.TextAlign.RIGHT,
                                                ),
                                                action_buttons,
                                            ],
                                            spacing=6,
                                            horizontal_alignment=ft.CrossAxisAlignment.END,
                                        ),
                                    ],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                ),



                                badges_row,
                            ],
                            spacing=10,
                        )
                    )
                )

            except Exception as ex:
                print(
                    f"[FIXED_EXPENSES_VIEW] build row error: {ex} | item={item}",
                    flush=True,
                )

                fixed_list.controls.append(
                    ft.Text(f"Row build error: {ex}", color=ft.Colors.RED)
                )

    def reload_all():
        load_accounts()
        load_fixed_expenses()
        safe_update()

    # ---------------- Navigation ----------------

    def go_back(e=None):
        page.data = page.data or {}

        clear_fixed_expense_form_state()

        page.data["sabtehazine_changed"] = False
        page.data["sabtehazine_loaded"] = True

        page.app_go("sabtehazine")

        fn = page.data.get("sabtehazine_request_summary_refresh")

        if callable(fn):
            fn()
        else:
            print("SUMMARY REFRESH FUNCTION NOT FOUND", flush=True)

    # ---------------- Layout ----------------

    header_card = ft.Container(
        padding=14,
        border_radius=18,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER),
        content=ft.Row(
            controls=[
                ft.Container(
                    width=48,
                    height=48,
                    border_radius=16,
                    bgcolor="#F8FAFC",
                    alignment=ft.Alignment.CENTER,
                    content=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_size=26,
                        icon_color=TEXT_MAIN,
                        width=48,
                        height=48,
                        tooltip="Back",
                        style=ft.ButtonStyle(padding=0),
                        on_click=go_back,
                    ),
                ),

                ft.Column(
                    controls=[
                        ft.Text(
                            "Fixed Expenses",
                            size=18,
                            weight=ft.FontWeight.W_800,
                            color=TEXT_MAIN,
                        ),
                        ft.Text(
                            "Recurring withdrawals from your accounts",
                            size=11,
                            color=TEXT_MUTED,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),

                ft.Container(
                    width=42,
                    height=42,
                    border_radius=14,
                    bgcolor=PRIMARY_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=PRIMARY,
                        tooltip="Refresh",
                        icon_size=20,
                        width=42,
                        height=42,
                        style=ft.ButtonStyle(padding=0),
                        on_click=lambda e: reload_all(),
                    ),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    fixed_section = ft.Container(
        padding=14,
        border_radius=20,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER),
        expand=True,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            [
                                ft.Text(
                                    "Recurring Expenses",
                                    size=17,
                                    weight=ft.FontWeight.W_800,
                                    color=TEXT_MAIN,
                                ),
                                ft.Text(
                                    "Rent, subscriptions, bills, and other repeated costs",
                                    size=10,
                                    color=TEXT_MUTED,
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),

                        ft.ElevatedButton(
                            "Add",
                            icon=ft.Icons.ADD_ROUNDED,
                            on_click=lambda e: (
                                print("[FIXED EXPENSE ADD CLICKED]", flush=True),
                                clear_fixed_expense_form_state(),
                                open_fixed_expense_form(),
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=PRIMARY_SOFT,
                                color=PRIMARY,
                                shape=ft.RoundedRectangleBorder(radius=16),
                                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            ),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),

                fixed_list,
            ],
            spacing=14,
            expand=True,
        ),
    )

    async def load_after_mount():
        await asyncio.sleep(0.05)

        try:
            should_reopen = bool(page.data.get("reopen_fixed_expense_dialog"))

            if should_reopen:
                temp_cover.visible = True
                main_content.opacity = 0
                temp_cover.content.controls[1].value = "در حال باز کردن فرم ویرایش..."
                safe_update()

                load_accounts()

                print(
                    "[FIXED EXPENSE REOPEN REQUEST]",
                    page.data.get("fixed_expense_form_state"),
                    flush=True,
                )

                page.data["reopen_fixed_expense_dialog"] = False

                await asyncio.sleep(0.20)

                open_fixed_expense_form(
                    item=None,
                    from_reopen=True,
                )

                await asyncio.sleep(0.05)
                hide_temp_cover()
                return

            reload_all()

        except Exception as ex:
            message.value = f"Load error: {ex}"
            print("[FIXED EXPENSES LOAD AFTER MOUNT ERROR]", ex, flush=True)
            hide_temp_cover()
            safe_update()
            

    main_content = ft.Column(
        expand=True,
        spacing=0,
        opacity=0 if initial_reopen_mode else 1,
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
                    bgcolor=APP_BG,
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
                bgcolor=APP_BG,
                content=ft.Column(
                    controls=[
                        fixed_section,
                        message,
                    ],
                    spacing=12,
                    expand=True,
                ),
            ),
        ],
    )

    view = ft.View(
        route="/fixed_expenses",
        padding=0,
        spacing=0,
        bgcolor=APP_BG,
        controls=[
            ft.Stack(
                expand=True,
                controls=[
                    main_content,
                    temp_cover,
                ],
            )
        ],
    )

    page.run_task(load_after_mount)

    return view