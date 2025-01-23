import json
import sqlite3
from datetime import datetime

from Torn.api import (
    cached_api_paged_call,
    cached_api_paged_log_call,
    _paginated_api_calls,
)

ATTACK_CALLS = {
    "attacks": {"endpoint": "faction/attacks", "LIMIT": 100},
    "attacksFull": {"endpoint": "faction/attacksFull", "LIMIT": 1000},
}

def create_attacks(conn,cursor, force=False):
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


def update_attacks(conn,cursor, force=False):
    is_full_endpoint = True
    callType = ATTACK_CALLS["attacksFull" if is_full_endpoint else "attacks"]
    endpoint =callType["endpoint"]  # if is_full_endpoint else "faction/attacks"
    limit = callType["LIMIT"]  # if is_full_endpoint else 100

    if force:
        cursor.execute("DELETE FROM attacks;")
        last_timestamp = None
    else:
        cursor.execute("SELECT MAX(started) AS last_timestamp FROM attacks;")
        last_timestamp = cursor.fetchone()[0]

    # print(f"last_timestamp={last_timestamp}")
    attacksData = []
    attacksData = _paginated_api_calls(
        conn,cursor, 
        endpoint=endpoint,
        params=None,
        timestamp_field="started",
        last_timestamp=last_timestamp,
        dataKey="attacks",
        limit=limit,
        callback = _insertAttacks_callback_fn, # callback
        callback_parameters={"is_full_endpoint":is_full_endpoint}
    )
    print(f"len data ={len(attacksData)}")
    # _insertAttacks(conn,cursor, attacksData, parameters={"is_full_endpoint":is_full_endpoint})


# def _update_attacks_with_endpoint(
#     cursor, is_full_endpoint=False, limit=100, force=False
# ):
#     """
#     Fetches attack data using geAttacks() and updates the SQLite database.

#     Args:
#         db_path (str): Path to the SQLite database file.
#     """
#     endpoint = "faction/attacksFull" if is_full_endpoint else "faction/attacks"
#     attacks = cached_api_paged_log_call(
#         endpoint=endpoint,
#         params=None,
#         dataKey="attacks",
#         limit=limit,
#         force=force,
#     )

#     print("attacks ", len(attacks))
#     _insertAttacks(cursor, attacks, is_full_endpoint)


def _insertAttacks_callback_fn(conn, cursor, attacks, parameters):
    ''' 
    passed as a callback to paginated 
    '''
    is_full_endpoint = parameters["is_full_endpoint"] if "is_full_endpoint" in parameters else False
    _insert_attacks(conn, cursor, attacks, is_full_endpoint)

def _insert_attacks(conn, cursor, attacks,is_full_endpoint):
    for attackRow in attacks:
        _insert_attack(conn, cursor, attackRow ,is_full_endpoint)

def _insert_attack(conn, cursor, attackRow ,is_full_endpoint):
        try:
            started = datetime.fromtimestamp(attackRow["started"]).isoformat()
            ended = datetime.fromtimestamp(attackRow["ended"]).isoformat()
            # Extract attacker data, handling potential NULL
            attacker_id = attackRow["attacker"]["id"] if attackRow.get("attacker") else None
            attacker_name = (
                attackRow["attacker"].get("name") if attackRow.get("attacker") else None
            )
            attacker_level = (
                attackRow["attacker"].get("level") if attackRow.get("attacker") else None
            )
            attacker_faction_id = (
                attackRow["attacker"].get("faction", {}).get("id")
                if attackRow.get("attacker") and attackRow["attacker"].get("faction", {})
                else None
            )

            # Extract defender data, handling potential NULL
            defender_id = attackRow["defender"]["id"] if attackRow.get("defender") else None
            defender_name = (
                attackRow["defender"].get("name") if attackRow.get("defender") else None
            )
            defender_level = (
                attackRow["defender"].get("level") if attackRow.get("defender") else None
            )
            defender_faction_id = (
                attackRow["defender"].get("faction", {}).get("id")
                if attackRow.get("defender") and attackRow["defender"].get("faction", {})
                else None
            )
            finishing_hit_effects = (
                json.dumps(attackRow.get("finishing_hit_effects", {}))
                if "finishing_hit_effects" in attackRow
                else None
            )
            cursor.execute(
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
                (
                    attackRow["id"],
                    1 if is_full_endpoint else 0,
                    attackRow["code"],
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
                    finishing_hit_effects,
                ),
            )
        except sqlite3.IntegrityError:
            print("Err")
            pass  # Ignore if attack ID already exists
