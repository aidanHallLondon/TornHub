import sqlite3
from Torn.manageDB import initDB,DB_CONNECTPATH
from Torn.updateDB import updateDB
from tabulate import tabulate

initDB()
updateDB()

conn = sqlite3.connect(DB_CONNECTPATH)
cursor = conn.cursor()

print('\n\n')
cursor.execute('''PRAGMA integrity_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))
print('\n\foreign_key_check (empty is good)')
cursor.execute('''PRAGMA foreign_key_check;''')
print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))

conn.close