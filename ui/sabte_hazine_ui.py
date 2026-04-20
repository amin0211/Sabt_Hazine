import flet as ft
from datetime import date
import asyncio
from queue import Queue
# from Hazineha import hazinaha_view
from services.voice_service import start_recording, stop_recording

def build_chat_ui(
    page,
    supabase_service,
    controller,
    parse_expense_,
    normalize_date, 
    theme
):
    q = Queue()
    APP_BG = theme["APP_BG"]
    CARD = theme["CARD"]
    PRIMARY = theme["PRIMARY"]
    
    text_primary = "#111827"
    text_secondary = "#6B7280"
    card_color = "#F0F0F3"
    input_bg =  "#FFFFFF"
    border_color = "#E5E7EB"
    success_bg =  "#EEFDF3"

    page.window.maximized = True

    chat_column = ft.Column(
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )
    def on_mic_press(e):
        if page.data.get("is_recording"):
            return

        page.data["is_recording"] = True
        mic_button.content = ft.Icon(
            ft.Icons.MIC,
            color="#DC2626"
        )
        page.update()

        page.run_task(start_recording, q)


    def on_mic_release(e):
        if not page.data.get("is_recording"):
            return

        page.data["is_recording"] = False
        mic_button.content = ft.Icon(
            ft.Icons.MIC_ROUNDED,
            color=PRIMARY
        )
        page.update()

        page.run_task(stop_recording, q)
        page.run_task(check_voice_result)

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

        buttons = []
        # print(f"444 = {suggestions}")
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
        page.update()

        text = input_field.value.strip()
        if not text:
            page.update()
            return

        page.update()

        send_button.disabled = True
        send_button.content = ft.Row(
            [
                ft.ProgressRing(width=16, height=16, stroke_width=2, color="#FFFFFF"),
                ft.Text("در حال ارسال...", color="#FCFCFC")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        )
        page.update()

        try:
            cost_id = getattr(input_field, "data", None)

            if cost_id:
                updated = await asyncio.to_thread(controller.edit_cost, cost_id, text)
                page.update()
                update_ui(cost_id, updated)
            else:
                page.update()

                parsed = await asyncio.to_thread(parse_expense_, text)
                parsed["text"] = text
                
                async def continue_after_choice(final_parsed):
                    new_row = await asyncio.to_thread(controller.save_new, final_parsed)
                    chat_column.controls.insert(0, create_message(new_row))
                    input_field.value = ""
                    input_field.data = None
                    input_field.focus()
                    page.update()

                if not parsed.get("matched") and parsed.get("suggestions"):
                    print("PARSED =", parsed)
                    ask_user_to_choose_category(
                            page,
                            parsed,
                            lambda final_parsed: page.run_task(continue_after_choice, final_parsed)
                        )
                else:
                    
                    await continue_after_choice(parsed)                
                
                # page.update()

                # new_row = await asyncio.to_thread(controller.save_new, text)
                # chat_column.controls.insert(0, create_message(new_row))
                # page.update()
     

            input_field.value = ""
            input_field.data = None
            input_field.focus()
     
            page.update()
        finally:
            send_button.disabled = False
            send_button.content = ft.Text("ارسال", weight=ft.FontWeight.W_600)
            page.update()


    def send_message(e):
        page.run_task(handle_send)
        # test_openai()

    input_field = ft.TextField(
        hint_text="هزینه را وارد کن",
        expand=True,
        border_radius=16,
        border_color="transparent",
        bgcolor=CARD,
        text_size=14,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        cursor_color=PRIMARY,
        on_submit=send_message,
    )

    start_date = date.today()
    end_date = date.today()

    start_picker = ft.DatePicker()
    end_picker = ft.DatePicker()
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
        content=build_filter_button(f"از: {start_date}", ft.Icons.CALENDAR_MONTH)
    )

    end_btn = ft.GestureDetector(
        on_tap=lambda e: open_end(e),
        content=build_filter_button(f"تا: {end_date}", ft.Icons.DATE_RANGE)
    )
    # tree_btn = ft.IconButton(
    #     icon=ft.Icons.ACCOUNT_TREE,
    #     on_click=lambda e: page.go("/hazinaha_view")   # یا push_route اگر route درست داری
    # )

    def open_start(e):
        start_picker.open = True
        page.update()

    def open_end(e):
        end_picker.open = True
        page.update()

    def load_filtered():
        res = supabase_service.load_costs(
            start_date.isoformat(),
            end_date.isoformat()
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=18,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        [
                            # ft.Icon(ft.Icons.RECEIPT_LONG, size=36, color="#9CA3AF"),
                            # ft.Text("هنوز هزینه‌ای ثبت نشده", size=15, weight=ft.FontWeight.W_600, color=text_primary),
                            # ft.Text("از پایین یک هزینه جدید وارد کن", size=12, color=text_secondary),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    )
                )
            )
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        page.update()

    def update_start(e):
        nonlocal start_date
        start_date = start_picker.value.date()

        start_btn.content = build_filter_button(f"از: {start_date}", ft.Icons.CALENDAR_MONTH)
        start_btn.update()
        load_filtered()

    def update_end(e):
        nonlocal end_date
        end_date = end_picker.value.date()

        end_btn.content = build_filter_button(f"تا: {end_date}", ft.Icons.DATE_RANGE)
        end_btn.update()
        load_filtered()

    start_picker.on_change = update_start
    end_picker.on_change = update_end

   # دکمه آیکونی کوچک reusable
    def small_icon_btn(icon, on_click):
        return ft.Container(
            width=46,
            height=46,
            border_radius=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, border_color),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=on_click,
            content=ft.Icon(icon, color=PRIMARY, size=20),
        )


    top_bar = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#F1F3F9", "#D3D6E6"]
        ),
        padding=ft.padding.only(left=12, top=14, right=12, bottom=12),
        border_radius=ft.border_radius.only(bottom_left=22, bottom_right=22),
        shadow=ft.BoxShadow(
            blur_radius=12,
            color="#12000000",
            offset=ft.Offset(0, 3),
        ),
        content=ft.Column(
            [
                # ردیف اول: انتخاب تاریخ
                ft.Row(
                    [
                       ft.Row(
                                [
                                    start_btn,
                                    end_btn,
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.START,
                            )
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),

                # ردیف دوم: دکمه های گزارش و درختی
                ft.Row(
                    [
                        small_icon_btn(
                            ft.Icons.ACCOUNT_TREE_OUTLINED,
                            lambda e: page.go("/hazinaha_view")
                        ),
                        small_icon_btn(
                            ft.Icons.ANALYTICS_OUTLINED,
                            lambda e: page.go("/GanttChart_view") 
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
            tight=True,
        ),
    )


    def create_message(row):
        def delete_message(e):
            supabase_service.delete_cost(row["id"])
            chat_column.controls.remove(container)
            page.update()

        async def edit_message(e):
            input_field.value = row["title"]
            input_field.data = row["id"]
            input_field.focus()
            page.update()

        title = row.get("title", "بدون عنوان")
        date_text = row.get("date_cost", "")
        price = row.get("price", "")
        currency = row.get("currency_id", "")

        container = ft.Container(
    padding=12,
    border_radius=16,
    bgcolor="#FFFFFF",
    border=ft.border.all(1, "#E5E7EB"),
    shadow=ft.BoxShadow(
        blur_radius=8,
        color="#0A000000",
        offset=ft.Offset(0, 2),
    ),
        content=ft.Row(
            [
                # آیکون
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=12,
                    bgcolor="#ECFDF5",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.RECEIPT, color="#16A34A", size=18),
                ),

                # متن
                ft.Column(
                    [
                        ft.Text(title, size=14, weight=ft.FontWeight.W_600, color="#111827"),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.SCHEDULE, size=11, color="#6B7280"),
                                ft.Text(date_text, size=11, color="#6B7280"),
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),

                # قیمت + دکمه‌ها
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_color=PRIMARY,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                    on_click=edit_message
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color="#DC2626",
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                    on_click=delete_message
                                ),
                            ],
                            spacing=0,
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

    def load_messages():
        res = supabase_service.load_costs(
            start_date.isoformat(),
            end_date.isoformat()
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(
                ft.Container(
                    padding=20,
                    border_radius=18,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        [
                            # ft.Icon(ft.Icons.RECEIPT_LONG, size=36, color="#9CA3AF"),
                            # ft.Text("هنوز هزینه‌ای ثبت نشده", size=15, weight=ft.FontWeight.W_600, color=text_primary),
                            # ft.Text("اولین هزینه را از پایین وارد کن", size=12, color=text_secondary),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    )
                )
            )
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

    async def check_voice_result():
        for _ in range(600):  # حدود 30 ثانیه
            if not q.empty():
                status, data = q.get()

                if status == "ok":
                    input_field.value = data
                else:
                    input_field.value = data

                input_field.focus()
                page.update()
                return

            await asyncio.sleep(0.1)
    input_field.value = "MIC ERROR: پاسخی از سرور دریافت نشد"
    input_field.focus()
    page.update()
    
    page.data = {"is_recording": False}

    def on_mic_click(e):
        # q.put(("ok", "test voice"))
        page.data["is_recording"] = True
        mic_button.icon = ft.Icons.STOP_CIRCLE_OUTLINED
        mic_button.content = ft.Icon(
            ft.Icons.STOP_CIRCLE_OUTLINED,
            color="#DC2626"
        )
        page.update()

        start_voice(q)
        page.run_task(check_voice_result)

    mic_button = ft.GestureDetector(
        on_pan_start=on_mic_press,
        on_pan_end=on_mic_release,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=ft.Container(
            width=48,
            height=48,
            border_radius=16,
            bgcolor="#EEF2FF",
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.MIC_ROUNDED, color=PRIMARY),
        ),
    )

    send_button = ft.ElevatedButton(
    # send_button = ft.Container(
        # text="ارسال",
        content=ft.Text("ارسال", weight=ft.FontWeight.W_600),
        on_click=send_message,
        height=48
        ,
        style=ft.ButtonStyle(
            bgcolor=PRIMARY,
            color="white",
            elevation=0,
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )

   
    input_row = ft.Container(
        bgcolor=card_color,
        border=ft.border.only(top=ft.BorderSide(1, "#E5E7EB")),
        padding=ft.padding.only(left=12, top=10, right=12, bottom=12),
        content=ft.Row(
            [
                mic_button,
                ft.Container(
                    expand=True,
                    bgcolor=input_bg,
                    border_radius=18,
                    border=ft.border.all(1, border_color),
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    content=input_field,
                ),
                send_button
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    
    load_messages()

    return ft.View(
        route="/sabtehazine",
        bgcolor=APP_BG,
        # bgcolor=bg_color,
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
                        input_row
                    ],
                    spacing=0,
                    expand=True
                )
            )
        ]
    )