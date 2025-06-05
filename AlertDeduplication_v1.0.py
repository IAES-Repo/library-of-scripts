import requests
import hashlib
import json
import sys

# GLPI API endpoint and authentication tokens
GLPI_URL = "API URL" # GLPI API URL
APP_TOKEN = "TOKEN" #SOC API Token
USER_TOKEN = "TOKEN" #Post Only User Token

def build_alert_hash(alert_desc, src_ip, dst_ip, src_mac, dst_mac):
    """
    Build a unique hash for the alert based on its description and network identifiers.
    """
    combined = f"{alert_desc}|{src_ip}|{dst_ip}|{src_mac}|{dst_mac}"
    return hashlib.sha256(combined.encode()).hexdigest()

def get_session_token():
    """
    Authenticate with the GLPI API and retrieve a session token.
    """
    headers = {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN
    }
    data = {
        "user_token": USER_TOKEN
    }
    r = requests.post(f"{GLPI_URL}/initSession", headers=headers, data=json.dumps(data))
    r.raise_for_status()
    return r.json()["session_token"]

def find_existing_ticket(session_token, alert_hash):
    """
    Search for an existing ticket in GLPI containing the alert hash in its name.
    Returns the ticket ID if found, otherwise None.
    """
    headers = {
        "Content-Type": "application/json",
        "Session-Token": session_token,
        "App-Token": APP_TOKEN
    }
    # Search for tickets where the name contains the alert hash
    search_url = f"{GLPI_URL}/search/Ticket"
    params = {
        "criteria[0][field]": 1,
        "criteria[0][searchtype]": "contains",
        "criteria[0][value]": alert_hash
    }
    r = requests.get(search_url, headers=headers, params=params)
    r.raise_for_status()
    results = r.json()
    if results["totalcount"] > 0:
        return results["data"][0]["id"]
    return None

def create_ticket(session_token, alert_hash, alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol):
    """
    Create a new ticket in GLPI for the alert.
    """
    headers = {
        "Content-Type": "application/json",
        "Session-Token": session_token,
        "App-Token": APP_TOKEN,
    }

    ticket_data = {
        "input": {
            "name": f"Alert: {alert_desc} [{alert_hash}]",
            "content": (
                f"Initial alert triggered:\n"
                f"Source IP: {src_ip}\n"
                f"Destination IP: {dst_ip}\n"
                f"Source MAC: {src_mac}\n"
                f"Destination MAC: {dst_mac}\n"
                f"Protocol: {protocol}\n"
                f"Alert Hash: {alert_hash}"
            ),
            "itilcategories_id": 1,
            "priority": 3,
            "requesttypes_id": 1,
            "entities_id": 0
        }
    }

    r = requests.post(f"{GLPI_URL}/Ticket", headers=headers, data=json.dumps(ticket_data))
    r.raise_for_status()
    return r.json()["id"]

def add_followup(session_token, ticket_id, alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol):
    """
    Add a follow-up comment to an existing ticket indicating a duplicate alert.
    """
    headers = {
        "Session-Token": session_token,
        "App-Token": APP_TOKEN,
        "Content-Type": "application/json"
    }

    followup_data = {
        "input": {
            "itemtype": "Ticket",
            "items_id": ticket_id,
            "content": (
                f"Duplicate alert seen again:\n"
                f"Source IP: {src_ip}\n"
                f"Destination IP: {dst_ip}\n"
                f"Source MAC: {src_mac}\n"
                f"Destination MAC: {dst_mac}\n"
                f"Protocol: {protocol}"
            )
        }
    }

    r = requests.post(f"{GLPI_URL}/Ticket/{ticket_id}/ITILFollowup", headers=headers, data=json.dumps(followup_data))
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    # Ensure correct number of arguments are provided
    if len(sys.argv) != 7:
        print("Usage: python3 glpi_ticket_deduplicator.py <alert_desc> <src_ip> <dst_ip> <src_mac> <dst_mac> <protocol>")
        sys.exit(1)

    # Parse arguments
    alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol = sys.argv[1:7]
    alert_hash = build_alert_hash(alert_desc, src_ip, dst_ip, src_mac, dst_mac)

    try:
        # Authenticate and get session token
        session_token = get_session_token()
        # Check if a ticket for this alert already exists
        existing_ticket_id = find_existing_ticket(session_token, alert_hash)

        if existing_ticket_id:
            print(f"Alert already exists. Adding comment to ticket ID {existing_ticket_id}.")
            add_followup(session_token, existing_ticket_id, alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol)
        else:
            new_ticket_id = create_ticket(session_token, alert_hash, alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol)
            print(f"New ticket created: ID {new_ticket_id}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
