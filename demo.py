import sqlite3 # db engine
from Torn.manageDB import initDB,DB_CONNECTPATH
from Torn.updateDB import updateDB
from tabulate import tabulate # optional support for outputing tables as grids or HTML
 
# Optional - you only need to update once and can skip these for some scripts
initDB() # creates the database if not already done 
updateDB() # updates the data using the API
 

conn = sqlite3.connect(DB_CONNECTPATH)
cursor = conn.cursor()

# executing a command:
cursor.execute('''PRAGMA integrity_check;''')
#  Print all the results (cursor.fetchall()) in a simple layout with headers
results = cursor.fetchall()
tableHeaders = [desc[0] for desc in cursor.description]
table = tabulate(results, headers=tableHeaders, tablefmt="simple")
print(table)
# print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="simple"))

# run a simple query
cursor.execute('''
    SELECT type, name 
    FROM sqlite_master 
    WHERE name NOT LIKE '[_]%' 
    ORDER BY 1, 2
''')
# print the results in a grid
#print(tabulate(cursor.fetchall(), headers= [desc[0] for desc in cursor.description], tablefmt="grid"))
results = cursor.fetchall()
tableHeaders = [desc[0] for desc in cursor.description]
table =tabulate(results, headers=tableHeaders, tablefmt="grid")
print(table)
# Commit changes if make any
# comm.commit 

# Close the connection
conn.close