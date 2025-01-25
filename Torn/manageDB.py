import sqlite3
import os
from tabulate import tabulate
from datetime import datetime

from Torn.db.admin import create_admin
from Torn.db.applications import create_applications, update_applications
from Torn.db.armory import create_armory, update_armory
from Torn.db.attacks import create_attacks, update_attacks
from Torn.db.crimes import create_crimes, update_crimes
from Torn.db.faction import create_faction, update_faction
from Torn.db.faction_upgrades import create_faction_upgrades, update_faction_upgrades
from Torn.db.revives import create_revives, update_revives
from Torn.db.users import create_users, update_faction_members
from Torn.db._globals import DB_PATH, DB_NAME, DB_CONNECTPATH

db_initialised = False

if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

   


def initDB(conn,cursor,force=False):
    create_faction(conn,cursor, force=force)
    conn.commit()
    create_admin(conn,cursor, force=force)
    create_users(conn,cursor, force=force)
    create_crimes(conn,cursor, force=force)
    create_applications(conn,cursor, force=force)
    create_armory(conn,cursor,force=force)
    create_faction_upgrades(conn,cursor, force=force)
    create_attacks(conn,cursor,force=force)
    create_revives(conn,cursor, force=force)
    conn.commit()
    db_initialised = True
    return db_initialised

def updateDB(conn,cursor,force=False):
    update_faction(conn,cursor)    
    conn.commit()    
    update_faction_members(conn,cursor)
    update_revives(conn,cursor, force=force) # FORCE FORCE
    update_crimes(conn,cursor, force=force)
    update_applications(conn,cursor)
    update_armory(conn, cursor)
    update_faction_upgrades(conn,cursor,)
    update_attacks(conn,cursor, force=force)


    conn.commit()
    print("\n < Updates done")
    #
    cleanUpFKIssues(conn,cursor)
    cursor.execute("""PRAGMA optimize;""")
    print(" < optimize done")
 
def dumpResults(conn,cursor, tablefmt="simple"):
    results = cursor.fetchall()
    tableHeaders = [desc[0] for desc in cursor.description]
    table = tabulate(results, headers=tableHeaders, tablefmt=tablefmt)
    print(table)


def cleanUpFKIssues(conn,cursor):
    cursor.execute(
        """ 
        UPDATE slot_assignments 
            SET user_id = NULL 
                WHERE user_id NOT IN (SELECT user_id FROM users);
    """
    )