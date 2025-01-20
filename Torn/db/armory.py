from Torn.api import cached_api_call
from enum import Enum
import sqlite3
import json

class TypeID(Enum):
    ARMOR = 1010
    BOOSTER = 1020
    MEDICAL = 1030
    TEMPORARY = 1040
    WEAPPONS = 1050
    DRUGS = 1060
    CACHE = 1070
    CESIUM = 1080

def create_armory(cursor,force=False):
    if force:
        cursor.executescript('''
        DROP TABLE IF EXISTS armory_types;
        DROP TABLE IF EXISTS armory_items;
        DROP TABLE IF EXISTS armory_loans;
        ''')
        
    cursor.executescript(f'''
    CREATE TABLE IF NOT EXISTS armory_types (
        armory_type_id INTEGER PRIMARY KEY,
        armory_type_name TEXT NOT NULL
    );
                        
    INSERT OR IGNORE INTO armory_types (armory_type_id, armory_type_name)
    VALUES  ({TypeID.ARMOR.value }, "armor"),
            ({TypeID.BOOSTER.value}, "booster"),
            ({TypeID.CACHE.value}, "cache"),
            ({TypeID.CESIUM.value}, "cesium");
                        
    CREATE TABLE IF NOT EXISTS armory_items (
        item_id INTEGER PRIMARY KEY,
        armory_type_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        item_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        available INTEGER,
        loaned INTEGER,
        loaned_to TEXT,
        FOREIGN KEY (armory_type_id) REFERENCES armory_types(armory_type_id)
    );

    DELETE FROM armory_items;

                        
    CREATE TABLE IF NOT EXISTS armory_loans (
        loan_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Add a primary key for this table
        item_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (item_id) REFERENCES armory_items(item_id)
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    DELETE FROM armory_loans;

    ''')
   

def insert_item(cursor, typeID,  item, item_type, available=None, loaned=None):
    try:
        cursor.execute('''
                INSERT INTO armory_items (armory_type_id,item_id,item_name, item_type, quantity, available, loaned)
                    VALUES (?,?, ?, ?, ?, ?, ?)''',
                (typeID, item["ID"], item["name"], item_type, item["quantity"], available, loaned)
        )
        if "loaned_to" in item:
            for user_id in item["loaned_to"].split(",") if isinstance(item["loaned_to"], str) else [str(item["loaned_to"])]:
                cursor.execute('''
                    INSERT INTO armory_loans (item_id, user_id)
                    VALUES (?, ?)''',
                    (item["ID"], user_id)
                )
    except sqlite3.IntegrityError:
        pass  # Ignore if  already exists


def update_armory(cursor, cache_age_limit=3600 * 12, force=False):
    data = cached_api_call("faction?selections=weapons,armor,medical,drugs,temporary,boosters,caches,cesium", force=force )
    # print(json.dumps(drugs, indent=2))

    for item in data["weapons"]:
        insert_item(cursor, TypeID.WEAPPONS.value, item, item['type'], item["available"], item["loaned"])
    for item in data["armor"]:
        insert_item(cursor, TypeID.ARMOR.value, item, 'Armor',item["available"], item["loaned"])
    for item in  data["boosters"]:
         insert_item(cursor, TypeID.BOOSTER.value, item , 'Booster')
    for item in data["medical"]:
         insert_item(cursor, TypeID.MEDICAL.value, item , 'Medical')
    for item in data["temporary"]:
        insert_item(cursor, TypeID.TEMPORARY.value, item, 'Temporary',item["available"], item["loaned"])
    for item in data["drugs"]:
         insert_item(cursor, TypeID.DRUGS.value, item , 'Drug')
    for item in data["caches"]:
         insert_item(cursor, TypeID.CACHE.value, item , 'CACHE')
    for item in data["cesium"]:
         insert_item(cursor, TypeID.CESIUM.value, item , 'Cesium')



