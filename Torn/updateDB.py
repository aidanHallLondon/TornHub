import sqlite3
from Torn.api import getFactionMembers,getCrimes
from datetime import datetime
from Torn.manageDB import initDB 
import time
from Torn.manageDB import DB_CONNECTPATH #= 'data/db/torn_data.db'


def demo():
    initDB()
    updateDB()
    exampleQ()

def execute(cursor, label, sql, values=None):  # Add optional values parameter
    """
    Executes an SQL statement and prints the label and time taken.

    Args:
        cursor: The database cursor.
        label (str): A label for the SQL statement.
        sql (str): The SQL statement to execute.
        values (tuple, optional): Values to be passed to the execute method. Defaults to None.
    """
    start_time = time.time()
    if values:
        cursor.execute(sql, values)  # Execute with values if provided
    else:
        cursor.execute(sql)  # Execute without values otherwise
    end_time = time.time()
    time_taken = end_time - start_time
    # print(f"SQL {label}: Completed in {time_taken:.2f} seconds")


def update_faction_members():
    """
    Fetches faction member data and updates the SQLite database,
    normalizing the data into 'users' and 'faction_members' tables.

    Args:
        db_path (str): Path to the SQLite database file.
    """
    data = getFactionMembers()

    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)  # Add detect_types
    cursor = conn.cursor()
 
    # Insert or update users
    for member in data:
        try:
            last_action_timestamp = datetime.fromtimestamp(member['last_action']['timestamp']).isoformat()
            until_timestamp = datetime.fromtimestamp(member['status']['until']).isoformat() if member['status']['until'] else None

            cursor.execute('''
                    INSERT INTO users (id, name, level, last_action_timestamp, status, 
                               life_current, life_maximum, has_early_discharge, until, is_revivable) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (member['id'], 
                            member['name'], 
                            member['level'], 
                            last_action_timestamp, 
                            member['status']['state'],
                            member['life']['current'], 
                            member['life']['maximum'],
                            member['has_early_discharge'], until_timestamp, 
                            member['is_revivable']))
        except sqlite3.IntegrityError:
            pass  # Ignore if user ID already exists

    # Insert or update faction members
    for member in data:
        cursor.execute('''INSERT OR REPLACE INTO faction_members 
                          (user_id, days_in_faction, position, is_in_oc) 
                          VALUES (?, ?, ?, ?)''',
                       (member['id'], member['days_in_faction'], member['position'],
                        member['is_in_oc']))

  
    conn.commit()
    conn.close()


def update_crimes():
    """
    Fetches crime data using getCrimes() and updates the SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
    """

    crimes = getCrimes()  # Get the list of crimes directly

    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()

    # Insert or update crimes (ignore if crime ID already exists)
    for crime in crimes:
        try:
            cursor.execute('''
                    INSERT INTO crimes (id, name, difficulty, status, created_at, 
                               initiated_at, planning_at, ready_at, expired_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (crime['id'], 
                            crime['name'], 
                            crime['difficulty'], 
                            crime['status'],
                            datetime.fromtimestamp(crime['created_at']).isoformat() if crime['created_at'] else None,
                            datetime.fromtimestamp(crime['initiated_at']).isoformat() if crime['initiated_at'] else None,
                            datetime.fromtimestamp(crime['planning_at']).isoformat() if crime['planning_at'] else None,
                            datetime.fromtimestamp(crime['ready_at']).isoformat() if crime['ready_at'] else None,
                            datetime.fromtimestamp(crime['expired_at']).isoformat() if crime['expired_at'] else None
                            )
            )
        except sqlite3.IntegrityError:
            pass  # Ignore if crime ID already exists
       
        # Insert or update crime slots
        for slot in crime['slots']:
            item_requirement_id = slot['item_requirement']['id'] if slot['item_requirement'] else None
            cursor.execute('''INSERT OR REPLACE INTO crime_slots 
                              (crimes_id, position, item_requirement_id, success_chance)
                              VALUES (?, ?, ?, ?)''',
                           (crime['id'], 
                            slot['position'], 
                            item_requirement_id, 
                            slot['success_chance']))

            # Get the slot_id for the current slot
            cursor.execute("SELECT id FROM crime_slots WHERE crimes_id = ? AND position = ?",
                           (crime['id'], slot['position']))
            slot_id = cursor.fetchone()[0]

            # Insert slot assignments (if user exists)
            if slot['user']:
                cursor.execute('''INSERT INTO slot_assignments (slot_id, user_id, joined_at, progress)
                                  VALUES (?, ?, ?, ?)''', (
                                slot_id, 
                                slot['user']['id'], 
                                datetime.fromtimestamp(slot['user']['joined_at']).isoformat(), 
                                slot['user']['progress'])
                                )
    
    # Insert distinct crime names into crime_names table
    execute(cursor,'INSERT INTO crime_names ','''
            INSERT OR IGNORE INTO crime_names (name) 
            SELECT DISTINCT name FROM crimes''')

    # # Insert positions for each crime name
    cursor.execute(''' DELETE FROM crime_positions ''')
    execute(cursor,'INSERT INTO crime_positions ','''
                    INSERT OR IGNORE INTO crime_positions (crime_name, position)
                        SELECT DISTINCT name, position FROM (
                        SELECT DISTINCT cn.name, cs.position
                        FROM crimes c 
                        INNER JOIN crime_names cn ON cn.name = c.name
                        INNER JOIN crime_slots cs ON c.id = cs.crimes_id 
                        ) AS T1
     ''')
    conn.commit()
    conn.close()

def updateDB():
    update_crimes()
    update_faction_members()


def exampleQ():
    # Now you can query your data using SQL
    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()

    # Example query: Get all current faction members with level > 50
    cursor.execute(''' SELECT * FROM crime_positions''')
    high_level_members = cursor.fetchall()
    print(high_level_members)

    conn.close()

