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
                amount, 
                price,
                item_uid, 
                stat_damage,
                stat_accuracy, 
                stat_armor,
                bonus_json_list, 
                rarity, 
                timestamp
            ) VALUES (?,?,?,?,?,?,?,?,?, strftime('%Y-%m-%d %H:%M:%S', 'now')); """,
            (
                (
                    item["id"],
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




import sqlite3

def update_unique_item_listings(conn, cursor):
    # --- Step 1: Insert New Unique Listings ---
    cursor.execute("""
        INSERT INTO item_listings (
            item_id, price, amount, item_uid, stat_damage, stat_accuracy, stat_armor,
            bonus_json_list, rarity, timestamp, created_at, removed_at
        )
        SELECT
            item_id, price, amount, item_uid, stat_damage, stat_accuracy, stat_armor,
            bonus_json_list, rarity, timestamp, strftime('%Y-%m-%d %H:%M:%S', 'now'), NULL
        FROM item_listings_latest AS latest
        WHERE latest.item_uid IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM item_listings AS existing
            WHERE existing.item_uid = latest.item_uid
              AND existing.removed_at IS NULL
        );
    """)

    # --- Step 2: Update Existing Unique Listings and Price History ---
    cursor.execute("""
        UPDATE item_listings
        SET
            price = latest.price,
            amount = latest.amount,
            stat_damage = latest.stat_damage,
            stat_accuracy = latest.stat_accuracy,
            stat_armor = latest.stat_armor,
            bonus_json_list = latest.bonus_json_list,
            rarity = latest.rarity,
            timestamp = strftime('%Y-%m-%d %H:%M:%S', 'now'),
            price_history = CASE
                WHEN item_listings.price != latest.price THEN
                    CASE
                        WHEN item_listings.price_history IS NULL THEN
                            json_array(json_object('price', item_listings.price, 'time', item_listings.created_at))
                        ELSE
                            json_insert(item_listings.price_history, '$[#]', json_object('price', item_listings.price, 'time', item_listings.created_at))
                    END
                ELSE item_listings.price_history
            END
        FROM item_listings_latest AS latest
        WHERE item_listings.item_uid = latest.item_uid
          AND item_listings.removed_at IS NULL;
    """)

    # --- Step 3: Mark Removed Unique Listings ---
    cursor.execute("""
        UPDATE item_listings
        SET removed_at = strftime('%Y-%m-%d %H:%M:%S', 'now')
        WHERE item_uid NOT IN (
            SELECT item_uid FROM item_listings_latest WHERE item_uid IS NOT NULL
        )
          AND removed_at IS NULL;
    """)


def update_batch_item_listings(conn, cursor):
    # --- Step 1: Insert New Batch Listings (or Ignore if Existing) ---
    cursor.execute("""
        INSERT OR IGNORE INTO item_listings (
            item_id, price, amount, item_uid, stat_damage, stat_accuracy, stat_armor,
            bonus_json_list, rarity, timestamp, created_at, removed_at
        )
        SELECT
            item_id, price, amount, NULL, stat_damage, stat_accuracy, stat_armor,
            bonus_json_list, rarity, strftime('%Y-%m-%d %H:%M:%S', 'now'), strftime('%Y-%m-%d %H:%M:%S', 'now'), NULL
        FROM item_listings_latest
        WHERE item_uid IS NULL;
    """)

    # --- Step 2: Update Existing Batch Listings (Amount Only) ---
    cursor.execute("""
        UPDATE item_listings
        SET
            amount = latest.amount,
            timestamp = strftime('%Y-%m-%d %H:%M:%S', 'now')
        FROM item_listings_latest AS latest
        WHERE item_listings.item_id = latest.item_id
          AND item_listings.price = latest.price
          AND item_listings.item_uid IS NULL
          AND item_listings.removed_at IS NULL;
    """)

    # --- Step 3: Mark Removed Batch Listings ---
    cursor.execute("""
        UPDATE item_listings
        SET removed_at = strftime('%Y-%m-%d %H:%M:%S', 'now')
        WHERE item_uid IS NULL
          AND removed_at IS NULL
          AND (item_id, price) NOT IN (
              SELECT item_id, price
              FROM item_listings_latest
              WHERE item_uid IS NULL
          );
    """)


def update_item_listings(conn, cursor):
    update_unique_item_listings(conn, cursor)
    update_batch_item_listings(conn, cursor)
    conn.commit()