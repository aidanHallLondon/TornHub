from Torn.api import cached_api_call
import sqlite3
from datetime import datetime


def create_users(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS users;")

    cursor.executescript(
        """
                         
        CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY, 
            name TEXT, 
            level INTEGER, 
            last_action DATETIME, 
            user_status TEXT, 
            life_current INTEGER, 
            life_maximum INTEGER,
            has_early_discharge BOOLEAN, 
            until DATETIME, 
            days_in_faction INTEGER,
            position_in_faction TEXT, 
            is_in_faction BOOLEAN DEFAULT 0,
            is_in_oc BOOLEAN, 
            is_revivable BOOLEAN,
            timestamp DATETIME DEFAULT GETDATE,
            is_rusty BOOLEAN DEFAULT True
        );
        CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);                                               
        CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
        CREATE INDEX IF NOT EXISTS idx_users_last_action ON users(last_action);  
        CREATE INDEX IF NOT EXISTS idx_users_is_in_faction ON users (is_in_faction);                           
        """
    )

    cursor.executescript(
        """
        DROP VIEW IF EXISTS users_unknown_from_attacks;
                         
        CREATE VIEW IF NOT EXISTS users_unknown_from_attacks AS         
            SELECT user_id FROM (
            SELECT  attacks.attacker_id as user_id, a.user_id AS matched, attacks.started as timestamp
            from attacks 
            LEFT JOIN users as a on a.user_id = attacks.attacker_id
            WHERE attacks.attacker_id IS NOT NULL and    a.user_id  IS  NULL
            UNION ALL 
            SELECT DISTINCT attacks.defender_id as user_id, d.user_id AS matched, attacks.started as timestamp
            from attacks
            LEFT JOIN users as d on d.user_id = attacks.defender_id
            WHERE attacks.defender_id IS NOT NULL and d.user_id  IS  NULL
            ) u
            GROUP BY user_id
            ORDER by max(timestamp);
        """
    )


def uodate_users(conn, cursor):
    insert_users_unknown(conn, cursor)


def getFactionMembers(
    conn, cursor, params={"striptags": "false"}, cache_age_limit=3600 * 24, force=False
):
    return cached_api_call(
        conn,
        cursor,
        "faction/members",
        dataKey="members",
        params=params,
        cache_age_limit=cache_age_limit,
        force=force,
    )


def update_faction_members(conn, cursor):
    """
    Fetches faction member data and updates the SQLite database,

    Args:
        db_path (str): Path to the SQLite database file.
    """
    cursor.executemany(
        """
            INSERT OR REPLACE INTO users (
                    user_id, name, level, last_action, user_status, 
                    life_current, life_maximum, has_early_discharge, until, is_revivable,
                    days_in_faction, is_in_faction, position_in_faction, is_in_oc
                    ) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?,?,?,?)""",
        [
            (  # Array of tuples
                member["id"],
                member["name"],
                member["level"],
                datetime.fromtimestamp(member["last_action"]["timestamp"]).isoformat(),
                member["status"]["state"],
                member["life"]["current"],
                member["life"]["maximum"],
                member["has_early_discharge"],
                (
                    datetime.fromtimestamp(member["status"]["until"]).isoformat()
                    if member["status"]["until"]
                    else None
                ),
                member["is_revivable"],
                member["days_in_faction"],
                1,  # is_in_faction
                member["position"],
                member["is_in_oc"],
            )
            for member in getFactionMembers(
                conn,
                cursor,
            )
        ],
    )


def insert_users_unknown(conn, cursor):
    print('insert_users_unknown')

    cursor.execute("""SELECT ae.opponent_id
                        FROM attack_events  ae
                        LEFT JOIN users on opponent_id=users.user_id
                        WHERE opponent_id IS NOT NULL and users.name IS NULL
                        order BY event_date DESC LIMIT 30
                    """)
    user_id_list = cursor.fetchall()
    
    # cursor.execute("""SELECT user_id FROM users_unknown_from_attacks LIMIT 10""")
    # user_id_list = cursor.fetchall()
    if user_id_list and len(user_id_list):
        cursor.executemany(
            """INSERT OR IGNORE INTO users (user_id) VALUES (?)""",
            user_id_list,  # Array of tuples
        )
    update_users(conn, cursor, user_id_list=user_id_list)


def update_users(conn, cursor, user_id_list=None, force=False):
    if user_id_list is None:
        cursor.execute(
            """SELECT user_id FROM users WHERE user_name IS NULL OR is_rusty=1 ORDER BY 1 ASC"""
        )
        user_id_list = cursor.fetchall()
    if len(user_id_list):
        for (user_id,) in user_id_list:  # data looks like [(1,), (172,), (568,), (1203,),
            update_user(conn, cursor, user_id=user_id)


def getUser(
    conn,
    cursor,
    user_id,
    params={},
    cache_age_limit=3600 * 24,
    force=False,
):
    params["id"] = user_id
    return cached_api_call(
        conn,
        cursor,
        "user?selections=profile",
        dataKey=None,
        params=params,
        cache_age_limit=cache_age_limit,
        force=force,
    )


def update_user(conn, cursor, user_id, cache_age_limit=3600 * 12, force=False):
    if not user_id:
        return
    data = getUser(
        conn,
        cursor,
        user_id=user_id,
        cache_age_limit=cache_age_limit,
        force=force,
    )
    # print(f'''data={data}''')
    if data and len(data) and "name" in data:
        user = data
        cursor.execute(
            """
                INSERT OR REPLACE INTO users (
                        user_id, name, level, last_action, user_status, 
                        life_current, life_maximum
                        ) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                user["name"],
                user["level"],
                datetime.fromtimestamp(user["last_action"]["timestamp"]).isoformat(),
                user["status"]["state"],
                user["life"]["current"],
                user["life"]["maximum"],
            ),
        )

    # print(json.dumps(data, indent=2))
    if "error" in data:
        return


# Basic
# {
#   "level": 21,
#   "gender": "Male",
#   "player_id": 3497989,
#   "name": "SaucyNewfie",
#   "status": {
#     "description": "Okay",
#     "details": "",
#     "state": "Okay",
#     "color": "green",
#     "until": 0
#   }
# }
# Profile
# {
#   "rank": "Above average Samaritan",
#   "level": 21,
#   "honor": 827,
#   "gender": "Male",
#   "property": "Private Island",
#   "signup": "2024-11-22 14:16:08",
#   "awards": 107,
#   "friends": 33,
#   "enemies": 1,
#   "forum_posts": 14,
#   "karma": 2,
#   "age": 75,
#   "role": "Civilian",
#   "donator": 1,
#   "player_id": 3497989,
#   "name": "SaucyNewfie",
#   "property_id": 2151299,
#   "revivable": 1,
#   "profile_image": "https://profileimages.torn.com/90fdc9e9-4113-4f10-8d4b-565d38c41b82-3497989.png",
#   "life": {
#     "current": 925,
#     "maximum": 925,
#     "increment": 55,
#     "interval": 300,
#     "ticktime": 117,
#     "fulltime": 0
#   },
#   "status": {
#     "description": "Okay",
#     "details": "",
#     "state": "Okay",
#     "color": "green",
#     "until": 0
#   },
#   "job": {
#     "job": "Director",
#     "position": "Director",
#     "company_id": 112297,
#     "company_name": "Saucy&#039;s FlexAppealFitness",
#     "company_type": 29
#   },
#   "faction": {
#     "position": "Made-Man",
#     "faction_id": 50245,
#     "days_in_faction": 74,
#     "faction_name": "Familia Delinquentium",
#     "faction_tag": "|FD|",
#     "faction_tag_image": "50245-93778.png"
#   },
#   "married": {
#     "spouse_id": 3538664,
#     "spouse_name": "LadyArt3mis",
#     "duration": 29
#   },
#   "basicicons": {
#     "icon6": "Male",
#     "icon4": "Subscriber",
#     "icon8": "Married - To LadyArt3mis",
#     "icon73": "Company - Director of Saucy's FlexAppealFitness (Fitness Center)",
#     "icon9": "Faction - Made-Man of Familia Delinquentium"
#   },
#   "states": {
#     "hospital_timestamp": 0,
#     "jail_timestamp": 0
#   },
#   "last_action": {
#     "status": "Offline",
#     "timestamp": 1738777801,
#     "relative": "3 minutes ago"
#   },
#   "competition": {
#     "name": "Rock, Paper, Scissors",
#     "status": "scissors",
#     "current_hp": 10,
#     "max_hp": 27
#   }
# }
