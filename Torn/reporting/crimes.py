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

def crimeexp_rank_bump_plot(
    conn,
    cursor,
    user_colourList,
    title="Members' Crime Experience Rank over time ",
    title_add_limits=True,
    path="reports/faction/crimes",
    out_filename="Crime_experience",
    limit_window=(1,100),
    figsize_in=(10,None),# width, height in inches - set height to None for auto
    line_width=5,
    show_image=False,
):
    # get user colours - user_colour_dict.get(user_name, "grey")
    user_colour_dict = {user_name: color for _, _, user_name, color in user_colourList}
    # clean up the parmameters    
    limit_window=(max(min(limit_window[0],100),1),max(min(limit_window[1],100),1)) # (1-100,1-100)
    if figsize_in[1] is None: # auto height
        figsize_in = (figsize_in[0],2+(figsize_in[0]-2) * (1.8 * (limit_window[1]-limit_window[0]+1)/100))
    if title_add_limits==True:
        if limit_window!=(1,100):
            if limit_window[0]==1:
                title+=f" — for the top {limit_window[1]}"
            elif limit_window[1]==100:
                title+=f" - for the lowest {100-limit_window[0]}"
            else: title+=f" - for ranks {limit_window[0]} to {limit_window[1]}"
    #
    cursor.execute(
        f"""
        SELECT batch_date, history.user_id, users.name as user_name, crimeexp_rank as rank, position_in_faction as role
        FROM crimeexp_ranks_history history
        LEFT JOIN users 
        ON users.user_id = history.user_id
        WHERE rank BETWEEN {limit_window[0]} and {limit_window[1]}
        ORDER BY batch_date ASC, crimeexp_rank DESC
    """
    )
    data = cursor.fetchall()
    npData = pd.DataFrame(data, columns=["date", "user_id", "user_name", "rank", "role"])
    npData["date"] = pd.to_datetime(npData["date"])
    rank_df = npData.pivot(index="date", columns=["user_name","role"], values="rank")

    fig, ax = plt.subplots(figsize=(figsize_in[0],figsize_in[1]))

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
            ax.scatter(x_values, y_values, color="White",marker=line_style[1], s=120,zorder=19)
            ax.scatter(x_values, y_values, color=line_style[2] if line_style[2] else color,marker=line_style[1], s=60,zorder=20)
            # Add annotations for user_name and role
            user_name_annotation=ax.annotate(
                f'{user_name}',
                (interp_x[-1] + 0.1, interp_y[-1]),
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
                (interp_x[-1] + 0.1, interp_y[-1]),
                xytext=(2 + user_name_bbox.width*44 ,0),  # Adjust offset based on username length
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
    ax.set_ylabel("Crime Experience Rank")
    ax.invert_yaxis()
    # chart
    ax.set_title(title)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    #
    plt_save_image(path, out_filename, show_image=show_image, clear_image=True)

def get_annotation_bbox(fig, annotation):
    renderer = fig.canvas.get_renderer()
    return annotation.get_window_extent(renderer=renderer)


