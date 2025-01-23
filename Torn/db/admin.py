

def create_admin(conn,cursor, force=False):
    '''
    Create the admin tables and views
    '''
    if force:
        cursor.executescript('''
            DROP TABLE IF EXISTS preferences;
            DROP TABLE IF EXISTS apiSemaphores;
        ''')

    cursor.executescript('''CREATE TABLE IF NOT EXISTS apiSemaphores (
        -- list of the latest API call timestamps to allow us to throttle the call rate
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timeStamp DATETIME NOT NULL);
                         
        CREATE INDEX IF NOT EXISTS idx_semaphore_timestamp ON apiSemaphores (timeStamp);
    ''')

    cursor.executescript('''CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT);
                    
    INSERT OR IGNORE INTO preferences (key, value) 
    VALUES 
            ('TORN_API_KEY',NULL);                  
    ''')

    # _rowCounts view
    # Create a view to show the row count of each table
    cursor.executescript("""DROP VIEW IF EXISTS _rowCounts;""")
    cursor.execute("SELECT name,type FROM sqlite_master WHERE (type='table' OR type='view') AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    sql = "CREATE VIEW _rowCounts AS --dynamic code\n"
    for i, table in enumerate(tables):
        sql += f"SELECT '{table[0]}' AS name, '{table[1]}' AS type, COUNT(*) AS row_count FROM {table[0]}"
        if i < len(tables) - 1:
            sql += " UNION ALL\n"
    cursor.executescript(sql)
