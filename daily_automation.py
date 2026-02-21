#!/usr/bin/env python3
"""
أتمتة يومية: تحميل، دمج، ونشر على يوتيوب.
"""
import os
import sys
import subprocess
import glob
from datetime import date, datetime

# Fix Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
MERGED_DIR = "merged"


def _find_client_secret():
    """Find client_secret.json - check SCRIPT_DIR and parent (for EXE in dist/)."""
    for d in (SCRIPT_DIR, PARENT_DIR):
        for name in ("client_secret.json", "client_secrets.json"):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


def run_script(script_name, *args):
    """Run a Python script."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + list(args)
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.returncode == 0, result.stdout, result.stderr


def load_title_template():
    """Load title template from config."""
    config_file = os.path.join(SCRIPT_DIR, "gui_config.json")
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("title_template", "ستوريات {username} | يوم {date} | الجزء {part}")
        except:
            pass
    return "ستوريات {username} | يوم {date} | الجزء {part}"

def upload_to_youtube(username, date_str, privacy="private"):
    """Upload merged videos to YouTube with custom titles."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("Error: Install YouTube API packages: pip install google-api-python-client google-auth-oauthlib")
        return False
    
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    client_path = _find_client_secret()
    if not client_path:
        print("Error: client_secret.json not found. Get it from Google Cloud Console.")
        return False

    token_path = os.path.join(os.path.dirname(client_path), "token.json")
    merged_folder = os.path.join(SCRIPT_DIR, "stories", username, date_str, MERGED_DIR)
    if not os.path.isdir(merged_folder):
        print(f"Merged folder not found: {merged_folder}")
        return False
    
    videos = sorted([v for v in glob.glob(os.path.join(merged_folder, "merged_*.mp4")) if "merged_all" not in v])
    if not videos:
        print(f"No merged shorts found in: {merged_folder}")
        return False
    
    # Get display name
    display_name = username.replace("_", " ").title()
    
    # Format date: 15-02-2026
    date_formatted = date_str.replace("-", "-")
    
    # Load title template
    title_template = load_title_template()
    
    # Authenticate
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Opening browser for YouTube authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    
    youtube = build("youtube", "v3", credentials=creds)
    
    uploaded = 0
    for idx, path in enumerate(videos, start=1):
        name = os.path.basename(path)
        # Use custom title template
        title = title_template.format(username=display_name, date=date_formatted, part=idx)
        description = f"ستوريات {display_name} من Snapchat Stories\n\n#{display_name.replace(' ', '')} #Shorts #Snapchat"
        
        print(f"Uploading part {idx}/{len(videos)}: {name} ...")
        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["Shorts", "Snapchat", display_name.replace(" ", "")],
                    "categoryId": "22",
                },
                "status": {"privacyStatus": privacy},
            }
            media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = request.execute()
            vid_id = response.get("id")
            print(f"  ✓ Uploaded: https://www.youtube.com/watch?v={vid_id}")
            uploaded += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\nUploaded {uploaded}/{len(videos)} videos.")
    if uploaded > 0 and uploaded == len(videos):
        try:
            import shutil
            archive_dir = os.path.join(merged_folder, "uploaded_youtube")
            os.makedirs(archive_dir, exist_ok=True)
            for path in videos:
                if os.path.exists(path):
                    shutil.move(path, os.path.join(archive_dir, os.path.basename(path)))
            print(f"  ✓ Moved uploaded files to: {archive_dir}")
        except Exception as e:
            print(f"  ✗ Could not move files: {e}")
    return uploaded > 0


def process_account(username, auto_upload=True, privacy="private", do_merge=True):
    """Process one account: download, optionally merge, optionally upload."""
    date_str = date.today().strftime("%Y-%m-%d")
    steps = 2 if do_merge else 1
    if auto_upload:
        steps += 1

    print(f"\n{'='*60}")
    print(f"Processing: {username} ({date_str})")
    print(f"{'='*60}")

    # 1. Download stories
    step = 1
    print(f"\n[{step}/{steps}] Downloading stories...")
    success, stdout, stderr = run_script("SnapScrap.py", username)
    if not success:
        print(f"Download failed: {stderr}")
        return False
    print("✓ Download complete")

    # 2. Merge videos (if enabled)
    if do_merge:
        step += 1
        print(f"\n[{step}/{steps}] Merging videos...")
        success, stdout, stderr = run_script("merge_videos.py", username, date_str)
        if not success:
            print(f"Merge failed: {stderr}")
            return False
        print("✓ Merge complete")
    else:
        print("\nMerge skipped")

    # 3. Upload to YouTube (if enabled)
    if auto_upload:
        step += 1
        print(f"\n[{step}/{steps}] Uploading to YouTube...")
        success = upload_to_youtube(username, date_str, privacy)
        if success:
            print("✓ Upload complete")
        else:
            print("✗ Upload failed or skipped")
    else:
        print("\nUpload skipped (auto_upload=False)")
    
    print(f"\n✓ Completed: {username}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python daily_automation.py <username> [--no-upload] [privacy]")
        print("  privacy: private (default), public, or unlisted")
        print("Example: python daily_automation.py dary_1256")
        print("         python daily_automation.py dary_1256 --no-upload")
        print("         python daily_automation.py dary_1256 public")
        sys.exit(1)
    
    username = sys.argv[1]
    auto_upload = "--no-upload" not in sys.argv
    privacy = "private"
    
    for arg in sys.argv[2:]:
        if arg in ("private", "public", "unlisted"):
            privacy = arg
    
    success = process_account(username, auto_upload, privacy)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
