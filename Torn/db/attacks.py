import json
import sqlite3
from datetime import datetime

from Torn.api import (
    cached_api_paged_call,
    cached_api_paged_log_call,
    paginated_api_calls,
)
from Torn.db.faction import get_faction_id


ATTACK_CALLS = {
    "attacks": {"endpoint": "faction?selections=attacks", "LIMIT": 100},
    "attacksFull": {"endpoint": "faction?selections=attacksFull", "LIMIT": 1000},
}


def create_attacks(conn, cursor, faction_id=None, force=False):
    if faction_id is None:
        faction_id=get_faction_id(conn,cursor)
    if force:
        cursor.execute("DROP TABLE IF EXISTS attacks;")

    cursor.executescript(
        f"""CREATE TABLE IF NOT EXISTS attacks (
                attack_id INTEGER PRIMARY KEY NOT NULL,
                is_full_endpoint BOOLEAN NOT NULL,
                attack_code TEXT NOT NULL,
                started DATETIME NOT NULL,
                started_timestamp INTEGER,
                ended DATETIME NOT NULL,
                ended_timestamp INTEGER,      
                attacker_id INTEGER,
                attacker_name TEXT,
                attacker_level INTEGER,
                attacker_faction_id INTEGER,
                attacker_faction_name TEXT,
                defender_id INTEGER NULL,
                defender_name TEXT,
                defender_level INTEGER,
                defender_faction_id INTEGER,
                defender_faction_name TEXT,        
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
    );
    
    
    

DROP VIEW IF EXISTS "main"."attack_events";
CREATE VIEW attack_events AS
        SELECT 
            event_date,	event_type,	a.user_id,	user_name,	
            opponent_id,	oppo.name as opponent_name, oppo.level AS opponent_level,
            attack_result,	result,	respect_change,	chain,	
            is_interrupted,	is_stealthed,	is_opponent_stealthed,	is_raid,	is_ranked_war,	is_assist,	
            started,	ended,	modifier_fair_fight,	
            modifier_war,modifier_retaliation,	modifier_group_attack,	modifier_overseas,	
            modifier_chain_modifier,	modifier_warlord,	
            finishing_hit_effects,	attack_id,	attack_code	
        FROM (
            SELECT
                    DATE(a.started) as event_date,
                    CASE
                        WHEN u.user_id = a.attacker_id THEN 'attack'
                        ELSE 'defend'
                    END as event_type,
                    u.user_id,
                    u.name as user_name,
                    CASE
                        WHEN u.user_id = a.attacker_id THEN a.defender_id
                        ELSE a.attacker_id
                    END as opponent_id,
                    CASE
                        WHEN u.user_id = a.attacker_id THEN a.defender_id
                        ELSE a.attacker_id
                    END as opponent_id,
                    a.result AS attack_result, -- Retain original result field
                    CASE
                        WHEN u.user_id = a.attacker_id THEN
                            CASE a.result
                                WHEN 'Arrested' THEN -1
                                WHEN 'Timeout' THEN -1
                                WHEN 'Lost' THEN -1
                                WHEN 'Interrupted' THEN 0
                                WHEN 'Special' THEN 0
                                WHEN 'Escape' THEN 0
                                WHEN 'Stalemate' THEN 0
                                WHEN 'Assist' THEN 1
                                WHEN 'Attacked' THEN 1
                                WHEN 'Mugged' THEN 1
                                WHEN 'Hospitalized' THEN 1
                                ELSE 0 -- Default to draw if unknown
                            END
                        ELSE -- User is defender
                            CASE a.result
                                WHEN 'Arrested' THEN 1
                                WHEN 'Timeout' THEN 1
                                WHEN 'Lost' THEN 1
                                WHEN 'Interrupted' THEN 1
                                WHEN 'Special' THEN 1
                                WHEN 'Escape' THEN 1
                                WHEN 'Stalemate' THEN 1
                                WHEN 'Assist' THEN -1
                                WHEN 'Attacked' THEN -1
                                WHEN 'Mugged' THEN -1
                                WHEN 'Hospitalized' THEN -1
                                ELSE 0 -- Default to draw if unknown
                            END
                    END as result,
                    CASE
                        WHEN u.user_id = a.attacker_id THEN a.respect_gain
                        ELSE a.respect_loss * -1
                    END as respect_change,
                    a.chain,
                    a.is_interrupted,
                    CASE
                        WHEN u.user_id = a.attacker_id THEN a.is_stealthed
                        ELSE FALSE
                    END as is_stealthed,
                    CASE
                        WHEN u.user_id = a.defender_id THEN a.is_stealthed
                        ELSE FALSE
                    END as is_opponent_stealthed,
                    a.is_raid,
                    a.is_ranked_war,
                    CASE
                        WHEN u.user_id = a.attacker_id AND a.result = 'Assist' THEN TRUE
                        ELSE FALSE
                    END as is_assist,
                        a.started,
                    a.ended,
                    a.modifier_fair_fight,
                    a.modifier_war,
                    a.modifier_retaliation,
                    a.modifier_group_attack,
                    a.modifier_overseas,
                    a.modifier_chain_modifier,
                    a.modifier_warlord,
                    a.finishing_hit_effects,
                    a.attack_id,
                    a.attack_code
                FROM
                    attacks a
                LEFT JOIN
                    users u ON  ((a.attacker_id = u.user_id AND a.attacker_faction_id={faction_id}) 
                                OR (a.defender_id = u.user_id AND a.defender_faction_id={faction_id})  ) 
            ) a
            LEFT JOIN users AS oppo ON oppo.user_id = a.opponent_id and oppo.user_id IS NOT NULL
            ORDER BY started DESC;
    """)

    cursor.executescript(
        """   
    DROP VIEW IF EXISTS attacks_incoming;
    
    CREATE VIEW attacks_incoming AS
    WITH
        Attacks7d AS (
            SELECT
                opponent_id, 
                opponent_name,
                opponent_level,
                SUM(CASE WHEN event_type = 'defend' THEN 1 ELSE 0 END) AS attacks_7d,
                SUM(CASE WHEN event_type = 'defend' THEN respect_change ELSE 0 END) AS respect_lost_7d,
                COUNT(DISTINCT user_id) AS members_attacked_7d,
                MAX(CASE WHEN event_type = 'defend' THEN event_date ELSE NULL END) AS last_incoming_attack_date, -- Filter for 'defend' events
                JULIANDAY('now') - JULIANDAY(MAX(CASE WHEN event_type = 'defend' THEN event_date ELSE NULL END)) AS days_since_last_incoming_attack -- Filter for 'defend' events
            FROM
                attack_events
            WHERE
                opponent_id IS NOT NULL
                AND event_date >= DATE('now', '-7 days')
            GROUP BY
                opponent_id
        ),
        AttacksAllTime AS (
            SELECT
                opponent_id,
                SUM(CASE WHEN event_type = 'defend' THEN respect_change ELSE 0 END) AS overall_respect_lost
            FROM
                attack_events
            WHERE
                opponent_id IS NOT NULL
            GROUP BY
                opponent_id
        )
    SELECT
        COALESCE(a7d.opponent_id, aAll.opponent_id) AS user_id,
        COALESCE(a7d.opponent_name, a7d.opponent_id) AS user_name,
        opponent_level as user_level, 
        COALESCE(a7d.attacks_7d, 0) AS attacks_7d,
        COALESCE(a7d.respect_lost_7d, 0) AS respect_change_7d,
        COALESCE(a7d.members_attacked_7d, 0) AS individuals_7d,
        COALESCE(a7d.days_since_last_incoming_attack, 9999) AS days_since_last_event, -- Use a large value if no recent attacks
        a7d.last_incoming_attack_date as last_event_date,
        COALESCE(aAll.overall_respect_lost, 0) AS overall_respect_lost,
        (
            (
                COALESCE(ABS(a7d.respect_lost_7d), 0) * 1.1 +
                COALESCE(a7d.members_attacked_7d, 0) * 1 
                ) * (7 - COALESCE(a7d.days_since_last_incoming_attack, 7)) 
        ) AS interest_score
    FROM
        Attacks7d a7d
    FULL OUTER JOIN
        AttacksAllTime aAll ON a7d.opponent_id = aAll.opponent_id
    ORDER BY
        interest_score DESC;

    """
    )

    cursor.executescript("""   
        DROP VIEW IF EXISTS  attacks_outgoing;

        CREATE VIEW attacks_outgoing AS
            SELECT * FROM (
                SELECT
                            attack_events.user_id, 
                            attack_events.user_name,
                            users.level AS user_level,
                            SUM(CASE WHEN event_type = 'attack' THEN 1 ELSE 0 END) AS attacks_7d,
                        SUM(CASE WHEN event_type = 'defend' THEN 1 ELSE 0 END) AS defends_7d,
                            SUM(CASE WHEN event_type = 'attack' THEN respect_change ELSE 0 END) AS respect_change_7d,
                            COUNT(DISTINCT opponent_id) AS individuals_7d,
                            MAX(CASE WHEN event_type = 'defend' THEN event_date ELSE NULL END) AS last_event_date, -- Filter for 'defend' events
                            JULIANDAY('now') - JULIANDAY(MAX(CASE WHEN event_type = 'attack' THEN event_date ELSE NULL END)) AS days_since_last_event ,
                            SUM(CASE WHEN event_type = 'attack' THEN respect_change ELSE 0 END)  *COUNT(DISTINCT attack_events.user_id)  AS  interest_score
                        FROM
                            attack_events LEFT JOIN users on users.user_id = attack_events.user_id
                        WHERE
                            attack_events.user_id IS NOT NULL AND
                            event_date >= DATE('now', '-7 days')
                        GROUP BY attack_events.user_id
                        ) summary
                        WHERE attacks_7d>0
                        ORDER BY respect_change_7d DESC
""")


def update_attacks(conn, cursor, force=False):
    is_full_endpoint = False
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
        """INSERT OR IGNORE INTO attacks (
            attack_id,
            is_full_endpoint,
            attack_code,
            started,
            ended,
            started_timestamp,
            ended_timestamp,
            attacker_id,
            attacker_name,
            attacker_level,
            attacker_faction_id,
            attacker_faction_name,  -- New: Attacker Faction Name
            defender_id,
            defender_name,
            defender_level,
            defender_faction_id,
            defender_faction_name,  -- New: Defender Faction Name
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
         [
            (
                attackRow["id"],
                1 if is_full_endpoint else 0,
                attackRow["code"],
                datetime.fromtimestamp(attackRow["started"]).isoformat(),
                datetime.fromtimestamp(attackRow["ended"]).isoformat(),
                attackRow["started"],
                attackRow["ended"],
                attackRow["attacker"]["id"] if attackRow.get("attacker") else None,
                attackRow["attacker"].get("name") if attackRow.get("attacker") else None,
                attackRow["attacker"].get("level") if attackRow.get("attacker") else None,
                (
                    attackRow["attacker"].get("faction", {}).get("id")
                    if attackRow.get("attacker")
                    and attackRow["attacker"].get("faction", {})
                    else None
                ),
                (  # New: Attacker Faction Name
                    attackRow["attacker"].get("faction", {}).get("name")
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
                (  # New: Defender Faction Name
                    attackRow["defender"].get("faction", {}).get("name")
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

