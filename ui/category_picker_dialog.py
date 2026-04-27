import flet as ft
from supabase import create_client
from dotenv import load_dotenv
import os
from services.i18n import t

SUPABASE_URL = "https://gisyttrgmhbuxvmsjdfm.supabase.co"

load_dotenv()
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class Node:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.children = []
        self.expanded = False


def open_category_picker_dialog(
    page: ft.Page,
    current_category_id=None,
    on_selected=None,
):
    APP_BG = "#F8FAFC"
    CARD_BG = "#FFFFFF"
    CARD_HOVER = "#F8FBFF"
    CARD_SELECTED = "#EEF4FF"
    PRIMARY = "#2563EB"
    TEXT_MAIN = "#111827"
    TEXT_MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    DANGER = "#DC2626"

    INDENT = 16

    def safe_update():
        try:
            page.update()
        except Exception as e:
            print(f"SAFE UPDATE SKIPPED: {e}")

    def load_data_from_db():
        response = supabase.table("hazineha").select("*").execute()
        return response.data or []

    def build_tree_from_db(data):
        nodes = {}

        for item in data:
            nodes[item["id"]] = Node(item["id"], item["title"])

        root_nodes = []

        for item in data:
            node = nodes[item["id"]]
            parent_id = item["id_parent"]

            if parent_id in (None, 0):
                root_nodes.append(node)
            else:
                parent = nodes.get(parent_id)
                if parent:
                    parent.children.append(node)

        return root_nodes, nodes

    data = load_data_from_db()
    root_nodes, nodes_dict = build_tree_from_db(data)

    selected_id = {"value": current_category_id}
    search_query = {"value": ""}

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

    def toggle_expand(node, e=None):
        node.expanded = not node.expanded
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

    def build_filtered_tree(item, level=0, force_expand=False):
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

        row_bg = CARD_SELECTED if is_selected else CARD_BG
        row_border = PRIMARY if is_selected else BORDER

        def on_row_hover(e):
            if selected_id["value"] == node.id:
                e.control.bgcolor = CARD_SELECTED
            else:
                e.control.bgcolor = CARD_HOVER if e.data == "true" else CARD_BG
            e.control.update()

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
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            on_click=lambda e, n=node: select_node(n),
            on_hover=on_row_hover,
            content=ft.Row(
                [
                    left_tree_area,
                    ft.Container(
                        expand=True,
                        content=build_display_name(node),
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        children_controls = []

        if should_expand:
            for child_item in visible_children:
                children_controls.append(
                    build_filtered_tree(
                        child_item,
                        level=level + 1,
                        force_expand=force_expand,
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

    def rebuild_tree():
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
                            level=0,
                            force_expand=True,
                        )
                    )
        else:
            for root in root_nodes:
                tree.controls.append(
                    build_filtered_tree(
                        build_full(root),
                        level=0,
                        force_expand=False,
                    )
                )

        safe_update()

    def close_dialog(e=None):
        dialog.open = False
        safe_update()

    def confirm_pick(e=None):
        selected_node_id = selected_id["value"]
        if not selected_node_id:
            return

        selected_node = nodes_dict.get(selected_node_id)
        if not selected_node:
            return

        if on_selected:
            on_selected({
                "category_id": selected_node.id,
                "category_title": selected_node.name,
            })

        dialog.open = False
        safe_update()

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

    search_box = ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=6, vertical=6),
        content=ft.Row(
            [
                ft.Container(expand=True, content=search_field),
                clear_btn,
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    tree_shell = ft.Container(
        height=420,
        bgcolor=APP_BG,
        border=ft.border.all(1, "#E7EEF9"),
        border_radius=16,
        padding=8,
        content=tree,
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor="#FFFFFF",
        title=ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_TREE_OUTLINED, color=PRIMARY, size=22),
                ft.Text(t(page, "Hazineha_title"), size=18, weight=ft.FontWeight.W_700, color=TEXT_MAIN),
            ],
            spacing=8,
            tight=True,
        ),
        content=ft.Container(
            width=520,
            content=ft.Column(
                [
                    search_box,
                    tree_shell,
                ],
                spacing=10,
                tight=True,
            ),
        ),
        actions=[
            ft.TextButton(
                t(page, "Hazineha_Reject"),
                on_click=close_dialog,
                style=ft.ButtonStyle(color=TEXT_MUTED),
            ),
            ft.ElevatedButton(
                t(page, "from services.i18n import t"),
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                on_click=confirm_pick,
                style=ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    rebuild_tree()

    if dialog not in page.overlay:
        page.overlay.append(dialog)

    dialog.open = True
    safe_update()