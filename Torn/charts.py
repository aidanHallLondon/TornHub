import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

IMAGE_DEFAULT={"WIDTH_INCHES":12,"HEIGHT_INCHES":6}

def plt_save_image(path, out_filname, show_image=False):
    plt.savefig(os.path.join(path, out_filname), bbox_inches="tight")
    if show_image:
        plt.show()

def draw_stackedarea_chart(
    width_inches=IMAGE_DEFAULT["WIDTH_INCHES"],
    height_inches=IMAGE_DEFAULT["HEIGHT_INCHES"],
    title_str=None,
    xaxis_title=None,
    yaxis_title=None,
    xaxis_label_scale=1,
    xaxis_data=[],
    series_data=[],
):
    fig, ax = plt.subplots(figsize=(width_inches, height_inches))  # Use plt.subplots()
    ax.stackplot(xaxis_data, series_data.values(), labels=series_data.keys(), alpha=0.5)
    axes_box = ax.get_position()
    ax.set_position(
        [axes_box.x0 * 0.6, axes_box.y0, axes_box.width * 1, axes_box.height]
    )
    ax.set_xlabel(xaxis_title)
    ax.set_ylabel(yaxis_title)
    ax.set_title(title_str)
    ax.grid(True)
    # Calculate the interval
    interval = max(1, int(len(xaxis_data) / (width_inches / xaxis_label_scale)))
    ax.invert_xaxis()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
    # Add legend outside the chart (with reversed order)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], loc="center left", bbox_to_anchor=(1, 0.5))
