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
    )''')  
  
   # Create tables if they don't exist
    cursor.executescript('''CREATE TABLE IF NOT EXISTS crimes_version
    (version_id INTEGER PRIMARY KEY, 
    name TEXT, 
    start_at DATETIME);
    
    INSERT OR IGNORE INTO crimes_version (version_id, name, start_at) 
    VALUES 
            (1, 'orginal high success chances','2024-12-31'), 
            (2, 'Lowered successes for new crime instances','2025-01-09');                  
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS crimeInstances
    (crimeInstance_id INTEGER PRIMARY KEY, 
    version_id INTEGER,
    name TEXT, 
    difficulty INTEGER,
    crime_status TEXT, 
    created_at DATETIME, 
    initiated_at DATETIME,
    planning_at DATETIME, 
    ready_at DATETIME, 
    expired_at DATETIME,
    FOREIGN KEY (name) REFERENCES crime_names(name)
    FOREIGN KEY (version_id) REFERENCES crimes_version(version_id),
    FOREIGN KEY (crime_status) REFERENCES crime_status(crime_status)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_status (crime_status TEXT PRIMARY KEY)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_slots
    (crime_slot_id INTEGER PRIMARY KEY AUTOINCREMENT, 
    crimeInstance_id INTEGER,
    position TEXT, item_requirement_id INTEGER,
    success_chance REAL, 
    FOREIGN KEY (crimeInstance_id) REFERENCES crimeInstances (crimeInstance_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS slot_assignments
    (slot_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, 
     crime_slot_id INTEGER,
     user_id INTEGER DEFAULT NULL, 
     joined_at DATETIME, 
     progress REAL,
     FOREIGN KEY (crime_slot_id) REFERENCES crime_slots (crime_slot_id), 
     FOREIGN KEY (user_id) REFERENCES users(user_id)
     );''') 

    # Create the crime_names table with generated id
    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_names (name TEXT PRIMARY KEY);''')  
    
    # Create the crime_positions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS crime_positions (
    crime_position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    crime_name TEXT,  
    position TEXT,
    FOREIGN KEY (crime_name) REFERENCES crime_names (name)
    )''')



    cursor.executescript('''DROP VIEW IF EXISTS crime_slot_assignments_view;
    CREATE VIEW crime_slot_assignments_view AS
    SELECT
        cs.crime_slot_id,
        users.user_id,
        c.name AS crime_name,
        cs.position AS slot_position,  -- Rename to avoid ambiguity
        users.name AS user_name,
        c.difficulty AS crime_difficulty,
        c.crime_status AS crime_status,                
        cs.item_requirement_id,
        cs.success_chance,
        sa.joined_at,
        sa.progress,
        users.level AS user_level,
        users.position_in_faction    
    FROM crimeInstances c 
    LEFT JOIN crime_slots cs ON cs.crimeInstance_id = c.crimeInstance_id
    LEFT JOIN slot_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
    LEFT JOIN users ON sa.user_id = users.user_id;
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
        UNION SELECT 'crimeInstances' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crimeInstances"
        UNION SELECT 'crimes_version' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "crimes_version"
        UNION SELECT 'preferences' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "preferences"
        UNION SELECT 'slot_assignments' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "slot_assignments"
        UNION SELECT 'sqlite_sequence' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "sqlite_sequence"
        UNION SELECT 'users' AS "name", 'table' AS "type", COUNT(*) AS "rows" FROM "users"
      """)

    cursor.executescript('''DROP VIEW IF EXISTS crimeInstance_cube ;
    CREATE VIEW crimeInstance_cube AS
    SELECT
        ci.crimeInstance_id,
        ci.name AS crime_name,
        ci.difficulty AS crime_difficulty,
        ci.crime_status AS crime_status,
        ci.created_at AS crime_created_at,
        ci.initiated_at AS crime_initiated_at,
        ci.planning_at AS crime_planning_at,
        ci.ready_at AS crime_ready_at,
        ci.expired_at AS crime_expired_at,
        cs.crime_slot_id,
        cs.position AS slot_position,
        cs.item_requirement_id,
        cs.success_chance,
        sa.slot_assignment_id,
        sa.joined_at AS assignment_joined_at,
        sa.progress AS assignment_progress,
        u.user_id,
        u.name AS user_name,
        u.level AS user_level,
        u.last_action AS user_last_action,
        u.user_status AS user_status,
        u.life_current AS user_life_current,
        u.life_maximum AS user_life_maximum,
        u.has_early_discharge AS user_has_early_discharge,
        u.until AS user_until,
        u.days_in_faction AS user_days_in_faction,
        u.position_in_faction AS user_position_in_faction,
        u.is_in_faction AS user_is_in_faction,
        u.is_in_oc AS user_is_in_oc,
        u.is_revivable AS user_is_revivable
    FROM
        crimeInstances ci
    LEFT JOIN
        crime_slots cs ON ci.crimeInstance_id = cs.crimes_id
    LEFT JOIN
        slot_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
    LEFT JOIN
        users u ON sa.user_id = u.user_id;
    ''')

    cursor.execute('''PRAGMA optimize;''')

    conn.commit()
    conn.close()

    db_initialised=True

    return db_initialised

