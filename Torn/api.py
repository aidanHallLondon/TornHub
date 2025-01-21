import requests
import time
import os
import json
from Torn.api_keyHandler import get_api_key

BASE_URL = "https://api.torn.com/v2"
headers = None # {"Authorization": f"ApiKey {api_key}"} # call getHeaders after Db initialised
MAX_API_CALLS_ALLOWED = 50
api_request_count = 0
api_last_request_time = None
CACHE_PATH = "data/cache"  # Directory to store cached files
JSON_INDENT = 2

if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)

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

def _getCacheFilePath(endpoint, params=None):
    '''
    Returns the file path for cached data for an endpoint and params.
    '''
    global CACHE_PATH
    if params is None:
        return f"{CACHE_PATH}/{endpoint}.json"
    else:
        return f"{CACHE_PATH}/{endpoint}_{params}.json" 
  
def _saveData(endpoint, params=None, data=None):
    '''
    Saves API results data to a file in the cache.
    '''
    filePath = _getCacheFilePath(endpoint, params)
    path = os.path.dirname(filePath)  
    print(filePath,path)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(filePath, "w") as file:
        json.dump(data, file, indent=JSON_INDENT) 
    
def _getApiURL(endpoint):
      global BASE_URL
      return f"{BASE_URL}/{endpoint}"
 

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
                    #print(f"Using cached data from {filePath}")
                    return data
            except json.JSONDecodeError:
                print(f"Error reading cache file {filePath}")
                pass
    return None
    
# API CALLS
# API CALLS
      
def _api_raw_call(url, params=None):
    """
    Makes a generic API call.

    Args:
        url (str): The full API URL.
        headers (dict, optional): Headers for the request. Defaults to None.
        params (dict, optional): Parameters for the request. Defaults to None.

    Returns:
        dict: The JSON response from the API, or None if there was an error.
    """
    global api_request_count, api_last_request_time, headers
    api_last_request_time=time.time()
    api_request_count+=1

    if headers==None:
        api_key = get_api_key() # Torn_limited_API_KEY # Torn_public_API_KEY
        headers = {"Authorization": f"ApiKey {api_key}"}
     
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        return None
    except ValueError as json_err:
        print(f"Error decoding JSON response: {json_err} {url} ")
        exit()
        return None

def cached_api_call(endpoint, params=None, dataKey=None, cache_age_limit=3600, force=False):
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
    print("URL",_getApiURL(endpoint), params)
    if force:
        data = None
    else:
        data = _loadCachedData(endpoint, params=params, cache_age_limit=cache_age_limit)
    if data == None:
        data = _api_raw_call(url=_getApiURL(endpoint), params=params)
        if dataKey:
            data = data[dataKey]
        _saveData(endpoint, params, data)
    return data

# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS
def cached_api_paged_call(endpoint,  params=None, dataKey=None, cache_age_limit=3600, force=False):
    '''
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
    '''
    if force:
        data = None
    else:
        data= _loadCachedData(endpoint, params=params, cache_age_limit=cache_age_limit)
        if data:
            return data

    if data == None:
        data = _paginated_api_calls(endpoint, dataKey=dataKey, params=params)
        _saveData(endpoint, params, data)
    return data

# def cached_api_paged_log_call(endpoint,  params=None, dataKey=None, cache_age_limit=3600, force=False):
#     '''
#     Fetches paged data from the Torn API and appends it to a file.
#     '''
#     offset=0 # assume none until we find cached data
#     data = _loadCachedData(endpoint, params=params)
#     data.extend( _paginated_api_calls(endpoint, dataKey=dataKey, offset= len(data), params=None))
#     _saveData(endpoint, params, data)
#     return data

def _paginated_api_calls(endpoint, dataKey, offset=0, params=None,limit=1000):
    '''
    request data from a paged API call using offset 
    if the data returns 100 or more records we need to make more calls to get all the data
    Some records in the data have the same offset timestamp so we need to use offset to avoid missing or duplicating records
    '''
    global api_request_count, MAX_API_CALLS_ALLOWED,headers
    data=[]
    running=True
    if params is None:
        params = {}
    params["sort"] = "ASC"
    params["limit"] = limit
    while running:
        print(offset) # progress indicator
        params["offset"] = offset
        new_data = _api_raw_call(url=_getApiURL(endpoint), params=params)[dataKey]
        count=len(new_data) if new_data != None else 0
        if count>0:
            offset+=count
            data.extend(new_data)
        if count<limit or api_request_count>MAX_API_CALLS_ALLOWED:
            running=False   
    return data    