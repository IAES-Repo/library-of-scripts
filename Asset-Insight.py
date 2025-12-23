
"""
Assest-Insight

This tool centralizes internal IP investigations by showing what device an IP belongs to and its recent network activity. Enter an IP to retrieve asset details and relevant logs, view key events in clear tables, and export a detailed report for quick analysis.

Author: Hassan Abkow
Date: 11/18/25
"""

import argparse
import requests
from elasticsearch import Elasticsearch
from tabulate import tabulate
from datetime import datetime
import getpass
from datetime import datetime, timezone
from collections import Counter

datetime.now(timezone.utc).isoformat()



GLPI_USERNAME = input("GLPI username: ")
GLPI_PASSWORD = getpass.getpass("GLPI password: ")

# Update configuration variables in the script.
ELASTIC_URL = "https://your-elasticsearch-server:9200/"
GLPI_URL = "https://your-glpi-server/apirest.php"
GLPI_APP_TOKEN = "your_glpi_app_token"


def summarize_elk_events(events, top_n=5):
    if not events:
        print("\nNo ELK logs to summarize.")
        return

    print("\nTop Events:")

    # Count event descriptions
    event_counter = Counter(e['event'] for e in events)
    print("\nMost frequent events:")
    for event, count in event_counter.most_common(top_n):
        print(f"{event}: {count} occurrence(s)")

    # Count source-destination pairs
    flow_counter = Counter((e['source'], e['dest'], e.get('protocol', '-')) for e in events)
    print("\nTop source -> destination flows:")
    for (src, dst, proto), count in flow_counter.most_common(top_n):
        print(f"{src} -> {dst} [{proto}]: {count} occurrence(s)")


# Elasticsearch Functions
def elk_search_ip(ip):

    # Update configuration variables in the script.
    es = Elasticsearch(
        ["https://your-elasticsearch-server:9200/"],   
        basic_auth=("username", "Password") 
    )

    query = {
        "query": {
            "bool": {
                "should": [
                    {"term": {"source.ip": ip}},
                    {"term": {"destination.ip": ip}},
                    {"term": {"client.ip": ip}},
                    {"term": {"host.ip": ip}},
                    {"term": {"src_ip": ip}},   
                    {"term": {"dest_ip": ip}},

                    {"term": {"zeek.source.ip": ip}},
                    {"term": {"zeek.destination.ip": ip}},
                    {"term": {"zeek.orig_ip": ip}},
                    {"term": {"zeek.resp_ip": ip}},
                    {"term": {"conn.src_ip": ip}},
                    {"term": {"conn.dest_ip": ip}},
                    {"term": {"source.address": ip}},
                    {"term": {"destination.address": ip}},
                    {"term": {"observer.ip": ip}},
                    {"term": {"network.forwarded_ip": ip}}   
                ]
            }
        },
        "size": 200
    }

    response = es.search(index="logs-*", body=query)

    events = []
    for hit in response["hits"]["hits"]:
        src = hit["_source"]

        # Extract Zeek flow_id
        flow_id = "-"
        if "uid" in src:
            if isinstance(src["uid"], list) and src["uid"]:
                flow_id = src["uid"][0]
            elif isinstance(src["uid"], str):
                flow_id = src["uid"]

        # Determine the event description in priority order
        # Determine the event description
        event_desc = "-"
            # Suricata / ECS style
        if "alert" in src and "signature" in src["alert"]:
            event_desc = src["alert"]["signature"]
        elif "event" in src and "action" in src["event"]:
            event_desc = src["event"]["action"]
        elif "event" in src and "id" in src["event"]:
            event_desc = src["event"]["id"]
        elif "flow_id" in src:
            event_desc = f"flow_id: {src['flow_id']}"
            # Zeek conn log
        elif "zeek.conn.state" in src or "zeek.conn.duration" in src:
            proto = src.get("network.transport", ["-"])[0] if isinstance(src.get("network.transport"), list) else src.get("network.transport", "-")
            state = src.get("zeek.conn.state", ["-"])[0] if isinstance(src.get("zeek.conn.state"), list) else src.get("zeek.conn.state", "-")
            duration = src.get("zeek.conn.duration", ["-"])[0] if isinstance(src.get("zeek.conn.duration"), list) else src.get("zeek.conn.duration", "-")
            flow_id = src.get("uid", ["-"])[0] if isinstance(src.get("uid"), list) else src.get("uid", "-")
            event_desc = f"{proto} session, state={state}, duration={duration}, flow_id={flow_id}"


        # Extract IPs
        src_ip = (
            src.get("source", {}).get("ip", ["-"])[0] if isinstance(src.get("source", {}).get("ip"), list) else src.get("source", {}).get("ip") or
            src.get("src_ip") or
            "-"
        )
        dest_ip = (
            src.get("destination", {}).get("ip", ["-"])[0] if isinstance(src.get("destination", {}).get("ip"), list) else src.get("destination", {}).get("ip") or
            src.get("dest_ip") or
            "-"
        )

        # Extract ports
        src_port = (
            src.get("source", {}).get("port", ["-"])[0] if isinstance(src.get("source", {}).get("port"), list) else src.get("source", {}).get("port") or
            src.get("src_port") or
            "-"
        )
        dest_port = (
            src.get("destination", {}).get("port", ["-"])[0] if isinstance(src.get("destination", {}).get("port"), list) else src.get("destination", {}).get("port") or
            src.get("dest_port") or
            "-"
        )

        # Extract protocol
        protocol = (
            src.get("network", {}).get("transport", ["-"])[0] if isinstance(src.get("network", {}).get("transport"), list) else src.get("network", {}).get("transport") or
            src.get("proto") or
            src.get("protocol") or
            "-"
        )



        events.append({
            "timestamp": src.get("@timestamp", "-"),
            "source": src_ip,
            "source_port": src_port,
            "dest": dest_ip,
            "dest_port": dest_port,
            "protocol": protocol,
            "event": event_desc,
            "flow_id": flow_id,
            "logsource": hit["_index"]
        })

    # Debug: print first 5 hits
    print("\nFirst 5 ELK hits (debug):")
    for hit in events[:5]:
        print(hit)

    return events



# GLPI Function
def glpi_init_session():
    payload = {
        "login": GLPI_USERNAME,
        "password": GLPI_PASSWORD
    }

    headers = {
        "App-Token": GLPI_APP_TOKEN,
        "Content-Type": "application/json"
    }

    r = requests.post(f"{GLPI_URL}/initSession", headers=headers, json=payload, verify=True)

    print("GLPI Response:", r.status_code, r.text)

    if r.status_code != 200:
        print("Failed to authenticate to GLPI API")
        exit()

    return r.json().get("session_token")



def glpi_search_ip(session_token, ip):
    headers = {
        "App-Token": GLPI_APP_TOKEN,
        "Session-Token": session_token
    }

    # Search Computers by IP field 
    url = (
        f"{GLPI_URL}/search/Computer?"
        f"criteria[0][field]=95&criteria[0][searchtype]=contains&criteria[0][value]={ip}"
    )

    r = requests.get(url, headers=headers, verify=True)
    if r.status_code != 200:
        return None

    return r.json()


# TXT EXPORT FUNCTION

def export_to_txt(ip, glpi_results, elk_results):
    filename = f"investigation_{ip}.txt"

    with open(filename, "w") as f:
        f.write(f"IP Investigation Report\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()} UTC\n")
        f.write(f"Target IP: {ip}\n\n")

        # GLPI Section
        f.write("=" * 60 + "\n")
        f.write("GLPI Asset Information\n")
        f.write("=" * 60 + "\n")

        if not glpi_results or "data" not in glpi_results or not glpi_results["data"]:
            f.write("No GLPI asset found for this IP.\n\n")
        else:
            for item in glpi_results["data"]:
                f.write(f"ID: {item.get('id', '-')}\n")
                f.write(f"Name: {item.get('name', '-')}\n")
                f.write(f"Full Name: {item.get('completename', '-')}\n")
                f.write("-" * 50 + "\n")
            f.write("\n")

        # ELK Section
        f.write("=" * 60 + "\n")
        f.write("ELK / SIEM Log Activity\n")
        f.write("=" * 60 + "\n")

        if not elk_results:
            f.write("No ELK logs found for this IP.\n")
        else:
            for e in elk_results:
                f.write(f"Time: {e['timestamp']}\n")
                f.write(f"Source: {e['source']}:{e['source_port']}\n")
                f.write(f"Destination: {e['dest']}:{e['dest_port']}\n")
                f.write(f"Protocol: {e['protocol']}\n")
                f.write(f"Event: {e['event']}\n")
                f.write(f"Index: {e['logsource']}\n")
                f.write("-" * 50 + "\n")


    print(f"\nExported report to: {filename}\n")


# REPORTING FUNCTIONS

def print_glpi_results(results):
    if not results or "data" not in results or not results["data"]:
        print("\nNo matching GLPI asset found for this IP.")
        return

    print("\nGLPI Asset Information\n")

    rows = []
    for item in results["data"]:
        rows.append([
            item.get("id", "-"),
            item.get("name", "-"),
            item.get("completename", "-")
        ])

    print(tabulate(rows, headers=["ID", "Device Name", "Full Name"], tablefmt="fancy_grid"))


def print_elk_results(events):
    if not events:
        print("\nNo ELK logs found for this IP.")
        return

    print("\nELK Log Activity\n")

    rows = []
    for event in events[:50]:
        rows.append([
            event["timestamp"],
            event["source"],
            event["source_port"],
            event["dest"],
            event["dest_port"],
            event["protocol"],
            event["event"],
            event["flow_id"],
            event["logsource"]
        ])

    print(tabulate(
        rows,
        headers=["Time", "Source", "Src Port", "Dest", "Dest Port", "Protocol", "Event", "Zeek-Events", "Index"],
        tablefmt="fancy_grid"
    ))


# MAIN

def main():
    parser = argparse.ArgumentParser(description="Internal IP Investigation Tool (ELK + GLPI) with TXT Export")
    parser.add_argument("ip", help="IP address to investigate")
    parser.add_argument("--export", action="store_true", help="Export results to TXT file")
    args = parser.parse_args()

    ip = args.ip
    print(f"\nInvestigating IP: {ip}\n")

    # GLPI search
    session_token = glpi_init_session()
    glpi_results = glpi_search_ip(session_token, ip)

    # ElasticSearch search
    elk_results = elk_search_ip(ip)

    # Print to screen
    print_glpi_results(glpi_results)
    print_elk_results(elk_results)
    summarize_elk_events(elk_results, top_n=5)

    # Export if requested
    if args.export:
        export_to_txt(ip, glpi_results, elk_results)

    print("\nInvestigation complete.\n")


if __name__ == "__main__":
    main()
