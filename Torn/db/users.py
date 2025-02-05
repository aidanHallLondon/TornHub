from Torn.api import cached_api_call
import sqlite3
from datetime import datetime

def create_users(conn,cursor, force=False):
    if force: cursor.execute("DROP TABLE IF EXISTS users;")
    cursor.executescript('''CREATE TABLE IF NOT EXISTS users
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
            is_revivable BOOLEAN
        );
        CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);                                               
        CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
        CREATE INDEX IF NOT EXISTS idx_users_last_action ON users(last_action);  
        CREATE INDEX IF NOT EXISTS idx_users_is_in_faction ON users (is_in_faction);                           
        ''')  
    
def getFactionMembers(conn,cursor,params={"striptags": "false"}, cache_age_limit=3600*24, force=False):
    return cached_api_call(conn,cursor,"faction/members", dataKey="members", params=params, cache_age_limit=cache_age_limit, force=force) 

def update_faction_members( conn,cursor):
    """
    Fetches faction member data and updates the SQLite database,

    Args:
        db_path (str): Path to the SQLite database file.
    """
    cursor.executemany('''
            INSERT OR REPLACE INTO users (
                    user_id, name, level, last_action, user_status, 
                    life_current, life_maximum, has_early_discharge, until, is_revivable,
                    days_in_faction, is_in_faction, position_in_faction, is_in_oc
                    ) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?, ?,?,?,?)''',
                [( # Array of tuples
                member['id'], 
                member['name'], 
                member['level'], 
                datetime.fromtimestamp(member['last_action']['timestamp']).isoformat(), 
                member['status']['state'],
                member['life']['current'], 
                member['life']['maximum'],
                member['has_early_discharge'], 
                datetime.fromtimestamp(member['status']['until']).isoformat() if member['status']['until'] else None, 
                member['is_revivable'],
                member['days_in_faction'], 
                1, # is_in_faction
                member['position'],
                member['is_in_oc']
            ) for member in getFactionMembers(conn,cursor,)]
    )
    