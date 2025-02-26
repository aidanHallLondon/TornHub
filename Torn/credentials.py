import json

# credentials = load_credentials()
# 
# primary_API_key = credentials.get("primary_API_key")
# upload = credentials.get("upload")
# web_username = credentials.get("web_username")
# web_password = credentials.get("web_password")
# hostname = credentials.get("hostname")
# host_username = credentials.get("host_username")
# static_web_local_path = credentials.get("static_web_local_path")
# remote_path = credentials.get("remote_path")
# host_password = credentials.get("host_password")
# htpasswd_path_on_server = credentials.get("htpasswd_path_on_server")




def load_credentials(filepath="credentials.json"):
    """Loads credentials from a JSON file, creates it if it doesn't exist, and overwrites with a cleaned version."""

    credentials = {}
    try:
        with open(filepath, "r") as f:
            credentials = json.load(f)
    except FileNotFoundError:
        print(f"Credentials file '{filepath}' not found. Creating a new one.")
        credentials = {}  # Start with an empty dict.
    except json.JSONDecodeError:
        print(f"Error decoding JSON in '{filepath}'. Starting with empty credentials.")
        credentials = {}

    # Ensure the credentials dictionary has the expected keys, even if they're empty.
    expected_keys = [
        "upload",
        "web_username",
        "web_password",
        "hostname",
        "host_username",
        "host_password",
        "static_web_local_path",
        "remote_path",
        "htpasswd_path_on_server",
        "primary_API_key",
    ]
    for key in expected_keys:
        if key not in credentials:
            credentials[key] = "" #ensure all keys exist

    # Write back the (potentially corrected) credentials to the JSON file, ensuring consistent formatting.
    try:
        print(filepath)
        with open(filepath, "w") as f:
            json.dump(credentials, f, indent=4)  # Indent for readability
    except IOError as e:
        print(f"Error writing credentials to '{filepath}': {e}")
    return credentials
