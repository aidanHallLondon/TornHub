# torn_api.py
import requests
import time
import os
import json
import sys
from Torn.manageDB import DB_PATH,getPreference,setPreference

BASE_URL = "https://api.torn.com/v2"
api_key_preferenceName='TORN_API_KEY'
api_key = None # call getHeaders after Db initialised
headers = None # call getHeaders after Db initialised
CACHE_PATH = "data/cache"  # Directory to store cached files
LAST_RECORD_FILE = "last_record.json"

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

def checkAPIKey(api_key=api_key):
    """
    Checks if the key looks right - i.e. not empty, is a string and is the right length at least
    """
    if isinstance(api_key, str) and len(api_key) > 0:
        return True
    else:
        return False

def _get_api_key(db_path=DB_PATH, api_key_settingName='TORN_API_KEY', force=False):
    """
    Retrieves the API key from the database, environment variables, 
    command-line arguments, or prompts the user for it.

    Args:
        db_path (str): Path to the SQLite database file.
        env_var_name (str): The name of the environment variable to check.
        force (bool): If True, forces prompting for the API key even if it's 
                      found elsewhere.

    Returns:
        str: The API key.
    """

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
This will be stored in the database '{db_path}' in preferences with the key '{api_key_settingName}'. 
DO NOT SHARE your database with this key 
""")

    while not checkAPIKey(api_key):
        api_key = input("Please enter your API key: ").strip()
        if not checkAPIKey(api_key):
            print("API key cannot be empty. Please try again.")
    # Store API key in database
    setPreference(api_key_settingName,api_key)
    print('API key stored in the DB.')

    return api_key


def _getHeaders():
    api_key = _get_api_key() # Torn_limited_API_KEY # Torn_public_API_KEY
    headers = {"Authorization": f"ApiKey {api_key}"}
    return headers

def getFactionMembers(params={"striptags": "true"}, force=False):
    return cached_api_call("faction/members", params, force)["members"]

def getCrimes(params=None, force=False):
    return paginated_api_call("faction/crimes",  params, force)["crimes"]

def api_call(url, headers=headers, params=None):
    """
    Makes a generic API call.

    Args:
        url (str): The full API URL.
        headers (dict, optional): Headers for the request. Defaults to None.
        params (dict, optional): Parameters for the request. Defaults to None.

    Returns:
        dict: The JSON response from the API, or None if there was an error.
    """
    if headers==None:
        headers=_getHeaders()
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        #print("api call made")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        return None
    except ValueError as json_err:
        print(f"Error decoding JSON response: {json_err}")
        return None
    

def cached_api_call(endpoint, params=None, maxAge=60, force=False):
    """
    Makes an API call with caching.

    Args:
        endpoint (str): The API endpoint (e.g., "faction/basic").
        params (dict, optional): Parameters for the API call. Defaults to None.
        maxAge (int, optional): Maximum age of cached data in seconds. Defaults to 60.
        force (bool, optional): Force a fresh API call, ignoring the cache. Defaults to False.

    Returns:
        dict: The JSON response from the API, or None if there was an error.
    """
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    cache_filename = f"{endpoint.replace('/', '_')}"
    if params:
        param_string = "_".join(
            f"{k}_{v}" for k, v in sorted(params.items()) if k not in ['selections', 'from', 'to']
        )
        cache_filename += f"_{param_string}"
    cache_filename += ".json"
    cache_filepath = os.path.join(CACHE_PATH, cache_filename)

    if not force:
        try:
            if os.path.exists(cache_filepath):
                file_age = time.time() - os.path.getmtime(cache_filepath)
                if file_age < maxAge:
                    with open(cache_filepath, "r") as f:
                        #print(f"Using cached data for {endpoint} (age: {int(file_age)} seconds)")
                        return json.load(f)
        except Exception as e:
            print(f"Error reading cache file: {e}")

    # Make the API call using generic_api_call
    url = f"{BASE_URL}/{endpoint}"
    data = api_call(url, headers=headers, params=params)

    # Cache the API response
    if data:
        try:
            with open(cache_filepath, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Data fetched and cached for {endpoint}")
        except Exception as e:
            print(f"Error writing to cache file: {e}")

    return data


def _get_newest_timestamp_from_response(data, current_newest_timestamp):
    """
    Finds the newest timestamp in a dictionary of API response data.

    Args:
        data (dict): The API response data (typically a dictionary).
        current_newest_timestamp: The current newest known timestamp.

    Returns:
        int: The newest timestamp found in the data, or the current_newest_timestamp if no newer 
             timestamp is found.
    """
    newest_timestamp = current_newest_timestamp

    if data:
        for key, entry in data.items():
            if isinstance(entry, dict) and 'timestamp' in entry:
                timestamp = entry['timestamp']
                if timestamp > newest_timestamp:
                    newest_timestamp = timestamp

    return newest_timestamp



# --- Paginated API Call Function (modified) ---
def paginated_api_call(endpoint, params=None, maxAge=60, force=False):
    """
    Makes a paginated API call, fetching only new records and using caching.
    Stores last record timestamp in the cache file itself.

    Args:
        endpoint (str): The API endpoint (e.g., "faction/crimes").
        params (dict, optional): Additional parameters for the API call. Defaults to None.
        maxAge (int, optional): Maximum age of cached data in seconds. Defaults to 60.
        force (bool, optional): Force a fresh API call, ignoring cache and record tracking. Defaults to False.

    Returns:
        dict: The JSON response from the API, or None if there was an error.
    """

    cache_filename = f"{endpoint.replace('/', '_')}"
    if params:
        param_string = "_".join(
            f"{k}_{v}" for k, v in sorted(params.items()) if k not in ['selections', 'from', 'to']
        )
        cache_filename += f"_{param_string}"
    cache_filename += ".json"
    cache_filepath = os.path.join(CACHE_PATH, cache_filename)

    # 1. Load Cached Data (if any) and Get Last Record Timestamp
    cached_data = None
    last_record_timestamp = 0
    
    if os.path.exists(cache_filepath):
        try:
            with open(cache_filepath, "r") as f:
                cached_data = json.load(f)
                # Get last record timestamp from cached data
                last_record_timestamp = cached_data.get("last_record_timestamp", 0)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading cache file: {e}")
            cached_data = None

    # 2. Prepare the request
    if params is None:
        params = {}

    if last_record_timestamp > 0 and not force:
        params["from"] = last_record_timestamp + 1
        params["sort"] = "ASC"

    # 3. Make API Call (using generic_api_call, not cached_api_call)
    url = f"{BASE_URL}/{endpoint}"
    new_data = api_call(url, headers=headers, params=params)

    # 4. Combine Cached and New Data (if any) and Update Last Record Timestamp
    if new_data is not None:
        if cached_data:
            # Merge new data with cached data
            if isinstance(new_data, dict) and isinstance(cached_data, dict):
                for key, value in new_data.items():
                    if key not in ['last_record_timestamp', 'data_fetched_at']:
                        if key not in cached_data:
                            cached_data[key] = value
                        elif isinstance(cached_data[key], dict) and isinstance(value, dict):
                            cached_data[key].update(value)
                        elif isinstance(cached_data[key], list) and isinstance(value, list):
                            cached_data[key].extend(value)
                        else:
                            print(f"Warning: Incompatible data types for key '{key}' in cached and new data. Skipping merge for this key.")
            elif isinstance(new_data, list) and isinstance(cached_data, list):
                cached_data.extend(new_data)
            else:
                print("Error: Incompatible data types between cached data and new data. Cannot merge.")
                return None
        else:
            cached_data = new_data
        # Update last record timestamp (if new records were fetched)
        current_newest_timestamp = last_record_timestamp
        newest_timestamp = _get_newest_timestamp_from_response(new_data, current_newest_timestamp)
        if newest_timestamp > last_record_timestamp:
            last_record_timestamp = newest_timestamp

    # Add metadata to cached data
    if cached_data is not None:
        cached_data["last_record_timestamp"] = last_record_timestamp
        cached_data["data_fetched_at"] = int(time.time())

        # 5. Save Combined Data to Cache
        try:
            with open(cache_filepath, "w") as f:
                json.dump(cached_data, f, indent=4)
            print(f"Data fetched and cached for {endpoint}, including last record timestamp")
        except Exception as e:
            print(f"Error writing to cache file: {e}")

    # 6. Return Combined Data
    return cached_data