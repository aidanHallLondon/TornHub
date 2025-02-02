import json
import os
from string import Template
from tabulate import tabulate
from Torn.reporting.reporting import move_template_file_with_subs
from Torn.tables import generateStyledTable, html_table


def save_browsable_tables(
    conn, cursor, template_file_path="templates/db/table.html", path="reports/db"
):
    # save_table_as_html(conn,cursor, table_name="oc_positions")
    iterate_tables(conn, cursor, template_file_path, path)


def iterate_tables(
    conn, cursor, template_file_path="templates/db/table.html", path="reports/db"
):
    # get a list of all tables and then write HTML files
    cursor.execute(
        """SELECT sm.name, sm.type, rc.row_count
            FROM sqlite_master sm
			LEFT JOIN _row_counts rc on sm.name=rc.name
            WHERE sm.type IN ('table', 'view') AND sm.name NOT LIKE 'sqlite_%' 
            ORDER BY sm.name;"""
    )
    data = cursor.fetchall()
    menu = []
    for name, entity_type, row_count in data:
        save_table_or_view_as_html(
            conn,
            cursor,
            entity_name=name,
            entity_type=entity_type,
            template_file_path=template_file_path,
            path=path,
        )
        menu.append(
            {
                "name": name,
                "icon": "•" if entity_type == "table" else "°",
                "type": entity_type,
                "row_count": row_count,
            },
        )
    html = generate_menu_html(menu)

    move_template_file_with_subs(
        template_file_path="templates/db/_menu.html",
        out_path=path,
        out_filename="_menu.html",
        substitutions={
            "page_title": "menu",
            "content_html": html,
            "sub_title": "sub",
        },
    )
 



def save_table_or_view_as_html(
    conn,
    cursor,
    entity_name,
    entity_type="Table",
    order_clause=None,
    template_file_path="templates/db/table.html",
    path="reports/db",
):
    cursor.execute(
        f"""
       SELECT * 
        FROM {entity_name}
        {order_clause if order_clause else ''} LIMIT 1000;
    """
    )
    save_data_as_html(
        conn,
        cursor,
        None,
        entity_name=entity_name,
        entity_type=entity_type,
        template_file_path=template_file_path,
        path=path,
    )


def save_data_as_html(
    conn,
    cursor,
    data=None,
    entity_name=None,
    entity_type="Table",
    template_file_path="templates/db/table.html",
    path="reports/db",
):
    table_view_html_str = html_table(cursor, data)

    out_filename = f"{entity_type}_{entity_name}.html"
    title_str = f"{entity_name} {entity_type}"
    table_title = f"Browse {entity_type}"
    move_template_file_with_subs(
        template_file_path=template_file_path,
        out_path=path,
        out_filename=out_filename,
        substitutions={
            "page_title": title_str,
            "content_html": table_view_html_str,
            "sub_title": table_title,
        },
    )




def generate_menu_html(menu_list):

    def menu_list_to_tree(menu_items):
        tree_root = {
            "parts": [{"label": "root", "href": "root", "type": "root", "row_count": None}],
            "children": [],
        }
        for item in menu_items:
            name = item["name"]
            entity_type = item["type"]
            row_count = item["row_count"]
            # split name into parts but skip the first char to ignore any leading "_"
            parts = name[1:].split("_")
            parts[0] = name[0] + parts[0]
            node = tree_root
            for index, part in enumerate(parts):
                is_last_part = index == len(parts) - 1
                
                
                # Search for a matching child node based on the current part
                match = None
                if "children" in node:
                    for child in node["children"]:
                        if child["parts"][-1]["label"] == part:
                            match = child
                            break

                if match:
                    if is_last_part:
                         match["parts"].append({"label": part, "href": name, "type": entity_type, "row_count": row_count})
                    node = match
                
                else:  # create a new match node
                    new_part = {"label": part}
                    if is_last_part:
                        new_part.update({"href": name, "type": entity_type, "row_count": row_count})

                    
                    
                    # Check if the current node already has parts
                    if "parts" in node and node["parts"] and node["parts"][-1]["label"] == part :
                       node["parts"].append(new_part)
                       
                    else:    
                       match = {
                           "parts": [new_part],
                           "children": []
                       }
                       node.setdefault("children", []).append(match)
                       node = match
        return tree_root

    def collapse_single_parents_tree(tree):
        def recursive_collapse(node):
            if not node.get("children"):
                return node

            # Modified while loop condition: Only check for single child
            while len(node["children"]) == 1:
                child = node["children"][0]
                node["parts"].extend(child["parts"])
                node["children"] = child.get("children", [])

            node["children"] = [recursive_collapse(child) for child in node.get("children", [])]
            return node

        return recursive_collapse(tree)

    def tree_to_html(menu_tree):
        def render_parts(parts, is_folder):
            """Renders a list of parts into HTML.
            """
            html_parts = []
            for i, part in enumerate(parts):
                if "href" in part:
                    entity_type = part.get("type", "table")
                    row_count = part.get("row_count")
                    f_row_count = f"({row_count:,})" if row_count else ""
                    class_name = "part"
                    href = f"{entity_type}_{part['href']}.html"
                    html = f"""<a class="{class_name}" href="{href}"
                        onclick="parent.frames['main-content'].location.href='{href}';  event.stopPropagation(); return false;" 
                        title="{part['href']}">{part['label']}</a>"""
                else:
                    # If it's not an href, but it is a folder, add the folder-toggle class
                    html = f"""<span class="label_part">{part['label']}</span>"""
                    f_row_count=""
                if i==len(parts)-1:
                    html += f""" <span class="row_count">{f_row_count}</span>"""
                else:
                    html+= '<span class="separator">_</span>'
                html_parts.append(html)
            return "".join(html_parts)

        def recursive_to_html(node):
            """Recursively converts a node and its children to HTML.
            """
            html = ""
            is_folder = bool(node.get("children"))
            
            li_class = "folder-toggle" if is_folder else ""
            
            html += f'<li class="{li_class}"><span class="label">'
            
            # Add the chevron only if it's a folder
            if is_folder:
                prefix='''<svg width="14" height="14"><use href="#chevron"></use></svg>&nbsp;'''
            else:
                prefix=""
                
            html += prefix + render_parts(node["parts"], is_folder)
            html+="</span>"
            if is_folder:
                html += "<ul>"
                for child in node["children"]:
                    html += recursive_to_html(child)
                html += "</ul>"

            html += "</li>"
            return html
        
        html=""
        if "children" in menu_tree and menu_tree["children"]:
           html += "<ul>"
           for child in menu_tree["children"]:
              html += recursive_to_html(child)
           html += "</ul>"
        return html

    # return build_html_tree(collapse_single_item_folders(build_hierarchy(menu_items)))
    menu_tree = menu_list_to_tree(menu_list)
    menu_tree = collapse_single_parents_tree(menu_tree)
    return tree_to_html(menu_tree)