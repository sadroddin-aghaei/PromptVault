"""Persian / English translations, digit localisation and Jalali date formatting."""
from __future__ import annotations

from datetime import datetime

from app.utils.jalali import gregorian_to_jalali

LANGUAGES = {"fa": "فارسی", "en": "English"}
_lang = "fa"
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def set_language(code: str) -> None:
    global _lang
    _lang = code if code in LANGUAGES else "fa"


def lang() -> str:
    return _lang


def is_rtl() -> bool:
    return _lang == "fa"


def t(key: str, **kw) -> str:
    s = STRINGS.get(_lang, {}).get(key) or STRINGS["en"].get(key) or key
    return s.format(**kw) if kw else s


def digits(text: str) -> str:
    return text.translate(_FA_DIGITS) if _lang == "fa" else text


def num(n: int) -> str:
    return digits(f"{n:,}".replace(",", "٬" if _lang == "fa" else ","))


def category_label(name: str | None) -> str:
    if not name:
        return t("uncategorized")
    return DEFAULT_CATEGORIES_FA.get(name, name) if _lang == "fa" else name


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if _lang == "fa":
        jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
        return digits(f"{jy:04d}/{jm:02d}/{jd:02d} {dt:%H:%M}")
    return f"{dt:%Y-%m-%d %H:%M}"


DEFAULT_CATEGORIES_FA = {
    "Programming": "برنامه‌نویسی", "Software Development": "توسعه نرم‌افزار",
    "AI & Machine Learning": "هوش مصنوعی و یادگیری ماشین", "Image Generation": "تولید تصویر",
    "Writing": "نویسندگی", "Marketing": "بازاریابی", "Productivity": "بهره‌وری",
    "Education": "آموزش", "Business": "کسب‌وکار", "Other": "سایر",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_tagline": "Your private prompt library",
        "nav_dashboard": "Dashboard", "nav_prompts": "Prompts", "nav_categories": "Categories", "nav_settings": "Settings",
        "save": "Save", "cancel": "Cancel", "delete": "Delete", "copy": "Copy", "duplicate": "Duplicate",
        "export": "Export", "rename": "Rename", "add": "Add", "view": "View", "error": "Error",
        "confirm": "Confirm", "uncategorized": "Uncategorized", "untitled": "Untitled prompt", "copy_suffix": "copy",
        "dash_title": "Dashboard", "dash_subtitle": "Everything in your vault at a glance",
        "dash_search_ph": "Search all prompts…", "new_prompt": "New prompt",
        "stat_total": "Total prompts", "stat_favorites": "Favorites", "stat_categories": "Categories", "stat_used": "Used prompts",
        "recently_used": "Recently used", "recently_added": "Recently added", "categories_overview": "Categories",
        "empty_used": "Prompts you copy will appear here.", "empty_added": "No prompts yet. Create your first one!",
        "search_ph": "Search title, content or tags…", "all_categories": "All categories",
        "favorites_only": "Favorites", "show_archived": "Archived",
        "sort_newest": "Newest first", "sort_oldest": "Oldest first", "sort_recent": "Recently used", "sort_modified": "Recently modified",
        "results_count": "{n} prompts", "no_results": "No prompts found", "no_results_hint": "Try a different search or filter.",
        "list_capped": "Showing the first {n} results — refine your search.",
        "empty_editor_title": "Select a prompt", "empty_editor_hint": "Pick a prompt from the list or create a new one.",
        "ed_title_ph": "Prompt title", "ed_desc_ph": "Short description (optional)", "ed_tags_ph": "Tags, separated by commas",
        "ed_content_ph": "Write your prompt here. Use {{variables}} such as {{topic}} or {{language}}.",
        "category": "Category", "tags": "Tags", "unsaved": "Unsaved changes", "saved_state": "All changes saved",
        "counter": "{c} characters · {w} words", "text_direction": "Text direction (LTR / RTL)", "monospace": "Monospace", "preview": "Live preview",
        "variables": "Variables", "variables_hint": "Fill in values — the preview and the copied text use them.",
        "insert_variable": "Variable", "copied": "Copied to clipboard", "title_required": "Please enter a title.",
        "saved_ok": "Prompt saved", "deleted_ok": "Prompt deleted", "duplicated_ok": "Prompt duplicated",
        "delete_prompt_text": "Delete “{title}”? This cannot be undone.",
        "unsaved_title": "Unsaved changes", "unsaved_text": "This prompt has unsaved changes. What would you like to do?",
        "discard": "Discard", "save_changes": "Save changes",
        "favorite": "Favorite", "archive": "Archive", "unarchive": "Unarchive", "archived_ok": "Prompt archived",
        "unarchived_ok": "Prompt restored", "new_prompt_heading": "New prompt", "used_times": "Used {n}×",
        "created": "Created", "modified": "Modified", "export_md": "Markdown (.md)", "export_txt": "Plain text (.txt)",
        "cat_title": "Categories", "cat_subtitle": "Organize your prompts your way", "cat_new_ph": "New category name…",
        "cat_exists": "A category with this name already exists.", "cat_name_required": "Please enter a category name.",
        "cat_rename_title": "Rename category", "cat_rename_label": "New name:",
        "cat_delete_text": "Delete category “{name}”? Its prompts are kept and moved to “Other”.",
        "cat_delete_text_other": "Delete the “Other” category? Its prompts are kept as uncategorized.",
        "cat_prompts": "{n} prompts", "cat_deleted": "Category deleted",
        "set_title": "Settings", "set_subtitle": "Make Prompt Vault yours",
        "set_appearance": "Appearance", "set_language": "Language", "set_theme": "Theme",
        "theme_oled": "OLED black", "theme_charcoal": "Charcoal", "theme_light": "Light", "set_font_size": "Font size",
        "set_general": "General", "set_startup": "On startup", "startup_dashboard": "Open the dashboard",
        "startup_prompts": "Open prompts", "startup_last": "Return to where I left off",
        "set_data": "Data & backup", "set_data_loc": "Data folder", "open_folder": "Open folder",
        "backup_db": "Backup database", "restore_db": "Restore backup", "import_json": "Import JSON",
        "export_json": "Export JSON", "export_txt_all": "Export TXT", "export_md_all": "Export Markdown",
        "set_privacy": "Privacy", "privacy_text": "Everything stays on this computer. No account, no servers, no analytics.",
        "about": "About", "about_text": "A private, elegant home for the prompts you rely on every day.",
        "version": "Version", "developer": "Developer",
        "backup_done": "Backup saved", "restore_confirm_title": "Restore backup",
        "restore_confirm_text": "This replaces ALL current prompts with the backup. A safety copy of your current data is saved first. Continue?",
        "restore_done": "Backup restored", "restore_unreadable": "The selected file could not be read.",
        "restore_corrupt": "The backup file is corrupted.", "restore_not_vault": "This is not a valid Prompt Vault backup.",
        "import_done": "Imported {imported} · skipped {dup} duplicates · {invalid} invalid",
        "import_confirm": "Prompts are added to your library; existing prompts are never overwritten and a safety backup is created first. Continue?",
        "import_unreadable": "The file could not be read.", "import_too_large": "The file is too large (max 25 MB).",
        "import_not_json": "The file is not valid JSON.", "import_bad_schema": "The file does not look like a Prompt Vault export.",
        "import_no_valid": "The file contains no valid prompts.",
        "export_done": "Exported {n} prompts", "nothing_to_export": "There are no prompts to export.",
        "db_error": "A database error occurred. Your data was not changed.", "io_error": "File error: {detail}",
        "filter_json": "JSON files (*.json)", "filter_db": "Prompt Vault backup (*.db);;All files (*)",
        "filter_txt": "Text files (*.txt)", "filter_md": "Markdown files (*.md)",
    },
    "fa": {
        "app_tagline": "کتابخانه خصوصی پرامپت‌های شما",
        "nav_dashboard": "داشبورد", "nav_prompts": "پرامپت‌ها", "nav_categories": "دسته‌بندی‌ها", "nav_settings": "تنظیمات",
        "save": "ذخیره", "cancel": "انصراف", "delete": "حذف", "copy": "کپی", "duplicate": "تکثیر",
        "export": "خروجی", "rename": "تغییر نام", "add": "افزودن", "view": "مشاهده", "error": "خطا",
        "confirm": "تأیید", "uncategorized": "بدون دسته", "untitled": "پرامپت بدون عنوان", "copy_suffix": "کپی",
        "dash_title": "داشبورد", "dash_subtitle": "نمای کلی از همه چیز در گاوصندوق شما",
        "dash_search_ph": "جستجو در همه پرامپت‌ها…", "new_prompt": "پرامپت جدید",
        "stat_total": "کل پرامپت‌ها", "stat_favorites": "علاقه‌مندی‌ها", "stat_categories": "دسته‌بندی‌ها", "stat_used": "پرامپت‌های استفاده‌شده",
        "recently_used": "اخیراً استفاده‌شده", "recently_added": "اخیراً افزوده‌شده", "categories_overview": "دسته‌بندی‌ها",
        "empty_used": "پرامپت‌هایی که کپی می‌کنید اینجا نمایش داده می‌شوند.", "empty_added": "هنوز پرامپتی ندارید. اولین پرامپت را بسازید!",
        "search_ph": "جستجو در عنوان، متن یا برچسب‌ها…", "all_categories": "همه دسته‌ها",
        "favorites_only": "علاقه‌مندی‌ها", "show_archived": "بایگانی",
        "sort_newest": "جدیدترین", "sort_oldest": "قدیمی‌ترین", "sort_recent": "اخیراً استفاده‌شده", "sort_modified": "آخرین ویرایش",
        "results_count": "{n} پرامپت", "no_results": "پرامپتی پیدا نشد", "no_results_hint": "جستجو یا فیلتر دیگری را امتحان کنید.",
        "list_capped": "{n} نتیجه اول نمایش داده شد — جستجو را دقیق‌تر کنید.",
        "empty_editor_title": "یک پرامپت انتخاب کنید", "empty_editor_hint": "از فهرست یک پرامپت انتخاب کنید یا پرامپت تازه‌ای بسازید.",
        "ed_title_ph": "عنوان پرامپت", "ed_desc_ph": "توضیح کوتاه (اختیاری)", "ed_tags_ph": "برچسب‌ها را با ویرگول جدا کنید",
        "ed_content_ph": "پرامپت خود را اینجا بنویسید. از متغیرهایی مثل {{topic}} یا {{language}} استفاده کنید.",
        "category": "دسته‌بندی", "tags": "برچسب‌ها", "unsaved": "تغییرات ذخیره‌نشده", "saved_state": "همه تغییرات ذخیره شد",
        "counter": "{c} نویسه · {w} کلمه", "text_direction": "جهت متن (چپ‌به‌راست / راست‌به‌چپ)", "monospace": "تک‌فاصله", "preview": "پیش‌نمایش زنده",
        "variables": "متغیرها", "variables_hint": "مقدارها را وارد کنید — پیش‌نمایش و متن کپی‌شده از آن‌ها استفاده می‌کنند.",
        "insert_variable": "متغیر", "copied": "در کلیپ‌بورد کپی شد", "title_required": "لطفاً یک عنوان وارد کنید.",
        "saved_ok": "پرامپت ذخیره شد", "deleted_ok": "پرامپت حذف شد", "duplicated_ok": "پرامپت تکثیر شد",
        "delete_prompt_text": "«{title}» حذف شود؟ این کار قابل بازگشت نیست.",
        "unsaved_title": "تغییرات ذخیره‌نشده", "unsaved_text": "این پرامپت تغییرات ذخیره‌نشده دارد. چه کنیم؟",
        "discard": "دور انداختن", "save_changes": "ذخیره تغییرات",
        "favorite": "علاقه‌مندی", "archive": "بایگانی", "unarchive": "خروج از بایگانی", "archived_ok": "پرامپت بایگانی شد",
        "unarchived_ok": "پرامپت بازگردانی شد", "new_prompt_heading": "پرامپت جدید", "used_times": "{n} بار استفاده",
        "created": "ساخت", "modified": "ویرایش", "export_md": "مارک‌داون (.md)", "export_txt": "متن ساده (.txt)",
        "cat_title": "دسته‌بندی‌ها", "cat_subtitle": "پرامپت‌هایتان را به سلیقه خودتان سازمان دهید", "cat_new_ph": "نام دسته‌بندی جدید…",
        "cat_exists": "دسته‌بندی‌ای با این نام از قبل وجود دارد.", "cat_name_required": "لطفاً نام دسته‌بندی را وارد کنید.",
        "cat_rename_title": "تغییر نام دسته‌بندی", "cat_rename_label": "نام جدید:",
        "cat_delete_text": "دسته‌بندی «{name}» حذف شود؟ پرامپت‌های آن حفظ شده و به «سایر» منتقل می‌شوند.",
        "cat_delete_text_other": "دسته «سایر» حذف شود؟ پرامپت‌های آن بدون دسته باقی می‌مانند.",
        "cat_prompts": "{n} پرامپت", "cat_deleted": "دسته‌بندی حذف شد",
        "set_title": "تنظیمات", "set_subtitle": "پرامپت وولت را به سلیقه خود درآورید",
        "set_appearance": "ظاهر", "set_language": "زبان", "set_theme": "تم",
        "theme_oled": "مشکی OLED", "theme_charcoal": "ذغالی", "theme_light": "روشن", "set_font_size": "اندازه قلم",
        "set_general": "عمومی", "set_startup": "هنگام شروع", "startup_dashboard": "باز کردن داشبورد",
        "startup_prompts": "باز کردن پرامپت‌ها", "startup_last": "بازگشت به آخرین صفحه",
        "set_data": "داده و پشتیبان‌گیری", "set_data_loc": "پوشه داده‌ها", "open_folder": "باز کردن پوشه",
        "backup_db": "پشتیبان‌گیری از پایگاه داده", "restore_db": "بازیابی پشتیبان", "import_json": "وارد کردن JSON",
        "export_json": "خروجی JSON", "export_txt_all": "خروجی TXT", "export_md_all": "خروجی مارک‌داون",
        "set_privacy": "حریم خصوصی", "privacy_text": "همه چیز روی همین رایانه می‌ماند. بدون حساب کاربری، بدون سرور، بدون ردیابی.",
        "about": "درباره برنامه", "about_text": "خانه‌ای خصوصی و زیبا برای پرامپت‌هایی که هر روز به آن‌ها تکیه می‌کنید.",
        "version": "نسخه", "developer": "توسعه‌دهنده",
        "backup_done": "پشتیبان ذخیره شد", "restore_confirm_title": "بازیابی پشتیبان",
        "restore_confirm_text": "این کار «همه» پرامپت‌های فعلی را با پشتیبان جایگزین می‌کند. پیش از آن یک نسخه ایمنی از داده‌های فعلی ذخیره می‌شود. ادامه می‌دهید؟",
        "restore_done": "پشتیبان بازیابی شد", "restore_unreadable": "فایل انتخاب‌شده خوانده نشد.",
        "restore_corrupt": "فایل پشتیبان خراب است.", "restore_not_vault": "این یک پشتیبان معتبر پرامپت وولت نیست.",
        "import_done": "{imported} وارد شد · {dup} تکراری نادیده گرفته شد · {invalid} نامعتبر",
        "import_confirm": "پرامپت‌ها به کتابخانه شما افزوده می‌شوند؛ هیچ پرامپت موجودی بازنویسی نمی‌شود و پیش از آن یک نسخه پشتیبان ایمنی ساخته می‌شود. ادامه می‌دهید؟",
        "import_unreadable": "فایل خوانده نشد.", "import_too_large": "حجم فایل زیاد است (حداکثر ۲۵ مگابایت).",
        "import_not_json": "فایل JSON معتبر نیست.", "import_bad_schema": "این فایل شبیه خروجی پرامپت وولت نیست.",
        "import_no_valid": "فایل هیچ پرامپت معتبری ندارد.",
        "export_done": "{n} پرامپت خروجی گرفته شد", "nothing_to_export": "پرامپتی برای خروجی گرفتن وجود ندارد.",
        "db_error": "خطای پایگاه داده رخ داد. داده‌های شما تغییری نکردند.", "io_error": "خطای فایل: {detail}",
        "filter_json": "فایل‌های JSON (*.json)", "filter_db": "پشتیبان پرامپت وولت (*.db);;همه فایل‌ها (*)",
        "filter_txt": "فایل‌های متنی (*.txt)", "filter_md": "فایل‌های مارک‌داون (*.md)",
    },
}
