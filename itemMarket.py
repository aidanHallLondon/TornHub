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
from Torn.reporting.itemMarket import item_market_page


# --- Configuration ---
UPPER_MARGIN_FACTOR = 0.20
LOWER_MARGIN_FACTOR = 0.05
OUTLIER_THRESHOLD = 2.0
TREND_PERCENTILE = 0.01
MODERN_LISTING_ID_THRESHOLD = 9 * 1000000

def main():
    """Main function to initialize the database and process data."""
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    initDB(conn, cursor)  # Initialize database structure

    # loadit(conn, cursor, mode="data") # Uncomment to load data
    path = "reports/items/market/items"
    f_menu = []
    f_menu = item_market_page(conn, cursor, item_id=332, path=path, f_menu=f_menu)
    f_menu = item_market_page(conn, cursor, item_id=652, path=path, f_menu=f_menu)
    f_menu = item_market_page(conn, cursor, item_id=653, path=path, f_menu=f_menu)
    f_menu = item_market_page(conn, cursor, item_id=654, path=path, f_menu=f_menu)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
