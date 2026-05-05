#اگر بخوام از جدول hazineha_template به hazineha برای یه کاربر بخصوص منتقل کنه
# 
#  do $$
# declare
#     v_user_id uuid := '9fceebe3-e299-4f14-870b-c0cfe2a32ff7';
# begin
#     create temporary table temp_hazineha_map (
#         old_template_id bigint,
#         new_hazineha_id bigint
#     ) on commit drop;

#     with inserted as (
#         insert into hazineha (
#             user_id,
#             id_parent,
#             title,
#             template_id,
#             keywords,
#             embedding_text,
#             is_active
#         )
#         select
#             v_user_id,
#             null,
#             ht.title,
#             ht.id,
#             coalesce(ht.keywords, '[]'::jsonb),
#             coalesce(ht.embedding_text, ''),
#             coalesce(ht.is_active, true)
#         from hazineha_template ht
#         where not exists (
#             select 1
#             from hazineha h
#             where h.user_id = v_user_id
#               and h.template_id = ht.id
#         )
#         returning id, template_id
#     )
#     insert into temp_hazineha_map (old_template_id, new_hazineha_id)
#     select template_id, id
#     from inserted;

#     update hazineha h
#     set id_parent = parent_map.new_hazineha_id
#     from hazineha_template ht
#     join temp_hazineha_map child_map
#         on child_map.old_template_id = ht.id
#     join temp_hazineha_map parent_map
#         on parent_map.old_template_id = ht.id_parent
#     where h.id = child_map.new_hazineha_id
#       and h.user_id = v_user_id;

# end $$;




import flet as ft
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import datetime, date
from services.i18n import t
import asyncio

from services.supabase_service import load_all_hazineha, load_leaf_hazineha, get_current_user

from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")

def today_local():
    return datetime.now(TZ).date()

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"

load_dotenv()
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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

    current_user_id = current_user.id

    selected_member_id = {"value": None}
    selected_member_title = {"value": t(page, "Hazineha_AllMember")}
    member_search_query = {"value": ""}

    picker_mode = False
    current_category_id = None

    if not isinstance(page.data, dict):
        page.data = {}

    picker_mode = page.data.get("category_picker_mode", False)
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

        if page.data.get("from") == "edit_cost_dialog":
            return "edit_cost_dialog"   # 👈 مهم

        return "sabtehazine"

    def go_back(e):
        from_view = page.data.get("from")

        if from_view == "edit_cost_dialog":
            dialog_ref = page.data.get("edit_cost_dialog_ref")

            page.app_go("sabtehazine")

            if dialog_ref:
                dialog_ref.open = True
                page.update()

            return

        page.app_go(get_from_view())

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

        # 🔥 مهم‌ترین قسمت
        if page.data.get("from") == "edit_cost_dialog":
            page.data["reopen_edit_cost_dialog"] = True
            page.data["sabtehazine_loaded"] = False
            page.data["sabtehazine_changed"] = True

            page.app_go("sabtehazine")
            return

        page.app_go(get_from_view())
                
    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    def first_day_of_current_month():
        today_ = today_local()
        return date(today_.year, today_.month, 1)

    start_date = first_day_of_current_month()
    end_date = today_local()

    start_picker = ft.DatePicker(value=start_date)
    end_picker = ft.DatePicker(value=end_date)

    page.overlay.append(start_picker)
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
        query = (
            supabase
            .table("cost")
            .select("id_hazine, price, date_cost, member_id")
            .eq("user_id", current_user_id)
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
        cost_map = load_cost_sums_filtered()
        attach_costs(nodes_dict, cost_map)

        for r in root_nodes:
            calc_total(r)

        rebuild_tree(update_page=update_page)

    def load_data_from_db():
        response = (
            supabase
            .table("hazineha")
            .select("*")
            .eq("user_id", current_user_id)
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
        (
            supabase
            .table("hazineha")
            .update({"title": new_title})
            .eq("id", node_id)
            .eq("user_id", current_user_id)
            .execute()
        )
        page.data["hazineha_changed"] = True

    def insert_node(title, parent_id):
        res = (
            supabase
            .table("hazineha")
            .insert({
                "title": title,
                "id_parent": parent_id,
                "user_id": current_user_id,
            })
            .execute()
        )
        page.data["hazineha_changed"] = True

        if hasattr(load_all_hazineha, "cache_clear"):
            load_all_hazineha.cache_clear()

        if hasattr(load_leaf_hazineha, "cache_clear"):
            load_leaf_hazineha.cache_clear()

        return res.data[0]["id"]

    data = load_data_from_db()

    # print("CURRENT USER ID:", current_user_id)
    # print("HAZINEHA DATA COUNT:", len(data) if data else 0)
    # print("HAZINEHA DATA:", data[:5] if data else data)

    root_nodes, nodes_dict = build_tree_from_db(data)

    cost_map = load_cost_sums_filtered()
    attach_costs(nodes_dict, cost_map)

    for r in root_nodes:
        calc_total(r)

    search_query = {"value": ""}
    selected_id = {"value": None}

    tree = ft.Column(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
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

    def delete_node(parent, child, e=None):
        if without_edit:
            return

        def close_dialog(e=None):
            dialog.open = False
            page.update()

        def confirm_delete(e=None):
            try:
                res = (
                    supabase
                    .table("hazineha")
                    .delete()
                    .eq("id", child.id)
                    .eq("user_id", current_user_id)
                    .execute()
                )

                print("DELETE RESULT:", res.data)

                if child in parent.children:
                    parent.children.remove(child)

                if child.id in nodes_dict:
                    del nodes_dict[child.id]

                page.data["hazineha_changed"] = True

                if hasattr(load_all_hazineha, "cache_clear"):
                    load_all_hazineha.cache_clear()

                if hasattr(load_leaf_hazineha, "cache_clear"):
                    load_leaf_hazineha.cache_clear()

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

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
 
    def confirm_delete(e):
        supabase.table("hazineha") \
            .delete() \
            .eq("id", child.id) \
            .eq("user_id", current_user_id) \
            .execute()

        # 🔥 دوباره کل دیتا رو از دیتابیس بگیر
        data = load_data_from_db()
        new_roots, new_nodes = build_tree_from_db(data)

        root_nodes.clear()
        root_nodes.extend(new_roots)

        nodes_dict.clear()
        nodes_dict.update(new_nodes)

        dialog.open = False

        page.data["hazineha_changed"] = True

        rebuild_tree()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("حذف کتگوری"),
            content=ft.Text(f"'{child.name}' حذف شود؟"),
            actions=[
                ft.TextButton("لغو", on_click=lambda e: close_dialog()),
                ft.TextButton("حذف", on_click=confirm_delete),
            ],
        )

        page.dialog = dialog
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
        node.expanded = not node.expanded
        selected_id["value"] = node.id
        rebuild_tree()

    def on_search_change(e):
        search_query["value"] = (e.control.value or "").strip().lower()
        rebuild_tree()

    def clear_search(e=None):
        search_query["value"] = ""
        search_field.value = ""
        rebuild_tree()

    def select_node(node):
        selected_id["value"] = node.id
        rebuild_tree()

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

        parts.append(
            ft.Text(
                f"مبلغ: {node.total_cost:,.2f}",
                # f"مبلغ: {node.total_cost}",
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
            expand_btn = action_icon(
                ft.Icons.EXPAND_MORE if should_expand else ft.Icons.CHEVRON_RIGHT,
                TEXT_MUTED,
                lambda e, n=node: toggle_expand(n, e)
            )
        else:
            expand_btn = ft.Container(width=24)

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
                [delete_btn, add_btn],
                spacing=0,
                tight=True,
            )

            if not is_selected:
                actions_row = ft.Container(width=0)

        if is_selected and not without_edit:
            edit_input = ft.TextField(
                value=node.name,
                expand=True,
                border=ft.InputBorder.NONE,
                bgcolor=None,
                text_size=13,
                content_padding=ft.padding.symmetric(horizontal=0, vertical=0),
            )

            def save_edit(e=None, n=node, inp=edit_input):
                new_value = (inp.value or "").strip()

                if not new_value:
                    return

                if new_value == n.name:
                    rebuild_tree()
                    return

                n.name = new_value
                update_title(n.id, new_value)
                rebuild_tree()

            def cancel_edit(e=None):
                rebuild_tree()

            edit_input.on_blur = save_edit
            edit_input.on_submit = save_edit

            title_content = ft.Row(
                controls=[
                    edit_input,
                    ft.IconButton(
                        icon=ft.Icons.CHECK,
                        icon_color=SUCCESS_TEXT,
                        icon_size=16,
                        width=34,
                        height=34,
                        on_click=save_edit,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=DANGER,
                        icon_size=16,
                        width=34,
                        height=34,
                        on_click=cancel_edit,
                    ),
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
            else:
                e.control.bgcolor = CARD_HOVER if e.data == "true" else CARD_BG
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
        tree.controls.clear()
        q = search_query["value"]

        if q:
            filtered = filter_tree(root_nodes, q)

            if not filtered:
                tree.controls.append(
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
                                # ft.Text(
                                #     "عبارت جستجو را تغییر بده",
                                #     size=11,
                                #     color=TEXT_MUTED,
                                # ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=6,
                        ),
                    )
                )
            else:
                for item in filtered:
                    tree.controls.append(
                        build_filtered_tree(
                            item,
                            parent=None,
                            level=0,
                            force_expand=True,
                        )
                    )
        else:
            for root in root_nodes:
                tree.controls.append(
                    build_filtered_tree(
                        build_full(root),
                        parent=None,
                        level=0,
                        force_expand=False,
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

    member_list_column = ft.Column(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def load_members():
        res = (
            supabase
            .table("members")
            .select("id, full_name, relation")
            .eq("user_id", current_user_id)
            .order("full_name")
            .execute()
        )
        return res.data or []

    members_data = load_members()

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
        title=ft.Text(" ", size=16, weight=ft.FontWeight.W_700),
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
        content=build_filter_button(f"{t(page, 'date_from')}: {start_date}", ft.Icons.CALENDAR_MONTH)
    )

    end_btn = ft.GestureDetector(
        on_tap=open_end,
        content=build_filter_button(f"{t(page, 'date_to')}: {end_date}", ft.Icons.DATE_RANGE)
    )

    def update_start(e):
        nonlocal start_date
        if not start_picker.value:
            return

        start_date = start_picker.value.date()
        start_picker.value = start_date
        start_btn.content = build_filter_button(f"{t(page, 'date_from')}: {start_date}", ft.Icons.CALENDAR_MONTH)
        start_btn.update()
        refresh_costs_only()

    def update_end(e):
        nonlocal end_date
        if not end_picker.value:
            return

        end_date = end_picker.value.date()
        end_picker.value = end_date
        end_btn.content = build_filter_button(f"{t(page, 'date_to')}: {end_date}", ft.Icons.DATE_RANGE)
        end_btn.update()
        refresh_costs_only()

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
        visible=picker_mode,
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

    return ft.View(
        route="/hazinaha_view",
        bgcolor=APP_BG,
        controls=[
            ft.Container(
                expand=True,
                padding=10,
                content=ft.Column(
                    [
                        filter_bar,
                        search_box,
                        tree_shell,

                        ft.SafeArea(
                            avoid_intrusions_top=False,
                            avoid_intrusions_left=False,
                            avoid_intrusions_right=False,
                            avoid_intrusions_bottom=True,
                            maintain_bottom_view_padding=True,
                            minimum_padding=ft.padding.only(bottom=8),
                            content=picker_action_bar,
                        ),
                    ],
                    spacing=10,
                    expand=True,
                ),
            )
        ],
    )