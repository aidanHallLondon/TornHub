import sqlite3
import os

DB_PATH = 'data/db'
DB_NAME = 'torn_data.db'
DB_CONNECTPATH = f'{DB_PATH}/{DB_NAME}'
db_initialised = False

if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

def getPreference(settingName):
    # os.remove(DB_CONNECTPATH)
    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()
    try:
        sql = f'SELECT value FROM preferences WHERE key = "{settingName}"'
        cursor.execute(sql)
        result = cursor.fetchone()
        return result
    except:
        return None
    
def setPreference(settingName,value):
    if not settingName:
        return None
    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (settingName, value))
    conn.commit()
    conn.close()


def initDB():
    conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)  # Add detect_types

    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.executescript('''CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT);
                   
    INSERT OR IGNORE INTO preferences (key, value) 
    VALUES 
          ('TORN_API_KEY',NULL);                  
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
    (id INTEGER PRIMARY KEY, 
    name TEXT, 
    level INTEGER, 
    last_action_timestamp DATETIME, 
    status TEXT, 
    life_current INTEGER, 
    life_maximum INTEGER,
    has_early_discharge BOOLEAN, 
    until DATETIME, 
    is_revivable BOOLEAN)''')  # Added user columns

    cursor.execute('''CREATE TABLE IF NOT EXISTS faction_members
    (user_id INTEGER PRIMARY KEY, 
    days_in_faction INTEGER,
    position TEXT, 
    is_in_faction BOOLEAN DEFAULT 1,
    is_in_oc BOOLEAN, 
    FOREIGN KEY (user_id) REFERENCES users (id)
    )''')  # Added is_in_oc
  
   # Create tables if they don't exist
    cursor.executescript('''DROP TABLE crimes_version; 
                         CREATE TABLE IF NOT EXISTS crimes_version
    (version_id INTEGER PRIMARY KEY, 
    name TEXT, 
    start_at DATETIME);
    
    INSERT OR IGNORE INTO crimes_version (version_id, name, start_at) 
    VALUES 
            (1, 'orginal high success chances','2024-12-31'), 
            (2, 'Lowered successes for new crime instances','2025-01-09');                  
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS crimes
    (id INTEGER PRIMARY KEY, 
    version_id INTEGER,
    name TEXT, 
    difficulty INTEGER,
    status TEXT, 
    created_at DATETIME, 
    initiated_at DATETIME,
    planning_at DATETIME, 
    ready_at DATETIME, 
    expired_at DATETIME,
    FOREIGN KEY (name) REFERENCES crime_names(name)
    FOREIGN KEY (version_id) REFERENCES crimes_version(version_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_slots
    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
    crimes_id INTEGER,
    position TEXT, item_requirement_id INTEGER,
    success_chance REAL, 
    FOREIGN KEY (crimes_id) REFERENCES crimes (id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS slot_assignments
    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
     slot_id INTEGER,
     user_id INTEGER DEFAULT NULL, 
     joined_at DATETIME, 
     progress REAL,
     FOREIGN KEY (slot_id) REFERENCES crime_slots (id), 
     FOREIGN KEY (user_id) REFERENCES users(id)
     );''') 

    # Create the crime_names table with generated id
    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_names (name TEXT PRIMARY KEY);''')  
    
    # Create the crime_positions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crime_name TEXT,  
    position TEXT,
    FOREIGN KEY (crime_name) REFERENCES crime_names (name)
    )''')


    # Drop the old view if it exists and create it 
    cursor.execute("DROP VIEW IF EXISTS faction_members_view")
    cursor.execute('''CREATE VIEW faction_members_view AS
    SELECT 
        u.id, 
        u.name, 
        u.level, 
        u.last_action_timestamp, 
        u.status, 
        u.life_current, 
        u.life_maximum, 
        u.has_early_discharge, 
        u.until,
        u.is_revivable, 
        fm.days_in_faction, 
        fm.position, 
        fm.is_in_faction, 
        fm.is_in_oc
    FROM users u
    INNER JOIN faction_members fm ON u.id = fm.user_id''')

    cursor.executescript('''DROP VIEW IF EXISTS crime_slot_assignments_view;
    CREATE VIEW crime_slot_assignments_view AS
    SELECT
        cs.id AS slot_id,
        sa.user_id,
        c.name AS crime_name,
        cs.position AS slot_position,  -- Rename to avoid ambiguity
        fmv.name AS user_name,
        c.difficulty AS crime_difficulty,
        c.status AS crime_status,                
        cs.item_requirement_id,
        cs.success_chance,
        sa.joined_at,
        sa.progress,
        fmv.level AS user_level,
        fmv.position AS faction_position  -- Rename to avoid ambiguity   
    FROM crimes c 
    LEFT JOIN crime_slots cs ON cs.crimes_id = c.id
    LEFT JOIN slot_assignments sa ON cs.id = sa.slot_id
    LEFT JOIN faction_members_view fmv ON sa.user_id = fmv.id;
        ''')
    
    cursor.executescript('''DROP VIEW IF EXISTS crime_name_positions_view;
    CREATE VIEW crime_name_positions_view AS
    SELECT
        cn.name AS crime_name,
        cp.position
    FROM crime_names cn
    INNER JOIN crime_positions cp ON cn.name = cp.crime_name;''')
    
    cursor.executescript("""DROP VIEW IF EXISTS _rowCounts ;
    CREATE VIEW _rowCounts AS
        SELECT 'crime_name_positions_view' AS "name", 'view' AS "type", COUNT(*) AS "rows" FROM "crime_name_positions_view"
        UNION SELECT 'crime_names' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crime_names"
        UNION SELECT 'crime_positions' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crime_positions"
        UNION SELECT 'crime_slot_assignments_view' AS "name", 'view' AS "type", COUNT(*) AS "rows" FROM "crime_slot_assignments_view"
        UNION SELECT 'crime_slots' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crime_slots"
        UNION SELECT 'crimes' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crimes"
        UNION SELECT 'crimes_version' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crimes_version"
        UNION SELECT 'faction_members' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "faction_members"
        UNION SELECT 'faction_members_view' AS "name", 'view' AS "type", COUNT(*) AS "rows" FROM "faction_members_view"
        UNION SELECT 'preferences' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "preferences"
        UNION SELECT 'slot_assignments' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "slot_assignments"
        UNION SELECT 'sqlite_sequence' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "sqlite_sequence"
        UNION SELECT 'users' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "users"
      """)

    cursor.execute('''PRAGMA optimize;''')

    conn.commit()
    conn.close()

    db_initialised=True

    return db_initialised

