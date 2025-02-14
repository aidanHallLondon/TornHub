from datetime import datetime
import sqlite3

from tabulate import tabulate 
from Torn.db._globals import DB_CONNECTPATH
from Torn.db.faction_upgrades import create_faction_upgrades, update_faction_upgrades
from Torn.db.items import create_item_listings, update_item
from Torn.db.revives import create_revives, update_revives
from Torn.manageDB import initDB, updateDB, dumpResults

# from Torn.db.faction import create_faction, update_faction
from Torn.api import (
    _api_raw_call,
    _getApiURL,
    cached_api_call,
    cached_api_paged_call,
    date_to_unix,
)
import json
from Torn.db.attacks import create_attacks, update_attacks

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

selectionsDone = [
    "crimes",
    "crimeexp",
    "members",
    "basic",
    "currency",
    "hof",
    "stats",
    "timestamp",
    "lookup",
    "upgrades",
    "applications",
    "armor",
    "boosters",
    "medical",
    "temporary",
    "weapons",
    "drugs",
    "caches",
    "cesium",
    "attacks",
    "attacksfull",
    "revives",
    "revivesfull",
]
selections = [
    "chain",
    "chainreport",
    "chains",
    "territory",
    "contributors",  # members but nothing useful in the data so far
    "donations",
    "positions",
    "reports",
    "rankedwars",
    "wars",
    "news",
    "mainnews",
    "armorynews",
    "attacknews",
    "crimenews",
    "territorynews",
    "membershipnews",
    "fundsnews",
]


# Applications ----------------------------------------------------------------


def main():
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    initDB(conn, cursor)  # creates the database structure if not already done
    # conn.commit()
    # # data=cursor.execute("""DELETE  FROM revives """)

    # updateDB(conn,cursor)  # updates the data using the API

    # conn.commit()
    loadit(conn, cursor)
    conn.commit()
    conn.close()


def loadit(conn, cursor):
    mode = "plot"
    if mode == "data":
        create_item_listings(conn, cursor, force=True)
        update_item(conn, cursor, 651)
        update_item(conn, cursor, 652)
        update_item(conn, cursor, 653)
        update_item(conn, cursor, 654)
        update_item(conn, cursor, 332)
    else:
        plot(conn, cursor)


# ===========================================================
1

upper_margin_factor = 20/100
lower_margin_factor = 5/100
outlier_threshold=200/100

def _filter_extreme_outliers(df_raw, price_trend_series):
    global upper_margin_factor, lower_margin_factor,outlier_threshold
    df_raw = df_raw.copy()
    df_trend = price_trend_series.to_frame(name="trend_price").reset_index()
    df_trend.columns = ["measure", "trend_price"]

    df_raw["measure"] = df_raw["measure"].astype(float)
    df_trend["measure"] = df_trend["measure"].astype(float)
    df_raw = df_raw.sort_values("measure")
    df_trend = df_trend.sort_values("measure")

    trend_dict = df_trend.set_index("measure")["trend_price"].to_dict()
    trend_measures = sorted(trend_dict.keys())
    interpolated_trend_prices = []

    for measure in df_raw["measure"]:
        if measure in trend_dict:
            interpolated_trend_prices.append(trend_dict[measure])
        else:
            lower_bound = None
            upper_bound = None
            for trend_measure in reversed(trend_measures):
                if trend_measure < measure:
                    lower_bound = trend_measure
                    break
            for trend_measure in trend_measures:
                if trend_measure > measure:
                    upper_bound = trend_measure
                    break

            if lower_bound is None and upper_bound is None:
                raise ValueError("No trend data found.")
            elif lower_bound is None:
                interpolated_trend_prices.append(trend_dict[upper_bound])
            elif upper_bound is None:
                interpolated_trend_prices.append(trend_dict[lower_bound])
            else:
                x1, y1 = lower_bound, trend_dict[lower_bound]
                x2, y2 = upper_bound, trend_dict[upper_bound]
                interpolated_price = np.where(
                    x1 == x2,
                    y1,
                    y1 + (y2 - y1) * (measure - x1) / (x2 - x1)
                )
                interpolated_trend_prices.append(interpolated_price)

    df_raw["trend_price"] = interpolated_trend_prices
    df_raw["price_diff"] = df_raw["price"] - df_raw["trend_price"]
    df_raw["outlier"] = df_raw["price"] > (df_raw["trend_price"] * outlier_threshold)
    df_filtered = df_raw[~df_raw["outlier"]].copy()

    upper_margin = df_filtered["trend_price"] * upper_margin_factor
    lower_margin = df_filtered["trend_price"] * lower_margin_factor

    df_filtered.loc[:, "above_trend"] = df_filtered["price_diff"] > upper_margin
    df_filtered.loc[:, "on_trend"] = (df_filtered["price_diff"] <= upper_margin) & (df_filtered["price_diff"] >= -lower_margin)
    df_filtered.loc[:, "below_trend"] = df_filtered["price_diff"] < -lower_margin

    return df_filtered, df_raw["outlier"]



def _calculate_bin_percentiles(
    df, bin_size, percentile, smoothing_window=1, smoothing_polyorder=1
):
    """
    Calculates percentile prices for bins, with smoothing.  Handles empty bins.
    """
    min_measure = df["measure"].min()
    max_measure = df["measure"].max()
    bins = np.arange(min_measure, max_measure + bin_size, bin_size)
    df["bin"] = pd.cut(df["measure"], bins=bins, labels=False, include_lowest=True)

    # Calculate percentiles within each bin, handling empty bins
    bin_percentiles = df.groupby("bin")["price"].quantile(percentile).reset_index()

    # Get bin midpoints
    bin_midpoints = [
        bins[i] + (bins[i + 1] - bins[i]) / 2 for i in bin_percentiles["bin"]
    ]
    bin_percentiles["measure"] = bin_midpoints

    # Convert to Series
    bin_percentiles_series = pd.Series(
        bin_percentiles["price"].values, index=bin_percentiles["measure"]
    )

    # --- KEY CHANGE: Forward Fill NaNs ---
    bin_percentiles_series = bin_percentiles_series.ffill()
    # --- Also backfill in case first bin is empty ---
    bin_percentiles_series = bin_percentiles_series.bfill()

    # # Smoothing (only if enough data points)
    # if len(bin_percentiles_series) >= smoothing_window:
    #     try:  # Add a try-except block
    #         smoothed_values = savgol_filter(bin_percentiles_series, smoothing_window, smoothing_polyorder)
    #         bin_percentiles_series = pd.Series(smoothed_values, index=bin_percentiles_series.index)
    #     except ValueError as e:
    #         print(f"Error during smoothing: {e}")
    #         print("Likely not enough data points after binning and outlier removal.")
    #         print("Consider reducing smoothing_window or increasing bin_size.")
    #         #  Could return the unsmoothed series here, or raise the exception.
    #         # raise e # Re-raise the exception for now

    return bin_percentiles_series


def _plot_price_vs_measure(df_raw, df_filtered, price_trend_series, original_outliers):
    """Creates the scatter plot with different upper and lower margins."""
    global upper_margin_factor, lower_margin_factor,outlier_threshold
    plt.figure(figsize=(10, 6))

    # Calculate margins based on *interpolated* trend_price in df_filtered
    upper_margin = df_filtered["trend_price"] * upper_margin_factor
    lower_margin = df_filtered["trend_price"] * lower_margin_factor

    # Classify points based on the margins
    above_trend = df_filtered["price_diff"] > upper_margin
    on_trend = (df_filtered["price_diff"] <= upper_margin) & (df_filtered["price_diff"] >= -lower_margin)
    below_trend = df_filtered["price_diff"] < -lower_margin

    # Plot categorized points (filtered data)
    plt.scatter(
        df_filtered.loc[above_trend, "measure"],
        df_filtered.loc[above_trend, "price"],
        color="red",
        label="Above Trend",
        alpha=0.5,
    )
    plt.scatter(
        df_filtered.loc[on_trend, "measure"],
        df_filtered.loc[on_trend, "price"],
        color="blue",
        label="On Trend",
        alpha=0.5,
    )
    plt.scatter(
        df_filtered.loc[below_trend, "measure"],
        df_filtered.loc[below_trend, "price"],
        color="green",
        label="Below Trend",
        alpha=0.5,
    )

    # Interpolated trend line
    plt.plot(
        df_filtered["measure"],
        df_filtered["trend_price"],
        color="orange",
        lw=2,
        linestyle='-',
        label="Interpolated Trend",
        alpha=.7
    )

    # Upper and Lower Margin lines
    plt.plot(
        df_filtered["measure"],
        df_filtered["trend_price"] + upper_margin,
        color="red",
        lw=1,
        linestyle='--',
        alpha=0.25,
        label=f"Upper Margin ({upper_margin_factor*100:.0f}%)" # Add label
    )
    plt.plot(
        df_filtered["measure"],
        df_filtered["trend_price"] - lower_margin,
        color="green",  # Different color for lower margin
        lw=1,
        linestyle='--',
        alpha=0.25,
        label=f"Lower Margin ({lower_margin_factor*100:.0f}%)" # Add label
    )

    # # All data points (grey)
    # plt.scatter(
    #     df_raw["measure"],
    #     df_raw["price"],
    #     color="grey",
    #     label="All Data",
    #     alpha=0.25,
    # )
# 


    plt.yscale("log")
    xmin, xmax = plt.xlim()
    ymin, ymax = plt.ylim()
    padding_x = (xmax - xmin) * 0.0
    padding_y = (ymax - ymin) * 0.0
    plt.xlim(xmin - padding_x, xmax + padding_x)
    plt.ylim(ymin - padding_y, ymax + padding_y)

    # Outlier points (using original_outliers)
    plt.scatter(
        df_raw[original_outliers]["measure"],
        df_raw[original_outliers]["price"],
        color="red",
        label="Excluded Outliers",
        marker="x",
        alpha=.15,
        s=50,
    )

    plt.xlabel("Measure")
    plt.ylabel("Price")
    plt.title("Item Price vs. Measure")
    plt.legend()  # Show the legend
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot(
    conn,
    cursor,
    item_id=332,
    bin_factor=12,
    percentile=0.05,
    smoothing_window=5,
    smoothing_polyorder=2,
    outlier_multiplier=2.0,
):
    """Main plotting function."""
    cursor.execute(
        f"""SELECT item_uid, stat_armor as measure, price
                 FROM item_listings
                 WHERE item_id={item_id}
                 ORDER BY measure ASC;"""
    )
    raw_data = cursor.fetchall()
    df_raw = pd.DataFrame(raw_data, columns=["item_uid", "measure", "price"])

    min_measure = df_raw["measure"].min()
    max_measure = df_raw["measure"].max()
    count = len(df_raw)
    bin_size = bin_factor * (max_measure - min_measure) / count

    # Calculate trend *before* filtering, for use in outlier detection
    price_trend_series = _calculate_bin_percentiles(
        df_raw, bin_size, percentile, smoothing_window, smoothing_polyorder
    )

    df_filtered, original_outliers = _filter_extreme_outliers(df_raw.copy(), price_trend_series)

    print(tabulate(price_trend_series.to_frame(), headers='keys', tablefmt='psql', floatfmt=",.0f", showindex="always"))
    _plot_price_vs_measure(df_raw, df_filtered, price_trend_series, original_outliers)


main()
