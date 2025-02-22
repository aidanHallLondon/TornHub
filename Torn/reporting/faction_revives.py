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
from Torn.reporting.build_menus import _menu_item_for_file
from Torn.tables import generateStyledTable

 
import sqlite3

def _add_totals_row(data, headers):
    """Adds totals row, handles grouped numbers, and reformats totals."""

    num_cols = len(headers)
    totals_row = ["Totals"] + [0] * (num_cols - 1)

    for row in data:
        for i in range(1, num_cols):
            try:
                value_str = str(row[i])
                value_str = value_str.replace(",", "")  # Remove commas for calculation
                value = float(value_str)
                totals_row[i] += value
            except (ValueError, TypeError):
                pass

    # Reformat the totals with commas
    for i in range(1, num_cols):
        try:
            totals_row[i] = "{:,.0f}".format(totals_row[i]) # Format with commas
        except (ValueError, TypeError):
            pass  # In case the total is not a number

    data.append(totals_row)
    return data


def revive_contract(conn, cursor,    template_file_path,
    name,
    path,
    out_filename,  revive_contract_id=None):
    # 
    title_str="Revives for contract"
    contract = _get_revive_contract(cursor, revive_contract_id)
    revive_contract_id, ally_factionname, enemy_factionname, started, ended, chance_min = contract
    # 
    cursor.execute("""
        SELECT 
            revive_contract_id,	ally_factionname,	target_factionname,	
            started, 	ended,	
            chance_min,	
            success_fee, failure_fee,	
            faction_cut,
            notes_html
        FROM revive_contracts
        WHERE revive_contract_id= ? """,(revive_contract_id,))
    data = cursor.fetchone()
    if data and len(data)==0:
        revive_contract_id=None
    else:
        (revive_contract_id,	ally_factionname,	target_factionname,	
            started, 	ended,	
            chance_min,	
            success_fee, failure_fee,	
            faction_cut,
            notes_html)=data
        
        html_str=f"""<h2>Contract #{revive_contract_id}</h2>
            <div class="contract">
            <div class="war"><span class="ally_faction">{ally_factionname}</span>
                            <span class="target_faction">{target_factionname}</span></div>
            <div class="period"><span class="started">{started}</span><span class="ended">{ended}</span></div>
            <div class="rules">
                <span class="chance_min">{chance_min}</span>
                <span class="status">Offline only</span>
            </div>
            <div class="finance">
                <div class="gross">
                    <span class="success_fee">{success_fee:,.0f}</span>
                    <span class="failure_fee">{failure_fee:,.0f}</span>
                </div>
                <div class="net">
                    <span class="success_fee">{success_fee*(1-faction_cut):,.0f}</span>
                    <span class="failure_fee">{failure_fee*(1-faction_cut):,.0f}</span>
                    <span class="faction_cut">{faction_cut}</span>
                </div>
               
            </div>
            <div class="notes">{notes_html}</div>
        </div>
        <h2>Overview</h2>
    """
    
        cursor.execute("""
            SELECT 
        reviver_name,
        SUM(CASE WHEN c_result = "failure" THEN 1 ELSE 0 END) AS "failure",
        SUM(CASE WHEN c_result = "invalid" THEN 1 ELSE 0 END) AS "invalid",
        SUM(CASE WHEN c_result = "success" THEN 1 ELSE 0 END) AS "success",
        count(*) AS total,
    --	sum(CASE WHEN target_last_action_status='Online' THEN 1 ELSE 0 END) as onlines,
    -- 	sum(gross_payment) AS gross_payment,
    -- 	sum(gross_payment)* (1-faction_cut) AS net_pay,
    -- 	sum(gross_payment)*(faction_cut) AS faction_contribution,
        printf('%,.0f', sum(gross_payment)) AS gross_payment,
        printf('%,.0f', sum(gross_payment)* (1-faction_cut)) AS net_pay,
        printf('%,.0f', sum(gross_payment)*(faction_cut)) AS faction_contribution
    FROM(
                SELECT
                    --revives.timestamp,
                    revives.result,
                    revives.chance,
                    revives.reviver_name,
                    revives.reviver_factionname,
                    revives.target_factionname,
                    target_last_action_status,
                    failure_fee,
                    success_fee,
                    faction_cut,
                    CASE 
                                WHEN target_last_action_status = "Online"  THEN "invalid"
                                WHEN result="success" THEN "success"
                                WHEN chance < 50 THEN "invalid"
                                WHEN result="failure" THEN "failure" 
                                ELSE "ERROR"
                    END AS c_result,
                    CASE 
                                WHEN target_last_action_status = "Online"  THEN 0
                                WHEN result="success" THEN success_fee
                                WHEN chance < 50 THEN 0
                                WHEN result="failure" THEN failure_fee
                                ELSE 0
                    END AS gross_payment
                FROM revives
                LEFT JOIN revive_contracts ON revive_contract_id = ?
                LEFT JOIN revivers ON revivers.user_name= reviver_name
                WHERE
                    revives.target_factionname = revive_contracts.target_factionname
                    AND strftime('%Y-%m-%d %H:%M:%S', revives.timestamp)  BETWEEN strftime('%Y-%m-%d %H:%M:%S',revive_contracts.started) 
                                                                                                                                                            AND strftime('%Y-%m-%d %H:%M:%S',revive_contracts.ended)		
        ) AS c_revives
    GROUP BY reviver_name
    ORDER BY sum(gross_payment) DESC, 1 ASC

    """,
            (revive_contract_id,))
        headers = [description[0] for description in cursor.description]
        colalign = ["right" for description in cursor.description]
        data = cursor.fetchall()
        data = _add_totals_row(data, headers)
        html_str += generateStyledTable(data, headers, colalign)

        cursor.execute("""
                    SELECT 
                            revives.timestamp ,
                            revives.result ,
                            revives.chance  ,
                            revives.reviver_name ,
                            revives.reviver_factionname ,
                            revives.target_name ,
                            revives.target_factionname,
                            revives.target_last_action_status      
                    FROM revives
                    LEFT JOIN revive_contracts ON revive_contracts.revive_contract_id = ?
                        WHERE
                        revives.target_factionname = revive_contracts.target_factionname
                        AND strftime('%Y-%m-%d %H:%M:%S', timestamp)  BETWEEN revive_contracts.started AND revive_contracts.ended
                    ORDER BY revives.timestamp DESC;
                    """,(revive_contract_id,))
        headers = [description[0] for description in cursor.description]
        colalign = ["right" for description in cursor.description]
        data = cursor.fetchall()
        if len(data):
            html_str += "<h2>Revives</h2>" + generateStyledTable(data, headers, colalign)
        else:
            html_str += "<h2>Revives</h2> None recorded" 

    output_filename = _process_template_report(template_file_path, path, out_filename, title_str, html_str)
    return _menu_item_for_file(path, name, output_filename)

def _process_template_report(template_file_path, path, out_filename, title_str, table_html_str):
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    final_html = html_template.safe_substitute(
        page_title=title_str,
        table_html=table_html_str,
        table_title="Table",
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")
    return output_filename

def _get_revive_contract(cursor, revive_contract_id):
    ally_factionname=None
    enemy_factionname=None
    started=None
    ended=None
    chance_min=None
    # 
    if revive_contract_id:
        cursor.execute(
            """
            SELECT revive_contract_id,
                ally_factionname,
                target_factionname,
                started,
                ended,
                chance_min 
            FROM revive_contracts 
            WHERE revive_contract_id=?
            """,
            (revive_contract_id,),
        )
    else:
        cursor.execute(
            """
            SELECT revive_contract_id,
                ally_factionname,
                target_factionname,
                started,
                ended,
                chance_min 
            FROM revive_contracts 
            ORDER BY started DESC
            LIMIT 1
            """
        )
    data= cursor.fetchone()
    if data and len(data):
        (
            revive_contract_id,
            ally_factionname,
            enemy_factionname,
            started,
            ended,
            chance_min,
        ) =data
    else: revive_contract_id=None
        
    return revive_contract_id, ally_factionname, enemy_factionname, started, ended, chance_min

def revivers_share_donut(
    conn, cursor, title=None, name=None, period=None, path=None, out_filename=None
):
    """
    period is a valid time period for SQLite DATE('now', ?) e.g. '-2 days'
    """
    if period is None:
        cursor.execute(
            """SELECT user_name AS label, successful_revives AS size FROM revivers ORDER BY 2 ASC"""
        )
    else:
        cursor.execute(
            """
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
        """,
            (period,),
        )
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
        out_filename=out_filename,
    )  # pie
    # draw_donut_chart(series=values, labels=labels) # pie
    return _menu_item_for_file(
        path, name=name if name else out_filename, href=out_filename+".svg"
    )


def revives_stackedarea_chart(
    conn,
    cursor,
    periodName,
    periodAlias,
    title="Revivers_contributors",
    path="reports/faction/revives",
    filename="stacked_area",
    truncate_after=None,
):
    xaxis_data, series_data = revives_pivot_stackedarea_dataseries(
        conn, cursor, periodAlias=periodAlias, periodName=periodName
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
    return _menu_item_for_file(path, name=filename, href=filename)


def revives_pivot_stackedarea_dataseries(conn, cursor, periodAlias, periodName):
    data, headers, colalign = get_revives_pivotted(
        conn, cursor, periodAlias, periodName, totals=False
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


def get_revives_pivotted(conn, cursor, periodAlias, periodName, totals=True):
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


def list_revivers_to_html_file( # revivers_list
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

    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")
    return _menu_item_for_file(path, out_filename, out_filename)


def revives_pivot_to_html_file(
    conn,
    cursor,
    template_file_path,
    name,
    path,
    periodAlias,
    periodName,
    title_str,
    image_title,
    image_list,
    out_filename,
):
    data, headers, colalign = get_revives_pivotted(
        conn, cursor, periodAlias, periodName, totals=True
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
    return _menu_item_for_file(path, name, output_filename)

