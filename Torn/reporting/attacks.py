import math
import os
from string import Template
import pandas as pd
import numpy as np
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import plt_save_image
from Torn.reporting.build_menus import _menu_item_for_file
from Torn.tables import html_table
from datetime import datetime, timedelta


def incoming_attack_chart(
    conn,
    cursor,
    template_file_path="templates/reports/attacks/incoming.html",
    title_str="Attacks Incoming Chart",
    table_title="Attacks",
    path="reports/attacks",
    out_filename="incoming_chart.html",
    f_menu=[],
):
    # 1. Get Attackers Ordered by Threat Score
    cursor.execute(
        """
        SELECT
            opponent_id,
            threat_score,
            last_incoming_attack_date
        FROM
            attacks_incoming
        WHERE threat_score > 0
        ORDER BY
            threat_score DESC
        """
    )
    opponents = cursor.fetchall()

    # Define SVG dimensions and other parameters
    svg_width = 1000  # Example width
    svg_height = 100  # Example height per opponent
    x_margin = 50  # Example margin
    y_centre = 50  # centre line
    min_radius = 5 # Minimum radius
    max_radius = svg_height / 2 - 10 # Example max radius
    percentile = 0.95 # Exclude the top 5% as outliers
    # ... other parameters for margins, colors, etc.

    # Calculate x_scale (based on fixed width and 7-day time range)
    time_range = timedelta(days=7).total_seconds()  # Total seconds in 7 days
    x_scale = (svg_width - x_margin * 2) / time_range

   # Calculate Percentiles for Respect Change
    cursor.execute(
        f"""
        WITH RespectChange AS (
            SELECT
                ABS(respect_change) AS abs_respect_change
            FROM
                attack_events
            WHERE
                event_date >= DATE('now', '-7 days')
        )
        SELECT
            MAX(abs_respect_change)
        FROM (
            SELECT abs_respect_change, NTILE(100) OVER (ORDER BY abs_respect_change) AS percentile
            FROM RespectChange
        ) AS subquery
        WHERE percentile <= {percentile*100};
        """
    )
    max_respect_change = cursor.fetchone()[0]

    # Determine max_radius (you might want to adjust the scaling factor)
    respect_scaling_factor = max_radius / (max_respect_change**0.5) if max_respect_change > 0 else 0.1

    # HTML for the table
    table_html_str = ""
    # Loop through each opponent
    for opponent_id, threat_score, last_attack_date in opponents:
        # 2. Query for Attacks Involving the Opponent
        cursor.execute(
            f"""
            SELECT
                a.started,
                ae.event_type,
                ae.respect_change,
                ae.user_id, ae.user_name
            FROM
                attack_events ae
            LEFT JOIN attacks a ON ae.attack_id = a.attack_id
            WHERE
                ae.opponent_id = ?
                AND a.started >= '{datetime.now() - timedelta(days=7)}'
            ORDER BY
                a.started
            """,
            (opponent_id,)
        )
        attacks = cursor.fetchall()

        # Check if there were any defends
        has_defends = any(attack[1] == 'defend' for attack in attacks)

        # If no defends, skip this opponent
        if not has_defends:
            continue
        
        # Convert last_attack_date to datetime object if it's not already
        if isinstance(last_attack_date, str):
            last_attack_date = datetime.fromisoformat(last_attack_date)

        # Start building the SVG string
        svg_content = f'<svg width="{svg_width}" height="{svg_height}" >'

        # White background
        # svg_content += f'<rect width="100%" height="100%" fill="white" />'

        # Draw subtle gridlines (days)
        min_time = datetime.now() - timedelta(days=7)  # 7 days ago
        svg_content += f'<line x1="{0}" y1="{y_centre }" x2="{svg_width}" y2="{y_centre}" stroke="gray" />'
 
        for i in range(8):  # 0 to 7 days
            day_width = (svg_width - 2 * x_margin) / 7
            day_x = x_margin + (i) * day_width
            minor_tick_offset = (svg_width - 2 * x_margin) / (7 * 4)
            day_label_dt = min_time + timedelta(days=i)
            day_label_str=day_label_dt.strftime("%a")
            if i==6: day_label_str="Yesterday"
            if i==7: day_label_str="Today"
            svg_content += f'''<text x="{day_x+day_width/2 }" y="{y_centre - 30}" text-anchor="middle" 
                                   font-size="10">{day_label_str} 
                                   <title>!!{day_label_dt.strftime("%Y-%m-%d")}</title></text>'''
            svg_content += f'<line x1="{day_x}" y1="{y_centre - 25}" x2="{day_x}" y2="{y_centre +25}" stroke="gray" />'
            for minor_tick in range(1,4):
                x_mt=day_x+minor_tick_offset*minor_tick
                svg_content += f'<line x1="{x_mt}" y1="{y_centre - 15}" x2="{x_mt}" y2="{y_centre +15}" stroke="gray" stroke-dasharray="2,2" />'

        # Draw 6-hour gridlines
        # for i in range(7 * 4):  # 7 days * 4 intervals per day
        #     x = x_offset + i * (svg_width - 2 * x_offset) / (7 * 4)
        #     svg_content += f'<line x1="{x}" y1="{y_offset - 15}" x2="{x}" y2="{y_offset -15}" stroke="gray" stroke-dasharray="2,2" />'

        # Find the minimum time for this opponent
        min_attack_time = datetime.now() - timedelta(days=7) # 7 days ago 

        # Draw circles for each attack
        last_defend=None
        for attack_date, event_type, respect_change,user_id,user_name in attacks:
            is_retaliation = False    
            if isinstance(attack_date, str):
                attack_date = datetime.fromisoformat(attack_date)
                if event_type=="defend":
                    last_defend= attack_date
                elif last_defend is not None:
                    diff = (attack_date - last_defend).total_seconds()
                    if diff<(5*60):
                        is_retaliation = True    
            day_x = x_margin + (attack_date - min_attack_time).total_seconds() * x_scale
            y = y_centre  # Center vertically
            radius = respect_scaling_factor * math.sqrt(abs(respect_change**0.5))
            if radius < min_radius:
                radius = min_radius
            
            if respect_change == 0:
                color = "orange" if event_type == "defend" else "grey"
            else:
                color = "red" if respect_change < 0 else "green"

            # Add bubble with transparency
            y_shift = +5 if event_type == "defend" else -5
            title=f'''{user_id} {"retaliation"+event_type if is_retaliation else event_type}  {attack_date} respect change = {respect_change} '''
            svg_content += f'''<circle cx="{day_x}" cy="{y+y_shift}" r="{radius}" fill="{color}" 
                fill-opacity="0.6" stroke="{"white" if is_retaliation else "Black"}" 
                stroke-width="{2 if is_retaliation else 0.75}"><title>{title}</title></circle>'''
            
   
        # --- Cumulative Respect Line ---
        svg_content += sparkline_simplified(svg_width, svg_height, x_margin, x_scale, respect_scaling_factor, attacks, min_attack_time)
   
        # (svg_width, svg_height, x_margin, y_centre, x_scale, respect_scaling_factor, attacks, "", min_attack_time)


        # --- End Cumulative Respect Line ---



        svg_content += "</svg>"

        # Add a row to the HTML table
        table_html_str += f"""
        <tr>
            <td>{opponent_id}</td>
            <td>{threat_score:.2f}</td>
            <td>{svg_content}</td>
        </tr>
        """

   

    # 3. HTML Template Substitution
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    final_html = html_template.safe_substitute(
        page_title=title_str,
        title_str=title_str,
        content_html=table_html_str,
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")

    # Menu Item (if needed)
    f_menu.append(_menu_item_for_file(path=path, name="attacks_incomingChart", href=out_filename))
    return f_menu


from datetime import datetime

def sparkline_simplified(svg_width, svg_height, x_margin, x_scale, respect_scaling_factor, attacks, min_attack_time):
    """
    Generates SVG sparkline data with simplified logic and explicit segment transitions.

    Assumes y_centre is effectively 0 for calculations.  Adds y_centre during SVG output.
    """

    y_centre = svg_height / 2  # Calculate y_centre here for drawing
    cumulative_respect = 0
    transitions = []  # List to store (x, y) transition points

    # --- 1. Calculate Transition Points ---

    # Initial transition point (left edge, y=0)
    transitions.append((x_margin, 0))

    # Add transition point PRE attack
    for attack_date, _, respect_change, _, _ in attacks:
        if isinstance(attack_date, str):
            attack_date = datetime.fromisoformat(attack_date)

        x = x_margin + (attack_date - min_attack_time).total_seconds() * x_scale
        y = -cumulative_respect * respect_scaling_factor * 0.1  # y_centre is 0 for calculations
        y = max(min(y, svg_height - 5 - y_centre), 5 - y_centre)
        transitions.append((x, y))

        #update respect
        cumulative_respect += respect_change
        #add POST attack point
        y = -cumulative_respect * respect_scaling_factor * 0.1  # y_centre is 0 for calculations
        y = max(min(y, svg_height - 5 - y_centre), 5 - y_centre)
        transitions.append((x,y))


    # Final transition point (right edge)
    x_end = svg_width - x_margin
    y_end = -cumulative_respect * respect_scaling_factor * 0.1
    y_end = max(min(y_end, svg_height - 5 - y_centre), 5 - y_centre) #Limit
    transitions.append((x_end, y_end))

    # --- 2. Generate SVG Path Data ---
    svg_content = ""

    for i in range(len(transitions) - 1):
        x1, y1 = transitions[i]
        x2, y2 = transitions[i + 1]

        # Determine color based on y2 (the *next* segment's starting point)
        color = "green" if y2 < 0 else "red"

        # --- Horizontal Segment ---
        if i > 0:   #skip drawing line to first x, as its on the 0 axis
            svg_content += f'<line x1="{x1}" y1="{y1 + y_centre}" x2="{x2}" y2="{y1 + y_centre}" stroke="{get_colour(y1)}" stroke-width="2" />'
        
        # --- Vertical Riser (except for the last segment) ---
        #Connects from previous line, to next.
        svg_content += f'<line x1="{x2}" y1="{y1 + y_centre}" x2="{x2}" y2="{y2 + y_centre}" stroke="{color}" stroke-width="2" />'

    return svg_content

def get_colour(y):
    return "green" if y <=0 else "red"








def attacks_overview(conn,cursor,
                        template_file_path="templates/reports/attacks/incoming.html",
                        title_str="Attacks incoming overview",
                        table_title="Scored attackers",
                        path ="reports/attacks",
                        out_filename="incoming.html",
                        f_menu=[]):
    cursor.execute('''SELECT 
                            opponent_id,
                            attacks_7d aS "attacks",
                            members_attacked_7d AS "members attacked",
                            respect_lost_7d AS "respect loss over 7 days",
                            overall_respect_lost "respect loss total",
                            -- respect_gained AS "respect gained from them",
                            -- overall_respect_lost+respect_gained AS "respect NET",
                            -- days_since_last_attack AS "latest attack (days ago)",
                            -- last_attack_date As "latest attack date",
                            threat_score AS "threat score"
                            -- our_attacks_on_them AS "our attacks",
                            --we_retaliated AS "did we retaliate",
                            -- respect_gained AS "respect gained",
                            -- our_attacks_on_them AS "retaliations"
                        FROM attacks_incoming 
                        WHERE attacks_7d>0
                        ORDER BY threat_score DESC ;''')
    table_html_str = html_table(cursor)
    # 
    output_filename = os.path.join(path, out_filename)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(template_file_path, "r") as f:
        html_template = Template(f.read())
    final_html = html_template.safe_substitute(
        page_title=title_str,
        title_str= title_str,
        content_html =table_html_str,
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")  
    f_menu.append(_menu_item_for_file(path=path, name="attacks_incoming", href=out_filename))

    return f_menu 

