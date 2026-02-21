"""
تتبع الستوريات المحملة لتجنب التكرار.
"""
import json
import os
from datetime import date

TRACKER_FILE = "downloaded_stories.json"


def load_tracker():
    """Load tracking data."""
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_tracker(data):
    """Save tracking data."""
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_story_key(username, date_str, story_url):
    """Generate unique key for a story."""
    return f"{username}|{date_str}|{story_url}"


def is_downloaded(username, date_str, story_url):
    """Check if story was already downloaded."""
    tracker = load_tracker()
    key = get_story_key(username, date_str, story_url)
    return key in tracker.get("stories", {})


def mark_downloaded(username, date_str, story_url, filename):
    """Mark story as downloaded."""
    tracker = load_tracker()
    if "stories" not in tracker:
        tracker["stories"] = {}
    
    key = get_story_key(username, date_str, story_url)
    tracker["stories"][key] = {
        "username": username,
        "date": date_str,
        "url": story_url,
        "filename": filename,
        "downloaded_at": date.today().strftime("%Y-%m-%d")
    }
    
    save_tracker(tracker)


def get_downloaded_count(username, date_str=None):
    """Get count of downloaded stories for user (optionally for a date)."""
    tracker = load_tracker()
    count = 0
    for key, info in tracker.get("stories", {}).items():
        if info["username"] == username:
            if date_str is None or info["date"] == date_str:
                count += 1
    return count
