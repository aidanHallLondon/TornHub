from datetime import datetime
import json
import os
import sqlite3
from matplotlib import text
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from Torn.db._globals import DB_CONNECTPATH
from Torn.charts import plt_save_image
from Torn.manageDB import initDB, updateDB

# def main(fast=True):
#     conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
#     cursor = conn.cursor()
#     if not fast:
#         initDB(conn, cursor)  # creates the database structure if not already done
#     if not fast:
#         updateDB(conn, cursor)
#     #
#     reviver_ranks_json(conn, cursor)

#     conn.commit()
#     conn.close()

# TODO use this approach in the crome.py version too and use a shared module

def reviver_ranks_json(
    conn,
    cursor
):
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
    cursor.execute(
        f"""{_reviver_rank_bump_plot_sql_ctes()}
        SELECT date_point as date, user_id, user_name,  rank_count, rank_skill, successful_revives, skill_est, role
        FROM revives_slice
        order by date_point DESC, user_id ASC
    """
    )

    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] #extract the column names

    npData = pd.DataFrame(
        data, columns=columns
    )

    dates = sorted(npData['date'].unique())
    date_strings = [str(date) for date in dates]

    chart_data = {
        "dates": date_strings,
        "series": []
    }

    for (user_id, user_name, role), group in npData.groupby(["user_id", "user_name", "role"]):
        player_data = {
            "name": f"{user_name} ({role})",
            "data": []
        }
        for date in dates:
            ranks = {}  # Dictionary to hold ranks for this date
            row = group.loc[group['date'] == date]
            if not row.empty: #check if the row is empty or not
                ranks["rank_skill"] = int(row['rank_skill'].iloc[0]) if isinstance(row['rank_skill'].iloc[0], np.integer) else row['rank_skill'].iloc[0]
                ranks["rank_count"] = int(row['rank_count'].iloc[0]) if isinstance(row['rank_count'].iloc[0], np.integer) else row['rank_count'].iloc[0]
                # Add more ranks here as needed:
                # ranks["rank_other"] = ...
            player_data["data"].append(ranks)  # Append the dictionary of ranks

        chart_data["series"].append(player_data)

    meta_data= {
        "name": "revive_ranks",
        "source": "reviver_ranks_json",
        "structure":""" {"dates": [date string, ...], 
                        "series": [ 
                            { "name": string, "data":[{rank_skill,rank_count}] }, ... ]
                        }""",
        "headings": [
            "rank_skill",
            "rank_count"
        ]
    },
    data = {"meta_data":meta_data, "data":chart_data}
    # print(json.dumps(data, indent=3))

    destination_path = "reports/faction/revives/json"
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)
    with open(os.path.join(destination_path,'rank.json'), 'w') as f:
        json.dump(data, f, indent=3)

