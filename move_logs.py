import os
import shutil
from datetime import datetime

logs="logs"
logs_backup="logs_backup"

def move_and_timestamp_files(logs, logs_backup):
    if not os.path.exists(logs):
        raise FileNotFoundError(f"Source directory does not exist: {logs}")

    os.makedirs(logs_backup, exist_ok=True)

    for filename in os.listdir(logs):
        src_path = os.path.join(logs, filename)

        if os.path.isdir(src_path):
            continue

        name, ext = os.path.splitext(filename)
        timestamp = datetime.utcnow().strftime("%Y_%m_%d_%H:%M:%S")
        new_name = f"{name}_{timestamp}{ext}"
        dest_path = os.path.join(logs_backup, new_name)
        shutil.move(src_path, dest_path)
        
if __name__ == "__main__":
    move_and_timestamp_files("logs", "logs_backup")
