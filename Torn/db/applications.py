from Torn.api import cached_api_call, cached_api_paged_call


def create_applications(conn,cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS applications;")
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS applications (
        application_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        user_level INTEGER NOT NULL,
        user_strength INTEGER ,
        user_speed INTEGER ,
        user_dexterity INTEGER ,
        user_defense INTEGER ,
        message TEXT,
        valid_until INTEGER NOT NULL,
        status TEXT NOT NULL
    );"""
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications (user_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status);"
    )
    # cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_valid_until ON applications (valid_until);")


def update_applications(conn,cursor, cache_age_limit=3600, force=False):

    data =cached_api_call(conn,cursor,endpoint="faction/applications",  
                                params={"striptags": "false", "sort": "ASC"}, 
                                dataKey="applications", cache_age_limit=cache_age_limit, force=force) 
    for row in data:
        stats = row["user"]["stats"] if row["user"]["stats"] else {"strength":None, "speed":None, "dexterity":None, "defense":None}
        cursor.execute("""INSERT INTO applications (
        application_id, user_id, user_name, user_level, user_strength,
        user_speed, user_dexterity, user_defense, message, valid_until, status
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT (application_id) DO 
    UPDATE SET 
        user_id = excluded.user_id,
        user_name = excluded.user_name,
        user_level = excluded.user_level,
        user_strength = excluded.user_strength,
        user_speed = excluded.user_speed,
        user_dexterity = excluded.user_dexterity,
        user_defense = excluded.user_defense,
        message = excluded.message,
        valid_until = excluded.valid_until,
        status = excluded.status;""",
            (
                row["id"],
                row["user"]["id"],
                row["user"]["name"],
                row["user"]["level"],
                stats["strength"],
                stats["speed"],
                stats["dexterity"],
                stats["defense"],
                row["message"],
                row["valid_until"],
                row["status"],
            ),
        )
