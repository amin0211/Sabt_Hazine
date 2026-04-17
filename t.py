import flet as ft
from datetime import date
from services.voice_service import start_voice
import asyncio
from queue import Queue


def build_chat_ui(
    page,
    supabase_service,
    controller,
    parse_expense_,
    normalize_date
):
    q = Queue()

    primary_color = "#4F46E5"
    bg_color = "#F5F7FB"
    card_color = "#FFFFFF"
    input_bg = "#FFFFFF"
    border_color = "#E5E7EB"
    text_primary = "#111827"
    text_secondary = "#6B7280"
    success_bg = "#EEFDF3"

    chat_column = ft.Column(
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )

    async def handle_send():
        text = input_field.value.strip()
        if not text:
            return

        send_button.disabled = True
        send_button.content = ft.Row(
            [
                ft.ProgressRing(width=16, height=16, stroke_width=2, color="white"),
                ft.Text("در حال ارسال...", color="white")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        )
        page.update()

        try:
            cost_id = getattr(input_field, "data", None)

            if cost_id:
                updated = await asyncio.to_thread(controller.edit_cost, cost_id, text)
                update_ui(cost_id, updated)
            else:
                new_row = await asyncio.to_thread(controller.save_new, text)
                chat_column.controls.insert(0, create_message(new_row))

            input_field.value = ""
            input_field.data = None
            input_field.focus()

        finally:
            send_button.disabled = False
            send_button.content = ft.Text("ارسال", weight=ft.FontWeight.W_600)
            page.update()

    def send_message(e):
        page.run_task(handle_send)

    input_field = ft.TextField(
        hint_text="مثلاً: دو لیوان قهوه 20 دلار",
        expand=True,
        border_radius=16,
        border_color="transparent",
        bgcolor=input_bg,
        text_size=14,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        cursor_color=primary_color,
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
                    ft.Icon(icon, size=16, color=primary_color),
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
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=36, color="#9CA3AF"),
                            ft.Text("هنوز هزینه‌ای ثبت نشده", size=15, weight=ft.FontWeight.W_600, color=text_primary),
                            ft.Text("از پایین یک هزینه جدید وارد کن", size=12, color=text_secondary),
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

    top_bar = ft.Container(
        bgcolor=card_color,
        padding=ft.padding.fromLTRB(16, 18, 16, 14),
        border_radius=ft.border_radius.only(bottom_left=24, bottom_right=24),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color="#12000000",
            offset=ft.Offset(0, 4),
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("ثبت هزینه‌ها", size=22, weight=ft.FontWeight.BOLD, color=text_primary),
                                ft.Text("مدیریت سریع و هوشمند هزینه‌های روزانه", size=12, color=text_secondary),
                            ],
                            spacing=2,
                        ),
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=14,
                            bgcolor="#EEF2FF",
                            alignment=ft.alignment.center,
                            content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=primary_color),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    [start_btn, end_btn],
                    spacing=10,
                    wrap=True,
                )
            ],
            spacing=16
        )
    )

    def create_message(row):
        def delete_message(e):
            supabase_service.delete_cost(row["id"])
            chat_column.controls.remove(container)
            page.update()

        def edit_message(e):
            input_field.value = row["title"]
            input_field.data = row["id"]
            input_field.focus()
            page.update()

        title = row.get("title", "بدون عنوان")
        date_text = row.get("date_cost", "")
        price = row.get("price", "")
        currency = row.get("currency_id", "")

        container = ft.Container(
            padding=14,
            border_radius=18,
            bgcolor=card_color,
            border=ft.border.all(1, "#EEF2F7"),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color="#10000000",
                offset=ft.Offset(0, 3),
            ),
            content=ft.Row(
                [
                    ft.Container(
                        width=42,
                        height=42,
                        border_radius=14,
                        bgcolor=success_bg,
                        alignment=ft.alignment.center,
                        content=ft.Icon(ft.Icons.RECEIPT, color="#16A34A", size=20),
                    ),
                    ft.Column(
                        [
                            ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=text_primary),
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.SCHEDULE, size=12, color=text_secondary),
                                    ft.Text(date_text, size=11, color=text_secondary),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                f"{price}" if price != "" else "",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=primary_color,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        tooltip="ویرایش",
                                        icon_color=primary_color,
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=12),
                                        ),
                                        on_click=edit_message
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="حذف",
                                        icon_color="#DC2626",
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=12),
                                        ),
                                        on_click=delete_message
                                    ),
                                ],
                                spacing=0,
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=4,
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
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=36, color="#9CA3AF"),
                            ft.Text("هنوز هزینه‌ای ثبت نشده", size=15, weight=ft.FontWeight.W_600, color=text_primary),
                            ft.Text("اولین هزینه را از پایین وارد کن", size=12, color=text_secondary),
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
        while page.data["is_recording"]:
            if not q.empty():
                status, data = q.get()

                if status == "ok":
                    input_field.value = data
                    input_field.focus()
                else:
                    print("ERROR:", data)
                break

            await asyncio.sleep(0.1)

        page.data["is_recording"] = False
        mic_button.icon = ft.Icons.MIC_ROUNDED
        mic_button.icon_color = primary_color
        page.update()

    page.data = {"is_recording": False}

    def on_mic_click(e):
        page.data["is_recording"] = True
        mic_button.icon = ft.Icons.STOP_CIRCLE_OUTLINED
        mic_button.icon_color = "#DC2626"
        page.update()

        start_voice(q)
        page.run_task(check_voice_result)

    mic_button = ft.Container(
        width=48,
        height=48,
        border_radius=16,
        bgcolor="#EEF2FF",
        alignment=ft.alignment.center,
        ink=True,
        on_click=on_mic_click,
        content=ft.Icon(ft.Icons.MIC_ROUNDED, color=primary_color),
    )

    send_button = ft.ElevatedButton(
        content=ft.Text("ارسال", weight=ft.FontWeight.W_600),
        on_click=send_message,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=primary_color,
            color="white",
            elevation=0,
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )

    input_row = ft.Container(
        bgcolor=card_color,
        border=ft.border.only(top=ft.BorderSide(1, "#E5E7EB")),
        padding=ft.padding.fromLTRB(12, 10, 12, 12),
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
        route="/",
        bgcolor=bg_color,
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