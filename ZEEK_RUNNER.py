"""
Zeek Runner Script
Monitors a directory for new files and automatically runs Zeek analysis on them.

Author: Jordan Lanham
Date: 2025-8-1
"""

import subprocess
import os
import time

# Directory to monitor for new files
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

def zeek(changed_files):
    """
    Run Zeek on the specified directory.
    """
    # Process each new file with Zeek
    for file in changed_files:
        # Build Zeek command with -r flag to read from file
        command = ["zeek", "-r", WATCH_DIRECTORY + "/" + file]
        try:
            # Execute Zeek analysis
            subprocess.run(command, check=True)
            print(f"Zeek analysis completed for {file}")
            time.sleep(30)  # Wait for 30 seconds before next run
        except subprocess.CalledProcessError as e:
            # Handle any errors during Zeek execution
            print(f"Error running Zeek: {e}")

def main():
    """
    Main function to watch the directory and run Zeek on changed files.
    """
    print(f"Watching directory: {WATCH_DIRECTORY}")
    # Continuous monitoring loop
    while True:
        # Check for new files in the directory
        changed_files = watch_directory(WATCH_DIRECTORY)
        if changed_files:
            print(f"Changed files detected: {changed_files}")
            # Run Zeek analysis on new files
            zeek(changed_files)
        time.sleep(1)  # Sleep before checking again