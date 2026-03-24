"""
ELI Watcher — checks GitHub Issues and fires Windows toast notifications.
Runs on Windows Task Scheduler at startup / on a schedule.

Setup:
  1. pip install requests winotify
  2. Edit CONFIG below with your details
  3. Add to Task Scheduler (see home-setup guide)
"""

import requests
import json
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════
# CONFIG — edit these for your machine
# ═══════════════════════════════════════════════════
MODE = "work"  # "work" or "private" — set per machine

WORK_REPO = "grantgrantgrantgrantgrant/eli"
WORK_PAT = "YOUR_WORK_PAT_HERE"

PRIVATE_REPO = "YOUR_PERSONAL_USERNAME/eli-private"
PRIVATE_PAT = "YOUR_PRIVATE_PAT_HERE"

# ═══════════════════════════════════════════════════
# Don't edit below this line
# ═══════════════════════════════════════════════════

def get_config():
    if MODE == "work":
        return WORK_REPO, WORK_PAT
    else:
        return PRIVATE_REPO, PRIVATE_PAT

def get_seen_file():
    """Track which issues we've already notified about."""
    return Path(os.path.expanduser("~")) / ".eli-watcher-seen.json"

def load_seen():
    f = get_seen_file()
    if f.exists():
        return set(json.loads(f.read_text()))
    return set()

def save_seen(seen):
    f = get_seen_file()
    f.write_text(json.dumps(list(seen)))

def fetch_open_issues(repo, pat):
    """Fetch open issues from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/issues?state=open&labels=&per_page=50"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        # Filter out pull requests (GitHub API returns PRs as issues too)
        return [i for i in r.json() if "pull_request" not in i]
    except Exception as e:
        print(f"Error fetching issues: {e}")
        return []

def send_notification(title, message, url=None):
    """Send a Windows toast notification."""
    try:
        from winotify import Notification, audio

        toast = Notification(
            app_id="ELI",
            title=title,
            msg=message,
            duration="long"
        )
        toast.set_audio(audio.Default, loop=False)

        if url:
            toast.add_actions(label="Open in browser", launch=url)

        toast.show()
    except ImportError:
        # Fallback if winotify not installed
        print(f"NOTIFICATION: {title} — {message}")

def main():
    repo, pat = get_config()

    if "YOUR_" in pat:
        print("ERROR: You haven't set your PAT in the CONFIG section.")
        print("Edit eli-watcher.py and replace YOUR_*_PAT_HERE with your actual token.")
        sys.exit(1)

    # Fetch open issues
    issues = fetch_open_issues(repo, pat)

    if not issues:
        return  # Nothing to do, stay silent

    # Check which ones are new (not yet notified)
    seen = load_seen()
    new_issues = [i for i in issues if i["number"] not in seen]

    if not new_issues:
        return  # All issues already notified, stay silent

    # Build notification
    count = len(new_issues)
    pipeline = "Work" if MODE == "work" else "Private"
    icon = "📋" if MODE == "work" else "🔒"

    if count == 1:
        title = f"{icon} ELI: 1 new {pipeline.lower()} request"
        message = new_issues[0]["title"]
    else:
        title = f"{icon} ELI: {count} new {pipeline.lower()} requests"
        titles = [i["title"] for i in new_issues[:3]]
        message = " • ".join(titles)
        if count > 3:
            message += f" (+{count - 3} more)"

    # URL to the issues list
    issues_url = f"https://github.com/{repo}/issues"

    send_notification(title, message, issues_url)

    # Mark all open issues as seen (not just new ones)
    all_numbers = {i["number"] for i in issues}
    save_seen(all_numbers)

if __name__ == "__main__":
    main()
