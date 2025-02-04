import os
from Torn.reporting.reporting import move_template_file_with_subs


def _menu_item_for_file(path, name, href):
    if path:
        href = os.path.join(path, href) if path else href
        href = href[8:] if href.startswith("reports/") else href
    return {
        "name": name,
        "href": href,
        "icon": "•",
        "type": "file",
        "row_count": None,
    }


def generate_menu_html(path, menu_list):
    menu_tree = _menu_list_to_tree(menu_list)
    menu_tree = _collapse_single_parents_tree(menu_tree)
    return _tree_to_html(path=path, menu_tree=menu_tree)


def _menu_list_to_tree(menu_items):
    tree_root = {
        "parts": [{"label": "Root", "href": None, "type": "root"}],
        "children": [],
    }
    for item in menu_items:
        name = item["name"]
        href = item.get("href", name)
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
                    match["parts"].append(
                        {
                            "label": part,
                            "href": href,
                            "type": entity_type,
                            "row_count": row_count,
                        }
                    )
                node = match

            else:  # create a new match node
                new_part = {"label": part}
                if is_last_part:
                    new_part.update(
                        {"href": href, "type": entity_type, "row_count": row_count}
                    )

                # Check if the current node already has parts
                if (
                    "parts" in node
                    and node["parts"]
                    and node["parts"][-1]["label"] == part
                ):
                    node["parts"].append(new_part)

                else:
                    match = {"parts": [new_part], "children": []}
                    node.setdefault("children", []).append(match)
                    node = match
    return tree_root


def _collapse_single_parents_tree(tree):
    def recursive_collapse(node):
        if not node.get("children"):
            return node
        new_children = [recursive_collapse(child) for child in node.get("children", [])]
        # check for this beein a single child in children but skip the root
        if len(new_children) == 1 and node["parts"][0].get("type", "") != "root":
            only_child = new_children[0]
            node["parts"].extend(only_child["parts"])
            new_children = only_child.get("children", [])

        # Propagate child's part href to parent if parent doesn't have a part href
            child_href = next((p.get("href") for p in only_child["parts"] if p.get("href")), None)

        node["children"] = new_children

        # merge parts where there is only on href
        if len(node["parts"]) > 1 and node["parts"][-1].get("href")  and all(p.get("label") for p in node["parts"]):
            last_part_href = node["parts"][-1].get("href")  # Get href from the last part
            merged_label = "_".join(p["label"] for p in node["parts"])
            merged_part = {
                "label": merged_label,
                "href": last_part_href,
                "type": node["parts"][-1]["type"],  # Keep type from the last part
                "row_count": node["parts"][-1].get("row_count") # Keep row_count from the last part
            }
            node["parts"] = [merged_part]  # Replace all parts with the merged part
            # print(f"""MERGER {node["parts"]}""")

        return node

    return recursive_collapse(tree)

def _tree_to_html(path, menu_tree):
    def _render_parts(parts, is_folder):
        """Renders a list of parts into HTML."""
        html_parts = []
        for i, part in enumerate(parts):
            if "href" in part:
                entity_type = part.get("type", "table")
                row_count = part.get("row_count")
                f_row_count = f"({row_count:,})" if row_count else ""
                class_name = "part"
                href = part.get("href", "")
                if entity_type != "file":
                    href = os.path.join(path, f"{entity_type}_{part['href']}.html")
                html = f"""<a class="{class_name}" href="{href}"
                    onclick="parent.frames['main-content'].location.href='{href}';  event.stopPropagation(); return false;" 
                    title="{part['href']}">{part['label']}</a>"""
            else:
                # If it's not an href, but it is a folder, add the folder-toggle class
                html = f"""<span class="label_part">{part['label']}</span>"""
                f_row_count = ""
            if i == len(parts) - 1:
                html += f""" <span class="row_count">{f_row_count}</span>"""
            else:
                html += '<span class="separator">_</span>'
            html_parts.append(html)
        return "".join(html_parts)

    def recursive_to_html(node):
        """Recursively converts a node and its children to HTML."""
        html = ""
        is_folder = bool(node.get("children"))

        li_class = "folder-toggle" if is_folder else ""

        html += f'<li class="{li_class}"><span class="label">'

        # Add the chevron only if it's a folder
        if is_folder:
            prefix = """<svg width="14" height="14"><use href="#chevron"></use></svg>&nbsp;"""
        else:
            prefix = ""

        html += prefix + _render_parts(node["parts"], is_folder)
        html += "</span>"
        if is_folder:
            html += "<ul>"
            for child in node["children"]:
                html += recursive_to_html(child)
            html += "</ul>"

        html += "</li>"
        return html

    html = ""
    if "children" in menu_tree and menu_tree["children"]:
        html += "<ul>"
        for child in menu_tree["children"]:
            html += recursive_to_html(child)
        html += "</ul>"
    return html


def save_menus_as_html(menus, template_file, out_filename):
    html = ""
    for menu_inst in menus:
        href_path = menu_inst.get("path")  # relative to /reports
        menu_list = menu_inst.get("menu")
        title = menu_inst.get("title")
        #
        menu_html = generate_menu_html(href_path, menu_list)
        html += f"""<div class="menu_title">{title}</div>\n<div class="menu">{menu_html}</div>"""
    # Insert into the template
    move_template_file_with_subs(
        template_file_path=template_file,
        out_path="reports",
        out_filename=out_filename,
        substitutions={
            "page_title": "menu",
            "content_html": html,
            "sub_title": "sub",
        },
    )
