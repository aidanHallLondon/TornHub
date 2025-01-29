from itertools import zip_longest
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
import os

# import numpy as np

IMAGE_DEFAULT = {"WIDTH_INCHES": 12, "HEIGHT_INCHES": 6}
user_colourList=None

def init(conn,cursor):
    return {'colourList':load_user_colourList_for_charts(conn, cursor, cmap="tab20c")}

def plt_save_image(path, out_filename, show_image=False, clear_image=True):
    if path is not None and out_filename is not None:
        if not os.path.exists(path):
            os.makedirs(path)
        plt.savefig(os.path.join(path, out_filename), bbox_inches="tight")
    if show_image:
        plt.show()
    if clear_image:
        plt.clf()

def load_user_colourList_for_charts(conn,cursor, cmap='magma'):
    '''
    color_for_named_user = user_colour_dict.get(user_name, "grey")
    '''
    global user_colourList
    cursor.execute('''SELECT crimeexp_rank AS rank, user_id, user_name FROM crimeexp_ranks ORDER BY 1 ASC''')
    ranks= cursor.fetchall()
    num_players = len(ranks)
    cmap = cm.get_cmap(cmap)
    # colors = cmap(np.linspace(0, 1, num_players))
    colors = [cmap(i % cmap.N) for i in range(num_players)] 
    # Add colors to the rank data
    user_colourList = [(rank[0], rank[1], rank[2], colors[i]) for i, rank in enumerate(ranks)]
    return user_colourList # [ (rank, user_id, user_name, color),...]

def group_small_segments(
    labels, sizes, other_category_label="Others", other_threshold=0.05
):
    """Groups small segments in a pie chart data into an "Other" category.

    Args:
        labels: List of labels for the slices.
        sizes: List of sizes for the slices.
        other_category_label: Label for the "Other" category.
        other_threshold: Threshold (as a fraction of total size) below which segments are grouped into "Other".

    Returns:
        A tuple containing the new lists of labels and sizes with small segments grouped.
    """
    total_size = sum(sizes)
    threshold = total_size * other_threshold

    other_size = 0
    new_labels = []
    new_sizes = []
    for label, size in zip(labels, sizes):
        if size < threshold:
            other_size += size
        else:
            new_labels.append(label)
            new_sizes.append(size)
    if other_size > 0:
        new_labels.append(other_category_label)
        new_sizes.append(other_size)

    return new_labels, new_sizes


def draw_donut_chart(
    width_inches=IMAGE_DEFAULT["WIDTH_INCHES"],
    height_inches=IMAGE_DEFAULT["HEIGHT_INCHES"],
    title=None,
    startangle=90,  # default to the top 12 o'clock postion
    donut_width=0.3,
    autopct= "%1.1f%%",
    series=None,  # pass EITHER series OR labels and sizes [ (size, label)...]
    labels=None,
    sizes=None,
    missing_label="no name",
    other_category_label="Others",
    other_threshold=0.05,  # Add threshold parameter (default 5%)
    path=None,
    out_filename=None,
    show_image=True,
):
    global user_colourList
    if series is None:
        raise ValueError(
            "'series' is required : either a list of (size,label) tuples or values with the 'labels' in the labels param"
        )

    # if series is not paired tuples as expected try to build that from a plain series of numbers and the labels
    if not all(isinstance(item, tuple) and len(item) == 2 for item in series):
        # Check it is a list of numbers 
        if  all(isinstance(item, (int, float)) for item in series):
            # process the two lists into one list of tuples
            if labels == None:
                labels = []
            data = list(zip_longest(labels, series, fillvalue=None))
        else:
            raise ValueError(
                "'series' must be a list of numbers (or a list of (size,label) tuples)"
            )
    series = [
        (l if l is not None else missing_label, s if s is not None and s > 0 else 0)
        for l, s in series
    ]
    #
    if series == None:
        # clean up sizes and labels to match and not have pesky None values
        if not sizes or sizes is None or sum(s for s in sizes if s is not None) == 0:
            return None
        series = [
            (l if l is not None else missing_label, s if s is not None and s > 0 else 0)
            for l, s in list(zip_longest(labels, sizes, fillvalue=None))
        ]
    if sum(size for label, size in series if size is not None) == 0:
        return None
    series, other = group_small_segments(series, other_threshold=0.2, min_other_count=2)

    # labels = [l if l is not None else 'no name' for l in labels] + ['no name'] * (len(sizes) - len(labels))
    # sizes = [s if s is not None and s > 0 else 0 for s in sizes] + [0] * (len(labels) - len(sizes))
    # labels, sizes = group_small_segments(labels, sizes, other_category_label="Others", other_threshold=0.1,min_other_count=2)
    # build a donut
    new_labels = [label for label, size in series]
    new_sizes = [size for label, size in series]
    if autopct is None:
        autopct = _make_autopct(new_sizes)
    plt.figure()  # Create a new figure for the pie chart

    # Get colors for the given labels (user_names)
    colors = []
    if user_colourList:
        for label in new_labels:
            for rank, user_id, user_name, color in user_colourList:
                if user_name == label:
                    colors.append(color)
                    break
            else:
                colors.append('gray')  # You can change this to any default color
    plt.pie(
        new_sizes,
        labels=new_labels,
        colors=colors ,  # Use the matched colors
        autopct=autopct,
        startangle=startangle,
        wedgeprops=dict(width=donut_width),
    )
    plt.title(title)
    plt.axis("equal")

    plt_save_image(
        path=path,
        out_filename=out_filename,
        show_image=False,
    )
def _make_autopct(values, format_string = '{value:d}\n({percentage:.2f}%)'):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0))
        return format_string.format(percentage=pct,value=val)
    return my_autopct

def group_small_segments(
    data_series,
    other_category_label="Others",
    other_show_count=True,
    other_threshold=0.05,
    min_other_count=2,
):
    """
    Groups small segments in a pie chart data into an "Other" category,
    preserving the original order. Only groups segments if there are at least
    `min_other_count` items below the threshold.

    Args:
        data_series: List of tuples (label, size) for the slices.
        other_category_label: Label for the "Other" category.
        other_threshold: Threshold (as a fraction of total size) below which segments are grouped into "Other".
        min_other_count: Minimum number of segments required to create the "Other" category.

    Returns:
        A tuple containing:
            - new_series: List of tuples (label, size) with small segments grouped into "Other".
            - other: List of tuples (label, size) that were grouped into "Other".
    """
    total_size = sum(size for label, size in data_series)
    threshold = total_size * other_threshold

    # Sort by size
    data_series.sort(key=lambda item: item[1])

    new_series = data_series.copy()
    other = []

    for label, size in data_series:
        if size < threshold and new_series:
            other.append(
                new_series.pop(0)
            )  # Remove from the beginning since the list is sorted
            threshold -= size

    if len(other) >= min_other_count:
        # new_series.append((other_category_label, sum(size for label, size in other)))
        new_series.insert(
            0,
            (
                other_category_label + (f" ({len(other)})" if other_show_count else ""),
                sum(size for label, size in other),
            ),
        )
        return new_series, other
    else:
        # Not enough segments for "Other", return original list and empty other list
        return data_series, []

def generate_colors_by_username(userLabels):
  # Get colors for the given labels (user_names)
    colors = []
    if user_colourList:
        for label in userLabels:
            for rank, user_id, user_name, color in user_colourList:
                if user_name == label:
                    colors.append(color)
                    break
            else:
                colors.append('gray')  # You can change this to any default color
    return colors

def draw_stackedarea_chart(
    width_inches=IMAGE_DEFAULT["WIDTH_INCHES"],
    height_inches=IMAGE_DEFAULT["HEIGHT_INCHES"],
    title=None,
    xaxis_title=None,
    yaxis_title=None,
    xaxis_label_scale=1,
    xaxis_data=[],
    series_data=[],
):
    fig, ax = plt.subplots(figsize=(width_inches, height_inches))  # Use plt.subplots()

    colors=generate_colors_by_username(userLabels=series_data.keys())
    ax.stackplot(xaxis_data, series_data.values(), labels=series_data.keys(),colors=colors, alpha=1)
    axes_box = ax.get_position()
    ax.set_position(
        [axes_box.x0 * 0.6, axes_box.y0, axes_box.width * 1, axes_box.height]
    )
    ax.set_xlabel(xaxis_title)
    ax.set_ylabel(yaxis_title)
    ax.set_title(title)
    ax.grid(True)
    # Calculate the interval
    interval = max(1, int(len(xaxis_data) / (width_inches / xaxis_label_scale)))
    ax.invert_xaxis()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
    # Add legend outside the chart (with reversed order)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], loc="center left", bbox_to_anchor=(1, 0.5))
