import flet as ft
from datetime import date, datetime
# from ui.category_picker_dialog import open_category_picker_dialog
from services.supabase_service import get_members, add_member, get_accounts, find_account_by_id
from ui.member_manager_shared import open_member_picker_dialog
from services.i18n import t
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()


def open_edit_cost_dialog(
    page: ft.Page,
    row: dict,
    on_save,
):
    PRIMARY = "#2563EB"
    PRIMARY_SOFT = "#EFF6FF"
    TEXT_MAIN = "#0F172A"
    TEXT_MUTED = "#64748B"
    BORDER = "#E2E8F0"
    BORDER_FOCUS = "#93C5FD"
    DANGER = "#DC2626"
    BG_APP = "#F8FAFC"
    CARD_BG = "#FFFFFF"
    CHIP_BG = "#F1F5F9"
    SUCCESS_TEXT = "#16A34A"

    FIELD_HEIGHT = 54
    RADIUS = 16
    

    original_category_id = row.get("id_hazine")

    selected_member = {
        "member_id": row.get("member_id"),
        "member_name": row.get("member_name", "") or "",
    }


    acc = find_account_by_id(row.get("account_id"))

    selected_account = {
        "account_id": row.get("account_id"),
        "account_name": acc.get("account_name", "") if acc else "",
    }

    def clear_account(e=None):
        selected_account["account_id"] = None
        selected_account["account_name"] = ""
        update_account_ui()


    account_field = ft.TextField(
        label="حساب",
        value=selected_account["account_name"] or "انتخاب حساب",
        read_only=True,
        expand=True,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),

        suffix_icon=ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=16,
            tooltip="حذف حساب",
            on_click=clear_account,
            visible=bool(selected_account["account_id"])
        ),
    )

    def update_account_ui():
        account_field.value = selected_account["account_name"] or "انتخاب حساب"
        account_field.suffix_icon.visible = bool(selected_account["account_id"])
        safe_update()

    def choose_account(e=None):
        accounts = get_accounts() or []

        dlg = ft.AlertDialog(modal=True)

        def close_dlg(ev=None):
            dlg.open = False
            safe_update()

        def select_account(acc):
            selected_account["account_id"] = acc.get("id")
            selected_account["account_name"] = acc.get("account_name", "")
            dlg.open = False
            update_account_ui()

        if not accounts:
            content = ft.Text("هیچ حسابی ثبت نشده است.")
        else:
            content = ft.Column(
                [
                    ft.ListTile(
                        title=ft.Text(acc.get("account_name", "")),
                        subtitle=ft.Text(acc.get("account_type", "")),
                        leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
                        on_click=lambda e, acc=acc: select_account(acc),
                    )
                    for acc in accounts
                ],
                tight=True,
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
                height=300,
            )

        dlg.title = ft.Text("انتخاب حساب")
        dlg.content = content
        dlg.actions = [
            ft.TextButton("بستن", on_click=close_dlg),
        ]

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        safe_update()
        

    def clear_member(e=None):
        selected_member["member_id"] = None
        selected_member["member_name"] = ""
        update_member_ui()

    member_field = ft.TextField(
        label=t(page, "edit_cost_member"),
        value=selected_member["member_name"] or "انتخاب عضو",
        read_only=True,
        expand=True,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),

        # 🔥 این خط مهمه
        suffix_icon=ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=16,
            tooltip="حذف عضو",
            on_click=clear_member,
            visible=bool(selected_member["member_id"])  # فقط وقتی عضو داره
        ),
    )


    def update_member_ui():
        member_field.value = selected_member["member_name"] or "انتخاب عضو"

        # 🔥 کنترل نمایش دکمه حذف
        member_field.suffix_icon.visible = bool(selected_member["member_id"])

        safe_update()

    def choose_member(e=None):
        def on_member_selected(member):
            selected_member["member_id"] = member.get("id")
            selected_member["member_name"] = member.get("full_name", "") or ""
            update_member_ui()

        open_member_picker_dialog(
            page=page,
            selected_member=selected_member,
            on_member_selected=on_member_selected,
        )
 
    def open_add_member_dialog(e=None):
        member_name = ft.TextField(label="نام عضو", autofocus=True)
        member_relation = ft.TextField(label="نسبت")

        dlg = ft.AlertDialog(modal=True)

        def close_dlg(ev=None):
            dlg.open = False
            page.update()

        def save_member(ev):
            if not member_name.value.strip():
                member_name.error_text = "نام عضو را وارد کن"
                page.update()
                return

            new_member = add_member(member_name.value, member_relation.value)

            all_members = get_members(page)
            member_dropdown.options = [
                ft.dropdown.Option(str(m["id"]), m["full_name"])
                for m in all_members
            ]

            if new_member:
                member_dropdown.value = str(new_member["id"])

            dlg.open = False
            page.update()

        dlg.title = ft.Text("افزودن عضو جدید")
        dlg.content = ft.Column(
            [member_name, member_relation],
            tight=True,
            spacing=10,
        )
        dlg.actions = [
            ft.TextButton(t(page, "edit_cost_regect"), on_click=close_dlg),
            ft.ElevatedButton(t(page, "edit_cost_save"), on_click=save_member),
        ]

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        page.update()
        
    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    def parse_date_safe(value):
        try:
            if isinstance(value, date):
                return value
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, str) and value.strip():
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except Exception:
            pass
        return today_local()

    def format_currency_label(currency_id):
        currency_map = {
            1: "ریال",
            2: "تومان",
            3: "دلار",
        }
        return currency_map.get(currency_id, "نامشخص")

    current_date = parse_date_safe(row.get("date_cost"))
    selected_category = {
        "category_id": row.get("id_hazine"),
        "category_title": row.get("category_title", "") or "",
    }

    title_value = row.get("title", "")
    price_value = row.get("price", "")
    currency_label = format_currency_label(row.get("currency_id"))

    date_picker = ft.DatePicker(value=current_date)
    if date_picker not in page.overlay:
        page.overlay.append(date_picker)

    title_field = ft.TextField(
        label=t(page, "edit_cost_title"),
        value=str(title_value),
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )

    price_field = ft.TextField(
        label=t(page, "edit_cost_price"),
        value=str(price_value) if price_value is not None else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )

    date_field = ft.TextField(
        label=t(page, "edit_cost_date"),
        value=current_date.isoformat(),
        read_only=True,
        expand=True,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )

    category_field = ft.TextField(
        label=t(page, "edit_cost_hazine"),
        value=selected_category["category_title"] or "انتخاب کتگوری",
        read_only=True,
        expand=True,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )

    error_text = ft.Text(
        "",
        size=11,
        color=DANGER,
        visible=False,
    )

    def update_category_ui():
        category_field.value = selected_category["category_title"] or "انتخاب کتگوری"
        safe_update()

    def open_date_picker(e=None):
        date_picker.value = parse_date_safe(date_field.value)
        date_picker.open = True
        safe_update()

    def on_date_change(e):
        if not date_picker.value:
            return
        picked = date_picker.value
        if isinstance(picked, datetime):
            picked = picked.date()
        date_field.value = picked.isoformat()
        safe_update()

    date_picker.on_change = on_date_change


    def on_category_selected(result: dict):
        selected_category["category_id"] = result.get("category_id")
        selected_category["category_title"] = result.get("category_title") or ""

        row["id_hazine"] = selected_category["category_id"]
        row["category_title"] = selected_category["category_title"]
        row["old_category_id"] = original_category_id

        page.data["edit_cost_row"] = row

        update_category_ui()
        

    def choose_category(e=None):
        page.data = page.data or {}

        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = selected_category["category_id"]
        page.data["category_picker_on_selected"] = on_category_selected

        page.data["from"] = "edit_cost_dialog"
        page.data["reopen_edit_cost_dialog"] = True

        row["old_category_id"] = original_category_id
        page.data["edit_cost_row"] = row

        dialog.open = False
        page.update()

        page.app_go("hazinaha_view")       
    
    
    def close_dialog(e=None):
        dialog.open = False
        safe_update()

    def validate_price(value: str):
        raw = (value or "").strip()

        if not raw:
            return None, "مبلغ را وارد کن."

        raw = raw.replace(",", ".")

        try:
            amount = float(raw)
        except:
            return None, "مبلغ نامعتبر است."

        if amount < 0:
            return None, "مبلغ نمی‌تواند منفی باشد."

        if amount.is_integer():
            amount = int(amount)

        return amount, None

    def save_changes(e=None):
        error_text.visible = False
        error_text.value = ""

        title_clean = (title_field.value or "").strip()
        if not title_clean:
            error_text.value = "عنوان را وارد کن."
            error_text.visible = True
            safe_update()
            return

        amount, price_error = validate_price(price_field.value)
        if price_error:
            error_text.value = price_error
            error_text.visible = True
            safe_update()
            return

        if not selected_category["category_id"]:
            error_text.value = "لطفاً کتگوری را انتخاب کن."
            error_text.visible = True
            safe_update()
            return

        payload = {
            "id": row.get("id"),
            "title": title_clean,
            "price": amount,
            "date_cost": date_field.value,
            "id_hazine": selected_category["category_id"],
            "category_title": selected_category["category_title"],
            "currency_id": row.get("currency_id"),
            "member_id": selected_member["member_id"],
            "account_id": selected_account["account_id"],
            "old_category_id": original_category_id,
        }

        try:
            on_save(payload)
            dialog.open = False
            safe_update()
        except Exception as ex:
            print(f"خطا در ذخیره‌سازی: {ex}")
            error_text.value = f"خطا در ذخیره‌سازی: {ex}"
            error_text.visible = True
            safe_update()

    def action_picker_button(icon, on_click, tooltip):
        return ft.Container(
            width=54,
            height=54,
            border_radius=14,
            bgcolor=PRIMARY_SOFT,
            border=ft.border.all(1, "#DBEAFE"),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=on_click,
            tooltip=tooltip,
            content=ft.Icon(icon, size=18, color=PRIMARY),
        )


    currency_field = ft.TextField(
        label=t(page, "edit_cost_curency"),
        value=currency_label,
        read_only=True,
        expand=True,
        border_radius=RADIUS,
        filled=True,
        bgcolor=CARD_BG,
        border_color=BORDER,
        focused_border_color=BORDER_FOCUS,
        text_size=14,
        height=FIELD_HEIGHT,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )

    form_card = ft.Container(
        bgcolor=BG_APP,
        border_radius=22,
        padding=16,
        content=ft.Column(
            [
                title_field,

                ft.Row(
                    [
                        ft.Container(expand=True, content=date_field),
                        action_picker_button(
                            ft.Icons.CALENDAR_MONTH_OUTLINED,
                            open_date_picker,
                            "انتخاب تاریخ",
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Row(
                    [
                        ft.Container(
                            expand=True,
                            content=account_field,
                            on_click=choose_account
                        ),
                        action_picker_button(
                            ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                            choose_account,
                            "انتخاب حساب",
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Container(expand=True, content=category_field, on_click=choose_category),
                        action_picker_button(
                            ft.Icons.ACCOUNT_TREE_OUTLINED,
                            choose_category,
                            "انتخاب کتگوری",
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),

                ft.Row(
                    [
                        ft.Container(
                            expand=True,
                            content=member_field,
                            on_click=choose_member
                        ),
                        action_picker_button(
                            ft.Icons.PERSON_OUTLINE,
                            choose_member,
                            "",
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            
                price_field,

                # currency_field,

                error_text,
            ],
            spacing=12,
            tight=True,
        ),
    )


    header_block = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        width=42,
                        height=42,
                        border_radius=14,
                        bgcolor=PRIMARY_SOFT,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=PRIMARY, size=22),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                t(page, "edit_cost_formtitle"),
                                size=18,
                                weight=ft.FontWeight.W_700,
                                color=TEXT_MAIN,
                            ),
                            
                        ],
                        spacing=2,
                        tight=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Divider(height=8, color="transparent"),
        ],
        spacing=0,
        tight=True,
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor="#FFFFFF",
        inset_padding=20,
        shape=ft.RoundedRectangleBorder(radius=24),
        title=header_block,
        content=ft.Container(
            width=460,
            padding=ft.padding.only(top=4),
            content=ft.Column(
                [
                    form_card,
                ],
                spacing=0,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.OutlinedButton(
                t(page, "edit_cost_regect"),
                on_click=close_dialog,
                style=ft.ButtonStyle(
                    color=TEXT_MUTED,
                    side=ft.BorderSide(1, BORDER),
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                ),
            ),
            ft.ElevatedButton(
                t(page, "edit_cost_save"),
                icon=ft.Icons.SAVE_OUTLINED,
                on_click=save_changes,
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    elevation=0,
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.padding.symmetric(horizontal=18, vertical=14),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    if dialog not in page.overlay:
        page.overlay.append(dialog)

    dialog.open = True
    safe_update()