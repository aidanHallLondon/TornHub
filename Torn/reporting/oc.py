import os
from string import Template
from tabulate import tabulate
from Torn.reporting.build_menus import _menu_item_for_file
from Torn.reporting.faction_revives import get_revives_pivotted
from Torn.tables import generateStyledTable, html_table


def oc_item_requirements(conn,cursor,
                        template_file_path="templates/reports/oc/items_required.html",
                        title_str="Organised Crimes 2.0 — Items Required",
                        table_title="Items Required per crime",
                        path ="reports/faction/oc",
                        out_filename="items_required",):
    cursor.execute('''
       SELECT
            c.crime_name as crime,
            item_name as name,
            r.requirement as count,
            item_type as type,
            c.crime_difficulty AS level,
            PRINTF('$ %,d', i.average_price) as f_price,
            average_price AS price,
            c.best_status,
            i.item_id
        FROM (
            SELECT
                crime_name,
                crime_difficulty,
                item_requirement_id,
                FIRST_VALUE(status) OVER (
                PARTITION BY crime_name, crime_difficulty 
                ORDER BY 
                    CASE
                        WHEN status = 'Successful' THEN 100
                        WHEN status = 'Expired' THEN -10
                        WHEN status = 'Failure' THEN 90
                        WHEN status = 'Recruiting' THEN 0
                        WHEN status = 'Planning' THEN 10
                        ELSE NULL
                        END DESC
                ) AS best_status
            FROM oc_crime_instances_cube
            WHERE status NOT IN ("Expired", "Recruiting") AND item_requirement_id IS NOT NULL
            GROUP BY crime_name, crime_difficulty, item_requirement_id
        ) AS c
        JOIN items AS i
            ON i.item_id = c.item_requirement_id
        JOIN (  -- Subquery to calculate requirement
            SELECT DISTINCT 
                crime_name,
                crime_difficulty,
                item_requirement_id,
                requirement
            FROM (
                SELECT DISTINCT 
                    crime_instance_id,
                    crime_name,
                    crime_difficulty,
                    item_requirement_id, 
                    COUNT(crime_slot_id) AS requirement
                FROM oc_crime_instances_cube
                WHERE item_requirement_id IS NOT NULL
                GROUP BY crime_instance_id, crime_name,crime_difficulty,item_requirement_id
            )
        ) AS r 
            ON c.crime_name = r.crime_name 
            AND c.crime_difficulty = r.crime_difficulty 
            AND c.item_requirement_id = r.item_requirement_id
        ORDER BY 4 DESC, 1;
    ''')
    table_html_str = html_table(cursor)
    # 
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    final_html = html_template.substitute(
        page_title=title_str,
        table_html= table_html_str,
        table_title=table_title,
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")  
    return  _menu_item_for_file(path,name="oc_crimes_items_required", href=out_filename)
