from datetime import datetime
import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.db.faction_upgrades import create_faction_upgrades, update_faction_upgrades
from Torn.db.revives import create_revives, update_revives
from Torn.manageDB import  initDB, updateDB, dumpResults
# from Torn.db.faction import create_faction, update_faction
from Torn.api import _api_raw_call, _getApiURL, cached_api_call, cached_api_paged_call, date_to_unix
import json
from Torn.db.attacks import create_attacks, update_attacks
import requests



def main():
    conn = sqlite3.connect(
        DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) 
    cursor = conn.cursor()

    initDB(conn,cursor)  # creates the database structure if not already done
    conn.commit()
    updateDB(conn,cursor)
    conn.commit()
    loadit(conn,cursor)
    conn.commit()
    conn.close()


def loadit(conn,cursor):
    pass


main()