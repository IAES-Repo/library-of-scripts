"""
UDP Receiver for JSON Files and Hash Logs v0.4
===========================================

This program implements a UDP receiver that listens indefinitely on a specified port for
incoming data packets from multiple FM plant sites. It is designed to correctly assemble JSON
files and hash logs from packets that may arrive interleaved from different senders. To achieve
this, the program uses per-sender session management, buffering incoming data separately based on
the sender's IP address.

Key Features:
-------------
1. **Per-Sender Session Management:**
   - When a sender initiates a transfer with a control message (e.g., a packet starting with
     "FILENAME:" for files or "HASH_LOG_START" for hash logs), a new session is created and stored
     in a session dictionary keyed by the sender's IP.
   - Each session maintains its own data buffer (a bytearray) where incoming data chunks are appended.
   - When an "EOF" control message is received, the session is finalized—data is written to disk,
     processed, and then the session is removed from memory.

2. **Control Message Handling:**
   - **"FILENAME:"**: Indicates the start of a file transmission. The filename is extracted and used
     to create a new file session.
   - **"HASH_LOG_START"**: Indicates the start of a hash log transmission used for integrity verification.
   - **"ALL_FILES_SENT"**: Used to indicate that all file transmissions are complete (logged for
     reference but not used in session assembly).
   - **"EOF"**: Marks the end of the current session. On receiving this, the data in the session is saved
     and, if a hash log is received, used to verify the integrity of the files.

3. **Data Integrity Verification:**
   - After a hash log session is finalized, the program compares the received SHA-256 hashes with those
     generated from the corresponding files.
   - Files failing the integrity check are moved to a designated "corrupted" folder.

4. **Site Name Logging:**
   - A mapping dictionary (`SITE_NAMES`) converts sender IP addresses into user-friendly site names.
   - All terminal logs display only the site names instead of the raw IP addresses for clarity and privacy.

5. **Long-Running Process:**
   - The receiver is designed to run continuously (e.g., handling updates every 10 minutes), ensuring
     that completed sessions are cleared from memory to avoid resource overload.

Usage:
------
- Configure the listening IP and port as required.
- Ensure that the necessary directories (for received files, corrupted files, hash logs, and site-specific folders)
  exist or will be created by the script.
- Run the script on a machine prepared to receive UDP packets from the remote sites.

Dependencies:
-------------
- Python 3.x and its standard library modules: os, socket, hashlib, json, time, shutil.

Author:
-------
Pedro Leal - IAES SOC

Date:
-----
Feb 11 2025
"""

import os
import socket
import hashlib
import json
import time
import shutil

# === Configuration and Directory Setup ===
received_dir = "./received"
corrupted_dir = "./corrupted"
hashlog_dir = "./hashlog"
fm1_dir = "./FM1"
fm2_dir = "./FM2"
fm3_dir = "./FM3"

# Ensure that needed directories exist.
for directory in (received_dir, corrupted_dir, hashlog_dir, fm1_dir, fm2_dir, fm3_dir):
    os.makedirs(directory, exist_ok=True)

# Listening settings
listen_ip = "0.0.0.0"  # Listen on all interfaces
listen_port = 50000
chunk_size = 1024

# Known sender IP addresses mapped to site names.
SITE_NAMES = {
    "1.1.1.1": "Site FM1",
    "2.2.2.2": "Site FM2",
    "3.3.3.3": "Site FM3",
}

# For convenience, assign sender IPs to variables.
fm1_ip = "1.1.1.1"
fm2_ip = "2.2.2.2"
fm3_ip = "3.3.3.3"

# Dictionary to keep track of active sessions by sender IP.
# Each session is a dict containing:
#    - type: "file" or "hash_log"
#    - filename: (if type=="file")
#    - data: a bytearray() that accumulates incoming chunks.
sessions = {}

# === Utility Functions ===
def generate_file_hash(file_path):
    """Generate SHA-256 hash for the given file."""
    try:
        hash_obj = hashlib.sha256()
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (FileNotFoundError, IOError) as e:
        print(f"Error generating hash for file '{file_path}': {e}")
        return None

def verify_files(received_dir, hash_log_path, corrupted_dir):
    """Verify received files against hashes provided in the hash log."""
    try:
        with open(hash_log_path, 'r') as log_file:
            hash_log = json.load(log_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading hash log: {e}")
        return

    for entry in hash_log:
        filename = entry['filename']
        expected_hash = entry['hash']
        file_path = os.path.join(received_dir, filename)

        if os.path.exists(file_path):
            received_hash = generate_file_hash(file_path)
            if received_hash == expected_hash:
                print(f"File '{filename}' passed integrity check.")
            else:
                print(f"File '{filename}' failed integrity check. Moving to corrupted folder.")
                try:
                    os.rename(file_path, os.path.join(corrupted_dir, filename))
                except OSError as e:
                    print(f"Error moving file '{filename}' to corrupted folder: {e}")
        else:
            print(f"File '{filename}' not found in received directory.")

# === Packet Processing Function ===
def process_packet(data, addr):
    """Process an incoming UDP packet from a sender."""
    sender_ip = addr[0]
    site_name = SITE_NAMES.get(sender_ip, "Unknown Site")

    # Check for control messages (process as bytes to protect binary data):
    if data.startswith(b"FILENAME:"):
        # Start a new file session.
        try:
            message = data.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Error decoding FILENAME message from {site_name}")
            return
        filename = message[len("FILENAME:"):]
        print(f"Starting file reception from {site_name}: {filename}")
        sessions[sender_ip] = {"type": "file", "filename": filename, "data": bytearray()}
        return

    elif data == b"HASH_LOG_START":
        # Start a new hash log session.
        print(f"Starting hash log reception from {site_name}")
        sessions[sender_ip] = {"type": "hash_log", "data": bytearray()}
        return

    elif data == b"ALL_FILES_SENT":
        # Log that all files have been sent.
        print(f"Received ALL_FILES_SENT from {site_name}")
        return

    elif data == b"EOF":
        # Finalize the current session for this sender.
        if sender_ip in sessions:
            session = sessions[sender_ip]
            if session["type"] == "file":
                filename = session["filename"]
                file_data = session["data"]
                file_path = os.path.join(received_dir, filename)
                try:
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    print(f"File '{filename}' received successfully from {site_name}")

                    # Copy the file to the appropriate folder based on sender IP.
                    if sender_ip == fm1_ip:
                        dest = os.path.join(fm1_dir, filename)
                    elif sender_ip == fm2_ip:
                        dest = os.path.join(fm2_dir, filename)
                    elif sender_ip == fm3_ip:
                        dest = os.path.join(fm3_dir, filename)
                    else:
                        dest = None

                    if dest:
                        shutil.copy(file_path, dest)
                except Exception as e:
                    print(f"Error writing file '{filename}' from {site_name}: {e}")

            elif session["type"] == "hash_log":
                hash_log_data = session["data"]
                timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
                # Create a hash log filename based on the sender's site.
                if sender_ip == fm1_ip:
                    hash_log_filename = f"FM1_received_hash_log_{timestamp}.json"
                elif sender_ip == fm2_ip:
                    hash_log_filename = f"FM2_received_hash_log_{timestamp}.json"
                elif sender_ip == fm3_ip:
                    hash_log_filename = f"FM3_received_hash_log_{timestamp}.json"
                else:
                    hash_log_filename = f"{sender_ip}_received_hash_log_{timestamp}.json"
                hash_log_path = os.path.join(hashlog_dir, hash_log_filename)
                try:
                    hash_log_text = hash_log_data.decode('utf-8')
                    with open(hash_log_path, 'w') as log_file:
                        log_file.write(hash_log_text)
                    print(f"Hash log received successfully from {site_name}")
                    verify_files(received_dir, hash_log_path, corrupted_dir)
                except Exception as e:
                    print(f"Error processing hash log from {site_name}: {e}")
            else:
                print(f"Unknown session type from {site_name}")

            # Remove the session after finalizing.
            del sessions[sender_ip]
        else:
            print(f"Received EOF from {site_name} with no active session.")
        return

    else:
        # This is a data chunk; if there's an active session, append the data.
        if sender_ip in sessions:
            sessions[sender_ip]["data"].extend(data)
        else:
            print(f"Received data from {site_name} with no active session. Ignoring.")

# === Main Receiving Loop ===
def receive_files_and_hash_logs():
    """Main loop to receive UDP packets and process them."""
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((listen_ip, listen_port))
        print(f"Listening on {listen_ip}:{listen_port}")
    except OSError as e:
        print(f"Error binding to {listen_ip}:{listen_port}: {e}")
        return

    try:
        while True:
            try:
                data, addr = udp_socket.recvfrom(chunk_size)
            except socket.error as e:
                print(f"Socket error: {e}")
                continue

            process_packet(data, addr)

    except KeyboardInterrupt:
        print("Receiver is shutting down.")
    finally:
        udp_socket.close()

if __name__ == "__main__":
    receive_files_and_hash_logs()
