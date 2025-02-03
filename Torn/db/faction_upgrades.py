import json
import sqlite3
from datetime import datetime
from Torn.api import cached_api_call, cached_api_paged_call


def create_faction_upgrades(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS faction_upgrades;")

    cursor.executescript(
        """CREATE TABLE  IF NOT EXISTS faction_upgrades (
        upgrade_uid INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_state TEXT NOT NULL,  -- 'peace', 'war', 'updgrade'.
        upgrade_id INTEGER NOT NULL,  -- '1', '2', '3', etc.
        branch TEXT NOT NULL,
        branchorder INTEGER,
        branchmultiplier INTEGER,
        name TEXT NOT NULL,
        level INTEGER,
        basecost INTEGER,
        ability TEXT,
        unlocked TEXT
        );"""
    )

def update_faction_upgrades(conn, cursor, force=False):
    cache_age_limit = 60
    faction_upgrades = cached_api_call(
        conn,
        cursor,
        endpoint="faction?selections=upgrades",
        params=None,
        dataKey=None,
        cache_age_limit=cache_age_limit,
        force=force,
    )
    state = faction_upgrades["state"]
    upgrades = faction_upgrades["upgrades"]
    war = faction_upgrades["war"]
    peace = faction_upgrades["peace"]
    all_upgrades = []

    for key in upgrades:
        _all_upgrades_append(all_upgrades, "upgrades", key, upgrades)
    for key in war:
        _all_upgrades_append(all_upgrades, "war", key, war)
    for key in peace:
        _all_upgrades_append(all_upgrades, "peace", key, peace)

    cursor.execute(
        f"""UPDATE faction_history 
        SET faction_state = '{state}' 
        WHERE batch_date = (SELECT batch_date FROM faction_history ORDER BY timestamp DESC LIMIT 1)
        AND timestamp >= strftime('%Y-%m-%d %H:%M:%S', datetime('now', '47 hours'));  -- Adjust the time difference as needed"""
    )
    cursor.executemany(
        """
            INSERT OR REPLACE INTO faction_upgrades (
            faction_state, upgrade_id, branch, branchorder, branchmultiplier, name, level, basecost, ability, unlocked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", all_upgrades,
    )

def _all_upgrades_append(all_items, state, upgrade_id, items):
    item = items[upgrade_id]
    all_items.append(
        (  
            state,
            upgrade_id,
            item["branch"],
            item["branchorder"],
            item["branchmultiplier"],
            item["name"],
            item["level"],
            item["basecost"],
            item["ability"],
            item["unlocked"],
        )
    )