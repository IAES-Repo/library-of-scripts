import requests
import hashlib
import json
import sys

# GLPI API endpoint and authentication tokens
GLPI_URL = "API URL"  # Replace with actual GLPI API URL
APP_TOKEN = "TOKEN"    # Replace with your App Token
USER_TOKEN = "TOKEN"   # Replace with your User Token

def build_alert_hash(alert_desc, src_ip, dst_ip, src_mac, dst_mac):
    combined = f"{alert_desc}|{src_ip}|{dst_ip}|{src_mac}|{dst_mac}"
    return hashlib.sha256(combined.encode()).hexdigest()

def get_session_token():
    headers = {
        "Content-Type": "application/json",
        "App-Token": APP_TOKEN,
        "Authorization": f"user_token {USER_TOKEN}"
    }
    r = requests.get(f"{GLPI_URL}/initSession", headers=headers)
    r.raise_for_status()
    return r.json()["session_token"]

def find_existing_ticket(session_token, alert_hash):
    headers = {
        "Content-Type": "application/json",
        "Session-Token": session_token,
        "App-Token": APP_TOKEN
    }
    search_url = f"{GLPI_URL}/search/Ticket"
    params = {
        "criteria[0][field]": 1,
        "criteria[0][searchtype]": "contains",
        "criteria[0][value]": alert_hash
    }
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    results = response.json()
    if results.get("totalcount", 0) > 0:
        return results["data"][0]["2"]  # "2" is ticket ID field
    return None

def create_ticket(session_token, alert_hash, alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol):
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
    headers = {
        "Content-Type": "application/json",
        "Session-Token": session_token,
        "App-Token": APP_TOKEN
    }
    followup_data = {
        "input": {
            "itemtype": "Ticket",
            "items_id": ticket_id,
            "content": (
                f"Duplicate alert seen again:\n"
                f"Alert: {alert_desc}\n"
                f"Source IP: {src_ip}\n"
                f"Destination IP: {dst_ip}\n"
                f"Source MAC: {src_mac}\n"
                f"Destination MAC: {dst_mac}\n"
                f"Protocol: {protocol}"
            )
        }
    }
    response = requests.post(
        f"{GLPI_URL}/Ticket/{ticket_id}/ITILFollowup",
        headers=headers,
        data=json.dumps(followup_data)
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Usage: python3 glpi_ticket_deduplicator.py <alert_desc> <src_ip> <dst_ip> <src_mac> <dst_mac> <protocol>")
        sys.exit(1)

    alert_desc, src_ip, dst_ip, src_mac, dst_mac, protocol = sys.argv[1:7]
    alert_hash = build_alert_hash(alert_desc, src_ip, dst_ip, src_mac, dst_mac)

    try:
        session_token = get_session_token()
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
