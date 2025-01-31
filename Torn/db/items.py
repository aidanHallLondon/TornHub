import sqlite3
from datetime import datetime
from Torn.api import paginated_api_calls, cached_api_call, cached_api_paged_call


def create_items(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS items;")
        cursor.execute("DROP TABLE IF EXISTS item_listings_history;")
 

    cursor.executescript("""
                                                  
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY,  
            item_name TEXT, 
            item_type TEXT,
            average_price INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
    
    
#     {
#   "itemmarket": {
#     "item": {
#       "id": 1362,
#       "name": "Net",
#       "type": "Tool",
#       "average_price": 4572554
#     },
#     "listings": [
#       {
#         "id": 9830442,
#         "price": 4499000,
#         "amount": 2
#       },
#     ]
#   }

# }


#  https://api.torn.com/v2/market?selections=itemmarket&id=1362%2C668

def getItem(conn,cursor,params=None, cache_age_limit=3600, force=False):
    return cached_api_call(conn,cursor,"market?selections=itemmarket",params=params, force=force )

def update_items(conn,cursor, force=False):
    cursor.execute("""SELECT item_id FROM items WHERE item_name IS NULL ORDER BY 1 ASC""")
    data = cursor.fetchall()
    for item_id, in data:  # data looks like [(1,), (172,), (568,), (1203,), 
        update_item(conn,cursor, item_id=item_id)

def update_item(conn,cursor, item_id, cache_age_limit=3600 * 12, force=False):
    data = getItem(conn,cursor,
        params={"id":item_id},
        cache_age_limit=cache_age_limit,
        force=force,
    )
    # print(json.dumps(data, indent=2))
    itemmarket = data["itemmarket"]

    if itemmarket:
        item = itemmarket["item"]
        listings = itemmarket["listings"]
        # 
        cursor.execute(
            """INSERT OR REPLACE INTO items (
                item_id ,  
                item_name, 
                item_type,
                average_price,
                timestamp 
            ) VALUES (?,?,?,?, strftime('%Y-%m-%d %H:%M:%S', 'now')); """,
            (
                item["id"],
                item["name"],
                item["type"],
                item["average_price"],
            )
        )

