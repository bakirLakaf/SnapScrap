"""YouTube upload service for SnapScrap web app - multi-channel support."""
import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BASE_DIR / "stories" / "tokens"
MERGED_DIR = "merged"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CONFIG_KEY = "youtube_channels"

def get_user_id():
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.id
    except RuntimeError:
        pass
    except ImportError:
        pass
    return os.environ.get("SNAPSCRAP_USER_ID", "")

def get_user_dir(user_id=None):
    uid = user_id if user_id is not None else get_user_id()
    d = BASE_DIR / "stories" / str(uid) if uid else BASE_DIR / "stories"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_tokens_dir(user_id=None):
    d = get_user_dir(user_id) / "tokens"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _safe_channel_id(channel_id):
    """Make channel ID safe for filename (replace non-alphanumeric)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", channel_id) if channel_id else "default"

def _token_path(channel_id, user_id=None):
    """Get token file path for a channel."""
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return tdir / "token.json"
    return tdir / f"token_{_safe_channel_id(channel_id)}.json"

def get_webapp_config_file(user_id=None):
    return get_user_dir(user_id) / "webapp_config.json"

def load_webapp_config(user_id=None):
    cfg_file = get_webapp_config_file(user_id)
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_webapp_config(config, user_id=None):
    cfg_file = get_webapp_config_file(user_id)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_youtube_channels_config(user_id=None):
    """Get list of connected channels from config."""
    cfg = load_webapp_config(user_id)
    return cfg.get(CONFIG_KEY, [])

def save_youtube_channels(channels, user_id=None):
    """Save connected channels to config."""
    cfg = load_webapp_config(user_id)
    cfg[CONFIG_KEY] = channels
    save_webapp_config(cfg, user_id)


def _migrate_legacy_token():
    """If token.json exists but no channels in config, migrate it."""
    channels = get_youtube_channels_config()
    default_token = get_tokens_dir() / "token.json"
    if channels or not default_token.exists():
        return
    youtube, err = get_youtube_service(channel_id=None)
    if err:
        return
    try:
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if items:
            c = items[0]
            ch_id = c["id"]
            title = c["snippet"].get("title", "YouTube")
            token_path = _token_path(ch_id)
            if token_path != default_token:
                import shutil
                shutil.copy(default_token, token_path)
            save_youtube_channels([{"id": ch_id, "title": title}])
    except Exception:
        pass


def _get_all_tokens_for_channel(channel_id, user_id=None):
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return [tdir / "token.json"]
    base_name = f"token_{_safe_channel_id(channel_id)}"
    tokens = []
    for p in tdir.glob(f"{base_name}*.json"):
        tokens.append(p)
    if not tokens:
        tokens.append(tdir / f"{base_name}.json")
    return sorted(tokens)


def _get_client_secrets():
    secrets = []
    for p in BASE_DIR.glob("client_secret*.json"):
        if p.name == "client_secrets.json":
            continue
        secrets.append(p)
    if not secrets:
        if (BASE_DIR / "client_secrets.json").exists():
            secrets.append(BASE_DIR / "client_secrets.json")
    return sorted(secrets)

def _get_token_for_secret(channel_id, user_id, secret_path):
    secret_name = secret_path.stem
    suffix = secret_name.replace("client_secret", "")
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return tdir / f"token{suffix}.json"
    return tdir / f"token{suffix}_{_safe_channel_id(channel_id)}.json"

def get_youtube_service(channel_id=None, token_path_override=None, client_secret_path=None):
    """Get YouTube API service for a specific channel. Uses provided secret or defaults to client_secret.json"""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")

    client_path = BASE_DIR / "client_secret.json"
    if not client_path.exists():
        client_path = BASE_DIR / "client_secrets.json"

    user_id = get_user_id()
    token_path = token_path_override
    if not token_path:
        token_path = _token_path(channel_id, user_id) if channel_id else None
        if not token_path:
            token_path = get_tokens_dir(user_id) / "token.json"
            if not token_path.exists():
                channels = get_youtube_channels_config(user_id)
                if channels:
                    token_path = _token_path(channels[0].get("id"), user_id)
                if not token_path or not token_path.exists():
                    return None, "No channels connected. Add a channel first (+ إضافة قناة)"

    creds = None
    if token_path and token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_path.exists():
                return None, "Place client_secret.json in project folder (from Google Cloud Console)"
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
            creds = flow.run_local_server(port=0)
        out_path = token_path_override if token_path_override else (_token_path(channel_id, user_id) if channel_id else token_path)
        with open(out_path, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds), None


def get_authorization_url(redirect_uri):
    """Get Google OAuth URL for adding a new channel."""
    flow, err = get_oauth_flow(redirect_uri)
    if err:
        return None, err
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url, state


def get_oauth_flow(redirect_uri):
    """Create OAuth flow for web redirect."""
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return None, "Install google-auth-oauthlib"
    client_path = BASE_DIR / "client_secret.json"
    if not client_path.exists():
        client_path = BASE_DIR / "client_secrets.json"
    if not client_path.exists():
        return None, "Place client_secret.json"
    flow = Flow.from_client_secrets_file(str(client_path), SCOPES, redirect_uri=redirect_uri)
    return flow, None


def add_channel_from_code(code, redirect_uri):
    """Exchange auth code for token, get channel info, save and add to config. Returns (ok, error, channel_info)."""
    flow, err = get_oauth_flow(redirect_uri)
    if err:
        return False, err, None
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as e:
        return False, str(e), None

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            return False, "No channel found for this account", None
        c = items[0]
        ch_id = c["id"]
        title = c["snippet"].get("title", "YouTube")

        token_path = _token_path(ch_id)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

        channels = get_youtube_channels_config()
        if not any(x.get("id") == ch_id for x in channels):
            channels.append({"id": ch_id, "title": title})
            save_youtube_channels(channels)
        return True, None, {"id": ch_id, "title": title}
    except Exception as e:
        return False, str(e), None


def list_connected_channels():
    """List channels from config (our connected channels). Optionally refresh from API."""
    _migrate_legacy_token()
    channels = get_youtube_channels_config()
    return {"ok": True, "channels": channels}


def refresh_channels():
    """Re-fetch channel info from YouTube API for all connected channels."""
    _migrate_legacy_token()
    channels = get_youtube_channels_config()
    updated = []
    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue
        youtube, err = get_youtube_service(channel_id=ch_id)
        if err:
            continue
        try:
            resp = youtube.channels().list(part="snippet", id=ch_id).execute()
            items = resp.get("items", [])
            if items:
                title = items[0]["snippet"].get("title", ch.get("title", "YouTube"))
                updated.append({"id": ch_id, "title": title})
        except Exception:
            updated.append(ch)
    save_youtube_channels(updated)
    return {"ok": True, "channels": updated}


def load_title_template():
    config_file = BASE_DIR / "gui_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f).get("title_template", "ستوريات {username} | يوم {date} | الجزء {part}")
        except Exception:
            pass
    return "ستوريات {username} | يوم {date} | الجزء {part}"


def list_youtube_channels():
    """Legacy: list channels (now returns connected channels)."""
    return list_connected_channels()


def get_youtube_service_for_channel(channel_id):
    """Get YouTube service for a specific channel ID (from our connected list)."""
    return get_youtube_service(channel_id=channel_id)


def upload_from_folder(username, date_str, privacy="private", upload_type="shorts", channel_id=None):
    """Upload merged videos. channel_id=None uses first available channel."""
    merged_folder = BASE_DIR / "stories" / username / date_str / MERGED_DIR
    if not merged_folder.is_dir():
        return {"success": False, "error": f"Folder not found: {username}/{date_str}/merged/"}

    youtube, err = get_youtube_service_for_channel(channel_id) if channel_id else get_youtube_service()
    if err:
        return {"success": False, "error": err}

    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError:
        return {"success": False, "error": "Missing google-api-python-client"}

    display_name = username.replace("_", " ").title()
    date_fmt = date_str.replace("-", "-")
    title_template = load_title_template()
    uploaded = 0

    shorts = sorted([p for p in merged_folder.glob("merged_*.mp4") if "merged_all" not in p.name])
    full_path = merged_folder / "merged_all.mp4"

    to_upload = []
    if upload_type in ("shorts", "both") and len(shorts) > 0:
        for idx, path in enumerate(shorts, start=1):
            to_upload.append(("short", path, title_template.format(username=display_name, date=date_fmt, part=idx)))
    if upload_type in ("full", "both") and full_path.exists():
        to_upload.append(("full", full_path, f"{display_name} | {date_fmt} | Full"))

    if not to_upload:
        return {"success": False, "error": f"No videos found to upload in {merged_folder} (check merge type: Shorts or Full)"}

    user_id = get_user_id()
    client_secrets = _get_client_secrets()
    if not client_secrets:
        return {"success": False, "error": "No client_secret.json files found in project root."}

    for vid_type, path, title in to_upload:
        uploaded_this = False
        secret_idx = 0

        while not uploaded_this and secret_idx < len(client_secrets):
            current_secret = client_secrets[secret_idx]
            current_token = _get_token_for_secret(channel_id, user_id, current_secret)

            youtube, err = get_youtube_service(channel_id=channel_id, token_path_override=current_token, client_secret_path=current_secret)
            if err:
                secret_idx += 1
                continue
                
            try:
                if vid_type == "short":
                    desc = f"Snapchat Stories from {display_name}\n\n#Shorts #Snapchat"
                    tags = ["Shorts", "Snapchat"]
                else:
                    desc = f"Snapchat Stories from {display_name} - Full compilation\n\n#Snapchat"
                    tags = ["Snapchat", "Stories"]
                body = {
                    "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "22"},
                    "status": {"privacyStatus": privacy},
                }
                media = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
                youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
                uploaded += 1
                uploaded_this = True
            except HttpError as e:
                # 403 / Quota Exceeded Token Fallback (Army of APIs)
                if e.resp.status in (403, 429) and "quota" in str(e).lower():
                    secret_idx += 1
                    continue
                return {"success": uploaded > 0, "error": str(e), "count": uploaded}
            except Exception as e:
                return {"success": uploaded > 0, "error": str(e), "count": uploaded}

        if not uploaded_this:
            return {"success": uploaded > 0, "error": "All tokens exhausted (Quota limits reached)", "count": uploaded}

    if uploaded > 0 and uploaded == len(to_upload):
        try:
            import shutil
            archive_dir = merged_folder / "uploaded_youtube"
            archive_dir.mkdir(exist_ok=True)
            for _, path, _ in to_upload:
                if path.exists():
                    shutil.move(str(path), str(archive_dir / path.name))
        except Exception as e:
            return {"success": True, "count": uploaded, "error": f"Uploaded but failed to move files: {e}"}

    return {"success": True, "count": uploaded}


def upload_single_file(file_path, title, privacy="private", channel_id=None):
    """Upload a single video file to YouTube."""
    if not os.path.isfile(file_path):
        return {"success": False, "error": "File not found"}

    youtube, err = get_youtube_service_for_channel(channel_id) if channel_id else get_youtube_service()
    if err:
        return {"success": False, "error": err}

    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return {"success": False, "error": "Missing google-api-python-client"}

    try:
        body = {
            "snippet": {"title": title, "description": "#Shorts #Snapchat", "tags": ["Shorts", "Snapchat"], "categoryId": "22"},
            "status": {"privacyStatus": privacy},
        }
        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
        response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        vid_id = response.get("id")
        return {"success": True, "url": f"https://www.youtube.com/watch?v={vid_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
