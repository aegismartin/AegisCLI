import os
import json
from datetime import datetime

LOG_DIR = os.path.expanduser("~/.aegiscli/logs")
os.makedirs(LOG_DIR, exist_ok=True)

file = None
logging = False

# After teh update 0.4.0a0 logging with ASCII encoding for pretty terminal output was suspended in favour of .json logs.
# This logging variant might be either modified in the future or completely removed

def start_log():
    
    global file, logging
    logging = True
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(LOG_DIR, f"aegiscli_{ts}.log")
    file = open(path, "w", encoding="utf-8")
    file.write(f"[LOG START] {datetime.now()} \n")
    return path
    """
    pass


def log(text):
    global file, logging
    print(text)
    """
    if logging:
        file.write(text + "\n")
    """

def log_json(envelope: dict):
    """
    Writes a structured JSON envelope to disk.
    Only called when --log flag is active — logger owns all disk writes.
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tool_slug = envelope.get("tool", "unknown").replace(".", "_")
    filename = f"aegiscli_{tool_slug}_{ts}.json"
    path = os.path.join(LOG_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2, default=str)

    return path


def stop_log():
    global file, logging
    if file:
        file.close()
        file = None
    logging = False