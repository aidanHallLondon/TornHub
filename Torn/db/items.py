import json
import sqlite3
from datetime import datetime
from Torn.api import paginated_api_calls, cached_api_call, cached_api_paged_call, paginated_api_calls_auto


def create_item_listings(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS item_listings;")
        cursor.execute("DROP TABLE IF EXISTS item_listings_latest;")

    cursor.executescript("""  
              
        CREATE TABLE IF NOT EXISTS item_listings (
            id_pk INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            listing_id TEXT UNIQUE NOT NULL, -- Changed to TEXT and UNIQUE
            price INTEGER,
            amount INTEGER,
            item_uid TEXT, -- Changed to TEXT
            stat_damage REAL,
            stat_accuracy REAL,
            stat_armor REAL,
            bonus_json_list TEXT,
            rarity TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME, -- When the listing was first seen
            removed_at DATETIME, -- When the listing disappeared
            price_history TEXT -- CSV or JSON for price changes
        );
                       

        CREATE TABLE IF NOT EXISTS item_listings_latest (
            item_id INTEGER NOT NULL,
            listing_id TEXT UNIQUE NOT NULL,
            price INTEGER,
            amount INTEGER,
            item_uid TEXT,
            stat_damage REAL,
            stat_accuracy REAL,
            stat_armor REAL,
            bonus_json_list TEXT,
            rarity TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
""")


def create_items(conn, cursor, force=False):
    if force:
        cursor.execute("DROP TABLE IF EXISTS items;")

    cursor.executescript(
        """                     
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER UNIQUE,
            item_name TEXT, 
            item_type TEXT,
            average_price INTEGER,
            id_pk INTEGER PRIMARY KEY,  
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def get_item(conn, cursor, params=None, cache_age_limit=3600, force=False):
    return cached_api_call(
        conn, cursor, "market?selections=itemmarket", params=params, force=force
    )


def update_items(conn, cursor, force=False):
    cursor.execute("DELETE FROM item_listings_latest")
    cursor.execute('SELECT item_id FROM items WHERE item_type="Defensive" ORDER BY 1 ASC')
    data = cursor.fetchall()
    for (item_id,) in data:  # data looks like [(1,), (172,), (568,), (1203,),
        update_item(conn, cursor, item_id=item_id)
    update_item_listings(conn,cursor)   



def _itemmarket_callback(conn, cursor, new_data, callback_parameters):
    if (not new_data) or ("error" in new_data):
        return
    itemmarket = new_data.get("itemmarket", {})
    item = itemmarket.get("item",{"id":None})
    listings = itemmarket.get("listings", [])
    #
    item = itemmarket.get("item", None)
    if not item.get("id", None):
        return None
    if callback_parameters.get("item_updates",0)<1:
        callback_parameters["item_updates"]=1
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
                item.get("name",None),
                item.get("type",None),
                item.get("average_price",None),
            )
        )   
    if listings and len(listings)>0:
        callback_parameters["listings_updates"]+=1
        cursor.executemany(
            """INSERT OR REPLACE INTO item_listings_latest (
                item_id, 
                listing_id,
                amount, 
                price,
                item_uid, 
                stat_damage,
                stat_accuracy, 
                stat_armor,
                bonus_json_list, 
                rarity, 
                timestamp
            ) VALUES (?,?,?,?,?,?,?,?,?,?, strftime('%Y-%m-%d %H:%M:%S', 'now')); """,
            (
                (
                    item["id"],
                    listing["id"],  # listing id
                    listing.get("amount"),
                    listing.get("price"),
                    listing.get("itemDetails", {}).get("uid"),
                    listing.get("itemDetails", {}).get("stats", {}).get("damage"),
                    listing.get("itemDetails", {}).get("stats", {}).get("accuracy"), # Corrected typo
                    listing.get("itemDetails", {}).get("stats", {}).get("armor"),
                    json.dumps(listing.get("bonuses")) if listing.get("bonuses") else None,
                    listing.get("rarity"),
                )
                for listing in listings
            ),
        ) 
        return(len(listings))
    else:
        print("Empty listings")
        return None

def update_item(conn, cursor, item_id, cache_age_limit=3600 * 12, force=False):
    if not item_id:
        return
    
    callback = _itemmarket_callback
    callback_parameters={"item_updates":0,"listings_updates":0}
    # 
    listings2 = paginated_api_calls_auto(
        conn,
        cursor,
        endpoint="market",
        params={"selections":"itemmarket", "id":item_id},
        callback=callback,
        callback_parameters=callback_parameters,
        short_name="itemmarket",
    )

def update_item_listings(conn,cursor):
    cursor.execute("""  
    INSERT OR IGNORE INTO item_listings (
                   item_id, listing_id, price, amount, item_uid, stat_damage, stat_accuracy, stat_armor, 
                   bonus_json_list, rarity, timestamp, created_at)
    SELECT item_id, listing_id, price, amount, item_uid, stat_damage, stat_accuracy, stat_armor, 
                   bonus_json_list, rarity, timestamp, timestamp FROM item_listings_latest;
    """)
    cursor.execute("""                                                  
    UPDATE item_listings
    SET
        price = (SELECT price FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        amount = (SELECT amount FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        item_uid = (SELECT item_uid FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        stat_damage = (SELECT stat_damage FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        stat_accuracy = (SELECT stat_accuracy FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        stat_armor = (SELECT stat_armor FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        bonus_json_list = (SELECT bonus_json_list FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        rarity = (SELECT rarity FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        timestamp = (SELECT timestamp FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id),
        price_history = CASE
            WHEN item_listings.price!= (SELECT price FROM item_listings_latest WHERE item_listings_latest.listing_id = item_listings.listing_id) THEN
                CASE WHEN item_listings.price_history IS NULL THEN
                    json_array(json_object('price', item_listings.price, 'time', item_listings.timestamp))
                ELSE
                    json_insert(item_listings.price_history, '$[' || (json_array_length(item_listings.price_history)) || ']', json_object('price', item_listings.price, 'time', item_listings.timestamp))
                END
            ELSE item_listings.price_history
        END
    WHERE item_listings.listing_id IN (SELECT listing_id FROM item_listings_latest);
    """)
    cursor.execute(""" 
    UPDATE item_listings
        SET removed_at = datetime('now')
        WHERE listing_id NOT IN (SELECT listing_id FROM item_listings_latest) AND removed_at IS NULL;
    """)

    
