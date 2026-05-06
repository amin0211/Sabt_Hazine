import flet as ft
from datetime import date, datetime
import asyncio
from queue import Queue, Empty
# from Hazineha import hazinaha_view
from services.voice_service_router import start_recording, stop_recording
# from services.supabase_service import insert_log
from ui.edit_cost_dialog import open_edit_cost_dialog

from services.supabase_service import (
    upsert_category_learning,
    update_category_learning_embedding,
    sign_out_user,
    get_members,
    add_member,
    get_financial_summary,
    get_income_transactions_by_month,
    get_my_profile,
    get_current_user,
)
from services.openai_service import get_embedding
from services.parser_service import normalize_text
from services.i18n import t
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def now_local():
    return datetime.now(TZ)

def today_local():
    return now_local().date()

def build_chat_ui(
    page,
    supabase_service,
    controller,
    parse_expense_,
    normalize_date, 
    theme
):
    q = Queue()
    
    voice_state = {
    "is_recording": False,
    "start_ready": False,
    }
   
    APP_BG = theme["APP_BG"]
    CARD = theme["CARD"]
    PRIMARY = theme["PRIMARY"]
    
    text_primary = "#111827"
    text_secondary = "#6B7280"
    card_color = "#F0F0F3"
    input_bg =  "#FFFFFF"
    border_color = "#E5E7EB"
    success_bg =  "#EEFDF3"



    # page.window.maximized = True

    chat_column = ft.Column(
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )

    async def check_user_session():
        stored_user_id = await page.shared_preferences.get("user_id")

        auth_user = get_current_user()
        current_user_id = auth_user.id if auth_user else None
        # current_user_Email = auth_user.email

        # print("eeeeeeee =", current_user_Email)
        print("STORED USER ID =", stored_user_id)
        print("AUTH USER ID =", current_user_id)

        if stored_user_id and current_user_id and stored_user_id != current_user_id:
            print("❌ USER MISMATCH - clearing local state")
            await page.shared_preferences.clear()
            page.data = {}
            page.app_go("login")
            safe_page_update(page)



    def remove_empty_state():
        chat_column.controls = [
            c for c in chat_column.controls
            if getattr(c, "data", None) != "empty_state"
        ]
    def build_empty_state():
        box = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            margin=ft.margin.only(top=80),
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.RECEIPT_LONG_OUTLINED,
                        size=48,
                        color="#9CA3AF",
                    ),
                    ft.Text(
                        t(page, "Sabt_hazine_empty_expense_title"),
                        size=16,
                        color="#9CA3AF",
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Text(
                        t(page, "Sabt_hazine_empty_expense_sub"),
                        size=12,
                        color="#D1D5DB",
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
        )
        box.data = "empty_state"
        return box

    def open_hazineha_from_menu():
        page.data = page.data or {}

        page.data["from"] = "sabtehazine"
        page.data["category_picker_mode"] = False
        page.data["category_picker_on_selected"] = None
        page.data["category_picker_current_id"] = None
        page.data["without_edit"] = False

        page.app_go("hazinaha_view")

    def build_main_menu():
        return ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            tooltip="منو",
            items=[
                ft.PopupMenuItem(
                    icon=ft.Icons.ACCOUNT_BALANCE,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "Accounts")),
                    ),
                    on_click=lambda e: page.app_go("accounts"),
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.GROUPS_OUTLINED,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "members")),
                    ),
                    on_click=lambda e: page.app_go("members"),
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "Income")),
                    ),
                    on_click=lambda e: page.app_go("income"),
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "Budget")),
                    ),
                    on_click=lambda e: page.app_go("budget_view"),
                ),
                ft.PopupMenuItem(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "dashboard")),
                    ),
                    on_click=lambda e: page.app_go("dashboard_view"),
                ),

                ft.PopupMenuItem(
                    icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "Categories")),
                    ),
                    on_click=lambda e: open_hazineha_from_menu(),
                ),

                ft.PopupMenuItem(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "GanttChart")),
                    ),
                    on_click=lambda e: page.app_go("GanttChart_view"),
                ),

                ft.PopupMenuItem(),

                ft.PopupMenuItem(
                    icon=ft.Icons.PERSON_OUTLINE,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "profile")),
                    ),
                    on_click=lambda e: page.app_go("profile"),
                ),

                ft.PopupMenuItem(
                    icon=ft.Icons.LOGOUT_ROUNDED,
                    content=ft.Container(
                        width=150,
                        content=ft.Text(t(page, "logout"), color="#DC2626"),
                    ),
                    on_click=logout,
                ),
            ],
        )

    def logout(e):
        try:
            sign_out_user()
        except Exception as ex:
            print("logout error:", ex)

        try:
            page.shared_preferences.clear()
        except Exception as ex:
            print("shared_preferences clear error:", ex)

        page.data = {}
        page.app_go("login")


    voice_state = {
        "is_recording": False,
        "start_ready": False,
        "release_pending": False,
    }

    async def start_recording_and_mark_ready():
        try:

            result = await start_recording(page)


        except Exception as ex:
            result = None

        # حتی اگر result None بود، ادامه بده
        voice_state["start_ready"] = True

        

        if voice_state.get("release_pending"):

            voice_state["release_pending"] = False
            page.run_task(stop_and_check_voice)

    def on_mic_press(e):

        if voice_state["is_recording"]:
            return

        voice_state["is_recording"] = True
        voice_state["start_ready"] = False

        recording_pulse["active"] = True
        page.run_task(pulse_recording_dot)

        mic_icon.name = ft.Icons.MIC
        mic_icon.color = "#DC2626"
        mic_button_box.bgcolor = "#FEE2E2"
        safe_page_update(page)

        page.run_task(start_recording_and_mark_ready)
        

    async def stop_and_check_voice():
        stop_recording_indicator()


        result = await stop_recording(page)


        # 🔥 این خط مهمه
        q.put(("voice", result))


        await check_voice_result()

        

    def on_mic_release(e):

        if not voice_state["is_recording"]:
            return

        if not voice_state["start_ready"]:

            voice_state["release_pending"] = True
            voice_state["is_recording"] = False

            stop_recording_indicator()

            mic_icon.name = ft.Icons.MIC_ROUNDED
            mic_icon.color = PRIMARY
            mic_button_box.bgcolor = "#EEF2FF"
            safe_page_update(page)
            return

        voice_state["is_recording"] = False
        voice_state["start_ready"] = False

        stop_recording_indicator()

        mic_icon.name = ft.Icons.MIC_ROUNDED
        mic_icon.color = PRIMARY
        mic_button_box.bgcolor = "#EEF2FF"
        safe_page_update(page)

        page.run_task(stop_and_check_voice)

    def ask_user_to_choose_category(page: ft.Page, parsed_result: dict, on_confirm):
        suggestions = parsed_result.get("suggestions", [])

        if not suggestions:
            on_confirm(parsed_result)
            return

        dlg = ft.AlertDialog(modal=True)

        def choose(cat):
            parsed_result["category_id"] = cat["category_id"]
            parsed_result["category_title"] = cat["category_title"]
            # parsed_result["title"] = cat["category_title"]
            parsed_result["matched"] = True

            dlg.open = False
            page.update()
            on_confirm(parsed_result)

        def close_dlg(e=None):
            dlg.open = False
            page.update()
            
        # ذخیره با category خالی
            parsed_result["category_id"] = None
            parsed_result["category_title"] = None
            parsed_result["matched"] = False

            on_confirm(parsed_result)


        buttons = []
        for cat in suggestions[:3]:
            buttons.append(
                ft.ElevatedButton(
                    cat["category_title"],
                    width=220,
                    on_click=lambda e, c=cat: choose(c)
                )
            )

        dlg.title = ft.Text("کدام دسته درست است؟")
        dlg.content = ft.Column(
            [
                ft.Text("این هزینه دقیق تشخیص داده نشد. یکی از این گزینه‌ها را انتخاب کن:"),
                *buttons,
            ],
            tight=True,
            spacing=10,
        )
        dlg.actions = [ft.TextButton("بستن", on_click=close_dlg)]
        dlg.actions_alignment = ft.MainAxisAlignment.END

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        page.update()

    async def handle_send():
        safe_page_update(page)

        text = input_field.value.strip()
        if not text:
            safe_page_update(page)
            return

        safe_page_update(page)

        send_state["loading"] = True
        send_btn_ui.content = ft.ProgressRing(width=18, height=18, stroke_width=2, color=PRIMARY)
        send_btn_ui.bgcolor = "#E5E7EB"
        send_btn_ui.on_click = None
        safe_page_update(page)

        try:
            cost_id = getattr(input_field, "data", None)

            if cost_id:
                updated = await asyncio.to_thread(controller.edit_cost, cost_id, text)
                safe_page_update(page)
                update_ui(cost_id, updated)
            else:
                safe_page_update(page)


                parsed = await asyncio.to_thread(parse_expense_, text)
                parsed["text"] = text
                

                async def continue_after_choice(final_parsed):
                    new_row = await asyncio.to_thread(controller.save_new, final_parsed)
                    remove_empty_state()
                    chat_column.controls.insert(0, create_message(new_row))
                    refresh_summary()
                    input_field.value = ""
                    input_field.data = None
                    await input_field.focus()
                    page.data["sabtehazine_changed"] = True
                    safe_page_update(page)


                if not parsed.get("matched") and parsed.get("suggestions"):
                    ask_user_to_choose_category(
                            page,
                            parsed,
                            lambda final_parsed: page.run_task(continue_after_choice, final_parsed)
                        )
                else:
                    await continue_after_choice(parsed)                


                page.update()

                # new_row = await asyncio.to_thread(controller.save_new, text)
                # chat_column.controls.insert(0, create_message(new_row))
                # page.update()
     

            input_field.value = ""
            input_field.data = None
            await input_field.focus()
     
            safe_page_update(page)
        finally:
            send_state["loading"] = False
            send_btn_ui.content = ft.Icon(ft.Icons.ARROW_UPWARD_ROUNDED, size=18, color=PRIMARY)
            send_btn_ui.bgcolor = "#F3F4F6"
            send_btn_ui.on_click = send_message
            safe_page_update(page)


    def send_message(e):
        page.run_task(handle_send)
        # test_openai()

    input_field = ft.TextField(
        hint_text=t(page, "hint_text_InsertHazine"),
        expand=True,
        border_radius=16,
        border_color="transparent",
        bgcolor=CARD,
        text_size=14,
        content_padding=ft.padding.only(left=28, right=12, top=12, bottom=12),
        cursor_color=PRIMARY,
        on_submit=send_message,
    )

    start_date = today_local()
    end_date = today_local()

    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)

    page.overlay.append(start_picker)
    page.overlay.append(end_picker)

    def build_filter_button(label, icon):
        return ft.Container(
            border=ft.border.all(1, border_color),
            border_radius=14,
            bgcolor=card_color,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=PRIMARY),
                    ft.Text(label, size=13, color=text_primary, weight=ft.FontWeight.W_500),
                ],
                spacing=8,
                tight=True,
            )
        )

    start_btn = ft.GestureDetector(
        on_tap=lambda e: open_start(e),
        content=build_filter_button(f"{t(page, "date_from")}: {start_date}", ft.Icons.CALENDAR_MONTH)
    )

    end_btn = ft.GestureDetector(
        on_tap=lambda e: open_end(e),
        content=build_filter_button(f"{t(page, "date_to")}: {end_date}", ft.Icons.DATE_RANGE)
    )
    # tree_btn = ft.IconButton(
    #     icon=ft.Icons.ACCOUNT_TREE,
    #     on_click=lambda e: page.app_go("hazinaha_view")   # یا push_route اگر route درست داری
    # )

    def open_start(e):
        start_picker.open = True
        page.update()

    def open_end(e):
        end_picker.open = True
        page.update()

    def load_filtered():
        res = supabase_service.load_my_costs_by_date(
            start_date.isoformat(),
            end_date.isoformat()
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(build_empty_state())
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        refresh_summary()
        page.update()   


    def update_start(e):
        nonlocal start_date
        start_date = start_picker.value.date()
        start_picker.value = start_date

        start_btn.content = build_filter_button(f"از: {start_date}", ft.Icons.CALENDAR_MONTH)
        start_btn.update()
        load_filtered()

    def update_end(e):
        nonlocal end_date
        end_date = end_picker.value.date()
        end_picker.value = end_date

        end_btn.content = build_filter_button(f"تا: {end_date}", ft.Icons.DATE_RANGE)
        end_btn.update()
        load_filtered()

    start_picker.on_change = update_start
    end_picker.on_change = update_end


    summary_balance = ft.Text(
        "$0.00",
        size=26,
        weight=ft.FontWeight.BOLD,
        color="#111827",
    )

    summary_income = ft.Text(
        "$0.00",
        size=10,
        weight=ft.FontWeight.BOLD,
        color="#16A34A",
    )
    summary_month_text = ft.Text(
        "",
        size=10,
        color="#6B7280",
    )

    summary_expense = ft.Text(
        "$0.00",
        size=10,
        weight=ft.FontWeight.BOLD,
        color="#DC2626",
    )

    summary_left = ft.Text(
        "$0.00",
        size=10,
        weight=ft.FontWeight.BOLD,
        color=PRIMARY,
    )

    def money(v):
        try:
            return f"${float(v):,.2f}"
        except:
            return "$0.00"


    def build_summary_item(label, value_control, icon, color):
        return ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=10, vertical=9),
            border_radius=16,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#EEF0F4"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=14, color=color),
                            ft.Text(label, size=10, color="#6B7280"),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                    value_control,
                ],
                spacing=4,
            ),
        )



    summary_card = ft.Container(
        padding=14,
        border_radius=20,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("Total Balance", size=12, color="#6B7280"),
                                        summary_month_text,
                                        # ft.Text(current_user_Email, size=12, color="#6B7280"),
                                    ],
                                    spacing=6,
                                ),
                                summary_balance,
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=14,
                            bgcolor="#EEF2FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.PopupMenuButton(
                                icon=ft.Icons.MENU_ROUNDED,
                                tooltip="Menu",
                                items=build_main_menu().items,
                            ),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        # build_summary_item("Income", summary_income, ft.Icons.ARROW_DOWNWARD_ROUNDED, "#16A34A"),
                        build_summary_item(
                            "Income",
                            summary_income,
                            ft.Icons.ARROW_DOWNWARD_ROUNDED,
                            "#16A34A",
                        ),
                        build_summary_item("Expense", summary_expense, ft.Icons.ARROW_UPWARD_ROUNDED, "#DC2626"),
                        build_summary_item("Left", summary_left, ft.Icons.SAVINGS_OUTLINED, PRIMARY),
                    ],
                    spacing=8,
                ),
            ],
            spacing=12,
        ),
    )


    def refresh_summary():
        current_ym = today_local().strftime("%Y-%m")
        summary_month_text.value = f"( {current_ym} )"

        try:
            data = get_financial_summary(
                start_date.isoformat(),
                end_date.isoformat()
            )

            income_rows = get_income_transactions_by_month(current_ym)

            total_income = sum(
                float(row.get("amount") or 0)
                for row in income_rows
                if row.get("status") == "confirmed"
            )

            expense = float(data.get("expense") or 0)

            summary_balance.value = money(total_income - expense)
            summary_income.value = money(total_income)
            summary_expense.value = money(expense)
            summary_left.value = money(total_income - expense)

        except Exception as ex:
            print("refresh_summary error:", ex)

        safe_page_update(page)

    top_bar = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#F1F3F9", "#D3D6E6"]
        ),
        padding=ft.padding.only(left=12, top=14, right=12, bottom=12),
        border_radius=ft.border_radius.only(bottom_left=22, bottom_right=22),
        # shadow=ft.BoxShadow(
        #     blur_radius=12,
        #     color="#12000000",
        #     offset=ft.Offset(0, 3),
        # ),
        content=ft.Column(
            [
                summary_card,
                # ردیف اول: انتخاب تاریخ
                ft.Row(
                    [
                        ft.Row(
                            [
                                start_btn,
                                end_btn,
                                # build_main_menu(),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.START,
                        )
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),

                # ردیف دوم: دکمه های گزارش و درختی
            ],
            spacing=10,
            tight=True,
        ),
    )

    def open_category_picker_for_edit(current_category_id, on_selected):
        page.data = page.data or {}

        page.data["category_picker_mode"] = True
        page.data["category_picker_current_id"] = current_category_id
        page.data["category_picker_on_selected"] = on_selected
        page.data["from"] = "edit_cost_dialog"

        page.app_go("hazinaha_view")
                
    def create_message(row):
        
        is_invalid = not row.get("id_hazine")

        def delete_message(e):
            confirm_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete expense?"),
                content=ft.Text("This action cannot be undone."),
                actions=[
                    ft.TextButton(
                        "Cancel",
                        on_click=lambda e: close_confirm()
                    ),
                    ft.TextButton(
                        "Delete",
                        style=ft.ButtonStyle(color="#DC2626"),
                        on_click=lambda e: confirm_delete()
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            def close_confirm():
                confirm_dlg.open = False
                safe_page_update(page)

            def confirm_delete():
                try:
                    page.data["sabtehazine_changed"] = True
                    supabase_service.delete_my_cost(row["id"])

                    if container in chat_column.controls:
                        chat_column.controls.remove(container)

                    refresh_summary()

                    if not chat_column.controls:
                        chat_column.controls.append(build_empty_state())

                except Exception as ex:
                    print("delete cost error:", ex)

                confirm_dlg.open = False
                safe_page_update(page)

            if confirm_dlg not in page.overlay:
                page.overlay.append(confirm_dlg)

            confirm_dlg.open = True
            safe_page_update(page)
                    
        def edit_message(e):
            def on_save(updated_data):
                page.data["sabtehazine_changed"] = True
                old_category_id = row.get("id_hazine")
                new_category_id = updated_data.get("id_hazine")

                updated_row = controller.edit_cost(row["id"], updated_data)
                page.data["sabtehazine_changed"] = True
                page.data.pop("sabtehazine_view_cache", None)
                page.data["sabtehazine_loaded"] = False

                updated_row["id_hazine"] = updated_data.get("id_hazine")
                updated_row["category_title"] = updated_data.get("category_title")
                updated_row["member_id"] = updated_data.get("member_id")
                updated_row["member_name"] = updated_data.get("member_name") or row.get("member_name")
                updated_row["price"] = updated_data.get("price")
                updated_row["title"] = updated_data.get("title")
                updated_row["date_cost"] = updated_data.get("date_cost")

                # ✅ فقط وقتی کاربر اصلاح کرده
                if new_category_id and new_category_id != old_category_id:

                    raw_text = row.get("temp_hazine") or row.get("title", "")
                    normalized_text = normalize_text(raw_text)
                    learning_row = upsert_category_learning(
                        raw_text=raw_text,
                        normalized_text=normalized_text,
                        category_id=new_category_id,
                        source="user_corrected",
                        embedding_text=normalized_text
                    )

                    if learning_row:
                        embedding_vector = get_embedding(normalized_text)

                        if embedding_vector:
                            update_category_learning_embedding(
                                learning_row["id"],
                                embedding_vector
                            )

                update_ui(row["id"], updated_row)
                
            open_edit_cost_dialog(
                page=page,
                row=row,
                on_save=on_save,
            )

        title = row.get("title", t(page, "edit_cost_title"))
        date_text = row.get("date_cost", "")
        category_title = row.get("category_title", "")
        member_name = (row.get("member_name") or "").strip()
        price = row.get("price", 0)
        price_text = money(price)


        def tiny_action_btn(icon, color, on_click):
            return ft.IconButton(
                icon=icon,
                icon_color=color,
                icon_size=15,
                width=28,
                height=28,
                splash_radius=16,
                style=ft.ButtonStyle(
                    padding=4,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=on_click,
            )

        container = ft.Container(
            padding=12,
            border_radius=16,
            bgcolor="#FEF2F2" if is_invalid else "#FFFFFF",
            border=ft.border.all(1, "#FCA5A5" if is_invalid else "#E5E7EB"),
            # shadow=ft.BoxShadow(
            #     blur_radius=8,
            #     color="#0A000000",
            #     offset=ft.Offset(0, 2),
            # ),
            content=ft.Row(
                [
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=12,
                        bgcolor="#ECFDF5",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(
                                    ft.Icons.RECEIPT,
                                    color="#DC2626" if is_invalid else "#16A34A",
                                    size=18
                                ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color="#111827",
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.SCHEDULE, size=11, color="#6B7280"),
                                            ft.Text(date_text, size=11, color="#6B7280"),
                                            ft.Text("•", size=10, color="#9CA3AF") if category_title else ft.Container(),
                                            ft.Text(
                                                category_title,
                                                size=11,
                                                color="#6B7280",
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ) if category_title else ft.Container(),
                                        ],
                                        spacing=4,
                                        tight=True,
                                    ),

                                    ft.Text(
                                        f"{price_text} / {member_name}" if member_name else price_text,
                                        size=10,
                                        color="#6B7280",
                                        weight=ft.FontWeight.W_500,
                                    ),

                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    tiny_action_btn(
                                        ft.Icons.EDIT_OUTLINED,
                                        PRIMARY,
                                        edit_message
                                    ),
                                    tiny_action_btn(
                                        ft.Icons.DELETE_OUTLINE,
                                        "#DC2626",
                                        delete_message
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=2,
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        container.data = row["id"]
        return container


    async def load_messages_async():
        await asyncio.sleep(0.05)

        res = await asyncio.to_thread(
            supabase_service.load_my_costs_by_date,
            start_date.isoformat(),
            end_date.isoformat()
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(build_empty_state())
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        safe_page_update(page)


    # def load_messages():
        res = supabase_service.load_my_costs_by_date(
            start_date.isoformat(),
            end_date.isoformat()
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(build_empty_state())        
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        page.update()


    def update_ui(cost_id, new_row):
        for i, item in enumerate(chat_column.controls):
            if item.data == cost_id:
                chat_column.controls[i] = create_message(new_row)
                break
        page.update()

    def safe_page_update(page):
        try:
            page.update()
        except RuntimeError as e:
            if "destroyed session" in str(e).lower():
                print("SKIP UPDATE: session destroyed")
            else:
                raise

    async def check_voice_result():

        for i in range(200):
            latest_items = []

            try:
                while True:
                    item = q.get_nowait()
                    latest_items.append(item)
            except Empty:
                pass

            if latest_items:

                for status, data in latest_items:

                    if not isinstance(data, dict):
                        continue

                    if not data.get("ok"):
                        return

                    text = data.get("text")

                    if not text:
                        return


                    input_field.value = text

                    await input_field.focus()
                    input_field.update()
                    safe_page_update(page)

                    return

            await asyncio.sleep(0.1)




    # input_field.value = "MIC ERROR: پاسخی از سرور دریافت نشد"
    # input_field.focus()
    # page.update()
    
    page.data = page.data or {}
    page.data["is_recording"] = False
    
    page.run_task(check_user_session)

    send_state = {
        "loading": False
    }

    def build_send_button():
        return ft.Container(
            width=36,
            height=36,
            border_radius=11,
            bgcolor="#F3F4F6",
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=send_message,
            content=ft.Icon(ft.Icons.ARROW_UPWARD_ROUNDED, size=16, color=PRIMARY),
        )



    send_btn_ui = build_send_button()

    mic_icon = ft.Icon(ft.Icons.MIC_ROUNDED, color=PRIMARY, size=16)

    mic_button_box = ft.Container(
        width=36,
        height=36,
        border_radius=11,
        bgcolor="#EEF2FF",
        alignment=ft.Alignment.CENTER,
        content=mic_icon,
    )



    mic_button = ft.GestureDetector(
        on_pan_start=on_mic_press,
        on_pan_end=on_mic_release,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=mic_button_box,
    )


    send_btn_ui = build_send_button()

    recording_pulse = {
        "active": False,
        "strong": False,
    }

    recording_dot = ft.Container(
        width=8,
        height=8,
        border_radius=10,
        bgcolor="#DC2626",
        opacity=0,
        animate_opacity=300,
        animate_size=300,
    )

    def stop_recording_indicator():
        recording_pulse["active"] = False
        recording_pulse["strong"] = False

        recording_dot.opacity = 0
        recording_dot.width = 10
        recording_dot.height = 10

        safe_page_update(page)


    async def pulse_recording_dot():
        while recording_pulse["active"]:
            recording_pulse["strong"] = not recording_pulse["strong"]

            recording_dot.opacity = 1
            recording_dot.width = 16 if recording_pulse["strong"] else 9
            recording_dot.height = 16 if recording_pulse["strong"] else 9

            safe_page_update(page)
            await asyncio.sleep(0.45)

        recording_dot.opacity = 0
        recording_dot.width = 10
        recording_dot.height = 10
        safe_page_update(page)


    input_row = ft.Container(
        bgcolor=card_color,
        border=ft.border.only(top=ft.BorderSide(1, border_color)),
        padding=ft.padding.only(left=12, right=12, top=8, bottom=6),

        content=ft.Row(
            [
                ft.Container(
                    expand=True,
                    bgcolor=input_bg,
                    border_radius=22,
                    border=ft.border.all(1, border_color),
                    padding=ft.padding.only(left=4, right=4, top=5, bottom=5),

                    content=ft.Row(
                        [   
                            ft.Container(
                                expand=True,
                                content=ft.Stack(
                                    [
                                        input_field,

                                        ft.Container(
                                            left=8,
                                            top=0,
                                            bottom=0,
                                            alignment=ft.Alignment.CENTER_LEFT,
                                            content=recording_dot,
                                        ),
                                    ],
                                    expand=True,
                                ),
                            ),

                            send_btn_ui,

                            mic_button,
                        ],
                        spacing=2,
                        tight=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
        ),
    )
    
    if page.data.get("sabtehazine_changed") or not page.data.get("sabtehazine_loaded"):
        page.run_task(load_messages_async)
        page.data["sabtehazine_loaded"] = True
            # load_messages()

    print("REOPEN FLAG =", page.data.get("reopen_edit_cost_dialog"))
    print("EDIT ROW =", page.data.get("edit_cost_row"))

    if isinstance(page.data, dict) and page.data.get("reopen_edit_cost_dialog"):
        page.data["reopen_edit_cost_dialog"] = False

        edit_row = page.data.get("edit_cost_row")

        if edit_row:
            def reopen_on_save(updated_data):
                old_category_id = edit_row.get("old_category_id")
                new_category_id = updated_data.get("id_hazine")

                print(f" 11111 = {old_category_id}  == {new_category_id}")

                updated_row = controller.edit_cost(edit_row["id"], updated_data)
                page.data["sabtehazine_changed"] = True
                page.data.pop("sabtehazine_view_cache", None)
                page.data["sabtehazine_loaded"] = False

                updated_row["id_hazine"] = updated_data.get("id_hazine")
                updated_row["category_title"] = updated_data.get("category_title")
                updated_row["member_id"] = updated_data.get("member_id")
                updated_row["member_name"] = updated_data.get("member_name") or edit_row.get("member_name")
                updated_row["price"] = updated_data.get("price")
                updated_row["title"] = updated_data.get("title")
                updated_row["date_cost"] = updated_data.get("date_cost")

                if new_category_id and new_category_id != old_category_id:
                    raw_text = edit_row.get("temp_hazine") or edit_row.get("title", "")
                    normalized_text = normalize_text(raw_text)

                    learning_row = upsert_category_learning(
                        raw_text=raw_text,
                        normalized_text=normalized_text,
                        category_id=new_category_id,
                        source="user_corrected",
                        embedding_text=normalized_text,
                    )

                    if learning_row:
                        embedding_vector = get_embedding(normalized_text)

                        if embedding_vector:
                            update_category_learning_embedding(
                                learning_row["id"],
                                embedding_vector,
                            )

                update_ui(edit_row["id"], updated_row)

            open_edit_cost_dialog(
                page=page,
                row=edit_row,
                on_save=reopen_on_save,
            )

    refresh_summary()

    return ft.View(
        route="/sabtehazine",
        bgcolor=APP_BG,
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        top_bar,
                        ft.Container(
                            expand=True,
                            padding=ft.padding.symmetric(horizontal=12, vertical=12),
                            content=chat_column,
                        ),
                        ft.SafeArea(
                            avoid_intrusions_top=False,
                            avoid_intrusions_left=False,
                            avoid_intrusions_right=False,
                            avoid_intrusions_bottom=True,
                            maintain_bottom_view_padding=True,
                            minimum_padding=ft.padding.only(bottom=8),
                            content=input_row,
                        )
                    ],
                    spacing=0,
                    expand=True
                )
            )
        ]
    )