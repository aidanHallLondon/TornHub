import sqlite3
import os
from tabulate import tabulate
from datetime import datetime

from Torn.db.admin import create_admin
from Torn.db.applications import create_applications, update_applications
from Torn.db.armory import create_armory, update_armory
from Torn.db.attacks import create_attacks, update_attacks
from Torn.db.crimes import create_crimes, update_crimes
from Torn.db.faction import create_faction, get_faction_id, update_faction
from Torn.db.faction_upgrades import create_faction_upgrades, update_faction_upgrades
from Torn.db.items import create_items, update_items
from Torn.db.revives import create_revive_contracts, create_revives, update_revive_contracts, update_revives
from Torn.db.users import create_users, uodate_users, update_faction_members
from Torn.db._globals import DB_PATH, DB_NAME, DB_CONNECTPATH

db_initialised = False
last_updateDB = None

if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)


def get_last_updateDB_delta():
    global last_updateDB
    if last_updateDB is None:
        return None
    return round((datetime.now() - last_updateDB).total_seconds())


def set_last_update():
    global last_updateDB
    last_updateDB = datetime.now()


def initDB(conn, cursor, force=False):
    faction_id = get_faction_id(conn, cursor)
    create_items(conn, cursor, force=force)
    create_faction(conn, cursor, force=force)
    conn.commit()
    create_admin(conn, cursor, force=force)
    create_users(conn, cursor, force=force)
    create_crimes(conn, cursor, force=force)
    create_applications(conn, cursor, force=force)
    create_armory(conn, cursor, force=force)
    create_faction_upgrades(conn, cursor, force=force)
    create_attacks(conn, cursor, faction_id=faction_id, force=force)
    create_revives(conn, cursor, force=force)
    create_revive_contracts(conn, cursor, force=force)

    conn.commit()
    db_initialised = True
    return db_initialised


def updateDB(conn, cursor, force=False):
    update_faction(conn, cursor)
    conn.commit()
    update_faction_members(conn, cursor)
    update_revives(conn, cursor, force=force)  
    update_revive_contracts(conn, cursor, force=force)
    update_crimes(conn, cursor, force=force)
    update_items(
        conn, cursor, force=force
    )  # should occur AFTER crimes may add new items to be looked up
    update_applications(conn, cursor)
    update_armory(conn, cursor)
    update_faction_upgrades(
        conn,
        cursor,
    )
    update_attacks(conn, cursor, force=force)
    #
    uodate_users(conn, cursor)

    conn.commit()
    print("\n < Updates done")
    #
    cleanUpFKIssues(conn, cursor)
    cursor.execute("""PRAGMA optimize;""")
    print(" < optimize done")

    set_last_update()


def dumpResults(conn, cursor, tablefmt="simple"):
    results = cursor.fetchall()
    tableHeaders = [desc[0] for desc in cursor.description]
    table = tabulate(results, headers=tableHeaders, tablefmt=tablefmt)
    print(table)


def cleanUpFKIssues(conn, cursor):
    cursor.execute(
        """ 
        UPDATE oc_assignments 
            SET user_id = NULL 
                WHERE user_id NOT IN (SELECT user_id FROM users);
    """
    )
