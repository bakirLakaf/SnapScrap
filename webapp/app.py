#!/usr/bin/env python3
"""SnapScrap Web App - واجهة ويب حديثة."""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import functools
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from webapp.models import db, User, ConnectedChannel
from webapp.billing import billing_bp

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB
app.config["UPLOAD_FOLDER"] = BASE_DIR / "uploads"
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'super-secret-default-key-123')
# Prevent XSS & Session Hijacking
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Trust reverse proxies for HTTPS scheme
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configure database
db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'snapscrap.db'}")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)

app.register_blueprint(billing_bp)

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("FLASK_CSRF_SECRET_KEY", "csrf-token-secret-xyz-444")
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://"
)

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def load_translations():
    t_file = BASE_DIR / "webapp" / "translations.json"
    if t_file.exists():
        with open(t_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

translations = load_translations()

def get_current_language():
    return session.get('lang', 'ar')

def _(key):
    lang = get_current_language()
    return translations.get(lang, {}).get(key, key)

@app.context_processor
def inject_translations():
    return dict(_=_, current_lang=get_current_language())

@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang in ["ar", "en", "fr"]:
        session['lang'] = lang
    return redirect(request.referrer or url_for('landing'))

# Auto-Migration for V2 SQLite (Add new columns without dropping data)
with app.app_context():
    db.create_all()
    try:
        from sqlalchemy import text
        # Attempt to query the newly added V2 columns
        db.session.execute(text("SELECT stripe_customer_id FROM user LIMIT 1"))
    except Exception:
        db.session.rollback()
        print("Migrating local database: Checking missing columns in User table...")
        columns_to_add = [
            ("subscription_tier", "VARCHAR(50) DEFAULT 'free'"),
            ("stripe_customer_id", "VARCHAR(255)"),
            ("created_at", "DATETIME")
        ]
        for col_name, col_def in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
                print(f"Added column {col_name}.")
            except Exception:
                db.session.rollback()
                pass

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static', 'landing', 'billing.stripe_webhook']
    if request.endpoint not in allowed_routes and not current_user.is_authenticated:
        if request.path.startswith('/api/'):
            return jsonify({"ok": False, "error": "Unauthorized. Please login."}), 401
        return redirect(url_for('login'))

ACCOUNTS_KEY = "accounts"
SCHEDULE_KEY = "schedule"
tasks = {}

def get_user_config_file(user_id=None):
    if user_id is None:
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
        else:
            return None
    user_dir = BASE_DIR / "stories" / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "webapp_config.json"


def load_config(user_id=None):
    """Load webapp config."""
    config_file = get_user_config_file(user_id)
    if config_file and config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config, user_id=None):
    """Save webapp config."""
    config_file = get_user_config_file(user_id)
    if not config_file:
        return
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())


def get_accounts(user_id=None):
    """Get accounts list: [{username, checked}, ...]."""
    cfg = load_config(user_id)
    return cfg.get(ACCOUNTS_KEY, [])


def save_accounts(accounts, user_id=None):
    """Save accounts."""
    cfg = load_config(user_id)
    cfg[ACCOUNTS_KEY] = accounts
    save_config(cfg, user_id)


def get_schedule(user_id=None):
    """Get schedule: {enabled, hour, minute, merge}."""
    cfg = load_config(user_id)
    return cfg.get(SCHEDULE_KEY, {"enabled": False, "hour": 9, "minute": 0, "merge": False})


def save_schedule(schedule, user_id=None):
    """Save schedule."""
    cfg = load_config(user_id)
    cfg[SCHEDULE_KEY] = schedule
    save_config(cfg, user_id)


def get_merged_folders():
    """List username/date folders that have merged videos."""
    result = []
    stories_dir = BASE_DIR / "stories"
    try:
        items = os.listdir(stories_dir)
    except OSError:
        return []
    for username in items:
        user_path = stories_dir / username
        if not user_path.is_dir() or username.startswith(".") or username in ("webapp", "build", "dist", "uploads"):
            continue
        try:
            subdirs = os.listdir(user_path)
        except OSError:
            continue
        for d in subdirs:
            merged_path = user_path / d / "merged"
            if merged_path.is_dir() and list(merged_path.glob("merged_*.mp4")):
                result.append({"username": username, "date": d})
    return sorted(result, key=lambda x: (x["username"], x["date"]), reverse=True)


def run_task(task_id, task_type, **kwargs):
    """Run task in background."""
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    
    def _run():
        try:
            if task_type == "download":
                _run_download(task_id, kwargs.get("username"), kwargs.get("merge", False), user_id)
            elif task_type == "download_batch":
                _run_download_batch(task_id, kwargs.get("usernames", []), kwargs.get("merge", False), user_id)
            elif task_type == "merge":
                _run_merge(task_id, kwargs.get("username"), kwargs.get("date_str"), kwargs.get("merge_mode", "shorts"), user_id)
            elif task_type == "upload":
                _run_upload(task_id, kwargs.get("username"), kwargs.get("date_str"), kwargs.get("privacy", "private"), kwargs.get("upload_type", "shorts"), kwargs.get("channel_id"), user_id)
            elif task_type == "upload_file":
                _run_upload_file(task_id, kwargs.get("file_path"), kwargs.get("title"), kwargs.get("privacy", "private"), kwargs.get("channel_id"), user_id)
        except Exception as e:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = str(e)

    threading.Thread(target=_run, daemon=True).start()


def _run_download(task_id, username, do_merge, user_id=""):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = f"Downloading {username}..."
    cmd = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username]
    if do_merge:
        cmd.append("--merge")
    env = os.environ.copy()
    env["SNAPSCRAP_LANG"] = "en"
    if user_id:
        env["SNAPSCRAP_USER_ID"] = str(user_id)
    proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if proc.returncode != 0:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = proc.stderr or proc.stdout or "Download failed"
        return
    tasks[task_id]["status"] = "done"
    tasks[task_id]["message"] = f"Downloaded {username}!"


def _run_download_batch(task_id, usernames, do_merge, user_id=""):
    total = len(usernames)
    done = 0
    failed = []
    for username in usernames:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["message"] = f"Downloading {username} ({done + 1}/{total})..."
        cmd = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username]
        if do_merge:
            cmd.append("--merge")
        env = os.environ.copy()
        env["SNAPSCRAP_LANG"] = "en"
        if user_id:
            env["SNAPSCRAP_USER_ID"] = str(user_id)
        proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if proc.returncode != 0:
            failed.append(username)
        else:
            done += 1
    tasks[task_id]["status"] = "done" if not failed else ("error" if done == 0 else "done")
    tasks[task_id]["message"] = f"Downloaded {done}/{total}" + (f" — failed: {', '.join(failed)}" if failed else "")


def _run_merge(task_id, username, date_str, merge_mode="shorts", user_id=""):
    """merge_mode: shorts | full | both (run both shorts and full)"""
    tasks[task_id]["status"] = "running"
    env = os.environ.copy()
    env["SNAPSCRAP_LANG"] = "en"
    if user_id:
        env["SNAPSCRAP_USER_ID"] = str(user_id)
        
    if merge_mode == "both":
        # First: Shorts (merged_1, merged_2, ...)
        tasks[task_id]["message"] = "Merging Shorts..."
        cmd1 = [sys.executable, str(BASE_DIR / "merge_videos.py"), username, date_str]
        proc1 = subprocess.run(cmd1, cwd=str(BASE_DIR), capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
        if proc1.returncode != 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = proc1.stderr or proc1.stdout or "Merge Shorts failed"
            return
        # Second: Full (merged_all.mp4)
        tasks[task_id]["message"] = "Merging full video..."
        cmd2 = [sys.executable, str(BASE_DIR / "merge_videos.py"), username, date_str, "--all"]
        proc2 = subprocess.run(cmd2, cwd=str(BASE_DIR), capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
        if proc2.returncode != 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = proc2.stderr or proc2.stdout or "Merge full failed"
            return
    else:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["message"] = "Merging videos..."
        cmd = [sys.executable, str(BASE_DIR / "merge_videos.py"), username, date_str]
        if merge_mode == "full":
            cmd.append("--all")
        proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = proc.stderr or proc.stdout or "Merge failed"
            return
    tasks[task_id]["status"] = "done"
    tasks[task_id]["message"] = "Merge complete!"


def _run_upload(task_id, username, date_str, privacy, upload_type="shorts", channel_id=None, user_id=""):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = "Connecting to YouTube..."
    try:
        from webapp.youtube_service import upload_from_folder
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
        result = upload_from_folder(username, date_str, privacy, upload_type=upload_type, channel_id=channel_id)
        if result.get("success"):
            tasks[task_id]["status"] = "done"
            tasks[task_id]["message"] = f"Uploaded {result.get('count', 0)} videos!"
        else:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = result.get("error", "Upload failed")
    except ImportError:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = "Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)


def _run_upload_file(task_id, file_path, title, privacy, channel_id=None):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = "Uploading to YouTube..."
    try:
        from webapp.youtube_service import upload_single_file
        result = upload_single_file(file_path, title or "Snapchat Short", privacy, channel_id=channel_id)
        if result.get("success"):
            tasks[task_id]["status"] = "done"
            tasks[task_id]["message"] = f"Uploaded! {result.get('url', '')}"
        else:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = result.get("error", "Upload failed")
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


def scheduler_loop():
    """Background scheduler - run at scheduled time daily."""
    last_date = None
    while True:
        time.sleep(30)
        sched = get_schedule()
        if not sched.get("enabled"):
            continue
        now = datetime.now()
        h, m = sched.get("hour", 9), sched.get("minute", 0)
        if now.hour == h and now.minute == m and last_date != now.date():
            accounts = [a["username"] for a in get_accounts() if a.get("checked")]
            if accounts:
                last_date = now.date()
                task_id = f"batch_{now.strftime('%Y%m%d_%H%M')}"
                tasks[task_id] = {"status": "running", "message": "Scheduled run..."}
                run_task(task_id, "download_batch", usernames=accounts, merge=sched.get("merge", False))


def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()


start_scheduler()

def fetch_snapchat_info(username):
    """Fetch public profile info (Bitmoji, Bio) from Snapchat."""
    url = f"https://story.snapchat.com/@{username}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if not r.ok:
            return {}
        soup = BeautifulSoup(r.content, "html.parser")
        next_data = soup.find(id="__NEXT_DATA__")
        if not next_data:
            return {}
        data = json.loads(next_data.string)
        props = data.get("props", {}).get("pageProps", {})
        user_profile = props.get("userProfile", {})
        public_info = user_profile.get("publicProfileInfo", {})
        user_info = user_profile.get("userInfo", {})
        
        # Try finding snapcode/bitmoji in publicProfileInfo first, then userInfo
        avatar = public_info.get("snapcodeImageUrl") or user_info.get("snapcodeImageUrl") or user_info.get("bitmoji3dAvatarId") 
        # Note: bitmoji3dAvatarId needs constructing url, snapcodeImageUrl is direct. 
        # Typically snapcodeImageUrl is what we want or 'squareImageURL'
        
        if not avatar:
             # Fallback to older keys if structure changed
             avatar = public_info.get("squareHeroImageUrl")
        
        return {"avatar": avatar}
    except Exception:
        return {}

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not username or not password:
            flash("اسم المستخدم وكلمة المرور مطلوبان", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم محجوز، اختر اسماً آخر", "danger")
            return redirect(url_for("register"))
        
        try:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("register"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("بيانات الدخول غير صحيحة", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username not in ["bakir", "testadmin"]:
            flash("غير مصرح لك بالدخول إلى لوحة التحكم", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin")
@admin_required
def admin_dashboard():
    from webapp.models import User, ConnectedChannel
    users = User.query.all()
    channel_count = ConnectedChannel.query.count()
    return render_template("admin.html", users=users, total_channels=channel_count)

@app.route("/admin/user/<int:user_id>/tier", methods=["POST"])
@admin_required
def admin_change_tier(user_id):
    from webapp.models import User
    user = User.query.get_or_404(user_id)
    new_tier = request.form.get("tier")
    if new_tier in ["free", "pro", "enterprise"]:
        user.subscription_tier = new_tier
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    from webapp.models import User, ConnectedChannel
    user = User.query.get_or_404(user_id)
    if user.username not in ["bakir", "testadmin"]:
        ConnectedChannel.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/dashboard")
@login_required
def dashboard():
    from webapp.youtube_service import get_youtube_channels_config, _get_all_tokens_for_channel
    
    raw_channels = get_youtube_channels_config(current_user.id)
    enriched_channels = []
    for c in raw_channels:
        ch_id = c.get("id")
        tokens = _get_all_tokens_for_channel(ch_id, current_user.id)
        c["token_count"] = len(tokens)
        enriched_channels.append(c)

    return render_template(
        "index.html",
        merged_folders=get_merged_folders(),
        accounts=get_accounts(),
        schedule=get_schedule(),
        youtube_channels=enriched_channels
    )


@app.route("/api/download_single_story", methods=["POST"])
@limiter.limit("10 per minute")
def api_download_single_story():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "رابط القصة مطلوب"})
    
    try:
        import requests, json, re
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        if "t.snapchat.com" in url:
            r = requests.get(url, allow_redirects=True, timeout=10)
            url = r.url
            
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        next_data = soup.find(id="__NEXT_DATA__")
        if not next_data:
            return jsonify({"error": "لم يتم العثور على بيانات سناب شات من الرابط."})
            
        media_url = None
        match = re.search(r'"mediaUrl":\s*"([^"]+)"', next_data.string)
        if match:
            media_url = match.group(1)
        
        if not media_url:
            return jsonify({"error": "الرابط لا يحتوي على ميديا متاحة"})
            
        # Download temp file
        import tempfile
        r = requests.get(media_url, stream=True, headers=headers)
        ext = ".mp4" if "video" in r.headers.get('Content-Type', '') else ".jpeg"
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
                
        return jsonify({"success": True, "download_url": url_for('serve_single_download', path=path, _external=True)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/download_temp")
@login_required
def serve_single_download():
    path = request.args.get("path")
    if path and os.path.exists(path):
        from flask import send_file
        return send_file(path, as_attachment=True, download_name=f"snapchat_story{os.path.splitext(path)[1]}")
    return "File not found", 404

@app.route("/api/accounts", methods=["GET", "POST", "DELETE"])
def api_accounts():
    if request.method == "GET":
        return jsonify(get_accounts())
    data = request.get_json() or {}
    action = data.get("action")
    accounts = get_accounts()
    
    if action == "add":
        max_accounts = 999
        if len(accounts) >= max_accounts:
            return jsonify({"ok": False, "error": f"You reached your limit of {max_accounts} accounts. Upgrade to add more."})
            
        username = (data.get("username") or "").strip().lower()
        if not username:
            return jsonify({"ok": False, "error": "Username required"})
        if any(a.get("username") == username for a in accounts):
            return jsonify({"ok": False, "error": "Already exists"})
        
        # Fetch info
        info = fetch_snapchat_info(username)
        accounts.append({"username": username, "checked": True, "avatar": info.get("avatar")})
        save_accounts(accounts, current_user.id)
        
    elif action == "add_bulk":
        max_accounts = 999
        
        raw = data.get("usernames") or data.get("text") or ""
        if isinstance(raw, list):
            usernames = [str(u).strip().lower() for u in raw if str(u).strip()]
        else:
            usernames = [u.strip().lower() for u in str(raw).replace(",", "\n").splitlines() if u.strip()]
        
        added = 0
        skipped = []
        for u in usernames:
            if len(accounts) >= max_accounts:
                skipped.append(u)
                continue
            if any(a.get("username") == u for a in accounts):
                skipped.append(u)
                continue
            
            # Fetch info (might be slow for many accounts, but acceptable for typical usage)
            info = fetch_snapchat_info(u)
            accounts.append({"username": u, "checked": True, "avatar": info.get("avatar")})
            added += 1
            
        save_accounts(accounts, current_user.id)
        return jsonify({
            "ok": True,
            "added": added,
            "skipped": skipped,
            "accounts": get_accounts()
        })
    elif action == "remove":
        username = data.get("username")
        accounts = [a for a in accounts if a.get("username") != username]
        save_accounts(accounts)
    elif action == "toggle":
        username = data.get("username")
        for a in accounts:
            if a.get("username") == username:
                a["checked"] = not a.get("checked")
        save_accounts(accounts)
    elif action == "set_checked":
        username = data.get("username")
        checked = data.get("checked", True)
        for a in accounts:
            if a.get("username") == username:
                a["checked"] = checked
                break
        save_accounts(accounts)
        return jsonify({"ok": True, "accounts": get_accounts()})
    elif action == "set_all_checked":
        checked = data.get("checked", True)
        for a in accounts:
            a["checked"] = checked
        save_accounts(accounts)
        return jsonify({"ok": True, "accounts": get_accounts()})
    return jsonify({"ok": True, "accounts": get_accounts()})


@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    """Open folder in OS explorer."""
    data = request.get_json() or {}
    username = data.get("username")
    date_str = data.get("date")
    
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    
    # Path logic
    target_path = BASE_DIR / "stories" / username
    if date_str:
        # If date is provided, try to open the date folder or merged folder
        p = target_path / date_str / "merged"
        if not p.exists():
            p = target_path / date_str
            if not p.exists():
                p = target_path # Fallback
        target_path = p
    
    if not target_path.exists():
        return jsonify({"ok": False, "error": "Folder not found"})

    try:
        if os.name == 'nt':  # Windows
            os.startfile(str(target_path))
        elif sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', str(target_path)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(target_path)])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"dl_{username}_{date.today().isoformat()}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "download", username=username, merge=data.get("merge", False))
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/download-selected", methods=["POST"])
def api_download_selected():
    data = request.get_json() or {}
    usernames = [u.strip() for u in (data.get("usernames") or []) if u.strip()]
    if not usernames:
        return jsonify({"ok": False, "error": "Select at least one account"})
    task_id = f"batch_{date.today().isoformat()}_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "download_batch", usernames=usernames, merge=data.get("merge", False))
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/schedule", methods=["GET", "POST"])
def api_schedule():
    if request.method == "GET":
        return jsonify(get_schedule())
    data = request.get_json() or {}
    schedule = {
        "enabled": bool(data.get("enabled")),
        "hour": int(data.get("hour", 9)) % 24,
        "minute": int(data.get("minute", 0)) % 60,
        "merge": bool(data.get("merge")),
    }
    save_schedule(schedule)
    return jsonify({"ok": True, "schedule": schedule})


@app.route("/api/merge", methods=["POST"])
def api_merge():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip() or date.today().strftime("%Y-%m-%d")
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"merge_{username}_{date_str}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    merge_mode = data.get("merge_mode") or data.get("mergeMode") or "shorts"  # shorts | full | both
    run_task(task_id, "merge", username=username, date_str=date_str, merge_mode=merge_mode)
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip() or date.today().strftime("%Y-%m-%d")
    privacy = data.get("privacy") or "private"
    upload_type = data.get("upload_type") or "shorts"
    channel_id = data.get("channel_id") or None
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"upload_{username}_{date_str}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "upload", username=username, date_str=date_str, privacy=privacy, upload_type=upload_type, channel_id=channel_id)
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/upload-file", methods=["POST"])
def api_upload_file():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"})
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"ok": False, "error": "No file selected"})
    if not f.filename.lower().endswith((".mp4", ".webm", ".mov")):
        return jsonify({"ok": False, "error": "Only video files (.mp4, .webm, .mov)"})
    filename = secure_filename(f.filename) or "video.mp4"
    file_path = app.config["UPLOAD_FOLDER"] / filename
    f.save(str(file_path))
    title = (request.form.get("title") or filename).replace(".mp4", "")
    privacy = request.form.get("privacy") or "private"
    channel_id = request.form.get("channel_id") or None
    task_id = f"uf_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "upload_file", file_path=str(file_path), title=title, privacy=privacy, channel_id=channel_id)
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/task/<task_id>")
def api_task(task_id):
    return jsonify(tasks.get(task_id, {"status": "unknown"}))


@app.route("/api/merged-folders")
def api_merged_folders():
    return jsonify(get_merged_folders())


# حسابات فرق صناعة المحتوى السعودية (مقترحة)
SUGGESTED_ACCOUNTS = [
    {"username": "falconsesports", "label": "فالكونز Falcons"},
    {"username": "teamfalconsgg", "label": "فالكونز Falcons"},
    {"username": "poweresports", "label": "باور Power"},
    {"username": "snap.topz", "label": "تي يو TU Topz"},
]


@app.route("/api/suggested-accounts")
def api_suggested_accounts():
    return jsonify({"accounts": SUGGESTED_ACCOUNTS})


@app.route("/api/youtube/channels")
def api_youtube_channels():
    try:
        from webapp.youtube_service import list_connected_channels
        return jsonify(list_connected_channels())
    except ImportError:
        return jsonify({"ok": False, "error": "Install google-api-python-client", "channels": []})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "channels": []})


@app.route("/api/youtube/refresh", methods=["POST"])
def api_youtube_refresh():
    try:
        from webapp.youtube_service import refresh_channels
        return jsonify(refresh_channels())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "channels": []})


@app.route("/api/youtube/upload_token", methods=["POST"])
@login_required
def api_youtube_upload_token():
    try:
        if 'token_file' not in request.files:
            return jsonify({"ok": False, "error": "No file part"})
        file = request.files['token_file']
        channel_id = request.form.get("channel_id")
        if file.filename == '' or not channel_id:
            return jsonify({"ok": False, "error": "No selected file or channel"})
            
        if not file.filename.endswith(".json"):
            return jsonify({"ok": False, "error": "Only .json files are allowed"})

        from webapp.youtube_service import get_tokens_dir, _safe_channel_id
        import time
        
        tdir = get_tokens_dir(current_user.id)
        safe_id = _safe_channel_id(channel_id)
        ts = int(time.time())
        
        filename = f"token_{safe_id}_reserve_{ts}.json"
        save_path = tdir / filename
        file.save(str(save_path))
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/youtube/connect")
def youtube_connect():
    """Redirect to Google OAuth to add a new channel."""
    try:
        from webapp.youtube_service import get_authorization_url
        base_url = request.url_root.rstrip("/")
        redirect_uri = f"{base_url}/youtube/callback"
        auth_url, state = get_authorization_url(redirect_uri)
        if not auth_url:
            return redirect("/?youtube_error=" + (state or "Unknown error"))
        session["youtube_oauth_state"] = state
        return redirect(auth_url)
    except Exception as e:
        return redirect("/?youtube_error=" + str(e).replace(" ", "+"))


@app.route("/youtube/callback")
def youtube_callback():
    """OAuth callback - add channel and redirect home."""
    state = request.args.get("state")
    if state != session.get("youtube_oauth_state"):
        return redirect("/?youtube_error=Invalid+state")
    session.pop("youtube_oauth_state", None)
    code = request.args.get("code")
    if not code:
        return redirect("/?youtube_error=No+code")
    try:
        from webapp.youtube_service import add_channel_from_code
        base_url = request.url_root.rstrip("/")
        redirect_uri = f"{base_url}/youtube/callback"
        ok, err, ch = add_channel_from_code(code, redirect_uri)
        if ok:
            return redirect("/?youtube_connected=1")
        return redirect("/?youtube_error=" + (err or "Unknown").replace(" ", "+"))
    except Exception as e:
        return redirect("/?youtube_error=" + str(e).replace(" ", "+"))


def _run_upload_all(task_id, folders, privacy, upload_type, channel_id=None, user_id=""):
    """Upload all merged folders to YouTube."""
    tasks[task_id]["status"] = "running"
    total = len(folders)
    uploaded_folders = 0
    total_videos = 0
    last_error = None
    try:
        from webapp.youtube_service import upload_from_folder
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
        for idx, f in enumerate(folders):
            tasks[task_id]["message"] = f"Uploading {f['username']}/{f['date']} ({idx + 1}/{total})..."
            r = upload_from_folder(f["username"], f["date"], privacy, upload_type, channel_id=channel_id)
            if r.get("success"):
                uploaded_folders += 1
                total_videos += r.get("count", 0)
            else:
                last_error = r.get("error", "Upload failed")
        tasks[task_id]["status"] = "done"
        tasks[task_id]["message"] = f"Uploaded {total_videos} videos from {uploaded_folders} folder(s)!"
        if last_error and uploaded_folders == 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = last_error
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)
        
        
@app.route("/api/upload-all", methods=["POST"])
def api_upload_all():
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    data = request.get_json() or {}
    folders = data.get("folders") or get_merged_folders()
    if not folders:
        return jsonify({"ok": False, "error": "No merged folders to upload"})
    privacy = data.get("privacy") or "private"
    upload_type = data.get("upload_type") or "shorts"
    channel_id = data.get("channel_id") or None
    task_id = f"upload_all_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}

    def _run():
        _run_upload_all(task_id, folders, privacy, upload_type, channel_id, user_id)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/clear-batch", methods=["POST"])
def api_clear_batch():
    """Delete username/date folder after upload (manual cleanup)."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip()
    if not username or not date_str:
        return jsonify({"ok": False, "error": "Username and date required"})
    folder = BASE_DIR / "stories" / username / date_str
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "Folder not found"})
    if username in ("webapp", "build", "dist", "uploads") or username.startswith("."):
        return jsonify({"ok": False, "error": "Cannot delete that folder"})
    try:
        import shutil
        shutil.rmtree(folder)
        return jsonify({"ok": True, "message": f"Deleted {username}/{date_str}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
