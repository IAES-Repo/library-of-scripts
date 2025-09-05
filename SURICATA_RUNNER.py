"""
Suricata Runner Script
Monitors a directory for new files and automatically runs Suricata analysis on them.

Author: Jordan Lanham
Date: 2025-8-1
"""

import subprocess
import os
import time

WATCH_DIRECTORY = "/path/to/watch"

def watch_directory(WATCH_DIRECTORY):
    """
    Watch a directory for changes and return a list of changed files.
    """
    changed_files = []
    # Get initial snapshot of files in directory
    initial_files = set(os.listdir(WATCH_DIRECTORY))
    time.sleep(600)  # Check every 10 minutes
    # Get current files after delay
    current_files = set(os.listdir(WATCH_DIRECTORY))
    # Find newly added files
    changed_files = list(current_files - initial_files)
    return changed_files

def suricata(changed_files):
    """
    Run Suricata on the specified directory.
    """
    for file in changed_files:
        command = ["suricata", "-r", WATCH_DIRECTORY + "/" + file]
        try:
            subprocess.run(command, check=True)
            print(f"Suricata analysis completed for {file}")
            time.sleep(30)  # Wait for 30 seconds before next run
        except subprocess.CalledProcessError as e:
            print(f"Error running Suricata: {e}")

def main():
    """
    Main function to watch the directory and run Suricata on changed files.
    """
    print(f"Watching directory: {WATCH_DIRECTORY}")
    while True:
        changed_files = watch_directory(WATCH_DIRECTORY)
        if changed_files:
            print(f"Changed files detected: {changed_files}")
            suricata(changed_files)
        time.sleep(1)  # Sleep before checking again

if __name__ == "__main__":
    main()