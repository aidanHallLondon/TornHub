from itertools import zip_longest
import os
import re
import sqlite3
import copy
from string import Template
from bs4 import BeautifulSoup
from tabulate import tabulate
import datetime

from Torn.charts import (
    _make_autopct,
    draw_donut_chart,
    draw_stackedarea_chart,
    get_user_colourList,
    plt_save_image,
)
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import dumpResults, initDB


conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()
initDB(conn, cursor)  # creates the database structure if not already done
get_user_colourList(conn,cursor, cmap='tab20c')
conn.commit()


def main():

    path = "reports/faction/revives"
    template_path = "templates/reports/revives/revivers_forum_list.html"

    revivers_share_donut(conn, cursor, title='Revivers total contributions', period=None,path=path,out_filename="contributions_all")
    revivers_share_donut(conn, cursor, title='Revivers contributions over the last seven days',period="-7 days",path=path,out_filename="contributions_7days")
    revivers_share_donut(conn, cursor, title='Revivers contributions over the last 30 days',period="-30 days",path=path,out_filename="contributions_30days")
    revivers_share_donut(conn, cursor, title='Revivers contributions this month',period="-1 month",path=path,out_filename="contributions_month")

    list_revivers_to_html_file(
        conn,
        cursor,
        template_path,
        path,
        title_str="Revivers",
        out_filename="revivers_forum_list.html",
    )

    template_path = "templates/reports/revives/pivot.html"
    path = "reports/faction/revives"

    pivot_to_html_file(
        template_path,
        path,
        periodAlias="date",
        periodName="date",
        title_str="Revives pivot by date",
        image_title="Charts",
        image_list=[
            "faction_revives_stacked_area_by_date.png",
            "faction_revives_stacked_area_by_date_12weeks.png",
        ],
        out_filename="by_date.html",
    )

    pivot_to_html_file(
        template_path,
        path,
        periodAlias="week",
        periodName="week",
        title_str="Revives pivot by week",
        image_title="Charts",
        image_list=[
            "faction_revives_stacked_area_by_week.png",
            "faction_revives_stacked_area_by_week_12weeks.png",
        ],
        out_filename="by_week.html",
    )
    # pivot_to_stacked_area_chart(
    revives_stackedarea_chart(
        "week",
        "week",
        title="Revivers contributions by week",
        path=path,
        filename="stacked_area_by_week",
    )
    revives_stackedarea_chart(
        "date",
        "date",
        title="Revivers contributions by day",
        path=path,
        filename="stacked_area_by_date",
    )
    revives_stackedarea_chart(
        "week",
        "week",
        title="Revivers contributions by week over 12 weeks",
        path=path,
        filename="stacked_area_by_week_12weeks",
        truncate_after=12,
    )
    revives_stackedarea_chart(
        "date",
        "date",
        title="Revivers contributions by day over 12 weeks",
        path=path,
        filename="stacked_area_by_date_12weeks",
        truncate_after=12 * 7,
    )


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
    periodName,
    periodAlias,
    title="Revivers contributions",
    path="reports/faction/revives",
    filename="stacked_area",
    truncate_after=None,
):
    xaxis_data, series_data = get_pivot_stackedarea_dataseries(
        periodAlias=periodAlias, periodName=periodName
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


def get_pivot_stackedarea_dataseries(periodAlias, periodName):
    data, headers, colalign = get_requests_pivotted(
        periodAlias, periodName, totals=False
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


def get_requests_pivotted(periodAlias, periodName, totals=True):
    pivot_template = Template(
        (
            """
    SELECT 'Total' as $periodAlias,  
             $player_case_statements       
        FROM RevivesBy$periodName
    UNION ALL """
            if totals
            else " "
        )
        + """
    SELECT period as $periodAlias,
             $player_case_statements
        FROM RevivesBy$periodName 
        GROUP BY period 
        ORDER BY 1 DESC;
   """
    )
    cursor.execute(
        f"SELECT DISTINCT user_name FROM revivesBy{periodName} ORDER BY 1 ASC"
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
    template_path,
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

    with open(template_path, "r") as f:
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


def pivot_to_html_file(
    template_path,
    path,
    periodAlias,
    periodName,
    title_str,
    image_title,
    image_list,
    out_filename,
):
    data, headers, colalign = get_requests_pivotted(
        periodAlias, periodName, totals=True
    )

    # Replace all instances of exactly 0 with None
    data2 = [[None if value == 0 else value for value in row] for row in data]
    data = data2
    table_html_str = generateStyledTable(data, headers, colalign)
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_path, "r") as f:
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


def generateStyledTable(data, headers, colalign):
    # generate html table
    table_html_str = tabulate(
        data, headers=headers, colalign=("right",), tablefmt="html"
    )
    soup = BeautifulSoup(table_html_str, "html.parser")

    for table in soup.find_all("table"):
        table["style"] = (
            "border-collapse: collapse; border: none;table-layout: fixed; width:95%;"
        )

    rows = soup.find_all("tr")
    for i, row in enumerate(rows):  # Add zebra stripes
        if i % 2 == 0:
            row["style"] = "background-color: #e0e0e0;"

    # Set column widths
    num_cols = len(headers)  # Assuming headers represent the number of columns
    col_width_percent = 100 / num_cols
    for row in rows:
        for cell in row.find_all("th"):
            cell["Style"] = (
                f" text-align: center; border:none; border-right:1px dotted #b0b0b0; font-size:smaller"
            )
        for cell in row.find_all("td"):
            cell["style"] = f"border:none;"

    # Get the modified HTML
    # return str(soup.prettify(formatter="minimal")).replace("\n","")
    html_str = str(soup.prettify(formatter="minimal"))  # .replace("\n", "")
    # Remove whitespace around numbers
    # html_str = re.sub(r"\s*(<|>)\s*", r"\1", html_str)
    return html_str


main()
