import sqlite3
from datetime import datetime
from Torn.api import paginated_api_calls, cached_api_call, cached_api_paged_call


def create_crimes(conn, cursor, force=False):

    if force:
        print("Warning: create_crimes force=True")
        cursor.execute("DROP TABLE IF EXISTS oc_crime_instances;")
        cursor.execute("DROP TABLE IF EXISTS oc_versions;")
        cursor.execute("DROP TABLE IF EXISTS oc_statuses;")
        cursor.execute("DROP TABLE IF EXISTS oc_slots;")
        cursor.execute("DROP TABLE IF EXISTS oc_assignments;")
        cursor.execute("DROP TABLE IF EXISTS oc_assignments_history;")
        cursor.execute("DROP TABLE IF EXISTS oc_names;")
        cursor.execute("DROP TABLE IF EXISTS oc_positions;")

        cursor.execute("DROP VIEW IF EXISTS oc_assignments_view;")
        cursor.execute("DROP VIEW IF EXISTS oc_name_positions_view;")
        cursor.execute("DROP VIEW IF EXISTS oc_crime_instances_cube;")
    cursor.executescript("""          
        CREATE TABLE IF NOT EXISTS oc_assignments_history (
            assignment_history_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            batch_id INTEGER NOT NULL, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, -- time captured
            version_id INTEGER,
            crime_instance_id INTEGER NOT NULL,
            created DATETIME NOT NULL,
            oc_name TEXT NOT NULL,
            difficulty INTEGER NOT NULL,
            status TEXT NOT NULL,                
            slot_id INTEGER NOT NULL,  
            position TEXT NOT NULL,  
            item_requirement_id INTEGER,
            joined_at DATETIME,
            success_chance REAL NOT NULL,
            progress REAL NOT NULL,
            user_id INTEGER,
            user_name TEXT
        );
    
        """)
    
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS oc_versions
        (version_id INTEGER PRIMARY KEY, 
        name TEXT, 
        start_at DATETIME);
        
        INSERT OR IGNORE INTO oc_versions (version_id, name, start_at) 
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
        """CREATE TABLE IF NOT EXISTS oc_crime_instances
    (crime_instance_id INTEGER PRIMARY KEY, 
    version_id INTEGER,
    name TEXT, 
    difficulty INTEGER,
    status TEXT, 
    created_at DATETIME, 
    initiated_at DATETIME,
    planning_at DATETIME, 
    ready_at DATETIME, 
    expired_at DATETIME,
    FOREIGN KEY (name) REFERENCES oc_names(name)
    FOREIGN KEY (version_id) REFERENCES oc_versions(version_id),
    FOREIGN KEY (status) REFERENCES oc_statuses(status)
    )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS oc_statuses (
        status TEXT PRIMARY KEY
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS oc_slots
    (crime_slot_id INTEGER PRIMARY KEY AUTOINCREMENT, 
    crime_instance_id INTEGER,
    position TEXT, item_requirement_id INTEGER, 
    FOREIGN KEY (crime_instance_id) REFERENCES oc_crime_instances (crime_instance_id)
    )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS oc_assignments
    (slot_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, 
     crime_slot_id INTEGER,
     user_id INTEGER DEFAULT NULL, 
     joined_at DATETIME, 
     progress REAL,
     success_chance REAL,
     FOREIGN KEY (crime_slot_id) REFERENCES oc_slots (crime_slot_id), 
     FOREIGN KEY (user_id) REFERENCES users(user_id)
     );"""
    )

    # Create the oc_names table with generated id
    cursor.executescript(
        """DROP TABLE IF EXISTS oc_names;
        CREATE TABLE IF NOT EXISTS oc_names (
            name TEXT PRIMARY KEY,
            level INTEGER
        );"""
    )

    # Create the oc_positions table
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS oc_positions (
    crime_position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,  
    position TEXT,
    FOREIGN KEY (name) REFERENCES oc_names (name)
    )"""
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS oc_assignments_view;
    CREATE VIEW oc_assignments_view AS
    SELECT
        ci.crime_instance_id,
        ci.name AS name,
        ci.difficulty AS crime_difficulty,
        ci.status,                
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
    FROM oc_crime_instances ci 
    LEFT JOIN oc_slots cs ON cs.crime_instance_id = ci.crime_instance_id
    LEFT JOIN oc_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
    LEFT JOIN users ON sa.user_id = users.user_id;
        """
    )

    cursor.executescript(
        """DROP VIEW IF EXISTS oc_name_positions_view;
    CREATE VIEW oc_name_positions_view AS
    SELECT
        cn.name AS crime_name,
        cp.position
    FROM oc_names cn
    INNER JOIN oc_positions cp ON cn.name = cp.name;"""
    )

  

    cursor.executescript(
        """DROP VIEW IF EXISTS oc_crime_instances_cube ;
    CREATE VIEW oc_crime_instances_cube AS
    SELECT
        ci.crime_instance_id,
        ci.name AS crime_name,
        ci.difficulty AS crime_difficulty,
        ci.status AS status,
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
        oc_crime_instances ci
    LEFT JOIN
        oc_slots cs ON ci.crime_instance_id = cs.crime_instance_id
    LEFT JOIN
        oc_assignments sa ON cs.crime_slot_id = sa.crime_slot_id
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
        cursor.execute("DELETE FROM oc_crime_instances;")
        latest_timestamp = None
        assigments_batch_id=1000
        print("!",end="")
    else:
        cursor.execute(f"SELECT MAX({timestamp_field}) AS last_timestamp FROM oc_crime_instances;")
        latest_timestamp_datetime = cursor.fetchone()[0]
        latest_timestamp =datetime.fromisoformat(latest_timestamp_datetime).timestamp() if latest_timestamp_datetime else None   
        cursor.execute(f"SELECT MAX(batch_id) AS last_batch_id FROM oc_assignments_history;")
        latest_batch_id = cursor.fetchone()[0]
        assigments_batch_id = latest_batch_id if latest_batch_id else 1000 
        assigments_batch_id += 1
    update_crimeexp_ranks(conn, cursor, force)

    oc_crime_instances = paginated_api_calls(
        conn,
        cursor,
        endpoint="faction/crimes",
        params=None,
        timestamp_field=timestamp_field,
        fromTimestamp=latest_timestamp,
        dataKey="crimes",
        callback=_insertCrimes_callback_fn,  # callback
        callback_parameters={"assigments_batch_id":assigments_batch_id},
        short_name="crimes",
    )
    add_item_requirement_ids_to_items_table(conn,cursor)

def add_item_requirement_ids_to_items_table(conn,cursor):
    cursor.execute("""
        INSERT OR IGNORE INTO items (item_id) 
        SELECT DISTINCT item_requirement_id FROM oc_slots;
    """)

def _insertCrimes_callback_fn(conn, cursor, oc_crime_instances, parameters):
    assigments_batch_id = parameters["assigments_batch_id"]
    for crime in oc_crime_instances:
        try:
            created_at = datetime.fromtimestamp(crime["created_at"]).isoformat()
            version_id = (
                1
                if datetime.fromtimestamp(crime["created_at"]) <= datetime(2025, 1, 8)
                else 2
            )
            cursor.execute(
                """
                    INSERT INTO oc_crime_instances (crime_instance_id, version_id, name, difficulty, status, created_at, 
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
                """INSERT OR REPLACE INTO oc_slots 
                              (crime_instance_id, position, item_requirement_id)
                              VALUES (?, ?, ?)""",
                (crime["id"], slot["position"], item_requirement_id),
            )
            crime_slot_id = cursor.lastrowid
            # Insert slot assignments (if user exists)
            if slot["user"]:
                cursor.execute(
                    """
                        INSERT OR REPLACE INTO oc_assignments 
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
                
                cursor.execute("""
                    INSERT INTO oc_assignments_history (
                        batch_id,
                        crime_instance_id, version_id,
                        created, status,  
                        oc_name, difficulty,              
                        slot_id, position, item_requirement_id,
                        joined_at, success_chance, progress,
                        user_id)            
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,(
                        assigments_batch_id,
                        crime["id"],version_id,
                        created_at, crime["status"],
                        crime["name"], crime["difficulty"],
                        crime_slot_id, slot["position"], item_requirement_id,
                        datetime.fromtimestamp(slot["user"]["joined_at"]).isoformat(), slot["success_chance"], slot["user"]["progress"],
                        slot["user"]["id"]
                ))
          
    # Insert distinct crime names into oc_names table
    cursor.execute(
        """
            INSERT OR IGNORE INTO oc_statuses (status)
            SELECT DISTINCT status FROM oc_crime_instances"""
    )

    cursor.execute(
        """
            INSERT OR IGNORE INTO oc_names (name) 
            SELECT DISTINCT name FROM oc_crime_instances"""
    )

    # # Insert positions for each crime name
    cursor.execute("""DELETE FROM oc_positions """)
    cursor.execute(
        """
                    INSERT OR IGNORE INTO oc_positions (name, position)
                        SELECT DISTINCT name, position FROM (
                        SELECT DISTINCT cn.name, cs.position
                        FROM oc_crime_instances c 
                        INNER JOIN oc_names cn ON cn.name = c.name
                        INNER JOIN oc_slots cs ON c.crime_instance_id = cs.crime_instance_id 
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
        cursor.execute("""--DELETE FROM crimeexp_ranks_history""")  # Clear table if forced
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