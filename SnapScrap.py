#!/usr/bin/env python3
"""SnapScrap - Download public Snapchat stories."""
__author__ = "https://codeberg.org/allendema"

import json
import os
import subprocess
import sys
import time
from datetime import date
from time import sleep

from bs4 import BeautifulSoup
import requests

from download_tracker import is_downloaded, mark_downloaded

# Fix Unicode print on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# English output if Arabic appears broken in CMD (use --en or set SNAPSCRAP_LANG=en)
USE_EN = os.environ.get("SNAPSCRAP_LANG", "").lower() == "en" or "--en" in sys.argv
if "--en" in sys.argv:
    sys.argv = [a for a in sys.argv if a != "--en"]


def show_help():
    """عرض قائمة بجميع الأوامر المتاحة."""
    if USE_EN:
        h = """
SnapScrap - Command list
------------------------
1) Download stories:
   python SnapScrap.py <username>
   python SnapScrap.py <username> --merge   (download then merge)
   Example: python SnapScrap.py dary_1256 --merge
   Output folder: username\\YYYY-MM-DD\\

2) Merge videos (every 8 per file, or all in one):
   python merge_videos.py <username> [YYYY-MM-DD] [--all]
   Without --all: merged_1.mp4, merged_2.mp4, ...
   With --all:   merged_all.mp4 (single video)
   Example: python merge_videos.py dary_1256
            python merge_videos.py dary_1256 2025-02-15 --all
   Output: username\\YYYY-MM-DD\\merged\\

3) Upload to YouTube Shorts:
   python upload_youtube_shorts.py <username> [YYYY-MM-DD] [private|public|unlisted]
   Example: python upload_youtube_shorts.py dary_1256 private
   (Requires client_secret.json from Google Cloud)

Per-script help:
   python SnapScrap.py help
   python merge_videos.py --help
   python upload_youtube_shorts.py --help

From CMD: use run.bat (e.g. run.bat help, run.bat dary_1256 --merge)
Or: run.bat en help   for English output if Arabic looks wrong.

Do NOT type < > or [ ] - they are placeholders. Use real values:
  python merge_videos.py dary_1256 2026-02-15 --all
"""
    else:
        h = """
+------------------------------------------------------------------+
|              SnapScrap - Command list                             |
+------------------------------------------------------------------+
| 1) Download stories:                                              |
|    python SnapScrap.py <username>                                |
|    python SnapScrap.py <username> --merge                        |
|    Example: python SnapScrap.py dary_1256 --merge                 |
|    Output folder: username\\YYYY-MM-DD\\                          |
+------------------------------------------------------------------+
| 2) Merge videos:                                                  |
|    python merge_videos.py <username> [YYYY-MM-DD] [--all]         |
|    Without --all: merged_1, merged_2, ... (every 8 videos)       |
|    With --all: merged_all.mp4 (one video)                         |
|    Example: python merge_videos.py dary_1256 --all                |
+------------------------------------------------------------------+
| 3) Upload YouTube Shorts:                                         |
|    python upload_youtube_shorts.py <username> [date] [privacy]    |
|    Example: python upload_youtube_shorts.py dary_1256 private     |
+------------------------------------------------------------------+
| Per-script help: python SnapScrap.py help  |  merge_videos --help |
| From CMD: run.bat help  or  run.bat en help (English)             |
|                                                                  |
| Do NOT type the symbols < > or [ ] - use real values, e.g.:       |
|   python merge_videos.py dary_1256 2026-02-15 --all               |
+------------------------------------------------------------------+
"""
    print(h.strip())


def user_input():
    """Get username from argument or user input."""
    args = [a for a in sys.argv[1:] if a not in ("--merge", "--en")]
    try:
        username = args[0]
    except IndexError:
        username = input("Enter a username: ")

    if args and args[0].lower() in ("help", "--help", "-h"):
        show_help()
        sys.exit(0)

    path = os.path.join("stories", username)
    date_str = date.today().strftime("%Y-%m-%d")
    date_folder = os.path.join(path, date_str)

    if os.path.exists(path):
        pass # removed this print statement to reduce console spam
    else:
        os.makedirs(path, exist_ok=True)
    os.makedirs(date_folder, exist_ok=True)
    os.chdir(date_folder)
    print(f"Download folder: {date_folder}" if USE_EN else f"التنزيل في مجلد: {date_folder}")
    return username


YELLOW = "\033[1;32;40m"
RED = "\033[31m"

headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/103.0.2'}

base_url = "https://story.snapchat.com/@"
username = user_input()

mix = base_url + username
print(mix)


def get_json():
	"""Get json from the website"""

	r = requests.get(mix, headers=headers)

	if not r.ok:
		sys.exit(f"{RED} Oh Snap! No connection with Snap!")

	soup = BeautifulSoup(r.content, "html.parser")
	snaps = soup.find(id="__NEXT_DATA__").string.strip()
	data = json.loads(snaps)

	return data


def profile_metadata(json_dict=get_json()):
	"""Detect public profile, then print bio and bitmoji"""
	# if public
	try:
		bitmoji = json_dict["props"]["pageProps"]["userProfile"]["publicProfileInfo"]["snapcodeImageUrl"]
		bio = json_dict["props"]["pageProps"]["userProfile"]["publicProfileInfo"]["bio"]

	# if not public
	except KeyError:
		bitmoji = json_dict["props"]["pageProps"]["userProfile"]["userInfo"]["snapcodeImageUrl"]
		bio = json_dict["props"]["pageProps"]["userProfile"]["userInfo"]["displayName"]

		print(f"{YELLOW}Here is the Bio: \n {bio}\n")
		print(f"Bitmoji:\n {bitmoji}\n")
		print(f"{RED} This user is private.")

		sys.exit(1)

	print(f"{YELLOW}\nBio of the user:\n", bio)
	print(f"\nHere is the Bitmoji:\n {bitmoji} \n")

	print(f"Getting posts of: {username}\n")


def download_media(json_dict=get_json()):
	"""Print media URLs and download media."""

	date_str = date.today().strftime("%Y-%m-%d")
	skipped = 0
	downloaded = 0

	try:
		# Get all links with a for-loop (numbered 1, 2, 3, ...)
		for num, i in enumerate(json_dict["props"]["pageProps"]["story"]["snapList"], start=1):

			file_url = i["snapUrls"]["mediaUrl"]

			if file_url == "":
				print("There is a Story but no URL is provided by Snapchat.")
				continue

			# Check if already downloaded
			if is_downloaded(username, date_str, file_url):
				skipped += 1
				continue

			# Download media
			r = requests.get(file_url, stream=True, headers=headers)

			if "image" in r.headers['Content-Type']:
				ext = ".jpeg"
			elif "video" in r.headers['Content-Type']:
				ext = ".mp4"
			else:
				ext = ".bin"

			file_name = f"{num}{ext}"
			
			#  Check if this file / file_name exists locally
			if os.path.isfile(file_name):
				mark_downloaded(username, date_str, file_url, file_name)
				skipped += 1
				continue

			print(file_name)

			#  Sleep a bit
			sleep(0.3)

			if r.status_code == 200:
				with open(file_name, 'wb') as f:
					for chunk in r:
						f.write(chunk)
				mark_downloaded(username, date_str, file_url, file_name)
				downloaded += 1
			else:
				print("Cannot make connection to download media!")

	except KeyError:
		print(f"{RED}No user stories found for the last 24h.")
	else:
		if skipped > 0:
			print(f"\nSkipped {skipped} already downloaded stories.")
		if downloaded > 0:
			print(f"\nDownloaded {downloaded} new stories.")
		if downloaded == 0 and skipped == 0:
			print("\nNo new stories found.")
		else:
			print("\nAt least one Story found. Successfully Downloaded.")


def main():
	start = time.perf_counter()
	do_merge = "--merge" in sys.argv

	profile_metadata()
	download_media()

	if do_merge:
		script_dir = os.path.dirname(os.path.abspath(__file__))
		merge_script = os.path.join(script_dir, "merge_videos.py")
		date_str = date.today().strftime("%Y-%m-%d")
		merge_msg = f"\n{YELLOW}Merging videos (date: {date_str})..." if USE_EN else f"\n{YELLOW}دمج كل 6 فيديوهات (تاريخ اليوم: {date_str})..."
		print(merge_msg)
		env = os.environ.copy()
		if USE_EN:
			env["SNAPSCRAP_LANG"] = "en"
		subprocess.run([sys.executable, merge_script, username, date_str], cwd=script_dir, env=env)

	end = time.perf_counter()
	total = end - start

	print(f"\n\nTotal time: {total}")


if __name__ == "__main__":
	main()
