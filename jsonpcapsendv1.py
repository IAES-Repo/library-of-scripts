"""
UDP JSON & PCAP File Sender with Hash Verification

This script monitors a specified directory for JSON/PCAP files and, upon receiving a signal,
sends these files over UDP to a defined receiver. Each JSON/PCAP file is transmitted in chunks,
with an EOF signal sent at the end to indicate completion. A hash log of all files is generated
and sent afterward for integrity verification. After transmission, all targeted files are deleted
from the directory.

Functions: 
- handle_signal: Sets a flag to start the file sending process upon receiving a signal.
- send_file: Sends a JSON/PCAP file in chunks over UDP and signals completion with an EOF.
- generate_file_hash: Generates a SHA-256 hash for a JSON/PCAP file for integrity checks.
- create_hash_log: Compiles hashes for all targeted files in the directory and saves to a log file.
- send_hash_log: Sends the hash log over UDP, chunked to fit UDP packet size, with an EOF signal at the end.
- delete_json_files: Deletes targeted files from the directory once processed.
- process_all_files_and_hashes: Orchestrates the file and hash log sending process after the trigger signal.
"""

import os
import socket
import time
import hashlib
import json
import signal

# path to monitor for JSON files
JSONdir = "./REPORTS"

# Path to store JSON hashes
JSONhash = "./HASH/hash_log.json"

# Path to monitor for PCAP files
PCAPdir = "./PCAP"

# Path to store PCAP hashes
PCAPhash = "./HASH/pcap_hash_log.json"

# Reciever IP and Port
recieverIP = "192.168.1.99"
recieverPort = 60000

# Flag for JSON access based on signal
JSONAccess = False

# Flag for PCAP access based on signal
PCAPAccess = False

# Signal handler (SIGUSR1)
def handle_json_signal(signum, frame):
    global JSONAccess
    print("Received SIGUSR1: Started JSON processing.")
    JSONAccess = True

def handle_pcap_signal(signum, frame):
    global PCAPAccess
    print("Received SIGUSR2: Started PCAP processing.")
    PCAPAccess = True
    
# Signal setup for SIGUSR1 & SIGUSR2
signal.signal(signal.SIGUSR1, handle_json_signal)
signal.signal(signal.SIGUSR2, handle_pcap_signal)

# Function to send a files via UDP
def send_file(file_path, recieverIP, recieverPort):
    chunk_size = 1024
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    filename = os.path.basename(file_path)
    # Send filename before the file data
    udp_socket.sendto(f"FILENAME:{filename}".encode(), (recieverIP, recieverPort))
    time.sleep(0.001) #Delay for filename creation

    # Open the file in binary mode
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            udp_socket.sendto(chunk, (recieverIP, recieverPort))
            time.sleep(0.001) # Delay to prevent flooding

    # Send EOF message to signal end of file
    udp_socket.sendto(b"EOF", (recieverIP, recieverPort))
    print(f"File '{filename}' sent via UDP")

    udp_socket.close()

# Function to generate a hash for a file
def generate_file_hash(file_path):
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(4096)
            if not chunk:
                break
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

# Function to create the hash log for all JSON / PCAP files
def create_hash_log(directory, log_file_path, extensions=['.json', '.pcap']):
    file_hashes = []
    for filename in os.listdir(directory):
        if any(filename.endswith(ext) for ext in extensions):
            file_path = os.path.join(directory, filename)
            file_hash = generate_file_hash(file_path)
            file_hashes.append({"filename": filename, "hash": file_hash})
            print(f"Generated hash for '{filename}': {file_hash}")

    # Write the hashes to the log file
    with open(log_file_path, 'w') as log_file:
        json.dump(file_hashes, log_file, indent=4)

    print(f"Hash log saved to '{log_file_path}'")

# Function to send the hash log via UDP
def send_hash_log(log_file_path, recieverIP, recieverPort):
    chunk_size = 1024
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send a start message to indicate the start of the hash log
    udp_socket.sendto(b"HASH_LOG_START", (recieverIP, recieverPort))
    time.sleep(0.01)  # Sleep

    # Read the hash log and send it in chunks via UDP
    with open(log_file_path, 'r') as log_file:
        log_data = log_file.read().encode()  # Convert the log data to bytes

        # Split the log data into chunks and send each chunk
        for i in range(0, len(log_data), chunk_size):
            udp_socket.sendto(log_data[i:i + chunk_size], (recieverIP, recieverPort))
            time.sleep(0.001)

    # Send EOF signal after the entire log file has been sent
    udp_socket.sendto(b"EOF", (recieverIP, recieverPort))
    print("Hash log sent via UDP")

    udp_socket.close()

    # Function to delete targeted files after processing
def delete_files(directory, extensions=['.json', '.pcap']):
    for filename in os.listdir(directory):
        if any (filename.endswith(ext) for ext in extensions):
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

def process_json_files_and_hashes():
    target_files = [f for f in os.listdir(JSONdir) if f.endswith('.json')]
    if target_files:
        create_hash_log(JSONdir, JSONhash, extensions=['.json'])
        for filename in target_files:
            file_path = os.path.join(JSONdir, filename)
            send_file(file_path, recieverIP, recieverPort)

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(b"ALL_FILES_SENT", (recieverIP, recieverPort))
        print("Sent ALL_FILES_SENT signal for JSON files")
        udp_socket.close()

        time.sleep(0.1)

        send_hash_log(JSONhash, recieverIP, recieverPort)
        delete_files(JSONdir, extensions=['.json'])
    else:
        print("No JSON files to process.")

def process_pcap_files_and_hashes():
    target_files = [f for f in os.listdir(PCAPdir) if f.endswith('.pcap')]
    if target_files:
        create_hash_log(PCAPdir, PCAPhash, extensions=['.pcap'])
        for filename in target_files:
            file_path = os.path.join(PCAPdir, filename)
            send_file(file_path, recieverIP, recieverPort)

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(b"ALL_FILES_SENT", (recieverIP, recieverPort))
        print("Sent ALL_FILES_SENT signal for PCAP files")
        udp_socket.close()

        time.sleep(0.1)

        send_hash_log(PCAPhash, recieverIP, recieverPort)
        delete_files(PCAPdir, extensions=['.pcap'])
    else:
        print("No PCAP files to process.")
        
if __name__ == "__main__":
    print(f"Process {os.getpid()} waiting for signal to start...")
    while True:
        if JSONAccess:
            process_json_files_and_hashes()
            JSONAccess = False
        if PCAPAccess:
            process_pcap_files_and_hashes()
            PCAPAccess = False
        time.sleep(1)




        
        
        
