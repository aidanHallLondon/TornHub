import json
from os import path
import os
import sqlite3
from string import Template
from tabulate import tabulate
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Torn.charts import plt_save_image
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import initDB
from Torn.db.items import create_item_listings, update_item
from Torn.reporting.build_menus import _menu_item_for_file


# --- Configuration ---
UPPER_MARGIN_FACTOR = 0.20
LOWER_MARGIN_FACTOR = 0.05
OUTLIER_THRESHOLD = 2.0
TREND_PERCENTILE = 0.01


def item_reporting(conn, cursor, f_menu):
    path = "reports/items/market/items"
    
    f_menu = create_item_market_json(conn,cursor, item_id=332, f_menu=f_menu)
    f_menu = create_item_market_json(conn,cursor, item_id=333, f_menu=f_menu)
    f_menu = create_item_market_json(conn,cursor, item_id=652, f_menu=f_menu)
    f_menu = create_item_market_json(conn,cursor, item_id=653, f_menu=f_menu)
    f_menu = create_item_market_json(conn,cursor, item_id=654, f_menu=f_menu)
    return f_menu


def plot_armory_pricing_chart(
    conn,
    cursor,
    item_id=332,
    item_name=None,
    item_type=None,
    average_price=None,
    bin_factor=12,
    percentile=TREND_PERCENTILE,
    out_filename=None,
    path=None,
):
    """
    Main plotting function.  Fetches data, calculates trends, filters outliers, and plots.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        item_id: The ID of the item to analyze.
        bin_factor:  Factor to determine bin size.
        percentile: The percentile for trend calculation.
    """
    global plt
    # --- Helper Functions ---

    def _filter_extreme_outliers(df_raw, price_trend_series):
        """
        Filters extreme outliers based on a trend series and thresholds.

        Args:
            df_raw: DataFrame with 'measure' and 'price' columns.
            price_trend_series:  Series with trend prices, indexed by 'measure'.

        Returns:
            Tuple: (DataFrame with outliers removed, Boolean Series indicating outliers in original data)
        """
        df_raw = df_raw.copy()
        df_trend = price_trend_series.to_frame(name="trend_price").reset_index()
        df_trend.columns = ["measure", "trend_price"]

        # Ensure consistent types and sorting
        df_raw["measure"] = df_raw["measure"].astype(float)
        df_trend["measure"] = df_trend["measure"].astype(float)
        df_raw = df_raw.sort_values("measure")
        df_trend = df_trend.sort_values("measure")

        # Create a dictionary for faster trend price lookup
        trend_dict = df_trend.set_index("measure")["trend_price"].to_dict()

        # Optimized trend price interpolation using NumPy
        trend_measures = np.array(sorted(trend_dict.keys()))
        trend_prices = np.array([trend_dict[m] for m in trend_measures])
        df_raw["trend_price"] = np.interp(
            df_raw["measure"], trend_measures, trend_prices, left=np.nan, right=np.nan
        )

        # Handle cases where interpolation might return NaN (measure out of trend range):
        df_raw["trend_price"].fillna(method="ffill", inplace=True)  # Forward fill
        df_raw["trend_price"].fillna(
            method="bfill", inplace=True
        )  # Backward fill (if any NaNs remain at start)

        # Calculate price differences and identify outliers
        df_raw["price_diff"] = df_raw["price"] - df_raw["trend_price"]

        df_raw["outlier"] = (
            df_raw["price"] > (df_raw["trend_price"] * OUTLIER_THRESHOLD)
        ) 
        df_filtered = df_raw[~df_raw["outlier"]].copy()

        df_filtered.loc[:, "above_trend"] = df_filtered["price_diff"] > (
            df_filtered["trend_price"] * UPPER_MARGIN_FACTOR
        )
        df_filtered.loc[:, "on_trend"] = (
            df_filtered["price_diff"]
            <= (df_filtered["trend_price"] * UPPER_MARGIN_FACTOR)
        ) & (
            df_filtered["price_diff"]
            >= -(df_filtered["trend_price"] * LOWER_MARGIN_FACTOR)
        )
        df_filtered.loc[:, "below_trend"] = df_filtered["price_diff"] < -(
            df_filtered["trend_price"] * LOWER_MARGIN_FACTOR
        )

        return df_filtered, df_raw["outlier"]

    def _calculate_bin_percentiles(df, bin_size, percentile):
        """Calculates percentile prices for bins, with forward-fill smoothing.
        Args:
            df: DataFrame with 'measure' and 'price'.
            bin_size:  The size of each bin.
            percentile: The percentile to calculate (e.g., 0.05 for 5th percentile).
        Returns:
            Series: Percentile prices, indexed by bin midpoints, with smoothing.  Handles empty bins.
        """
        bins = np.arange(df["measure"].min(), df["measure"].max() + bin_size, bin_size)
        df["bin"] = pd.cut(df["measure"], bins=bins, labels=False, include_lowest=True)
        # Calculate percentiles within each bin, handling empty bins (they'll become NaN)
        bin_percentiles = df.groupby("bin")["price"].quantile(percentile).reset_index()
        # Get bin midpoints *for the bins that actually have data*
        bin_midpoints = [
            bins[int(i)] + (bins[int(i) + 1] - bins[int(i)]) / 2
            for i in bin_percentiles["bin"]
        ]
        bin_percentiles["measure"] = bin_midpoints
        # Convert to Series, indexed by measure
        bin_percentiles_series = pd.Series(
            bin_percentiles["price"].values, index=bin_percentiles["measure"]
        )
        bin_percentiles_series = bin_percentiles_series.ffill().bfill()
        #
        return bin_percentiles_series

    def _plot_price_vs_measure(
        df_raw,
        df_filtered,
        original_outliers,
        item_id,
        item_name,
        item_type,
        average_price,
    ):
        """
        Creates the scatter plot with categorized points and trend lines.

        Args:
            df_raw: Original DataFrame.
            df_filtered: DataFrame with outliers removed.
            price_trend_series: Series with trend prices.
            original_outliers: Boolean Series indicating outliers in the original data.
        """

        def _plt_scatter(x, y, color, gid, label, marker=".", size=12, alpha=0.5):
            for i in range(len(x)):
                plt_label = label if i == 0 else None  # Only label the first point
                plt.plot(
                    x.iloc[i],
                    y.iloc[i],
                    marker=marker,
                    linestyle="",
                    color=color,
                    alpha=alpha,
                    label=plt_label,
                    ms=size,
                    gid=f"""datum|{gid}|{i}"""
                )
            plt.legend()

        # Plot categorized points (filtered data), using the calculated classifications.
        _plt_scatter(
            df_filtered.loc[df_filtered["above_trend"], "measure"],
            df_filtered.loc[df_filtered["above_trend"], "price"],
            gid="above_trend",
            color="red",
            label="Above Trend"
        )

        _plt_scatter(
            df_filtered.loc[df_filtered["on_trend"], "measure"],
            df_filtered.loc[df_filtered["on_trend"], "price"],
            gid="on_trend",
            color="blue",
            label="On Trend"
        )
        _plt_scatter(
            df_filtered.loc[df_filtered["below_trend"], "measure"],
            df_filtered.loc[df_filtered["below_trend"], "price"],
            gid="below_trend",
            color="green",
            label="Below Trend"
        )

        # Interpolated trend line
        plt.plot(
            df_filtered["measure"],
            df_filtered["trend_price"],
            color="orange",
            lw=2,
            linestyle="-",
            label="Interpolated Trend",
            alpha=0.7,
        )

        # Upper and Lower Margin lines
        plt.plot(
            df_filtered["measure"],
            df_filtered["trend_price"]
            + (df_filtered["trend_price"] * UPPER_MARGIN_FACTOR),
            color="red",
            lw=1,
            linestyle="--",
            alpha=0.25,
            label=f"Upper Margin ({UPPER_MARGIN_FACTOR*100:.0f}%)",
        )
        plt.plot(
            df_filtered["measure"],
            df_filtered["trend_price"]
            - (df_filtered["trend_price"] * LOWER_MARGIN_FACTOR),
            color="green",
            lw=1,
            linestyle="--",
            alpha=0.25,
            label=f"Lower Margin ({LOWER_MARGIN_FACTOR*100:.0f}%)",
        )

        plt.yscale("log")
        xmin, xmax = plt.xlim()
        ymin, ymax = plt.ylim()
        padding_x = (xmax - xmin) * 0.0  # Removed padding for a tighter plot
        padding_y = (ymax - ymin) * 0.0
        plt.xlim(xmin - padding_x, xmax + padding_x)
        plt.ylim(ymin - padding_y, ymax + padding_y)

        # Outlier points (using original_outliers)
        _plt_scatter(
            df_raw[original_outliers]["measure"],
            df_raw[original_outliers]["price"],
            gid="excluded_outliers",
            color="black",
            label="Excluded Outliers",
            marker="x",
            size=4,
            alpha=.1,
        )
        plt.xlabel("Measure")
        plt.ylabel("Price")
        plt.title(f"{item_name} (#{item_id} {item_type}) Price vs. Measure")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        return plt

    # -- plot_armory_pricing_chart --
    cursor.execute(
        f"""
        SELECT item_uid, stat_armor as measure, price
        FROM item_listings
        WHERE item_id={item_id}
        ORDER BY measure ASC;"""
    )
    raw_data = cursor.fetchall()
    df_raw = pd.DataFrame(
        raw_data, columns=["item_uid", "measure", "price"]
    )

    # Calculate dynamic bin size
    min_measure = df_raw["measure"].min()
    max_measure = df_raw["measure"].max()
    count = len(df_raw)
    bin_size = (
        bin_factor * (max_measure - min_measure) / count if count > 0 else 1
    )  # Avoid division by zero

    # Calculate trend *before* filtering, for use in outlier detection
    price_trend_series = _calculate_bin_percentiles(df_raw, bin_size, percentile)

    # Filter outliers
    df_filtered, original_outliers = _filter_extreme_outliers(
        df_raw.copy(), price_trend_series
    )

    # Print the price trend series
    print(
        tabulate(
            price_trend_series.to_frame(),
            headers="keys",
            tablefmt="psql",
            floatfmt=",.0f",
            showindex="always",
        )
    )

    # Create the plot
    plt = _plot_price_vs_measure(
        df_raw,
        df_filtered,
        original_outliers,
        item_id,
        item_name,
        item_type,
        average_price,
    )
    # plt.show()
    out_filename = out_filename if out_filename else f"item_{item_id:06}"
    plt_save_image(
        path=path,
        out_filename=out_filename,
        show_image=False,
        format="svg",
    )
    return out_filename + ".svg"


# ------------------------

def create_item_market_json(conn, cursor, item_id, f_menu):
    title_str="Item Pricing for weapons and armor"
    path="reports/items/armory/items/json"
    out_filename=f"items_armory_{item_id:06}"
    if not os.path.exists(path):
        os.makedirs(path)
    # 
    cursor.execute(f'''
        SELECT 	item_name,	item_type,	average_price
        FROM items
        WHERE item_id={item_id} AND item_name IS NOT NULL
        LIMIT 1; ''')
    item_data = cursor.fetchone()
    if item_data:
        item_name, item_type, average_price = item_data
        cursor.execute(f"""
            SELECT item_uid, stat_damage, stat_accuracy, stat_armor, price
            FROM item_listings
            WHERE item_id={item_id}
            ORDER BY price ASC;"""
        )
        raw_data = cursor.fetchall()
        # 
        data={
            "meta_data":{
                    "name": f"items_armory_{item_name}",
                    "source": f"item_market_json({item_id})",
                    "id" : item_id,
                    "headings":["item_uid", "stat_damage", "stat_accuracy", "stat_armor", "price"],
                },
            "data":raw_data
        }
        # 
        with open(os.path.join(path, out_filename+'.json'), "w") as f:
            f.write(json.dumps(data,indent=4))
        print(f"{title_str} saved in {out_filename}")  
        f_menu.append(
            _menu_item_for_file(
                name=f"items_armory_{item_name}",
                href=f"/items/armory/items/item_pricing.html?item_id={item_id}",
            )
        )
        return f_menu
