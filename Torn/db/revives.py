import json
import sqlite3
from datetime import datetime

from Torn.api import (
    cached_api_paged_call,
    cached_api_paged_log_call,
    paginated_api_calls,
    date_to_unix
)

REVIVES_CALLS = {
    "revives": {"endpoint": "faction?selections=revives", "LIMIT": 100},
    "revivesFull": {"endpoint": "faction?selections=revivesFull", "LIMIT": 1000},
}


def create_revives(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS revives;")
    cursor.executescript(
        """CREATE TABLE IF NOT EXISTS revives (
            revive_id INTEGER PRIMARY KEY NOT NULL,
            timestamp DATETIME NOT NULL,
            result TEXT NOT NULL,
            chance REAL NOT NULL,
            reviver_id INTEGER NOT NULL,
            -- reviver_name TEXT,
            reviver_faction_id INTEGER,
            -- reviver_factionname TEXT,
            target_id INTEGER NOT NULL,
            --target_name TEXT,
            target_faction_id INTEGER,
            --target_factionname TEXT,
            target_hospital_reason TEXT NOT NULL,
            target_early_discharge BOOLEAN NOT NULL,
            target_last_action_status TEXT NOT NULL,
            target_last_action_timestamp DATETIME NOT NULL,
            is_full_endpoint BOOLEAN DEFAULT 1 NOT NULL,
            is_success GENERATED ALWAYS AS (CASE WHEN result='success' THEN 1 ELSE 0 END),
            is_a_faction_revive GENERATED ALWAYS AS (CASE WHEN reviver_faction_id = 1234 THEN 1 ELSE 0 END),
            is_success_faction_revive GENERATED ALWAYS AS (CASE WHEN reviver_faction_id = 1234 AND result='success' THEN 1 ELSE 0 END)
        )"""
    )


def update_revives(conn, cursor, force=False):
    is_full_endpoint = True
    callType = REVIVES_CALLS["revivesFull" if is_full_endpoint else "revives"]
    endpoint = callType["endpoint"]  # if is_full_endpoint else "faction/revives"
    limit = callType["LIMIT"]  # if is_full_endpoint else 100
    sort = "ASC"   
    latest_timestamp = fromTimestamp=date_to_unix('2014-01-01 00:00:00') # random early date
 
    if force:
        print("Force deleting revives")
        cursor.execute("DELETE FROM revives;")
    else:
        conn.commit()
        cursor.execute("SELECT MAX(timestamp) FROM revives;")
        latest_timestamp_datetime = cursor.fetchone()[0]
        if latest_timestamp_datetime:
            latest_timestamp =datetime.fromisoformat(latest_timestamp_datetime).timestamp()   

    paginated_api_calls(
        conn,
        cursor,
        endpoint=endpoint,
        params={"sort": sort},
        timestamp_field="timestamp",
        fromTimestamp=latest_timestamp,
        dataKey="revives",
        limit=limit,
        callback=_insert_revives_callback_fn,  # callback
        callback_parameters={"is_full_endpoint": is_full_endpoint},
        short_name='revives'
    )
    conn.commit()

def _insert_revives_callback_fn(conn, cursor, revives, parameters):
    is_full_endpoint = parameters.get("is_full_endpoint", False)
    _insert_revives(conn, cursor, revives, is_full_endpoint)


def _insert_revives(conn, cursor, revives, is_full_endpoint):
    cursor.executemany(
        """
        INSERT OR IGNORE INTO revives (
            revive_id, 
            is_full_endpoint, 
            timestamp, 
            result, 
            chance, 
            reviver_id, 
            reviver_faction_id, 
            target_id, 
            target_faction_id, 
            target_hospital_reason, 
            target_early_discharge, 
            target_last_action_status, 
            target_last_action_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                revive_row["revive_id"],
                1 if is_full_endpoint else 0,
                datetime.fromtimestamp(revive_row["timestamp"]).isoformat(),
                revive_row["result"],
                revive_row["chance"],
                revive_row["reviver_id"],
                revive_row.get("reviver_faction_id"),
                revive_row["target_id"],
                revive_row.get("target_faction_id"),
                revive_row["target_hospital_reason"],
                1 if revive_row["target_early_discharge"] else 0,
                revive_row["target_last_action"].get("status"),
                datetime.fromtimestamp(
                    revive_row.get("target_last_action").get("timestamp")
                ).isoformat(),
            )
            for revive_row in revives
            # for revive_key, revive_row in revives.items()
        ],
    )
