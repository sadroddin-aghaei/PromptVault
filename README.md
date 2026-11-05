# Prompt Vault

**A private, minimal, OLED-dark desktop app for storing, organizing, searching and reusing AI prompts.**
Persian (RTL) and English (LTR) · 100% local · no account · no analytics.

> © 2026 Sadroddin Aghaei. All Rights Reserved.
> Developer: Sadroddin Aghaei · Version 1.0.0

## Features
- **Prompts:** create, edit, delete, duplicate, copy, favorite, archive; title, description, category, tags, created / modified timestamps (Jalali dates in Persian mode).
- **Editor:** large editor, monospace option, LTR/RTL toggle (auto-detected per prompt), character & word counters, unsaved-changes indicator + guard, `Ctrl+S`, live preview.
- **Variables:** `{{topic}}`, `{{language}}`, `{{role}}`, `{{context}}`, `{{output_format}}` or your own. A panel lists them; filled values appear in the preview and in the copied text. The stored prompt always keeps the template.
- **Search:** instant (debounced) search across title, content, description and tags; category and favorites filters; sort by newest / oldest / recently used / recently modified.
- **Categories:** 10 defaults; create, rename, delete (prompts move to "Other").
- **Dashboard:** totals, favorites, used prompts, categories, recently used / added, quick search, quick "New prompt".
- **Import / export:** JSON import (validated, size-limited, duplicates skipped, atomic, automatic safety backup), JSON / TXT / Markdown export (single prompt or all), full database backup & restore (validated + safety copy).
- **Settings:** language (default Persian), theme (OLED / Charcoal / Light), font size, startup behaviour, backup/restore, About.
- **Privacy:** everything stays on your machine. No network code, no telemetry.

Shortcuts: `Ctrl+1…4` pages · `Ctrl+N` new prompt · `Ctrl+F` search · `Ctrl+S` save · `Ctrl+Shift+C` copy.

## Run from source (Windows 10/11)
Requires Python 3.12+.
```bat
git clone <your-repo> PromptVault && cd PromptVault
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Or just double-click `run_dev.bat`. (macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python main.py`.)

## Build a Windows executable
```bat
build_windows.bat            :: folder build  -> dist\PromptVault\PromptVault.exe  (fastest startup, recommended)
build_windows.bat onefile    :: single file   -> dist\PromptVault.exe              (slower first start)
```
Manual: `pip install -r requirements.txt` then `pyinstaller --noconfirm --clean PromptVault.spec`
(`set PV_ONEFILE=1` first for a single exe). The `.spec` bundles `assets/` (icons, Vazirmatn font) and the QtAwesome icon fonts.

## Automated releases (GitHub Actions)
`.github/workflows/release.yml` builds, tests and publishes installers for every platform:

| Platform | Output |
|---|---|
| Windows x64 (Intel/AMD 64-bit) | `PromptVault-<ver>-windows-x64-setup.exe` + `-portable.zip` |
| Windows ARM64 | `PromptVault-<ver>-windows-arm64-setup.exe` + `-portable.zip` |
| macOS Apple Silicon | `PromptVault-<ver>-macos-apple-silicon.dmg` |
| macOS Intel | `PromptVault-<ver>-macos-intel.dmg` |
| macOS Universal (both) | `PromptVault-<ver>-macos-universal.dmg` |

To release: bump `APP_VERSION` in `app/__init__.py`, commit, then
```bash
git tag v1.0.1 && git push origin v1.0.1
```
The tag must equal `APP_VERSION` or the run stops. Every build runs the tests and starts the frozen app (`--smoke-test`) before it is published; a `SHA256SUMS.txt` is attached. You can also run the workflow manually from the *Actions* tab to get the files as artifacts without publishing.

Notes: 32-bit Windows is not supported (Qt 6 / PySide6 ships no 32-bit wheels). Builds are not code-signed; see the Release notes for the first-launch steps (Windows SmartScreen, macOS right-click → Open).
`ci.yml` runs the tests on Windows and macOS for every push and pull request.

## Where is my data?
User-data directory, never the install/temp folder:
| OS | Path |
|---|---|
| Windows | `%APPDATA%\PromptVault\` |
| macOS | `~/Library/Application Support/PromptVault/` |
| Linux | `~/.local/share/PromptVault/` |

Contains `promptvault.db`, `settings.json`, `backups/` (automatic safety copies, last 10 kept) and `promptvault.log`.
Set `PROMPT_VAULT_HOME` to use a different folder (handy for testing).

## Project layout
```
main.py                     entry point (logging, exception hook)
app/app.py                  controller: language/theme/font, window (re)building
app/database/               engine + session_scope (rollback, DatabaseError)
app/models/                 SQLAlchemy models (Prompt, Category, Tag, Meta)
app/services/               prompt / category / import-export-backup / settings (no Qt)
app/ui/{dashboard,prompts,categories,settings,components}/
app/styles/theme.py         design tokens + QSS
app/utils/                  paths, i18n (fa/en), Jalali dates, variables
assets/{icons,fonts}/       app icon, Vazirmatn
tests/                      pytest (services + headless UI)
```

## Tests
```bash
pip install -r requirements.txt
python -m pytest -q          # UI tests run headless (QT_QPA_PLATFORM=offscreen)
```

## Import file format
```json
{ "app": "Prompt Vault", "format_version": 1,
  "prompts": [ { "title": "…", "content": "…", "description": "", "category": "Writing",
                 "tags": ["a","b"], "is_favorite": false, "is_archived": false,
                 "created_at": "2026-01-01T10:00:00", "updated_at": "2026-01-01T10:00:00" } ] }
```
Only `title` (string) is required. A bare JSON list of prompts is accepted too.

## Credits & licenses
Vazirmatn font (SIL OFL 1.1) · Material Design Icons via QtAwesome · PySide6 (Qt) · SQLAlchemy.
Distributing a PyInstaller build bundles Qt under the LGPL; keep the Qt license notices with your release.

© 2026 Sadroddin Aghaei. All Rights Reserved.
