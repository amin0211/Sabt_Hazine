import flet as ft
import asyncio
from queue import Queue, Empty
from datetime import date, datetime
from services.utils import today_local, safe_picker_date, local_date_iso

from services.i18n import t
async def prepare_ios_recording_safe(page):
    try:
        if page.platform != ft.PagePlatform.IOS:
            return {"ok": False, "reason": "not_ios"}

        from services.voice_service_ios import prepare_recording as prepare_ios_recording
        return await prepare_ios_recording(page)

    except Exception as ex:
        print("[IOS PREPARE SAFE ERROR]", ex, flush=True)
        return {"ok": False, "error": str(ex)}


async def warmup_ios_recording_safe(page):
    try:
        if page.platform != ft.PagePlatform.IOS:
            return {"ok": False, "reason": "not_ios"}

        from services.voice_service_ios import warmup_recording as warmup_ios_recording
        return await warmup_ios_recording(page)

    except Exception as ex:
        print("[IOS WARMUP SAFE ERROR]", ex, flush=True)
        return {"ok": False, "error": str(ex)}



# from services.supabase_service import (
#     upsert_category_learning,
#     update_category_learning_embedding,
#     sign_out_user,
#     get_members,
#     add_member,
#     get_financial_summary,
#     get_income_transactions_by_month,
#     get_current_user,
#     get_my_profile,
#     get_my_workspaces,
#     update_my_profile,
#     set_current_workspace,
#     get_opening_balance_total,
# )



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

    controller_cache = {"obj": controller}

    def get_controller():
        if controller_cache["obj"] is None:
            import controllers.sabte_hazine_controller as sabtehazine_controller
            controller_cache["obj"] = sabtehazine_controller

        return controller_cache["obj"]

    parser_cache = {"obj": parse_expense_}

    def get_parser():
        if parser_cache["obj"] is None:
            from services.parser_service import parse_expense
            parser_cache["obj"] = parse_expense

        return parser_cache["obj"]    


    def get_page_members_cached():
        page.data = page.data or {}

        cached = page.data.get("sabtehazine_members_cache")

        if cached is not None:
            return cached

        try:
            members = supabase_service.get_members() or []
        except Exception as ex:
            print("[MEMBERS CACHE] get_members error:", ex, flush=True)
            members = []

        page.data["sabtehazine_members_cache"] = members

        return members

    def import_parser_sync():
        from services.parser_service import parse_expense
        return parse_expense


    async def warmup_parser_after_page_load():
        try:
            await asyncio.sleep(1.5)

            if parser_cache["obj"] is None:
                import time
                t0 = time.perf_counter()

                parser_cache["obj"] = await asyncio.to_thread(import_parser_sync)

                t1 = time.perf_counter()
                print(
                    f"[PARSER WARMUP] parser_service imported in background = {t1 - t0:.3f}s",
                    flush=True,
                )

            # ✅ warmup members/accounts cache
            try:
                import time
                from services.openai_service import (
                    get_member_names_cached,
                    get_account_names_cached,
                )

                t0 = time.perf_counter()
                await asyncio.to_thread(get_member_names_cached)
                t1 = time.perf_counter()
                print(f"[OPENAI WARMUP] members cached = {t1 - t0:.3f}s", flush=True)

                t0 = time.perf_counter()
                await asyncio.to_thread(get_account_names_cached)
                t1 = time.perf_counter()
                print(f"[OPENAI WARMUP] accounts cached = {t1 - t0:.3f}s", flush=True)

                from services.parser_service import load_leaf_hazineha_cached
                t0 = time.perf_counter()
                await asyncio.to_thread(load_leaf_hazineha_cached)
                t1 = time.perf_counter()

                print(f"[PARSER WARMUP] leaf categories cached = {t1 - t0:.3f}s", flush=True)

            except Exception as ex:
                print("OPENAI CACHE WARMUP ERROR:", ex, flush=True)

        except Exception as ex:
            print("PARSER WARMUP ERROR:", ex, flush=True)




    async def prepare_ios_voice_after_mount():
        try:
            await asyncio.sleep(0.8)

            if page.platform != ft.PagePlatform.IOS:
                return

            if page.data.get("ios_voice_prepared"):
                print("[MIC PREP] skipped: already prepared", flush=True)
                return

            print("[MIC PREP] warming up iOS voice in background", flush=True)

            warmup_result = await warmup_ios_recording_safe(page)

            print("[MIC PREP] iOS voice warmup result:", warmup_result, flush=True)

            if not isinstance(warmup_result, dict) or not warmup_result.get("ok"):
                print("[MIC PREP] warmup failed; continuing to prepare anyway", flush=True)
            else:
                print("[MIC PREP] warmup ok", flush=True)

            await asyncio.sleep(0.2)

            print("[MIC PREP] preparing iOS voice recorder after warmup", flush=True)

            prepare_result = await prepare_ios_recording_safe(page)


            print("[MIC PREP] iOS voice prepare result:", prepare_result, flush=True)

            if isinstance(prepare_result, dict) and prepare_result.get("ok"):
                page.data["ios_voice_prepared"] = True

                mic_button_box.opacity = 1
                mic_icon.color = PRIMARY
                safe_page_update(page)

        except Exception as ex:
            print("[MIC PREP] iOS voice prepare failed:", ex, flush=True)

    # chat_column = ft.Column(.    IOS
    #     spacing=10,
    #     expand=True,
    #     scroll=ft.ScrollMode.ALWAYS,
    # )

    chat_column = ft.ListView(
        expand=True,
        spacing=10,
        padding=0,
        auto_scroll=False,
    )

    initial_loading = ft.Container(
        # expand=True,        IOS
        height=260,
        alignment=ft.Alignment.CENTER,
        padding=ft.padding.only(top=80),
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=34, height=34, stroke_width=3, color=PRIMARY),
                ft.Text(
                    "در حال بارگذاری اطلاعات...",
                    size=13,
                    color="#6B7280",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            tight=True,
        ),
    )

    chat_column.controls.append(initial_loading)


    def refresh_after_edit():
        page.data["sabtehazine_changed"] = True
        page.data.pop("sabtehazine_view_cache", None)

        load_filtered()
        refresh_summary()
        safe_page_update(page)

    def ensure_current_workspace():
        page.data = page.data or {}

        ws_id = page.data.get("current_workspace_id")

        if ws_id and str(ws_id) != "None":
            return ws_id

        print("[ENSURE WS] fallback DB get_my_profile called", flush=True)

        profile = supabase_service.get_my_profile()
        if not profile:
            return None

        ws_id = profile.get("current_workspace_id")

        if not ws_id or str(ws_id) == "None":
            return None

        page.data["current_workspace_id"] = ws_id
        return ws_id

    async def check_user_session():
        try:
            stored_user_id = await page.shared_preferences.get("user_id")

            auth_user = supabase_service.get_current_user()
            current_user_id = auth_user.id if auth_user else None

            print("[SESSION CHECK] stored_user_id:", stored_user_id, flush=True)
            print("[SESSION CHECK] current_user_id:", current_user_id, flush=True)

            if stored_user_id and current_user_id and str(stored_user_id) != str(current_user_id):
                print(
                    "[SESSION CHECK] user mismatch detected. NOT clearing tokens.",
                    flush=True,
                )

                page.data = page.data or {}
                page.data["session_mismatch"] = True

                # فعلاً نه clear کن، نه login بفرست.
                return

        except Exception as ex:
            print("[SESSION CHECK ERROR]", ex, flush=True)


    def remove_empty_state():
        chat_column.controls = [
            c for c in chat_column.controls
            if getattr(c, "data", None) != "empty_state"
        ]
    def build_empty_state():
        box = ft.Container(
            # expand=True,    IOS 
            height=260,  
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
        MENU_WIDTH = 180
        ITEM_HEIGHT = 42
        HEADER_HEIGHT = 28

        def menu_header(title):
            return ft.PopupMenuItem(
                disabled=True,
                height=28,
                content=ft.Container(
                    width=180,
                    height=24,
                    alignment=ft.Alignment.CENTER_RIGHT,
                    content=ft.Text(
                        title,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#64748B",
                        rtl=True,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ),
            )

        def menu_item(label, icon, on_click, color="#111827"):
            return ft.PopupMenuItem(
                height=42,
                icon=icon,
                content=ft.Container(
                    width=180,
                    height=36,
                    alignment=ft.Alignment.CENTER_RIGHT,
                    content=ft.Text(
                        label,
                        color=color,
                        size=14,
                        rtl=True,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ),
                on_click=on_click,
            )

        return ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            # tooltip="منو",
            items=[
                # ---------------- برنامه مالی ----------------
                menu_header(t(page, "menu_financial_plan")),

                menu_item(
                    t(page, "Income"),
                    ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    lambda e: page.app_go("income"),
                ),

                menu_item(
                    t(page, "fixed_expenses_view"),
                    ft.Icons.EVENT_REPEAT_OUTLINED,
                    lambda e: page.app_go("fixed_expenses_view"),
                ),

                menu_item(
                    t(page, "Budget"),
                    ft.Icons.SAVINGS_OUTLINED,
                    lambda e: page.app_go("budget_view"),
                ),

                menu_item(
                    t(page, "bank_reconcile_view"),
                    ft.Icons.SYNC_ALT_OUTLINED,
                    lambda e: page.app_go("bank_reconcile_view"),
                ),

                ft.PopupMenuItem(),

                # ---------------- اطلاعات پایه ----------------
                menu_header(t(page, "menu_basic_info")),

                menu_item(
                    t(page, "Accounts"),
                    ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                    lambda e: page.app_go("accounts"),
                ),

                menu_item(
                    t(page, "Categories"),
                    ft.Icons.ACCOUNT_TREE_OUTLINED,
                    lambda e: open_hazineha_from_menu(),
                ),

                menu_item(
                    t(page, "members"),
                    ft.Icons.GROUPS_OUTLINED,
                    lambda e: page.app_go("members"),
                ),

                menu_item(
                    t(page, "workspaces_view"),
                    ft.Icons.WORKSPACES_OUTLINED,
                    lambda e: page.app_go("workspaces_view"),
                ),

                ft.PopupMenuItem(),

                # ---------------- گزارش‌ها ----------------
                menu_header(t(page, "menu_reports")),

                menu_item(
                    t(page, "dashboard"),
                    ft.Icons.DASHBOARD_OUTLINED,
                    lambda e: page.app_go("dashboard_view"),
                ),

                menu_item(
                    t(page, "cost_report_view"),
                    ft.Icons.RECEIPT_LONG_OUTLINED,
                    lambda e: page.app_go("cost_report_view"),
                ),

                menu_item(
                    t(page, "GanttChart"),
                    ft.Icons.INSERT_CHART_OUTLINED,
                    lambda e: page.app_go("GanttChart_view"),
                ),

                # فعلاً اگر صفحه تطبیق حساب بانکی نداری، این بخش را کامنت نگه دار
                # menu_item(
                #     "تطبیق حساب بانکی",
                #     ft.Icons.SYNC_ALT_OUTLINED,
                #     lambda e: page.app_go("bank_reconcile_view"),
                # ),

                ft.PopupMenuItem(),

                # ---------------- حساب کاربری ----------------
                menu_header(t(page, "menu_user_account")),

                menu_item(
                    t(page, "profile"),
                    ft.Icons.PERSON_OUTLINE,
                    lambda e: page.app_go("profile"),
                ),

                # menu_item(
                #     t(page, "suscription"),
                #     ft.Icons.CARD_MEMBERSHIP_OUTLINED,
                #     lambda e: page.app_go("subscription_view"),
                #     color="#DC2626",
                # ),

                menu_item(
                    t(page, "logout"),
                    ft.Icons.LOGOUT_ROUNDED,
                    logout,
                    color="#DC2626",
                ),
            ],
        )


    async def logout_async(e=None):
        try:
            await asyncio.to_thread(supabase_service.sign_out_user)
        except Exception as ex:
            print("logout error:", ex, flush=True)

        try:
            await page.shared_preferences.clear()
            print("[LOGOUT] shared_preferences cleared", flush=True)
        except Exception as ex:
            print("shared_preferences clear error:", ex, flush=True)

        page.data = {}
        page.app_go("login")


    def logout(e):
        page.run_task(logout_async, e)


    STOP_GRACE_SECONDS = 0.6
    MIN_RECORD_SECONDS = 0.75
    MAX_RECORD_SECONDS = 20

    voice_state = {
        "is_starting": False,
        "is_recording": False,
        "is_stopping": False,
        "started_at": None,
        "recording_token": 0,
        "stop_requested_by_user": False,
    }

    async def auto_stop_recording_after_timeout(token):
        try:
            await asyncio.sleep(MAX_RECORD_SECONDS)

            if token != voice_state.get("recording_token"):
                print("[MIC UI] auto-stop ignored: old token", flush=True)
                return

            if not voice_state.get("is_recording"):
                print("[MIC UI] auto-stop ignored: not recording", flush=True)
                return

            if voice_state.get("is_stopping"):
                print("[MIC UI] auto-stop ignored: already stopping", flush=True)
                return

            print("[MIC UI] auto-stop: max recording time reached", flush=True)

            recording_status_text.value = "زمان ضبط تمام شد؛ در حال تبدیل صدا به متن..."
            recording_status_text.visible = True

            mic_icon.name = ft.Icons.HOURGLASS_TOP_ROUNDED
            mic_icon.color = "#FFFFFF"
            mic_button_box.bgcolor = "#F97316"

            safe_page_update(page)

            await stop_after_minimum_duration(extra_delay=0)

        except Exception as ex:
            print("[MIC UI] auto-stop error:", ex, flush=True)

            
    def reset_mic_ui():
        recording_pulse["active"] = False
        recording_pulse["strong"] = False

        recording_dot.opacity = 0
        recording_dot.width = 10
        recording_dot.height = 10

        mic_icon.name = ft.Icons.MIC_ROUNDED
        mic_icon.color = PRIMARY
        mic_button_box.bgcolor = "#EEF2FF"

        recording_status_text.value = ""
        recording_status_text.visible = False

        safe_page_update(page)

        
    async def stop_after_minimum_duration(extra_delay=STOP_GRACE_SECONDS):
        if voice_state.get("is_stopping"):
            return

        if not voice_state.get("is_recording"):
            return

        voice_state["is_stopping"] = True

        started_at = voice_state.get("started_at")
        elapsed = 0

        if started_at:
            elapsed = (datetime.now() - started_at).total_seconds()

        if elapsed < MIN_RECORD_SECONDS:
            wait_time = MIN_RECORD_SECONDS - elapsed
            print(f"[MIC UI] wait minimum before stop = {wait_time:.2f}s", flush=True)
            await asyncio.sleep(wait_time)

        if extra_delay and extra_delay > 0:
            print(f"[MIC UI] stop grace delay = {extra_delay:.2f}s", flush=True)

            recording_status_text.value = "در حال پایان ضبط..."
            recording_status_text.visible = True

            mic_icon.name = ft.Icons.HOURGLASS_TOP_ROUNDED
            mic_icon.color = "#FFFFFF"
            mic_button_box.bgcolor = "#F97316"

            safe_page_update(page)

            await asyncio.sleep(extra_delay)

        await stop_and_check_voice()
        

    async def start_recording_and_mark_ready():
        try:
            from services.voice_service_router import start_recording

            print("[MIC UI] native start requested", flush=True)
            result = await start_recording(page)
            print("[MIC UI] native start result:", result, flush=True)

        except Exception as ex:
            print("[MIC UI] start recording error:", ex, flush=True)
            result = {
                "ok": False,
                "error": str(ex),
            }

        voice_state["is_starting"] = False

        if not isinstance(result, dict) or not result.get("ok"):
            print("[MIC UI] native start failed; reset", flush=True)

            voice_state["is_recording"] = False
            voice_state["is_stopping"] = False
            voice_state["started_at"] = None

            reset_mic_ui()
            return

        voice_state["is_recording"] = True
        voice_state["started_at"] = datetime.now()

        current_token = voice_state.get("recording_token")
        page.run_task(auto_stop_recording_after_timeout, current_token)

        mic_icon.name = ft.Icons.STOP_ROUNDED
        mic_icon.color = "#FFFFFF"
        mic_button_box.bgcolor = "#DC2626"

        recording_status_text.value = "در حال ضبط... برای توقف دوباره بزنید"
        recording_status_text.visible = True

        safe_page_update(page)

        print("[MIC UI] native recording started", flush=True)

    def on_mic_tap(e):
        if send_state.get("loading"):
            return

        if page.platform == ft.PagePlatform.IOS and not page.data.get("ios_voice_prepared"):
            print("[MIC UI] ignored tap: iOS voice is not prepared yet", flush=True)
            return

        if voice_state.get("is_starting") or voice_state.get("is_stopping"):
            print("[MIC UI] ignored tap: busy", flush=True)
            return

        # Tap دوم: stop
        if voice_state.get("is_recording"):
            print("[MIC UI] tap -> stop requested", flush=True)

            voice_state["stop_requested_by_user"] = True

            recording_status_text.value = "در حال پایان ضبط..."
            recording_status_text.visible = True

            mic_icon.name = ft.Icons.HOURGLASS_TOP_ROUNDED
            mic_icon.color = "#FFFFFF"
            mic_button_box.bgcolor = "#F97316"

            safe_page_update(page)

            page.run_task(stop_after_minimum_duration, STOP_GRACE_SECONDS)
            return



        # Tap اول: start
        print("[MIC UI] tap -> start", flush=True)

        voice_state["is_starting"] = True
        voice_state["is_recording"] = False
        voice_state["is_stopping"] = False
        voice_state["started_at"] = None

        voice_state["recording_token"] += 1
        voice_state["stop_requested_by_user"] = False

        current_token = voice_state["recording_token"]

        recording_pulse["active"] = True
        page.run_task(pulse_recording_dot)

        mic_icon.name = ft.Icons.STOP_ROUNDED
        mic_icon.color = "#FFFFFF"
        mic_button_box.bgcolor = "#DC2626"

        recording_status_text.value = "در حال ضبط... برای توقف دوباره بزنید"
        recording_status_text.visible = True

        safe_page_update(page)

        page.run_task(start_recording_and_mark_ready)

        
    async def stop_and_check_voice():
        try:
            print("[MIC UI] stop_and_check_voice", flush=True)

            recording_pulse["active"] = False
            recording_pulse["strong"] = False
            recording_dot.opacity = 0

            recording_status_text.value = "در حال تبدیل صدا به متن..."
            recording_status_text.visible = True

            mic_icon.name = ft.Icons.HOURGLASS_TOP_ROUNDED
            mic_icon.color = "#FFFFFF"
            mic_button_box.bgcolor = "#F97316"

            safe_page_update(page)

            from services.voice_service_router import stop_recording

            result = await stop_recording(page)

            print("[MIC UI] stop result:", result, flush=True)

            q.put(("voice", result))

            await check_voice_result()

        except Exception as ex:
            print("[MIC UI] stop recording error:", ex, flush=True)

        finally:
            voice_state["is_starting"] = False
            voice_state["is_recording"] = False
            voice_state["is_stopping"] = False
            voice_state["started_at"] = None
            voice_state["stop_requested_by_user"] = False

            voice_state["recording_token"] += 1

            reset_mic_ui()

            if page.platform == ft.PagePlatform.IOS:
                page.data["ios_voice_prepared"] = False
                mic_button_box.opacity = 0.45
                safe_page_update(page)
                page.run_task(prepare_ios_voice_after_mount)


    def ask_user_to_choose_category(page: ft.Page, parsed_result: dict, on_confirm):
        suggestions = parsed_result.get("suggestions", [])

        if not suggestions:
            on_confirm(parsed_result)
            return

        dlg = ft.AlertDialog(modal=True)

        choice_state = {
            "submitted": False
        }

        buttons = []

        def disable_dialog_buttons():
            for btn in buttons:
                btn.disabled = True

            if dlg.actions:
                for action in dlg.actions:
                    action.disabled = True

            dlg.content = ft.Column(
                [
                    ft.ProgressRing(width=30, height=30, stroke_width=3),
                    ft.Text(
                        "در حال ذخیره هزینه...",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "لطفاً چند لحظه صبر کنید",
                        size=11,
                        color="#6B7280",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                tight=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

            page.update()
            
        def choose(cat):
            if choice_state["submitted"]:
                return

            choice_state["submitted"] = True

            # جلوگیری از دوبار کلیک
            disable_dialog_buttons()

            parsed_result["category_id"] = cat["category_id"]
            parsed_result["category_title"] = cat["category_title"]
            parsed_result["matched"] = True

            new_category_id = parsed_result.get("category_id")
            raw_text = parsed_result.get("temp_hazine") or parsed_result.get("title", "")

            async def learn_after_choice():
                try:
                    if not new_category_id:
                        return

                    from services.parser_service import normalize_text

                    normalized_text = normalize_text(raw_text)

                    await asyncio.to_thread(
                        supabase_service.upsert_category_learning,
                        raw_text=raw_text,
                        normalized_text=normalized_text,
                        category_id=new_category_id,
                        source="user_corrected",
                        embedding_text=normalized_text,
                    )

                    print(
                        f"[CATEGORY LEARNING] saved raw={raw_text!r} category_id={new_category_id}",
                        flush=True,
                    )

                except Exception as ex:
                    print("CATEGORY LEARNING ERROR:", ex, flush=True)

            # یادگیری در background
            page.run_task(learn_after_choice)

            # بستن سریع dialog و ادامه ذخیره هزینه
            dlg.open = False
            page.update()

            on_confirm(parsed_result)

        def close_dlg(e=None):
            if choice_state["submitted"]:
                return

            choice_state["submitted"] = True
            disable_dialog_buttons()

            parsed_result["category_id"] = None
            parsed_result["category_title"] = None
            parsed_result["matched"] = False

            dlg.open = False
            page.update()

            on_confirm(parsed_result)

        for cat in suggestions[:3]:
            buttons.append(
                ft.ElevatedButton(
                    cat["category_title"],
                    width=220,
                    on_click=lambda e, c=cat: choose(c),
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

        dlg.actions = [
            ft.TextButton(
                "بستن و ذخیره بدون دسته‌بندی",
                on_click=close_dlg,
            )
        ]

        dlg.actions_alignment = ft.MainAxisAlignment.END

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        page.update()

    def perf_log(tag, t0=None, extra=""):
        import time
        now = time.perf_counter()

        if t0 is None:
            print(f"[SAVE PERF] {tag} START {extra}", flush=True)
            return now

        print(f"[SAVE PERF] {tag} = {now - t0:.3f}s {extra}", flush=True)
        return now
            
    async def handle_send():
        total_t0 = perf_log("HANDLE_SEND")

        if send_state.get("loading"):
            print("[SAVE PERF] ignored: already loading", flush=True)
            return

        text = (input_field.value or "").strip()

        if not text:
            print("[SAVE PERF] ignored: empty text", flush=True)
            return

        print(f"[SAVE PERF] INPUT text_len={len(text)} text={text!r}", flush=True)

        t0 = perf_log("SET_BUSY_ANALYZE")
        set_page_busy(True, "در حال تحلیل و ثبت هزینه...")
        perf_log("SET_BUSY_ANALYZE", t0)

        try:
            cost_id = getattr(input_field, "data", None)

            if cost_id:
                print(f"[SAVE PERF] EDIT_MODE cost_id={cost_id}", flush=True)

                t0 = perf_log("EDIT_COST")
                updated = await asyncio.to_thread(get_controller().edit_cost, cost_id, text)
                perf_log("EDIT_COST", t0)

                t0 = perf_log("UPDATE_UI_EDIT")
                update_ui(cost_id, updated)
                perf_log("UPDATE_UI_EDIT", t0)

                input_field.value = ""
                input_field.data = None

                t0 = perf_log("FOCUS_AFTER_EDIT")
                await input_field.focus()
                perf_log("FOCUS_AFTER_EDIT", t0)

                t0 = perf_log("PAGE_UPDATE_AFTER_EDIT")
                safe_page_update(page)
                perf_log("PAGE_UPDATE_AFTER_EDIT", t0)

                perf_log("HANDLE_SEND_TOTAL_EDIT", total_t0)
                return

            # 1) Parser import/cache
            t0 = perf_log("GET_PARSER")
            parser_func = get_parser()
            perf_log("GET_PARSER", t0)

            # 2) Parse expense
            t0 = perf_log("LOAD_MEMBERS_FOR_PARSE")
            members_for_parse = await asyncio.to_thread(get_page_members_cached)
            perf_log(
                "LOAD_MEMBERS_FOR_PARSE",
                t0,
                extra=f"count={len(members_for_parse or [])}",
            )

            t0 = perf_log("PARSE_EXPENSE")
            parsed = await asyncio.to_thread(
                parser_func,
                text,
                members_for_parse,
            )
            perf_log(
                "PARSE_EXPENSE",
                t0,
                extra=(
                    f"matched={parsed.get('matched')} "
                    f"suggestions={len(parsed.get('suggestions') or [])} "
                    f"cat={parsed.get('category_title')} "
                    f"member={parsed.get('member_name')} "
                    f"member_id={parsed.get('member_id')}"
                ),
            )
            # متن اصلی کاربر برای ذخیره در DB
            original_text = text

            # فعلاً هیچ normalize روی متن ذخیره‌شده انجام نده
            # title/text/temp_hazine باید همان چیزی باشد که کاربر گفته
            parsed["text"] = original_text
            parsed["raw_text"] = original_text

            print(
                f"[SAVE PERF] TEXT_FOR_DB raw_text={original_text!r}",
                flush=True,
            )

            print(f"[SAVE PERF] PARSED_RESULT={parsed}", flush=True)


            save_state = {
                "saving": False
            }

            async def continue_after_choice(final_parsed):
                save_total_t0 = perf_log("CONTINUE_AFTER_CHOICE")

                if save_state["saving"]:
                    print("[SAVE PERF] ignored: already saving", flush=True)
                    return

                save_state["saving"] = True

                t0 = perf_log("SET_BUSY_SAVE")
                set_page_busy(True, "در حال ذخیره هزینه...")
                perf_log("SET_BUSY_SAVE", t0)

                try:
                    # controller import/cache
                    t0 = perf_log("GET_CONTROLLER")
                    controller_obj = get_controller()
                    perf_log("GET_CONTROLLER", t0)

                    # save_new
                    t0 = perf_log("SAVE_NEW")

                    if not final_parsed.get("category_id"):
                        root_hazine_id = None

                        if page and isinstance(page.data, dict):
                            root_hazine_id = page.data.get("root_hazine_id")

                        if root_hazine_id:
                            final_parsed["category_id"] = root_hazine_id
                            final_parsed["category_title"] = (
                                page.data.get("root_hazine_title")
                                or final_parsed.get("category_title")
                                or "Uncategorized"
                            )
                            final_parsed["matched"] = False

                    new_row = await asyncio.to_thread(controller_obj.save_new, final_parsed, page)
                    perf_log(
                        "SAVE_NEW",
                        t0,
                        extra=f"id={new_row.get('id') if isinstance(new_row, dict) else None}"
                    )

                    print(f"[SAVE PERF] NEW_ROW={new_row}", flush=True)

                    # remove empty state
                    t0 = perf_log("REMOVE_EMPTY_STATE")
                    remove_empty_state()
                    perf_log("REMOVE_EMPTY_STATE", t0)

                    # create message
                    t0 = perf_log("CREATE_MESSAGE")
                    msg = create_message(new_row)
                    perf_log("CREATE_MESSAGE", t0)

                    # insert in chat
                    t0 = perf_log("INSERT_MESSAGE_UI")
                    chat_column.controls.insert(0, msg)
                    perf_log("INSERT_MESSAGE_UI", t0)

                    # summary background
                    t0 = perf_log("START_REFRESH_SUMMARY_TASK")
                    page.run_task(refresh_summary_after_save_async)
                    perf_log("START_REFRESH_SUMMARY_TASK", t0)

                    # clear input
                    t0 = perf_log("CLEAR_INPUT")
                    input_field.value = ""
                    input_field.data = None
                    perf_log("CLEAR_INPUT", t0)

                    # focus
                    t0 = perf_log("FOCUS_INPUT")
                    await input_field.focus()
                    perf_log("FOCUS_INPUT", t0)

                    # flags
                    t0 = perf_log("UPDATE_PAGE_FLAGS")
                    page.data["sabtehazine_changed"] = False
                    page.data["sabtehazine_loaded"] = True
                    perf_log("UPDATE_PAGE_FLAGS", t0)

                    # final page update
                    t0 = perf_log("FINAL_PAGE_UPDATE")
                    safe_page_update(page)
                    perf_log("FINAL_PAGE_UPDATE", t0)

                    perf_log("CONTINUE_AFTER_CHOICE_TOTAL", save_total_t0)

                finally:
                    save_state["saving"] = False

                    t0 = perf_log("SET_BUSY_FALSE")
                    set_page_busy(False)
                    perf_log("SET_BUSY_FALSE", t0)

            if not parsed.get("matched") and parsed.get("suggestions"):
                print("[SAVE PERF] CATEGORY_SUGGESTION_DIALOG_OPEN", flush=True)

                t0 = perf_log("SET_BUSY_FALSE_BEFORE_CATEGORY_DIALOG")
                set_page_busy(False)
                perf_log("SET_BUSY_FALSE_BEFORE_CATEGORY_DIALOG", t0)

                ask_user_to_choose_category(
                    page,
                    parsed,
                    lambda final_parsed: page.run_task(
                        continue_after_choice,
                        final_parsed,
                    ),
                )
            else:
                await continue_after_choice(parsed)

            perf_log("HANDLE_SEND_TOTAL", total_t0)

        except Exception as ex:
            print("SEND COST ERROR:", ex, flush=True)
            perf_log("HANDLE_SEND_ERROR_TOTAL", total_t0)

            set_page_busy(False)

            snack = ft.SnackBar(
                content=ft.Text(f"خطا در ثبت هزینه: {ex}"),
                bgcolor="#DC2626",
            )

            page.overlay.append(snack)
            snack.open = True
            safe_page_update(page)
            
    def send_message(e):
        if send_state.get("loading"):
            return

        page.run_task(handle_send)


    input_field = ft.TextField(
        hint_text=t(page, "hint_text_InsertHazine"),
        expand=True,

        # مهم برای بزرگ شدن خودکار
        multiline=True,
        min_lines=1,
        max_lines=4,

        border_radius=16,
        border_color="transparent",
        bgcolor=CARD,
        text_size=14,
        content_padding=ft.padding.only(left=28, right=12, top=10, bottom=10),
        cursor_color=PRIMARY,

        # در multiline، Enter ممکن است خط جدید بدهد
        # پس send با دکمه انجام شود
        on_submit=send_message,
    )

    page.data = page.data or {}


    if page.data.get("sabtehazine_start_date"):
        start_date = safe_picker_date(page.data["sabtehazine_start_date"], page)
    else:
        start_date = today_local(page)

    if page.data.get("sabtehazine_end_date"):
        end_date = safe_picker_date(page.data["sabtehazine_end_date"], page)
    else:
        end_date = today_local(page)
        
    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)

    if start_picker not in page.overlay:
        page.overlay.append(start_picker)

    if end_picker not in page.overlay:
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
        content=build_filter_button(
            f"{t(page, 'date_from')}: {start_date.isoformat()}",
            ft.Icons.CALENDAR_MONTH,
        ),
    )

    end_btn = ft.GestureDetector(
        on_tap=lambda e: open_end(e),
        content=build_filter_button(
            f"{t(page, 'date_to')}: {end_date.isoformat()}",
            ft.Icons.DATE_RANGE,
        ),
    )

    def open_start(e):
        start_picker.open = True
        page.update()

    def open_end(e):
        end_picker.open = True
        page.update()

    def load_filtered():
        workspace_id = ensure_current_workspace()
        if not workspace_id:
            chat_column.controls.clear()
            chat_column.controls.append(build_empty_state())
            refresh_summary()
            page.update()
            return

        res = supabase_service.load_my_costs_by_date(
            page, 
            start_date.isoformat(),
            end_date.isoformat(),
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(build_empty_state())
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        refresh_summary()
        page.update()

    toast_state = {
        "snack": None,
    }


    def show_app_message(
        message: str,
        kind: str = "error",
        duration: int = 2500,
    ):
        """
        kind: error | warning | success | info
        """

        colors = {
            "error": "#DC2626",
            "warning": "#F97316",
            "success": "#16A34A",
            "info": PRIMARY,
        }

        icons = {
            "error": ft.Icons.ERROR_OUTLINE_ROUNDED,
            "warning": ft.Icons.WARNING_AMBER_ROUNDED,
            "success": ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
            "info": ft.Icons.INFO_OUTLINE_ROUNDED,
        }

        bgcolor = colors.get(kind, "#DC2626")
        icon = icons.get(kind, ft.Icons.ERROR_OUTLINE_ROUNDED)

        try:
            old_snack = toast_state.get("snack")
            if old_snack:
                old_snack.open = False
        except Exception:
            pass

        snack = ft.SnackBar(
            duration=duration,
            bgcolor=bgcolor,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=ft.margin.only(left=16, right=16, bottom=90),
            content=ft.Row(
                [
                    ft.Icon(
                        icon,
                        size=20,
                        color="#FFFFFF",
                    ),
                    ft.Text(
                        message,
                        size=13,
                        color="#FFFFFF",
                        weight=ft.FontWeight.W_600,
                        expand=True,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        toast_state["snack"] = snack

        if snack not in page.overlay:
            page.overlay.append(snack)

        snack.open = True
        safe_page_update(page)

    def update_start(e):
        nonlocal start_date, end_date

        if not start_picker.value:
            return

        new_start = safe_picker_date(start_picker.value, page)

        if new_start > end_date:
            start_picker.value = start_date

            show_app_message(
                "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.",
                kind="warning",
            )
            return

        start_date = new_start
        start_picker.value = start_date

        page.data["sabtehazine_start_date"] = start_date.isoformat()

        start_btn.content = build_filter_button(
            f"{t(page, 'date_from')}: {start_date.isoformat()}",
            ft.Icons.CALENDAR_MONTH,
        )
        start_btn.update()

        load_filtered()

    def update_end(e):
        nonlocal start_date, end_date

        if not end_picker.value:
            return

        new_end = safe_picker_date(end_picker.value, page)

        if new_end < start_date:
            end_picker.value = end_date

            show_app_message(
                "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.",
                kind="warning",
            )
            return

        end_date = new_end
        end_picker.value = end_date

        page.data["sabtehazine_end_date"] = end_date.isoformat()

        end_btn.content = build_filter_button(
            f"{t(page, 'date_to')}: {end_date.isoformat()}",
            ft.Icons.DATE_RANGE,
        )
        end_btn.update()

        load_filtered()


    start_picker.on_change = update_start
    end_picker.on_change = update_end


    summary_balance = ft.Text(
        "$0.00",
        size=16,
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
        size=9,
        color="#6B7280",
    )

    active_user_email_text = ft.Text(
        page.data.get("current_user_email") or page.data.get("user_email") or "",
        size=9,
        color="#6B7280",
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.LEFT,
    )


    def get_current_workspace_title_for_ui():
        page.data = page.data or {}

        ws_id = page.data.get("current_workspace_id")
        ws_title = page.data.get("current_workspace_title")

        if ws_id and ws_title and ws_title != "Workspace":
            return ws_title

        workspaces = page.data.get("workspaces") or []

        if not workspaces:
            try:
                workspaces = supabase_service.get_my_workspaces() or []
                page.data["workspaces"] = workspaces
            except Exception as ex:
                print("GET WORKSPACES FOR TITLE ERROR:", ex)
                workspaces = []

        if ws_id and workspaces:
            current_ws = next(
                (w for w in workspaces if str(w.get("id")) == str(ws_id)),
                None
            )

            if current_ws:
                title = current_ws.get("title") or "Workspace"
                page.data["current_workspace_title"] = title
                return title

        return ws_title or "Workspace"


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

    def open_workspace_picker(e):
        workspaces = page.data.get("workspaces") or supabase_service.get_my_workspaces()
        page.data["workspaces"] = workspaces

        current_workspace_id = page.data.get("current_workspace_id")

        dlg = ft.AlertDialog(modal=True)

        def close():
            dlg.open = False
            page.update()

        def select(ws):
            page.data["current_workspace_id"] = ws["id"]
            page.data["current_workspace_title"] = ws.get("title") or "Workspace"
            page.data["workspaces"] = workspaces

            page.data["root_hazine_id"] = ws.get("root_hazine_id")
            page.data["root_hazine_title"] = ws.get("title") or "Workspace"


            try:
                supabase_service.set_current_workspace(ws["id"])
            except Exception as ex:
                print("set current workspace error:", ex)


            dlg.open = False
            load_filtered()
            refresh_summary()
            page.update()

        def workspace_row(ws):
            is_selected = str(ws.get("id")) == str(current_workspace_id)

            access_type = ws.get("access_type") or "owner"

            if access_type == "owner":
                subtitle = "فضای کاری شخصی شما"
                icon = ft.Icons.HOME_ROUNDED
                badge = "Owner"
                badge_bg = "#DCFCE7"
                badge_color = "#166534"
            else:
                shared_by = ws.get("shared_by_name") or ws.get("shared_by_email") or "نامشخص"
                subtitle = f"اشتراکی از: {shared_by}"
                icon = ft.Icons.GROUP_ROUNDED
                badge = ws.get("role") or "Shared"
                badge_bg = "#E0F2FE"
                badge_color = "#0369A1"

            return ft.Container(
                ink=True,
                on_click=lambda e, w=ws: select(w),
                padding=ft.padding.symmetric(horizontal=10, vertical=9),
                border_radius=16,
                bgcolor="#EEF2FF" if is_selected else "#FFFFFF",
                border=ft.border.all(
                    1,
                    "#818CF8" if is_selected else "#E5E7EB"
                ),
                content=ft.Row(
                    [
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=14,
                            bgcolor="#FFFFFF" if is_selected else "#F8FAFC",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                icon,
                                size=21,
                                color="#4F46E5" if is_selected else "#64748B",
                            ),
                        ),

                        ft.Column(
                            [
                                # Title
                                ft.Text(
                                    ws.get("title") or "Workspace",
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color="#0F172A",
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),

                                # 👇 Subtitle + Owner در یک ردیف
                                ft.Row(
                                    [
                                        # Subtitle (سمت چپ)
                                        ft.Text(
                                            subtitle,
                                            size=10,
                                            color="#64748B",
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            expand=True,   # 👈 خیلی مهم
                                        ),
                                        # 👇 تیک انتخاب
                                        ft.Icon(
                                            ft.Icons.CHECK_CIRCLE_ROUNDED,
                                            size=16,
                                            color="#22C55E",
                                            visible=is_selected,
                                        ),

                                        # 👇 Owner (badge)
                                        ft.Container(
                                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                            border_radius=12,
                                            bgcolor=badge_bg,
                                            content=ft.Text(
                                                badge,
                                                size=8,
                                                weight=ft.FontWeight.W_600,
                                                color=badge_color,
                                            ),
                                        ),

                                    ],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        )

                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        dlg.title = ft.Row(
            [
                ft.Container(
                    width=38,
                    height=38,
                    border_radius=13,
                    bgcolor="#EEF2FF",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.WORKSPACES_ROUNDED,
                        color="#4F46E5",
                        size=21,
                    ),
                ),
                ft.Column(
                    [
                        ft.Text(
                            "انتخاب Workspace",
                            size=15,
                            weight=ft.FontWeight.W_800,
                            color="#0F172A",
                        ),
                        ft.Text(
                            "فضای کاری ثبت هزینه‌ها را انتخاب کن",
                            size=10,
                            color="#64748B",
                        ),
                    ],
                    spacing=1,
                    expand=True,
                ),
            ],
            spacing=10,
        )

        dlg.content = ft.Container(
            width=360,
            height=380,
            content=ft.Column(
                [
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        border_radius=14,
                        bgcolor="#F8FAFC",
                        border=ft.border.all(1, "#E2E8F0"),
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.INFO_OUTLINE_ROUNDED,
                                    size=15,
                                    color="#64748B",
                                ),
                                ft.Text(
                                    "هزینه‌ها، بودجه، درآمد و گزارش‌ها بر اساس Workspace انتخاب‌شده فیلتر می‌شوند.",
                                    size=10,
                                    color="#64748B",
                                    expand=True,
                                ),
                            ],
                            spacing=7,
                        ),
                    ),

                    ft.ListView(
                        controls=[workspace_row(ws) for ws in workspaces],
                        spacing=8,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        )

        dlg.actions = [
            ft.TextButton(
                "Manage",
                on_click=lambda e: page.app_go("workspaces_view"),
            ),
            ft.TextButton(
                "Close",
                on_click=lambda e: close(),
            ),
        ]

        dlg.actions_alignment = ft.MainAxisAlignment.END

        if dlg not in page.overlay:
            page.overlay.append(dlg)

        dlg.open = True
        page.update()

    def get_active_user_email_for_ui():
        page.data = page.data or {}

        return (
            page.data.get("current_user_email")
            or page.data.get("user_email")
            or ""
        )
        
    def money(v):
        try:
            return f"${float(v):,.2f}"
        except:
            return "$0.00"

    def get_total_account_balance_for_ui():
        try:
            balances = supabase_service.get_account_balances()

            total = 0

            for b in balances:
                account_id = b.get("account_id") or b.get("out_account_id")

                balance_value = b.get("balance")

                if balance_value is None:
                    balance_value = b.get("out_balance")

                if account_id:
                    total += float(balance_value or 0)

            return total

        except Exception as ex:
            print("GET TOTAL ACCOUNT BALANCE ERROR:", ex)
            return 0

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
                                        ft.Text(
                                            "Account Balance",
                                            size=11,
                                            color="#6B7280",
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),

                                        summary_month_text,

                                        ft.Container(
                                            expand=True,
                                            alignment=ft.Alignment.CENTER_RIGHT,
                                            content=active_user_email_text,
                                        ),
                                    ],
                                    spacing=3,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                summary_balance,
                            ],
                            spacing=2,
                            expand=True,
                        ),

                        ft.Container(
                            margin=ft.margin.only(top=18),
                            width=38,
                            height=38,
                            border_radius=13,
                            bgcolor="#EEF2FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.PopupMenuButton(
                                icon=ft.Icons.MENU_ROUNDED,
                                icon_size=20,
                                tooltip="Menu",
                                items=build_main_menu().items,
                            ),
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.START,
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
        current_ym = today_local(page).strftime("%Y-%m")
        summary_month_text.value = f"( {current_ym} )"

        active_user_email_text.value = get_active_user_email_for_ui()
        
        workspace_id = ensure_current_workspace()

        if not workspace_id:
            summary_balance.value = "$0.00"
            summary_income.value = "$0.00"
            summary_expense.value = "$0.00"
            summary_left.value = "$0.00"
            safe_page_update(page)
            return

        try:
            today_ = today_local(page)
            month_start = date(today_.year, today_.month, 1)

            data = supabase_service.get_financial_summary(
                month_start.isoformat(),
                today_.isoformat(),
                workspace_id=workspace_id,
                page=page,
            )
            income_rows = supabase_service.get_income_transactions_by_month(
                current_ym,
                workspace_id=workspace_id,
                page=page,
            )

            total_income = sum(
                float(row.get("amount") or 0)
                for row in income_rows
                if row.get("status") == "confirmed"
            )

            expense = float(data.get("expense") or 0)

            total_account_balance = get_total_account_balance_for_ui()

            summary_balance.value = money(total_account_balance)
            summary_income.value = money(total_income)
            summary_expense.value = money(expense)
            summary_left.value = money(total_income - expense)
            
            
        except Exception as ex:
            print("refresh_summary error:", ex)

        safe_page_update(page)

    def get_summary_values_for_ui():
        current_ym = today_local(page).strftime("%Y-%m")
        today_ = today_local(page)
        month_start = date(today_.year, today_.month, 1)

        workspace_id = ensure_current_workspace()
        if not workspace_id:
            return None

        financial_data = supabase_service.get_financial_summary(
            month_start.isoformat(),
            today_.isoformat(),
            workspace_id=workspace_id,
            page=page,
        )

        income_rows = supabase_service.get_income_transactions_by_month(
            current_ym,
            workspace_id=workspace_id,
            page=page,
        )

        total_account_balance = get_total_account_balance_for_ui()

        total_income = sum(
            float(row.get("amount") or 0)
            for row in income_rows
            if row.get("status") == "confirmed"
        )

        expense = float(financial_data.get("expense") or 0)

        return {
            "current_ym": current_ym,
            "total_income": total_income,
            "expense": expense,
            "total_account_balance": float(total_account_balance or 0),
        }

    async def refresh_summary_after_save_async():
        await asyncio.sleep(0.1)

        try:
            data = await asyncio.to_thread(get_summary_values_for_ui)

            if not data:
                return

            total_income = data["total_income"]
            expense = data["expense"]
            total_account_balance = data["total_account_balance"]
            current_ym = data["current_ym"]

            summary_month_text.value = f"( {current_ym} )"
            summary_balance.value = money(total_account_balance)
            summary_income.value = money(total_income)
            summary_expense.value = money(expense)
            summary_left.value = money(total_income - expense)

            safe_page_update(page)

            print("SUMMARY REFRESHED AFTER SAVE OR EDIT")

        except Exception as ex:
            print("refresh_summary_after_save_async error:", ex)


    async def refresh_summary_async():
        await asyncio.sleep(0.05)

        try:
            await asyncio.to_thread(refresh_summary)
        except Exception as ex:
            print("refresh_summary_async error:", ex)

    def request_summary_refresh_from_outside():
        print("REQUEST SUMMARY REFRESH FROM OUTSIDE")
        page.run_task(refresh_summary_async)

    page.data["sabtehazine_request_summary_refresh"] = request_summary_refresh_from_outside
            
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

    async def learn_category_after_save(raw_text, category_id):
        try:
            from services.parser_service import normalize_text
            from services.openai_service import get_embedding

            normalized_text = normalize_text(raw_text)

            learning_row = await asyncio.to_thread(
                supabase_service.upsert_category_learning,
                raw_text=raw_text,
                normalized_text=normalized_text,
                category_id=category_id,
                source="user_corrected",
                embedding_text=normalized_text,
            )

            if learning_row:
                embedding_vector = await asyncio.to_thread(
                    get_embedding,
                    normalized_text,
                )

                if embedding_vector:
                    await asyncio.to_thread(
                        supabase_service.update_category_learning_embedding,
                        learning_row["id"],
                        embedding_vector,
                    )

        except Exception as ex:
            print("CATEGORY LEARNING BACKGROUND ERROR:", ex)
                            
    def create_message(row):

        root_hazine_id = None
        if page and isinstance(page.data, dict):
            root_hazine_id = page.data.get("root_hazine_id")

        is_root_fallback = (
            root_hazine_id
            and row.get("id_hazine")
            and str(row.get("id_hazine")) == str(root_hazine_id)
        )

        is_invalid = (not row.get("id_hazine")) or is_root_fallback
        
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
                page.data["sabtehazine_changed"] = False
                page.data["sabtehazine_loaded"] = True

                old_category_id = row.get("id_hazine")
                new_category_id = updated_data.get("id_hazine")

                updated_row = get_controller().edit_cost(row["id"], updated_data)

                updated_row["id_hazine"] = updated_data.get("id_hazine")
                updated_row["category_title"] = updated_data.get("category_title")
                updated_row["member_id"] = updated_data.get("member_id")
                updated_row["member_name"] = updated_data.get("member_name", "")
                updated_row["account_id"] = updated_data.get("account_id")
                updated_row["price"] = updated_data.get("price")
                updated_row["title"] = updated_data.get("title")
                updated_row["date_cost"] = updated_data.get("date_cost")

                # فقط همین آیتم را در لیست آپدیت کن
                update_ui(row["id"], updated_row)

                # بعد از ویرایش، جدول/کارت بالای صفحه را رفرش کن
                page.run_task(refresh_summary_after_save_async)

                if new_category_id and new_category_id != old_category_id:
                    raw_text = (
                        row.get("temp_hazine")
                        or updated_data.get("title")
                        or row.get("title", "")
                    )

                    page.run_task(
                        learn_category_after_save,
                        raw_text,
                        new_category_id,
                    )

                safe_page_update(page)

            from ui.edit_cost_dialog import open_edit_cost_dialog

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

        workspace_id = await asyncio.to_thread(ensure_current_workspace)

        if not workspace_id:
            chat_column.controls.clear()
            chat_column.controls.append(build_empty_state())
            safe_page_update(page)
            return

        res = await asyncio.to_thread(
            supabase_service.load_my_costs_by_date,
            page,
            start_date.isoformat(),
            end_date.isoformat(),
        )

        chat_column.controls.clear()

        if not res:
            chat_column.controls.append(build_empty_state())
        else:
            for row in res:
                chat_column.controls.append(create_message(row))

        safe_page_update(page)

            
    async def load_initial_page_async():
        if page.data.get("sabtehazine_loading"):
            print("[SABTEH LOAD] ignored: already loading", flush=True)
            return

        page.data["sabtehazine_loading"] = True

        await asyncio.sleep(0.05)

        try:
            chat_column.controls.clear()
            chat_column.controls.append(initial_loading)
            safe_page_update(page)

            import time
            total_t0 = time.perf_counter()

            print("========== SABTEH load_initial_page_async START ==========")

            # 0) Workspace
            t0 = time.perf_counter()
            workspace_id = await asyncio.to_thread(ensure_current_workspace)
            t1 = time.perf_counter()
            print(f"[LOAD STEP 0] ensure_current_workspace = {t1 - t0:.3f}s")

            if not workspace_id:
                t0 = time.perf_counter()

                chat_column.controls.clear()
                chat_column.controls.append(build_empty_state())

                summary_balance.value = "$0.00"
                summary_income.value = "$0.00"
                summary_expense.value = "$0.00"
                summary_left.value = "$0.00"

                safe_page_update(page)

                t1 = time.perf_counter()
                print(f"[LOAD STEP EMPTY] build empty state + update = {t1 - t0:.3f}s")
                print("========== SABTEH load_initial_page_async END: no workspace ==========")
                return

            # 1) Prepare summary dates
            t0 = time.perf_counter()

            today_ = today_local(page)
            current_ym = today_.strftime("%Y-%m")
            month_start = date(today_.year, today_.month, 1)

            summary_month_text.value = f"( {current_ym} )"
            active_user_email_text.value = get_active_user_email_for_ui()

            t1 = time.perf_counter()
            print(f"[LOAD STEP 1] prepare summary dates = {t1 - t0:.3f}s")

            # 2) Run DB calls in parallel
            t0 = time.perf_counter()

            cost_task = asyncio.to_thread(
                supabase_service.load_my_costs_by_date,
                page,
                start_date.isoformat(),
                end_date.isoformat(),
            )

            financial_task = asyncio.to_thread(
                supabase_service.get_financial_summary,
                month_start.isoformat(),
                today_.isoformat(),
                workspace_id,
                page,
            )

            income_task = asyncio.to_thread(
                supabase_service.get_income_transactions_by_month,
                current_ym,
                workspace_id=workspace_id,
                page=page,
            )

            account_balance_task = asyncio.to_thread(
                get_total_account_balance_for_ui,
            )

            res, financial_data, income_rows, total_account_balance = await asyncio.gather(
            cost_task,
            financial_task,
            income_task,
            account_balance_task,
            )

            t1 = time.perf_counter()
            print(
                f"[LOAD STEP 2] parallel DB calls = {t1 - t0:.3f}s | "
                f"cost_rows={len(res or [])}, income_rows={len(income_rows or [])}, "
                f"financial={financial_data}, account_balance={total_account_balance}",
                flush=True,
            )

            # 3) Clear chat list
            t0 = time.perf_counter()
            chat_column.controls.clear()
            t1 = time.perf_counter()
            print(f"[LOAD STEP 3] clear chat_column = {t1 - t0:.3f}s")

            # 4) Build cost message controls
            t0 = time.perf_counter()

            if not res:
                chat_column.controls.append(build_empty_state())
                built_count = 0
            else:
                built_count = 0
                for row in res[:80]:
                    msg_t0 = time.perf_counter()
                    chat_column.controls.append(create_message(row))
                    msg_t1 = time.perf_counter()

                    built_count += 1

                    if built_count <= 5 or built_count % 20 == 0:
                        print(
                            f"[LOAD STEP 4.ITEM] create_message #{built_count} "
                            f"id={row.get('id')} time={msg_t1 - msg_t0:.4f}s"
                        )

            t1 = time.perf_counter()
            print(f"[LOAD STEP 4] build messages = {t1 - t0:.3f}s | built={built_count}")

            # 8) Calculate summary values
            t0 = time.perf_counter()

            total_income = sum(
                float(row.get("amount") or 0)
                for row in income_rows
                if row.get("status") == "confirmed"
            )

            expense = float(financial_data.get("expense") or 0)

            summary_balance.value = money(total_account_balance)
            summary_income.value = money(total_income)
            summary_expense.value = money(expense)
            summary_left.value = money(total_income - expense)

            t1 = time.perf_counter()
            print(
                f"[LOAD STEP 8] calculate summary values = {t1 - t0:.3f}s | "
                f"income={total_income}, expense={expense}, account_balance={total_account_balance}"
            )

            # 9) Update flags
            t0 = time.perf_counter()

            page.data["sabtehazine_changed"] = False
            page.data["sabtehazine_loaded"] = True

            t1 = time.perf_counter()
            print(f"[LOAD STEP 9] update page.data flags = {t1 - t0:.3f}s")

            # 10) Final UI update
            t0 = time.perf_counter()
            safe_page_update(page)
            t1 = time.perf_counter()
            print(f"[LOAD STEP 10] safe_page_update = {t1 - t0:.3f}s")

            total_t1 = time.perf_counter()
            print(f"========== SABTEH load_initial_page_async TOTAL = {total_t1 - total_t0:.3f}s ==========")

        except Exception as ex:
            print("load_initial_page_async error:", ex, flush=True)

            chat_column.controls.clear()
            chat_column.controls.append(
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.padding.only(top=80),
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.ERROR_OUTLINE,
                                size=42,
                                color="#DC2626",
                            ),
                            ft.Text(
                                "خطا در بارگذاری اطلاعات",
                                size=15,
                                weight=ft.FontWeight.W_700,
                                color="#DC2626",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "لطفاً دوباره وارد صفحه شوید یا اینترنت را بررسی کنید.",
                                size=11,
                                color="#6B7280",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.ElevatedButton(
                                "تلاش دوباره",
                                on_click=lambda e: page.run_task(load_initial_page_async),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        tight=True,
                    ),
                )
            )

            page.data["sabtehazine_loaded"] = False
            page.data["sabtehazine_changed"] = True

            safe_page_update(page)
        finally:
            page.data["sabtehazine_loading"] = False

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
                        err = data.get("error") or "Voice recording failed."
                        print("[VOICE RESULT ERROR]", err, flush=True)

                        user_message = "ضبط صدا انجام نشد. لطفاً دوباره امتحان کنید."

                        if "permission" in err.lower() or "mic" in err.lower():
                            user_message = "دسترسی میکروفون فعال نیست. لطفاً اجازه میکروفون را بررسی کنید."
                        elif "timeout" in err.lower():
                            user_message = "زمان پاسخ‌گویی طولانی شد. لطفاً دوباره تلاش کنید."
                        elif "server" in err.lower() or "network" in err.lower():
                            user_message = "ارتباط با سرور برقرار نشد. اینترنت را بررسی کنید و دوباره تلاش کنید."

                        show_app_message(
                            user_message,
                            kind="warning",
                            duration=3500,
                        )

                        return

                    text = (data.get("text") or "").strip()

                    if not text:
                        print("[VOICE RESULT] empty text", flush=True)

                        show_app_message(
                            "صدایی تشخیص داده نشد. کمی واضح‌تر صحبت کنید و دوباره امتحان کنید.",
                            kind="info",
                            duration=3000,
                        )

                        return

                    try:
                        from services.parser_service import normalize_voice_money_text

                        normalized_text = normalize_voice_money_text(text)

                        if normalized_text and normalized_text != text:
                            print(
                                f"[VOICE MONEY NORMALIZED] raw={text!r} normalized={normalized_text!r}",
                                flush=True,
                            )
                            text = normalized_text

                    except Exception as ex:
                        print("[VOICE MONEY NORMALIZE ERROR]", ex, flush=True)

                    input_field.value = text
                    input_field.update()
                    safe_page_update(page)
                    return

            await asyncio.sleep(0.1)



    # input_field.value = "MIC ERROR: پاسخی از سرور دریافت نشد"
    # input_field.focus()
    # page.update()
    
    page.data = page.data or {}
    page.data["is_recording"] = False
    
    #۱۱۱۱۱۱ page.run_task(check_user_session)

    busy_overlay = ft.GestureDetector(
        visible=False,
        on_tap=lambda e: None,
        content=ft.Container(
            expand=True,
            bgcolor="#66000000",
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                width=260,
                padding=ft.padding.symmetric(horizontal=18, vertical=18),
                border_radius=22,
                bgcolor="#FFFFFF",
                shadow=ft.BoxShadow(
                    blur_radius=18,
                    color="#22000000",
                    offset=ft.Offset(0, 6),
                ),
                content=ft.Column(
                    [
                        ft.ProgressRing(width=34, height=34, stroke_width=3, color=PRIMARY),
                        ft.Text(
                            "در حال ثبت هزینه...",
                            size=14,
                            weight=ft.FontWeight.W_700,
                            color="#111827",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "لطفاً چند لحظه صبر کنید",
                            size=11,
                            color="#6B7280",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
            ),
        ),
    )


    def set_page_busy(is_busy: bool, message: str = "در حال ثبت هزینه..."):
        send_state["loading"] = is_busy
        busy_overlay.visible = is_busy

        try:
            busy_overlay.content.content.content.controls[1].value = message
        except Exception as ex:
            print("SET BUSY MESSAGE ERROR:", ex)

        input_field.disabled = is_busy

        if is_busy:
            mic_button_box.opacity = 0.45
        else:
            if page.platform == ft.PagePlatform.IOS and not page.data.get("ios_voice_prepared"):
                mic_button_box.opacity = 0.45
            else:
                mic_button_box.opacity = 1
                
        if is_busy:
            send_btn_ui.content = ft.ProgressRing(
                width=18,
                height=18,
                stroke_width=2,
                color=PRIMARY,
            )
            send_btn_ui.bgcolor = "#E5E7EB"
            send_btn_ui.on_click = None
        else:
            send_btn_ui.content = ft.Icon(
                ft.Icons.ARROW_UPWARD_ROUNDED,
                size=18,
                color=PRIMARY,
            )
            send_btn_ui.bgcolor = "#F3F4F6"
            send_btn_ui.on_click = send_message

            input_field.disabled = False
            if page.platform == ft.PagePlatform.IOS and not page.data.get("ios_voice_prepared"):
                mic_button_box.opacity = 0.45
            else:
                mic_button_box.opacity = 1  

        safe_page_update(page)

    send_state = {
        "loading": False
    }



    def build_send_button():
        return ft.Container(
            width=46,
            height=46,
            border_radius=15,
            bgcolor="#F3F4F6",
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=send_message,
            content=ft.Icon(
                ft.Icons.ARROW_UPWARD_ROUNDED,
                size=22,
                color=PRIMARY,
            ),
        )


    send_btn_ui = build_send_button()

    mic_icon = ft.Icon(ft.Icons.MIC_ROUNDED, color=PRIMARY, size=22)

    mic_button_box = ft.Container(
        width=46,
        height=46,
        border_radius=15,
        bgcolor="#EEF2FF",
        alignment=ft.Alignment.CENTER,
        content=mic_icon,
    )



    if page.platform == ft.PagePlatform.IOS and not page.data.get("ios_voice_prepared"):
        mic_button_box.opacity = 0.45

    mic_button = ft.GestureDetector(
        on_tap=on_mic_tap,
        mouse_cursor=ft.MouseCursor.CLICK,
        content=mic_button_box,
    )


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

    recording_status_text = ft.Text(
        "",
        size=11,
        color="#DC2626",
        weight=ft.FontWeight.W_600,
        visible=False,
        text_align=ft.TextAlign.CENTER,
    )

    input_row = ft.Container(
        bgcolor=card_color,
        border=ft.border.only(top=ft.BorderSide(1, border_color)),
        padding=ft.padding.only(left=12, right=12, top=8, bottom=6),

        content=ft.Column(
            [
                recording_status_text,

                ft.Row(
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
            ],
            spacing=5,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    async def refresh_summary_after_mount_async():
        await asyncio.sleep(0.4)

        try:
            refresh_summary()
            print("SUMMARY REFRESHED AFTER MOUNT")
        except Exception as ex:
            print("refresh_summary_after_mount_async error:", ex)
                

    # if page.data.get("sabtehazine_changed") or not page.data.get("sabtehazine_loaded"):
    #     page.run_task(load_initial_page_async)
    # else:
    #     page.run_task(refresh_summary_after_mount_async)
    
    # page.run_task(warmup_parser_after_page_load)

    async def process_fixed_expenses_after_mount():
        await asyncio.sleep(1.2)

        try:
            page.data = page.data or {}

            workspace_id = ensure_current_workspace()
            if not workspace_id:
                print("[FIXED EXPENSES AUTO] skipped: no workspace", flush=True)
                return

            today_key = today_local(page).isoformat()
            fixed_key = f"{workspace_id}:{today_key}"

            if page.data.get("fixed_expenses_checked_key") == fixed_key:
                print("[FIXED EXPENSES AUTO] skipped: already checked today", flush=True)
                return

            page.data["fixed_expenses_checked_key"] = fixed_key

            if not hasattr(supabase_service, "process_due_fixed_expenses"):
                print("[FIXED EXPENSES AUTO] skipped: process_due_fixed_expenses not found", flush=True)
                return

            result = await asyncio.to_thread(
                supabase_service.process_due_fixed_expenses,
                page,
            )

            print("[FIXED EXPENSES AUTO] result:", result, flush=True)

            created_count = 0

            if isinstance(result, dict):
                created_count = int(result.get("created_count") or 0)

            if created_count <= 0:
                return

            print(
                f"[FIXED EXPENSES AUTO] {created_count} cost rows created; refreshing UI",
                flush=True,
            )

            page.data["sabtehazine_changed"] = False
            page.data["sabtehazine_loaded"] = True

            await load_messages_async()
            await refresh_summary_after_save_async()

        except Exception as ex:
            print("[FIXED EXPENSES AUTO ERROR]", ex, flush=True)


    if (
        page.data.get("sabtehazine_changed")
        or not page.data.get("sabtehazine_loaded")
    ) and not page.data.get("sabtehazine_loading"):
        page.run_task(load_initial_page_async)
    else:
        page.run_task(refresh_summary_after_mount_async)

    page.run_task(process_fixed_expenses_after_mount)
    page.run_task(prepare_ios_voice_after_mount)


    if isinstance(page.data, dict) and page.data.get("reopen_edit_cost_dialog"):
        page.data["reopen_edit_cost_dialog"] = False

        edit_row = page.data.get("edit_cost_row")

        if edit_row:
            def reopen_on_save(updated_data):
                page.data["sabtehazine_changed"] = False
                page.data["sabtehazine_loaded"] = True

                old_category_id = edit_row.get("old_category_id") or edit_row.get("id_hazine")
                new_category_id = updated_data.get("id_hazine")

                updated_row = get_controller().edit_cost(edit_row["id"], updated_data)

                updated_row["id_hazine"] = updated_data.get("id_hazine")
                updated_row["category_title"] = updated_data.get("category_title")

                updated_row["member_id"] = updated_data.get("member_id")
                updated_row["member_name"] = updated_data.get("member_name", "")

                updated_row["account_id"] = updated_data.get("account_id")
                updated_row["price"] = updated_data.get("price")
                updated_row["title"] = updated_data.get("title")
                updated_row["date_cost"] = updated_data.get("date_cost")

                # سریع UI را آپدیت کن؛ کل لیست را reload نکن
                update_ui(edit_row["id"], updated_row)
                page.run_task(refresh_summary_after_save_async)

                # learning و embedding در background
                if new_category_id and new_category_id != old_category_id:
                    raw_text = (
                        edit_row.get("temp_hazine")
                        or updated_data.get("title")
                        or edit_row.get("title", "")
                    )

                    page.run_task(
                        learn_category_after_save,
                        raw_text,
                        new_category_id,
                    )

                # summary را هم سبک‌تر و async انجام بده
                page.run_task(refresh_summary_async)

                safe_page_update(page)
                
            from ui.edit_cost_dialog import open_edit_cost_dialog
            open_edit_cost_dialog(
                page=page,
                row=edit_row,
                on_save=reopen_on_save,
            )

    # refresh_summary()
    bottom_input_container = ft.Container(
        bgcolor=APP_BG,
        padding=ft.padding.only(
            left=12,
            right=12,
            top=8,
            bottom=20 if page.platform == ft.PagePlatform.IOS else 8,
        ),
        content=input_row,
    )

    if page.platform == ft.PagePlatform.ANDROID:
        bottom_input_control = ft.SafeArea(
            avoid_intrusions_top=False,
            avoid_intrusions_left=False,
            avoid_intrusions_right=False,
            avoid_intrusions_bottom=True,
            content=bottom_input_container,
        )
    else:
        bottom_input_control = bottom_input_container


    return ft.View(
        route="/sabtehazine",
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

                    ft.Container(
                        expand=True,
                        bgcolor=APP_BG,
                        padding=ft.padding.only(
                            left=12,
                            right=12,
                            top=12,
                            bottom=12,
                        ),
                        content=chat_column,
                    ),

                    bottom_input_control,
                ],
            )
        ],
    )
