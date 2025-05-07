"""
UDP JSON File Sender with Hash Verification

This script monitors a specified directory for JSON files and, upon receiving a signal,
sends these files over UDP to a defined receiver. Each JSON file is transmitted in chunks,
with an EOF signal sent at the end to indicate completion. A hash log of all files is generated
and sent afterward for integrity verification. After transmission, all JSON files are deleted
from the directory.

Functions:
- handle_signal: Sets a flag to start the file sending process upon receiving a signal.
- send_file: Sends a JSON file in chunks over UDP and signals completion with an EOF.
- generate_file_hash: Generates a SHA-256 hash for a JSON file for integrity checks.
- create_hash_log: Compiles hashes for all JSON files in the directory and saves to a log file.
- send_hash_log: Sends the hash log over UDP, chunked to fit UDP packet size, with an EOF signal at the end.
- delete_json_files: Deletes JSON files from the directory once processed.
- process_all_files_and_hashes: Orchestrates the file and hash log sending process after the trigger signal.
"""

import os
import socket
import time
import hashlib
import json
import signal

# Path to monitor for JSON files
directoryToWatch = "./REPORTS"
# Path to store the hash log
hashlogFile = "./HASH/hash_log.json"

# Define the receiver IP and port
receiverIP = "192.168.1.X"
receiverPort = 60000

# Flag for JSON access based on signal
JSONAccess = False

# Signal handler to handle the JSON signal (SIGUSR1)
def handle_signal(signum, frame):
    global JSONAccess
    print("Received signal to start sending files.")
    JSONAccess = True

# Set up signal handling for SIGUSR1
signal.signal(signal.SIGUSR1, handle_signal)

# Function to send a file via UDP
def send_file(file_path, receiverIP, receiverPort):
    chunk_size = 1024  # Define the chunk size (in bytes)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    filename = os.path.basename(file_path)
    # Send the filename before the file data
    udp_socket.sendto(f"FILENAME:{filename}".encode(), (receiverIP, receiverPort))
    time.sleep(0.001)  # Short delay to ensure the receiver processes the filename

    # Open the file in binary mode
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            udp_socket.sendto(chunk, (receiverIP, receiverPort))
            time.sleep(0.001)  # Sleep to avoid flooding

    # Send EOF message to signal the end of the file
    udp_socket.sendto(b"EOF", (receiverIP, receiverPort))
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

# Function to create the hash log for all JSON files
def create_hash_log(directory, log_file_path):
    file_hashes = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            file_hash = generate_file_hash(file_path)
            file_hashes.append({"filename": filename, "hash": file_hash})
            print(f"Generated hash for '{filename}': {file_hash}")

    # Write the hashes to the log file
    with open(log_file_path, 'w') as log_file:
        json.dump(file_hashes, log_file, indent=4)

    print(f"Hash log saved to '{log_file_path}'")

# Function to send the hash log via UDP
def send_hash_log(log_file_path, receiverIP, receiverPort):
    chunk_size = 1024
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send a start message to indicate the start of the hash log
    udp_socket.sendto(b"HASH_LOG_START", (receiverIP, receiverPort))
    time.sleep(0.01)  # Sleep

    # Read the hash log and send it in chunks via UDP
    with open(log_file_path, 'r') as log_file:
        log_data = log_file.read().encode()  # Convert the log data to bytes

        # Split the log data into chunks and send each chunk
        for i in range(0, len(log_data), chunk_size):
            udp_socket.sendto(log_data[i:i + chunk_size], (receiverIP, receiverPort))
            time.sleep(0.001)

    # Send EOF signal after the entire log file has been sent
    udp_socket.sendto(b"EOF", (receiverIP, receiverPort))
    print("Hash log sent via UDP")

    udp_socket.close()

# Function to delete JSON files after processing
def delete_json_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

# Function to process all files and hashes
def process_all_files_and_hashes():
    json_files = [f for f in os.listdir(directoryToWatch) if f.endswith('.json')]

    if json_files:
        # Step 1: Create the hash log
        create_hash_log(directoryToWatch, hashlogFile)

        # Step 2: Send all JSON files via UDP
        for filename in json_files:
            file_path = os.path.join(directoryToWatch, filename)
            send_file(file_path, receiverIP, receiverPort)

        # Step 3: Send "ALL_FILES_SENT" signal
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(b"ALL_FILES_SENT", (receiverIP, receiverPort))
        print("Sent ALL_FILES_SENT signal")
        udp_socket.close()

        time.sleep(0.1)  # Short delay before sending the hash log

        # Step 4: Send the hash log
        send_hash_log(hashlogFile, receiverIP, receiverPort)

        # Step 5: Delete the JSON files
        delete_json_files(directoryToWatch)
    else:
        print("No JSON files to process.")

if __name__ == "__main__":
    print(f"Process {os.getpid()} waiting for signal to start...")
    while True:
        if JSONAccess:
            process_all_files_and_hashes()
            JSONAccess = False  # Reset the flag to wait for the next signal
        time.sleep(1)
