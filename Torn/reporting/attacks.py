import math
import os
from string import Template
import pandas as pd
import numpy as np
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import plt_save_image
from Torn.reporting.build_menus import _menu_item_for_file
from Torn.tables import html_table
from datetime import date, datetime, timedelta


def incoming_attack_chart(
    conn,
    cursor,
    template_file_path="templates/reports/attacks/incoming chart.html",
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
            opponent_name,
            opponent_level,
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
    x_margin = 10  # Example margin
    y_centre = 50  # centre line
    min_radius = 5  # Minimum radius
    max_radius = svg_height / 2 - 10  # Example max radius
    percentile = 0.95  # Exclude the top 5% as outliers
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
    respect_scaling_factor = (
        max_radius / (max_respect_change**0.5) if max_respect_change > 0 else 0.1
    )

    # HTML for the table
    table_html_str = ""
    # Loop through each opponent
    # Query for Attacks Involving the Opponent
    # and draw it
    for (
        opponent_id,
        opponent_name,
        opponent_level,
        threat_score,
        last_attack_date,
    ) in opponents:
        cursor.execute(
            f"""
            SELECT
                started,
                event_type,
                respect_change,
                user_id, user_name, 
				opponent_id, opponent_name,	opponent_level,
				modifier_fair_fight as fair_fight,
				modifier_retaliation as retaliation ,
				modifier_group_attack as group_attack, 
				is_assist as assist,
				modifier_overseas as overseas
            FROM
                attack_events 
            WHERE
                 opponent_id=? AND started >= '{datetime.now() - timedelta(days=7)}'
             ORDER BY started ASC
            """,
            (opponent_id,),
        )
        attacks = cursor.fetchall()

        # Find the minimum time for this opponent
        min_attack_time = datetime.now() - timedelta(days=7)  # 7 days ago

        # Check if there were any defends
        has_defends = any(attack[1] == "defend" for attack in attacks)

        # If no defends, skip this opponent
        if not has_defends:
            continue

        # Start building the SVG string
        svg_content = f'<svg width="{svg_width}" height="{svg_height}" >'

        # Draw subtle gridlines (days)
        svg_content += _draw_axis_and_grid(
            min_attack_time=min_attack_time,
            svg_height=svg_height,
            svg_width=svg_width,
            x_margin=x_margin,
            y_centre=y_centre,
            min_radius=min_radius,
            x_scale=x_scale,
            respect_scaling_factor=respect_scaling_factor,
        )

        svg_content += _draw_attack_event_bubbles(
            attacks=attacks,
            min_attack_time=min_attack_time,
            svg_height=svg_height,
            svg_width=svg_width,
            x_margin=x_margin,
            y_centre=y_centre,
            min_radius=min_radius,
            x_scale=x_scale,
            respect_scaling_factor=respect_scaling_factor,
        )

        svg_content += _draw_cumulative_respect_sparkline(
            attacks,
            min_attack_time=min_attack_time,
            svg_height=svg_height,
            svg_width=svg_width,
            x_margin=x_margin,
            y_centre=y_centre,
            min_radius=min_radius,
            x_scale=x_scale,
            respect_scaling_factor=respect_scaling_factor,
        )

        svg_content += "</svg>"

        versus_html = get_member_roles_in_the_attacks(attacks)

        # Add a row to the HTML table
        table_html_str += f"""
        <tr>
            <td title="{opponent_name} [{opponent_id}] Level {opponent_level if {opponent_level} else "pending"}, threat score = {threat_score:.2f}">
                <a href="https://www.torn.com/profiles.php?XID={opponent_id}" target="_blank">
                {opponent_name} {'<span class="level_label">{' + str(opponent_level) +'}</span>' if opponent_level else '' }
                </a>
            </td>
            <td>{versus_html}</td>
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
    f_menu.append(
        _menu_item_for_file(path=path, name="attacks_incoming_chart", href=out_filename)
    )
    return f_menu


def get_member_roles_in_the_attacks(attacks):
    faction_members = {"attack": [], "defend": []}
    for (
        attack_date,
        event_type,
        respect_change,
        user_id,
        user_name,
        opponent_id,
        opponent_name,
        opponent_level,
        fair_fight,
        retaliation,
        group_attack,
        assist,
        overseas,
    ) in attacks:
        if user_name not in faction_members[event_type]:
            faction_members[event_type].append(user_name)

    versus_html = f"""<div class="defenders"><span class="defender">{'</span> <span class="defender">'.join(faction_members["defend"])}</span></div>"""

    if (
        faction_members["attack"] != faction_members["defend"]
        and len(faction_members["attack"]) > 0
    ):
        versus_html += f"""<div class="attackers"><span class="attacker">{'</span> <span class="attacker">'.join(faction_members["attack"])}</span></div>"""
    return versus_html


def _x_from_date(attack_date, min_attack_time, x_margin, x_scale):
    return (attack_date - min_attack_time).total_seconds() * x_scale


def _get_colour(y):
    return "green" if y <= 0 else "red"


def _draw_axis_and_grid(
    min_attack_time,
    svg_width,
    svg_height,
    x_margin,
    y_centre,
    min_radius,
    x_scale,
    respect_scaling_factor,
):
    end_of_today = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    minor_tick_count = 4
    day_width = (svg_width - 2 * x_margin) / 7
    minor_tick_offset = day_width / minor_tick_count
    #
    svg_content = ""
    svg_content += f'<line x1="{0}" y1="{y_centre }" x2="{svg_width}" y2="{y_centre}" stroke="gray" />'
    #
    for i in range(0, 8):  # 0 to 7 days
        day = end_of_today - timedelta(days=i)
        day_x = _x_from_date(day, min_attack_time, x_margin, x_scale)
        day_label_dt = end_of_today - timedelta(days=i + 1)
        day_label_str = day_label_dt.strftime("%A")
        if i == 1:
            day_label_str = "Yesterday"
        if i == 0:
            day_label_str = "Today"

        svg_content += f"""<text x="{day_x - day_width/2}" y="{y_centre - 30}" text-anchor="middle" 
                                   font-size="10">{day_label_str} 
                                   <title>{day_label_dt.strftime("%Y-%m-%d")}</title></text>"""
        svg_content += f"""<line x1="{day_x}" y1="{y_centre - 25}" 
                               x2="{day_x}" y2="{y_centre +25}" stroke="gray" />"""
        for minor_tick in range(1, minor_tick_count):
            x_mt = day_x + minor_tick_offset * minor_tick
            svg_content += f'<line x1="{x_mt}" y1="{y_centre - 15}" x2="{x_mt}" y2="{y_centre +15}" stroke="gray" stroke-dasharray="2,2" />'
        # Draw 6-hour gridlines
        # for i in range(7 * 4):  # 7 days * 4 intervals per day
        #     x = x_offset + i * (svg_width - 2 * x_offset) / (7 * 4)
        #     svg_content += f'<line x1="{x}" y1="{y_offset - 15}" x2="{x}" y2="{y_offset -15}" stroke="gray" stroke-dasharray="2,2" />'

    return svg_content


def _draw_attack_event_bubbles(
    attacks,
    min_attack_time,
    svg_width,
    svg_height,
    x_margin,
    y_centre,
    min_radius,
    x_scale,
    respect_scaling_factor,
):
    svg_content = ""
    last_defend = None
    for (
        attack_date,
        event_type,
        respect_change,
        user_id,
        user_name,
        opponent_id,
        opponent_name,
        opponent_level,
        fair_fight,
        retaliation,
        group_attack,
        assist,
        overseas,
    ) in attacks:
        attack_date = datetime.fromisoformat(attack_date)
        day_x = _x_from_date(attack_date, min_attack_time, x_margin, x_scale)
        y = y_centre  # Center vertically
        y_shift = +5 if event_type == "defend" else -5
        radius = respect_scaling_factor * math.sqrt(abs(respect_change**0.5))
        if radius < min_radius:
            radius = min_radius

        if respect_change == 0:
            color = "orange" if event_type == "defend" else "grey"
        else:
            color = "red" if respect_change < 0 else "green"
        #
        is_retaliation = False
        if isinstance(attack_date, str):
            attack_date = datetime.fromisoformat(attack_date)
            if event_type == "defend":
                last_defend = attack_date
            elif last_defend is not None:
                diff = (attack_date - last_defend).total_seconds()
                if diff < (5 * 60):
                    is_retaliation = True
        title = f"""attack_date={attack_date},
respect_change={respect_change}
user_name={user_name}
opponent_name={opponent_name}
opponent_level={opponent_level}
fair_fight={fair_fight}
retaliation={('×'+ str(retaliation)) if retaliation!=1 else ''}
group_attack={('×'+ str(group_attack)) if group_attack!=1 else ''}
overseas={('×'+ str(overseas)) if overseas!=1 else ''}
assist={str(assist) if assist>0 else ''}"""

        #
        # Add event bubble with transparency
        y_label = max(y + y_shift + radius + 5, svg_height - y_centre - 10)
        svg_content += f"""<circle cx="{day_x}" cy="{y+y_shift}" r="{radius}" fill="{color}" 
                fill-opacity="0.4" stroke="{"white" if retaliation==1 else "Black"}" 
                stroke-width="{(retaliation+group_attack+overseas) if retaliation+group_attack+overseas!=3 else 0.75}"><title>{title}</title></circle>"""
        # svg_content += f"""<text x="{day_x }" y="{y_label}" text-anchor="middle" font-size="8">
        #                         {user_name}
        #                     <title>{user_name}</title>
        #                     </text>"""
    return svg_content


def _draw_cumulative_respect_sparkline(
    attacks,
    min_attack_time,
    svg_width,
    svg_height,
    x_margin,
    y_centre,
    min_radius,
    x_scale,
    respect_scaling_factor,
):
    """
    Generates SVG sparkline data with simplified logic and explicit segment transitions.

    Assumes y_centre is effectively 0 for calculations.  Adds y_centre during SVG output.
    """

    def _y(cumulative_respect):
        y = -cumulative_respect * respect_scaling_factor * 0.3
        return max(min(y, svg_height - 5 - y_centre), 5 - y_centre)

    y_centre = svg_height / 2  # Calculate y_centre here for drawing
    cumulative_respect = 0
    transitions = []  # List to store (x, y) transition points

    # --- 1. Calculate Transition Points ---
    # Initial transition point (left edge, y=0)
    transitions.append((x_margin, 0))
    for attack in attacks:
        attack_date = attack[0]
        respect_change = attack[2]
        if isinstance(attack_date, str):
            attack_date = datetime.fromisoformat(attack_date)
        x = _x_from_date(attack_date, min_attack_time, x_margin, x_scale)
        transitions.append((x, _y(cumulative_respect)))  # add Pre attack point
        cumulative_respect += respect_change
        transitions.append((x, _y(cumulative_respect)))  # add POST attack point
    # Final transition point (right edge)
    transitions.append(
        (
            _x_from_date(datetime.now(), min_attack_time, x_margin, x_scale),
            _y(cumulative_respect),
        )
    )

    # --- 2. Generate SVG Path Data ---
    svg_content = ""
    for i in range(len(transitions) - 1):
        x1, y1 = transitions[i]
        x2, y2 = transitions[i + 1]
        # Determine color based on y2 (the *next* segment's starting point)
        color = "green" if y2 < 0 else "red"
        # --- Horizontal Segment ---
        if i > 0:  # skip drawing line to first x, as its on the 0 axis
            svg_content += f'<line x1="{x1}" y1="{y1 + y_centre}" x2="{x2}" y2="{y1 + y_centre}" stroke="{_get_colour(y1)}" stroke-width="2" />'
        # --- Vertical Riser (except for the last segment) ---
        svg_content += f'<line x1="{x2}" y1="{y1 + y_centre}" x2="{x2}" y2="{y2 + y_centre}" stroke="{color}" stroke-width="2" />'

    return svg_content


def attacks_incoming_overview(
    conn,
    cursor,
    template_file_path="templates/reports/attacks/incoming.html",
    title_str="Attacks incoming overview - 7 days",
    table_title="Scored attackers",
    path="reports/attacks",
    out_filename="incoming.html",
    f_menu=[],
):
    cursor.execute(f'''
    SELECT
            started,
            user_name, 
            event_type,
            opponent_name,	opponent_level
            respect_change,
            is_assist as assist,
            modifier_fair_fight as fair_fight,
            modifier_retaliation as retaliation ,
            modifier_group_attack as group_attack, 
            modifier_overseas as overseas,
            user_id,
            opponent_id
            FROM
                attack_events 
            WHERE
                 event_type="defend" and started >= '{datetime.now() - timedelta(days=7)}'
             ORDER BY started DESC
''')
    table_html_str = html_table(cursor)
    #
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
    f_menu.append(
        _menu_item_for_file(path=path, name="attacks_incoming_recent", href=out_filename)
    )

    return f_menu

def attacks_overview(
    conn,
    cursor,
    template_file_path="templates/reports/attacks/incoming.html",
    title_str="Attacks list - 7 days",
    table_title="Scored attackers",
    path="reports/attacks",
    out_filename="attacks_recent.html",
    f_menu=[],
):
    cursor.execute(f'''
    SELECT
            started,
            user_name, 
            event_type,
            opponent_name,	opponent_level
            respect_change,
            is_assist as assist,
            modifier_fair_fight as fair_fight,
            modifier_retaliation as retaliation ,
            modifier_group_attack as group_attack, 
            modifier_overseas as overseas,
            user_id,
            opponent_id
            FROM
                attack_events 
            WHERE
                 event_type="attack" and started >= '{datetime.now() - timedelta(days=7)}'
             ORDER BY started DESC
''')
    table_html_str = html_table(cursor)
    #
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
    f_menu.append(
        _menu_item_for_file(path=path, name="attacks_recent", href=out_filename)
    )

    return f_menu
