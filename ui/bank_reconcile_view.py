import asyncio
import os
import flet as ft

from services.utils import safe_picker_date
from services.i18n import t
from services.bank_import_parser import parse_bank_file

from services.supabase_service import (
    get_accounts,
    get_members,
    load_leaf_hazineha,
    create_bank_import,
    get_bank_imports,
    get_bank_import_rows,
    add_bank_import_rows,
    update_bank_import_status,
    prepare_bank_import_rows_for_save,
    update_bank_import_row_decision,
    insert_cost_for_current_user,
    mark_bank_row_as_created_cost,
    get_my_cost_by_id,
    update_my_cost,
    get_income_transaction_by_id,
    create_income_transaction,
    update_income_transaction,
    mark_bank_row_as_created_income,
)


def bank_reconcile_view(page: ft.Page, theme):
    APP_BG = theme["APP_BG"]
    CARD = theme["CARD"]
    PRIMARY = theme["PRIMARY"]
    TEXT = theme["TEXT"]

    selected_filter = {"value": "all"}
    current_rows = {"items": []}

    selected_account = {"id": None}
    selected_import = {"id": None}

    selected_file = {
        "path": None,
        "name": None,
    }

    file_pick_state = {
        "handled": False,
    }

    def safe_update():
        try:
            page.update()
        except Exception as ex:
            print("[BANK RECONCILE] safe_update error:", ex, flush=True)

    def set_status(message, color="#64748B"):
        status_text.value = message
        status_text.color = color
        safe_update()

    def show_empty_message(message, color="#64748B"):
        rows_column.controls.clear()
        update_summary_from_rows([])

        rows_column.controls.append(
            ft.Container(
                bgcolor=CARD,
                border_radius=16,
                padding=20,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(
                    message,
                    size=13,
                    color=color,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )

        safe_update()

    def handle_picked_file_result(e, source="unknown"):
        try:
            print(f"[BANK RECONCILE] handle_picked_file_result source={source}", flush=True)
            print("[BANK RECONCILE] picked raw result:", e, flush=True)

            if file_pick_state["handled"]:
                print("[BANK RECONCILE] file result already handled, skipping", flush=True)
                return

            if isinstance(e, list):
                files = e
            else:
                files = getattr(e, "files", None)

            print("[BANK RECONCILE] normalized picked files:", files, flush=True)

            if not files:
                set_status(t(page, "bank_no_file_selected"), "#64748B")
                return

            picked = files[0]

            file_path = getattr(picked, "path", None)
            file_name = getattr(picked, "name", None)

            print("[BANK RECONCILE] picked file name:", file_name, flush=True)
            print("[BANK RECONCILE] picked file path:", file_path, flush=True)

            if not file_path:
                set_status(t(page, "bank_file_path_missing"), "#DC2626")
                show_empty_message(t(page, "bank_file_path_missing_detail"), "#DC2626")
                return

            file_pick_state["handled"] = True

            selected_file["path"] = file_path
            selected_file["name"] = file_name or os.path.basename(file_path)

            selected_import["id"] = None
            selected_filter["value"] = "all"
            current_rows["items"] = []
            update_summary_from_rows([])

            set_status(f"{t(page, 'bank_file_selected')}: {selected_file['name']}", "#16A34A")
            show_loading_state(t(page, "bank_preparing_file"))

            page.run_task(process_selected_file_async)

        except Exception as ex:
            print("[BANK RECONCILE] handle picked file error:", ex, flush=True)
            set_status(f"{t(page, 'bank_pick_file_error')}: {ex}", "#DC2626")

    def on_file_picker_result(e):
        print("[BANK RECONCILE] on_file_picker_result called", flush=True)
        handle_picked_file_result(e, source="on_result")

    file_picker = ft.FilePicker()
    file_picker.on_result = on_file_picker_result

    page_list = ft.ListView(
        expand=True,
        spacing=0,
        padding=0,
        auto_scroll=False,
    )

    rows_column = ft.Column(
        spacing=10,
        controls=[],
    )

    status_text = ft.Text(
        "",
        size=13,
        color="#64748B",
        text_align=ft.TextAlign.CENTER,
        max_lines=3,
    )

    account_dropdown = ft.Dropdown(
        label=t(page, "bank_account"),
        width=320,
        options=[],
    )

    summary_all_text = ft.Text(
        f"{t(page, 'bank_summary_all')}: 0",
        size=12,
        color="#64748B",
        weight=ft.FontWeight.BOLD,
    )

    summary_new_text = ft.Text(
        f"{t(page, 'bank_summary_new')}: 0",
        size=12,
        color="#2563EB",
        weight=ft.FontWeight.BOLD,
    )

    summary_confirmed_text = ft.Text(
        f"{t(page, 'bank_summary_confirmed')}: 0",
        size=12,
        color="#CA8A04",
        weight=ft.FontWeight.BOLD,
    )

    summary_review_text = ft.Text(
        f"{t(page, 'bank_summary_review')}: 0",
        size=12,
        color="#EA580C",
        weight=ft.FontWeight.BOLD,
    )

    summary_all = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=999,
        content=summary_all_text,
        on_click=lambda e: set_filter("all"),
    )

    summary_new = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=999,
        content=summary_new_text,
        on_click=lambda e: set_filter("new"),
    )

    summary_confirmed = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=999,
        content=summary_confirmed_text,
        on_click=lambda e: set_filter("confirmed"),
    )

    summary_review = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        border_radius=999,
        content=summary_review_text,
        on_click=lambda e: set_filter("review"),
    )

    def update_summary_styles():
        active_bg = "#E0F2FE"
        normal_bg = None

        summary_all.bgcolor = active_bg if selected_filter["value"] == "all" else normal_bg
        summary_new.bgcolor = active_bg if selected_filter["value"] == "new" else normal_bg
        summary_confirmed.bgcolor = active_bg if selected_filter["value"] == "confirmed" else normal_bg
        summary_review.bgcolor = active_bg if selected_filter["value"] == "review" else normal_bg

    def show_loading_state(message=None):
        if message is None:
            message = t(page, "bank_reading_file")

        rows_column.controls.clear()
        update_summary_from_rows([])

        rows_column.controls.append(
            ft.Container(
                bgcolor=CARD,
                border_radius=16,
                padding=20,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.ProgressRing(width=32, height=32, stroke_width=3),
                        ft.Text(
                            message,
                            size=13,
                            color="#64748B",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            )
        )

        safe_update()

    async def choose_file_path(e):
        print("[BANK RECONCILE] choose_file_path clicked", flush=True)

        try:
            file_pick_state["handled"] = False

            result = await file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["csv", "qbo", "qfx", "ofx"],
            )

            print("[BANK RECONCILE] pick_files returned:", result, flush=True)

            if result is not None:
                handle_picked_file_result(result, source="await_return")
            else:
                print("[BANK RECONCILE] pick_files returned None; waiting for on_result", flush=True)

        except Exception as ex:
            print("[BANK RECONCILE] choose_file_path error:", ex, flush=True)
            set_status(f"{t(page, 'bank_pick_file_error')}: {ex}", "#DC2626")

    def get_file_ext(file_name):
        file_name = file_name or ""

        if "." not in file_name:
            return ""

        return file_name.rsplit(".", 1)[-1].lower().strip()

    def normalize_bank_date_for_form(value):
        if value is None:
            return ""

        text = str(value).strip()

        text = (
            text.replace("\u200e", "")
            .replace("\u200f", "")
            .replace("\u202a", "")
            .replace("\u202b", "")
            .replace("\u202c", "")
            .replace("\u00a0", "")
            .strip()
        )

        digits_map = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789",
        )

        text = text.translate(digits_map)
        text = text.replace("/", "-").replace(".", "-")

        if len(text) == 8 and text.isdigit():
            return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"

        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]

        return text

    def load_accounts():
        try:
            accounts = get_accounts()

            account_dropdown.options = [
                ft.dropdown.Option(
                    key=str(a["id"]),
                    text=a.get("account_name") or "Account",
                )
                for a in accounts
            ]

            if accounts and not selected_account["id"]:
                selected_account["id"] = accounts[0]["id"]
                account_dropdown.value = str(accounts[0]["id"])

            if not accounts:
                status_text.value = t(page, "bank_no_account_message")
                status_text.color = "#DC2626"

            safe_update()

        except Exception as ex:
            print("[BANK RECONCILE] load_accounts error:", ex, flush=True)
            set_status(f"{t(page, 'bank_load_accounts_error')}: {ex}", "#DC2626")

    def on_account_change(e):
        try:
            selected_account["id"] = account_dropdown.value
            print("[BANK RECONCILE] selected_account:", selected_account["id"], flush=True)
        except Exception:
            selected_account["id"] = None

    account_dropdown.on_change = on_account_change

    def update_summary_from_rows(rows):
        total = len(rows)
        new_count = 0
        confirmed_count = 0
        review_count = 0

        for r in rows:
            status = r.get("match_status") or "new"

            if status == "new":
                new_count += 1
            elif status == "confirmed":
                confirmed_count += 1
            elif status in ("matched", "possible_match", "needs_review", "error"):
                review_count += 1

        summary_all_text.value = f"{t(page, 'bank_summary_all')}: {total}"
        summary_new_text.value = f"{t(page, 'bank_summary_new')}: {new_count}"
        summary_confirmed_text.value = f"{t(page, 'bank_summary_confirmed')}: {confirmed_count}"
        summary_review_text.value = f"{t(page, 'bank_summary_review')}: {review_count}"

        update_summary_styles()

    def build_import_row_card(row):
        amount = float(row.get("amount") or 0)
        amount_text = f"{amount:,.2f}"

        status = row.get("match_status") or "new"

        if status == "confirmed":
            status_label = t(page, "bank_status_confirmed")
            status_color = "#16A34A"
        elif status == "matched":
            status_label = t(page, "bank_status_matched")
            status_color = "#16A34A"
        elif status == "possible_match":
            status_label = t(page, "bank_status_possible_match")
            status_color = "#CA8A04"
        elif status == "needs_review":
            status_label = t(page, "bank_status_needs_review")
            status_color = "#EA580C"
        elif status == "ignored":
            status_label = t(page, "bank_status_ignored")
            status_color = "#64748B"
        elif status == "error":
            status_label = t(page, "bank_status_error")
            status_color = "#DC2626"
        else:
            status_label = t(page, "bank_status_new")
            status_color = "#2563EB"

        is_done = status == "confirmed"

        has_matched_cost = bool(row.get("matched_cost_id"))
        has_matched_income = bool(row.get("matched_income_id"))

        is_expense_row = amount < 0
        is_income_row = amount > 0

        action_buttons = []

        if is_expense_row and has_matched_cost and not is_done:
            action_buttons.append(
                ft.ElevatedButton(
                    t(page, "bank_review_and_edit"),
                    icon=ft.Icons.EDIT_NOTE_OUTLINED,
                    on_click=lambda e, r=row: open_matched_cost_for_review(r),
                )
            )

        if is_income_row and has_matched_income and not is_done:
            action_buttons.append(
                ft.ElevatedButton(
                    t(page, "bank_review_and_edit"),
                    icon=ft.Icons.EDIT_NOTE_OUTLINED,
                    on_click=lambda e, r=row: open_matched_income_for_review(r),
                )
            )

        if is_expense_row:
            main_button_title = t(page, "bank_create_expense")
        elif is_income_row:
            main_button_title = t(page, "bank_create_income")
        else:
            main_button_title = t(page, "bank_review")

        action_buttons.append(
            ft.ElevatedButton(
                t(page, "bank_status_confirmed") if is_done else main_button_title,
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                disabled=is_done,
                on_click=None if is_done else lambda e, r=row: open_bank_row_for_review(r),
            )
        )

        action_buttons.append(
            ft.TextButton(
                t(page, "bank_ignore"),
                disabled=is_done,
                on_click=None if is_done else lambda e, r=row: ignore_bank_row(r),
            )
        )

        return ft.Container(
            bgcolor=CARD,
            border_radius=16,
            padding=10,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Container(
                                expand=True,
                                content=ft.Text(
                                    row.get("bank_description") or t(page, "bank_transaction_default_title"),
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT,
                                    text_align=ft.TextAlign.LEFT,
                                    max_lines=3,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ),
                            ft.Text(
                                amount_text,
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color="#DC2626" if amount < 0 else "#16A34A",
                            ),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                row.get("bank_date") or "",
                                size=12,
                                color="#64748B",
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                border_radius=999,
                                bgcolor="#F1F5F9",
                                content=ft.Text(
                                    status_label,
                                    size=11,
                                    color=status_color,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=action_buttons,
                    ),
                ],
            ),
        )

    def filter_rows(rows):
        filter_value = selected_filter["value"]

        if filter_value == "all":
            return rows

        if filter_value == "new":
            return [
                r for r in rows
                if (r.get("match_status") or "new") == "new"
            ]

        if filter_value == "confirmed":
            return [
                r for r in rows
                if (r.get("match_status") or "") == "confirmed"
            ]

        if filter_value == "review":
            return [
                r for r in rows
                if (r.get("match_status") or "") in ("matched", "possible_match", "needs_review", "error")
            ]

        return rows

    def apply_current_filter():
        rows_column.controls.clear()

        rows = current_rows["items"] or []
        filtered_rows = filter_rows(rows)

        if not filtered_rows:
            rows_column.controls.append(
                ft.Container(
                    bgcolor=CARD,
                    border_radius=16,
                    padding=20,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        t(page, "bank_empty_filter"),
                        color="#64748B",
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )
        else:
            for row in filtered_rows:
                rows_column.controls.append(build_import_row_card(row))

        safe_update()

    def set_filter(filter_value):
        selected_filter["value"] = filter_value
        update_summary_styles()
        apply_current_filter()

    def load_import_rows(import_id):
        try:
            rows_column.controls.clear()

            rows = get_bank_import_rows(import_id, page=page)
            current_rows["items"] = rows

            update_summary_from_rows(rows)

            if not rows:
                rows_column.controls.clear()
                rows_column.controls.append(
                    ft.Container(
                        height=220,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            t(page, "bank_import_saved_no_rows"),
                            color="#64748B",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    )
                )
                safe_update()
            else:
                apply_current_filter()

            safe_update()

        except Exception as ex:
            print("[BANK RECONCILE] load_import_rows error:", ex, flush=True)
            set_status(f"{t(page, 'bank_load_rows_error')}: {ex}", "#DC2626")

    def ignore_bank_row(row):
        try:
            update_bank_import_row_decision(
                row_id=row.get("id"),
                user_decision="ignore",
                match_status="ignored",
            )

            if selected_import["id"]:
                load_import_rows(selected_import["id"])

        except Exception as ex:
            print("[BANK RECONCILE] ignore row error:", ex, flush=True)
            set_status(f"{t(page, 'bank_ignore_error')}: {ex}", "#DC2626")

    def open_matched_cost_for_review(row):
        matched_cost_id = row.get("matched_cost_id")

        if not matched_cost_id:
            set_status(t(page, "bank_no_matched_cost"), "#DC2626")
            return

        try:
            cost_row = get_my_cost_by_id(matched_cost_id)

            if not cost_row:
                set_status(t(page, "bank_matched_cost_not_found"), "#DC2626")
                return

            open_bank_expense_dialog(row, existing_cost=cost_row)

        except Exception as ex:
            print("[BANK RECONCILE] open matched cost error:", ex, flush=True)
            set_status(f"{t(page, 'bank_open_matched_cost_error')}: {ex}", "#DC2626")

    def open_matched_income_for_review(row):
        matched_income_id = row.get("matched_income_id")

        if not matched_income_id:
            set_status(t(page, "bank_no_matched_income"), "#DC2626")
            return

        try:
            income_row = get_income_transaction_by_id(matched_income_id)

            if not income_row:
                set_status(t(page, "bank_matched_income_not_found"), "#DC2626")
                return

            open_bank_income_dialog(row, existing_income=income_row)

        except Exception as ex:
            print("[BANK RECONCILE] open matched income error:", ex, flush=True)
            set_status(f"{t(page, 'bank_open_matched_income_error')}: {ex}", "#DC2626")

    def open_bank_row_for_review(row):
        amount = float(row.get("amount") or 0)

        if amount < 0:
            open_bank_expense_dialog(row)
            return

        if amount > 0:
            open_bank_income_dialog(row)
            return

        set_status(t(page, "bank_zero_amount_error"), "#DC2626")

    def open_bank_income_dialog(row, existing_income=None):
        bank_row_id = row.get("id")
        is_edit_mode = existing_income is not None

        amount = abs(float(row.get("amount") or 0))

        if is_edit_mode:
            amount = float(existing_income.get("amount") or amount)

        title_field = ft.TextField(
            label=t(page, "bank_income_title"),
            value=(existing_income.get("title") if existing_income else row.get("bank_description")) or "",
            width=320,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )

        amount_field = ft.TextField(
            label=t(page, "bank_amount"),
            value=str(amount),
            width=320,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        date_field = ft.TextField(
            label=t(page, "bank_date"),
            value=normalize_bank_date_for_form(
                existing_income.get("transaction_date") if existing_income else row.get("bank_date")
            ),
            width=320,
            hint_text="YYYY-MM-DD",
        )

        income_type_dropdown = ft.Dropdown(
            label=t(page, "bank_income_type"),
            width=320,
            value=(existing_income.get("income_type") if existing_income else "one_time") or "one_time",
            options=[
                ft.dropdown.Option("one_time", t(page, "bank_income_type_one_time")),
                ft.dropdown.Option("monthly", t(page, "bank_income_type_monthly")),
            ],
        )

        status_dropdown = ft.Dropdown(
            label=t(page, "bank_income_status"),
            width=320,
            value=(existing_income.get("status") if existing_income else "confirmed") or "confirmed",
            options=[
                ft.dropdown.Option("confirmed", t(page, "bank_income_status_confirmed")),
                ft.dropdown.Option("pending", t(page, "bank_income_status_pending")),
                ft.dropdown.Option("missed", t(page, "bank_income_status_missed")),
                ft.dropdown.Option("cancelled", t(page, "bank_income_status_cancelled")),
            ],
        )

        account_dropdown_income = ft.Dropdown(
            label=t(page, "bank_account"),
            width=320,
            options=[],
        )

        note_field = ft.TextField(
            label=t(page, "bank_note"),
            value=(existing_income.get("note") if existing_income else "") or "",
            width=320,
            multiline=True,
            min_lines=2,
            max_lines=3,
        )

        dialog_status = ft.Text("", size=12, color="#DC2626")

        try:
            accounts = get_accounts()

            account_dropdown_income.options = [
                ft.dropdown.Option(
                    key=str(a.get("id")),
                    text=a.get("account_name") or "Account",
                )
                for a in accounts
            ]

            if existing_income:
                account_id = existing_income.get("account_id")
            else:
                account_id = row.get("account_id") or selected_account["id"]

            if account_id:
                account_dropdown_income.value = str(account_id)

        except Exception as ex:
            print("[BANK RECONCILE] load income accounts error:", ex, flush=True)

        def close_dialog(e=None):
            dialog.open = False
            safe_update()

        def save_income(e):
            try:
                title = (title_field.value or "").strip()
                date_text = normalize_bank_date_for_form(date_field.value)
                amount_text = (amount_field.value or "").strip()

                print("[BANK RECONCILE] income date_text repr:", repr(date_text), flush=True)

                if not title:
                    dialog_status.value = t(page, "bank_enter_income_title")
                    safe_update()
                    return

                if not date_text:
                    dialog_status.value = t(page, "bank_enter_date")
                    safe_update()
                    return

                try:
                    tx_date = safe_picker_date(date_text, page).isoformat()
                except Exception as ex:
                    print(
                        "[BANK RECONCILE] income date parse error:",
                        repr(ex),
                        "| value:",
                        repr(date_text),
                        flush=True,
                    )
                    dialog_status.value = t(page, "bank_invalid_date_format")
                    safe_update()
                    return

                try:
                    amount_value = float(amount_text.replace(",", "").strip())
                except Exception:
                    dialog_status.value = t(page, "bank_invalid_amount")
                    safe_update()
                    return

                if amount_value <= 0:
                    dialog_status.value = t(page, "bank_amount_must_be_positive")
                    safe_update()
                    return

                if not account_dropdown_income.value:
                    dialog_status.value = t(page, "bank_select_account")
                    safe_update()
                    return

                if is_edit_mode:
                    update_income_transaction(
                        tx_id=existing_income["id"],
                        title=title,
                        amount=amount_value,
                        transaction_date=tx_date,
                        account_id=account_dropdown_income.value,
                        income_type=income_type_dropdown.value or "one_time",
                        status=status_dropdown.value or "confirmed",
                        note=(note_field.value or "").strip() or None,
                    )

                    update_bank_import_row_decision(
                        row_id=bank_row_id,
                        user_decision="confirm_income_match",
                        match_status="confirmed",
                        matched_income_id=existing_income["id"],
                    )

                else:
                    saved = create_income_transaction(
                        title=title,
                        amount=amount_value,
                        transaction_date=tx_date,
                        account_id=account_dropdown_income.value,
                        income_type=income_type_dropdown.value or "one_time",
                        status=status_dropdown.value or "confirmed",
                        note=(note_field.value or "").strip() or None,
                    )

                    if saved and saved.get("id"):
                        mark_bank_row_as_created_income(bank_row_id, saved["id"])

                dialog.open = False

                if selected_import["id"]:
                    load_import_rows(selected_import["id"])

            except Exception as ex:
                print("[BANK RECONCILE] save income from bank row error:", ex, flush=True)
                dialog_status.value = f"{t(page, 'bank_save_income_error')}: {ex}"
                dialog_status.color = "#DC2626"
                safe_update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                t(page, "bank_income_dialog_title_edit")
                if is_edit_mode
                else t(page, "bank_income_dialog_title_new"),
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        title_field,
                        amount_field,
                        date_field,
                        income_type_dropdown,
                        account_dropdown_income,
                        status_dropdown,
                        note_field,
                        dialog_status,
                    ],
                ),
            ),
            actions=[
                ft.TextButton(t(page, "bank_cancel"), on_click=close_dialog),
                ft.ElevatedButton(
                    t(page, "bank_save_and_confirm")
                    if is_edit_mode
                    else t(page, "bank_save_income"),
                    on_click=save_income,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dialog not in page.overlay:
            page.overlay.append(dialog)

        dialog.open = True
        safe_update()

    def open_category_picker_for_bank_reconcile(current_category_id, on_selected):
        page.data = page.data or {}

        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = current_category_id
        page.data["category_picker_on_selected"] = on_selected
        page.data["from"] = "bank_reconcile_view"
        page.data["without_edit"] = True

        page.app_go("hazinaha_view")

    async def go_to_category_picker_after_cover(current_category_id, on_selected):
        await asyncio.sleep(0.25)

        open_category_picker_for_bank_reconcile(
            current_category_id,
            on_selected,
        )

    bank_reconcile_temp_cover_text = ft.Text(
        t(page, "bank_preparing"),
        size=13,
        color="#64748B",
        text_align=ft.TextAlign.CENTER,
    )

    bank_reconcile_temp_cover = ft.Container(
        visible=False,
        expand=True,
        bgcolor=APP_BG,
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            tight=True,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ProgressRing(width=34, height=34, stroke_width=3),
                bank_reconcile_temp_cover_text,
            ],
        ),
    )

    def show_bank_reconcile_temp_cover(message=None):
        if message is None:
            message = t(page, "bank_preparing")

        bank_reconcile_temp_cover_text.value = message
        bank_reconcile_temp_cover.visible = True
        safe_update()

    def remove_bank_reconcile_temp_cover():
        bank_reconcile_temp_cover.visible = False
        safe_update()

    def open_bank_expense_dialog(row, existing_cost=None):
        bank_row_id = row.get("id")
        is_edit_mode = existing_cost is not None

        amount = abs(float(row.get("amount") or 0))

        if is_edit_mode:
            amount = float(existing_cost.get("price") or amount)

        title_field = ft.TextField(
            label=t(page, "bank_expense_title"),
            value=(existing_cost.get("title") if existing_cost else row.get("bank_description")) or "",
            width=320,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )

        amount_field = ft.TextField(
            label=t(page, "bank_amount"),
            value=str(amount),
            width=320,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        date_field = ft.TextField(
            label=t(page, "bank_date"),
            value=normalize_bank_date_for_form(
                existing_cost.get("date_cost") if existing_cost else row.get("bank_date")
            ),
            width=320,
            hint_text="YYYY-MM-DD",
        )

        selected_category = {
            "id": None,
            "title": "",
        }

        category_field = ft.TextField(
            label=t(page, "bank_category"),
            width=260,
            read_only=True,
            value="",
        )

        category_button = ft.IconButton(
            icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
            icon_color=PRIMARY,
            tooltip=t(page, "bank_select_category_tooltip"),
        )

        member_dropdown = ft.Dropdown(
            label=t(page, "bank_member"),
            width=320,
            options=[
                ft.dropdown.Option(key="", text=t(page, "bank_no_member"))
            ],
            value="",
        )

        account_dropdown_dialog = ft.Dropdown(
            label=t(page, "bank_account"),
            width=320,
            options=[],
        )

        dialog_status = ft.Text("", size=12, color="#DC2626")

        try:
            categories = load_leaf_hazineha()

            selected_category_id = None

            if existing_cost:
                selected_category_id = existing_cost.get("id_hazine")
            else:
                selected_category_id = row.get("suggested_category_id")

            if selected_category_id:
                selected_category["id"] = selected_category_id

                found_category = next(
                    (
                        c for c in categories
                        if str(c.get("id")) == str(selected_category_id)
                    ),
                    None,
                )

                if found_category:
                    selected_category["title"] = found_category.get("title") or ""
                elif existing_cost:
                    selected_category["title"] = existing_cost.get("category_title") or ""
                else:
                    selected_category["title"] = row.get("suggested_category_title") or ""

                category_field.value = selected_category["title"]

        except Exception as ex:
            print("[BANK RECONCILE] load categories error:", ex, flush=True)

        picked_category = None

        if isinstance(page.data, dict):
            picked_category = page.data.pop("bank_reconcile_selected_category", None)

        if picked_category:
            selected_category["id"] = picked_category.get("id")
            selected_category["title"] = picked_category.get("title") or ""
            category_field.value = selected_category["title"]

        draft = None

        if isinstance(page.data, dict):
            draft = page.data.pop("bank_reconcile_expense_draft", None)

        if draft:
            title_field.value = draft.get("title") or title_field.value
            amount_field.value = draft.get("amount") or amount_field.value
            date_field.value = draft.get("date") or date_field.value

            if draft.get("member_id") is not None:
                member_dropdown.value = draft.get("member_id")

            if draft.get("account_id") is not None:
                account_dropdown_dialog.value = draft.get("account_id")

        try:
            members = get_members(page)

            member_dropdown.options = [
                ft.dropdown.Option(key="", text=t(page, "bank_no_member"))
            ] + [
                ft.dropdown.Option(
                    key=str(m.get("id")),
                    text=m.get("full_name") or "Member",
                )
                for m in members
            ]

            selected_member_id = None

            if existing_cost:
                selected_member_id = existing_cost.get("member_id")
            else:
                selected_member_id = row.get("suggested_member_id")

            if selected_member_id:
                member_dropdown.value = str(selected_member_id)

        except Exception as ex:
            print("[BANK RECONCILE] load members error:", ex, flush=True)

        try:
            accounts = get_accounts()

            account_dropdown_dialog.options = [
                ft.dropdown.Option(
                    key=str(a.get("id")),
                    text=a.get("account_name") or "Account",
                )
                for a in accounts
            ]

            row_account_id = None

            if existing_cost:
                row_account_id = existing_cost.get("account_id")
            else:
                row_account_id = row.get("account_id") or selected_account["id"]

            if row_account_id:
                account_dropdown_dialog.value = str(row_account_id)

        except Exception as ex:
            print("[BANK RECONCILE] load accounts dialog error:", ex, flush=True)

        def close_dialog(e=None):
            dialog.open = False
            safe_update()

        def select_category(e=None):
            page.data = page.data or {}

            page.data["bank_reconcile_edit_row"] = row
            page.data["bank_reconcile_existing_cost"] = existing_cost
            page.data["bank_reconcile_selected_import_id"] = selected_import["id"]
            page.data["reopen_bank_reconcile_dialog"] = True

            page.data["bank_reconcile_selected_filter"] = selected_filter["value"]
            page.data["bank_reconcile_selected_account_id"] = selected_account["id"]

            page.data["bank_reconcile_expense_draft"] = {
                "title": title_field.value,
                "amount": amount_field.value,
                "date": date_field.value,
                "member_id": member_dropdown.value,
                "account_id": account_dropdown_dialog.value,
            }

            def on_selected(category):
                if not category:
                    return

                page.data["bank_reconcile_selected_category"] = {
                    "id": category.get("category_id"),
                    "title": category.get("category_title") or "",
                }

            try:
                dialog.open = False
            except Exception:
                pass

            safe_update()

            show_bank_reconcile_temp_cover(t(page, "bank_loading_categories"))

            page.run_task(
                go_to_category_picker_after_cover,
                selected_category["id"],
                on_selected,
            )

        category_button.on_click = select_category

        def save_expense(e):
            try:
                title = (title_field.value or "").strip()
                date_cost_text = normalize_bank_date_for_form(date_field.value)
                amount_text = (amount_field.value or "").strip()

                if not title:
                    dialog_status.value = t(page, "bank_enter_expense_title")
                    safe_update()
                    return

                if not date_cost_text:
                    dialog_status.value = t(page, "bank_enter_date")
                    safe_update()
                    return

                try:
                    date_cost = safe_picker_date(date_cost_text, page).isoformat()
                except Exception as ex:
                    print(
                        "[BANK RECONCILE] expense date parse error:",
                        repr(ex),
                        "| value:",
                        repr(date_cost_text),
                        flush=True,
                    )
                    dialog_status.value = t(page, "bank_invalid_date_format")
                    safe_update()
                    return

                if not amount_text:
                    dialog_status.value = t(page, "bank_enter_amount")
                    safe_update()
                    return

                try:
                    price = float(amount_text.replace(",", ""))
                except Exception:
                    dialog_status.value = t(page, "bank_invalid_amount")
                    safe_update()
                    return

                if price <= 0:
                    dialog_status.value = t(page, "bank_amount_must_be_positive")
                    safe_update()
                    return

                if not selected_category["id"]:
                    dialog_status.value = t(page, "bank_select_category")
                    safe_update()
                    return

                if not account_dropdown_dialog.value:
                    dialog_status.value = t(page, "bank_select_account")
                    safe_update()
                    return

                member_id = None

                if member_dropdown.value:
                    member_id = int(member_dropdown.value)

                payload = {
                    "title": title,
                    "price": price,
                    "date_cost": date_cost,
                    "id_hazine": selected_category["id"],
                    "member_id": member_id,
                    "account_id": account_dropdown_dialog.value,
                    "temp_hazine": None,
                }

                if is_edit_mode:
                    saved = update_my_cost(
                        cost_id=existing_cost["id"],
                        title=payload["title"],
                        price=payload["price"],
                        date_cost=payload["date_cost"],
                        id_hazine=payload["id_hazine"],
                        member_id=payload["member_id"],
                        account_id=payload["account_id"],
                    )

                    if saved and saved.get("id"):
                        update_bank_import_row_decision(
                            row_id=bank_row_id,
                            user_decision="confirm_match",
                            match_status="confirmed",
                            matched_cost_id=saved["id"],
                        )

                else:
                    saved = insert_cost_for_current_user(payload)

                    if saved and saved.get("id"):
                        mark_bank_row_as_created_cost(bank_row_id, saved["id"])

                dialog.open = False

                if selected_import["id"]:
                    load_import_rows(selected_import["id"])

            except Exception as ex:
                print("[BANK RECONCILE] save expense from bank row error:", ex, flush=True)
                dialog_status.value = f"{t(page, 'bank_save_expense_error')}: {ex}"
                dialog_status.color = "#DC2626"
                safe_update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                t(page, "bank_expense_dialog_title_edit")
                if is_edit_mode
                else t(page, "bank_expense_dialog_title_new"),
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        title_field,
                        amount_field,
                        date_field,
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(
                                    expand=True,
                                    content=category_field,
                                ),
                                ft.Container(
                                    width=58,
                                    height=58,
                                    border_radius=14,
                                    bgcolor="#EFF6FF",
                                    alignment=ft.Alignment.CENTER,
                                    content=category_button,
                                ),
                            ],
                        ),
                        member_dropdown,
                        account_dropdown_dialog,
                        dialog_status,
                    ],
                ),
            ),
            actions=[
                ft.TextButton(t(page, "bank_cancel"), on_click=close_dialog),
                ft.ElevatedButton(
                    t(page, "bank_save_and_confirm")
                    if is_edit_mode
                    else t(page, "bank_create_expense"),
                    on_click=save_expense,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dialog not in page.overlay:
            page.overlay.append(dialog)

        dialog.open = True
        safe_update()

    def open_previous_imports_dialog(e=None):
        try:
            imports = get_bank_imports(page=page)
        except Exception as ex:
            print("[BANK RECONCILE] get previous imports error:", ex, flush=True)
            set_status(f"{t(page, 'bank_load_previous_imports_error')}: {ex}", "#DC2626")
            return

        previous_list = ft.ListView(
            height=360,
            spacing=8,
            padding=0,
            auto_scroll=False,
        )

        def close_dialog(e=None):
            dialog.open = False
            safe_update()

        def select_import(item):
            selected_filter["value"] = "all"
            selected_import["id"] = item.get("id")

            selected_file["path"] = None
            selected_file["name"] = None

            dialog.open = False

            file_name = item.get("file_name") or t(page, "bank_previous_files")
            status_text.value = f"{t(page, 'bank_previous_file_selected')}: {file_name}"
            status_text.color = "#16A34A"

            load_import_rows(item.get("id"))

            safe_update()

        if not imports:
            previous_list.controls.append(
                ft.Container(
                    height=160,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        t(page, "bank_no_previous_imports"),
                        color="#64748B",
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )
        else:
            for item in imports:
                file_name = item.get("file_name") or t(page, "bank_untitled_file")
                account_name = item.get("account_name") or ""
                created_at = (item.get("created_at") or "")[:19].replace("T", " ")

                total_rows = item.get("total_rows") or 0
                new_count = item.get("new_count") or 0
                matched_count = item.get("matched_count") or 0
                review_count = item.get("review_count") or 0

                previous_list.controls.append(
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border_radius=14,
                        padding=10,
                        on_click=lambda e, x=item: select_import(x),
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text(
                                    file_name,
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    f"{account_name}  •  {created_at}",
                                    size=11,
                                    color="#64748B",
                                ),
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            f"{t(page, 'bank_total')}: {total_rows}",
                                            size=11,
                                            color="#64748B",
                                        ),
                                        ft.Text(
                                            f"{t(page, 'bank_summary_new')}: {new_count}",
                                            size=11,
                                            color="#2563EB",
                                        ),
                                        ft.Text(
                                            f"{t(page, 'bank_confirmed_short')}: {matched_count}",
                                            size=11,
                                            color="#16A34A",
                                        ),
                                        ft.Text(
                                            f"{t(page, 'bank_summary_review')}: {review_count}",
                                            size=11,
                                            color="#EA580C",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                t(page, "bank_previous_imports_title"),
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
            ),
            content=ft.Container(
                width=380,
                content=previous_list,
            ),
            actions=[
                ft.TextButton(t(page, "bank_close"), on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if dialog not in page.overlay:
            page.overlay.append(dialog)

        dialog.open = True
        safe_update()

    async def process_selected_file_async():
        if not selected_account["id"]:
            set_status(t(page, "bank_select_account_first"), "#DC2626")
            return

        file_path = (selected_file.get("path") or "").strip()

        if not file_path:
            set_status(t(page, "bank_select_new_file_first"), "#DC2626")
            return

        if not os.path.exists(file_path):
            print("[BANK RECONCILE] file path does not exist:", file_path, flush=True)

            set_status(t(page, "bank_file_not_readable"), "#DC2626")
            show_empty_message(t(page, "bank_file_not_readable_detail"), "#DC2626")
            return

        file_name = selected_file.get("name") or os.path.basename(file_path)
        file_ext = get_file_ext(file_name)

        allowed_exts = ["csv", "qbo", "qfx", "ofx"]

        if file_ext not in allowed_exts:
            set_status(t(page, "bank_invalid_file_format"), "#DC2626")
            return

        try:
            set_status(t(page, "bank_creating_import"), "#64748B")
            show_loading_state(t(page, "bank_creating_import"))
            await asyncio.sleep(0.1)

            item = create_bank_import(
                account_id=selected_account["id"],
                file_name=file_name,
                file_type=file_ext,
                detected_format=file_ext,
            )

            selected_import["id"] = item["id"]

            update_bank_import_status(item["id"], "processing")

            set_status(t(page, "bank_reading_file"), "#64748B")
            show_loading_state(t(page, "bank_reading_file"))
            await asyncio.sleep(0.1)

            parsed = parse_bank_file(file_path)

            if not parsed.get("ok"):
                update_bank_import_status(
                    item["id"],
                    "failed",
                    error_message=parsed.get("error"),
                )

                msg = f"{t(page, 'bank_import_failed_prefix')}: {parsed.get('error')}"
                set_status(msg, "#DC2626")
                show_empty_message(msg, "#DC2626")
                return

            parsed_rows = parsed.get("rows") or []

            if not parsed_rows:
                update_bank_import_status(
                    item["id"],
                    "failed",
                    error_message="No rows extracted",
                )

                msg = t(page, "bank_no_rows_extracted")
                set_status(msg, "#DC2626")
                show_empty_message(msg, "#DC2626")
                return

            set_status(t(page, "bank_matching_transactions"), "#64748B")
            show_loading_state(t(page, "bank_matching_transactions"))
            await asyncio.sleep(0.1)

            prepared_rows = prepare_bank_import_rows_for_save(
                account_id=selected_account["id"],
                parsed_rows=parsed_rows,
                page=page,
            )

            add_bank_import_rows(
                import_id=item["id"],
                account_id=selected_account["id"],
                rows=prepared_rows,
            )

            update_bank_import_status(item["id"], "ready")

            warning_text = ""
            warnings = parsed.get("warnings") or []

            if warnings:
                warning_text = " / " + " ".join(warnings[:2])

            status_text.value = f"{len(prepared_rows)} {t(page, 'bank_rows_extracted')}{warning_text}"
            status_text.color = "#16A34A"

            load_import_rows(item["id"])

        except Exception as ex:
            print("[BANK RECONCILE] import/parse error:", ex, flush=True)

            if selected_import["id"]:
                try:
                    update_bank_import_status(
                        selected_import["id"],
                        "failed",
                        error_message=str(ex),
                    )
                except Exception:
                    pass

            msg = f"{t(page, 'bank_process_file_error')}: {ex}"
            set_status(msg, "#DC2626")
            show_empty_message(msg, "#DC2626")

    top_bar = ft.Container(
        bgcolor=CARD,
        padding=ft.padding.only(left=12, right=12, top=12, bottom=12),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.app_go("sabtehazine"),
                ),
                ft.Text(
                    t(page, "bank_title"),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(width=40),
            ],
        ),
    )

    form_card = ft.Container(
        bgcolor=CARD,
        border_radius=18,
        padding=14,
        margin=ft.margin.only(left=12, right=12, top=12),
        content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                account_dropdown,
                ft.Text(
                    t(page, "bank_allowed_formats"),
                    size=12,
                    color="#64748B",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.ElevatedButton(
                            t(page, "bank_previous_files"),
                            icon=ft.Icons.FOLDER_COPY_OUTLINED,
                            on_click=open_previous_imports_dialog,
                        ),
                        ft.ElevatedButton(
                            t(page, "bank_new_file"),
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=choose_file_path,
                        ),
                    ],
                ),
                status_text,
            ],
        ),
    )

    summary_card = ft.Container(
        bgcolor=CARD,
        border_radius=18,
        padding=14,
        margin=ft.margin.only(left=12, right=12, top=10),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                summary_all,
                summary_new,
                summary_confirmed,
                summary_review,
            ],
        ),
    )

    async def reopen_bank_expense_dialog_after_mount(row, existing_cost=None):
        await asyncio.sleep(0.25)

        try:
            open_bank_expense_dialog(row, existing_cost=existing_cost)
            await asyncio.sleep(0.05)
            remove_bank_reconcile_temp_cover()

        except Exception as ex:
            print("[BANK RECONCILE] reopen expense dialog error:", ex, flush=True)
            remove_bank_reconcile_temp_cover()

    async def load_after_mount():
        await asyncio.sleep(0.1)

        load_accounts()

        page.data = page.data or {}

        saved_account_id = page.data.get("bank_reconcile_selected_account_id")
        saved_import_id = page.data.get("bank_reconcile_selected_import_id")
        saved_filter = page.data.get("bank_reconcile_selected_filter")

        if saved_account_id:
            selected_account["id"] = saved_account_id
            account_dropdown.value = str(saved_account_id)

        if saved_filter:
            selected_filter["value"] = saved_filter
            update_summary_styles()

        if saved_import_id:
            selected_import["id"] = saved_import_id
            load_import_rows(saved_import_id)

        safe_update()

    page.run_task(load_after_mount)

    page_list.controls.extend(
        [
            top_bar,
            form_card,
            summary_card,
            ft.Container(
                padding=ft.padding.only(left=12, right=12, top=10, bottom=24),
                content=rows_column,
            ),
        ]
    )

    page.data = page.data or {}

    if page.data.get("reopen_bank_reconcile_dialog"):
        page.data["reopen_bank_reconcile_dialog"] = False

        reopen_row = page.data.get("bank_reconcile_edit_row")
        reopen_existing_cost = page.data.get("bank_reconcile_existing_cost")

        if page.data.get("bank_reconcile_selected_import_id"):
            selected_import["id"] = page.data.get("bank_reconcile_selected_import_id")

        if reopen_row:
            show_bank_reconcile_temp_cover(t(page, "bank_opening_edit_form"))

            page.run_task(
                reopen_bank_expense_dialog_after_mount,
                reopen_row,
                reopen_existing_cost,
            )

    return ft.View(
        route="/bank_reconcile_view",
        bgcolor=APP_BG,
        padding=0,
        spacing=0,
        services=[
            file_picker,
        ],
        controls=[
            ft.Stack(
                expand=True,
                controls=[
                    page_list,
                    bank_reconcile_temp_cover,
                ],
            )
        ],
    )