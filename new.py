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

selectionsDone = [
    "crimes", "crimeexp",
    "members",
    "basic","currency","hof","stats","timestamp","lookup",
    "upgrades",
    "applications", 
    "armor", "boosters","medical","temporary","weapons", "drugs","caches","cesium",
    "attacks", "attacksfull", "revives", "revivesfull",
]
selections = [

    "chain",
    "chainreport",
    "chains",

    "territory",
    "contributors",  # members but nothing useful in the data so far
    "donations",
    "positions",
    "reports",

    "rankedwars",
    "wars",

    "news",
    "mainnews",
    "armorynews",
    "attacknews",
    "crimenews",
    "territorynews",
    "membershipnews",
    "fundsnews",

]



# Applications ----------------------------------------------------------------



def main():
    conn = sqlite3.connect(
        DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES
    ) 
    cursor = conn.cursor()

    
    initDB(conn,cursor)  # creates the database structure if not already done
    conn.commit()
    # data=cursor.execute("""DELETE  FROM revives """)
  
    updateDB(conn,cursor)  # updates the data using the API
    conn.commit()
    loadit(conn,cursor)
    conn.commit()
    conn.close()


def loadit(conn,cursor):
    global _api_request_count
    # update_revives(conn, cursor, force=True )

    # # cursor.execute("""SELECT * FROM applications """)
    # create_revives(conn,cursor, force=True)
    # conn.commit()
    # update_revives(conn,cursor, force=False)
    # conn.commit()
    # data=cursor.execute("""SELECT count(*) FROM revives """)
    # dumpResults(conn,cursor)
    # endpoint = "faction?selections=revives"
    # params={}
    # running = True
    # count=54
    # fromTimestamp=date_to_unix('2014-01-01 00:00:00') # random early date
    # while running and count>0:
    #     count-=1
    #     params['from']=fromTimestamp
    #     new_data = _api_raw_call(conn, cursor, url=_getApiURL(endpoint,params=params), params=params)["revives"]
    #     if isinstance(new_data, dict):
    #         new_data = [{"revive_id": key, **value} for key, value in new_data.items()] 
    #     for revive_row in new_data:
    #         revive_row["timestamp_datetime"]= datetime.fromtimestamp(revive_row["timestamp"]).isoformat() 
    #     fromTimestamp=new_data[-1]["timestamp"]+0.1      
    #     print("XX",json.dumps(new_data[0]),flush=True)
    #     # print("XX",json.dumps([revive_row["timestamp"] for revive_row in new_data]))
    #     # print(toTS, new_data[0]["timestamp"],new_data[-1]["timestamp"],new_data[0]["timestamp"]-new_data[-1]["timestamp"], new_data[0]["timestamp_datetime"],new_data[-1]["timestamp_datetime"],)
    #     print(new_data[0]["revive_id"],new_data[-1]["revive_id"], int(new_data[-1]["revive_id"])-int(new_data[0]["revive_id"]))
    #     print('')
        # print(json.dumps(new_data,indent=2))

    # key='j5qsOlKvE0YWHTIx'
    # start_time_str = "2014-11-09 18:00:00" #Enter the start time (YYYY-MM-DD HH:MM:SS)#
    # end_time_str = "2025-01-24 09:35:00" #Enter the end time (YYYY-MM-DD HH:MM:SS) (Optional)
    

 
        # dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        # return int(time.mktime(dt.timetuple()))
    # start_time_unix=date_to_unix(start_time_str)
    # end_time_unix=date_to_unix(end_time_str) 
    # while True:

    #     url_revives = f'https://api.torn.com/faction/?key={key}&comment=FactionCal&selections=revivesfull&from={start_time_unix}'
    #     print(url_revives)
    #     response_revives = requests.get(url_revives)
    #     revives_data = response_revives.json()
    #     if "error" in revives_data:
    #         exit(revives_data["error"])

    #     # Check if no revives are returned
    #     if not revives_data.get("revives"):
    #         print("STOP")
    #         break # Break the loop
    
    #     no_revives_count = 0
    
    #   # Get the newest revive's timestamp
    #     newest_revive_timestamp = max(revive["timestamp"] for revive in revives_data["revives"].values())
    #     start_time_unix = newest_revive_timestamp + 1
    #     print(len(revives_data.get("revives")))
    # print("end")



# cursor.execute("""SELECT * FROM _rowCounts """)

# cursor.execute("""SELECT * FROM armory_items """)
# dumpResults(cursor)
# cursor.execute("""SELECT * FROM armory_loans """)
# dumpResults(cursor)
# # data=getFaction()
# # data = getSelection(cursor,selections=["basic","currency","hof", "stats"],cache_age_limit=3600, force=False)

# print(json.dumps(data, indent=2))

main()