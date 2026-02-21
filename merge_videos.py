#!/usr/bin/env python3
"""
دمج كل 6 فيديوهات من مجلد المستخدم في فيديو واحد (مناسب لـ Shorts).
يستخدم ffmpeg من النظام أو من الحزمة imageio-ffmpeg.
"""
import os
import re
import sys
import subprocess
import tempfile
from datetime import date

# Fix Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

USE_EN = os.environ.get("SNAPSCRAP_LANG", "").lower() == "en" or "--en" in sys.argv
if "--en" in sys.argv:
    sys.argv = [a for a in sys.argv if a != "--en"]

def load_config():
    """Load config from file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "gui_config.json")
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

config = load_config()
CHUNK_SIZE = config.get("chunk_size", 7)
VIDEO_QUALITY = config.get("video_quality", 23)  # CRF value
MERGED_DIR = "merged"
# تنسيق Shorts عمودي
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920


def find_ffmpeg():
    """Find ffmpeg: first in PATH, then from imageio-ffmpeg package."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    return None


def get_video_files(folder):
    """Get sorted list of .mp4 files (by number). Supports 1.mp4, 2.mp4 and old ETag names."""
    if not os.path.isdir(folder):
        return []
    files = []
    for f in os.listdir(folder):
        if f.lower().endswith(".mp4"):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                # ترتيب رقمي: 1, 2, 3, ...
                num_match = re.match(r"^(\d+)", f)
                num = int(num_match.group(1)) if num_match else 999999
                files.append((num, f, path))
    files.sort(key=lambda x: x[0])
    return [t[1:] for t in files]  # (filename, fullpath)


def merge_chunk(ffmpeg_exe, file_paths, output_path):
    """Merge multiple video files into one with scale to Shorts size.
    Uses concat filter (re-encodes) to avoid freezing issues."""
    if not file_paths:
        return
    
    # Build filter_complex for concat with scaling
    inputs = []
    scaled = []
    for i, path in enumerate(file_paths):
        inputs.extend(["-i", path])
        # Scale each input to 1080x1920
        scaled.append(f"[{i}:v]scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")
    
    # Concat all scaled videos
    concat_inputs = "".join([f"[v{i}]" for i in range(len(file_paths))])
    concat_filter = f"{';'.join(scaled)};{concat_inputs}concat=n={len(file_paths)}:v=1:a=1[outv]"
    
    # Handle audio - concat audio streams
    audio_inputs = "".join([f"[{i}:a]" for i in range(len(file_paths))])
    audio_filter = f"{audio_inputs}concat=n={len(file_paths)}:v=0:a=1[outa]"
    
    # Combine filters
    filter_complex = f"{concat_filter};{audio_filter}"
    
    cmd = [
        ffmpeg_exe,
        "-y",
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "medium",  # Better quality than fast
        "-crf", str(VIDEO_QUALITY),  # Quality setting from config
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",  # Web optimization
        output_path,
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        # Fallback: try concat demuxer if filter fails
        list_fd, list_path = tempfile.mkstemp(suffix=".txt", text=True)
        try:
            with os.fdopen(list_fd, "w", encoding="utf-8") as f:
                for p in file_paths:
                    p_escaped = p.replace("'", "'\\''")
                    f.write(f"file '{p_escaped}'\n")
            vf = (
                f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            )
            cmd_fallback = [
                ffmpeg_exe,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", str(VIDEO_QUALITY),
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True)
        finally:
            try:
                os.unlink(list_path)
            except Exception:
                pass


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        if USE_EN:
            print("Usage: python merge_videos.py <username> [YYYY-MM-DD] [--all]")
            print("  Without --all: merge every", CHUNK_SIZE, "videos into merged_1, merged_2, ...")
            print("  With --all:   merge all videos into one (merged_all.mp4)")
            print("Example: python merge_videos.py dary_1256 --all")
        else:
            print("استخدام: python merge_videos.py <username> [YYYY-MM-DD] [--all]")
            print("  بدون --all: دمج كل", CHUNK_SIZE, "فيديوهات في ملف (merged_1, merged_2, ...)")
            print("  مع --all:   دمج كل الفيديوهات في فيديو واحد (merged_all.mp4)")
            print("مثال:   python merge_videos.py dary_1256 --all")
        print("\nFull command list: python SnapScrap.py help" if USE_EN else "\nقائمة كل الأوامر: python SnapScrap.py help")
        sys.exit(0)
    if len(sys.argv) < 2:
        print("Usage: python merge_videos.py <username> [YYYY-MM-DD] [--all]" if USE_EN else "استخدام: python merge_videos.py <username> [YYYY-MM-DD] [--all]")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if a not in ("--all", "--help", "-h", "--en")]
    merge_all = "--all" in sys.argv

    username = args[0]
    date_str = args[1] if len(args) > 1 else date.today().strftime("%Y-%m-%d")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(script_dir, "stories", username, date_str)
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}" if USE_EN else f"المجلد غير موجود: {folder}")
        sys.exit(1)

    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        if USE_EN:
            print("Install ffmpeg (add to PATH) or run: pip install imageio-ffmpeg")
        else:
            print("يجب توفير ffmpeg بأحد الطريقتين:")
            print("  1) تثبيت ffmpeg وإضافته إلى PATH: https://ffmpeg.org/download.html")
            print("  2) أو تثبيت الحزمة: pip install imageio-ffmpeg")
        sys.exit(1)

    videos = get_video_files(folder)
    if not videos:
        print(f"No .mp4 files in folder: {folder}" if USE_EN else f"لا توجد ملفات .mp4 في المجلد: {folder}")
        sys.exit(1)

    merged_path = os.path.join(folder, MERGED_DIR)
    os.makedirs(merged_path, exist_ok=True)

    if merge_all:
        paths = [p for _, p in videos]
        out_path = os.path.join(merged_path, "merged_all.mp4")
        print(f"Merging {len(videos)} videos into one: merged_all.mp4 ..." if USE_EN else f"دمج كل {len(videos)} فيديو في ملف واحد: merged_all.mp4 ...")
        try:
            merge_chunk(ffmpeg_exe, paths, out_path)
            print(f"Done: {out_path}" if USE_EN else f"تم: {out_path}")
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg error: {e}" if USE_EN else f"خطأ في ffmpeg: {e}")
            if e.stderr:
                print(e.stderr.decode(errors="replace"))
            sys.exit(1)
    else:
        chunks = []
        for i in range(0, len(videos), CHUNK_SIZE):
            chunk = videos[i : i + CHUNK_SIZE]
            if chunk:
                chunks.append(chunk)

        print(f"Videos: {len(videos)} -> merging every {CHUNK_SIZE} = {len(chunks)} file(s)." if USE_EN else f"عدد الفيديوهات: {len(videos)} → دمج كل {CHUNK_SIZE} في فيديو واحد = {len(chunks)} فيديو.")
        for idx, chunk in enumerate(chunks, start=1):
            paths = [p for _, p in chunk]
            out_name = f"merged_{idx}.mp4"
            out_path = os.path.join(merged_path, out_name)
            print(f"  Merge {idx}/{len(chunks)}: {out_name} ..." if USE_EN else f"  دمج {idx}/{len(chunks)}: {out_name} ...")
            try:
                merge_chunk(ffmpeg_exe, paths, out_path)
                print(f"    Done: {out_path}" if USE_EN else f"    تم: {out_path}")
            except subprocess.CalledProcessError as e:
                print(f"    ffmpeg error: {e}" if USE_EN else f"    خطأ في ffmpeg: {e}")
                if e.stderr:
                    print(e.stderr.decode(errors="replace"))

    print(f"\nDone. Merged files in: {merged_path}" if USE_EN else f"\nانتهى. الفيديوهات المدمجة في: {merged_path}")
    print("Upload: python upload_youtube_shorts.py" if USE_EN else "لرفعها على يوتيوب شورتس: python upload_youtube_shorts.py", username, date_str)


if __name__ == "__main__":
    main()
