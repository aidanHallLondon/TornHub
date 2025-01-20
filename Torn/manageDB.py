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


def initDB(force=False):
    conn = sqlite3.connect(
        DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
    )  # Add detect_types
    cursor = conn.cursor()
    create_users(cursor, force=force)
    create_crimes(cursor, force=force)
    create_faction(cursor, force=force)
    create_applications(cursor, force=force)
    create_armory(cursor)
    create_admin(cursor, force=force)
    cursor.execute("""PRAGMA optimize;""")
    conn.commit()
    conn.close()

    db_initialised = True

    return db_initialised


def updateDB():
    conn = sqlite3.connect(
        DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
    )  # Add detect_types
    cursor = conn.cursor()
    #
    update_faction_members(cursor)
    update_crimes(cursor)
    update_applications(cursor)
    update_faction(cursor)
    update_armory(cursor)
    #
    cleamUpFKIssues(cursor)
    #
    conn.commit()
    conn.close()


def dumpResults(cursor, tablefmt="simple"):
    results = cursor.fetchall()
    tableHeaders = [desc[0] for desc in cursor.description]
    table = tabulate(results, headers=tableHeaders, tablefmt=tablefmt)
    print(table)


def cleamUpFKIssues(cursor):
    cursor.execute(
        """ 
        UPDATE slot_assignments 
            SET user_id = NULL 
                WHERE user_id NOT IN (SELECT user_id FROM users);
    """
    )