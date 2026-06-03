import flet as ft
import asyncio

from services.supabase_service import get_members, add_member, get_accounts, find_account_by_id
from ui.member_manager_shared import open_member_picker_dialog
from services.i18n import t
from services.utils import today_local, safe_picker_date, local_date_iso


def open_edit_cost_dialog(
    page: ft.Page,
    row: dict,
    on_save,
):
    page.data = page.data or {}
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
        label=t(page, "edit_cost_account"),
        value=selected_account["account_name"] or t(page, "edit_cost_select_account"),
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
            # tooltip="حذف حساب",
            on_click=clear_account,
            visible=bool(selected_account["account_id"])
        ),
    )

    def update_account_ui():
        account_field.value = selected_account["account_name"] or t(page, "edit_cost_select_account")
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
            content = ft.Text(t(page, "edit_cost_message_no_account"))
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

        dlg.title = ft.Text(t(page, "edit_cost_select_account"))
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
        value=selected_member["member_name"] or t(page, "edit_cost_member"),
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
            # tooltip="حذف عضو",
            on_click=clear_member,
            visible=bool(selected_member["member_id"])  # فقط وقتی عضو داره
        ),
    )


    def update_member_ui():
        member_field.value = selected_member["member_name"] or t(page, "edit_cost_member")

        # 🔥 کنترل نمایش دکمه حذف
        member_field.suffix_icon.visible = bool(selected_member["member_id"])

        safe_update()

    def choose_member(e=None):
        remove_category_loading_cover()

        members = get_members(page) or []
        search_state = {"q": ""}

        member_picker_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t(page, "edit_cost_select_member"), size=16, weight=ft.FontWeight.W_700),
        )

        member_list = ft.ListView(
            spacing=8,
            expand=True,
            padding=0,
            auto_scroll=False,
        )

        search_field = ft.TextField(
            hint_text=t(page, "edit_cost_search_member"),
            prefix_icon=ft.Icons.SEARCH,
            text_size=13,
            height=46,
            border_radius=12,
            filled=True,
            bgcolor="#F8FAFC",
            border_color="#E2E8F0",
            focused_border_color="#93C5FD",
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        def close_picker(ev=None):
            member_picker_dialog.open = False
            safe_update()

        def clear_selected_member(ev=None):
            selected_member["member_id"] = None
            selected_member["member_name"] = ""
            member_picker_dialog.open = False
            update_member_ui()

        def select_member(member):
            selected_member["member_id"] = member.get("id")
            selected_member["member_name"] = member.get("full_name", "") or ""
            member_picker_dialog.open = False
            update_member_ui()

        def build_member_list():
            member_list.controls.clear()

            q = (search_state["q"] or "").strip().lower()

            member_list.controls.append(
                ft.Container(
                    bgcolor="#F8FAFC",
                    border=ft.border.all(1, "#E2E8F0"),
                    border_radius=12,
                    padding=10,
                    on_click=clear_selected_member,
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.GROUP_OUTLINED, size=18, color=PRIMARY),
                            ft.Text(
                                t(page, "edit_cost_no_member"),
                                size=13,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

            filtered_members = []

            for m in members:
                name = m.get("full_name") or ""
                relation = m.get("relation") or ""

                search_text = f"{name} {relation}".lower()

                if q and q not in search_text:
                    continue

                filtered_members.append(m)

            if not filtered_members:
                member_list.controls.append(
                    ft.Container(
                        height=120,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            t(page, "edit_cost_member_not_found"),
                            size=13,
                            color="#64748B",
                        ),
                    )
                )
                return

            for m in filtered_members:
                name = m.get("full_name") or ""
                relation = m.get("relation") or ""

                member_list.controls.append(
                    ft.Container(
                        bgcolor="#FFFFFF",
                        border=ft.border.all(1, "#E2E8F0"),
                        border_radius=12,
                        padding=10,
                        on_click=lambda e, member=m: select_member(member),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.PERSON_OUTLINE, size=18, color="#64748B"),
                                ft.Column(
                                    [
                                        ft.Text(
                                            name or "",
                                            size=13,
                                            weight=ft.FontWeight.W_600,
                                            color="#0F172A",
                                        ),
                                        ft.Text(
                                            relation or "",
                                            size=11,
                                            color="#64748B",
                                            visible=bool(relation),
                                        ),
                                    ],
                                    spacing=2,
                                    tight=True,
                                    expand=True,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )

        def on_search_change(e):
            search_state["q"] = e.control.value or ""
            build_member_list()
            safe_update()

        search_field.on_change = on_search_change

        build_member_list()

        member_picker_dialog.content = ft.Container(
            width=360,
            height=470,
            content=ft.Column(
                [
                    search_field,
                    member_list,
                ],
                spacing=10,
                expand=True,
            ),
        )

        member_picker_dialog.actions = [
            ft.TextButton(t(page, "Close"), on_click=close_picker),
        ]

        if member_picker_dialog not in page.overlay:
            page.overlay.append(member_picker_dialog)

        member_picker_dialog.open = True
        safe_update()


    def open_add_member_dialog(e=None):
        member_name = ft.TextField(label=t(page, "edit_cost_member"), autofocus=True)
        member_relation = ft.TextField(label=t(page, "Member_LableRelation"))

        dlg = ft.AlertDialog(modal=True)

        def close_dlg(ev=None):
            dlg.open = False
            page.update()

        def save_member(ev):
            if not member_name.value.strip():
                member_name.error_text = t(page, "Member_Message_Enter_Name")
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

        dlg.title = ft.Text(t(page, "Member_Insert"))
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

    def remove_category_loading_cover():
        try:
            for ctrl in list(page.overlay):
                if getattr(ctrl, "key", None) == "category_nav_cover":
                    page.overlay.remove(ctrl)
        except Exception as ex:
            print("REMOVE_CATEGORY_NAV_COVER_ERROR:", ex)

    def parse_date_safe(value):
        try:
            return safe_picker_date(value, page)
        except Exception:
            return today_local(page)    

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

        # ✅ متن کوتاه = یک خط
        # ✅ متن بلند = بزرگ شدن تا ۴ خط
        multiline=True,
        min_lines=1,
        max_lines=4,

        # ❌ height ثابت نگذار، چون جلوی بزرگ شدن را می‌گیرد
        # height=FIELD_HEIGHT,

        content_padding=ft.padding.only(
            left=14,
            right=14,
            top=10,
            bottom=10,
        ),
    )

    price_field = ft.TextField(
        label=t(page, "edit_cost_price"),
        value=str(price_value) if price_value is not None else "",
        keyboard_type=ft.KeyboardType.TEXT,
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
        value=selected_category["category_title"],
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
        category_field.value = selected_category["category_title"]
        safe_update()

    def open_date_picker(e=None):
        date_picker.value = parse_date_safe(date_field.value)
        date_picker.open = True
        safe_update()

    def on_date_change(e):
        if not date_picker.value:
            return

        picked = safe_picker_date(date_picker.value, page)
        date_picker.value = picked

        date_field.value = picked.isoformat()
        safe_update()
        
    date_picker.on_change = on_date_change

    def on_category_selected(result: dict):
        selected_category["category_id"] = result.get("category_id")
        selected_category["category_title"] = result.get("category_title") or ""

        # ✅ حفظ مقدارهای ویرایش‌شده فرم
        row["title"] = (title_field.value or "").strip()
        row["price"] = price_field.value
        row["date_cost"] = local_date_iso(page, date_field.value)

        row["member_id"] = selected_member.get("member_id")
        row["member_name"] = selected_member.get("member_name") or ""

        row["account_id"] = selected_account.get("account_id")
        row["account_name"] = selected_account.get("account_name") or ""

        # ✅ آپدیت کتگوری جدید
        row["id_hazine"] = selected_category["category_id"]
        row["category_title"] = selected_category["category_title"]
        row["old_category_id"] = original_category_id

        page.data["edit_cost_row"] = row

        update_category_ui()

    def show_category_loading_cover():
        cover = ft.Container(
            key="category_nav_cover",
            expand=True,
            bgcolor="#FFFFFF",
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                [
                    ft.ProgressRing(width=26, height=26, stroke_width=3),
                    ft.Text(t(page, "edit_cost_message_loading_categories"), size=13, color="#64748B"),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )

        if cover not in page.overlay:
            page.overlay.append(cover)

        page.update()


    def choose_category(e=None):
        page.data = page.data or {}

        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = selected_category["category_id"]
        page.data["category_picker_on_selected"] = on_category_selected

        page.data["from"] = "edit_cost_dialog"
        page.data["reopen_edit_cost_dialog"] = True

        row["title"] = (title_field.value or "").strip()
        row["price"] = price_field.value
        row["date_cost"] = local_date_iso(page, date_field.value)

        row["member_id"] = selected_member.get("member_id")
        row["member_name"] = selected_member.get("member_name") or ""

        row["account_id"] = selected_account.get("account_id")
        row["account_name"] = selected_account.get("account_name") or ""

        row["id_hazine"] = selected_category.get("category_id")
        row["category_title"] = selected_category.get("category_title") or ""

        row["old_category_id"] = original_category_id
        page.data["edit_cost_row"] = row

        show_category_loading_cover()

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

        raw = raw.replace("٬", "")
        raw = raw.replace(",", ".")
        raw = raw.replace("−", "-")  # minus symbol

        # تبدیل اعداد فارسی/عربی به انگلیسی
        fa_digits = "۰۱۲۳۴۵۶۷۸۹"
        ar_digits = "٠١٢٣٤٥٦٧٨٩"
        en_digits = "0123456789"

        for fa, en in zip(fa_digits, en_digits):
            raw = raw.replace(fa, en)

        for ar, en in zip(ar_digits, en_digits):
            raw = raw.replace(ar, en)

        # اگر کاربر اشتباهی 100- نوشت، تبدیل به -100 شود
        if raw.endswith("-"):
            raw = "-" + raw[:-1]

        try:
            amount = float(raw)
        except Exception:
            return None, "مبلغ نامعتبر است."

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
            error_text.value = t(page, "edit_cost_message_select_category")
            error_text.visible = True
            safe_update()
            return

        payload = {
            "id": row.get("id"),
            "title": title_clean,
            "price": amount,
            "date_cost": local_date_iso(page, date_field.value),
            "id_hazine": selected_category["category_id"],
            "category_title": selected_category["category_title"],
            "currency_id": row.get("currency_id"),

            # ✅ مهم
            "member_id": selected_member.get("member_id"),
            "member_name": selected_member.get("member_name") or "",

            # ✅ اگر حساب هم می‌خواهی ذخیره شود
            "account_id": selected_account.get("account_id"),

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
                            t(page, "edit_cost_select_account"),
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
                            "",
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


    header_block = ft.Row(
        [
            ft.Icon(
                ft.Icons.EDIT_NOTE_ROUNDED,
                color=PRIMARY,
                size=18,
            ),
            ft.Text(
                t(page, "edit_cost_formtitle"),
                size=15,
                weight=ft.FontWeight.W_700,
                color=TEXT_MAIN,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


    dialog = ft.AlertDialog(
        modal=True,
        bgcolor="#FFFFFF",
        inset_padding=20,
        shape=ft.RoundedRectangleBorder(radius=24),
        title=header_block,
        content=ft.Container(
            width=460,
            height=620,
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