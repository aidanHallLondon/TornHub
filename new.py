import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.db.faction_upgrades import create_faction_upgrades, update_faction_upgrades
from Torn.manageDB import  initDB, updateDB, dumpResults
# from Torn.db.faction import create_faction, update_faction
from Torn.api import cached_api_call, cached_api_paged_call
import json
from Torn.db.attacks import create_attacks, update_attacks


selectionsDone = [
    "crimes", "crimeexp",
    "members",
    "basic","currency","hof","stats","timestamp","lookup",
    "upgrades",
    "applications", 
    "armor", "boosters","medical","temporary","weapons", "drugs","caches","cesium",
    "attacks", "attacksfull",
]
selections = [
    "territory",
    "contributors",  # members but nothing useful in the data so far
    "donations",
    "positions",
    "reports",
    "revives",
    "revivesfull",
    "news",
    "mainnews",
    "armorynews",
    "attacknews",
    "crimenews",
    "territorynews",
    "membershipnews",
    "fundsnews",
    "chain",
    "chainreport",
    "chains",
    "rankedwars",
    "wars",

]



# Applications ----------------------------------------------------------------



def main():
    conn = sqlite3.connect(
        DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) 
    cursor = conn.cursor()
    create_faction_upgrades(conn,cursor, force=False)
    conn.commit()
    update_faction_upgrades(conn,cursor, force=False)
    conn.commit()
    
    initDB(conn,cursor)  # creates the database structure if not already done
    conn.commit()
    updateDB(conn,cursor)  # updates the data using the API
    conn.commit()
    loadit(conn,cursor)
    conn.commit()
    conn.close()


def loadit(conn,cursor):
    global _api_request_count
    # # cursor.execute("""SELECT * FROM applications """)
    create_attacks(conn,cursor,force=False)
    conn.commit()
    update_attacks(conn,cursor,force=False)
    conn.commit()



# cursor.execute("""SELECT * FROM _rowCounts """)

# cursor.execute("""SELECT * FROM armory_items """)
# dumpResults(cursor)
# cursor.execute("""SELECT * FROM armory_loans """)
# dumpResults(cursor)
# # data=getFaction()
# # data = getSelection(cursor,selections=["basic","currency","hof", "stats"],cache_age_limit=3600, force=False)

# print(json.dumps(data, indent=2))

main()