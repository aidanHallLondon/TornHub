

import sqlite3
import time
from Torn.db._globals import DB_CONNECTPATH
from Torn.manageDB import get_last_updateDB_delta, updateDB
import generate_reporting

BACKGROUND_UPDATE_DUTY_CYCLE_SECONDS =5
BACKGROUND_UPDATE_UPDATEDB_DUTY_CYCLE_SECONDS = 30



# def background_update():
#     print(f"background_update running: press ENTER to stop")
#     print(get_last_updateDB_delta())
#     last_update = get_last_updateDB_delta()
#     if last_update is None or last_update>BACKGROUND_UPDATE_UPDATEDB_DUTY_CYCLE_SECONDS:
#         conn = sqlite3.connect(DB_CONNECTPATH, detect_types=sqlite3.PARSE_DECLTYPES)
#         cursor = conn.cursor()
#         updateDB(conn,cursor)
#         generate_reporting(conn,cursor)

#     time.sleep(BACKGROUND_UPDATE_DUTY_CYCLE_SECONDS)
