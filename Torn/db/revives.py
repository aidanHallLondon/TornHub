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

def create_revive_contracts(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS revive_contracts;")
    cursor.executescript(
        """
        DROP TABLE IF EXISTS revive_contracts;

        CREATE TABLE IF NOT EXISTS revive_contracts (
                revive_contract_id INTEGER PRIMARY KEY NOT NULL,
                ally_factionname TEXT,
                target_factionname TEXT,
                started DATETIME,
                ended DATETIME,
                chance_min INTEGER,
                success_fee INTEGER,
                failure_fee INTEGER,
                faction_cut REAL,
                notes_html TEXT
            )
        """)
 
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
            reviver_name TEXT,
            reviver_faction_id INTEGER,
            reviver_factionname TEXT,
            target_id INTEGER NOT NULL,
            target_name TEXT,
            target_faction_id INTEGER,
            target_factionname TEXT,
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

    # a view to see revives by user by date
    cursor.executescript('''
  DROP  VIEW IF EXISTS revivers;
  DROP  VIEW IF EXISTS revives_by_date;
  DROP  VIEW IF EXISTS revives_by_week;
  DROP  VIEW IF EXISTS revivesByDate;
  DROP  VIEW IF EXISTS revivesByWeek;

 
  CREATE VIEW revivers AS 
           SELECT
                    revives.reviver_id AS user_id,
                    r_user.name AS user_name,
                    COUNT(*) AS successful_revives,
                    CAST(ROUND((MAX(chance) - 90) * 10) AS INT) AS skill_est
            FROM revives
            INNER JOIN users AS r_user
                    ON revives.reviver_id = r_user.user_id
                    AND r_user.is_in_faction = 1
            WHERE
                    is_success = 1
                    GROUP BY
                        revives.reviver_id,
                    r_user.name;                      

  CREATE VIEW revives_by_date AS 
        WITH RECURSIVE date_series(dt) AS (
        SELECT MIN(dayDate) 
        FROM (
            SELECT
            r_user.name AS user_name,
            DATE(revives.timestamp) AS dayDate,
            COUNT(*) AS successful_revives,
            ROUND(AVG(chance), 1) AS avg_chance,
            CAST(ROUND((MAX(chance) - 90) * 10) AS INT) AS skill_est
            FROM revives
            INNER JOIN users AS r_user
            ON revives.reviver_id = r_user.user_id
            AND r_user.is_in_faction = 1
            WHERE
            is_success = 1
            GROUP BY
            r_user.name,
            dayDate
        ) AS revives_by_date
        UNION 
        SELECT date(dt, '+1 day')
        FROM date_series
        WHERE dt < (
            SELECT MAX(dayDate) FROM (
            SELECT
                r_user.name AS user_name,
                DATE(revives.timestamp) AS dayDate,
                COUNT(*) AS successful_revives,
                ROUND(AVG(chance), 1) AS avg_chance,
                CAST(ROUND((MAX(chance) - 90) * 10) AS INT) AS skill_est
            FROM revives
            INNER JOIN users AS r_user
                ON revives.reviver_id = r_user.user_id
                AND r_user.is_in_faction = 1
            WHERE
                is_success = 1
            GROUP BY
                r_user.name,
                dayDate
            ) AS revives_by_date
        )
        ), revives_by_date AS (
        SELECT
            r_user.name AS user_name,
            DATE(revives.timestamp) AS dayDate,
            COUNT(*) AS successful_revives,
            ROUND(AVG(chance), 1) AS avg_chance,
            CAST(ROUND((MAX(chance) - 90) * 10) AS INT) AS skill_est
        FROM revives
        INNER JOIN users AS r_user
            ON revives.reviver_id = r_user.user_id
            AND r_user.is_in_faction = 1
        WHERE
            is_success = 1
        GROUP BY
            r_user.name,
            dayDate
        )
        , DateSeries AS (
        SELECT DISTINCT dayDate
        FROM revives_by_date
        UNION 
        SELECT dt FROM date_series
        ), PlayerSeries AS (
        SELECT DISTINCT user_name
        FROM revives_by_date
        ), AllCombinations AS (
        SELECT
            ds.dayDate,
            ps.user_name
        FROM DateSeries AS ds
        CROSS JOIN PlayerSeries AS ps
        )
        SELECT
            ac.dayDate as period,
            ac.user_name,
            COALESCE(rbd.successful_revives, 0) AS successful_revives
        FROM AllCombinations AS ac
        LEFT JOIN revives_by_date AS rbd
        ON ac.dayDate = rbd.dayDate AND ac.user_name = rbd.user_name;
    ''')
    cursor.executescript('''
        CREATE VIEW revives_by_week AS
            SELECT
            STRFTIME('%Y-%W', period) AS period,  -- Extract year and week number (Monday as start of week)
            user_name,
            SUM(successful_revives) AS successful_revives  -- Sum revives for each player within the week
            FROM revives_by_date
            GROUP BY period, user_name;             
    '''
  )

def update_revive_contracts(conn, cursor, force=False):
    if force:
        print("Force deleting revives")
        cursor.execute("DELETE FROM revive_contracts; DROP TABLE revive_contracts")
    cursor.executescript(
        """
        DELETE FROM revive_contracts;
        INSERT OR IGNORE INTO revive_contracts (
            revive_contract_id,
            ally_factionname,
            target_factionname,
            started,
            ended,
            chance_min,
            success_fee,
            failure_fee,
            faction_cut,
            notes_html) 
            VALUES 
            (1,"Halos","The Psychonauts",'2025-02-08 23:30:00', '2025-02-09 19:30:00', 50, 820000,410000,0.125,
                "Test case - may differ slightly from actual billing"),
            (2,"Monarch HQ","Natural Selection",'2025-02-15 00:00:00', '2025-02-16 23:59:59', 50, 1500000,500000,0.125,
                'For this contract you will have to join the <a href="https://discord.gg/WWkSwFAa">Monarch QC Discord Server</a>'
            );
        """)


def update_revives(conn, cursor, force=False):
    is_full_endpoint = False
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
            reviver_name,
            reviver_factionname,
            target_id, 
            target_name,
            target_factionname,
            target_hospital_reason, 
            target_early_discharge, 
            target_last_action_status, 
            target_last_action_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                revive_row["revive_id"],
                1 if is_full_endpoint else 0,
                datetime.fromtimestamp(revive_row["timestamp"]).isoformat(),
                revive_row["result"],
                revive_row["chance"],
                revive_row["reviver_id"],
                revive_row["reviver_name"],
                revive_row.get("reviver_factionname"),
                revive_row["target_id"],
                revive_row["target_name"],
                revive_row.get("target_factionname"),
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
