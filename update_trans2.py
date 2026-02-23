import json
from pathlib import Path

translations_path = Path("W:/AntiGravity/SnapScrap/webapp/translations.json")

with open(translations_path, "r", encoding="utf-8") as f:
    t = json.load(f)

new_keys = {
    "dash_username_placeholder": {"ar": "أدخل اسم المستخدم (مثال: dary_1256)", "en": "Enter username (e.g. ishowspeed)", "fr": "Entrer nom d'utilisateur (ex: ishowspeed)"},
    "dash_bulk_add_placeholder": {"ar": "أو أضف حسابات متعددة (كل حساب في سطر)", "en": "Or add multiple accounts (one per line)", "fr": "Ou ajoutez plusieurs comptes (un par ligne)"},
    "dash_add": {"ar": "إضافة", "en": "Add", "fr": "Ajouter"},
    "dash_toggle_bulk_add": {"ar": "إضافة جملة / حساب واحد", "en": "Add Bulk / Single", "fr": "Ajout Groupé / Unique"},
    "dash_suggested_accounts": {"ar": "حسابات مقترحة", "en": "Suggested Accounts", "fr": "Comptes Suggérés"},
    "dash_refresh": {"ar": "تحديث", "en": "Refresh", "fr": "Rafraîchir"},
    "dash_add_selected": {"ar": "إضافة المحدد", "en": "Add Selected", "fr": "Ajouter la sélection"},
    "dash_without_adding_to_list": {"ar": "دون إضافة للقائمة", "en": "Without adding to list", "fr": "Sans ajouter à la liste"},
    "dash_merge_after_download": {"ar": "دمج بعد التحميل", "en": "Merge after download", "fr": "Fusionner après téléchargé"},
    "dash_download": {"ar": "تنزيل", "en": "Download", "fr": "Télécharger"},
    "dash_merge_videos": {"ar": "دمج الفيديوهات", "en": "Merge Videos", "fr": "Fusionner Vidéos"},
    "dash_merge": {"ar": "دمج", "en": "Merge", "fr": "Fusionner"},
    "dash_schedule": {"ar": "جدولة", "en": "Schedule", "fr": "Planifier"},
    "dash_enable_daily_schedule": {"ar": "تفعيل الجدولة اليومية", "en": "Enable Daily Schedule", "fr": "Activer la Planification Quotidienne"},
    "dash_save": {"ar": "حفظ", "en": "Save", "fr": "Enregistrer"},
    "dash_folder": {"ar": "مجلد", "en": "Folder", "fr": "Dossier"},
    "dash_file": {"ar": "ملف", "en": "File", "fr": "Fichier"},
    "dash_folders": {"ar": "مجلدات", "en": "Folders", "fr": "Dossiers"},
    "dash_channels": {"ar": "قنوات", "en": "Channels", "fr": "Chaînes"},
    "dash_channel": {"ar": "قناة", "en": "Channel", "fr": "Chaîne"},
    "dash_select_channel": {"ar": "اختر القناة", "en": "Select Channel", "fr": "Sélectionner la Chaîne"},
    "dash_select_folder": {"ar": "اختر المجلد", "en": "Select Folder", "fr": "Sélectionner le Dossier"},
    "dash_manual": {"ar": "يدوي", "en": "Manual", "fr": "Manuel"},
    "dash_user": {"ar": "المستخدم", "en": "User", "fr": "Utilisateur"},
    "dash_date": {"ar": "التاريخ", "en": "Date", "fr": "Date"},
    "dash_private": {"ar": "خاص", "en": "Private", "fr": "Privé"},
    "dash_unlisted": {"ar": "غير مدرج", "en": "Unlisted", "fr": "Non Répertorié"},
    "dash_public": {"ar": "عام", "en": "Public", "fr": "Public"},
    "dash_upload_selected": {"ar": "رفع المحدد", "en": "Upload Selected", "fr": "Téléverser la Sélection"},
    "dash_drag_file_here": {"ar": "اسحب ملف هنا", "en": "Drag file here", "fr": "Glissez le fichier ici"},
    "dash_title": {"ar": "العنوان", "en": "Title", "fr": "Titre"},
    "dash_upload_youtube": {"ar": "رفع YouTube", "en": "Upload to YouTube", "fr": "Publier sur YouTube"},
    "dash_bulk_upload": {"ar": "رفع الكل (Bulk Upload)", "en": "Bulk Upload", "fr": "Téléversement Groupé"},
    "dash_bulk_upload_desc": {"ar": "رفع جميع المجلدات الجاهزة وتوزيعها على القنوات", "en": "Upload all ready folders and distribute across channels", "fr": "Téléverser tous les dossiers prêts et distribuer aux chaînes"},
    "dash_select_channel_important": {"ar": "اختر القناة (مهم: اختر Content Creators Stories)", "en": "Select Channel (Important: Choose Content Creators Stories)", "fr": "Choisissez la chaîne (Important: Content Creators Stories)"},
    "dash_start_bulk_upload": {"ar": "بدء الرفع الشامل", "en": "Start Bulk Upload", "fr": "Démarrer le Téléversement Groupé"},
    "dash_manage_api_army": {"ar": "إدارة جيش المفاتيح", "en": "Manage API Army", "fr": "Gérer l'Armée d'API"},
    "dash_api_army_desc": {"ar": "لن تتوقف الرفوعات أبداً. أضف مفاتيح احتياطية لكل قناة، وسيقوم النظام بتدويرها تلقائياً عند نفاذ الحصة (Quota).", "en": "Uploads will never stop. Add backup tokens per channel, and the system will auto-rotate when quota runs out.", "fr": "Les téléversements ne s'arrêteront jamais. Ajoutez des clés de secours, le système les tournera auto si le quota s'épuise."},
    "dash_upload_client_secret": {"ar": "رفع ملف Client Secret جديد (Google Project)", "en": "Upload New Client Secret (Google Project)", "fr": "Téléverser nouveau Client Secret (Projet Google)"},
    "dash_client_secret_upload_success": {"ar": "تم رفع مشروع جوجل بنجاح! يمكن للنظام استخدامه.", "en": "Client Secret uploaded successfully! Ready to use.", "fr": "Client Secret téléchargé avec succès ! Prêt à l'emploi."},
    "dash_error": {"ar": "خطأ", "en": "Error", "fr": "Erreur"},
    "dash_ensure_correct_file": {"ar": "تأكد من اختيار ملف صحيح", "en": "Ensure you selected a valid file", "fr": "Veuillez choisir un fichier valide"},
    "dash_upload_error_occurred": {"ar": "حدث خطأ أثناء الرفع", "en": "An error occurred during upload", "fr": "Erreur lors du téléversement"},
    "dash_backup_keys": {"ar": "مفاتيح احتياطية", "en": "Backup Keys", "fr": "Clés de Secours"},
    "dash_add_key": {"ar": "إضافة مفتاح", "en": "Add Key", "fr": "Ajouter Clé"},
    "dash_no_youtube_channels_linked": {"ar": "لا توجد قنوات يوتيوب مرتبطة بعد. قم بإضافة قناة من الدخول.", "en": "No YouTube channels linked yet. Add one first.", "fr": "Aucune chaîne YouTube liée. Ajoutez-en une d'abord."},
    "dash_backup_key_added_success": {"ar": "تمت إضافة المفتاح الاحتياطي بنجاح! 🛡️", "en": "Backup Key added successfully! 🛡️", "fr": "Clé de secours ajoutée avec succès ! 🛡️"},
    "dash_ensure_correct_token_file": {"ar": "تأكد من اختيار ملف token.json صحيح", "en": "Ensure you chose a valid token.json file", "fr": "Veillez à choisir un fichier token.json valide"},
    "dash_manual_bridge_helper": {"ar": "مساعد الرفع اليدوي (Manual Bridge)", "en": "Manual Bridge Helper", "fr": "Assistant Manuel de Téléversement"},
    "dash_copy_caption": {"ar": "نسخ العنوان", "en": "Copy Caption", "fr": "Copier la Description"},
    "dash_open_folder": {"ar": "فتح المجلد", "en": "Open Folder", "fr": "Ouvrir Dossier"},
    "dash_open_tiktok": {"ar": "فتح TikTok", "en": "Open TikTok", "fr": "Ouvrir TikTok"},
    "dash_clean_up": {"ar": "تنظيف", "en": "Clean up", "fr": "Nettoyage"},
    "dash_delete": {"ar": "حذف", "en": "Delete", "fr": "Supprimer"}
}

for k, lang_dict in new_keys.items():
    if k not in t['ar']:  # Only update if missing to avoid overwriting existing ones.
        t['ar'][k] = lang_dict['ar']
        t['en'][k] = lang_dict['en']
        t['fr'][k] = lang_dict['fr']

with open(translations_path, "w", encoding="utf-8") as f:
    json.dump(t, f, ensure_ascii=False, indent=4)

print(f"Added {len(new_keys)} keys to translations.json!")
