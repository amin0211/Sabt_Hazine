import flet as ft
from services.i18n import t
import asyncio
from services.supabase_service import (
    supabase,
    load_all_hazineha, 
    load_leaf_hazineha,
    get_current_user,
    get_my_profile,
    get_current_workspace_id,
    _load_all_hazineha_for_workspace,
    _load_active_hazineha_for_workspace, 
    _load_leaf_hazineha_for_workspace,
)

from datetime import date
from services.utils import today_local, safe_picker_date






class Node:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.children = []
        self.costs = []
        self.adding_child = False
        self.expanded = False
        self.total_cost = 0
        self.direct_cost = 0


def hazinaha_view(page: ft.Page):
    APP_BG = "#F6F8FC"
    CARD_BG = "#FFFFFF"
    CARD_HOVER = "#F8FBFF"
    CARD_SELECTED = "#EEF4FF"
    PRIMARY = "#2563EB"
    SUCCESS_BG = "#ECFDF3"
    SUCCESS_TEXT = "#16A34A"
    DANGER = "#DC2626"
    TEXT_MAIN = "#111827"
    TEXT_MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    CHIP_BG = "#F1F5F9"

    INDENT = 16

    if not isinstance(page.data, dict):
        page.data = {}

    try:
        for ctrl in list(page.overlay):
            if getattr(ctrl, "key", None) in (
                "category_nav_cover",
                "fixed_expense_temp_cover",
                "bank_reconcile_temp_cover",
            ):
                page.overlay.remove(ctrl)
    except Exception as ex:
        print("REMOVE_TEMP_COVER_ERROR:", ex, flush=True)

    current_user = get_current_user()
    if not current_user:
        return ft.View(
            route="/hazinaha_view",
            bgcolor=APP_BG,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("کاربر وارد نشده است", size=16, color=DANGER),
                )
            ],
        )

    # current_user_id = current_user.id

    selected_member_id = {"value": None}
    selected_member_title = {"value": t(page, "Hazineha_AllMember")}
    member_search_query = {"value": ""}

    picker_mode = False
    current_category_id = None

    if not isinstance(page.data, dict):
        page.data = {}



    from_view = page.data.get("from")
        
    picker_mode = (
        page.data.get("category_picker_mode") == True
        and from_view != "sabtehazine"   # 👈 فقط منو رو حذف کن
    )


    # اگر از منو اومده → picker خاموش
    if from_view == "sabtehazine":
        page.data["category_picker_mode"] = False    
        
    current_category_id = page.data.get("category_picker_current_id")
    
    without_edit = page.data.get("without_edit") == True

    # def get_from_route():
    #     if page.data.get("from") == "dashboard_view":
    #         return "/dashboard_view"


    #     if page.data.get("from") == "trend_view":
    #         return "/trend_view"
        

    #     return "/sabtehazine"

    def get_from_view():


        if page.data.get("from") == "dashboard_view":
            return "dashboard_view"

        if page.data.get("from") == "trend_view":
            return "trend_view"
        
        if page.data.get("from") == "cost_report_view":
            return "cost_report_view"

        if page.data.get("from") == "edit_cost_dialog":
            return "edit_cost_dialog"   # 👈 مهم

        if page.data.get("from") == "accounts":
            return "accounts"
        
        if page.data.get("from") == "fixed_expenses_view":
            return "fixed_expenses_view"

        if page.data.get("from") == "bank_reconcile_view":
            return "bank_reconcile_view"

        return "sabtehazine"


    def go_back(e):
        from_view = page.data.get("from")

        if from_view == "edit_cost_dialog":
            page.data["reopen_edit_cost_dialog"] = True
            page.data["sabtehazine_loaded"] = False
            page.data["sabtehazine_changed"] = True
            page.data.pop("sabtehazine_view_cache", None)
            page.app_go("sabtehazine")
            return

        if from_view == "accounts":
            page.data["reopen_account_filter_dialog"] = True
            page.data["category_picker_mode"] = False
            page.app_go("accounts")
            return

        if from_view == "fixed_expenses_view":
            page.data["reopen_fixed_expense_dialog"] = True
            page.data["category_picker_mode"] = False
            page.data["without_edit"] = False
            page.app_go("fixed_expenses_view")
            return

        if from_view == "trend_view":
            page.data["category_picker_mode"] = False
            page.data["reopen_trend_filter_dialog"] = True   # اگر در trend از این flag استفاده می‌کنی
            page.data["trend_changed"] = True                # اگر trend cache داری
            page.data.pop("trend_view_cache", None)

            page.app_go("trend_view")
            return
        
        if from_view == "cost_report_view":
            page.data["category_picker_mode"] = False
            page.data["cost_report_changed"] = True
            page.data.pop("cost_report_view_cache", None)

            page.app_go("cost_report_view")
            return

        if from_view == "bank_reconcile_view":
            page.data["category_picker_mode"] = False
            page.data["without_edit"] = False
            page.data["reopen_bank_reconcile_dialog"] = True
            page.app_go("bank_reconcile_view")
            return

        if from_view == "dashboard_view":
            page.data["category_picker_mode"] = False

            # اگر از dashboard هم چیزی باید reopen شود
            page.data["reopen_dashboard"] = True   # اختیاری، اگر لازم داری

            # اگر dashboard cache داری
            page.data.pop("dashboard_view_cache", None)

            page.app_go("dashboard_view")
            return        

        page.data["category_picker_mode"] = False
        page.app_go("sabtehazine")


    def confirm_category_pick(e=None):
        selected_node_id = selected_id["value"]
        if not selected_node_id:
            return

        selected_node = nodes_dict.get(selected_node_id)
        if not selected_node:
            return

        callback = None

        if isinstance(page.data, dict):
            callback = page.data.get("category_picker_on_selected")

        if callback:
            callback({
                "category_id": selected_node.id,
                "category_title": selected_node.name,
            })
            
        if page.data.get("from") == "fixed_expenses_view":
            page.data["reopen_fixed_expense_dialog"] = True
            page.data["category_picker_mode"] = False
            page.data["without_edit"] = False
            page.app_go("fixed_expenses_view")
            return

        # 🔥 مهم‌ترین قسمت
        if page.data.get("from") == "edit_cost_dialog":
            page.data["reopen_edit_cost_dialog"] = True
            page.data["sabtehazine_loaded"] = False
            page.data["sabtehazine_changed"] = True
            page.app_go("sabtehazine")
            return

        if page.data.get("from") == "bank_reconcile_view":
            page.data["category_picker_mode"] = False
            page.data["without_edit"] = False
            page.data["reopen_bank_reconcile_dialog"] = True
            page.app_go("bank_reconcile_view")
            return

        if page.data.get("from") == "accounts":
            page.data["reopen_account_filter_dialog"] = True
            page.app_go("accounts")
            return

        page.app_go(get_from_view())
                
    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")


    def first_day_of_current_month():
        today_ = today_local(page)
        return date(today_.year, today_.month, 1)

    start_date = first_day_of_current_month()
    end_date = today_local(page)

    start_picker = None
    end_picker = None

    if not picker_mode:
        start_picker = ft.DatePicker(value=start_date)
        end_picker = ft.DatePicker(value=end_date)

        if start_picker not in page.overlay:
            page.overlay.append(start_picker)

        if end_picker not in page.overlay:
            page.overlay.append(end_picker)


    def attach_costs(nodes_dict, cost_map):
        for node in nodes_dict.values():
            node.direct_cost = 0
            node.total_cost = 0

        for nid, total in cost_map.items():
            if nid in nodes_dict:
                nodes_dict[nid].direct_cost = total

    def calc_total(node):
        total = node.direct_cost
        for child in node.children:
            total += calc_total(child)
        node.total_cost = total
        return total


    def load_cost_sums_filtered():
        if picker_mode:
            print("HAZINEHA COST skipped: picker_mode", flush=True)
            return {}        
        workspace_id = get_current_workspace_id(page)

        print("HAZINEHA COST workspace_id:", workspace_id, flush=True)

        if not workspace_id:
            return {}

        query = (
            supabase
            .table("cost")
            .select("id_hazine, price, date_cost, member_id")
            .eq("workspace_id", workspace_id)
            .gte("date_cost", start_date.isoformat())
            .lte("date_cost", end_date.isoformat())
        )

        if selected_member_id["value"]:
            query = query.eq("member_id", selected_member_id["value"])

        res = query.execute()
        data = res.data or []
        cost_map = {}

        for c in data:
            nid = c.get("id_hazine")
            price = c.get("price") or 0
            if nid is not None:
                cost_map[nid] = cost_map.get(nid, 0) + price

        return cost_map



    def refresh_costs_only(update_page=True):

        if not picker_mode:
            try:
                print("HAZINEHA STEP 2: load_cost_sums_filtered")
                cost_map = load_cost_sums_filtered()
            except Exception as ex:
                print("HAZINEHA load_cost_sums_filtered ERROR:", ex)
                cost_map = {}

            attach_costs(nodes_dict, cost_map)

            for r in root_nodes:
                calc_total(r)
        else:
            for node in nodes_dict.values():
                node.direct_cost = 0
                node.total_cost = 0

        rebuild_tree(update_page=update_page)

    def load_data_from_db():
        workspace_id = get_current_workspace_id(page)

        print("HAZINEHA workspace_id:", workspace_id, flush=True)

        if not workspace_id:
            print("HAZINEHA ERROR: no workspace_id", flush=True)
            return []

        response = (
            supabase
            .table("hazineha")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("id")
            .execute()
        )

        return response.data or []

    def build_tree_from_db(data):
        if not data:
            return [], {}
        nodes = {}

        for item in data:
            nodes[item["id"]] = Node(item["id"], item["title"])

        root_nodes_local = []

        for item in data:
            node = nodes[item["id"]]
            parent_id = item["id_parent"]

            if parent_id in (None, 0):
                root_nodes_local.append(node)
            else:
                parent = nodes.get(parent_id)
                if parent:
                    parent.children.append(node)

        for root in root_nodes_local:
            root.expanded = True
            for child in root.children:
                child.expanded = False

        # ✅ این باید بیرون حلقه باشد
        return root_nodes_local, nodes

    def update_title(node_id, new_title):
        workspace_id = get_current_workspace_id(page)

        (
            supabase
            .table("hazineha")
            .update({"title": new_title})
            .eq("id", node_id)
            .eq("workspace_id", workspace_id)
            .execute()
        )

        page.data["hazineha_changed"] = True

    def insert_node(title, parent_id):
        workspace_id = get_current_workspace_id(page)
        user = get_current_user()

        if not workspace_id:
            raise Exception("current_workspace_id is empty")

        if not user:
            raise Exception("User is not logged in")

        res = (
            supabase
            .table("hazineha")
            .insert({
                "user_id": user.id,
                "workspace_id": workspace_id,
                "title": title,
                "id_parent": parent_id,
                "keywords": [],
                "embedding_text": "",
                "is_active": True,
                "template_id": None,
            })
            .execute()
        )

        page.data["hazineha_changed"] = True

        return res.data[0]["id"]




    try:
        print("HAZINEHA STEP 1: load_data_from_db")
        data = load_data_from_db()
        print("HAZINEHA DATA COUNT:", len(data) if data else 0)
    except Exception as ex:
        print("HAZINEHA load_data_from_db ERROR:", ex)
        data = []

    root_nodes, nodes_dict = build_tree_from_db(data)

    if picker_mode:
        print("HAZINEHA STEP 2 skipped costs: picker_mode", flush=True)
        cost_map = {}
    else:
        try:
            print("HAZINEHA STEP 2: load_cost_sums_filtered")
            cost_map = load_cost_sums_filtered()
        except Exception as ex:
            print("HAZINEHA load_cost_sums_filtered ERROR:", ex)
            cost_map = {}

    attach_costs(nodes_dict, cost_map)

    if not picker_mode:
        for r in root_nodes:
            calc_total(r)
            
    search_query = {"value": ""}
    selected_id = {"value": None}
    row_controls = {}

    tree = ft.ListView(
        spacing=6,
        expand=True,
        padding=0,
        auto_scroll=False,
    )

    def node_matches(node, query: str):
        return query in node.name.strip().lower()

    def filter_tree(nodes, query: str):
        result = []

        for node in nodes:
            filtered_children = filter_tree(node.children, query)
            is_match = node_matches(node, query)

            if is_match or filtered_children:
                result.append({
                    "node": node,
                    "children": filtered_children
                })

        return result

    def build_full(node):
        return {
            "node": node,
            "children": [build_full(c) for c in node.children]
        }

    def tree_prefix(level):
        return ft.Container(width=level * INDENT)

    def action_icon(icon, color, on_click):
        return ft.IconButton(
            icon=icon,
            icon_color=color,
            icon_size=14,
            width=24,
            height=24,
            on_click=on_click,
            style=ft.ButtonStyle(padding=0),
        )

    def expand_icon(icon, color, on_click):
        return ft.IconButton(
            icon=icon,
            icon_color=color,
            icon_size=22,
            width=38,
            height=38,
            on_click=on_click,
            style=ft.ButtonStyle(padding=0),
        )

    def save_title(node, value):
        value = (value or "").strip()
        if not value:
            return
        node.name = value
        update_title(node.id, value)
        rebuild_tree(update_page=False)

    def close_dialog(e=None):
        dialog.open = False
        page.update()


    def clear_hazineha_cache():
        _load_all_hazineha_for_workspace.cache_clear()
        _load_active_hazineha_for_workspace.cache_clear()
        _load_leaf_hazineha_for_workspace.cache_clear()
        
    def delete_node(parent, child, e=None):
        if without_edit:
            return

        def close_dialog(e=None):
            dialog.open = False
            page.update()

        def confirm_delete(e=None):
            try:
                workspace_id = get_current_workspace_id(page)

                res = (
                    supabase
                    .table("hazineha")
                    .delete()
                    .eq("id", child.id)
                    .eq("workspace_id", workspace_id)
                    .execute()
                )

                if child in parent.children:
                    parent.children.remove(child)

                if child.id in nodes_dict:
                    del nodes_dict[child.id]

                page.data["hazineha_changed"] = True

                if hasattr(load_all_hazineha, "cache_clear"):
                    clear_hazineha_cache()

                if hasattr(load_leaf_hazineha, "cache_clear"):
                    clear_hazineha_cache()

                dialog.open = False
                rebuild_tree()

            except Exception as ex:
                print("DELETE ERROR:", ex)
                dialog.open = False
                page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("حذف کتگوری"),
            content=ft.Text(f"'{child.name}' حذف شود؟"),
            actions=[
                ft.TextButton("لغو", on_click=close_dialog),
                ft.TextButton("حذف", on_click=confirm_delete),
            ],
        )

        if dialog not in page.overlay:
            page.overlay.append(dialog)

        dialog.open = True
        page.update()
 

    def start_adding_child(node, e=None):
        if without_edit:
            return
        node.adding_child = True
        node.expanded = True
        selected_id["value"] = node.id
        rebuild_tree()

    # def add_child_wrapper(node, e):
        # if not node.adding_child:
        #     return

        # node.adding_child = False
        # name = (e.control.value or "").strip()

        # if name:
        #     new_id = insert_node(name, node.id)
        #     new_node = Node(new_id, name)

        #     # اضافه به درخت
        #     node.children.append(new_node)

        #     # خیلی مهم: اضافه به dictionary اصلی
        #     nodes_dict[new_id] = new_node

        #     node.expanded = True
        #     selected_id["value"] = new_id

        #     rebuild_tree()

        #     # # اگر در حالت انتخاب کتگوری هستیم، همان آیتم جدید انتخاب شود
        #     # if picker_mode:
        #     #     confirm_category_pick()
        #     #     return

        # rebuild_tree()
        
    def toggle_expand(node, e=None):
        try:
            node.expanded = not node.expanded
            # selected_id["value"] = node.id
            print(
                "TOGGLE NODE:",
                node.id,
                node.name,
                "expanded=",
                node.expanded,
                "children=",
                len(node.children),
                flush=True,
            )
            rebuild_tree()
        except Exception as ex:
            print("TOGGLE EXPAND ERROR:", repr(ex), flush=True)
            

    def on_search_change(e):
        search_query["value"] = (e.control.value or "").strip().lower()
        rebuild_tree()

    def clear_search(e=None):
        search_query["value"] = ""
        search_field.value = ""
        rebuild_tree()

    def apply_row_style(row_control, node_id):
        is_selected_row = selected_id["value"] == node_id

        row_control.bgcolor = CARD_SELECTED if is_selected_row else CARD_BG
        row_control.border = ft.border.all(1, PRIMARY if is_selected_row else BORDER)


    def refresh_selected_row_styles():
        for node_id, row_control in list(row_controls.items()):
            try:
                apply_row_style(row_control, node_id)
                row_control.update()
            except Exception as ex:
                print("ROW STYLE UPDATE SKIPPED:", node_id, repr(ex), flush=True)

                
    def select_node(node):
        selected_id["value"] = node.id
        print("ROW SELECTED:", node.id, node.name, flush=True)

        # فقط رنگ ردیف‌های فعلی را عوض کن؛ کل tree را rebuild نکن
        refresh_selected_row_styles()

        
    def build_display_name(node):
        q = search_query["value"]

        if not q:
            return ft.Text(
                node.name,
                size=13,
                weight=ft.FontWeight.W_600,
                color=TEXT_MAIN,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            )

        name_lower = node.name.lower()
        idx = name_lower.find(q)

        if idx == -1:
            return ft.Text(
                node.name,
                size=13,
                weight=ft.FontWeight.W_600,
                color=TEXT_MAIN,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            )

        before = node.name[:idx]
        match = node.name[idx:idx + len(q)]
        after = node.name[idx + len(q):]

        return ft.Row(
            [
                ft.Text(before, size=13, color=TEXT_MAIN),
                ft.Text(match, size=13, color=PRIMARY, weight=ft.FontWeight.W_700),
                ft.Text(after, size=13, color=TEXT_MAIN),
            ],
            spacing=0,
            tight=True,
        )

    def build_meta_line(node):
        parts = []

        if not picker_mode:
            parts.append(
                ft.Text(
                    f"{t(page, 'edit_cost_price')}: {node.total_cost:,.2f}",
                    size=10,
                    color=SUCCESS_TEXT,
                    weight=ft.FontWeight.W_600,
                )
            )

        if node.children:
            parts.append(
                ft.Text(
                    f"{len(node.children)} {t(page, 'Hazineha_SubHazine')}",
                    size=10,
                    color=TEXT_MUTED,
                )
            )

        return ft.Row(parts, spacing=8, tight=True)
        
    def build_filtered_tree(item, parent=None, level=0, force_expand=False):
        node = item["node"]
        visible_children = item["children"]
        should_expand = force_expand or node.expanded
        is_selected = selected_id["value"] == node.id

        if node.children:
            expand_btn = expand_icon(
                ft.Icons.EXPAND_MORE if should_expand else ft.Icons.CHEVRON_RIGHT,
                TEXT_MUTED,
                lambda e, n=node: toggle_expand(n, e)
            )
        else:
            expand_btn = ft.Container(width=38)

        if node.children:
            type_icon = ft.Icon(
                ft.Icons.FOLDER_OUTLINED,
                size=14,
                color=PRIMARY if level == 0 else "#64748B"
            )
        else:
            type_icon = ft.Icon(
                ft.Icons.LABEL_OUTLINE,
                size=13,
                color="#94A3B8"
            )
        def open_edit_dialog(node):
            title_field = ft.TextField(
                value=node.name,
                label="نام کتگوری",
                text_size=13,
                autofocus=True,
            )

            def close_dlg(e=None):
                edit_dialog.open = False
                safe_update()

            def save_dlg(e=None):
                new_title = (title_field.value or "").strip()

                if not new_title:
                    return

                try:
                    node.name = new_title
                    update_title(node.id, new_title)

                    page.data["hazineha_changed"] = True
                    clear_hazineha_cache()

                    edit_dialog.open = False
                    rebuild_tree()

                except Exception as ex:
                    print("EDIT CATEGORY ERROR:", repr(ex), flush=True)
                    edit_dialog.open = False
                    safe_update()

            edit_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("ویرایش کتگوری"),
                content=title_field,
                actions=[
                    ft.TextButton("لغو", on_click=close_dlg),
                    ft.TextButton("ذخیره", on_click=save_dlg),
                ],
            )

            if edit_dialog not in page.overlay:
                page.overlay.append(edit_dialog)

            edit_dialog.open = True
            safe_update()

        edit_btn = action_icon(
            ft.Icons.EDIT_OUTLINED,
            TEXT_MUTED,
            lambda e, n=node: open_edit_dialog(n)
        )

        add_btn = action_icon(
            ft.Icons.ADD,
            PRIMARY,
            lambda e, n=node: start_adding_child(n, e)
        )




        if parent is not None and not node.children:
            delete_btn = action_icon(
                ft.Icons.DELETE_OUTLINE,
                DANGER,
                lambda e, p=parent, c=node: delete_node(p, c, e)
            )
        else:
            delete_btn = ft.Container(width=24)

        if without_edit:
            actions_row = ft.Container(width=0)
        else:
            actions_row = ft.Row(
                [delete_btn, edit_btn, add_btn],
                spacing=0,
                tight=True,
            )

            # if not is_selected:
            #     actions_row = ft.Container(width=0)

        # if is_selected and not without_edit:
        if False:
            original_value = node.name

            confirm_btn = ft.IconButton(
                icon=ft.Icons.CHECK,
                icon_color=SUCCESS_TEXT,
                icon_size=16,
                width=34,
                height=34,
                visible=False,
            )

            cancel_btn = ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color=DANGER,
                icon_size=16,
                width=34,
                height=34,
                visible=False,
            )

            edit_input = ft.TextField(
                value=node.name,
                expand=True,
                border=ft.InputBorder.NONE,
                bgcolor=None,
                text_size=13,
                content_padding=ft.padding.symmetric(horizontal=0, vertical=0),
            )

            def update_edit_buttons(e=None, inp=edit_input):
                changed = (inp.value or "").strip() != original_value

                confirm_btn.visible = changed
                cancel_btn.visible = changed

                try:
                    confirm_btn.update()
                    cancel_btn.update()
                except Exception:
                    pass

            def save_edit(e=None, n=node, inp=edit_input):
                new_value = (inp.value or "").strip()

                if not new_value:
                    inp.value = original_value
                    rebuild_tree()
                    return

                if new_value == original_value:
                    rebuild_tree()
                    return

                n.name = new_value
                update_title(n.id, new_value)
                rebuild_tree()

            def cancel_edit(e=None, inp=edit_input):
                inp.value = original_value
                rebuild_tree()

            edit_input.on_change = update_edit_buttons
            edit_input.on_submit = save_edit

            # اگر نمی‌خواهی با خارج شدن از فیلد اتومات ذخیره کند، on_blur را حذف کن
            # edit_input.on_blur = save_edit

            confirm_btn.on_click = save_edit
            cancel_btn.on_click = cancel_edit

            title_content = ft.Row(
                controls=[
                    edit_input,
                    confirm_btn,
                    cancel_btn,
                ],
                spacing=2,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        else:
            title_content = build_display_name(node)
            
        row_bg = CARD_SELECTED if is_selected else CARD_BG
        row_border = PRIMARY if is_selected else BORDER

        def on_row_hover(e):
            if selected_id["value"] == node.id:
                e.control.bgcolor = CARD_SELECTED
                e.control.border = ft.border.all(1, PRIMARY)
            else:
                e.control.bgcolor = CARD_HOVER if e.data == "true" else CARD_BG
                e.control.border = ft.border.all(1, BORDER)

            e.control.update()

            
        title_block = ft.Column(
            [
                title_content,
                build_meta_line(node),
            ],
            spacing=2,
            tight=True,
            expand=True,
        )

        left_tree_area = ft.Row(
            [
                tree_prefix(level),
                expand_btn,
                type_icon,
            ],
            spacing=4,
            tight=True,
        )

        node_row = ft.Container(
            bgcolor=row_bg,
            border=ft.border.all(1, row_border),
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=8, vertical=7),
            on_click=lambda e, n=node: select_node(n),
            on_hover=on_row_hover,
            content=ft.Row(
                [
                    left_tree_area,
                    ft.Container(
                        expand=True,
                        content=title_block,
                    ),
                    actions_row,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )
        row_controls[node.id] = node_row

        children_controls = []

        if should_expand:
            for child_item in visible_children:
                children_controls.append(
                    build_filtered_tree(
                        child_item,
                        parent=node,
                        level=level + 1,
                        force_expand=force_expand,
                    )
                )

        # if node.adding_child:
        #     new_child_input = ft.TextField(
        #         label=t(page, "Hazineha_NameNew"),
        #         autofocus=True,
        #         filled=True,
        #         border_radius=10,
        #         bgcolor="#FFFFFF",
        #         text_size=13,
        #         on_blur=lambda e, n=node: save_new_child,
        #         on_submit=lambda e, n=node: save_new_child,
        #     )

        #     children_controls.append(
        #         ft.Container(
        #             padding=ft.padding.only(left=(level + 1) * INDENT + 32, top=4),
        #             content=new_child_input,
        #         )
        #     )


        if node.adding_child:
            new_child_input = ft.TextField(
                label=t(page, "Hazineha_NameNew"),
                autofocus=True,
                filled=True,
                border_radius=10,
                bgcolor="#FFFFFF",
                text_size=13,
                expand=True,
            )

            async def save_new_child(e=None, n=node, inp=new_child_input):
                await asyncio.sleep(0.15)

                if not n.adding_child:
                    return

                name = (inp.value or "").strip()   # 👈 همیشه از inp بخون

                n.adding_child = False

                if name:
                    new_id = insert_node(name, n.id)
                    new_node = Node(new_id, name)
                    n.children.append(new_node)
                    nodes_dict[new_id] = new_node
                    n.expanded = True
                    selected_id["value"] = new_id

                rebuild_tree()

            def cancel_new_child(e=None, n=node):
                n.adding_child = False
                rebuild_tree()

            new_child_input.on_blur = save_new_child
            new_child_input.on_submit = save_new_child

            children_controls.append(
                ft.Container(
                    padding=ft.padding.only(left=(level + 1) * INDENT + 32, top=4),
                    content=ft.Row(
                        [
                            new_child_input,
                            ft.IconButton(
                                icon=ft.Icons.CHECK,
                                icon_color=SUCCESS_TEXT,
                                width=36,
                                height=36,
                                on_click=save_new_child,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=DANGER,
                                width=36,
                                height=36,
                                on_click=cancel_new_child,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            
        return ft.Column(
            controls=[
                node_row,
                ft.Column(children_controls, spacing=4, tight=True),
            ],
            spacing=2,
            tight=True,
        )

    def rebuild_tree(update_page=True):
        try:
            row_controls.clear()
            new_controls = []
            q = search_query["value"]

            if q:
                filtered = filter_tree(root_nodes, q)

                if not filtered:
                    new_controls.append(
                        ft.Container(
                            bgcolor="#FFFFFF",
                            border=ft.border.all(1, BORDER),
                            border_radius=14,
                            padding=20,
                            content=ft.Column(
                                [
                                    ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=28, color="#94A3B8"),
                                    ft.Text(
                                        t(page, "Hazineha_CanNotFind"),
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=TEXT_MAIN,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=6,
                            ),
                        )
                    )
                else:
                    for item in filtered:
                        new_controls.append(
                            build_filtered_tree(
                                item,
                                parent=None,
                                level=0,
                                force_expand=True,
                            )
                        )
            else:
                for root in root_nodes:
                    new_controls.append(
                        build_filtered_tree(
                            build_full(root),
                            parent=None,
                            level=0,
                            force_expand=False,
                        )
                    )

            tree.controls.clear()
            tree.controls.extend(new_controls)

            if update_page:
                safe_update()

        except Exception as ex:
            print("REBUILD_TREE_ERROR:", repr(ex), flush=True)

            tree.controls.clear()
            tree.controls.append(
                ft.Container(
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, BORDER),
                    border_radius=14,
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Text(
                                "Tree rebuild error",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=DANGER,
                            ),
                            ft.Text(
                                str(ex),
                                size=11,
                                color=TEXT_MUTED,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

            if update_page:
                safe_update()


    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_ROUNDED,
        icon_color=TEXT_MAIN,
        icon_size=18,
        width=34,
        height=34,
        on_click=go_back,
    )

    search_field = ft.TextField(
        hint_text=t(page, "Hazineha_hintserch"),
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        text_size=13,
        on_change=on_search_change,
        on_submit=on_search_change,
    )

    clear_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=TEXT_MUTED,
        icon_size=18,
        width=34,
        height=34,
        on_click=clear_search,
    )

    def build_filter_button(label, icon):
        return ft.Container(
            expand=True,   # 🔥 مهم
            height=42,     # 🔥 ارتفاع ثابت
            border=ft.border.all(1, BORDER),
            border_radius=14,
            bgcolor="#FFFFFF",
            padding=ft.padding.symmetric(horizontal=14),
            alignment=ft.Alignment.CENTER_LEFT,   # 🔥 متن چپ
            content=ft.Row(
                [
                    ft.Icon(icon, size=16, color=PRIMARY),
                    ft.Text(label, size=13, color=TEXT_MAIN, weight=ft.FontWeight.W_500),
                ],
                spacing=8,
            )
        )

    #  ---------------------   member ----------------

    member_list_column = ft.ListView(
        spacing=6,
        expand=True,
        padding=0,
        auto_scroll=False,
    )

    def load_members():
        workspace_id = get_current_workspace_id(page)

        print("HAZINEHA MEMBERS workspace_id:", workspace_id, flush=True)

        if not workspace_id:
            return []

        res = (
            supabase
            .table("members")
            .select("id, full_name, relation")
            .eq("workspace_id", workspace_id)
            .order("full_name")
            .execute()
        )

        return res.data or []


    if picker_mode:
        print("HAZINEHA STEP 3 skipped members: picker_mode", flush=True)
        members_data = []
    else:
        try:
            print("HAZINEHA STEP 3: load_members", flush=True)
            members_data = load_members()
            print("HAZINEHA MEMBERS COUNT:", len(members_data) if members_data else 0, flush=True)
        except Exception as ex:
            print("HAZINEHA load_members ERROR:", ex, flush=True)
            members_data = []

    def close_member_dialog(e=None):
        member_dialog.open = False
        safe_update()

    def refresh_member_button():
        member_btn.content = build_filter_button(
            f"{selected_member_title['value']}",
            ft.Icons.PERSON_OUTLINE,
        )

    def on_member_selected(member_id, member_name):
        selected_member_id["value"] = member_id
        selected_member_title["value"] = member_name

        refresh_member_button()
        member_dialog.open = False

        refresh_costs_only(update_page=False)
        safe_update()

    def clear_member_filter(e=None):
        selected_member_id["value"] = None
        selected_member_title["value"] = t(page, "Hazineha_AllMember")

        refresh_member_button()
        member_dialog.open = False

        refresh_costs_only(update_page=False)
        safe_update()


    def rebuild_member_list():
        member_list_column.controls.clear()

        q = (member_search_query["value"] or "").strip().lower()

        member_list_column.controls.append(
            ft.Container(
                bgcolor="#F8FAFC",
                border=ft.border.all(1, BORDER),
                border_radius=12,
                padding=10,
                on_click=clear_member_filter,
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.GROUP_OUTLINED, size=17, color=PRIMARY),
                        ft.Text(
                            t(page, "Hazineha_AllMember"),
                            size=13,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                        ),
                        ft.Text(
                            "-",
                            size=12,
                            color=TEXT_MUTED,
                            width=90,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

        for m in members_data:
            name = m.get("full_name") or ""
            relation = m.get("relation") or ""
            mid = m.get("id")

            search_text = f"{name} {relation}".lower()

            if q and q not in search_text:
                continue

            member_list_column.controls.append(
                ft.Container(
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, BORDER),
                    border_radius=12,
                    padding=10,
                    on_click=lambda e, member_id=mid, member_name=name: on_member_selected(member_id, member_name),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.PERSON_OUTLINE, size=17, color=TEXT_MUTED),
                            ft.Text(
                                name or "بدون نام",
                                size=13,
                                color=TEXT_MAIN,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                            ft.Text(
                                relation or "-",
                                size=12,
                                color=TEXT_MUTED,
                                width=90,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    def on_member_search_change(e):
        member_search_query["value"] = e.control.value or ""
        rebuild_member_list()
        safe_update()

    member_search_field = ft.TextField(
        hint_text=t(page, "Hazine_SerchMember"),
        prefix_icon=ft.Icons.SEARCH,
        text_size=13,
    )

    member_search_field.on_change = on_member_search_change

    member_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(t(page, "Budget_Budget"), size=16, weight=ft.FontWeight.W_700),
        content=ft.Container(
            width=360,
            height=520,
            content=ft.Column(
                [
                    member_search_field,
                    member_list_column,
                ],
                spacing=10,
                expand=True,
            ),
        ),
        actions=[
            ft.TextButton(t(page, "Close"), on_click=close_member_dialog),
        ],
    )

    if member_dialog not in page.overlay:
        page.overlay.append(member_dialog)

    def open_member_dialog(e=None):
        member_search_query["value"] = ""
        member_search_field.value = ""
        rebuild_member_list()

        member_dialog.open = True
        safe_update()

    member_btn = ft.GestureDetector(
        on_tap=open_member_dialog,
        content=build_filter_button(
                selected_member_title['value'],
            ft.Icons.PERSON_OUTLINE,
        ),
    )
    

    #  ---------  member ----------------



    def open_start(e):
        start_picker.open = True
        page.update()

    def open_end(e):
        end_picker.open = True
        page.update()

    start_btn = ft.GestureDetector(
        on_tap=open_start,
        content=build_filter_button(
            f"{t(page, 'date_from')}: {start_date.isoformat()}",
            ft.Icons.CALENDAR_MONTH,
        ),
    )

    end_btn = ft.GestureDetector(
        on_tap=open_end,
        content=build_filter_button(
            f"{t(page, 'date_to')}: {end_date.isoformat()}",
            ft.Icons.DATE_RANGE,
        ),
    )

    def update_start(e):
        nonlocal start_date

        if not start_picker.value:
            return

        start_date = safe_picker_date(start_picker.value, page)
        start_picker.value = start_date

        start_btn.content = build_filter_button(
            f"{t(page, 'date_from')}: {start_date.isoformat()}",
            ft.Icons.CALENDAR_MONTH,
        )

        start_btn.update()
        refresh_costs_only()

    def update_end(e):
        nonlocal end_date

        if not end_picker.value:
            return

        end_date = safe_picker_date(end_picker.value, page)
        end_picker.value = end_date

        end_btn.content = build_filter_button(
            f"{t(page, 'date_to')}: {end_date.isoformat()}",
            ft.Icons.DATE_RANGE,
        )

        end_btn.update()
        refresh_costs_only()
        
    if not picker_mode:
        start_picker.on_change = update_start
        end_picker.on_change = update_end

    search_box = ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=6, vertical=6),
        content=ft.Row(
            [
                back_btn,
                ft.Container(expand=True, content=search_field),
                clear_btn,
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def on_member_change(e):
        value = e.control.value

        if value == "all":
            selected_member_id["value"] = None
        else:
            selected_member_id["value"] = value

        refresh_costs_only()




    filter_bar = ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        visible=not picker_mode,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(expand=True, content=start_btn),
                        ft.Container(expand=True, content=end_btn),
                    ],
                    spacing=8,
                ),
                ft.Container(
                    width=float("inf"),
                    content=member_btn,
                ),
            ],
            spacing=8,
        ),
    )





    tree_shell = ft.Container(
        expand=True,
        bgcolor="#F9FBFF",
        border=ft.border.all(1, "#E7EEF9"),
        border_radius=16,
        padding=8,
        content=tree,
    )

    rebuild_tree(update_page=False)

    picker_action_bar = ft.Container(
        # visible=picker_mode,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        border_radius=16,
        padding=12,
        content=ft.Row(
            [
                # ft.Text(
                #     "یک کتگوری را از درخت انتخاب کن",
                #     size=12,
                #     color=TEXT_MUTED,
                #     expand=True,
                # ),
                ft.ElevatedButton(
                    t(page, "Hazineha_title"),
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    on_click=confirm_category_pick,
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color="#FFFFFF",
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    body_content = ft.Container(
        expand=True,
        padding=ft.padding.only(
            left=10,
            right=10,
            top=42,
            bottom=10 if page.platform != ft.PagePlatform.ANDROID else 4,
        ),
        content=ft.Column(
            [
                filter_bar,
                search_box,
                tree_shell,

                ft.Container(
                    visible=picker_mode,
                    padding=ft.padding.only(bottom=12),
                    content=picker_action_bar,
                ),
            ],
            spacing=10,
            expand=True,
        ),
    )

    if page.platform == ft.PagePlatform.ANDROID:
        page_body = ft.SafeArea(
            expand=True,
            avoid_intrusions_top=False,
            avoid_intrusions_left=False,
            avoid_intrusions_right=False,
            avoid_intrusions_bottom=True,
            content=body_content,
        )
    else:
        page_body = body_content

    return ft.View(
        route="/hazinaha_view",
        bgcolor=APP_BG,
        padding=0,
        spacing=0,
        controls=[
            page_body
        ],
    )