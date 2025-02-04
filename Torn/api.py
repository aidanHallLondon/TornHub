from datetime import datetime
import requests
import time
import os
import json
import re
import sqlite3
from Torn.db._globals import DB_CONNECTPATH
from Torn.api_keyHandler import get_api_key
from urllib.parse import urlencode, urlparse, parse_qsl

VERBOSE = False
BASE_URL = "https://api.torn.com/v2"
headers = None  # {"Authorization": f"ApiKey {api_key}"} # call getHeaders after Db initialised
API_SEMAPHORE_CALL_RATE = {
    "LIMIT": 60,
    "WINDOW": 60,
    "MINIMUM_PAUSE": 2,
    "THROTTLE_LIMIT": 30,
    "THROTTLE_TIME": 1,
}  # actual limit is 100 every 60s across all api_keys
CACHE_PATH = "data/cache"  # Directory to store cached files
JSON_INDENT = 2
TEXT = {"API_CALL":'•', "CACHE": "📄", "WAIT": "🛑", "PAUSE": "🐌"}


if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

def api_semaphore_check(conn, cursor):
    """
    Pause if we have made too many calls in the last period (minute)
    relies on API_SEMAPHORE_CALL_RATE for API_SEMAPHORE_CALL_RATE["LIMIT"] and API_SEMAPHORE_CALL_RATE["WINDOW"]
    """
    try:
        while True:
            semaphore_cutoff_time = time.time() - API_SEMAPHORE_CALL_RATE["WINDOW"]
            cursor.execute(
                "DELETE FROM api_semaphores WHERE timestamp < ?",
                (semaphore_cutoff_time,),
            )
            conn.commit()  # Commit after deleting
            cursor.execute(
                "SELECT COUNT(*) AS call_count, MIN(timestamp) AS oldestTimeStamp FROM api_semaphores"
            )
            semaphore_count, oldest_timestamp = cursor.fetchone()

            if semaphore_count >= API_SEMAPHORE_CALL_RATE["LIMIT"]:
                time_to_pause = max(
                    (
                        oldest_timestamp - semaphore_cutoff_time
                        if oldest_timestamp is not None
                        else 0
                    ),
                    API_SEMAPHORE_CALL_RATE["MINIMUM_PAUSE"],
                )
                if VERBOSE:
                    print(
                        f"* Semaphore - {TEXT["WAIT"]} WAITING {round(time_to_pause*10)/10} seconds"
                    )
                else:
                    print(TEXT["WAIT"], end="", flush=True)
                time.sleep(time_to_pause)
            else:
                if semaphore_count >= API_SEMAPHORE_CALL_RATE["THROTTLE_LIMIT"]:
                    if VERBOSE:
                        print(
                            f"* Semaphore - {TEXT["PAUSE"]} Throttling {API_SEMAPHORE_CALL_RATE["THROTTLE_TIME"]} second"
                        )
                    else:
                        print(TEXT["PAUSE"], end="", flush=True)
                    time.sleep(API_SEMAPHORE_CALL_RATE["THROTTLE_TIME"])
                cursor.execute(
                    "INSERT INTO api_semaphores (timestamp) VALUES (?)", (time.time(),)
                )
                conn.commit()  # Commit after inserting
                break  # Exit the loop when a semaphore is acquired
    finally:  # Ensure connection is commited even if errors occur
        conn.commit()


# Torn API call wrappers

# def getAttacks(params=None, cache_age_limit=3600, force=False):
#     attacks = cached_api_paged_call(endpoint="faction/attacks",  params=params, dataKey="attacks", cache_age_limit=cache_age_limit, force=force)
#     return attacks

# def getAttacksfull(params=None, cache_age_limit=3600, force=False):
#     attacksfull = cached_api_paged_call(endpoint="faction/attacksfull",  params=params, dataKey="attacksfull", cache_age_limit=cache_age_limit, force=force)
#     return attacksfull

# def getBasic(params=None, cache_age_limit=3600, force=False):
#     basic = cached_api_paged_call(endpoint="faction/basic",  params=params, dataKey="basic", cache_age_limit=cache_age_limit, force=force)
#     return basic

# def getChain(params=None, cache_age_limit=3600, force=False):
#     chain = cached_api_paged_call(endpoint="faction/chain",  params=params, dataKey="chain", cache_age_limit=cache_age_limit, force=force)
#     return chain

# def getChainreport(params=None, cache_age_limit=3600, force=False):
#     chainreport = cached_api_paged_call(endpoint="faction/chainreport",  params=params, dataKey="chainreport", cache_age_limit=cache_age_limit, force=force)
#     return chainreport

# def getChains(params=None, cache_age_limit=3600, force=False):
#     chains = cached_api_paged_call(endpoint="faction/chains",  params=params, dataKey="chains", cache_age_limit=cache_age_limit, force=force)
#     return chains

# def getCrimes(params=None, cache_age_limit=3600, force=False):
#     crimes = cached_api_paged_call(endpoint="faction/crimes",  params=params, dataKey="crimes", cache_age_limit=cache_age_limit, force=force)
#     return crimes

# def getHof(params=None, cache_age_limit=3600, force=False):
#     hof = cached_api_paged_call(endpoint="faction/hof",  params=params, dataKey="hof", cache_age_limit=cache_age_limit, force=force)
#     return hof

# def getLookup(params=None, cache_age_limit=3600, force=False):
#     lookup = cached_api_paged_call(endpoint="faction/lookup",  params=params, dataKey="lookup", cache_age_limit=cache_age_limit, force=force)
#     return lookup

# def getMembers(params=None, cache_age_limit=3600, force=False):
#     members = cached_api_paged_call(endpoint="faction/members",  params=params, dataKey="members", cache_age_limit=cache_age_limit, force=force)
#     return members

# def getNews(params=None, cache_age_limit=3600, force=False):
#     news = cached_api_paged_call(endpoint="faction/news",  params=params, dataKey="news", cache_age_limit=cache_age_limit, force=force)
#     return news

# def getTerritory(params=None, cache_age_limit=3600, force=False):
#     territory = cached_api_paged_call(endpoint="faction/territory",  params=params, dataKey="territory", cache_age_limit=cache_age_limit, force=force)
#     return territory

# def getTimestamp(params=None, cache_age_limit=3600, force=False):
#     timestamp = cached_api_paged_call(endpoint="faction/timestamp",  params=params, dataKey="timestamp", cache_age_limit=cache_age_limit, force=force)
#     return timestamp

# def getWars(params=None, cache_age_limit=3600, force=False):
#     wars = cached_api_paged_call(endpoint="faction/wars",  params=params, dataKey="wars", cache_age_limit=cache_age_limit, force=force)
#     return wars

# def getArmor(params=None, cache_age_limit=3600, force=False):
#     armor = cached_api_paged_call(endpoint="faction/armor",  params=params, dataKey="armor", cache_age_limit=cache_age_limit, force=force)
#     return armor

# def getBoosters(params=None, cache_age_limit=3600, force=False):
#     boosters = cached_api_paged_call(endpoint="faction/boosters",  params=params, dataKey="boosters", cache_age_limit=cache_age_limit, force=force)
#     return boosters

# def getCaches(params=None, cache_age_limit=3600, force=False):
#     caches = cached_api_paged_call(endpoint="faction/caches",  params=params, dataKey="caches", cache_age_limit=cache_age_limit, force=force)
#     return caches

# def getCesium(params=None, cache_age_limit=3600, force=False):
#     cesium = cached_api_paged_call(endpoint="faction/cesium",  params=params, dataKey="cesium", cache_age_limit=cache_age_limit, force=force)
#     return cesium

# def getContributors(params=None, cache_age_limit=3600, force=False):
#     contributors = cached_api_paged_call(endpoint="faction/contributors",  params=params, dataKey="contributors", cache_age_limit=cache_age_limit, force=force)
#     return contributors

# def getCrimeexp(params=None, cache_age_limit=3600, force=False):
#     crimeexp = cached_api_paged_call(endpoint="faction/crimeexp",  params=params, dataKey="crimeexp", cache_age_limit=cache_age_limit, force=force)
#     return crimeexp

# def getCurrency(params=None, cache_age_limit=3600, force=False):
#     currency = cached_api_paged_call(endpoint="faction/currency",  params=params, dataKey="currency", cache_age_limit=cache_age_limit, force=force)
#     return currency

# def getDonations(params=None, cache_age_limit=3600, force=False):
#     donations = cached_api_paged_call(endpoint="faction/donations",  params=params, dataKey="donations", cache_age_limit=cache_age_limit, force=force)
#     return donations

# def getDrugs(params=None, cache_age_limit=3600, force=False):
#     drugs = cached_api_paged_call(endpoint="faction/drugs",  params=params, dataKey="drugs", cache_age_limit=cache_age_limit, force=force)
#     return drugs

# def getMedical(params=None, cache_age_limit=3600, force=False):
#     medical = cached_api_paged_call(endpoint="faction/medical",  params=params, dataKey="medical", cache_age_limit=cache_age_limit, force=force)
#     return medical

# def getPositions(params=None, cache_age_limit=3600, force=False):
#     positions = cached_api_paged_call(endpoint="faction/positions",  params=params, dataKey="positions", cache_age_limit=cache_age_limit, force=force)
#     return positions

# def getRankedwars(params=None, cache_age_limit=3600, force=False):
#     rankedwars = cached_api_paged_call(endpoint="faction/rankedwars",  params=params, dataKey="rankedwars", cache_age_limit=cache_age_limit, force=force)
#     return rankedwars

# def getReports(params=None, cache_age_limit=3600, force=False):
#     reports = cached_api_paged_call(endpoint="faction/reports",  params=params, dataKey="reports", cache_age_limit=cache_age_limit, force=force)
#     return reports

# def getRevives(params=None, cache_age_limit=3600, force=False):
#     revives = cached_api_paged_call(endpoint="faction/revives",  params=params, dataKey="revives", cache_age_limit=cache_age_limit, force=force)
#     return revives

# def getRevivesfull(params=None, cache_age_limit=3600, force=False):
#     revivesfull = cached_api_paged_call(endpoint="faction/revivesfull",  params=params, dataKey="revivesfull", cache_age_limit=cache_age_limit, force=force)
#     return revivesfull

# def getStats(params=None, cache_age_limit=3600, force=False):
#     stats = cached_api_paged_call(endpoint="faction/stats",  params=params, dataKey="stats", cache_age_limit=cache_age_limit, force=force)
#     return stats

# def getTemporary(params=None, cache_age_limit=3600, force=False):
#     temporary = cached_api_paged_call(endpoint="faction/temporary",  params=params, dataKey="temporary", cache_age_limit=cache_age_limit, force=force)
#     return temporary

# def getUpgrades(params=None, cache_age_limit=3600, force=False):
#     upgrades = cached_api_paged_call(endpoint="faction/upgrades",  params=params, dataKey="upgrades", cache_age_limit=cache_age_limit, force=force)
#     return upgrades

# def getWeapons(params=None, cache_age_limit=3600, force=False):
#     weapons = cached_api_paged_call(endpoint="faction/weapons",  params=params, dataKey="weapons", cache_age_limit=cache_age_limit, force=force)
#     return weapons


# Interface functions

# def _getCacheFilePath(endpoint, params=None):
#     '''
#     Returns the file path for cached data for an endpoint and params.
#     '''
#     global CACHE_PATH
#     if params is None:
#         return f"{CACHE_PATH}/{endpoint}.json"
#     else:
#         return f"{CACHE_PATH}/{endpoint}_{params}.json"


def _getCacheFilePath(endpoint, params=None):
    """
    Returns the file path for cached data for an endpoint and params.
    """
    global CACHE_PATH
    endpoint = endpoint.replace("?", "/").replace("=", "/")
    if params is None:
        return f"{CACHE_PATH}/{endpoint}.json"
    else:  # Flatten the params dictionary into a string Replace non-alphanumeric characters with underscores
        params_str = re.sub(r"[^a-zA-Z0-9]+", "_", json.dumps(params, sort_keys=True))
        return f"{CACHE_PATH}/{endpoint}{params_str}.json"


def _saveData(endpoint, params=None, data=None):
    """
    Saves API results data to a file in the cache.
    """
    filePath = _getCacheFilePath(endpoint, params)
    path = os.path.dirname(filePath)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(filePath, "w") as file:
        json.dump(data, file, indent=JSON_INDENT)


def _getApiURL(endpoint,params = None):
    global BASE_URL
    url =f"{BASE_URL}/{endpoint}"
    if params:
        url = add_params_to_url(url, params)  # Add parameters safely
    return url

def add_params_to_url(url, params):
    """Safely adds parameters to a URL, handling existing query strings."""
    url_parts = urlparse(url)
    query = dict(parse_qsl(url_parts.query))
    query.update({k: v for k, v in params.items() if v } )
    return url_parts._replace(query=urlencode(query)).geturl()


def _loadCachedData(endpoint, params=None, cache_age_limit=3600):
    """
    Loads cached API data from a file if it exists and is not too old.
    Otherwise returns the default empty data.

    Args:
        endpoint (str): The API endpoint.
        params (dict, optional): Parameters for the API call. Defaults to None.
        cache_age_limit (int, optional): Maximum age of the cached file in seconds. Defaults to 3600.

    Returns:
        list or dict: The cached data if found and valid, otherwise the default empty data.
    """
    filePath = _getCacheFilePath(endpoint, params=params)
    if os.path.exists(filePath):
        if time.time() - os.path.getmtime(filePath) < cache_age_limit:
            try:
                with open(filePath, "r") as file:
                    data = json.load(file)
                    return data
            except json.JSONDecodeError:
                print(f"Error reading cache file {filePath}")
                pass
    return None


# API CALLS
# API CALLS

import requests


def _api_raw_call(conn, cursor, url, params=None):
    """
    Makes a generic API call.

    Args:
        url (str): The full API URL.
        headers (dict, optional): Headers for the request. Defaults to None.
        params (dict, optional): Parameters for the request. Defaults to None.

    Returns:
        dict: The JSON response from the API.

    Raises:
        APIError: If the API returns an error.
        requests.exceptions.HTTPError: If an HTTP error occurs.
        requests.exceptions.RequestException: If a request error occurs.
        ValueError: If there's an error decoding the JSON response.
    """
    global headers

    api_semaphore_check(conn, cursor)

    if headers is None:
        api_key = get_api_key()  # Torn_limited_API_KEY # Torn_public_API_KEY
        headers = {"Authorization": f"ApiKey {api_key}"}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json()
        if "error" in data:
            print(f'\n\nError data={data}\n      url={url}')
            if data["error"].get("code",0)==6:
                return data # !!!
            else:
                raise APIError(data["error"])  # Raise a custom APIError
        # 
        print(TEXT["API_CALL"],end='',flush=True)
        return data

    except requests.exceptions.HTTPError as http_err:
        print(f"\nHTTP error occurred: {http_err}")
        raise  # Re-raise the HTTPError
    except requests.exceptions.RequestException as req_err:
        print(f"\nRequest error occurred: {req_err}")
        raise  # Re-raise the RequestException
    except ValueError as json_err:
        print(f"\nError decoding JSON response: {json_err} {url}")
        raise  # Re-raise the ValueError


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, error_data):
        self.code = error_data.get("code")
        self.message = error_data.get("error")
        super().__init__(self.message)

    def __str__(self):
        return f"API Error {self.code}: {self.message}"


def cached_api_call(
    conn, cursor, endpoint, params=None, dataKey=None, cache_age_limit=3600, force=False
):
    """
    Makes an API call with caching.

    Args:
        endpoint (str): The API endpoint (e.g., "faction/basic").
        params (dict, optional): Parameters for the API call. Defaults to None.
        cache_age_limit (int, optional): Maximum age of cached data in seconds. Defaults to 3600.
        force (bool, optional): Force a fresh API call, ignoring the cache. Defaults to False.

    Returns:
        dict: The JSON response from the API, or None if there was an error.
    """
    if force:
        data = None
    else:
        data = _loadCachedData(endpoint, params=params, cache_age_limit=cache_age_limit)
    if data == None:
        data = _api_raw_call(conn, cursor, url=_getApiURL(endpoint,params=params), params=params)
        if dataKey:
            data = data[dataKey]
        _saveData(endpoint, params, data)
    else:
        print(TEXT["CACHE"], end="", flush=True)

    return data


# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS
def cached_api_paged_call(
    conn, cursor, endpoint, params=None, dataKey=None, cache_age_limit=3600, force=False
):
    """
    Makes a cached API call with pagination support.
    This function attempts to load cached data for the given API endpoint and parameters.
    If the cached data is not available or is outdated, it makes paginated API calls to
    fetch the data and then caches it for future use.
    Args:
        endpoint (str): The API endpoint to call.
        params (dict, optional): The parameters to pass to the API call. Defaults to None.
        dataKey (str, optional): The key to extract data from the API response. Defaults to None.
        cache_age_limit (int, optional): The maximum age of the cache in seconds. Defaults to 3600.
        force (bool, optional): If True, forces a fresh API call, bypassing the cache. Defaults to False.
    Returns:
        dict: The data retrieved from the API or cache.
    """
    if force:
        data = None
    else:
        data = _loadCachedData(endpoint, params=params, cache_age_limit=cache_age_limit)
        if data:
            return data

    if data == None:
        data = paginated_api_calls(
            conn, cursor, endpoint, dataKey=dataKey, params=params
        )
        _saveData(endpoint, params, data)
    return data


def cached_api_paged_log_call(
    conn,
    cursor,
    endpoint,
    timestamp_field="started",
    params=None,
    dataKey=None,
    limit=100,
    force=False,
):
    """
    Fetches paged log data from the Torn API using timestamps with dynamic field names.
    Assumes duplicate handling is done in the database.
    """
    cache_data = _loadCachedData(endpoint, params=params)

    if force or cache_data is None:
        last_timestamp = cache_data.get("last_timestamp", 0) if cache_data else 0
        new_data = paginated_api_calls(
            conn,
            cursor,
            endpoint=endpoint,
            dataKey=dataKey,
            timestamp_field=timestamp_field,
            last_timestamp=last_timestamp,
            limit=limit,
            params=params,
        )

        if cache_data is None:
            cache_data = {"data": [], "last_updated": time.time()}

        cache_data["data"].extend(new_data)
        if new_data:
            cache_data["last_timestamp"] = new_data[-1][timestamp_field]
        _saveData(endpoint, params, cache_data)
        return cache_data["data"]
    else:
        return cache_data["data"]


def paginated_api_calls(
    conn,
    cursor,
    endpoint,
    dataKey,
    timestamp_field="created_at",
    fromTimestamp=None,
    params=None,
    limit=100,
    callback=None,
    callback_parameters={},
    short_name=''
):
    """
    Requests data from a paged API call using timestamps with dynamic field names.
    """
    global headers
    verbose=False
    data = []
    running = True
    if params is None:
        params = {}
    if short_name=='':
        short_name=endpoint
    if fromTimestamp: params["from"] = ( fromTimestamp )
    if short_name=='verbose'  :
        verbose=True
        print(f"\n\nVerbose mode on for {short_name} !!!!!!!!!!!!!!!!!!!!!!!")
        print(f"endpoint = {endpoint}")
        print(f"params =  {params}")
    # if not fromTimestamp:
    #     fromTimestamp=int(datetime.strptime('2020-01-01 00:00:00', "%Y-%m-%d %H:%M:%S").timestamp())  
    print(f"[{short_name}{':' if short_name else ''}",end='',flush=True)
    while running:
        if fromTimestamp: params["from"] = ( fromTimestamp )
        new_data=[]
        # try:
        if 1==1: 
            new_data = _api_raw_call(conn, cursor, url=_getApiURL(endpoint,params=params), params=params)
            if verbose: print(f'url {_getApiURL(endpoint,params=params)} : {len(new_data['revives'])}') 
            if dataKey and dataKey in new_data:
                new_data = new_data[dataKey]
        # except Exception as e:
        #     print(f"API call failed: {e}")
        #     running = False
        #     raise APIError({"endpoint":endpoint,"params":params,'response':new_data["error"] if new_data else 'unknown'})
        #     break

        count = len(new_data) if new_data is not None else 0
        if count > 0:
            if isinstance(new_data, list):
                data.extend(new_data)
            elif isinstance(new_data, dict):
                # Convert the dictionary to a list of rows, including the key
                new_data = [{"revive_id": key, **value} for key, value in new_data.items()] 
                data.extend(new_data)  # Add all rows from the converted list
            else:
                print(f"Unexpected data type: {type(new_data)}")
                running = False
                data.extend(new_data)
                break

            oldestTimestamp = int(min(row[timestamp_field] for row in new_data))
            latestTimestamp = int(max(row[timestamp_field] for row in new_data))

            if callback is not None:
                callback(conn, cursor, new_data, callback_parameters)

            if verbose: print(f'\nfromTimestamp={fromTimestamp} oldestTimestamp={oldestTimestamp} latestTimestamp={latestTimestamp}') 
        else:
            latestTimestamp=0
            running=False
        if fromTimestamp and latestTimestamp<=fromTimestamp and running:
            running = False
        else:
            fromTimestamp = latestTimestamp+1
    print(len(data),"]",end='',flush=True)
    return data

def date_to_unix(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").timestamp()) # date_to_unix('2014-01-01 00:00:00')
