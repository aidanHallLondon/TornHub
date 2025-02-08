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
    menu_name="attacks_incoming_chart",
    path="reports/attacks",
    out_filename="incoming_chart.html",
    f_menu=[],
):
    return _draw_attack_chart(
        conn,
        cursor,
        user_type="defenders",
        template_file_path=template_file_path,
        title_str=title_str,
        table_title=table_title,
        menu_name=menu_name,
        path=path,
        out_filename=out_filename,
        f_menu=f_menu,
    )


def outgoing_attack_chart(
    conn,
    cursor,
    template_file_path="templates/reports/attacks/incoming chart.html",
    title_str="Attacks Outgoing Chart",
    table_title="outgoing attacks",
    menu_name="attacks_outgoing_chart",
    path="reports/attacks",
    out_filename="outgoing_chart.html",
    f_menu=[],
):
    return _draw_attack_chart(
        conn,
        cursor,
        user_type="attackers",
        template_file_path=template_file_path,
        title_str=title_str,
        table_title=table_title,
        menu_name=menu_name,
        path=path,
        out_filename=out_filename,
        f_menu=f_menu,
    )


def _draw_attack_chart(
    conn,
    cursor,
    user_type,  # attackers or defenders
    template_file_path,
    title_str,
    table_title,
    menu_name,
    path,
    out_filename,
    f_menu=[],
):
    # menu_name="attacks_incoming_chart"

    # Define SVG dimensions and other parameters
    svg_width = 1000  # Example width
    svg_height = 100  # Example height per opponent
    x_margin = 10  # Example margin
    y_centre = 50  # centre line
    min_radius = 5  # Minimum radius
    max_radius = svg_height / 2 - 4  # Example max radius
    percentile = 0.95  # Exclude the top 5% as outliers
    # ... other parameters for margins, colors, etc.

    # Calculate x_scale (based on fixed width and 7-day time range)
    time_range = timedelta(days=7).total_seconds()  # Total seconds in 7 days
    x_scale = (svg_width - x_margin * 2) / time_range

    # 1. Get Attackers Ordered by Threat Score
    primary_users_list = _get_primary_user_list(cursor, user_type)
    max_respect_sum, max_respect_change = _calculate_percentiles(cursor, percentile)

    # HTML for the table
    table_html_str = ""

    attacks_all,respect_max,respect_sum_max = get_attacks_and_meta_data(cursor, user_type, primary_users_list)
    print(respect_max,respect_sum_max)
    respect_bubble_scaling_factor = max_radius / (respect_max**0.5)if respect_max > 0.1 else 0.1
    respect_sparkline_scaling_factor = max_radius / (respect_sum_max)if respect_sum_max > 0.1 else 0.1
    print(respect_bubble_scaling_factor,respect_sparkline_scaling_factor)
   # Determine max_radius (you might want to adjust the scaling factor)
    # respect_scaling_factor = (
    #     max_radius / (max_respect_change**0.5) if max_respect_change > 0 else 0.1
    # )
    # if user_type == "attackers":
    #     max_radius = max_radius / 10
 

    # Loop through each opponent
    # Query for Attacks Involving the Opponent
    # and draw it
    for (
        prime_user_id,
        prime_user_name,
        prime_user_level,
        interest_score,
        last_event_date,
    ) in primary_users_list:
        # process each user
        attacks = attacks_all[prime_user_id] #_get_attack_events_by_user(cursor, user_type, prime_user_id)
        # if user_type=="attackers": print(attacks)

        # Find the minimum time for this opponent
        min_attack_time = datetime.now() - timedelta(days=7)  # 7 days ago

        # Check if there were any defends
        has_defends = any(attack[1] == "defend" for attack in attacks)

        # If no defends, skip this opponent
        if user_type == "defenders" and not has_defends:
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
            respect_scaling_factor=None,
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
            respect_scaling_factor=respect_bubble_scaling_factor,
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
            respect_scaling_factor=respect_sparkline_scaling_factor,
        )

        svg_content += "</svg>"

        versus_html = get_member_roles_in_the_attacks(prime_user_id, attacks, user_type)

        # Add a row to the HTML table
        table_html_str += f"""
        <tr>
            <td title="{prime_user_name} [{prime_user_id}] Level {prime_user_level if {prime_user_level} else "pending"}, threat score = {interest_score:.2f}">
                <a href="https://www.torn.com/profiles.php?XID={prime_user_id}" target="_blank">
                {prime_user_name} {'<span class="level_label">{' + str(prime_user_level) +'}</span>' if prime_user_level else '' }
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
        user_label=user_type,
        content_html=table_html_str,
    )
    with open(output_filename, "w") as f:
        f.write(final_html)
    print(f"{title_str} saved in {output_filename}")

    # Menu Item (if needed)
    f_menu.append(_menu_item_for_file(path=path, name=menu_name, href=out_filename))
    return f_menu

def get_attacks_and_meta_data(cursor, user_type, primary_users_list):
    '''
    loas the attacks into a list
    go through that list and work out:
    the maximum absolute cummulatative respect and max individual respect_changes per user
    return the list and max values in a tuple
    '''
    percentile=0.95
    respect_sum_list=[]
    respect_max_list=[]
    attacks_all={}
    for (
        prime_user_id,
        prime_user_name,
        prime_user_level,
        interest_score,
        last_event_date,
    ) in primary_users_list:
            attacks = _get_attack_events_by_user(cursor, user_type, prime_user_id)
            attacks_all[prime_user_id] = attacks
            # 
            respect_sum=0
            respect_max=0
            respect_sum_max=0
            for attack in attacks:
                    event_type = attack[1]
                    respect_change = attack[2]
                    respect_max = max(respect_max,abs(respect_change))
                    respect_sum+=respect_change
                    respect_sum_max= max(abs(respect_sum),respect_sum_max)
            respect_max_list.append(respect_max)
            respect_sum_list.append(respect_sum_max)
    respect_max_list.sort()
    respect_sum_list.sort()
    respect_max = respect_max_list[round(len(respect_max_list)*percentile)] if len(respect_max_list)>10 else respect_max_list[-1]
    respect_sum = respect_sum_list[round(len(respect_sum_list)*percentile)] if len(respect_sum_list)>10 else respect_sum_list[-1]
    return (attacks_all,respect_max,respect_sum)


def _get_attack_events_by_user(cursor, user_type, prime_user_id):
    id_field_name = "opponent_id" if user_type == "defenders" else "user_id"
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
                {id_field_name}=? AND started >= '{datetime.now() - timedelta(days=7)}'
            ORDER BY started ASC
            """,
        (prime_user_id,),
    )
    events = cursor.fetchall()
    return events


def _calculate_percentiles(cursor, percentile):
    percentile = 5
    cursor.execute(
        f"""
        SELECT
            (SELECT sum_respect_change
            FROM (
                SELECT SUM(respect_change) AS sum_respect_change,
                    100 * PERCENT_RANK() OVER (ORDER BY SUM(respect_change) DESC) AS percentRank
                FROM attack_events
                WHERE event_date >= DATE('now', '-7 days')
                GROUP BY user_id
            )
            WHERE percentRank >= ?
            ORDER BY percentRank ASC
            LIMIT 1
            ) AS sum_respect_change,

            (SELECT max_respect_change
            FROM (
                SELECT MAX(respect_change) AS max_respect_change,
                    100 * PERCENT_RANK() OVER (ORDER BY MAX(respect_change) DESC) AS percentRank
                FROM attack_events
                WHERE event_date >= DATE('now', '-7 days')
                GROUP BY user_id
            )
            WHERE percentRank >= ?
            ORDER BY percentRank ASC
            LIMIT 1
            ) AS max_respect_change;
        """,(percentile,percentile,))
    max_respect_sum ,max_respect_change = cursor.fetchone()
    return (max_respect_sum, max_respect_change)


def _get_primary_user_list(cursor, user_type):
    # user_type = "attacker" | "defenders"
    user_data_source = (
        "attacks_incoming" if user_type == "defenders" else "attacks_outgoing"
    )

    cursor.execute(
        f"""
        SELECT
            user_id,
            user_name,
            user_level,
            interest_score,
            last_event_date
        FROM {user_data_source}
        WHERE COALESCE(interest_score,0) > 0 -- ignore the tens of thousands of dull rows
        ORDER BY
            interest_score DESC
        """
    )
    user_list = cursor.fetchall()
    print(f'user_list("{user_data_source}") = {len(user_list)}')
    return user_list


def get_member_roles_in_the_attacks(
    prime_user_id, attacks, user_type="defenders"
):  # user_type parameter is unused
    """
    Processes a list of game attacks and returns HTML representing attackers and defenders.

    Args:
        prime_user_id: the user we are building this report for
        attacks: A list of tuples, where each tuple represents an attack
                 and contains the following elements:
                 (attack_date, event_type, respect_change, user_id, user_name,
                  opponent_id, opponent_name, opponent_level, fair_fight,
                  retaliation, group_attack, assist, overseas).
        user_type:  Unused parameter.  Consider removing.

    Returns:
        An HTML string showing attackers and/or defenders.  Returns an empty
        string if there are no attackers or defenders.
    """

    faction_members = {"foes": [], "friends": []}

    for attack in attacks:
        (
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
        ) = attack  # Unpack directly in the loop

        if not opponent_name:
            opponent_name = "Someone"

        existing_foes = {member[0] for member in faction_members["foes"]}
        if opponent_name not in existing_foes:
            faction_members["foes"].append(
                (
                    opponent_name,
                    _torn_profile_anchor_html(
                        "user foe", opponent_id, opponent_name, opponent_level
                    ),
                )
            )
        existing_friends = {member[0] for member in faction_members["friends"]}
        if user_name not in existing_friends:
            faction_members["friends"].append(
                (
                    user_name,
                    _torn_profile_anchor_html("user friend", user_id, user_name, None),
                )
            )
    # Build the HTML using f-strings and join for cleaner formatting.
    foes_html = ""
    if len(faction_members["foes"]):
        foes_links = [member[1] for member in faction_members["foes"]]
        foes_html = f'<div class="foes">{", ".join(foes_links)}</div>'

    defenders_html = ""
    if len(faction_members["friends"]):
        friends_links = [member[1] for member in faction_members["friends"]]
        friends_html = f'<div class="friends">{", ".join(friends_links)}</div>'

    return foes_html + friends_html  # Concatenate the two HTML strings


def _torn_profile_anchor_html(class_name, user_id, user_name, user_level):
    """
    Generates an HTML anchor tag for a Torn profile link.

    Args:
        user_id: The Torn user ID.
        user_name: The Torn user name.
        user_level: The user's level.

    Returns:
        An HTML string representing the anchor tag.
    """
    href= f"https://www.torn.com/profiles.php?XID={user_id}"
    user_level_label = f"({user_level})" if user_level else ''
    return f'<a class={class_name} href="{href}" data-target="{user_id}" target="_blank">{user_name} {user_level_label}</a>'


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
        radius = respect_scaling_factor * (abs(respect_change)**0.5)
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
        class_list = " ".join([(f"u{user_id}" if user_id else ""),(f"u{opponent_id}" if opponent_id else "")])
        svg_content += f"""<circle class="{class_list}" cx="{day_x}" cy="{y+y_shift}" r="{radius}" fill="{color}" 
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
        y = -cumulative_respect * respect_scaling_factor 
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
    cursor.execute(
        f"""
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
"""
    )
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
        _menu_item_for_file(
            path=path, name="attacks_incoming_recent", href=out_filename
        )
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
    cursor.execute(
        f"""
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
"""
    )
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
