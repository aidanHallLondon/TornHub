import copy
import datetime
from itertools import zip_longest
import os
from string import Template

from bs4 import BeautifulSoup
from Torn.charts import (
    _make_autopct,
    draw_donut_chart,
    draw_stackedarea_chart,
    load_user_colourList_for_charts,
    plt_save_image,
)
from Torn.tables import generateStyledTable

def revivers_share_donut(conn, cursor, title=None, period=None,path=None,out_filename=None):
    '''
    period is a valid time period for SQLite DATE('now', ?) e.g. '-2 days'
    '''
    if period is None:
        cursor.execute(
            """SELECT user_name AS label, successful_revives AS size FROM revivers ORDER BY 2 ASC"""
        )
    else:
        cursor.execute("""
        SELECT
                r_user.name AS label,
                COUNT(*) AS size             
            FROM
                (SELECT * FROM revives WHERE timestamp >= DATE('now', ?)) as revives             
            INNER JOIN users AS r_user                     
                ON revives.reviver_id = r_user.user_id                     
                AND r_user.is_in_faction = 1                           
            WHERE is_success = 1    
            GROUP BY
                revives.reviver_id,
                r_user.name   
        """,(period,))
    data = cursor.fetchall()
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    # combine two lists in one list of tuples that the function prefers
    series = [(l, s) for l, s in list(zip_longest(labels, values, fillvalue=None))]
    draw_donut_chart(
        series=series,
        title=title if title else "Contributions by Revivers",
        autopct=_make_autopct(values, format_string="{value:d}\n({percentage:.1f}%)"),
        path=path,
        out_filename=out_filename
    )  # pie
    # draw_donut_chart(series=values, labels=labels) # pie


def revives_stackedarea_chart(
    conn,cursor,
    periodName,
    periodAlias,
    title="Revivers contributions",
    path="reports/faction/revives",
    filename="stacked_area",
    truncate_after=None,
):
    xaxis_data, series_data = revives_pivot_stackedarea_dataseries(
        conn,cursor,periodAlias=periodAlias, periodName=periodName
    )
    if truncate_after:  # removes older data points
        xaxis_data = xaxis_data[:truncate_after]
        for key in series_data:
            series_data[key] = series_data[key][:truncate_after]
    # Create the stacked area chart
    draw_stackedarea_chart(
        width_inches=12,
        height_inches=6,
        title=title,
        xaxis_title="Week number" if periodName == "week" else "Date",
        yaxis_title="Successful revives contributed",
        xaxis_label_scale=1.5 if periodName == "week" else 2,
        xaxis_data=xaxis_data,
        series_data=series_data,
    )
    plt_save_image(
        path=path,
        out_filename=filename,
        show_image=False,
    )


def revives_pivot_stackedarea_dataseries(conn,cursor,periodAlias, periodName):
    data, headers, colalign = get_revives_pivotted(
        conn,cursor,periodAlias, periodName, totals=False
    )
    # Extract columns into separate lists
    xaxis_data = [row[0] for row in data]
    series_data = {}
    for i in range(1, len(headers)):  # Start from 1 to skip the 'date' column
        series_data[headers[i]] = [row[i] for row in data]
    series_data = dict(
        sorted(series_data.items(), key=lambda item: sum(item[1]), reverse=True)
    )
    return xaxis_data, series_data


def get_revives_pivotted(conn,cursor,periodAlias, periodName, totals=True):
    pivot_template = Template(
        (
            """
    SELECT 'Total' as $periodAlias,  
             $player_case_statements       
        FROM revives_by_$periodName
    UNION ALL """
            if totals
            else " "
        )
        + """
    SELECT period as $periodAlias,
             $player_case_statements
        FROM revives_by_$periodName 
        GROUP BY period 
        ORDER BY 1 DESC;
   """
    )
    cursor.execute(
        f"SELECT DISTINCT user_name FROM revives_by_{periodName} ORDER BY 1 ASC"
    )
    players = [row[0] for row in cursor.fetchall()]
    player_case_statements = ", ".join(
        [
            f"SUM(CASE WHEN user_name = '{player}' THEN successful_revives ELSE '0' END) AS {player.replace(' ', '').replace('-', '')}"
            for player in players
        ]
    )
    pivot_sql = pivot_template.substitute(
        periodAlias=periodAlias,
        periodName=periodName,
        player_case_statements=player_case_statements,
    )
    #

    cursor.execute(pivot_sql)
    headers = [description[0] for description in cursor.description]
    colalign = ["right" for description in cursor.description]
    data = cursor.fetchall()
    return data, headers, colalign


def list_revivers_to_html_file(
    conn,
    cursor,
    template_file_path,
    path,
    title_str="Revivers",
    out_filename="by_date.html",
):
    cursor.execute("""SELECT * FROM revivers ORDER BY 3 DESC,4 DESC,2 """)

    # user_id,user_name,revive_count,revive_skill
    reviver_data = (
        cursor.fetchall()
    )  # [[11111,'a',10,.1],[2222,'b',20,.2],[33333,'b',30,.3],[4444,'d',40,.4]]
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)

    with open(template_file_path, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    soup.find("span", id="generated_date_field").string = datetime.datetime.now(
        datetime.UTC
    ).strftime("%Y-%m-%dT%H:%M Torn time")
    tbody = soup.find("tbody")
    template_row = tbody.find("tr", class_="template")
    # Iterate through the reviver data and create table rows
    for i, reviver in enumerate(reviver_data):
        user_id, user_name, count, skill = reviver  # Assuming your tuple structure
        new_row = copy.copy(template_row)
        new_row["class"] = f"appended{i}"
        # new_row.clear() # Remove existing contents from the clone # This seems dumb
        cells = new_row.find_all("td")
        cells[0].string = str(i + 1)
        cells[1].string = str(user_name)
        cells[2].string = str(count)
        cells[3].string = str(skill)
        # zebra stripe from second row in tbody
        if i % 2 == 1:
            for cell in cells:
                cell["style"] = cell["style"] + "; background-color:#e0e0e0;"

        # Update the signature link and image source
        anchor_tag = cells[4].find("a")
        anchor_tag["href"] = str(anchor_tag["href"]).replace("$user_id", str(user_id))
        img_tag = anchor_tag.find("img")
        img_tag["src"] = str(img_tag["src"]).replace("$user_id", str(user_id))
        img_tag["alt"] = str(img_tag["alt"]).replace("$user_id", str(user_id))

        tbody.append(new_row)

    # Remove the original template row
    template_row.decompose()

    # Update the page title
    soup.title.string = title_str
    soup.find("h1").string = title_str

    final_html = str(soup)

    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")


def revives_pivot_to_html_file(
    conn,cursor,
    template_file_path,
    path,
    periodAlias,
    periodName,
    title_str,
    image_title,
    image_list,
    out_filename,
):
    data, headers, colalign = get_revives_pivotted(
        conn,cursor,periodAlias, periodName, totals=True
    )

    # Replace all instances of exactly 0 with None
    data2 = [[None if value == 0 else value for value in row] for row in data]
    data = data2
    table_html_str = generateStyledTable(data, headers, colalign)
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    final_html = html_template.substitute(
        page_title=title_str,
        table_html=table_html_str,
        image_title=image_title,
        image1_src=image_list[0] if image_list and len(image_list) >= 1 else None,
        image2_src=image_list[1] if image_list and len(image_list) >= 2 else None,
        table_title="Table",
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")
