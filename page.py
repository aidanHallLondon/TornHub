
import requests
import time
import os
import json
import sys

# from Torn.api import cached_api_paged_call, cached_api_call
from Torn.api import getFactionMembers,getCrimes
def main():
    # cached_api_paged_call("faction/crimes", dataKey="crimes", params=None)         
    # cached_api_call("faction/members", dataKey="members", params=None)         
    getFactionMembers()
    getCrimes()

main()