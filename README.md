# SnapScrap.py

Downloads public Snapchat stories to your system. Includes merge, YouTube upload, batch processing, and GUI.

## Install

```bash
git clone https://github.com/allendema/SnapScrap.py.git
cd SnapScrap.py/
pip install -r requirements.txt
```

## Commands

| Task | Command |
|------|---------|
| **Download** | `python SnapScrap.py <username>` |
| **Download + merge** | `python SnapScrap.py <username> --merge` |
| **Merge videos** | `python merge_videos.py <username> [YYYY-MM-DD] [--all]` |
| **Upload to YouTube** | `python upload_youtube_shorts.py <username> [date] [private\|public\|unlisted]` |
| **One account (full)** | `python daily_automation.py <username> [--no-upload] [privacy]` |
| **Multiple accounts** | `python batch_processor.py [--no-upload] [privacy]` (reads `accounts.txt`) |
| **GUI** | `python snapscrap_gui.py` |
| **Web App** | `run_web.bat` or `python -m flask --app webapp.app run` |

## Web App (جديد)

واجهة ويب حديثة مع:
- تنزيل Stories ودمج الفيديوهات
- **رفع إلى يوتيوب فقط** — من المجلد المدمج أو رفع ملف فيديو مباشرة
- تصميم عصري وأنيق

```bash
pip install -r requirements_web.txt
run_web.bat
# أو: python -m flask --app webapp.app run
# ثم افتح: http://127.0.0.1:5000
```

## Help

```bash
python SnapScrap.py help
# Or from CMD: run.bat help   (run.bat en help for English)
```

## Output layout

- Download: `username/YYYY-MM-DD/`
- Merged videos: `username/YYYY-MM-DD/merged/`

## Requirements

- **ffmpeg** (for merge): install system ffmpeg or `pip install imageio-ffmpeg`
- **YouTube upload** (optional): `pip install google-api-python-client google-auth-oauthlib google-auth-httplib2` + `client_secret.json` from Google Cloud Console
- **GUI** (optional): `pip install -r requirements_gui.txt`

## Heads Up

Use to archive important things, be polite and cause no harm. Use at own risk.

Allen 2022

[![License: Apache License 2.0](https://img.shields.io/github/license/allendema/SnapScrap.py)](https://github.com/allendema/SnapScrap.py/blob/main/LICENSE)
