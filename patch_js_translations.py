import json
import re
from pathlib import Path

translations_path = Path("W:/AntiGravity/SnapScrap/webapp/translations.json")
app_js_path = Path("W:/AntiGravity/SnapScrap/webapp/static/app.js")

with open(translations_path, "r", encoding="utf-8") as f:
    t = json.load(f)

js_keys = {
    "js_status_success": {"ar": "تم بنجاح", "en": "Success", "fr": "Succès"},
    "js_status_error": {"ar": "خطأ", "en": "Error", "fr": "Erreur"},
    "js_status_processing": {"ar": "جاري المعالجة...", "en": "Processing...", "fr": "Traitement..."},
    "js_status_added": {"ar": "تم إضافة", "en": "Added", "fr": "Ajouté"},
    "js_status_added_plural": {"ar": "تم إضافة {0} حساب", "en": "Added {0} accounts", "fr": "Ajouté {0} comptes"},
    "js_status_all_exist": {"ar": "كل المحدد موجود مسبقاً", "en": "All selected already exist", "fr": "Tous existants"},
    "js_err_enter_user": {"ar": "أدخل اسم مستخدم", "en": "Enter a username", "fr": "Entrer nom d'utilisateur"},
    "js_err_unexpected": {"ar": "حدث خطأ غير متوقع", "en": "Unexpected error occurred", "fr": "Erreur inattendue"},
    "js_err_select_download": {"ar": "حدّد حسابات لتنزيلها", "en": "Select accounts to download", "fr": "Sélectionner comptes à télécharger"},
    "js_status_downloading": {"ar": "جاري التحميل...", "en": "Downloading...", "fr": "Téléchargement..."},
    "js_status_sched_saved": {"ar": "تم حفظ إعدادات الجدولة بنجاح", "en": "Schedule settings saved successfully", "fr": "Planification enregistrée"},
    "js_status_updated_folders": {"ar": "تم تحديث قائمة المجلدات", "en": "Folders list updated", "fr": "Dossiers mis à jour"},
    "js_status_select_add": {"ar": "حدّد حسابات لإضافتها", "en": "Select accounts to add", "fr": "Sélectionner comptes à ajouter"},
    "js_next_run": {"ar": "التشغيل التالي: ", "en": "Next run: ", "fr": "Prochaine exécution: "},
}

for k, lang_dict in js_keys.items():
    if k not in t['ar']:
        t['ar'][k] = lang_dict['ar']
        t['en'][k] = lang_dict['en']
        t['fr'][k] = lang_dict['fr']

with open(translations_path, "w", encoding="utf-8") as f:
    json.dump(t, f, ensure_ascii=False, indent=4)

with open(app_js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

replacements = [
    ("type === 'done' ? 'تم بنجاح' : type === 'error' ? 'خطأ' : 'جاري المعالجة...'", "type === 'done' ? window._T('js_status_success') : type === 'error' ? window._T('js_status_error') : window._T('js_status_processing')"),
    ("showStatus('done', `تم إضافة ${username}`);", "showStatus('done', `${window._T('js_status_added')} ${username}`);"),
    ("'لا توجد حسابات'", "window._T('dash_empty')"),
    ("addBtn.textContent = 'إضافة دفعة'", "addBtn.textContent = window._T('dash_add')"),
    ("addBtn.textContent = 'إضافة'", "addBtn.textContent = window._T('dash_add')"),
    ("'فشل تحميل الحسابات المقترحة'", "window._T('dash_error')"),
    ("showStatus('done', 'تم تحديث الحسابات المقترحة');", "showStatus('done', window._T('js_status_success'));"),
    ("showStatus('error', 'حدّد حسابات لإضافتها');", "showStatus('error', window._T('js_status_select_add'));"),
    ("data.added > 0 ? `تم إضافة ${data.added} حساب${data.added > 1 ? 'ات' : ''}` : 'كل المحدد موجود مسبقاً'", "data.added > 0 ? window._T('js_status_added_plural').replace('{0}', data.added) : window._T('js_status_all_exist')"),
    ("showStatus('error', 'أدخل اسم مستخدم');", "showStatus('error', window._T('js_err_enter_user'));"),
    ("const msg = data.added > 0 ? `تم إضافة ${data.added} حساب` : '';", "const msg = data.added > 0 ? window._T('js_status_added_plural').replace('{0}', data.added) : '';"),
    ("const skip = data.skipped?.length ? ` (${data.skipped.length} موجود)` : '';", "const skip = data.skipped?.length ? ` (x${data.skipped.length})` : '';"),
    ("showStatus('error', 'حدث خطأ غير متوقع');", "showStatus('error', window._T('js_err_unexpected'));"),
    ("showStatus('error', 'حدّد حسابات لتنزيلها');", "showStatus('error', window._T('js_err_select_download'));"),
    ("showStatus('running', 'جاري التحميل...');", "showStatus('running', window._T('js_status_downloading'));"),
    ("showStatus('done', 'تم تحديث قائمة المجلدات');", "showStatus('done', window._T('js_status_updated_folders'));"),
    ("el.textContent = 'التشغيل التالي: ' + next.toLocaleDateString('ar-SA', opts);", "el.textContent = window._T('js_next_run') + next.toLocaleDateString(navigator.language, opts);"),
    ("showStatus('done', 'تم حفظ إعدادات الجدولة بنجاح');", "showStatus('done', window._T('js_status_sched_saved'));"),
    ("'<option value=\"\">اختر المجلد</option><option value=\"__manual__\">أدخل يدوياً</option>'", " `<option value=\"\">${window._T('dash_select_folder')}</option><option value=\"__manual__\">${window._T('dash_manual')}</option>` "),
    ("'<option value=\"\">اختر المجلد</option>'", " `<option value=\"\">${window._T('dash_select_folder')}</option>` "),
    ("'<option value=\"\">اختر القناة</option>'", " `<option value=\"\">${window._T('dash_select_channel')}</option>` ")
]

for old, new in replacements:
    js_content = js_content.replace(old, new)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print("Patched app.js and updated translations.json successfully.")
