import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import  initDB, updateDB, dumpResults
# from Torn.db.faction import create_faction, update_faction
from Torn.api import cached_api_paged_call

selectionsDone = [
    "crimes",
    "members",
    "basic","currency","hof","stats","timestamp","lookup",
    "applications", 
]
selections = [
    "upgrades",
    "territory",
    "contributors",  # members but nothing useful in the data so far
    "crimeexp",
    "donations",
    "positions",
    "reports",
    "revives",
    "revivesfull",
    "armor",
    "boosters",
    "medical",
    "temporary",
    "weapons" "drugs",
    "caches",
    "cesium",
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
    "attacks",
    "attacksfull",
    "rankedwars",
    "wars",

]



# Applications ----------------------------------------------------------------


initDB()  # creates the database if not already done
updateDB()  # updates the data using the API


conn = sqlite3.connect(
    DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
)  # Add detect_types
cursor = conn.cursor()


# # cursor.execute("""SELECT * FROM applications """)

cursor.execute("""SELECT * FROM _rowCounts """)
dumpResults(cursor)
# # data=getFaction()
# # data = getSelection(cursor,selections=["basic","currency","hof", "stats"],cache_age_limit=3600, force=False)

# #print(json.dumps(data, indent=2))

conn.commit()
conn.close()
