import flet as ft
from supabase import create_client
from dotenv import load_dotenv
import os

# SUPABASE_URL = 
# SUPABASE_KEY = 

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
        self.expanded = False  # برای باز/بسته کردن شاخه
        self.total_cost = 0
        self.direct_cost = 0
        self.total_cost = 0

# def main(page: ft.Page):
def hazinaha_view(page: ft.Page):

    # page.title = "مدیریت هزینه‌ها (درختی)"
    # page.scroll = "auto"
    
#    page.data["tree_column"] = ft.Column()
    back_btn = ft.ElevatedButton(
        content=ft.Text("⬅ Back"),
        on_click=lambda e: page.go("/sabtehazine")
    )
    
    page.data["tree_column"] = ft.Column(scroll=ft.ScrollMode.ALWAYS)
    def attach_costs(nodes_dict, cost_map):
        for nid, total in cost_map.items():
            if nid in nodes_dict:
                nodes_dict[nid].direct_cost = total
                                
    def calc_total(node):
        total = node.costs_sum if hasattr(node, "costs_sum") else node.direct_cost

        for child in node.children:
            total += calc_total(child)

        node.total_cost = total
        return total
        
    def load_cost_sums():
        res = supabase.table("cost") \
            .select("id_hazine, price") \
            .execute()

        data = res.data

        cost_map = {}

        for c in data:
            nid = c["id_hazine"]
            cost_map[nid] = cost_map.get(nid, 0) + c["price"]

        return cost_map
        
    def load_data_from_db():
        response = supabase.table("hazineha").select("*").execute()
        return response.data

    def build_tree_from_db(data):
        nodes = {}
        # ساخت همه نودها
        for item in data:
            nodes[item["id"]] = Node(item["id"], item["title"])
    
        root_nodes = []

        # اتصال نودها به هم
        for item in data:
            node = nodes[item["id"]]
            parent_id = item["id_parent"]

            if parent_id in (None, 0):
                root_nodes.append(node)
            else:
                parent = nodes.get(parent_id)
                if parent:
                    parent.children.append(node)
    
        # 👇 فقط اولین ریشه باز باشه
        if root_nodes:
            root_nodes[0].expanded = True

        return root_nodes, nodes

    def update_title(node_id, new_title):
        supabase.table("hazineha").update(
            {"title": new_title}
        ).eq("id", node_id).execute()

    def save_title(node, value):
        node.name = value
        update_title(node.id, value)

    def insert_node(title, parent_id):
        res = supabase.table("hazineha").insert({
            "title": title,
            "id_parent": parent_id
        }).execute()
        return res.data[0]["id"]

    data = load_data_from_db()

    root_nodes, nodes_dict = build_tree_from_db(data)

    cost_map = load_cost_sums()   # 👈 اینجا

    attach_costs(nodes_dict, cost_map)
    for r in root_nodes:
        calc_total(r)

    
    # ---------- خطوط عمودی ----------
    def tree_prefix(level, is_last_child_list):
        row_controls = []

        for i in range(level):
            show_line = not is_last_child_list[i]

            ft.Container(
                width=10,
                border=ft.border.Border(
                    left=ft.border.BorderSide(1, "grey")
                ) if show_line else None
            )

        return ft.Row(row_controls, spacing=0)

    # ---------- ساخت درخت ----------
    def build_tree(node, parent=None, level=0, is_last_child_list=None):
        if is_last_child_list is None:
            is_last_child_list = []

        controls = []

        # هزینه‌ها
        for idx, cost in enumerate(node.costs):
            cost_field = ft.TextField(
                value=str(cost),
                width=80,
                on_submit=lambda e, n=node, i=idx: update_cost(n, i, e)
            )

            controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("💰"),
                        cost_field,
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            on_click=lambda e, n=node, i=idx: delete_cost(n, i, e)
                        )
                    ]),
                    padding=ft.padding.only(left=(level + 1) * INDENT, top=0, bottom=0)
                )
            )

        # زیر دسته‌ها
        if node.expanded:
            for i, child in enumerate(node.children):
                last_child_flags = is_last_child_list + [i == len(node.children) - 1]
                controls.append(
                    build_tree(
                        child,
                        parent=node,
                        level=level + 1,
                        is_last_child_list=last_child_flags
                    )
                )

        # ادیت باکس اضافه کردن زیر دسته
        if node.adding_child:
            new_child_input = ft.TextField(
                label="نام زیر دسته جدید",
                autofocus=True,
                on_blur=lambda e, n=node: add_child_wrapper(n, e),
                on_submit=lambda e, n=node: add_child_wrapper(n, e)
            )

            controls.append(
                ft.Container(
                    new_child_input,
                    padding=ft.padding.only(left=(level + 1) * INDENT)
                )
            )

        # نام نود
        name_field = ft.TextField(
            value=node.name,
            on_blur=lambda e, n=node: save_title(n, e.control.value),
            expand=True,
            border=ft.InputBorder.NONE,
            bgcolor=None,
            content_padding=ft.padding.symmetric(vertical=0, horizontal=5),
        )

        # دکمه حذف
        delete_btn = (
            ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="حذف زیر دسته",
                on_click=lambda e, p=parent, c=node: delete_node(p, c, e)
            )
            if parent is not None
            else ft.Container(width=40)
        )

        # دکمه افزودن
        add_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="افزودن زیر دسته",
            on_click=lambda e, n=node: start_adding_child(n, e)
        )

        # دکمه باز/بسته
        expand_btn = (
            ft.IconButton(
                icon=ft.Icons.EXPAND_MORE if node.expanded else ft.Icons.CHEVRON_RIGHT,
                on_click=lambda e, n=node: toggle_expand(n, e)
            )
            if node.children
            else ft.Container(width=40)
        )

        node_row = ft.Row(
            [
                tree_prefix(level, is_last_child_list),
                expand_btn,
                name_field,
                ft.Text(f"{node.total_cost}", color="green"),
                add_btn,
                delete_btn
            ],
            alignment="start",
            spacing=0
        )

        return ft.Container(
            content=ft.Column([
                node_row,
                ft.Column(controls, spacing=0, expand=True, tight=True)
            ]),
            padding=ft.padding.only(left=level * INDENT),
            margin=0
        )

    # ---------- عملیات ----------
    def start_adding_child(node, e=None):
        node.adding_child = True
        refresh_tree()

    def add_child_wrapper(node, e):
        name = e.control.value.strip()
        if name:
            new_id = insert_node(name, node.id)
            node.children.append(Node(new_id, name))

        node.adding_child = False
        refresh_tree()

    def toggle_expand(node, e=None):
        node.expanded = not node.expanded
        refresh_tree()

    def update_cost(node, idx, e):
        try:
            node.costs[idx] = float(e.control.value)
        except ValueError:
            pass
        refresh_tree()

    INDENT = 10

    def delete_cost(node, idx, e):
        node.costs.pop(idx)
        refresh_tree()

    def delete_node(parent, child, e):
        if parent:
            parent.children.remove(child)
            refresh_tree()

    def refresh_tree():

        tree = page.data["tree_column"]
        tree.controls.clear()


        for n in root_nodes:
            tree.controls.append(build_tree(n))
        page.update()
    
    # ---------- UI ----------return ft.Column([

    root_input = ft.TextField(
        label="اضافه کردن دسته جدید",
        autofocus=True,
        on_submit=lambda e: root_nodes.append(Node(e.control.value)) or refresh_tree()
    )

    
    page.data["tree_column"] = ft.Column(scroll=ft.ScrollMode.ALWAYS)

    tree = page.data["tree_column"]

    refresh_tree()

    return ft.View(
        route="/hazinaha_view",
        controls=[
            ft.Column([
                back_btn,
                tree
            ])  
        ]
    )
