#!/usr/bin/env python3
"""
تطبيق سطح مكتب تفاعلي لـ SnapScrap.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import subprocess
import os
import sys
import json
import re
from datetime import date, datetime, timedelta

# Fix Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Get script directory (works for both .py and .exe)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    # عند التشغيل كـ EXE من dist/، الملفات قد تكون في المجلد الأب
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = SCRIPT_DIR


def find_client_secret():
    """Find client_secret.json - checks SCRIPT_DIR and parent folder (for EXE in dist/)."""
    for d in (SCRIPT_DIR, PARENT_DIR):
        for name in ("client_secret.json", "client_secrets.json"):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


class SnapScrapGUI:
    def __init__(self, root):
        self.root = root

        # Dark theme
        self.apply_dark_theme()

        # Load settings
        self.config_file = os.path.join(SCRIPT_DIR, "gui_config.json")
        self.settings = self.load_settings()
        self.language = self.settings.get("language", "ar")  # ar or en
        
        # Set title based on language
        self.update_title()
        
        # Window size (removed fullscreen)
        self.root.geometry("1000x800")
        self.root.minsize(850, 650)
        
        # Try to set icon (if exists)
        icon_path = os.path.join(SCRIPT_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass
        
        self.running = False
        self.process_thread = None
        
        # Start scheduler thread if enabled
        self.scheduler_thread = None
        if self.settings.get("scheduler_enabled", False):
            self.start_scheduler_thread()
        
        self.setup_ui()
    
    def start_scheduler_thread(self):
        """Start scheduler monitoring thread."""
        def scheduler_loop():
            while True:
                try:
                    if self.settings.get("scheduler_enabled", False):
                        now = datetime.now()
                        hour = self.settings.get("scheduler_hour", 9)
                        minute = self.settings.get("scheduler_minute", 0)
                        
                        if now.hour == hour and now.minute == minute:
                            accounts = self.settings.get("scheduler_accounts", [])
                            if accounts:
                                upload = self.settings.get("scheduler_upload", False)
                                privacy = self.settings.get("scheduler_privacy", "private")
                                merge = self.settings.get("scheduler_merge", True)
                                self.root.after(0, lambda: self.start_batch_from_accounts(accounts, upload, privacy, merge))
                                # Wait 60 seconds to avoid running multiple times
                                threading.Event().wait(60)
                    threading.Event().wait(60)  # Check every minute
                except:
                    threading.Event().wait(60)
        
        self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
    def load_settings(self):
        """Load settings from config file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_settings(self):
        """Save settings to config file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def apply_dark_theme(self):
        """Apply dark theme - داكن جداً."""
        self.root.configure(bg="#08080c")
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.root.option_add("*Background", "#12121c")
        self.root.option_add("*Foreground", "#f5f5fa")
        self.root.option_add("*selectBackground", "#ff0050")
        self.root.option_add("*selectForeground", "white")
        self.root.option_add("*insertBackground", "#f5f5fa")

        style = ttk.Style()
        for t in ("clam", "alt", "default"):
            try:
                style.theme_use(t)
                break
            except tk.TclError:
                pass

        bg_dark = "#08080c"
        bg_card = "#0e0e14"
        bg_input = "#14141c"
        fg_light = "#f5f5fa"
        fg_muted = "#7a7a8a"
        accent = "#ff0050"

        style.configure(".", background=bg_card, foreground=fg_light)
        style.configure("TFrame", background=bg_card)
        style.configure("TLabel", background=bg_card, foreground=fg_light, padding=6)
        style.configure("TLabelframe", background=bg_card)
        style.configure("TLabelframe.Label", background=bg_card, foreground=fg_light, font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background=accent, foreground="white", padding=10)
        style.map("TButton", background=[("active", "#ff2d6a"), ("pressed", "#cc0040")])
        style.configure("TEntry", fieldbackground=bg_input, foreground=fg_light)
        style.configure("TCheckbutton", background=bg_card, foreground=fg_light)
        style.configure("TRadiobutton", background=bg_card, foreground=fg_light)
        style.configure("TSpinbox", fieldbackground=bg_input, foreground=fg_light, background=bg_card)
        style.configure("TNotebook", background=bg_dark)
        style.configure("TNotebook.Tab", background=bg_card, foreground=fg_muted, padding=12)
        style.map("TNotebook.Tab", background=[("selected", accent)], foreground=[("selected", "white")])
        style.configure("TProgressbar", background=accent, troughcolor=bg_input)
        style.configure("Horizontal.TProgressbar", background=accent, troughcolor=bg_input)

        if "TLabelframe" in style.element_names() or hasattr(style, "map"):
            try:
                style.configure("TLabelframe", bordercolor=bg_input)
            except Exception:
                pass

    def update_title(self):
        """Update window title based on language."""
        if self.language == "ar":
            self.root.title("SnapScrap - تحميل ستوريات Snapchat")
        else:
            self.root.title("SnapScrap - Snapchat Stories Downloader")
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab1, text=self.t("حساب واحد", "Single Account"))
        self.setup_single_account_tab(tab1)

        tab2_merge = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab2_merge, text=self.t("دمج فقط", "Merge Only"))
        self.setup_merge_only_tab(tab2_merge)

        tab2 = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab2, text=self.t("حسابات متعددة", "Batch Processing"))
        self.setup_batch_tab(tab2)

        tab_stats = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab_stats, text=self.t("إحصائيات", "Statistics"))
        self.setup_statistics_tab(tab_stats)

        tab_sched = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab_sched, text=self.t("جدولة", "Scheduler"))
        self.setup_scheduler_tab(tab_sched)

        tab3 = tk.Frame(notebook, bg="#0e0e14")
        notebook.add(tab3, text=self.t("الإعدادات", "Settings"))
        self.setup_settings_tab(tab3)
        
        # Progress bar
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.progress_var = tk.StringVar(value=self.t("جاهز", "Ready"))
        self.status_var = tk.StringVar(value=self.t("جاهز", "Ready"))
        ttk.Label(self.progress_frame, textvariable=self.progress_var, font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate', length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
        # Output log
        log_frame = ttk.LabelFrame(self.root, text=self.t("سجل العمليات", "Output Log"), padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD, bg="#1a1a28", fg="#f5f5fa", insertbackground="#f5f5fa", selectbackground="#ff0050")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar - dark
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.FLAT, anchor=tk.W, bg="#08080c", fg="#7a7a8a", font=("Segoe UI", 9))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
    
    def make_scrollable(self, parent):
        """Create a scrollable canvas with frame - للمحتوى الطويل."""
        container = tk.Frame(parent, bg="#0e0e14")
        container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, bg="#0e0e14", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg="#0e0e14")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _scroll(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _scroll)
        inner.bind("<MouseWheel>", _scroll)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return inner

    def t(self, ar_text, en_text):
        """Translate text based on current language."""
        return ar_text if self.language == "ar" else en_text
    
    def setup_single_account_tab(self, parent):
        scroll_area = self.make_scrollable(parent)
        frame = ttk.LabelFrame(scroll_area, text=self.t("تحميل ومعالجة", "Download & Process"), padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Username
        ttk.Label(frame, text=self.t("اسم المستخدم:", "Username:")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Date (optional)
        ttk.Label(frame, text=self.t("التاريخ (YYYY-MM-DD، اختياري):", "Date (YYYY-MM-DD, optional):")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_entry = ttk.Entry(frame, width=30)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Options
        self.merge_var = tk.BooleanVar(value=True)
        chunk_size = self.settings.get("chunk_size", 7)
        ttk.Checkbutton(frame, text=self.t(f"دمج الفيديوهات (كل {chunk_size})", f"Merge videos (every {chunk_size})"), variable=self.merge_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.merge_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text=self.t("دمج كل الفيديوهات في فيديو واحد", "Merge all into one video"), variable=self.merge_all_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.upload_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text=self.t("رفع على يوتيوب", "Upload to YouTube"), variable=self.upload_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Privacy
        ttk.Label(frame, text=self.t("خصوصية يوتيوب:", "YouTube Privacy:")).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.privacy_var = tk.StringVar(value="private")
        privacy_frame = ttk.Frame(frame)
        privacy_frame.grid(row=5, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(privacy_frame, text=self.t("خاص", "Private"), variable=self.privacy_var, value="private").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_frame, text=self.t("غير مدرج", "Unlisted"), variable=self.privacy_var, value="unlisted").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_frame, text=self.t("عام", "Public"), variable=self.privacy_var, value="public").pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        self.start_btn = ttk.Button(btn_frame, text=self.t("▶ بدء", "▶ Start"), command=self.start_single, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text=self.t("⏹ إيقاف", "⏹ Stop"), command=self.stop_process, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("📁 فتح المجلد", "📁 Open Folder"), command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("📁 فتح المدمجات", "📁 Open Merged"), command=self.open_merged_folder).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("💾 حفظ السجل", "💾 Save Log"), command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("🗑 مسح السجل", "🗑 Clear Log"), command=self.clear_log).pack(side=tk.LEFT, padx=5)
    
    def setup_merge_only_tab(self, parent):
        """Tab for merging already downloaded files."""
        scroll_area = self.make_scrollable(parent)
        frame = ttk.LabelFrame(scroll_area, text=self.t("دمج الملفات المحملة", "Merge Downloaded Files"), padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Username
        ttk.Label(frame, text=self.t("اسم المستخدم:", "Username:")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.merge_username_entry = ttk.Entry(frame, width=30)
        self.merge_username_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Date
        ttk.Label(frame, text=self.t("التاريخ (YYYY-MM-DD):", "Date (YYYY-MM-DD):")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.merge_date_entry = ttk.Entry(frame, width=30)
        self.merge_date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.merge_date_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Merge options
        self.merge_only_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text=self.t("دمج كل الفيديوهات في فيديو واحد", "Merge all into one video"), variable=self.merge_only_all_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        chunk_size = self.settings.get("chunk_size", 7)
        ttk.Label(frame, text=self.t(f"بدون هذا الخيار: سيتم دمج كل {chunk_size} فيديوهات في ملف", f"Without this: merges every {chunk_size} videos into files")).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.merge_start_btn =         ttk.Button(btn_frame, text=self.t("▶ بدء الدمج", "▶ Start Merge"), command=self.start_merge_only, width=15)
        self.merge_start_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("📁 فتح المجلد", "📁 Open Folder"), command=self.open_merge_folder).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=self.t("📊 معاينة الملفات", "📊 Preview Files"), command=self.preview_merge_files).pack(side=tk.LEFT, padx=5)
    
    def setup_batch_tab(self, parent):
        scroll_area = self.make_scrollable(parent)
        frame = ttk.LabelFrame(scroll_area, text=self.t("معالجة متعددة", "Batch Processing"), padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Accounts input
        lbl = ttk.Label(frame, text=self.t("الحسابات (واحد لكل سطر):", "Accounts (one per line):"), font=("Segoe UI", 10, "bold"))
        lbl.pack(anchor=tk.W, pady=(0, 8))
        self.accounts_text = scrolledtext.ScrolledText(frame, height=10, width=55, bg="#14141c", fg="#f5f5fa", insertbackground="#f5f5fa", selectbackground="#ff0050", font=("Consolas", 10))
        self.accounts_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Load accounts
        accounts_file = os.path.join(SCRIPT_DIR, "accounts.txt")
        if os.path.exists(accounts_file):
            try:
                with open(accounts_file, "r", encoding="utf-8") as f:
                    self.accounts_text.insert("1.0", f.read())
            except Exception:
                pass

        # Options frame - improved layout
        opts_frame = ttk.LabelFrame(frame, text=self.t("خيارات المعالجة", "Processing Options"), padding=12)
        opts_frame.pack(fill=tk.X, pady=(0, 15))

        self.batch_merge_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text=self.t("دمج الفيديوهات بعد التحميل", "Merge videos after download"), variable=self.batch_merge_var).pack(anchor=tk.W, pady=4)

        self.batch_upload_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_frame, text=self.t("رفع على يوتيوب", "Upload to YouTube"), variable=self.batch_upload_var).pack(anchor=tk.W, pady=4)

        privacy_row = ttk.Frame(opts_frame)
        privacy_row.pack(anchor=tk.W, pady=4)
        ttk.Label(privacy_row, text=self.t("الخصوصية:", "Privacy:")).pack(side=tk.LEFT, padx=(0, 10))
        self.batch_privacy_var = tk.StringVar(value="private")
        ttk.Radiobutton(privacy_row, text=self.t("خاص", "Private"), variable=self.batch_privacy_var, value="private").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_row, text=self.t("غير مدرج", "Unlisted"), variable=self.batch_privacy_var, value="unlisted").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_row, text=self.t("عام", "Public"), variable=self.batch_privacy_var, value="public").pack(side=tk.LEFT, padx=5)

        # Buttons - cleaner layout
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.batch_start_btn = ttk.Button(btn_frame, text=self.t("▶ بدء المعالجة", "▶ Start Batch"), command=self.start_batch, width=18)
        self.batch_start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.batch_stop_btn = ttk.Button(btn_frame, text=self.t("⏹ إيقاف", "⏹ Stop"), command=self.stop_process, state=tk.DISABLED, width=12)
        self.batch_stop_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text=self.t("💾 حفظ الحسابات", "💾 Save"), command=self.save_accounts, width=14).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text=self.t("📂 تحميل من ملف", "📂 Load"), command=self.load_accounts_file, width=14).pack(side=tk.LEFT, padx=4)
    
    def setup_statistics_tab(self, parent):
        """Statistics and system status tab."""
        scroll_area = self.make_scrollable(parent)
        # System Status
        status_frame = ttk.LabelFrame(scroll_area, text=self.t("حالة النظام", "System Status"), padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, state=tk.DISABLED, wrap=tk.WORD, bg="#1a1a28", fg="#f5f5fa", insertbackground="#f5f5fa", selectbackground="#ff0050")
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text=self.t("🔄 تحديث الحالة", "🔄 Refresh Status"), command=self.check_system_status).pack(side=tk.LEFT, padx=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(scroll_area, text=self.t("إحصائيات", "Statistics"), padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, state=tk.DISABLED, wrap=tk.WORD, bg="#1a1a28", fg="#f5f5fa", insertbackground="#f5f5fa", selectbackground="#ff0050")
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        stats_btn_frame = ttk.Frame(stats_frame)
        stats_btn_frame.pack(pady=5)
        ttk.Label(stats_btn_frame, text=self.t("اسم المستخدم:", "Username:")).pack(side=tk.LEFT, padx=5)
        self.stats_username_entry = ttk.Entry(stats_btn_frame, width=20)
        self.stats_username_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(stats_btn_frame, text=self.t("عرض الإحصائيات", "Show Statistics"), command=self.show_statistics).pack(side=tk.LEFT, padx=5)
        
        # Initial status check
        self.check_system_status()
    
    def setup_scheduler_tab(self, parent):
        """Scheduler tab for daily automation."""
        scroll_area = self.make_scrollable(parent)
        frame = ttk.LabelFrame(scroll_area, text=self.t("جدولة يومية", "Daily Scheduler"), padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Enable scheduler
        self.scheduler_enabled = tk.BooleanVar(value=self.settings.get("scheduler_enabled", False))
        ttk.Checkbutton(frame, text=self.t("تفعيل الجدولة اليومية", "Enable Daily Scheduler"), variable=self.scheduler_enabled, command=self.save_scheduler_setting).pack(anchor=tk.W, pady=5)
        
        # Time selection
        time_frame = ttk.LabelFrame(frame, text=self.t("وقت التشغيل", "Run Time"), padding=10)
        time_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(time_frame, text=self.t("الساعة:", "Hour:")).grid(row=0, column=0, padx=5)
        self.scheduler_hour = tk.StringVar(value=str(self.settings.get("scheduler_hour", 9)))
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.scheduler_hour, width=5, command=self.save_scheduler_setting)
        hour_spin.grid(row=0, column=1, padx=5)
        
        ttk.Label(time_frame, text=self.t("الدقيقة:", "Minute:")).grid(row=0, column=2, padx=5)
        self.scheduler_minute = tk.StringVar(value=str(self.settings.get("scheduler_minute", 0)))
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.scheduler_minute, width=5, command=self.save_scheduler_setting)
        minute_spin.grid(row=0, column=3, padx=5)
        
        # Accounts for scheduler
        ttk.Label(frame, text=self.t("الحسابات المجدولة:", "Scheduled Accounts:")).pack(anchor=tk.W, pady=(10, 5))
        self.scheduler_accounts_text = scrolledtext.ScrolledText(frame, height=8, width=50, bg="#1a1a28", fg="#f5f5fa", insertbackground="#f5f5fa", selectbackground="#ff0050")
        self.scheduler_accounts_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Load scheduler accounts
        scheduler_accounts = self.settings.get("scheduler_accounts", [])
        if scheduler_accounts:
            self.scheduler_accounts_text.insert("1.0", "\n".join(scheduler_accounts))
        
        # Options
        self.scheduler_merge_var = tk.BooleanVar(value=self.settings.get("scheduler_merge", True))
        ttk.Checkbutton(frame, text=self.t("دمج الفيديوهات بعد التحميل", "Merge videos after download"), variable=self.scheduler_merge_var, command=self.save_scheduler_setting).pack(anchor=tk.W, pady=4)
        self.scheduler_upload_var = tk.BooleanVar(value=self.settings.get("scheduler_upload", False))
        ttk.Checkbutton(frame, text=self.t("رفع على يوتيوب", "Upload to YouTube"), variable=self.scheduler_upload_var, command=self.save_scheduler_setting).pack(anchor=tk.W, pady=4)
        
        self.scheduler_privacy_var = tk.StringVar(value=self.settings.get("scheduler_privacy", "private"))
        privacy_frame = ttk.Frame(frame)
        privacy_frame.pack(anchor=tk.W, pady=5)
        ttk.Label(privacy_frame, text=self.t("الخصوصية:", "Privacy:")).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_frame, text=self.t("خاص", "Private"), variable=self.scheduler_privacy_var, value="private", command=self.save_scheduler_setting).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_frame, text=self.t("غير مدرج", "Unlisted"), variable=self.scheduler_privacy_var, value="unlisted", command=self.save_scheduler_setting).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(privacy_frame, text=self.t("عام", "Public"), variable=self.scheduler_privacy_var, value="public", command=self.save_scheduler_setting).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=self.t("💾 حفظ الإعدادات", "💾 Save Settings"), command=self.save_scheduler_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.t("▶ تشغيل الآن", "▶ Run Now"), command=self.run_scheduler_now).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text=self.t("\nملاحظة: الجدولة تعمل فقط عند تشغيل البرنامج.", "\nNote: Scheduler only works when the application is running."), font=("Arial", 8)).pack(anchor=tk.W, pady=5)
    
    def setup_settings_tab(self, parent):
        scroll_area = self.make_scrollable(parent)
        frame = ttk.LabelFrame(scroll_area, text=self.t("الإعدادات", "Settings"), padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Language selection
        lang_frame = ttk.LabelFrame(frame, text=self.t("اللغة", "Language"), padding=10)
        lang_frame.pack(fill=tk.X, pady=5)
        
        self.lang_var = tk.StringVar(value=self.language)
        lang_btn_frame = ttk.Frame(lang_frame)
        lang_btn_frame.pack(anchor=tk.W)
        
        ttk.Radiobutton(lang_btn_frame, text="العربية", variable=self.lang_var, value="ar", command=self.change_language).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(lang_btn_frame, text="English", variable=self.lang_var, value="en", command=self.change_language).pack(side=tk.LEFT, padx=10)
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(frame, text=self.t("إعدادات متقدمة", "Advanced Settings"), padding=10)
        advanced_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(advanced_frame, text=self.t("عدد الفيديوهات في كل دمج:", "Videos per merge:")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chunk_size_var = tk.StringVar(value=str(self.settings.get("chunk_size", 7)))
        chunk_spin = ttk.Spinbox(advanced_frame, from_=1, to=20, textvariable=self.chunk_size_var, width=5, command=self.save_advanced_settings)
        chunk_spin.grid(row=0, column=1, padx=5)
        
        ttk.Label(advanced_frame, text=self.t("جودة الفيديو (CRF):", "Video Quality (CRF):")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.video_quality_var = tk.StringVar(value=str(self.settings.get("video_quality", 23)))
        quality_spin = ttk.Spinbox(advanced_frame, from_=18, to=28, textvariable=self.video_quality_var, width=5, command=self.save_advanced_settings)
        quality_spin.grid(row=1, column=1, padx=5)
        ttk.Label(advanced_frame, text=self.t("(18=عالية, 28=منخفضة)", "(18=high, 28=low)"), font=("Arial", 8)).grid(row=1, column=2, padx=5)
        
        # Title Template
        title_frame = ttk.LabelFrame(frame, text=self.t("قالب العنوان", "Title Template"), padding=10)
        title_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(title_frame, text=self.t("استخدم: {username}, {date}, {part}", "Use: {username}, {date}, {part}")).pack(anchor=tk.W)
        self.title_template_var = tk.StringVar(value=self.settings.get("title_template", "ستوريات {username} | يوم {date} | الجزء {part}"))
        title_entry = ttk.Entry(title_frame, textvariable=self.title_template_var, width=60)
        title_entry.pack(fill=tk.X, pady=5)
        ttk.Button(title_frame, text=self.t("💾 حفظ", "💾 Save"), command=self.save_title_template).pack(anchor=tk.W, pady=5)
        
        # Cleanup Settings
        cleanup_frame = ttk.LabelFrame(frame, text=self.t("تنظيف الملفات", "File Cleanup"), padding=10)
        cleanup_frame.pack(fill=tk.X, pady=5)
        
        self.auto_cleanup_var = tk.BooleanVar(value=self.settings.get("auto_cleanup", False))
        ttk.Checkbutton(cleanup_frame, text=self.t("حذف الملفات القديمة تلقائياً", "Auto-delete old files"), variable=self.auto_cleanup_var, command=self.save_advanced_settings).pack(anchor=tk.W, pady=2)
        
        ttk.Label(cleanup_frame, text=self.t("احتفظ بالملفات لأيام:", "Keep files for days:")).pack(anchor=tk.W, pady=2)
        self.cleanup_days_var = tk.StringVar(value=str(self.settings.get("cleanup_days", 30)))
        cleanup_spin = ttk.Spinbox(cleanup_frame, from_=1, to=365, textvariable=self.cleanup_days_var, width=5, command=self.save_advanced_settings)
        cleanup_spin.pack(anchor=tk.W, pady=2)
        
        ttk.Button(cleanup_frame, text=self.t("🗑 تنظيف الآن", "🗑 Cleanup Now"), command=self.cleanup_old_files).pack(anchor=tk.W, pady=5)
        
        # Output Directory
        ttk.Label(frame, text=self.t("مجلد المخرجات:", "Output Directory:")).pack(anchor=tk.W, pady=5)
        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill=tk.X, pady=5)
        self.output_dir_var = tk.StringVar(value=SCRIPT_DIR)
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_frame, text=self.t("تصفح", "Browse"), command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Backup/Restore Settings
        backup_frame = ttk.LabelFrame(frame, text=self.t("نسخ احتياطي", "Backup"), padding=10)
        backup_frame.pack(fill=tk.X, pady=5)
        
        btn_backup_frame = ttk.Frame(backup_frame)
        btn_backup_frame.pack(anchor=tk.W)
        ttk.Button(btn_backup_frame, text=self.t("💾 تصدير الإعدادات", "💾 Export Settings"), command=self.export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_backup_frame, text=self.t("📥 استيراد الإعدادات", "📥 Import Settings"), command=self.import_settings).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text=self.t("\nملاحظة: تأكد من وجود:", "\nNote: Make sure you have:")).pack(anchor=tk.W, pady=10)
        ttk.Label(frame, text="• ffmpeg أو imageio-ffmpeg مثبت" if self.language == "ar" else "• ffmpeg or imageio-ffmpeg installed").pack(anchor=tk.W)
        ttk.Label(frame, text="• client_secret.json للرفع على يوتيوب (في مجلد البرنامج أو المجلد الأب)" if self.language == "ar" else "• client_secret.json for YouTube upload (in app folder or parent folder)").pack(anchor=tk.W)
        ttk.Label(frame, text="• حزم Python: bs4, requests, إلخ" if self.language == "ar" else "• Python packages: bs4, requests, etc.").pack(anchor=tk.W)
    
    def change_language(self):
        """Change language and reload UI."""
        new_lang = self.lang_var.get()
        if new_lang != self.language:
            self.language = new_lang
            self.settings["language"] = new_lang
            self.save_settings()
            self.update_title()
            messagebox.showinfo(
                self.t("تم", "Done"),
                self.t("تم تغيير اللغة. أعد تشغيل البرنامج لتطبيق التغييرات.", "Language changed. Restart the application to apply changes.")
            )
    
    def log(self, message, level="info"):
        """Log message with timestamp."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "info": "[INFO]",
            "success": "[✓]",
            "error": "[✗]",
            "warning": "[!]"
        }.get(level, "[INFO]")
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{timestamp} {prefix} {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(message[:50] + "..." if len(message) > 50 else message)
        self.root.update()
    
    def clear_log(self):
        """Clear the log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(self.t("تم مسح السجل", "Log cleared"))
    
    def save_log(self):
        """Save log to file."""
        log_content = self.log_text.get("1.0", tk.END)
        if not log_content.strip():
            messagebox.showinfo(self.t("معلومات", "Info"), self.t("السجل فارغ", "Log is empty"))
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[(self.t("ملفات نصية", "Text files"), "*.txt"), (self.t("جميع الملفات", "All files"), "*.*")],
            initialfile=f"snapscrap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(log_content)
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"تم حفظ السجل في: {filename}", f"Log saved to: {filename}"))
            except Exception as e:
                messagebox.showerror(self.t("خطأ", "Error"), self.t(f"فشل حفظ السجل: {e}", f"Failed to save log: {e}"))
    
    def export_settings(self):
        """Export settings to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[(self.t("ملفات JSON", "JSON files"), "*.json"), (self.t("جميع الملفات", "All files"), "*.*")],
            initialfile=f"snapscrap_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=2, ensure_ascii=False)
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"تم تصدير الإعدادات إلى: {filename}", f"Settings exported to: {filename}"))
            except Exception as e:
                messagebox.showerror(self.t("خطأ", "Error"), self.t(f"فشل تصدير الإعدادات: {e}", f"Failed to export settings: {e}"))
    
    def import_settings(self):
        """Import settings from file."""
        filename = filedialog.askopenfilename(
            filetypes=[(self.t("ملفات JSON", "JSON files"), "*.json"), (self.t("جميع الملفات", "All files"), "*.*")]
        )
        
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    imported_settings = json.load(f)
                
                if messagebox.askyesno(self.t("تأكيد", "Confirm"), self.t("هل تريد استبدال الإعدادات الحالية؟", "Replace current settings?")):
                    self.settings.update(imported_settings)
                    self.save_settings()
                    
                    # Reload UI elements
                    self.language = self.settings.get("language", "ar")
                    self.lang_var.set(self.language)
                    self.update_title()
                    
                    # Update other settings
                    if hasattr(self, 'chunk_size_var'):
                        self.chunk_size_var.set(str(self.settings.get("chunk_size", 7)))
                    if hasattr(self, 'video_quality_var'):
                        self.video_quality_var.set(str(self.settings.get("video_quality", 23)))
                    if hasattr(self, 'title_template_var'):
                        self.title_template_var.set(self.settings.get("title_template", "ستوريات {username} | يوم {date} | الجزء {part}"))
                    
                    messagebox.showinfo(
                        self.t("نجح", "Success"),
                        self.t("تم استيراد الإعدادات. قد تحتاج لإعادة تشغيل البرنامج.", "Settings imported. You may need to restart the application.")
                    )
            except Exception as e:
                messagebox.showerror(self.t("خطأ", "Error"), self.t(f"فشل استيراد الإعدادات: {e}", f"Failed to import settings: {e}"))
    
    def start_merge_only(self):
        """Start merge only (no download)."""
        if self.running:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("العملية قيد التشغيل بالفعل!", "Process already running!"))
            return
        
        username = self.merge_username_entry.get().strip()
        if not username:
            messagebox.showerror(self.t("خطأ", "Error"), self.t("الرجاء إدخال اسم مستخدم!", "Please enter a username!"))
            return
        
        date_str = self.merge_date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        merge_all = self.merge_only_all_var.get()
        
        self.running = True
        self.merge_start_btn.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.progress_var.set(self.t("جاري الدمج...", "Merging..."))
        self.log(self.t(f"بدء دمج الفيديوهات لـ: {username}", f"Starting merge for: {username}"), "info")
        
        self.process_thread = threading.Thread(target=self.run_merge_only, args=(username, date_str, merge_all))
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def run_merge_only(self, username, date_str, merge_all):
        """Run merge only process."""
        try:
            if not self.running:
                return
            
            # Get Python executable
            if getattr(sys, 'frozen', False):
                import shutil
                python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
            else:
                python_exe = sys.executable
            
            # Merge
            self.log(self.t(f"دمج الفيديوهات...", "Merging videos..."), "info")
            merge_cmd = [python_exe, os.path.join(SCRIPT_DIR, "merge_videos.py"), username, date_str]
            if merge_all:
                merge_cmd.append("--all")
            result = subprocess.run(merge_cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.log(line, "info")
            if result.stderr:
                self.log(f"{self.t('خطأ:', 'Error:')} {result.stderr}", "error")
            
            if self.running:
                self.log(self.t("اكتمل الدمج بنجاح!", "Merge completed successfully!"), "success")
                self.progress_var.set(self.t("مكتمل", "Completed"))
                self.show_notification(
                    self.t("اكتمل الدمج", "Merge Completed"),
                    self.t(f"اكتمل الدمج لـ {username}!", f"Merge completed for {username}!")
                )
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"اكتمل الدمج لـ {username}!", f"Merge completed for {username}!"))
        except Exception as e:
            self.log(f"{self.t('خطأ:', 'Error:')} {e}", "error")
            messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('حدث خطأ:', 'An error occurred:')} {e}")
        finally:
            self.running = False
            self.progress_bar.stop()
            self.root.after(0, lambda: self.merge_start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set(self.t("جاهز", "Ready")))
    
    def open_merge_folder(self):
        """Open merge folder."""
        username = self.merge_username_entry.get().strip()
        if not username:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل اسم مستخدم أولاً!", "Enter a username first!"))
            return
        
        date_str = self.merge_date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        folder = os.path.join(SCRIPT_DIR, username, date_str)
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showinfo(self.t("معلومات", "Info"), self.t(f"المجلد غير موجود: {folder}", f"Folder not found: {folder}"))
    
    def preview_merge_files(self):
        """Preview files that will be merged."""
        username = self.merge_username_entry.get().strip()
        if not username:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل اسم مستخدم أولاً!", "Enter a username first!"))
            return
        
        date_str = self.merge_date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        folder = os.path.join(SCRIPT_DIR, username, date_str)
        
        if not os.path.exists(folder):
            messagebox.showinfo(self.t("معلومات", "Info"), self.t(f"المجلد غير موجود: {folder}", f"Folder not found: {folder}"))
            return
        
        # Get video files
        video_files = []
        for f in os.listdir(folder):
            if f.lower().endswith('.mp4'):
                file_path = os.path.join(folder, f)
                try:
                    size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    video_files.append((f, size))
                except:
                    video_files.append((f, 0))
        
        def get_file_number(filename):
            match = re.match(r'^(\d+)', filename)
            return int(match.group(1)) if match else 999999
        
        video_files.sort(key=lambda x: get_file_number(x[0]))
        
        if not video_files:
            messagebox.showinfo(self.t("معلومات", "Info"), self.t("لا توجد ملفات فيديو في المجلد", "No video files found in folder"))
            return
        
        # Show preview
        preview_text = self.t(f"الملفات الموجودة ({len(video_files)}):\n", f"Files found ({len(video_files)}):\n")
        preview_text += "\n".join([f"{i+1}. {f} ({size:.2f} MB)" for i, (f, size) in enumerate(video_files)])
        
        # Create preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title(self.t("معاينة الملفات", "Preview Files"))
        preview_window.geometry("500x400")
        
        preview_window.configure(bg="#0a0a0f")
        text_widget = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD, bg="#1a1a28", fg="#f5f5fa", insertbackground="#f5f5fa")
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", preview_text)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(preview_window, text=self.t("إغلاق", "Close"), command=preview_window.destroy).pack(pady=5)
    
    def start_single(self):
        if self.running:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("العملية قيد التشغيل بالفعل!", "Process already running!"))
            return
        
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror(self.t("خطأ", "Error"), self.t("الرجاء إدخال اسم مستخدم!", "Please enter a username!"))
            return
        
        date_str = self.date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        merge = self.merge_var.get()
        merge_all = self.merge_all_var.get()
        upload = self.upload_var.get()
        privacy = self.privacy_var.get()
        
        if not merge and not upload:
            if not messagebox.askyesno(self.t("تأكيد", "Confirm"), self.t("لم يتم اختيار دمج أو رفع. تحميل فقط؟", "No merge or upload selected. Only download?")):
                return
        
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar.start(10)
        self.progress_var.set(self.t("جاري المعالجة...", "Processing..."))
        self.log(self.t(f"بدء العملية لـ: {username}", f"Starting process for: {username}"), "info")
        
        self.process_thread = threading.Thread(target=self.run_single_process, args=(username, date_str, merge, merge_all, upload, privacy))
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def stop_process(self):
        """Stop the running process."""
        if self.running:
            if messagebox.askyesno(self.t("إيقاف", "Stop"), self.t("هل أنت متأكد من إيقاف العملية؟", "Are you sure you want to stop the process?")):
                self.running = False
                self.log(self.t("تم إيقاف العملية من قبل المستخدم", "Process stopped by user"), "warning")
                self.progress_bar.stop()
                self.progress_var.set(self.t("متوقف", "Stopped"))
                self.status_var.set(self.t("تم إيقاف العملية", "Process stopped"))
    
    def run_single_process(self, username, date_str, merge, merge_all, upload, privacy):
        try:
            if not self.running:
                return
            
            # Get Python executable (works for both script and exe)
            if getattr(sys, 'frozen', False):
                # Running as exe - need to find Python
                python_exe = sys.executable  # Use exe itself or find python
                # Try to find python in PATH
                import shutil
                python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
            else:
                python_exe = sys.executable
            
            # Download
            self.log(self.t(f"[1/3] تحميل الستوريات لـ {username}...", f"[1/3] Downloading stories for {username}..."), "info")
            cmd = [python_exe, os.path.join(SCRIPT_DIR, "SnapScrap.py"), username]
            result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.log(line, "info")
            if result.stderr:
                self.log(f"Error: {result.stderr}", "error")
            
            if not self.running:
                return
            
            # Merge
            if merge:
                self.log(self.t(f"[2/3] دمج الفيديوهات...", f"[2/3] Merging videos..."), "info")
                merge_cmd = [python_exe, os.path.join(SCRIPT_DIR, "merge_videos.py"), username, date_str]
                if merge_all:
                    merge_cmd.append("--all")
                result = subprocess.run(merge_cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            self.log(line, "info")
                if result.stderr:
                    self.log(f"Error: {result.stderr}", "error")
            
            if not self.running:
                return
            
            # Upload
            if upload:
                self.log(self.t(f"[3/3] رفع على يوتيوب...", f"[3/3] Uploading to YouTube..."), "info")
                upload_cmd = [python_exe, os.path.join(SCRIPT_DIR, "daily_automation.py"), username, privacy]
                result = subprocess.run(upload_cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            self.log(line, "info")
                if result.stderr:
                    self.log(f"Error: {result.stderr}", "error")
            
            if self.running:
                self.log(self.t("اكتملت العملية بنجاح!", "Process completed successfully!"), "success")
                self.progress_var.set(self.t("مكتمل", "Completed"))
                self.show_notification(
                    self.t("اكتملت العملية", "Process Completed"),
                    self.t(f"اكتملت العملية لـ {username}!", f"Process completed for {username}!")
                )
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"اكتملت العملية لـ {username}!", f"Process completed for {username}!"))
        except Exception as e:
            self.log(f"{self.t('خطأ:', 'Error:')} {e}", "error")
            messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('حدث خطأ:', 'An error occurred:')} {e}")
        finally:
            self.running = False
            self.progress_bar.stop()
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_var.set(self.t("جاهز", "Ready")))
    
    def start_batch(self):
        if self.running:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("العملية قيد التشغيل بالفعل!", "Process already running!"))
            return
        
        accounts_text = self.accounts_text.get("1.0", tk.END).strip()
        if not accounts_text:
            messagebox.showerror(self.t("خطأ", "Error"), self.t("الرجاء إدخال حساب واحد على الأقل!", "Please enter at least one account!"))
            return
        
        accounts = [line.strip() for line in accounts_text.split("\n") if line.strip() and not line.strip().startswith("#")]
        if not accounts:
            messagebox.showerror(self.t("خطأ", "Error"), self.t("لم يتم العثور على حسابات صحيحة!", "No valid accounts found!"))
            return
        
        upload = self.batch_upload_var.get()
        merge = self.batch_merge_var.get()
        privacy = self.batch_privacy_var.get()

        self.running = True
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        self.progress_bar.start(10)
        self.progress_var.set(self.t(f"معالجة {len(accounts)} حساب...", f"Processing {len(accounts)} account(s)..."))
        self.log(self.t(f"بدء معالجة {len(accounts)} حساب... (دمج: {'نعم' if merge else 'لا'})", f"Starting batch for {len(accounts)} account(s)... (merge: {'yes' if merge else 'no'})"), "info")

        self.process_thread = threading.Thread(target=self.run_batch_process, args=(accounts, upload, privacy, merge))
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def run_batch_process(self, accounts, upload, privacy, do_merge=True):
        try:
            from daily_automation import process_account
            for idx, username in enumerate(accounts, start=1):
                if not self.running:
                    break
                self.log(self.t(f"\n[{idx}/{len(accounts)}] معالجة: {username}", f"\n[{idx}/{len(accounts)}] Processing: {username}"), "info")
                self.progress_var.set(self.t(f"معالجة {username} ({idx}/{len(accounts)})", f"Processing {username} ({idx}/{len(accounts)})"))
                process_account(username, upload, privacy, do_merge)
            
            if self.running:
                self.log(self.t("اكتملت معالجة الحسابات بنجاح!", "Batch process completed successfully!"), "success")
                self.progress_var.set(self.t("مكتمل", "Completed"))
                self.show_notification(
                    self.t("اكتملت المعالجة", "Batch Completed"),
                    self.t(f"اكتملت معالجة {len(accounts)} حساب!", f"Batch process completed for {len(accounts)} account(s)!")
                )
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"اكتملت معالجة {len(accounts)} حساب!", f"Batch process completed for {len(accounts)} account(s)!"))
        except Exception as e:
            self.log(f"{self.t('خطأ:', 'Error:')} {e}", "error")
            messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('حدث خطأ:', 'An error occurred:')} {e}")
        finally:
            self.running = False
            self.progress_bar.stop()
            self.root.after(0, lambda: self.batch_start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.batch_stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_var.set(self.t("جاهز", "Ready")))
    
    def load_accounts_file(self):
        """Load accounts from file."""
        accounts_file = os.path.join(SCRIPT_DIR, "accounts.txt")
        if os.path.exists(accounts_file):
            try:
                with open(accounts_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.accounts_text.delete("1.0", tk.END)
                    self.accounts_text.insert("1.0", content)
                messagebox.showinfo(self.t("نجح", "Success"), self.t(f"تم تحميل الحسابات من {accounts_file}", f"Loaded accounts from {accounts_file}"))
            except Exception as e:
                messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('فشل التحميل:', 'Failed to load:')} {e}")
        else:
            messagebox.showinfo(self.t("معلومات", "Info"), self.t(f"الملف غير موجود: {accounts_file}", f"File not found: {accounts_file}"))
    
    def save_accounts(self):
        accounts_text = self.accounts_text.get("1.0", tk.END)
        accounts_file = os.path.join(SCRIPT_DIR, "accounts.txt")
        try:
            with open(accounts_file, "w", encoding="utf-8") as f:
                f.write(accounts_text)
            messagebox.showinfo(self.t("نجح", "Success"), self.t(f"تم حفظ الحسابات في {accounts_file}", f"Accounts saved to {accounts_file}"))
        except Exception as e:
            messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('فشل الحفظ:', 'Failed to save:')} {e}")
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def open_output_folder(self):
        """Open download folder."""
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل اسم مستخدم أولاً!", "Enter a username first!"))
            return
        
        date_str = self.date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        folder = os.path.join(SCRIPT_DIR, username, date_str)
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showinfo(self.t("معلومات", "Info"), self.t(f"المجلد غير موجود: {folder}", f"Folder not found: {folder}"))
    
    def open_merged_folder(self):
        """Open merged videos folder."""
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل اسم مستخدم أولاً!", "Enter a username first!"))
            return
        
        date_str = self.date_entry.get().strip() or date.today().strftime("%Y-%m-%d")
        merged_folder = os.path.join(SCRIPT_DIR, username, date_str, "merged")
        if os.path.exists(merged_folder):
            os.startfile(merged_folder)
        else:
            messagebox.showinfo(self.t("معلومات", "Info"), self.t(f"مجلد المدمجات غير موجود: {merged_folder}", f"Merged folder not found: {merged_folder}"))


    def check_system_status(self):
        """Check system status (FFmpeg, YouTube API, etc.)."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        
        status_lines = []
        
        # Check FFmpeg
        try:
            import subprocess
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            status_lines.append(self.t("✓ FFmpeg: مثبت", "✓ FFmpeg: Installed"))
        except:
            try:
                import imageio_ffmpeg
                exe = imageio_ffmpeg.get_ffmpeg_exe()
                if exe:
                    status_lines.append(self.t("✓ FFmpeg: من imageio-ffmpeg", "✓ FFmpeg: From imageio-ffmpeg"))
                else:
                    status_lines.append(self.t("✗ FFmpeg: غير موجود", "✗ FFmpeg: Not found"))
            except:
                status_lines.append(self.t("✗ FFmpeg: غير موجود", "✗ FFmpeg: Not found"))
        
        # Check YouTube API (checks SCRIPT_DIR and parent for EXE)
        client_secret = find_client_secret()
        if client_secret:
            status_lines.append(self.t("✓ YouTube API: جاهز", "✓ YouTube API: Ready"))
        else:
            status_lines.append(self.t("✗ YouTube API: client_secret.json غير موجود", "✗ YouTube API: client_secret.json not found"))
        
        # Check Python packages
        packages = ["bs4", "requests", "googleapiclient"]
        for pkg in packages:
            try:
                __import__(pkg)
                status_lines.append(self.t(f"✓ {pkg}: مثبت", f"✓ {pkg}: Installed"))
            except:
                status_lines.append(self.t(f"✗ {pkg}: غير مثبت", f"✗ {pkg}: Not installed"))
        
        # Check imageio-ffmpeg
        try:
            import imageio_ffmpeg
            status_lines.append(self.t("✓ imageio-ffmpeg: مثبت", "✓ imageio-ffmpeg: Installed"))
        except:
            status_lines.append(self.t("✗ imageio-ffmpeg: غير مثبت", "✗ imageio-ffmpeg: Not installed"))
        
        self.status_text.insert("1.0", "\n".join(status_lines))
        self.status_text.config(state=tk.DISABLED)
    
    def show_statistics(self):
        """Show statistics for a username."""
        username = self.stats_username_entry.get().strip()
        if not username:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل اسم مستخدم!", "Enter a username!"))
            return
        
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        
        stats_lines = [self.t(f"إحصائيات لـ: {username}", f"Statistics for: {username}"), "=" * 50]
        
        user_folder = os.path.join(SCRIPT_DIR, username)
        if not os.path.exists(user_folder):
            stats_lines.append(self.t("المجلد غير موجود", "Folder not found"))
        else:
            total_stories = 0
            total_size = 0
            dates = []
            
            for date_folder in os.listdir(user_folder):
                date_path = os.path.join(user_folder, date_folder)
                if os.path.isdir(date_path) and len(date_folder) == 10:  # YYYY-MM-DD format
                    dates.append(date_folder)
                    for file in os.listdir(date_path):
                        if file.endswith(('.mp4', '.jpeg')):
                            total_stories += 1
                            file_path = os.path.join(date_path, file)
                            try:
                                total_size += os.path.getsize(file_path)
                            except:
                                pass
            
            stats_lines.append(self.t(f"عدد الستوريات: {total_stories}", f"Total Stories: {total_stories}"))
            stats_lines.append(self.t(f"الحجم الإجمالي: {total_size / (1024*1024):.2f} MB", f"Total Size: {total_size / (1024*1024):.2f} MB"))
            stats_lines.append(self.t(f"عدد الأيام: {len(dates)}", f"Number of Days: {len(dates)}"))
            if dates:
                stats_lines.append(self.t(f"أول تاريخ: {min(dates)}", f"First Date: {min(dates)}"))
                stats_lines.append(self.t(f"آخر تاريخ: {max(dates)}", f"Last Date: {max(dates)}"))
        
        self.stats_text.insert("1.0", "\n".join(stats_lines))
        self.stats_text.config(state=tk.DISABLED)
    
    def save_scheduler_setting(self):
        """Save scheduler setting."""
        self.settings["scheduler_enabled"] = self.scheduler_enabled.get()
        self.settings["scheduler_hour"] = int(self.scheduler_hour.get())
        self.settings["scheduler_minute"] = int(self.scheduler_minute.get())
        self.settings["scheduler_merge"] = self.scheduler_merge_var.get()
        self.settings["scheduler_upload"] = self.scheduler_upload_var.get()
        self.settings["scheduler_privacy"] = self.scheduler_privacy_var.get()
        self.save_settings()
    
    def save_scheduler_settings(self):
        """Save all scheduler settings."""
        accounts_text = self.scheduler_accounts_text.get("1.0", tk.END).strip()
        accounts = [line.strip() for line in accounts_text.split("\n") if line.strip() and not line.strip().startswith("#")]
        self.settings["scheduler_accounts"] = accounts
        self.save_scheduler_setting()
        messagebox.showinfo(self.t("نجح", "Success"), self.t("تم حفظ إعدادات الجدولة", "Scheduler settings saved"))
    
    def run_scheduler_now(self):
        """Run scheduler tasks now."""
        accounts_text = self.scheduler_accounts_text.get("1.0", tk.END).strip()
        if not accounts_text:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("أدخل حسابات!", "Enter accounts!"))
            return
        
        accounts = [line.strip() for line in accounts_text.split("\n") if line.strip() and not line.strip().startswith("#")]
        if not accounts:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("لا توجد حسابات صحيحة!", "No valid accounts!"))
            return
        
        upload = self.scheduler_upload_var.get()
        privacy = self.scheduler_privacy_var.get()
        do_merge = self.scheduler_merge_var.get()
        self.start_batch_from_accounts(accounts, upload, privacy, do_merge)
    
    def start_batch_from_accounts(self, accounts, upload, privacy, do_merge=True):
        """Start batch process from account list."""
        if self.running:
            messagebox.showwarning(self.t("تحذير", "Warning"), self.t("العملية قيد التشغيل بالفعل!", "Process already running!"))
            return

        self.running = True
        self.progress_bar.start(10)
        self.progress_var.set(self.t(f"معالجة {len(accounts)} حساب...", f"Processing {len(accounts)} account(s)..."))
        self.log(self.t(f"بدء معالجة {len(accounts)} حساب...", f"Starting batch for {len(accounts)} account(s)..."), "info")

        self.process_thread = threading.Thread(target=self.run_batch_process, args=(accounts, upload, privacy, do_merge))
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def save_advanced_settings(self):
        """Save advanced settings."""
        try:
            self.settings["chunk_size"] = int(self.chunk_size_var.get())
            self.settings["video_quality"] = int(self.video_quality_var.get())
            self.settings["auto_cleanup"] = self.auto_cleanup_var.get()
            self.settings["cleanup_days"] = int(self.cleanup_days_var.get())
            self.save_settings()
        except:
            pass
    
    def save_title_template(self):
        """Save title template."""
        self.settings["title_template"] = self.title_template_var.get()
        self.save_settings()
        messagebox.showinfo(self.t("نجح", "Success"), self.t("تم حفظ قالب العنوان", "Title template saved"))
    
    def cleanup_old_files(self):
        """Clean up old files."""
        days = int(self.cleanup_days_var.get())
        if not messagebox.askyesno(self.t("تأكيد", "Confirm"), self.t(f"حذف الملفات الأقدم من {days} يوم؟", f"Delete files older than {days} days?")):
            return
        
        deleted_count = 0
        deleted_size = 0
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for item in os.listdir(SCRIPT_DIR):
                item_path = os.path.join(SCRIPT_DIR, item)
                if os.path.isdir(item_path):
                    # Check date folders
                    for date_folder in os.listdir(item_path):
                        date_path = os.path.join(item_path, date_folder)
                        if os.path.isdir(date_path) and len(date_folder) == 10:
                            try:
                                folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
                                if folder_date < cutoff_date:
                                    # Delete old folder
                                    import shutil
                                    size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                             for dirpath, dirnames, filenames in os.walk(date_path)
                                             for filename in filenames)
                                    shutil.rmtree(date_path)
                                    deleted_count += 1
                                    deleted_size += size
                            except:
                                pass
        except Exception as e:
            messagebox.showerror(self.t("خطأ", "Error"), f"{self.t('خطأ في التنظيف:', 'Cleanup error:')} {e}")
            return
        
        messagebox.showinfo(
            self.t("نجح", "Success"),
            self.t(f"تم حذف {deleted_count} مجلد ({deleted_size / (1024*1024):.2f} MB)", f"Deleted {deleted_count} folders ({deleted_size / (1024*1024):.2f} MB)")
        )
        self.log(self.t(f"تم التنظيف: {deleted_count} مجلد", f"Cleanup: {deleted_count} folders"), "success")
    
    def show_notification(self, title, message):
        """Show Windows notification."""
        try:
            if sys.platform == "win32":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=5, threaded=True)
                except ImportError:
                    # Fallback: use Windows built-in notification
                    try:
                        import ctypes
                        ctypes.windll.user32.MessageBoxW(0, message, title, 0)
                    except:
                        pass
        except:
            pass


def main():
    root = tk.Tk()
    root.configure(bg="#08080c")
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    app = SnapScrapGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
