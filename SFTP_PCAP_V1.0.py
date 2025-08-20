"""
SFTP File Upload Script v1.0

This script monitors a directory for PCAP files with a specific prefix
and automatically uploads them to a remote server via SFTP.

Author: Jordan Lanham
Date: 2025-8-20
"""

import os
import subprocess

# SFTP connection configuration
SFTP_HOST = "IP_ADDRESS"  # Remote server IP address
SFTP_USER = "USER"           # SSH username for remote server
SFTP_PATH = "SFTP_PATH"       # Destination path on remote server
SFTP_KEY = "KEY_PATH"  # Path to SSH private key

# File monitoring configuration
WATCH_DIRECTORY = "/home/iaes/PCAP"   # Local directory to monitor for files
FILE_PREFIX = "x_"          # Only process files starting with this prefix
DELETE_AFTER_UPLOAD = True  # Whether to delete files after successful upload

def watch_directory():
    """
    Scan the watch directory for files matching the specified prefix.
    Upload matching files and optionally delete them after upload.
    """
    while True:
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
    print(f"Uploading {file_path} to SFTP server {SFTP_HOST} as user {SFTP_USER}")

    # Execute SFTP command with SSH key authentication
    sftp_command = f"echo 'put {file_path} {SFTP_PATH}' | sftp -i {SFTP_KEY} {SFTP_USER}@{SFTP_HOST}"
    subprocess.run(sftp_command, shell=True)

    print(f"Finished uploading {file_path}")

if __name__ == "__main__":
    print("Watching directory for new files...")
    watch_directory()