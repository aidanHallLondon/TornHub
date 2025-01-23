import sqlite3
import os
from tabulate import tabulate
from datetime import datetime

from Torn.db.admin import create_admin
from Torn.db.applications import create_applications, update_applications
from Torn.db.armory import create_armory, update_armory
from Torn.db.crimes import create_crimes, update_crimes
from Torn.db.faction import create_faction, update_faction
from Torn.db.users import create_users, update_faction_members
from Torn.db._globals import DB_PATH, DB_NAME, DB_CONNECTPATH

db_initialised = False

if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)



def initDB(conn,cursor,force=False):
    create_admin(conn,cursor, force=force)
    create_users(conn,cursor, force=force)
    create_crimes(conn,cursor, force=force)
    create_faction(conn,cursor, force=force)
    create_applications(conn,cursor, force=force)
    create_armory(conn,cursor,)
    cursor.execute("""PRAGMA optimize;""")
    conn.commit()
    db_initialised = True
    return db_initialised

def updateDB(conn,cursor):
    update_faction_members(conn,cursor)
    update_crimes(conn,cursor)
    update_applications(conn,cursor)
    update_faction(conn,cursor)
    update_armory(conn, cursor)
    #
    cleamUpFKIssues(conn,cursor)

def dumpResults(conn,cursor, tablefmt="simple"):
    results = cursor.fetchall()
    tableHeaders = [desc[0] for desc in cursor.description]
    table = tabulate(results, headers=tableHeaders, tablefmt=tablefmt)
    print(table)


def cleamUpFKIssues(conn,cursor):
    cursor.execute(
        """ 
        UPDATE slot_assignments 
            SET user_id = NULL 
                WHERE user_id NOT IN (SELECT user_id FROM users);
    """
    )