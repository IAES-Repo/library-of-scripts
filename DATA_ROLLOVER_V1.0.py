"""
Data Rollover Script v1.0
Monitors directory for files with specific prefix, renames them with timestamps,
and deletes files older than 2 days.

Author: Jordan Lanham
Date: 2025-7-25
"""

import os
import datetime
import time

# Directory to monitor for files
WATCH_DIRECTORY = "/mnt/nas"  
# Only process files starting with this prefix
FILE_PREFIX = "x_"          

def rename_files():
    """Rename files with x_ prefix to timestamp-based names with .pcap extension"""
    # Scan all files in the watch directory
    for filename in os.listdir(WATCH_DIRECTORY):
        # Only process files that start with the specified prefix
        if filename.startswith(FILE_PREFIX):
            # Generate current timestamp for new filename
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            new_name = f"{timestamp}.pcap"
            # Create full file paths
            old_path = os.path.join(WATCH_DIRECTORY, filename)
            new_path = os.path.join(WATCH_DIRECTORY, new_name)
            
            # Perform the rename operation
            os.rename(old_path, new_path)
            print(f"Renamed {filename} to {new_name}")
            # Brief pause between file operations
            time.sleep(5)

def delete_old_files():
    """Remove files older than 2 days to prevent disk space issues"""
    # Check each file in the directory
    for filename in os.listdir(WATCH_DIRECTORY):
        file_path = os.path.join(WATCH_DIRECTORY, filename)
        # Only process actual files, not directories
        if os.path.isfile(file_path):
            # Calculate file age based on modification time
            file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            # Delete files older than 2 days
            if file_age.days > 182: 
                os.remove(file_path)
                print(f"Deleted old file: {filename}")

# Main execution when script is run directly
if __name__ == "__main__":
    print("Starting data rollover process...")
    # Continuous monitoring loop
    while True:
        rename_files()      # Process new files with x_ prefix
        delete_old_files()  # Clean up old files
        time.sleep(60)      # Wait 1 minute before next check