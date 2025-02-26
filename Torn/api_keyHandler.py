import os
import sqlite3
import sys
from Torn.credentials import load_credentials
from Torn.db._globals import DB_CONNECTPATH

api_key_preferenceName='TORN_API_KEY'
api_key = None  



def checkAPIKey(api_key=api_key):
    """
    Checks if the key looks right - i.e. not empty, is a string and is the right length at least
    """
    if isinstance(api_key, str) and len(api_key) > 0:
        return True
    else:
        return False

def get_api_key( api_key_settingName='TORN_API_KEY', force=False):
    """
    Retrieves the API key from the database, environment variables, 
    command-line arguments, or prompts the user for it.

    Args:
        env_var_name (str): The name of the environment variable to check.
        force (bool): If True, forces prompting for the API key even if it's 
                      found elsewhere.

    Returns:
        str: The API key.
    """
    global api_key 
    
    if api_key != None and checkAPIKey(api_key) and not force:
        return api_key
    
    #check credentiols file
    credentials = load_credentials()
    if credentials:
        primary_API_key = credentials.get("primary_API_key")
        if primary_API_key:
            api_key=primary_API_key
            return api_key
        
    # Check for API key in command-line arguments
    for arg in sys.argv:
        if arg.startswith("--api_key="):
            api_key = arg.split("=")[1]
            if checkAPIKey(api_key) and not force:
                print('API key retrieved from argument passed in on the command line (not stored in the DB)')
                return api_key

    # Check for API key in environment variable
    api_key = os.getenv(api_key_settingName)
    if checkAPIKey(api_key) and not force:
        print('API key retrieved from environment variable (not stored in the DB)')
        return api_key

    # Try to load API key from database
    result = getPreference(api_key_settingName)
    if result:
        api_key = result[0]
        if checkAPIKey(api_key) and not force:
            print('API key retrieved from preferenced stored in the DB. DO NOT SHARE YOUR DB')
            return api_key

    # If not found, prompt the user
    print(f"""
A Torn API key is needed. 
-------------------------          
Go to Torn.com -> Settings -> API Keys and create a Limited Access key. Copy it and paste it here.
This will be stored in the database in preferences with the key '{api_key_settingName}'. 
DO NOT SHARE your database with this key 
""")

    while not checkAPIKey(api_key):
        api_key = input("Please enter your API key: ").strip()
        if not checkAPIKey(api_key):
            print("API key cannot be empty. Please try again.")
    # Store API key in database
    # setPreference(api_key_settingName,api_key)
    # print('API key stored in the DB.')

    return api_key

def getPreference(settingName):
    # os.remove(DB_CONNECTPATH)
    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()
    try:
        sql = f'SELECT value FROM preferences WHERE key = "{settingName}"'
        cursor.execute(sql)
        result = cursor.fetchone()
        return result
    except:
        return None
    
def setPreference(settingName,value):
    if not settingName:
        return None
    conn = sqlite3.connect(DB_CONNECTPATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (settingName, value))
    conn.commit()
    conn.close()