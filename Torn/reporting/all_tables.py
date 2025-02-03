import json
import os
from string import Template
from tabulate import tabulate
from Torn.reporting.reporting import move_template_file_with_subs
from Torn.tables import generateStyledTable, html_table


def save_browsable_tables(
    conn, cursor, template_file_path="templates/db/table.html", path="reports/db"
):
    menu = iterate_tables_and_menu(conn, cursor, template_file_path, path)
    template_file = "templates/db/_menu.html"
    out_filename = "_menu.html"
    return menu


def iterate_tables_and_menu(
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
    return menu
    
 

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
