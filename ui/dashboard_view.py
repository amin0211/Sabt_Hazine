import flet as ft
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()

from services.supabase_service import get_current_month_dashboard_data


def dashboard_view(page: ft.Page):
    data = get_current_month_dashboard_data()
    today = today_local()
     
    if not data:
        data = {
            "month": today.strftime("%Y-%m"),
            "total_income": 0,
            "total_expense": 0,
            "balance": 0,
            "budget_total": 0,
            "budget_used_percent": 0,
            "income_used_percent": 0,
            "days_passed": today.day,
            "days_in_month": 30,
            "avg_daily_spending": 0,
            "projected_end_month_expense": 0,
            "insights": [],
        }

    def go_back(e):
        page.app_go("sabtehazine")

    def open_budget(e):
        # page.app_go("budget_view")
        page.data["from"] = "dashboard_view"
        page.app_go("budget_view")    

    def open_hazinaha_view(e):
        # page.app_go("budget_view")
        page.data["from"] = "dashboard_view"
        page.app_go("hazinaha_view")    
        
    def progress_color(value):
        if value < 0.7:
            return "#16A34A"
        if value <= 1:
            return "#D97706"
        return "#DC2626"

    def money(value):
        try:
            return f"{float(value):,.0f}"
        except Exception:
            return "0"

    def summary_item(title, value, color="#111827"):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=11, color="#6B7280"),
                    ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color),
                ],
                spacing=2,
            ),
            padding=10,
            border_radius=12,
            bgcolor="#FFFFFF",
            expand=True,
        )

    def progress_section(title, percent, subtitle):
        percent = float(percent or 0)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(title, size=13, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"{percent * 100:.0f}%",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=progress_color(percent),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.ProgressBar(
                        value=min(percent, 1),
                        height=8,
                        color=progress_color(percent),
                        bgcolor="#E5E7EB",
                    ),
                    ft.Text(subtitle, size=11, color="#6B7280"),
                ],
                spacing=6,
            ),
            padding=12,
            border_radius=14,
            bgcolor="#FFFFFF",
        )

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_size=20,
                            tooltip="Back",
                            on_click=go_back,
                        ),
                        ft.Text(
                            data.get("month", ""),
                            size=18,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    [
                        summary_item("Income", money(data.get("total_income"))),
                        summary_item("Expense", money(data.get("total_expense"))),
                        summary_item(
                            "Remaining",
                            money(data.get("balance")),
                            "#16A34A" if float(data.get("balance") or 0) >= 0 else "#DC2626",
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=12,
        ),
        padding=14,
        border_radius=16,
        bgcolor="#F9FAFB",
    )

    progress_card = ft.Column(
        [
            progress_section(
                "Budget usage",
                data.get("budget_used_percent", 0),
                f"{money(data.get('total_expense'))} used from {money(data.get('budget_total'))} budget",
            ),
            progress_section(
                "Income usage",
                data.get("income_used_percent", 0),
                f"{money(data.get('total_expense'))} spent from {money(data.get('total_income'))} income",
            ),
        ],
        spacing=10,
    )

    forecast_card = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Day", size=11, color="#6B7280"),
                        ft.Text(
                            f"{data.get('days_passed', 0)} of {data.get('days_in_month', 0)}",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Text("Avg/day", size=11, color="#6B7280"),
                        ft.Text(
                            money(data.get("avg_daily_spending")),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Text("Forecast", size=11, color="#6B7280"),
                        ft.Text(
                            money(data.get("projected_end_month_expense")),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#DC2626"
                            if float(data.get("projected_end_month_expense") or 0)
                            > float(data.get("budget_total") or 0)
                            and float(data.get("budget_total") or 0) > 0
                            else "#111827",
                        ),
                    ],
                    expand=True,
                ),
            ],
            spacing=8,
        ),
        padding=14,
        border_radius=16,
        bgcolor="#FFFFFF",
    )

    insights = data.get("insights") or []

    if insights:
        insight_controls = [
            ft.Container(
                content=ft.Text(item, size=13, color="#111827"),
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=10,
                bgcolor="#F9FAFB",
            )
            for item in insights
        ]
    else:
        insight_controls = [
            ft.Text(
                "No insights yet. Add income, expenses, and budgets to see analysis.",
                size=12,
                color="#6B7280",
            )
        ]

    insights_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("Quick insights", size=14, weight=ft.FontWeight.BOLD),
                *insight_controls,
            ],
            spacing=8,
        ),
        padding=14,
        border_radius=16,
        bgcolor="#FFFFFF",
    )

    report_buttons = ft.Container(
        content=ft.Column(
            [
                ft.Text("Reports", size=14, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Text("Budget"),
                            on_click=open_budget,
                        ),
                        ft.ElevatedButton(
                            content=ft.Text("Categories"),
                            on_click=open_hazinaha_view,
                        ),                   
                        ft.ElevatedButton(
                            content=ft.Text("Trends"),
                            on_click=lambda e: page.app_go("trend_view"),
                        ),
                    ],
                    spacing=8,
                ),
                # ft.Row(
                #     [
                        # ft.ElevatedButton(
                        #     content=ft.Text("Transactions"),
                        #     on_click=lambda e: page.app_go("transaction_report"),
                        # ),
                    # ],
                    # spacing=8,
                # ),
            ],
            spacing=10,
        ),
        padding=14,
        border_radius=16,
        bgcolor="#FFFFFF",
    )

    content = ft.Container(
        content=ft.Column(
            [
                header,
                progress_card,
                forecast_card,
                insights_card,

                ft.SafeArea(
                    avoid_intrusions_top=False,
                    avoid_intrusions_left=False,
                    avoid_intrusions_right=False,
                    avoid_intrusions_bottom=True,
                    maintain_bottom_view_padding=True,
                    minimum_padding=ft.padding.only(bottom=12),
                    content=report_buttons,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=12,
        bgcolor="#F3F4F6",
        expand=True,
    )

    return ft.View(
        route="/dashboard_view",
        controls=[content],
        bgcolor="#F3F4F6",
        padding=0,
    )