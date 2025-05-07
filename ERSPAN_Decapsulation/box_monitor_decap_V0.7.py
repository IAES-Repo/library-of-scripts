import os
import time
import threading
import re
from datetime import datetime
from io import BytesIO

'''
Third party libs required
pip install "boxsdk[jwt]" boxsdk watchdog 
'''
from boxsdk import JWTAuth, Client
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

VERSION = "0.7"

class StatusMonitor:
    def __init__(self):
        self.files_processed = 0
        self.files_failed = 0
        self.last_upload_time = None
        self.start_time = datetime.now()
        self.upload_sizes = []  # Track last 10 upload sizes
        self.lock = threading.Lock()

    def record_upload(self, size, success=True):
        with self.lock:
            if success:
                self.files_processed += 1
                self.last_upload_time = datetime.now()
                self.upload_sizes.append(size)
                # Keep only last 10 uploads
                if len(self.upload_sizes) > 10:
                    self.upload_sizes.pop(0)
            else:
                self.files_failed += 1

    def get_status_report(self):
        with self.lock:
            current_time = datetime.now()
            uptime = current_time - self.start_time
            time_since_last_upload = "Never" if not self.last_upload_time else \
                str(current_time - self.last_upload_time).split('.')[0]

            avg_size = sum(self.upload_sizes) / len(self.upload_sizes) if self.upload_sizes else 0

            return f"""
=== IAES DECAP WatchTower Status Report ===
Version: {VERSION}
Timestamp: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
Uptime: {str(uptime).split('.')[0]}
Files Processed: {self.files_processed}
Files Failed: {self.files_failed}
Last Upload: {time_since_last_upload} ago
Average Upload Size: {avg_size/1024:.2f} KB
Success Rate: {(self.files_processed/(self.files_processed + self.files_failed)*100) if (self.files_processed + self.files_failed) > 0 else 0:.1f}%
====================================="""

class BoxUploader:
    def __init__(self, config, status_monitor):
        self.status_monitor = status_monitor
        auth = JWTAuth(
            client_id=config['clientID'],
            client_secret=config['clientSecret'],
            enterprise_id=config['enterpriseID'],
            jwt_key_id=config['publicKeyID'],
            rsa_private_key_data=config['privateKey'],
            rsa_private_key_passphrase=config['passphrase']
        )
        self.client = Client(auth)
        self.folder_mapping = {
            '/home/onix/DECAP/REPORTS': config['reportsFolderID']
        }
        # Cache for daily folders to minimize API calls
        self.daily_folder_cache = {}

    def extract_date_from_filename(self, filename):
        """
        Extract date from filenames like:
        2025-04-04-10-32-33-jsonALLConnections.json
        
        Returns: YYYY-MM-DD format string or None if pattern doesn't match
        """
        # Pattern to match YYYY-MM-DD at the start of the filename
        date_pattern = r'^(\d{4}-\d{2}-\d{2})'
        match = re.match(date_pattern, filename)
        
        if match:
            return match.group(1)
        return None

    def get_or_create_daily_folder(self, parent_folder_id, date_str):
        """
        Gets or creates a folder for the specified date within the parent folder.
        Returns the folder object.
        """
        cache_key = f"{parent_folder_id}_{date_str}"

        # Check cache first
        if cache_key in self.daily_folder_cache:
            return self.daily_folder_cache[cache_key]

        parent_folder = self.client.folder(parent_folder_id)

        # Search for existing folder
        items = parent_folder.get_items()
        for item in items:
            if item.type == 'folder' and item.name == date_str:
                self.daily_folder_cache[cache_key] = item
                return item

        # Create new folder if it doesn't exist
        new_folder = parent_folder.create_subfolder(date_str)
        self.daily_folder_cache[cache_key] = new_folder
        print(f"Created new folder for date: {date_str}")
        return new_folder

    def is_file_ready(self, file_path, timeout=30, check_interval=0.5):
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                if not os.path.exists(file_path):
                    return False

                current_size = os.path.getsize(file_path)
                if current_size == 0:
                    time.sleep(check_interval)
                    continue

                if current_size == last_size and current_size > 0:
                    return True

                last_size = current_size
                time.sleep(check_interval)

            except (OSError, IOError) as e:
                print(f"Error checking file {file_path}: {str(e)}")
                return False

        return False

    def upload_file(self, file_path):
        file_name = os.path.basename(file_path)
        directory = os.path.dirname(file_path)

        if not self.is_file_ready(file_path):
            print(f"File {file_name} not ready for upload after timeout")
            self.status_monitor.record_upload(0, success=False)
            return

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                print(f"Warning: File {file_name} has zero size, skipping upload")
                self.status_monitor.record_upload(0, success=False)
                return

            # Get the parent folder ID from the mapping
            parent_folder_id = self.folder_mapping[directory]
            
            # Extract date from filename or use current date as fallback
            file_date = self.extract_date_from_filename(file_name)
            if not file_date:
                file_date = datetime.now().strftime('%Y-%m-%d')
                print(f"Could not extract date from filename {file_name}, using current date: {file_date}")
            else:
                print(f"Extracted date {file_date} from filename {file_name}")
                
            # Create or get folder based on file date
            target_folder = self.get_or_create_daily_folder(parent_folder_id, file_date)

            print(f"Attempting to upload {file_name} (size: {file_size} bytes) to folder {target_folder.name}")

            try:
                with open(file_path, 'rb') as file_content:
                    file_data = file_content.read()
                    if len(file_data) == 0:
                        print(f"Warning: File {file_name} read as empty, skipping upload")
                        self.status_monitor.record_upload(0, success=False)
                        return

                    file_stream = BytesIO(file_data)
                    uploaded_file = target_folder.upload_stream(
                        file_stream=file_stream,
                        file_name=file_name
                    )

                if uploaded_file.size == 0:
                    print(f"Warning: Uploaded file {file_name} has zero size on Box")
                    self.status_monitor.record_upload(0, success=False)
                    return

                print(f"Successfully uploaded {file_name} ({uploaded_file.size} bytes) to Box folder {target_folder.name}")
                self.status_monitor.record_upload(file_size, success=True)

                #os.remove(file_path)
                #print(f"Deleted local file {file_name}")

            except Exception as folder_error:
                print(f"Folder access error details: {str(folder_error)}")
                self.status_monitor.record_upload(0, success=False)
                raise

        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            print(f"File path: {file_path}")
            print(f"Exception type: {type(e).__name__}")
            self.status_monitor.record_upload(0, success=False)

class FileHandler(FileSystemEventHandler):
    def __init__(self, uploader):
        self.uploader = uploader

    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            self.uploader.upload_file(event.src_path)

def print_status(status_monitor):
    while True:
        print(status_monitor.get_status_report())
        time.sleep(600)  # 10 minutes

def monitor_directories(paths_to_watch, uploader):
    observer = Observer()
    for path in paths_to_watch:
        event_handler = FileHandler(uploader)
        observer.schedule(event_handler, path, recursive=False)
        print(f"Monitoring directory: {path}")

    observer.start()

if __name__ == "__main__":
    print("\n=== DECAP IAES WatchTower ===")
    print(f"Version: {VERSION}")
    print("=====================\n")

    config = {
        'clientID': '',
        'clientSecret': '',
        'enterpriseID': '',
        'publicKeyID': '',
        'privateKey': '''''',
        'passphrase': '',
        'reportsFolderID': ''

    }

    paths_to_watch = [
        '/home/onix/DECAP/REPORTS'
    ]

    status_monitor = StatusMonitor()
    uploader = BoxUploader(config, status_monitor)

    # Start status printing thread
    status_thread = threading.Thread(target=print_status, args=(status_monitor,), daemon=True)
    status_thread.start()

    # Start directory monitoring
    monitor_directories(paths_to_watch, uploader)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down IAES WatchTower...")
