import flet as ft
from datetime import datetime

from services.supabase_service import (
    supabase,
    get_current_user,
    get_current_workspace_id,
)


# Google Play product ids
# این اسم‌ها باید دقیقاً با Product ID هایی که در Google Play Console می‌سازی یکی باشند
GOOGLE_PLAY_PRODUCTS = {
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

    def go_back(e=None):
        page.app_go("sabtehazine")

    def show_message(message):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            open=True,
        )
        page.update()

    async def start_google_play_purchase(plan: str):
        user = get_current_user()
        if not user:
            show_message("Please login first.")
            return

        product_id = GOOGLE_PLAY_PRODUCTS.get(plan)
        if not product_id:
            show_message("Invalid plan selected.")
            return

        workspace_id = get_current_workspace_id(page)

        show_message(f"Opening Google Play for {product_id}")

        url = (
            f"costio://buy"
            f"?product_id={product_id}"
            f"&plan_type={plan}"
            f"&user_id={user.id}"
        )

        if workspace_id:
            url += f"&workspace_id={workspace_id}"

        await page.launch_url(url)
        
    async def open_google_play_subscription_management(e=None):
        """
        برای مدیریت یا cancel کردن subscription در Google Play.
        این جایگزین Stripe Customer Portal است.
        """
        await page.launch_url(
            "https://play.google.com/store/account/subscriptions"
        )

    async def restore_purchase(e=None):
        """
        بعداً اینجا می‌توانیم restore purchases بگذاریم.
        فعلاً فقط پیام می‌دهد.
        """
        show_message("Restore purchase will be connected to Google Play later.")

    def plan_card(
        title,
        subtitle,
        price,
        features,
        button_text,
        on_click,
        highlighted=False,
        disabled=False,
    ):
        return ft.Container(
            expand=True,
            padding=20,
            border_radius=20,
            bgcolor="#EEF2FF" if highlighted else "#FFFFFF",
            border=ft.border.all(
                2 if highlighted else 1,
                "#2563EB" if highlighted else "#E5E7EB",
            ),
            content=ft.Column(
                [
                    ft.Text(
                        title,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color="#111827",
                    ),
                    ft.Text(
                        subtitle,
                        size=12,
                        color="#6B7280",
                    ),
                    ft.Text(
                        price,
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="#2563EB",
                    ),
                    ft.Divider(),
                    *[
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                                    size=16,
                                    color="#16A34A",
                                ),
                                ft.Text(
                                    item,
                                    size=13,
                                    color="#374151",
                                    expand=True,
                                ),
                            ],
                            spacing=8,
                        )
                        for item in features
                    ],
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        button_text,
                        disabled=disabled,
                        on_click=on_click,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=12),
                            bgcolor="#2563EB" if highlighted else "#111827",
                            color="#FFFFFF",
                        ),
                    ),
                ],
                spacing=10,
            ),
        )

    current_plan_box = ft.Container(
        padding=18,
        border_radius=18,
        bgcolor="#F9FAFB",
        border=ft.border.all(1, "#E5E7EB"),
        content=ft.Column(
            [
                ft.Text(
                    "پلن فعلی شما",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row(
                    [
                        ft.Text("Plan:", size=13, color="#6B7280"),
                        ft.Text(
                            plan_type.upper() if plan_type else "FREE",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#2563EB" if is_active else "#111827",
                        ),
                    ]
                ),
                ft.Row(
                    [
                        ft.Text("Status:", size=13, color="#6B7280"),
                        ft.Text(
                            status,
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color="#16A34A" if is_active else "#DC2626",
                        ),
                    ]
                ),
                ft.Row(
                    [
                        ft.Text("Active until:", size=13, color="#6B7280"),
                        ft.Text(
                            format_date(current_period_end),
                            size=14,
                        ),
                    ]
                ),
                ft.Container(height=6),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "مدیریت اشتراک",
                            icon=ft.Icons.SETTINGS_OUTLINED,
                            disabled=not is_active,
                            on_click=lambda e: page.run_task(
                                open_google_play_subscription_management
                            ),
                        ),
                        ft.TextButton(
                            "Restore purchase",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: page.run_task(restore_purchase),
                        ),
                    ],
                    spacing=10,
                    wrap=True,
                ),
            ],
            spacing=8,
        ),
    )

    free_card = plan_card(
        title="Free",
        subtitle="برای شروع و تست برنامه",
        price="$0",
        features=[
            "ثبت هزینه‌های ساده",
            "یک فضای کاری",
            "امکانات محدود",
        ],
        button_text="پلن فعلی" if not is_active else "Free",
        on_click=lambda e: show_message("You are already on Free plan."),
        disabled=True,
    )

    monthly_card = plan_card(
        title="Monthly",
        subtitle="مناسب استفاده ماهانه",
        price="$4.99 / month",
        features=[
            "ثبت نامحدود هزینه",
            "AI برای تشخیص هزینه",
            "بودجه‌بندی",
            "گزارش‌ها",
            "اشتراک‌گذاری workspace",
        ],
        button_text="خرید ماهانه"
        if plan_type != "monthly" or not is_active
        else "پلن فعلی",
        on_click=lambda e: page.run_task(
            start_google_play_purchase,
            "monthly",
        ),
        highlighted=True,
        disabled=plan_type == "monthly" and is_active,
    )

    yearly_card = plan_card(
        title="Yearly",
        subtitle="به‌صرفه‌تر از ماهانه",
        price="$39.99 / year",
        features=[
            "همه امکانات Monthly",
            "قیمت کمتر",
            "مناسب استفاده طولانی‌مدت",
            "اشتراک‌گذاری workspace",
            "Dashboard پیشرفته",
        ],
        button_text="خرید سالانه"
        if plan_type != "yearly" or not is_active
        else "پلن فعلی",
        on_click=lambda e: page.run_task(
            start_google_play_purchase,
            "yearly",
        ),
        highlighted=False,
        disabled=plan_type == "yearly" and is_active,
    )

    return ft.View(
        route="/subscription_view",
        bgcolor="#F3F4F6",
        controls=[
            ft.AppBar(
                title=ft.Text("اشتراک و پلن‌ها"),
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=go_back,
                ),
                bgcolor="#FFFFFF",
            ),
            ft.Container(
                expand=True,
                padding=20,
                content=ft.Column(
                    [
                        current_plan_box,
                        ft.Text(
                            "انتخاب پلن",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    col={"xs": 12, "md": 4},
                                    content=free_card,
                                ),
                                ft.Container(
                                    col={"xs": 12, "md": 4},
                                    content=monthly_card,
                                ),
                                ft.Container(
                                    col={"xs": 12, "md": 4},
                                    content=yearly_card,
                                ),
                            ],
                            spacing=16,
                            run_spacing=16,
                        ),
                    ],
                    spacing=18,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ),
        ],
    )