import json
import os
from string import Template
from tabulate import tabulate
from Torn.tables import generateStyledTable, html_table


def browse_tables(
    conn, cursor, template_file_path="templates/db/table.html", path="reports/db"
):
    # save_table_as_html(conn,cursor, table_name="oc_positions")
    iterate_tables(conn, cursor, template_file_path, path)


def iterate_tables(conn, cursor, template_file_path="templates/db/table.html", path="reports/db"):
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
            { "name": name, "icon": "•" if entity_type=='table' else "°", "type":entity_type, "row_count":row_count},
        )
    html = generate_menu_html(menu)
    save_html_in_template(
        title_str="menu",
        content_html_str=html,
        sub_title="sub",
        template_file_path="templates/db/_menu.html",
        path=path,
        out_filename="_menu.html",
    )


def generate_menu_html(menu_list):
    def _find_object_match(objects, key,value):
        for obj in objects:
            if key in obj and obj[key] == value: return obj
        return None
    
    def menu_list_to_tree(menu_items):
        tree_root = {
            "label": "root",
            "href": "root",
            "type":'root',
            "children": [],
        }
        for item in menu_items:
            name=item["name"]
            entity_type=item["type"] 
            row_count=item["row_count"]
            #split name into parts but skip the first char to ignore any leading "_"
            parts = name[1:].split("_")
            parts[0]=name[0]+parts[0]
            node=tree_root
            for index, part in enumerate(parts):
                is_last_part = (index==len(parts) -1)
                #
                match = _find_object_match(node["children"], "label", part) if "children" in node else None
                if match:
                    if is_last_part:
                        match['href'] = name 
                        match['type'] = entity_type
                        match['row_count'] = row_count
                    node=match
                else: # create a new match node
                    match = {"label": part,}
                    if is_last_part:
                        match['href'] = name 
                        match['type'] = entity_type
                        match['row_count'] = row_count
                    node.setdefault('children',[]).append(match) 
                    node=match
        return tree_root
  

    def collapse_single_parents_tree(tree):
        def recursive_collapse(node):
            if not "children" in node or len(node["children"])==0:
                return node
            if len(node["children"]) == 1 and not "href" in node:
                child = node["children"][0]
                node['label']=f"{node['label']}_{child['label']}"
                node["href"]= child['href'] if "href" in child else None
                node["icon"]= child['icon'] if "icon" in child else None
                node['type']= child['type'] if "href" in child and "type" in child else None
                node['row_count']= child['row_count'] if "href" in child and "row_count" in child else None
                node["children"]= child['children'] if "children" in child else None
            else:
                children_list= [recursive_collapse(child) for child in node["children"]]
                node["children"] = children_list
            return node
        return recursive_collapse(tree)

    def tree_to_html(menu_tree):
        html = ""
        if "children" in menu_tree and menu_tree["children"] and len(menu_tree["children"]) > 0:  # == 'folder':
            html +="<ul>"
            for child in menu_tree["children"]:
                icon=""
                entity_type=child["type"] if "type" in child else "table"
                row_count=child["row_count"] if "row_count" in child else None
                f_row_count=f"({row_count:,})" if row_count else ""
                if "children" in child and child["children"]:
                    icon="📁 "
                html += f"<li>{icon}"
                if "href" in child:
                    html+=f'''<a href='{entity_type}_{child['href']}.html' 
                        onclick=\"parent.frames['main-content'].location.href='{entity_type}_{child['href']}.html'; return false;\" 
                        title='{child['href']}'>{child['label']} <span class="row_count">{f_row_count}</span></a>'''
                else:
                    html+=child['label']
                html += tree_to_html(child)
                html += "</li>"
            html += "</ul>"                
        return html

    # return build_html_tree(collapse_single_item_folders(build_hierarchy(menu_items)))
    menu_tree=menu_list_to_tree(menu_list)
    menu_tree=collapse_single_parents_tree(menu_tree)
    return tree_to_html(menu_tree)


    # def collapse_single_item_folders(tree):
    #     def recursive_collapse(node):
    #         if node["type"] == "leaf":
    #             return node

    #         if len(node["children"]) == 1 and node["children"]["type"] == "folder":
    #             child = node["children"]
    #             return {
    #                 "name": f"{node['name']}_{child['name']}",
    #                 "type": "folder",
    #                 "children": child["children"],
    #             }
    #         else:
    #             node["children"] = [recursive_collapse(child) for child in node["children"]]
    #             return node

    #     return recursive_collapse(tree)

    # def build_html_tree(data):
    #     html = "<ul>"
    #     if data["type"] == "folder":
    #         for child in data["children"]:
    #             if child["type"] == "folder":
    #                 html += f"<li>📁 {child['name']}"
    #                 html += build_html_tree(child)
    #                 html += "</li>"
    #             else:
    #                 hrefpath = f"table_{child['name']}.html"
    #                 label = child.get("label", child["name"])
    #                 html += f"<li><a href='{hrefpath}' onclick=\"parent.frames['main-content'].location.href='{hrefpath}'; return false;\" title='{child['name']}'>{label}</a></li>"
    #     html += "</ul>"
    #     return html

    # return build_html_tree(collapse_single_item_folders(build_hierarchy(menu_items)))


def save_table_or_view_as_html(
    conn,
    cursor,
    entity_name,
    entity_type='Table',
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
    save_html_in_template(
        title_str, table_view_html_str, table_title, template_file_path, path, out_filename
    )


def save_html_in_template(
    title_str,
    content_html_str,
    sub_title,
    template_file_path=None,
    path=None,
    out_filename=None,
):
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    #
    final_html = html_template.substitute(
        page_title=title_str,
        content_html=content_html_str,
        sub_title=sub_title,
    )
    #
    out_filepath = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(out_filepath, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {out_filepath}")
