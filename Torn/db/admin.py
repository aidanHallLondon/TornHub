

def create_admin(cursor, force=False):
    '''
    Create the admin tables and views
    '''
    if force:
        cursor.execute("DROP TABLE IF EXISTS preferences;")

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
