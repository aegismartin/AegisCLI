import json
import os

LOG_DIR = os.path.expanduser("~/.aegiscli/logs")
os.makedirs(LOG_DIR, exist_ok=True)


def dump(tool: str, target: str, data: dict, elapsed: int) -> dict:
    """
    Builds and returns the standard AegisCLI envelope dict.
    Does NOT write to disk — that's logger's job.
    """
    from datetime import datetime
    return {
        "tool": tool,
        "target": target,
        "timestamp": datetime.now().isoformat(),
        "elapsed":elapsed,
        "data": data
    }


def load(path: str) -> dict:
    """
    Reads an AegisCLI JSON envelope from disk.
    Used by chaining tools to consume a previous tool's output.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)