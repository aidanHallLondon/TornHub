import sqlite3
from Torn.manageDB import initDB,DB_CONNECTPATH,updateDB
from tabulate import tabulate
from eralchemy import render_er
from sqlalchemy import create_engine,MetaData



conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
cursor = conn.cursor()
initDB(conn,cursor)
updateDB(conn,cursor)
cursor.execute('''SELECT schema.type, schema.name,row_count FROM sqlite_master AS Schema 
               LEFT JOIN _rowCounts as rc ON rc.name = Schema.name AND rc.type = Schema.type
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

# Write the table string to a file
with open("data/db/schema_dump.txt", "w") as targetFile:
    targetFile.write(table_string_with_breaks)


# Generate the ER diagram
# conn = sqlite3.connect(DB_CONNECTPATH)
engine = create_engine(f'sqlite:///./{DB_CONNECTPATH}')  # Note the triple slash ///
metadata = MetaData()
metadata.reflect(bind=engine)

render_er(metadata, 'data/db/schema_diagram.png') 

print('')
cursor.execute('''PRAGMA integrity_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))
print('\nforeign_key_check (empty is good)')
cursor.execute('''PRAGMA foreign_key_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))

conn.close