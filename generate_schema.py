import os
import sqlite3
from Torn.manageDB import initDB,DB_CONNECTPATH,updateDB
from tabulate import tabulate
from eralchemy import render_er
from sqlalchemy import create_engine,MetaData



conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()
initDB(conn,cursor)
updateDB(conn,cursor)
cursor.execute('''SELECT schema.type, schema.name, row_count 
               FROM sqlite_master AS Schema 
               LEFT JOIN _row_counts as rc ON rc.name = Schema.name AND rc.type = Schema.type
               WHERE Schema.name NOT LIKE '[_]%' 
               ORDER BY 3 DESC,2,1''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))
print('----')
cursor.execute('''SELECT sql FROM sqlite_master AS Schema 
               WHERE Schema.name NOT LIKE '[_]%'  
               ORDER BY Schema.name,Schema.type''')
# Fetch all results and filter out None values
sql_statements = [row[0] for row in cursor.fetchall() if row[0] is not None]

# Generate the table as a string with breaks between SQL statements
table_string_with_breaks = "\n\n".join(sql_statements)  # Join with double newlines

if not os.path.exists("data/db/images"): os.makedirs("data/db/images")


# Write the table string to a file
with open("data/db/schema_dump.txt", "w") as targetFile:
    targetFile.write(table_string_with_breaks)


# Generate the ER diagram
# conn = sqlite3.connect(DB_CONNECTPATH)
engine = create_engine(f'sqlite:///./{DB_CONNECTPATH}')  # Note the triple slash ///
metadata = MetaData()
metadata.reflect(bind=engine)

render_er(metadata, 'reports/db/images/schema_diagram.png') 

# Generate the main diagram, excluding the large tables
exclude_list = ['faction_records'] 
filtered_metadata = MetaData()
all_tables = metadata.tables.keys()  # Get names of all tables
included_tables = [table for table in all_tables if table not in exclude_list]
filtered_metadata.reflect(bind=engine, only=included_tables)
render_er(filtered_metadata, 'reports/db/images/schema_diagram_without_factionrecords.png')

# Generate a separate diagram for the large table
large_table_metadata = MetaData()
large_table_metadata.reflect(bind=engine, only=exclude_list)
render_er(large_table_metadata, 'reports/db/images/schema_diagram_for_factionrecords.png')

print('')
cursor.execute('''PRAGMA integrity_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))
print('\nforeign_key_check (empty is good)')
cursor.execute('''PRAGMA foreign_key_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))

conn.close