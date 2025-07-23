"""
SCP PCAP File Upload Script v1.0

This script monitors a directory for PCAP files with a specific prefix
and automatically uploads them to a remote server via SCP.

Author: Jordan Lanham
Date: 2025-7-23
"""

import os
import subprocess

# SCP connection configuration
SCP_HOST = "10.129.47.227"  # Remote server IP address
SCP_USER = "IAES"           # SSH username for remote server
SCP_PATH = "/mnt/nas"       # Destination path on remote server
SCP_KEY = "/home/iaes/.ssh/Onix_rsa"  # Path to SSH private key

# File monitoring configuration
WATCH_DIRECTORY = "/PCAP"   # Local directory to monitor for files
FILE_PREFIX = "x_"          # Only process files starting with this prefix
DELETE_AFTER_UPLOAD = True  # Whether to delete files after successful upload

def watch_directory():
    """
    Scan the watch directory for files matching the specified prefix.
    Upload matching files and optionally delete them after upload.
    """
    # Get all files in the watch directory
    for i in os.listdir(WATCH_DIRECTORY):
        # Only process files that start with the specified prefix
        if i.startswith(FILE_PREFIX):
            file_path = os.path.join(WATCH_DIRECTORY, i)
            upload_file(file_path)
            
            # Delete the file after upload if configured to do so
            if DELETE_AFTER_UPLOAD:
                os.remove(file_path)

def upload_file(file_path):
    """
    Upload a file to the remote server using SCP with SSH key authentication.
    
    Args:
        file_path (str): Full path to the file to be uploaded
    """
    print(f"Uploading {file_path} to SCP server {SCP_HOST} as user {SCP_USER}")
    
    # Execute SCP command with SSH key authentication
    subprocess.run(["scp", "-i", SCP_KEY, file_path, f"{SCP_USER}@{SCP_HOST}:{SCP_PATH}"])
    
    print(f"Finished uploading {file_path}")

if __name__ == "__main__":
    print("Watching directory for new files...")
    watch_directory()