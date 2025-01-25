import json
import sqlite3
from datetime import datetime

from Torn.api import (
    cached_api_paged_call,
    cached_api_paged_log_call,
    paginated_api_calls,
)

ATTACK_CALLS = {
    "attacks": {"endpoint": "faction?selections=attacks", "LIMIT": 100},
    "attacksFull": {"endpoint": "faction?selections=attacksFull", "LIMIT": 1000},
}


def create_attacks(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS attacks;")

    cursor.executescript(
        """CREATE TABLE IF NOT EXISTS attacks (
        attack_id INTEGER PRIMARY KEY NOT NULL,
        is_full_endpoint BOOLEAN NOT NULL,
        attack_code TEXT NOT NULL,
        started DATETIME NOT NULL,
        ended DATETIME NOT NULL,
        attacker_id INTEGER,
        attacker_name TEXT,
        attacker_level INTEGER,
        attacker_faction_id INTEGER,
        defender_id INTEGER NULL,
        defender_name TEXT,
        defender_level INTEGER,
        defender_faction_id INTEGER,
        result TEXT NOT NULL,
        respect_gain REAL NOT NULL,
        respect_loss REAL NOT NULL,
        chain INTEGER,
        is_interrupted BOOLEAN,
        is_stealthed BOOLEAN,
        is_raid BOOLEAN,
        is_ranked_war BOOLEAN,
        modifier_fair_fight REAL,
        modifier_war REAL,
        modifier_retaliation REAL,
        modifier_group_attack REAL,
        modifier_overseas REAL,
        modifier_chain_modifier REAL,
        modifier_warlord REAL,
        finishing_hit_effects TEXT
    
        -- FOREIGN KEY (xxx) REFERENCES xxx(xxx)
    )"""
    )


def update_attacks(conn, cursor, force=False):
    is_full_endpoint = True
    callType = ATTACK_CALLS["attacksFull" if is_full_endpoint else "attacks"]
    endpoint = callType["endpoint"]  # if is_full_endpoint else "faction/attacks"
    limit = callType["LIMIT"]  # if is_full_endpoint else 100

    if force:
        cursor.execute("DELETE FROM attacks;")
        latest_timestamp = None
    else:
        cursor.execute("SELECT MAX(started) AS last_timestamp FROM attacks;")
        latest_timestamp_datetime = cursor.fetchone()[0]
        print(latest_timestamp_datetime)
        latest_timestamp =datetime.fromisoformat(latest_timestamp_datetime).timestamp()  if latest_timestamp_datetime else None  

    paginated_api_calls(
        conn,
        cursor,
        endpoint=endpoint,
        params={"sort":"ASC"},
        timestamp_field="started",
        fromTimestamp=latest_timestamp,
        dataKey="attacks",
        limit=limit,
        callback=_insertAttacks_callback_fn,  # callback
        callback_parameters={"is_full_endpoint": is_full_endpoint},
        short_name='attacks'    
    )
 
def _insertAttacks_callback_fn(conn, cursor, attacks, parameters):
    # TODO is_full_endpoint = parameters.get("is_full_endpoint", False)
    is_full_endpoint = (
        parameters["is_full_endpoint"] if "is_full_endpoint" in parameters else False
    )
    _insert_attacks(conn, cursor, attacks, is_full_endpoint)


def _insert_attacks(conn, cursor, attacks, is_full_endpoint):

    cursor.executemany(
        """
        INSERT OR IGNORE INTO attacks (
            attack_id, 
            is_full_endpoint,
            attack_code, 
            started, 
            ended, 
            attacker_id, 
            attacker_name, 
            attacker_level, 
            attacker_faction_id, 
            defender_id, 
            defender_name, 
            defender_level, 
            defender_faction_id, 
            result, 
            respect_gain, 
            respect_loss, 
            chain, 
            is_interrupted, 
            is_stealthed, 
            is_raid, 
            is_ranked_war,
            modifier_fair_fight,
            modifier_war,
            modifier_retaliation,
            modifier_group_attack,
            modifier_overseas,
            modifier_chain_modifier,
            modifier_warlord,
            finishing_hit_effects
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
        (
            attackRow["id"],
            1 if is_full_endpoint else 0,
            attackRow["code"],
            datetime.fromtimestamp(attackRow["started"]).isoformat(),
            datetime.fromtimestamp(attackRow["ended"]).isoformat(),
            attackRow["attacker"]["id"] if attackRow.get("attacker") else None,
            attackRow["attacker"].get("name") if attackRow.get("attacker") else None,
            attackRow["attacker"].get("level") if attackRow.get("attacker") else None,
            (
                attackRow["attacker"].get("faction", {}).get("id")
                if attackRow.get("attacker")
                and attackRow["attacker"].get("faction", {})
                else None
            ),
            attackRow["defender"]["id"] if attackRow.get("defender") else None,
            attackRow["defender"].get("name") if attackRow.get("defender") else None,
            (
                attackRow["defender"].get("level")
                if attackRow.get("defender")
                else None
            ),
            (
                attackRow["defender"].get("faction", {}).get("id")
                if attackRow.get("defender")
                and attackRow["defender"].get("faction", {})
                else None
            ),
            attackRow["result"],
            attackRow["respect_gain"],
            attackRow["respect_loss"],
            attackRow.get("chain"),
            attackRow.get("is_interrupted"),
            attackRow.get("is_stealthed"),
            attackRow.get("is_raid"),
            attackRow.get("is_ranked_war"),
            attackRow.get("modifiers", {}).get("fair_fight"),
            attackRow.get("modifiers", {}).get("war"),
            attackRow.get("modifiers", {}).get("retaliation"),
            attackRow.get("modifiers", {}).get("group"),
            attackRow.get("modifiers", {}).get("overseas"),
            attackRow.get("modifiers", {}).get("chain"),
            attackRow.get("modifiers", {}).get("warlord"),
            (
                json.dumps(attackRow.get("finishing_hit_effects", {}))
                if "finishing_hit_effects" in attackRow
                else None
            ),
        )
        for attackRow in attacks
    ],
    )
