import requests

# Torn API Key
API_KEY = "Ry3XWtDC7xeMgxNc"

# API Endpoints
AVAILABLE_CRIMES_ENDPOINT = f"https://api.torn.com/v2/faction/crimes?key={API_KEY}&cat=available&offset=0"
COMPLETED_CRIMES_ENDPOINT = f"https://api.torn.com/v2/faction/crimes?key={API_KEY}&cat=completed&offset=0"
FACTION_MEMBERS_ENDPOINT = f"https://api.torn.com/v2/faction/members?key={API_KEY}&striptags=true"

# Fetch data from the Torn API
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Retrieve available and completed crimes
def get_crimes():
    available_crimes = fetch_data(AVAILABLE_CRIMES_ENDPOINT)["crimes"]
    completed_crimes = fetch_data(COMPLETED_CRIMES_ENDPOINT)["crimes"]
    return available_crimes, completed_crimes

# Retrieve current faction members
def get_faction_members():
    members = fetch_data(FACTION_MEMBERS_ENDPOINT)["members"]
    return {member["id"]: {"name": member["name"], "position": member["position"]} for member in members}

# Process crimes and participants
def process_crimes(available_crimes, completed_crimes, faction_members):
    crime_data = {}
    participants = set()  # Track members who participated in crimes

    # Combine available and completed crimes
    for crime in available_crimes + completed_crimes:
        crime_name = crime["name"]
        difficulty = crime["difficulty"]
        slots = crime["slots"]
        planning_at = crime["planning_at"]

        # Initialize crime entry
        if crime_name not in crime_data:
            crime_data[crime_name] = {
                "difficulty": difficulty,
                "roles": {}
            }

        for slot in slots:
            # Ignore empty positions
            if not slot["user"]:
                continue

            role = slot["position"]
            user_id = slot["user"]["id"]
            user_name = faction_members.get(user_id, {}).get("name", f"Unknown ({user_id})")
            success_chance = slot["success_chance"]

            # Add to participants list
            participants.add(user_id)

            # Initialize role entry in crime_data
            if role not in crime_data[crime_name]["roles"]:
                crime_data[crime_name]["roles"][role] = []

            # Check if the user is already in the role list for this crime
            existing_entry = next(
                (entry for entry in crime_data[crime_name]["roles"][role] if entry["user_id"] == user_id), None
            )

            if existing_entry:
                # Update if the new chance is higher
                if success_chance > existing_entry["success_chance"]:
                    existing_entry["success_chance"] = success_chance
                    existing_entry["last_seen"] = planning_at
            else:
                # Add new entry if user not found for this role
                crime_data[crime_name]["roles"][role].append({
                    "user_name": user_name,
                    "user_id": user_id,
                    "success_chance": success_chance,
                    "last_seen": planning_at
                })

    # Identify slackers and recruits
    slackers = []
    recruits = []

    for user_id, info in faction_members.items():
        if user_id not in participants:
            if info["position"] == "Recruit":
                recruits.append({"name": info["name"], "id": user_id})
            else:
                slackers.append({"name": info["name"], "id": user_id})

    return crime_data, slackers, recruits



# Generate HTML output
def generate_html(crime_data, slackers, recruits):
    html = "<h1>Faction Crime Report</h1>"

    # Generate one table per crime
    for crime_name, crime_details in sorted(crime_data.items(), key=lambda x: x[1]["difficulty"], reverse=True):
        html += f"<h2>{crime_name}</h2>"
        html += '<table border="1" cellpadding="5" cellspacing="0">'
        html += "<tr><th>Name [ID]</th><th>Chance %</th><th>Last Seen</th></tr>"
        for role, participants in crime_details["roles"].items():
            html += f'<tr><td colspan="3"><strong>{role}</strong></td></tr>'
            for participant in sorted(participants, key=lambda x: x["success_chance"], reverse=True):
                profile_link = f"https://www.torn.com/profiles.php?XID={participant['user_id']}"
                html += (
                    f"<tr>"
                    f"<td><a href='{profile_link}' target='_blank'>{participant['user_name']} [{participant['user_id']}]</a></td>"
                    f"<td>{participant['success_chance']}%</td>"
                    f"<td>{participant['last_seen']}</td>"
                    f"</tr>"
                )
        html += "</table>"

    # Add slackers list
    html += "<h2>Slackers</h2>"
    if slackers:
        html += '<table border="1" cellpadding="5" cellspacing="0">'
        for slacker in slackers:
            profile_link = f"https://www.torn.com/profiles.php?XID={slacker['id']}"
            html += (
                f"<tr><td><a href='{profile_link}' target='_blank'>{slacker['name']} [{slacker['id']}]</a></td></tr>"
            )
        html += "</table>"
    else:
        html += "<p>No slackers found!</p>"

    # Add recruits list
    html += "<h2>Recruits</h2>"
    if recruits:
        html += '<table border="1" cellpadding="5" cellspacing="0">'
        for recruit in recruits:
            profile_link = f"https://www.torn.com/profiles.php?XID={recruit['id']}"
            html += (
                f"<tr><td><a href='{profile_link}' target='_blank'>{recruit['name']} [{recruit['id']}]</a></td></tr>"
            )
        html += "</table>"
    else:
        html += "<p>No recruits found!</p>"

    return html




# Main script
if __name__ == "__main__":
    available_crimes, completed_crimes = get_crimes()
    faction_members = get_faction_members()
    crime_data, slackers, recruits = process_crimes(available_crimes, completed_crimes, faction_members)
    html_output = generate_html(crime_data, slackers, recruits)
    print(html_output)
