from datetime import datetime
from matplotlib import text
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import plt_save_image

def _sigmoid_pairwise(xs, ys, smooth=8, n=1000):
    """
    Work out the sigmoid curve control points based on a pair of points in a bump chart
    Uses NumPy data
    Args
        xs - np list of relative x axis positions (ordinals from dates)
        ys - np list of date and rank for one user
        smooth - real >=8
        n - int number of steps
    Returns
        (x,y)
        x is a set of x coordinates for the line segments to pass to .plot
        y is a set of y coordinates for the line segments to pass to .plot
    """
    def _sigmoid(xs, ys, smooth=smooth, n=n):
        (x_from, x_to), (y_from, y_to) = xs, ys
        xs = np.linspace(-smooth, smooth, num=n)[:, None]
        ys = np.exp(xs) / (np.exp(xs) + 1)
        return (
            ((xs + smooth) / (smooth * 2) * (x_to - x_from) + x_from),
            (ys * (y_to - y_from) + y_from),
        )

    xs = np.lib.stride_tricks.sliding_window_view(xs, 2)
    ys = np.lib.stride_tricks.sliding_window_view(ys, 2)
    interp_x, interp_y = _sigmoid(xs.T, ys.T, smooth=smooth, n=n)
    return interp_x.T.flat, interp_y.T.flat

# TODO use this approach in the crome.py version too and use a shared module
def _reviver_rank_bump_plot_sql_ctes():
    return """
        WITH RECURSIVE date_series(date_point) AS (
            SELECT DATE('now', '-182 days') AS date_point
            UNION ALL
            SELECT DATE(date_point, '+7 day') AS date_point
            FROM date_series
            WHERE date_point < DATE('now')
        ),
        revives_slice AS (
            SELECT
                ds.date_point,
                DENSE_RANK() OVER (PARTITION BY ds.date_point ORDER BY COUNT(CASE WHEN rr.result = 'success' THEN 1 END) DESC, MAX(chance) DESC) AS rank_count,  -- Rank by count, then chance
                DENSE_RANK() OVER (PARTITION BY ds.date_point ORDER BY MAX(chance) DESC, COUNT(CASE WHEN rr.result = 'success' THEN 1 END) DESC) AS rank_skill,  -- Rank by chance, then count
                rr.reviver_id AS user_id,
                rr.reviver_name AS user_name,
                r_user.position_in_faction as role,
                COUNT(CASE WHEN rr.result = 'success' THEN 1 END) AS successful_revives,
                round(10*(MAX(chance)-90)) AS skill_est
            FROM date_series AS ds
            LEFT JOIN revives AS rr ON DATE(rr.timestamp) <= ds.date_point
            INNER JOIN users AS r_user ON rr.reviver_id = r_user.user_id AND r_user.is_in_faction = 1
            GROUP BY ds.date_point, rr.reviver_id, rr.reviver_name
        )"""

def reviver_count_bump_plot(
    conn,
    cursor,
    user_colourList,
    title="Members' Revive Experience Rank over time ",
    title_add_limits=True,
    path="reports/revives",
    out_filename="Reviver_experience",
    limit_window=(1,None),
    figsize_in=(14,None),# width, height in inches - set height to None for auto
    line_width=5,
    show_image=False,
):
    if limit_window==None: limit_window[1,None]
    if limit_window[1]==None:
        cursor.execute('''SELECT count(*) as reviver_count FROM revivers''')
        reviver_count=cursor.fetchone()[0]
        limit_window=(limit_window[0],reviver_count)
    cursor.execute(
        f"""{_reviver_rank_bump_plot_sql_ctes()}
        SELECT date_point, user_id, user_name,  rank_count as rank,  role 
        FROM revives_slice
        order by date_point DESC, rank ASC
    """ )
    data = cursor.fetchall()

    return bump_plot(    
        data,
        user_colourList,
        title=title,
        title_add_limits=title_add_limits,
        path=path,
        out_filename=out_filename,
        figsize_in=figsize_in,
        limit_window=limit_window,
        show_image=show_image
        )

def reviver_skill_bump_plot(
    conn,
    cursor,
    user_colourList,
    title="Members' Reviver Skill Rank over time ",
    title_add_limits=True,
    path="reports/revives",
    out_filename="Reviver_skill",
    limit_window=(1,None),
    figsize_in=(24,None),# width, height in inches - set height to None for auto
    line_width=5,
    show_image=False,
):
    if limit_window==None: limit_window[1,None]
    if limit_window[1]==None:
        cursor.execute('''SELECT count(*) as reviver_count FROM revivers''')
        reviver_count=cursor.fetchone()[0]
        limit_window=(limit_window[0],reviver_count)
    cursor.execute(
        f"""{_reviver_rank_bump_plot_sql_ctes()}
        SELECT date_point, user_id, user_name,  rank_skill as rank,  role  -- rank_skill, successful_revives, skill_est, role
        FROM revives_slice
        order by date_point DESC, rank ASC
    """ )

    return bump_plot(    
        cursor.fetchall(),
        user_colourList,
        title=title,
        title_add_limits=True,
        path=path,
        out_filename=out_filename,
        figsize_in=figsize_in,
        limit_window=limit_window,
        show_image=show_image )

def bump_plot(    
        data,
        user_colourList,
        title,
        title_add_limits,
        path,
        out_filename,
        limit_window=(1,20),
        figsize_in=(12,8),# width, height in inches - set height to None for auto
        line_width=5,
        show_image=False,):
    y_label="Reviver"
    if figsize_in[1]==None:
        figsize_in= (figsize_in[0],2 + 0.25 * ( limit_window[1] -limit_window[0]))
    npData = pd.DataFrame(data, columns=["date", "user_id", "user_name", "rank", "role"])
    npData["date"] = pd.to_datetime(npData["date"])
    rank_df = npData.pivot(index="date", columns=["user_name","role"], values="rank")
    fig, ax = plt.subplots(figsize=(figsize_in[0],figsize_in[1]))

    user_colour_dict = {user_name: color for _, _, user_name, color in user_colourList}
    line_styles = {
        "Recruit": ((.4, 1),'o','Grey'),     
        "Member": ((.4, .4),'d',None),     
        "Astro Guard": ((4,.15),'o',None),  
        "Star Explorer": ((1,0),'P','Black'),  
        "Galactic Commander":((1,0),"*",'Black'),
        "Co-leader":((1,0),"*",'Black'),
        "Leader":((1,0),"*",'Orange'),    }

    for user in rank_df.columns:
        user_name,role =user
        y_values = rank_df[user]
        x_values = pd.to_datetime(rank_df.index).map(datetime.toordinal)
        color = user_colour_dict.get(user_name, "grey")
        if not y_values.isnull().all():
            interp_x, interp_y = _sigmoid_pairwise(x_values, y_values)
            line_style = line_styles.get(role, ((1, 0),"o",None))
            ax.plot(interp_x, interp_y, lw=line_width, dashes=line_style[0],color=color,zorder=10)
            ax.scatter(x_values, y_values, color="White",marker=line_style[1], s=60,zorder=19)
            ax.scatter(x_values, y_values, color=line_style[2] if line_style[2] else color,marker=line_style[1], s=30,zorder=20)
            # Add annotations for user_name and role
            user_name_annotation=ax.annotate(
                f'{user_name}',
                (interp_x[-1] + 1.6, interp_y[-1]),
                xytext=(2, 0),  # Reduced xytext
                textcoords="offset points",
                va="center",
                ha="left",
                color=color,
                fontsize=9,
            )
            user_name_bbox = get_annotation_bbox(fig, user_name_annotation).transformed(ax.transData.inverted())
            ax.annotate(
                f'{role}',
                (interp_x[-1] + 1.5, interp_y[-1]),
                xytext=(2 ,9),  # Adjust offset based on username length
                # xytext=(2 + user_name_bbox.width*44 ,0),  # Adjust offset based on username length
                textcoords="offset points",
                va="center",
                ha="left",
                color='grey',  # Grey color for the role
                fontsize=5,    # Smaller font size
            )
    # x axis
    ax.set_xticks(pd.to_datetime(rank_df.index).map(datetime.toordinal))
    ax.set_xticklabels(rank_df.index.strftime("%Y-%m-%d"), rotation=45)
    # y axis
    ax.set_ylim(limit_window[0]-0.5, limit_window[1]+0.75) 
    ax.set_yticks([i for i in range(limit_window[0], limit_window[1]+1)])
    ax.set_ylabel(y_label)
    ax.invert_yaxis()
    # chart
    ax.set_title(title)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # fig.tight_layout()
    #
    plt_save_image(path, out_filename, show_image=show_image, clear_image=True)
  
def get_annotation_bbox(fig, annotation):
    renderer = fig.canvas.get_renderer()
    return annotation.get_window_extent(renderer=renderer)


