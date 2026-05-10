import flet as ft
import flet_charts as fch
from datetime import date, timedelta, datetime
from services.i18n import t

from services.supabase_service import load_all_hazineha, load_my_costs_by_date
import traceback
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()


class Node:
    def __init__(self, id, title, parent_id):
        self.id = id
        self.title = title
        self.parent_id = parent_id
        self.children = []
        self.total = 0


def GanttChart_view(page: ft.Page, theme):
    APP_BG = theme["APP_BG"]
    PRIMARY = theme["PRIMARY"]

    page_bg = "#F8FAFC"
    card_bg = "#FFFFFF"
    soft_bg = "#F1F5F9"
    text_primary = "#0F172A"
    text_secondary = "#64748B"
    border_color = "#E2E8F0"

    current_chart_type = {"value": "pie"}
    current_parent_id = {"value": None}
    path_stack = []

    today = today_local()
    start_date = today.replace(day=1)

    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)

    end_date = next_month_first - timedelta(days=1)

    CHART_COLORS = [
        "#6366F1",
        "#22C55E",
        "#F59E0B",
        "#EF4444",
        "#0EA5E9",
        "#A855F7",
        "#14B8A6",
        "#F97316",
    ]

    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)
    
    page.overlay.append(start_picker)
    page.overlay.append(end_picker)

    def build_filter_button(label, icon):
        return ft.Container(
            border=ft.border.all(1, border_color),
            border_radius=14,
            bgcolor=card_bg,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=PRIMARY),
                    ft.Text(
                        label,
                        size=13,
                        color=text_primary,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
        )

    def open_start(e):
        start_picker.open = True
        page.update()

    def open_end(e):
        end_picker.open = True
        page.update()

    start_btn = ft.GestureDetector(
        on_tap=open_start,
        content=build_filter_button(f"{t(page, "date_from")}: {start_date}", ft.Icons.CALENDAR_MONTH),
    )

    end_btn = ft.GestureDetector(
        on_tap=open_end,
        content=build_filter_button(f"{t(page, "date_to")}: {end_date}", ft.Icons.DATE_RANGE),
    )

    def go_up(e=None):
        if path_stack:
            path_stack.pop()

        current_parent_id["value"] = path_stack[-1] if path_stack else None
        render_chart()

    back_btn = ft.Container(
        bgcolor=card_bg,
        border=ft.border.all(1, border_color),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        ink=True,
        on_click=lambda e: page.app_go("sabtehazine"),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ARROW_BACK_ROUNDED, size=18, color=text_primary),
            ],
            spacing=8,
            tight=True,
        ),
    )

    level_back_btn = ft.Container(
        visible=False,
        bgcolor=soft_bg,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        ink=True,
        on_click=go_up,
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.KEYBOARD_DOUBLE_ARROW_UP_ROUNDED,
                    size=16,
                    color=text_secondary,
                ),
                # ft.Text(
                #     "یک سطح بالاتر",
                #     color=text_secondary,
                #     weight=ft.FontWeight.W_600,
                # ),
            ],
            spacing=6,
            tight=True,
        ),
    )

    breadcrumb_text = ft.Text(
        "",
        size=10,
        weight=ft.FontWeight.W_600,
        color=text_secondary,
        expand=True,
    )

    chart_body = ft.Column(
        spacing=14,
        expand=True,
    )

    chart_container = ft.Container(
        expand=True,
        bgcolor=card_bg,
        border_radius=24,
        padding=22,
        border=ft.border.all(1, border_color),
        shadow=ft.BoxShadow(
            blur_radius=18,
            color="#12000000",
            offset=ft.Offset(0, 4),
        ),
        content=chart_body,
    )

    details_column = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    def build_breadcrumb(parent_id, nodes):
        if parent_id is None:
            return ""

        parts = []
        current = nodes.get(parent_id)

        while current:
            parts.append(current.title)
            current = nodes.get(current.parent_id)

        parts.reverse()

        # حذف تمام سطح اول‌ها (هر نودی که parent نداره)
        filtered = []

        for i, title in enumerate(parts):
            node = nodes.get(parent_id)
        
        current = nodes.get(parent_id)
        stack = []

        while current:
            stack.append(current)
            current = nodes.get(current.parent_id)

        stack.reverse()

        filtered = [
            n.title for n in stack
            if n.parent_id not in (None, 0)
        ]

        return " / ".join(filtered)

    def build_tree(data):
        nodes = {}
        roots = []

        for item in data:
            nodes[item["id"]] = Node(
                item["id"],
                item["title"],
                item.get("id_parent"),
            )

        for item in data:
            node = nodes[item["id"]]
            parent_id = item.get("id_parent")

            if parent_id in (None, 0):
                roots.append(node)
            else:
                parent = nodes.get(parent_id)
                if parent:
                    parent.children.append(node)

        return roots, nodes

    def add_to_ancestors(node_id, amount, nodes):
        current = nodes.get(node_id)
        while current:
            current.total += amount
            current = nodes.get(current.parent_id)

    def get_children_report(parent_id=None):

        all_hazineha = load_all_hazineha()

        all_costs = load_my_costs_by_date(
            page, 
            start_date.isoformat(),
            end_date.isoformat()
        )

        roots, nodes = build_tree(all_hazineha)

        for row in all_costs:
            hazine_id = row.get("id_hazine")
            price = row.get("price", 0) or 0

            if hazine_id in nodes:
                add_to_ancestors(hazine_id, price, nodes)
            else:
                print("WARNING: id_hazine not found in nodes ->", hazine_id)

        if parent_id is None:
            if len(roots) == 1:
                target_nodes = roots[0].children
            else:
                target_nodes = roots
        else:
            parent_node = nodes.get(parent_id)
            if not parent_node:
                return [], nodes
            target_nodes = parent_node.children

        result = []
        for node in target_nodes:
            if node.total > 0:
                result.append(
                    {
                        "id": node.id,
                        "title": node.title,
                        "value": node.total,
                        "has_children": len(node.children) > 0,
                        "parent_id": node.parent_id,
                    }
                )

        return result, nodes

    def handle_item_click(item_index, data):
        if item_index is None:
            return

        if item_index < 0 or item_index >= len(data):
            return

        item = data[item_index]

        if not item.get("has_children"):
            return

        current_parent_id["value"] = item["id"]
        path_stack.append(item["id"])

        render_chart()
          
    def build_pie_chart(data):
        total = sum(item["value"] for item in data) or 1

        def on_pie_event(e):
            if e.type != fch.ChartEventType.TAP_UP:
                return

            section_index = getattr(e, "section_index", None)
            if section_index is None or section_index < 0:
                return

            handle_item_click(section_index, data)

        sections = []
        for i, item in enumerate(data):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            percent = (item["value"] / total) * 100

            sections.append(
                fch.PieChartSection(
                    value=item["value"],
                    title=f"{item['title']}\n{percent:.0f}%",
                    color=color,
                    radius=95,
                    title_style=ft.TextStyle(
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                )
            )

        return fch.PieChart(
            sections=sections,
            sections_space=3,
            center_space_radius=36,
            on_event=on_pie_event,
            expand=True,
        )

    def build_bar_chart(data):
        groups = []
        labels = []

        def on_bar_event(e):
            if e.type != fch.ChartEventType.TAP_UP:
                return

            group_index = getattr(e, "group_index", None)
            if group_index is None or group_index < 0:
                return

            handle_item_click(group_index, data)

        for i, item in enumerate(data):
            color = CHART_COLORS[i % len(CHART_COLORS)]

            groups.append(
                fch.BarChartGroup(
                    x=i,
                    rods=[
                        fch.BarChartRod(
                            from_y=0,
                            to_y=item["value"],
                            width=28,
                            border_radius=8,
                            color=color,
                        )
                    ],
                )
            )

            labels.append(
                fch.ChartAxisLabel(
                    value=i,
                    label=ft.Container(
                        content=ft.Text(
                            item["title"],
                            size=10,
                            color=text_secondary,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        padding=4,
                    ),
                )
            )

        max_y = max((item["value"] for item in data), default=100)

        return fch.BarChart(
            groups=groups,
            border=ft.border.all(1, border_color),
            left_axis=fch.ChartAxis(
                label_size=40,
            #     title=ft.Text("مبلغ"),
                # title_size=8,
            ),
            bottom_axis=fch.ChartAxis(
                labels=labels,
                label_size=40,
            ),
            horizontal_grid_lines=fch.ChartGridLines(
                interval=max(max_y / 5, 1),
                color=border_color,
                width=1,
            ),
            max_y=max_y * 1.2 if max_y > 0 else 100,
            interactive=True,
            on_event=on_bar_event,
            expand=True,
        )

    def set_chart_type(chart_type):
        current_chart_type["value"] = chart_type
        update_chart_switcher()
        render_chart()

    pie_btn = ft.ElevatedButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PIE_CHART_OUTLINE_ROUNDED, size=16),
                ft.Text(t(page, "GantChart_pie"), weight=ft.FontWeight.W_600),
            ],
            spacing=6,
            tight=True,
        ),
        on_click=lambda e: set_chart_type("pie"),
    )

    bar_btn = ft.ElevatedButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.BAR_CHART_ROUNDED, size=16),
                ft.Text(t(page, "GantChart_Bar"), weight=ft.FontWeight.W_600),
            ],
            spacing=6,
            tight=True,
        ),
        on_click=lambda e: set_chart_type("bar"),
    )

    def update_chart_switcher():
        active_style = ft.ButtonStyle(
            bgcolor=PRIMARY,
            color="white",
            elevation=0,
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=14),
        )

        inactive_style = ft.ButtonStyle(
            bgcolor=card_bg,
            color=text_primary,
            elevation=0,
            side=ft.BorderSide(1, border_color),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=14),
        )

        if current_chart_type["value"] == "pie":
            pie_btn.style = active_style
            bar_btn.style = inactive_style
        else:
            bar_btn.style = active_style
            pie_btn.style = inactive_style

        page.update()

    def update_start(e):
        nonlocal start_date
        if start_picker.value:
            start_date = start_picker.value.date()
            start_btn.content = build_filter_button(
                f"{t(page, "date_from")}: {start_date}",
                ft.Icons.CALENDAR_MONTH,
            )
            start_btn.update()

            # current_parent_id["value"] = None
            # path_stack.clear()
            render_chart()

    def update_end(e):
        nonlocal end_date
        if end_picker.value:
            end_date = end_picker.value.date()
            end_btn.content = build_filter_button(
                f"{t(page, "date_to")}: {end_date}",
                ft.Icons.DATE_RANGE,
            )
            end_btn.update()

            # current_parent_id["value"] = None
            # path_stack.clear()
            render_chart()

    start_picker.on_change = update_start
    end_picker.on_change = update_end

    update_chart_switcher()

    def render_chart():
        try:

            data, nodes = get_children_report(current_parent_id["value"])

            breadcrumb_text.value = build_breadcrumb(current_parent_id["value"], nodes)
            level_back_btn.visible = len(path_stack) > 0

            details_column.controls.clear()

            if not data:
                chart_body.controls = [
                    
                    ft.Container(
                        bgcolor=soft_bg,
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ACCOUNT_TREE_OUTLINED,
                                    size=16,
                                    color=text_secondary,
                                ),
                                breadcrumb_text,
                                ft.Container(expand=True),
                                level_back_btn,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.INSERT_CHART_OUTLINED,
                                    size=42,
                                    color="#9CA3AF",
                                ),
                                ft.Text(
                                    t(page, "GantChart_Empty"),
                                    color=text_secondary,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                        ),
                    ),
                ]
                page.update()
                return

            for i, item in enumerate(data):
                details_column.controls.append(
                    ft.Container(
                        padding=14,
                        border_radius=16,
                        bgcolor=soft_bg,
                        border=ft.border.all(1, "#EAEFF5"),
                        content=ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    border_radius=999,
                                    bgcolor=CHART_COLORS[i % len(CHART_COLORS)],
                                ),
                                ft.Text(
                                    item["title"],
                                    expand=True,
                                    color=text_primary,
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(
                                    bgcolor=card_bg,
                                    border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                                    content=ft.Text(
                                        f"{item['value']:.0f}",
                                        weight=ft.FontWeight.W_700,
                                        color=text_primary,
                                    ),
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )

            if current_chart_type["value"] == "pie":
                chart_widget = build_pie_chart(data)
            else:
                chart_widget = build_bar_chart(data)

            chart_body.controls = [
                ft.Container(
                    bgcolor=soft_bg,
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.ACCOUNT_TREE_OUTLINED,
                                size=16,
                                color=text_secondary,
                            ),
                            breadcrumb_text,
                            ft.Container(expand=True),
                            level_back_btn,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    content=chart_widget,
                ),
            ]

            page.update()

        except Exception as ex:
            traceback.print_exc()
            page.update()


    chart_switcher = ft.Row(
        [
            pie_btn,
            bar_btn,
        ],
        spacing=10,
    )

    top_bar = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#F1F3F9", "#D3D6E6"],
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
                ft.Row(
                    [
                        ft.Row(
                            [
                                start_btn,
                                end_btn,
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        back_btn,
                        chart_switcher,
                    ],
                    spacing=14,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            tight=True,
        ),
    )

    render_chart()
    
    screen_width = page.width or 400
    is_mobile = screen_width < 700

    row_controls = [
        ft.Container(
            expand=3,
            content=chart_container,
        )
    ]

    if not is_mobile:
        row_controls.append(
            ft.Container(
                expand=2,
                bgcolor=card_bg,
                border_radius=24,
                border=ft.border.all(1, border_color),
                shadow=ft.BoxShadow(
                    blur_radius=18,
                    color="#12000000",
                    offset=ft.Offset(0, 4),
                ),
                padding=18,
                content=ft.Column(
                    [
                        details_column,
                    ],
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
            )
        )
        
    return ft.View(
        route="/report_view",
        bgcolor=page_bg,
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        top_bar,   # 👈 این خط مهمه (دکمه‌های بالا)

                        ft.Container(
                            expand=True,
                            padding=20,
                            content=ft.Row(
                                row_controls,
                                expand=True,
                                spacing=20,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            )
        ],
)