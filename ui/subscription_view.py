import flet as ft
from datetime import datetime

from services.supabase_service import (
    supabase,
    get_current_user,
    get_current_workspace_id,
)


# Store product ids
# این اسم‌ها باید دقیقاً با Product ID هایی که در فروشگاه ساختی یکی باشند

STORE_PRODUCTS = {
    "monthly": "costio_monthly",
    "yearly": "costio_yearly",
}


def get_my_subscription(page=None):
    user = get_current_user()
    if not user:
        return None

    workspace_id = get_current_workspace_id(page)

    q = (
        supabase.table("user_subscriptions")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
    )

    if workspace_id:
        q = q.eq("workspace_id", workspace_id)

    res = q.execute()
    rows = res.data or []

    return rows[0] if rows else None


def is_subscription_active(sub):
    if not sub:
        return False

    if sub.get("status") != "active":
        return False

    current_period_end = sub.get("current_period_end")

    if not current_period_end:
        return True

    try:
        end_date = datetime.fromisoformat(
            current_period_end.replace("Z", "+00:00")
        )
        return end_date > datetime.now(end_date.tzinfo)
    except Exception:
        return True


def format_date(value):
    if not value:
        return "-"

    try:
        return value[:10]
    except Exception:
        return "-"


def subscription_view(page: ft.Page):
    page.title = "Subscription"

    sub = get_my_subscription(page)
    is_active = is_subscription_active(sub)

    plan_type = sub.get("plan_type") if sub else "free"
    status = sub.get("status") if sub else "inactive"
    current_period_end = sub.get("current_period_end") if sub else None

    APP_BG = "#F5F7FB"
    CARD = "#FFFFFF"
    PRIMARY = "#4F46E5"
    TEXT = "#111827"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    GREEN = "#16A34A"
    RED = "#DC2626"

    def go_back(e=None):
        page.app_go("sabtehazine")

    def show_message(message):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            open=True,
        )
        page.update()

    async def start_store_purchase(plan: str):
        user = get_current_user()
        if not user:
            show_message("Please login first.")
            return

        product_id = STORE_PRODUCTS.get(plan)
        if not product_id:
            show_message("Invalid plan selected.")
            return

        workspace_id = get_current_workspace_id(page)

        url = (
            f"costio://buy"
            f"?product_id={product_id}"
            f"&plan_type={plan}"
            f"&user_id={user.id}"
        )

        if workspace_id:
            url += f"&workspace_id={workspace_id}"

        await page.launch_url(url)

    async def open_store_subscription_management(e=None):
        await page.launch_url(
            "https://Amin.Yavari.com/store/account/subscriptions"
        )

    async def restore_purchase(e=None):
        show_message("Restore purchase will be connected later.")

    def status_badge():
        if is_active:
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                border_radius=20,
                bgcolor="#DCFCE7",
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE_ROUNDED,
                            size=14,
                            color=GREEN,
                        ),
                        ft.Text(
                            "Active",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color="#166534",
                        ),
                    ],
                    spacing=5,
                    tight=True,
                ),
            )

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border_radius=20,
            bgcolor="#FEE2E2",
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE_ROUNDED,
                        size=14,
                        color=RED,
                    ),
                    ft.Text(
                        "Inactive",
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color="#991B1B",
                    ),
                ],
                spacing=5,
                tight=True,
            ),
        )

    def info_tile(label, value, icon, color):
        return ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=11),
            border_radius=16,
            bgcolor="#F9FAFB",
            border=ft.border.all(1, "#EEF0F4"),
            content=ft.Row(
                [
                    ft.Container(
                        width=34,
                        height=34,
                        border_radius=12,
                        bgcolor="#EEF2FF",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(
                            icon,
                            size=17,
                            color=color,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                label,
                                size=10,
                                color=MUTED,
                            ),
                            ft.Text(
                                value,
                                size=13,
                                weight=ft.FontWeight.W_700,
                                color=TEXT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    current_plan_box = ft.Container(
        padding=18,
        border_radius=24,
        bgcolor=CARD,
        border=ft.border.all(1, BORDER),
        shadow=ft.BoxShadow(
            blur_radius=18,
            color="#12000000",
            offset=ft.Offset(0, 5),
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=46,
                            height=46,
                            border_radius=16,
                            bgcolor="#EEF2FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.WORKSPACE_PREMIUM_ROUNDED,
                                size=24,
                                color=PRIMARY,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "اشتراک Costio",
                                    size=18,
                                    weight=ft.FontWeight.W_800,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "پلن فعلی و وضعیت دسترسی شما",
                                    size=11,
                                    color=MUTED,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        status_badge(),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        info_tile(
                            "Current plan",
                            plan_type.upper() if plan_type else "FREE",
                            ft.Icons.STAR_ROUNDED,
                            PRIMARY,
                        ),
                        info_tile(
                            "Renewal / End date",
                            format_date(current_period_end),
                            ft.Icons.EVENT_AVAILABLE_ROUNDED,
                            PRIMARY,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "مدیریت اشتراک",
                            icon=ft.Icons.SETTINGS_OUTLINED,
                            disabled=not is_active,
                            on_click=lambda e: page.run_task(
                                open_store_subscription_management
                            ),
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                bgcolor="#111827",
                                color="#FFFFFF",
                                padding=ft.padding.symmetric(
                                    horizontal=16,
                                    vertical=12,
                                ),
                            ),
                        ),
                        ft.TextButton(
                            "Restore purchase",
                            icon=ft.Icons.REFRESH_ROUNDED,
                            on_click=lambda e: page.run_task(restore_purchase),
                            style=ft.ButtonStyle(
                                color=PRIMARY,
                                padding=ft.padding.symmetric(
                                    horizontal=12,
                                    vertical=12,
                                ),
                            ),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                ),
            ],
            spacing=14,
        ),
    )

    def feature_row(text, included=True):
        return ft.Row(
            [
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_ROUNDED
                    if included
                    else ft.Icons.REMOVE_CIRCLE_OUTLINE,
                    size=16,
                    color=GREEN if included else "#9CA3AF",
                ),
                ft.Text(
                    text,
                    size=12,
                    color="#374151" if included else "#9CA3AF",
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def plan_card(
        title,
        subtitle,
        price,
        period,
        # features,
        button_text,
        on_click,
        highlighted=False,
        disabled=False,
        badge_text=None,
    ):
        return ft.Container(
            padding=18,
            border_radius=26,
            bgcolor="#EEF2FF" if highlighted else CARD,
            border=ft.border.all(
                2 if highlighted else 1,
                PRIMARY if highlighted else BORDER,
            ),
            shadow=ft.BoxShadow(
                blur_radius=20,
                color="#16000000" if highlighted else "#0A000000",
                offset=ft.Offset(0, 6),
            ),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        title,
                                        size=19,
                                        weight=ft.FontWeight.W_800,
                                        color=TEXT,
                                    ),
                                    ft.Text(
                                        subtitle,
                                        size=11,
                                        color=MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Container(
                                visible=badge_text is not None,
                                padding=ft.padding.symmetric(
                                    horizontal=9,
                                    vertical=4,
                                ),
                                border_radius=20,
                                bgcolor="#DBEAFE" if highlighted else "#F3F4F6",
                                content=ft.Text(
                                    badge_text or "",
                                    size=10,
                                    weight=ft.FontWeight.W_700,
                                    color=PRIMARY if highlighted else MUTED,
                                ),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.Text(
                                price,
                                size=28,
                                weight=ft.FontWeight.W_900,
                                color=PRIMARY if highlighted else TEXT,
                            ),
                            ft.Container(
                                margin=ft.margin.only(top=10),
                                content=ft.Text(
                                    period,
                                    size=12,
                                    color=MUTED,
                                ),
                            ),
                        ],
                        spacing=5,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Divider(
                        height=12,
                        color="#DDE3F0" if highlighted else BORDER,
                    ),
                    # ft.Column(
                    #     [feature_row(item) for item in features],
                    #     spacing=8,
                    # ),
                    ft.Container(height=4),
                    ft.ElevatedButton(
                        button_text,
                        disabled=disabled,
                        on_click=on_click,
                        width=999,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=14),
                            bgcolor=PRIMARY if highlighted else "#111827",
                            color="#FFFFFF",
                            padding=ft.padding.symmetric(vertical=13),
                        ),
                    ),
                ],
                spacing=12,
            ),
        )

    monthly_card = plan_card(
        title="Monthly",
        subtitle="مناسب استفاده منظم ماهانه",
        price="$4.99",
        period="/ month",
        # features=[
        #     "ثبت نامحدود هزینه‌ها",
        #     "تشخیص هوشمند هزینه با AI",
        #     "بودجه‌بندی و گزارش ماهانه",
        #     "Workspace اشتراکی",
        # ],
        button_text="پلن فعلی"
        if plan_type == "monthly" and is_active
        else "خرید ماهانه",
        on_click=lambda e: page.run_task(
            start_store_purchase,
            "monthly",
        ),
        highlighted=True,
        disabled=plan_type == "monthly" and is_active,
        badge_text="Popular",
    )

    yearly_card = plan_card(
        title="Yearly",
        subtitle="به‌صرفه‌تر برای استفاده طولانی",
        price="$39.99",
        period="/ year",
        # features=[
        #     "همه امکانات پلن Monthly",
        #     "هزینه کمتر نسبت به پرداخت ماهانه",
        #     "مناسب خانواده یا پروژه‌های طولانی",
        #     "دسترسی کامل به گزارش‌ها",
        # ],
        button_text="پلن فعلی"
        if plan_type == "yearly" and is_active
        else "خرید سالانه",
        on_click=lambda e: page.run_task(
            start_store_purchase,
            "yearly",
        ),
        highlighted=False,
        disabled=plan_type == "yearly" and is_active,
        badge_text="Best value",
    )

    header = ft.Container(
        padding=ft.padding.only(left=18, right=18, top=18, bottom=16),
        bgcolor=CARD,
        border_radius=ft.border_radius.only(
            bottom_left=24,
            bottom_right=24,
        ),
        shadow=ft.BoxShadow(
            blur_radius=12,
            color="#10000000",
            offset=ft.Offset(0, 3),
        ),
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                    icon_size=18,
                    icon_color=TEXT,
                    on_click=go_back,
                ),
                ft.Column(
                    [
                        ft.Text(
                            "اشتراک و پلن‌ها",
                            size=18,
                            weight=ft.FontWeight.W_800,
                            color=TEXT,
                        ),
                        ft.Text(
                            "پلن مناسب خود را انتخاب کنید",
                            size=11,
                            color=MUTED,
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.Container(
                    width=38,
                    height=38,
                    border_radius=14,
                    bgcolor="#EEF2FF",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.LOCK_ROUNDED,
                        size=20,
                        color=PRIMARY,
                    ),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    return ft.View(
        route="/subscription_view",
        bgcolor=APP_BG,
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        header,
                        ft.Container(
                            expand=True,
                            padding=ft.padding.symmetric(
                                horizontal=16,
                                vertical=16,
                            ),
                            content=ft.Column(
                                [
                                    current_plan_box,
                                    ft.Row(
                                        [
                                            ft.Column(
                                                [
                                                    ft.Text(
                                                        "انتخاب پلن",
                                                        size=20,
                                                        weight=ft.FontWeight.W_800,
                                                        color=TEXT,
                                                    ),
                                                    ft.Text(
                                                        "برای فعال کردن امکانات کامل Costio یکی از پلن‌ها را انتخاب کنید.",
                                                        size=11,
                                                        color=MUTED,
                                                    ),
                                                ],
                                                spacing=2,
                                                expand=True,
                                            ),
                                        ],
                                    ),
                                    ft.ResponsiveRow(
                                        [
                                            ft.Container(
                                                col={"xs": 12, "md": 6},
                                                content=monthly_card,
                                            ),
                                            ft.Container(
                                                col={"xs": 12, "md": 6},
                                                content=yearly_card,
                                            ),
                                        ],
                                        spacing=14,
                                        run_spacing=14,
                                    ),
                                    ft.Container(
                                        padding=ft.padding.symmetric(
                                            horizontal=12,
                                            vertical=10,
                                        ),
                                        border_radius=16,
                                        bgcolor="#FFFFFF",
                                        border=ft.border.all(1, BORDER),
                                        content=ft.Row(
                                            [
                                                ft.Icon(
                                                    ft.Icons.INFO_OUTLINE_ROUNDED,
                                                    size=16,
                                                    color=MUTED,
                                                ),
                                                ft.Text(
                                                    "مدیریت پرداخت و لغو اشتراک از طریق تنظیمات حساب انجام می‌شود.",
                                                    size=11,
                                                    color=MUTED,
                                                    expand=True,
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ),
                                ],
                                spacing=16,
                                scroll=ft.ScrollMode.AUTO,
                                expand=True,
                            ),
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
            )
        ],
    )