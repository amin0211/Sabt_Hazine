# ui/date_picker_test_view.py

import flet as ft
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from services.supabase_service import insert_log


def date_picker_test_view(page: ft.Page):
    page.data = page.data or {}

    APP_BG = "#F8FAFC"
    BORDER = "#E5E7EB"
    PRIMARY = "#2563EB"
    DANGER = "#DC2626"
    SUCCESS = "#16A34A"
    TEXT = "#111827"
    MUTED = "#6B7280"

    log_rows = []
    row_counter = {"value": 0}

    def safe_update():
        try:
            page.update()
        except RuntimeError as ex:
            if "destroyed session" in str(ex).lower():
                print("[DATE TEST] skip update: destroyed session", flush=True)
            else:
                raise
        except Exception as ex:
            print("[DATE TEST UPDATE ERROR]", ex, flush=True)

    def value_info(value):
        try:
            return {
                "repr": repr(value),
                "str": str(value),
                "type": type(value).__name__,
                "iso": value.isoformat() if hasattr(value, "isoformat") else "",
                "year": getattr(value, "year", ""),
                "month": getattr(value, "month", ""),
                "day": getattr(value, "day", ""),
                "tzinfo": str(getattr(value, "tzinfo", "")),
            }
        except Exception as ex:
            return {
                "repr": repr(value),
                "str": str(value),
                "type": type(value).__name__,
                "iso": "",
                "year": "",
                "month": "",
                "day": "",
                "tzinfo": "",
                "error": str(ex),
            }

    def short_raw(value):
        raw = repr(value)
        if len(raw) > 80:
            return raw[:80] + "..."
        return raw

    def insert_date_test_log(item):
        try:
            insert_log(
                message=f"DATE PICKER TEST | {item.get('method')} | final={item.get('final')}",
                tag="date_picker_test",
                extra={
                    "no": item.get("no"),
                    "method": item.get("method"),
                    "selected": item.get("selected"),
                    "final": item.get("final"),
                    "is_ok": item.get("selected") == item.get("final"),
                    "type": item.get("type"),
                    "iso": item.get("iso"),
                    "raw": item.get("raw"),
                    "repr_full": item.get("repr_full"),
                    "str": item.get("str"),
                    "tzinfo": item.get("tzinfo"),
                    "ymd": item.get("ymd"),
                    "platform": str(getattr(page, "platform", "")),
                },
            )

            print("[DATE TEST] inserted into Supabase log", flush=True)

        except Exception as ex:
            print("[DATE TEST] insert_log error:", ex, flush=True)

    def make_log_row(item):
        selected = item.get("selected")
        final = item.get("final")

        # برای Today/Yesterday selected برابر "-" است، پس OK/CHECK معنی ندارد
        if selected == "-":
            is_ok = True
            status = "INFO"
            status_color = PRIMARY
            status_bg = "#DBEAFE"
            row_bg = "#EFF6FF"
        else:
            is_ok = selected == final
            status = "OK" if is_ok else "CHECK"
            status_color = SUCCESS if is_ok else DANGER
            status_bg = "#DCFCE7" if is_ok else "#FEE2E2"
            row_bg = "#ECFDF5" if is_ok else "#FFFFFF"

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEF0F4")),
            bgcolor=row_bg,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=26,
                                height=26,
                                border_radius=9,
                                bgcolor=status_bg,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(
                                    str(item["no"]),
                                    size=11,
                                    weight=ft.FontWeight.W_800,
                                    color=status_color,
                                ),
                            ),
                            ft.Text(
                                item["method"],
                                size=12,
                                weight=ft.FontWeight.W_700,
                                color=TEXT,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                status,
                                size=10,
                                weight=ft.FontWeight.W_800,
                                color=status_color,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.Text("Selected:", size=10, color=MUTED),
                            ft.Text(
                                selected or "-",
                                size=11,
                                color=TEXT,
                                weight=ft.FontWeight.W_700,
                                selectable=True,
                            ),
                            ft.Text("Final:", size=10, color=MUTED),
                            ft.Text(
                                final or "-",
                                size=11,
                                color=status_color,
                                weight=ft.FontWeight.W_800,
                                selectable=True,
                            ),
                        ],
                        spacing=5,
                        wrap=True,
                    ),
                    ft.Text(
                        f"TYPE: {item.get('type')} | ISO: {item.get('iso')}",
                        size=10,
                        color=MUTED,
                        selectable=True,
                    ),
                    ft.Text(
                        f"RAW: {item.get('raw')}",
                        size=10,
                        color=MUTED,
                        selectable=True,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
        )

    log_table = ft.ListView(
        expand=True,
        spacing=0,
        padding=0,
        auto_scroll=True,
    )

    latest_result_text = ft.Text(
        "هنوز تستی انجام نشده.",
        size=12,
        color=MUTED,
        selectable=True,
    )

    def add_log(method_title, selected_date, raw_value, final_value):
        row_counter["value"] += 1

        info = value_info(raw_value)

        item = {
            "no": row_counter["value"],
            "method": method_title,
            "selected": selected_date,
            "final": final_value,
            "type": info.get("type"),
            "iso": info.get("iso"),
            "raw": short_raw(raw_value),
            "repr_full": info.get("repr"),
            "str": info.get("str"),
            "tzinfo": info.get("tzinfo"),
            "ymd": f"{info.get('year')}-{info.get('month')}-{info.get('day')}",
        }

        log_rows.append(item)
        log_table.controls.append(make_log_row(item))

        # ذخیره در جدول log Supabase
        insert_date_test_log(item)

        latest_result_text.value = (
            f"{method_title}\n"
            f"Selected: {selected_date}\n"
            f"Final: {final_value}\n"
            f"Type: {info.get('type')}\n"
            f"ISO: {info.get('iso')}\n"
            f"Raw: {info.get('repr')}"
        )

        print("\n========== DATE PICKER TEST ==========", flush=True)
        print(f"METHOD: {method_title}", flush=True)
        print(f"SELECTED: {selected_date}", flush=True)
        print(f"TYPE: {info.get('type')}", flush=True)
        print(f"REPR: {info.get('repr')}", flush=True)
        print(f"STR: {info.get('str')}", flush=True)
        print(f"ISO: {info.get('iso')}", flush=True)
        print(f"TZINFO: {info.get('tzinfo')}", flush=True)
        print(f"Y/M/D: {info.get('year')}-{info.get('month')}-{info.get('day')}", flush=True)
        print(f"FINAL: {final_value}", flush=True)
        print("======================================\n", flush=True)

        safe_update()

    def open_picker(picker):
        picker.open = True
        safe_update()

    def selected_date_from_picker(value):
        if value is None:
            return ""

        y = getattr(value, "year", None)
        m = getattr(value, "month", None)
        d = getattr(value, "day", None)

        if y and m and d:
            return f"{y:04d}-{m:02d}-{d:02d}"

        return str(value)[:10]

    # -------------------------
    # 5 روش تبدیل
    # -------------------------

    def method_1_date_only(value):
        """
        روش ۱:
        مستقیم year/month/day از DatePicker value.
        """
        if value is None:
            return None

        return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"

    def method_2_string_cut(value):
        """
        روش ۲:
        str(value)[:10]
        """
        if value is None:
            return None

        return str(value)[:10]

    def method_3_iso_cut(value):
        """
        روش ۳:
        value.isoformat()[:10]
        """
        if value is None:
            return None

        if hasattr(value, "isoformat"):
            return value.isoformat()[:10]

        return str(value)[:10]

    def method_4_dubai_timezone(value):
        """
        روش ۴:
        اگر datetime بود، تبدیل به Asia/Dubai.
        """
        if value is None:
            return None

        dubai = ZoneInfo("Asia/Dubai")

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=dubai)
            else:
                value = value.astimezone(dubai)

            return value.date().isoformat()

        if isinstance(value, date):
            return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"

        return str(value)[:10]

    def method_5_force_dubai_noon(value):
        """
        روش ۵:
        year/month/day را می‌گیرد و ساعت ۱۲ ظهر دبی می‌سازد.
        """
        if value is None:
            return None

        y = getattr(value, "year", None)
        m = getattr(value, "month", None)
        d = getattr(value, "day", None)

        if not y or not m or not d:
            return str(value)[:10]

        dubai_noon = datetime(y, m, d, 12, 0, 0, tzinfo=ZoneInfo("Asia/Dubai"))
        return dubai_noon.date().isoformat()

    # -------------------------
    # Pickers
    # -------------------------

    today = date.today()

    picker_1 = ft.DatePicker(value=today)
    picker_2 = ft.DatePicker(value=today)
    picker_3 = ft.DatePicker(value=today)
    picker_4 = ft.DatePicker(value=today)
    picker_5 = ft.DatePicker(value=today)

    for picker in [picker_1, picker_2, picker_3, picker_4, picker_5]:
        if picker not in page.overlay:
            page.overlay.append(picker)

    # -------------------------
    # Method buttons
    # -------------------------

    def build_method_button(number, title, subtitle, on_click):
        value_label = ft.Text(
            "No date selected",
            size=11,
            color=MUTED,
            selectable=True,
        )

        box = ft.Container(
            ink=True,
            on_click=on_click,
            padding=12,
            border_radius=16,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, BORDER),
            content=ft.Row(
                [
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=11,
                        bgcolor="#EEF2FF",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            str(number),
                            size=13,
                            weight=ft.FontWeight.W_800,
                            color=PRIMARY,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                size=12,
                                weight=ft.FontWeight.W_700,
                                color=TEXT,
                            ),
                            ft.Text(
                                subtitle,
                                size=9,
                                color=MUTED,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            value_label,
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CALENDAR_MONTH_ROUNDED, size=19, color=PRIMARY),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        box.value_label = value_label
        return box

    btn_1 = build_method_button(
        1,
        "Direct year/month/day",
        "value.year / value.month / value.day",
        lambda e: open_picker(picker_1),
    )

    btn_2 = build_method_button(
        2,
        "String cut",
        "str(value)[:10]",
        lambda e: open_picker(picker_2),
    )

    btn_3 = build_method_button(
        3,
        "ISO cut",
        "value.isoformat()[:10]",
        lambda e: open_picker(picker_3),
    )

    btn_4 = build_method_button(
        4,
        "Dubai timezone",
        "astimezone Asia/Dubai if datetime",
        lambda e: open_picker(picker_4),
    )

    btn_5 = build_method_button(
        5,
        "Force Dubai noon",
        "build Dubai datetime at 12:00",
        lambda e: open_picker(picker_5),
    )

    def on_change_1(e):
        raw = picker_1.value
        selected = selected_date_from_picker(raw)
        final = method_1_date_only(raw)
        btn_1.value_label.value = final or "No date"
        add_log("M1 - Direct Y/M/D", selected, raw, final)

    def on_change_2(e):
        raw = picker_2.value
        selected = selected_date_from_picker(raw)
        final = method_2_string_cut(raw)
        btn_2.value_label.value = final or "No date"
        add_log("M2 - str(value)[:10]", selected, raw, final)

    def on_change_3(e):
        raw = picker_3.value
        selected = selected_date_from_picker(raw)
        final = method_3_iso_cut(raw)
        btn_3.value_label.value = final or "No date"
        add_log("M3 - isoformat()[:10]", selected, raw, final)

    def on_change_4(e):
        raw = picker_4.value
        selected = selected_date_from_picker(raw)
        final = method_4_dubai_timezone(raw)
        btn_4.value_label.value = final or "No date"
        add_log("M4 - Dubai timezone", selected, raw, final)

    def on_change_5(e):
        raw = picker_5.value
        selected = selected_date_from_picker(raw)
        final = method_5_force_dubai_noon(raw)
        btn_5.value_label.value = final or "No date"
        add_log("M5 - Dubai noon", selected, raw, final)

    picker_1.on_change = on_change_1
    picker_2.on_change = on_change_2
    picker_3.on_change = on_change_3
    picker_4.on_change = on_change_4
    picker_5.on_change = on_change_5

    # -------------------------
    # Today / Yesterday test
    # -------------------------

    def test_today_yesterday(e=None):
        dubai_today = datetime.now(ZoneInfo("Asia/Dubai")).date()
        python_local_today = datetime.now().date()
        utc_today = datetime.now(ZoneInfo("UTC")).date()

        rows = [
            {
                "label": "Dubai today",
                "value": dubai_today.isoformat(),
            },
            {
                "label": "Python local today",
                "value": python_local_today.isoformat(),
            },
            {
                "label": "UTC today",
                "value": utc_today.isoformat(),
            },
            {
                "label": "Dubai yesterday",
                "value": (dubai_today - timedelta(days=1)).isoformat(),
            },
            {
                "label": "Python local yesterday",
                "value": (python_local_today - timedelta(days=1)).isoformat(),
            },
            {
                "label": "UTC yesterday",
                "value": (utc_today - timedelta(days=1)).isoformat(),
            },
        ]

        latest_lines = []

        for r in rows:
            row_counter["value"] += 1

            item = {
                "no": row_counter["value"],
                "method": r["label"],
                "selected": "-",
                "final": r["value"],
                "type": "system-date",
                "iso": r["value"],
                "raw": r["value"],
                "repr_full": r["value"],
                "str": r["value"],
                "tzinfo": "-",
                "ymd": r["value"],
            }

            log_rows.append(item)
            log_table.controls.append(make_log_row(item))

            # ذخیره Today/Yesterday هم در جدول log
            insert_date_test_log(item)

            latest_lines.append(f"{r['label']}: {r['value']}")

        latest_result_text.value = "\n".join(latest_lines)

        print("\n========== TODAY/YESTERDAY TEST ==========", flush=True)
        print(latest_result_text.value, flush=True)
        print("==========================================\n", flush=True)

        safe_update()

    def clear_logs(e=None):
        log_rows.clear()
        log_table.controls.clear()
        row_counter["value"] = 0

        for btn in [btn_1, btn_2, btn_3, btn_4, btn_5]:
            btn.value_label.value = "No date selected"

        latest_result_text.value = "Logs cleared."
        safe_update()

    # -------------------------
    # UI
    # -------------------------

    top_bar = ft.Container(
        padding=ft.padding.only(left=16, right=16, top=16, bottom=14),
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    icon_color=TEXT,
                    on_click=lambda e: page.app_go("sabtehazine"),
                ),
                ft.Column(
                    [
                        ft.Text(
                            "DatePicker Dubai Test",
                            size=16,
                            weight=ft.FontWeight.W_800,
                            color=TEXT,
                        ),
                        ft.Text(
                            "هر انتخاب هم در UI می‌آید، هم در Supabase log ذخیره می‌شود",
                            size=11,
                            color=MUTED,
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                    icon_color=DANGER,
                    tooltip="Clear UI logs",
                    on_click=clear_logs,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    test_tools = ft.Container(
        padding=12,
        border_radius=16,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(
                    "Step 1",
                    size=12,
                    weight=ft.FontWeight.W_800,
                    color=TEXT,
                ),
                ft.ElevatedButton(
                    "Test Dubai Today / Yesterday",
                    icon=ft.Icons.PUBLIC_ROUNDED,
                    on_click=test_today_yesterday,
                ),
                ft.Text(
                    "بعد هر ۵ روش را یکی‌یکی بزن و یک تاریخ یکسان انتخاب کن. هر نتیجه مستقیم پایین در Log می‌آید و در Supabase ذخیره می‌شود.",
                    size=10,
                    color=MUTED,
                ),
            ],
            spacing=7,
            tight=True,
        ),
    )

    methods_card = ft.Container(
        padding=12,
        border_radius=16,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(
                    "Methods",
                    size=13,
                    weight=ft.FontWeight.W_800,
                    color=TEXT,
                ),
                btn_1,
                btn_2,
                btn_3,
                btn_4,
                btn_5,
            ],
            spacing=7,
            tight=True,
        ),
    )

    latest_card = ft.Container(
        padding=10,
        border_radius=16,
        bgcolor="#F9FAFB",
        border=ft.border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(
                    "Latest",
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=TEXT,
                ),
                latest_result_text,
            ],
            spacing=5,
            tight=True,
        ),
    )

    log_header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        border_radius=12,
        bgcolor="#EEF2FF",
        content=ft.Row(
            [
                ft.Text("#", size=10, color=PRIMARY, weight=ft.FontWeight.W_800, width=28),
                ft.Text("Method / Result", size=10, color=PRIMARY, weight=ft.FontWeight.W_800, expand=True),
                ft.Text("Status", size=10, color=PRIMARY, weight=ft.FontWeight.W_800),
            ],
            spacing=8,
        ),
    )

    body = ft.Container(
        expand=True,
        padding=12,
        content=ft.Column(
            [
                test_tools,
                methods_card,
                latest_card,
                ft.Row(
                    [
                        ft.Text(
                            "Log Table",
                            size=13,
                            weight=ft.FontWeight.W_800,
                            color=TEXT,
                            expand=True,
                        ),
                        ft.Text(
                            "Saved to Supabase log",
                            size=10,
                            color=SUCCESS,
                            weight=ft.FontWeight.W_700,
                        ),
                    ],
                    spacing=8,
                ),
                log_header,
                ft.Container(
                    expand=True,
                    border_radius=16,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, BORDER),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=log_table,
                ),
            ],
            spacing=9,
        ),
    )

    return ft.View(
        route="/date_picker_test",
        bgcolor=APP_BG,
        padding=0,
        spacing=0,
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.SafeArea(
                        avoid_intrusions_top=True,
                        avoid_intrusions_bottom=False,
                        content=top_bar,
                    ),
                    body,
                ],
            )
        ],
    )