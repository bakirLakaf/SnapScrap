import json
from pathlib import Path

translations_path = Path("W:/AntiGravity/SnapScrap/webapp/translations.json")

with open(translations_path, "r", encoding="utf-8") as f:
    t = json.load(f)

# Update enterprise names for better accuracy
t['ar']['tier_ent_name'] = "الشركات (Enterprise)"
t['ar']['feat_proxy'] = "IP خاص (Dedicated Proxy)"
t['ar']['stats_army_desc'] = "تبديل تلقائي لمفاتيح API"
t['en']['stats_army_desc'] = "Auto API Key Swap"

dashboard_keys = {
    "dash_accounts": {"ar": "الحسابات المضافة", "en": "Added Accounts", "fr": "Comptes Ajoutés"},
    "dash_all": {"ar": "الكل", "en": "All", "fr": "Tout"},
    "dash_none": {"ar": "لا أحد", "en": "None", "fr": "Aucun"},
    "dash_empty": {"ar": "لا توجد حسابات", "en": "No accounts", "fr": "Aucun compte"},
    "dash_auto_merge": {"ar": "دمج تلقائي", "en": "Auto Merge", "fr": "Fusion Auto"},
    "dash_download_selected": {"ar": "تنزيل المحدد", "en": "Download Selected", "fr": "Télécharger Sélection"},
    "dash_admin_panel": {"ar": "لوحة الإدارة 👑", "en": "Admin Panel 👑", "fr": "Plateau Admin 👑"},
    "dash_free_tier": {"ar": "الباقة المجانية", "en": "Free Tier", "fr": "Forfait Gratuit"},
    "dash_free_limits": {"ar": "أنت حالياً تستخدم الباقة المجانية بحد أقصى (2) حسابات. للوصول لعدد أكبر وجدولة أسرع وجيش API، قم بالترقية للـ Pro.", "en": "You are currently on the Free tier (max 2 accounts). To bypass limits, unlock faster scheduling, and use API Armies, upgrade to Pro.", "fr": "Vous êtes sur le forfait Gratuit (max 2 comptes). Pour débloquer plus de limites et utiliser des armées d'API, passez à Pro."},
    "dash_upgrade_pro": {"ar": "ترقية إلى Pro", "en": "Upgrade to Pro", "fr": "Passer à Pro"},
    "dash_quick_download": {"ar": "جلب رابط سريع", "en": "Quick Download", "fr": "Téléchargement Rapide"},
    "dash_url_placeholder": {"ar": "رابط ستوري سناب شات...", "en": "Snapchat Story URL...", "fr": "URL de la story Snapchat..."},
    "dash_add_accounts": {"ar": "إضافة حسابات سناب شات وتخصيص الجدولة", "en": "Add Snapchat Accounts & Configure Scheduling", "fr": "Ajouter des comptes Snapchat & Configurer la planification"},
    "dash_username": {"ar": "اسم المستخدم (مثال: ishowspeed)", "en": "Username (e.g. ishowspeed)", "fr": "Nom d'utilisateur (ex: ishowspeed)"},
    "dash_fetch": {"ar": "جلب الملف الشخصي", "en": "Fetch Profile", "fr": "Récupérer Profil"},
    "dash_schedule_time": {"ar": "وقت التشغيل (24H)", "en": "Run Time (24H)", "fr": "Heure d'exécution (24H)"},
    "dash_youtube_channel": {"ar": "رفع إلى قناة يوتيوب (يجب تفعيل OAuth)", "en": "Upload to YouTube Channel (OAuth required)", "fr": "Uploader vers Chaîne YouTube (OAuth requis)"},
    "dash_no_channels": {"ar": "لم يتم تفعيل قنوات يوتيوب. أضف JSON.", "en": "No YouTube channels linked. Add JSON.", "fr": "Aucune chaîne YouTube liée."},
    "dash_add_account_btn": {"ar": "حفظ وإضافة الحساب للجدولة", "en": "Save & Add Account to Schedule", "fr": "Enregistrer & Ajouter le compte"},
    "dash_schedule_disclaimer": {"ar": "النظام سيقوم آلياً بتحميل ستوريات هذا الحساب يومياً في التوقيت المحدد ودمجها ورفعها لقناتك المختارة بصيغة Shorts.", "en": "The system will automatically download these stories daily at the set time, merge them, and upload them to your selected channel as Shorts.", "fr": "Le système téléchargera automatiquement ces stories tous les jours à l'heure définie, les fusionnera et les mettra en ligne en tant que Shorts."},
    "dash_status_wait": {"ar": "بانتظار بدء الجلب...", "en": "Waiting to start fetching...", "fr": "En attente..."},
    "dash_status_fetching": {"ar": "جاري التحميل...", "en": "Downloading...", "fr": "Téléchargement en cours..."},
    "dash_status_merging": {"ar": "جاري دمج الفيديوهات...", "en": "Merging videos...", "fr": "Fusion des vidéos..."},
    "dash_status_uploading": {"ar": "جاري الرفع ليوتيوب...", "en": "Uploading to YouTube...", "fr": "Mise en ligne YouTube..."},
    "dash_status_done": {"ar": "اكتملت العملية بنجاح! 🎉", "en": "Process completed successfully! 🎉", "fr": "Processus terminé ! 🎉"}
}

for k, lang_dict in dashboard_keys.items():
    t['ar'][k] = lang_dict['ar']
    t['en'][k] = lang_dict['en']
    t['fr'][k] = lang_dict['fr']

with open(translations_path, "w", encoding="utf-8") as f:
    json.dump(t, f, ensure_ascii=False, indent=4)

print("Updated translations.json successfully!")
