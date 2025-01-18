import requests
import time
import os
import json
import sys
from Torn.manageDB import DB_PATH,getPreference,setPreference
from Torn.api_keyHandler import get_api_key, api_key

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

def getFactionMembers(params={"striptags": "false"}, force=False):
    return cached_api_call("faction/members", dataKey="members", params=params, force=force) 

def getCrimes(params=None, force=False):
    crimes= cached_api_paged_call(endpoint="faction/crimes", dataKey="crimes", params=params, force=force) 
    return crimes 

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
 
def _loadCachedData(endpoint,params=None,defaultEmptyData=[]):
    '''
    Loads cached API data from a file.
    Otherwise returns the default empty data.
    '''
    filePath = _getCacheFilePath(endpoint, params=params)
    if os.path.exists(filePath):
        with open(filePath, "r") as file:
            return json.load(file)
    else:
        return defaultEmptyData
    
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
        print(f"Error decoding JSON response: {json_err}")
        return None
    
def cached_api_call(endpoint, params=None, dataKey=None, force=False):
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
    data = _loadCachedData(endpoint, params=params)
    new_data = _api_raw_call(url=_getApiURL(endpoint), params=params)
   
    if dataKey:
        data.extend(new_data[dataKey])
    else:
        data.extend(new_data )
    _saveData(endpoint, params, data)
    return data

# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS
# PAGED API CALLS

def cached_api_paged_call(endpoint, dataKey=None, params=None, force=False):
    '''
    Fetches paged data from the Torn API and appends it to a file.
    '''
    offset=0 # assume none until we find cached data
    data = _loadCachedData(endpoint, params=params)
    data.extend( _paginated_api_calls(endpoint, dataKey=dataKey, offset= len(data), params=None))
    _saveData(endpoint, params, data)
    return data

def _paginated_api_calls(endpoint, dataKey, offset=0, params=None):
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
    while running:
        params["offset"] = offset
        new_data = _api_raw_call(url=_getApiURL(endpoint), params=params)[dataKey]
        count=len(new_data)
        if count>0:
            offset+=count
            data.extend(new_data)
        if count<100 or api_request_count>MAX_API_CALLS_ALLOWED:
            running=False   
    return data    