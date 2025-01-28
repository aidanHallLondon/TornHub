import sqlite3
from datetime import datetime
from Torn.api import paginated_api_calls, cached_api_call, cached_api_paged_call


def create_crimes(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS crimes_version;")
        cursor.execute("DROP TABLE IF EXISTS crimeInstances;")
        cursor.execute("DROP TABLE IF EXISTS crime_status;")
        cursor.execute("DROP TABLE IF EXISTS crime_slots;")
        cursor.execute("DROP TABLE IF EXISTS slot_assignments;")
        cursor.execute("DROP TABLE IF EXISTS crime_names;")
        cursor.execute("DROP TABLE IF EXISTS crime_positions;")
        cursor.execute("DROP TABLE IF EXISTS crimeexp_ranks;")

        cursor.execute("DROP VIEW IF EXISTS crime_slot_assignments_view;")
        cursor.execute("DROP VIEW IF EXISTS crime_name_positions_view;")
        cursor.execute("DROP VIEW IF EXISTS _rowCounts;")
        cursor.execute("DROP VIEW IF EXISTS crimeInstance_cube;")

    cursor.executescript(
        """CREATE TABLE IF NOT EXISTS crimes_version
    (version_id INTEGER PRIMARY KEY, 
    name TEXT, 
    start_at DATETIME);
    
    INSERT OR IGNORE INTO crimes_version (version_id, name, start_at) 
    VALUES 
            (1, 'orginal high success chances','2024-12-31'), 
            (2, 'Lowered successes for new crime instances','2025-01-09');                  
    """
    )

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS crimeexp_ranks_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- New primary key
            batch_date DATE DEFAULT CURRENT_DATE,
            user_id INTEGER NOT NULL,
            crimeexp_rank INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE (user_id, batch_date)  -- Ensure unique user rank per day
            );
        CREATE INDEX IF NOT EXISTS idx_crimeexp_ranks_batch_date 
            ON crimeexp_ranks_history (batch_date DESC);
        CREATE INDEX IF NOT EXISTS idx_crimeexp_ranks_rank 
            ON crimeexp_ranks_history (crimeexp_rank ASC);                 
        CREATE INDEX IF NOT EXISTS idx_crimeexp_ranks_batch_rank 
            ON crimeexp_ranks_history (batch_date DESC, crimeexp_rank ASC);  

        DROP VIEW IF EXISTS crimeexp_ranks;
        CREATE VIEW crimeexp_ranks AS
            SELECT ranks.*, users.name AS user_name, users.level as user_level
            FROM crimeexp_ranks_history AS ranks
            LEFT JOIN users ON users.user_id = ranks.user_id
            WHERE batch_date = (SELECT MAX(batch_date) FROM crimeexp_ranks_history);                                                
        """)

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS crimeInstances
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
    )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS crime_status (crime_status TEXT PRIMARY KEY)"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS crime_slots
    (crime_slot_id INTEGER PRIMARY KEY AUTOINCREMENT, 
    crimeInstance_id INTEGER,
    position TEXT, item_requirement_id INTEGER, 
    FOREIGN KEY (crimeInstance_id) REFERENCES crimeInstances (crimeInstance_id)
    )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS slot_assignments
    (slot_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, 
     crime_slot_id INTEGER,
     user_id INTEGER DEFAULT NULL, 
     joined_at DATETIME, 
     progress REAL,
     success_chance REAL,
     FOREIGN KEY (crime_slot_id) REFERENCES crime_slots (crime_slot_id), 
     FOREIGN KEY (user_id) REFERENCES users(user_id)
     );"""
    )

    # Create the crime_names table with generated id
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS crime_names (name TEXT PRIMARY KEY);"""
    )

    # Create the crime_positions table
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS crime_positions (
    crime_position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    crime_name TEXT,  
    position TEXT,
    FOREIGN KEY (crime_name) REFERENCES crime_names (name)
    )"""
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS crime_slot_assignments_view;
    CREATE VIEW crime_slot_assignments_view AS
    SELECT
        ci.crimeInstance_id,
        ci.name AS crime_name,
        ci.difficulty AS crime_difficulty,
        ci.crime_status,                
        cs.crime_slot_id,
        cs.position AS slot_position,  -- Rename to avoid ambiguity
        cs.item_requirement_id,
        sa.joined_at,
        sa.success_chance,
        sa.progress,
        users.user_id,
        users.name AS user_name,
        users.level AS user_level,
        users.position_in_faction ,   
        users.last_action AS user_last_action,
        users.is_in_faction AS user_is_in_faction           
    FROM crimeInstances ci 
    LEFT JOIN crime_slots cs ON cs.crimeInstance_id = ci.crimeInstance_id
    LEFT JOIN slot_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
    LEFT JOIN users ON sa.user_id = users.user_id;
        """
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS crime_name_positions_view;
    CREATE VIEW crime_name_positions_view AS
    SELECT
        cn.name AS crime_name,
        cp.position
    FROM crime_names cn
    INNER JOIN crime_positions cp ON cn.name = cp.crime_name;"""
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS _rowCounts ;
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
      """
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS crimeInstance_cube ;
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
        sa.success_chance,
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
        crime_slots cs ON ci.crimeInstance_id = cs.crimeInstance_id
    LEFT JOIN
        slot_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
    LEFT JOIN
        users u ON sa.user_id = u.user_id;
    """
    )


def update_crimes(conn, cursor,force=False):
    """
    Fetches crime data using getCrimes() and updates the SQLite database.

    Args:
        db_path (str): Path to the SQLite database file.
    """
    timestamp_field="created_at"
    if force:
        cursor.execute("DELETE FROM crimeInstances;")
        cursor.execute("DELETE FROM crimeexp_ranks;")
        latest_timestamp = None
        print("!",end="")
    else:
        cursor.execute(f"SELECT MAX({timestamp_field}) AS last_timestamp FROM crimeInstances;")
        latest_timestamp_datetime = cursor.fetchone()[0]
        latest_timestamp =datetime.fromisoformat(latest_timestamp_datetime).timestamp() if latest_timestamp_datetime else None   

    update_crimeexp_ranks(conn, cursor, force)

    crimeInstances = paginated_api_calls(
        conn,
        cursor,
        endpoint="faction/crimes",
        params=None,
        timestamp_field=timestamp_field,
        fromTimestamp=latest_timestamp,
        dataKey="crimes",
        callback=_insertCrimes_callback_fn,  # callback
        callback_parameters=None,
        short_name="crimes",
    )


def _insertCrimes_callback_fn(conn, cursor, crimeInstances, parameters):
    for crime in crimeInstances:
        try:
            created_at = datetime.fromtimestamp(crime["created_at"]).isoformat()
            version_id = (
                1
                if datetime.fromtimestamp(crime["created_at"]) <= datetime(2025, 1, 8)
                else 2
            )
            cursor.execute(
                """
                    INSERT INTO crimeInstances (crimeInstance_id, version_id, name, difficulty, crime_status, created_at, 
                               initiated_at, planning_at, ready_at, expired_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    crime["id"],
                    version_id,
                    crime["name"],
                    crime["difficulty"],
                    crime["status"],
                    created_at,
                    (
                        datetime.fromtimestamp(crime["initiated_at"]).isoformat()
                        if crime["initiated_at"]
                        else None
                    ),
                    (
                        datetime.fromtimestamp(crime["planning_at"]).isoformat()
                        if crime["planning_at"]
                        else None
                    ),
                    (
                        datetime.fromtimestamp(crime["ready_at"]).isoformat()
                        if crime["ready_at"]
                        else None
                    ),
                    (
                        datetime.fromtimestamp(crime["expired_at"]).isoformat()
                        if crime["expired_at"]
                        else None
                    ),
                ),
            )
        except sqlite3.IntegrityError:
            pass  # Ignore if crime ID already exists

        # Insert or update crime slots
        for slot in crime["slots"]:
            item_requirement_id = (
                slot["item_requirement"]["id"] if slot["item_requirement"] else None
            )
            cursor.execute(
                """INSERT OR REPLACE INTO crime_slots 
                              (crimeInstance_id, position, item_requirement_id)
                              VALUES (?, ?, ?)""",
                (crime["id"], slot["position"], item_requirement_id),
            )
            crime_slot_id = cursor.lastrowid
            # Insert slot assignments (if user exists)
            if slot["user"]:
                cursor.execute(
                    """
                        INSERT OR REPLACE INTO slot_assignments 
                                (crime_slot_id, user_id, joined_at, success_chance, progress)
                                VALUES (?, ?, ?, ?, ?)""",
                    (
                        crime_slot_id,
                        slot["user"]["id"],
                        datetime.fromtimestamp(slot["user"]["joined_at"]).isoformat(),
                        slot["success_chance"],
                        slot["user"]["progress"],
                    ),
                )

    # Insert distinct crime names into crime_names table
    cursor.execute(
        """
            INSERT OR IGNORE INTO crime_status (crime_status)
            SELECT DISTINCT crime_status FROM crimeInstances"""
    )

    cursor.execute(
        """
            INSERT OR IGNORE INTO crime_names (name) 
            SELECT DISTINCT name FROM crimeInstances"""
    )

    # # Insert positions for each crime name
    cursor.execute("""DELETE FROM crime_positions """)
    cursor.execute(
        """
                    INSERT OR IGNORE INTO crime_positions (crime_name, position)
                        SELECT DISTINCT name, position FROM (
                        SELECT DISTINCT cn.name, cs.position
                        FROM crimeInstances c 
                        INNER JOIN crime_names cn ON cn.name = c.name
                        INNER JOIN crime_slots cs ON c.crimeInstance_id = cs.crimeInstance_id 
                        ) AS T1
     """
    )
    conn.commit()

def update_crimeexp_ranks(conn, cursor, force=False):
    crimeexp_ranks_from_api = cached_api_call(
        conn,
        cursor,
        endpoint="faction?selections=crimeexp",
        params=None,
        dataKey="crimeexp",
        force=force,
    )
    '''
    Load the crimeExperience ranks from the api and check them against the view that filters out the latest batch 
    If they are differnt insert tham as today's data. Ignore changes on any one day.
    The table crimeexp_ranks_history data will include at most one batch per day and no two batches will be the same.
    The view crimeexp_ranks just returns the newest batch.
    '''
    if force:
        cursor.execute("""DELETE FROM crimeexp_ranks_history""")  # Clear table if forced
    else:
        # Get the latest batch of rankings
        cursor.execute("""SELECT user_id, crimeexp_rank, batch_date FROM crimeexp_ranks ORDER BY crimeexp_rank ASC""")
        crimeexp_ranks_from_db = [row[0] for row in cursor.fetchall()]
        if crimeexp_ranks_from_api != crimeexp_ranks_from_db: 
            print("Crime Exp inject")
            cursor.executemany(
                """INSERT OR IGNORE INTO crimeexp_ranks_history (user_id, crimeexp_rank, batch_date) 
                   VALUES (?, ?, CURRENT_DATE)""",
                [(user, rank + 1) for rank, user in enumerate(crimeexp_ranks_from_api)], 
            )
            conn.commit()