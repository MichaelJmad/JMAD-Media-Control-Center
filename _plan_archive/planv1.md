# 🧭 JMAD Media Tool V2 — Full Design Plan (Current Draft)

---

## 1️⃣ Project Overview
JMAD Media Tool V2 completely re-envisions the media-management pipeline.  
Its goal: replace Tiny Media Manager and Media Center Manager with an intuitive, high-accuracy, and highly controllable system for organizing, renaming, and enriching media libraries.

---

## 2️⃣ Main Application Layout

### 2.1 Window Structure
- **Main Split Layout**
  - **Left Panel — Media Tree**
    - Displays staging + live libraries (Series → Seasons → Episodes / Movies / Specials / OVAs).  
    - Collapse / expand behavior.  
    - Icons & color badges indicate processing state or issues (e.g., ⚠ for Uncategorized).  
    - Supports drag-and-drop re-organization.
  - **Right Panel — Info / Preview**
    - Tabs: Episodes · Movies · OVAs · Specials · Related.  
    - Shows artwork, synopsis, metadata, audio & subtitle info.  
    - Right-click: Rename · Rescan · Open Folder.
  - **Bottom Panel — Console**
    - Docked by default; hide/show via toolbar or Ctrl + L.  
    - Undock fills full lower right area; preview resizes.  
    - Logs actions & shows progress bars.

---

### 2.2 Toolbar & Menus
| Action | Behavior |
|--------|-----------|
| **Scan / Rescan / Clear** | Scans staging for changes; progress in console. |
| **Settings ⚙️** | Opens settings dialog (with Apply button). |
| **Tools Menu** | Cleanup, Move to Library, other utilities. |
| **Catalog Tab Toggle** | Opens Catalog (disabled if no live DB; tooltip explains). |
| **Console Toggle** | Show/Hide Console (mirrors context menu). |

Context menus mirror toolbar options + add quick metadata resync, Open in Explorer, etc.

---

### 2.3 Process Status Indicators
- Color-coded icons (configurable in Settings → Appearance).  
- Based on naming pattern and metadata state.  
- ⭐ Define final rules for “processed” vs “unprocessed”.

---

### 2.4 Console Panel Functions
- Logs all major actions.  
- Progress bars for long tasks.  
- Clear Log button.  
- Export (Log → right-click).  
- Filters: Errors / Warnings / Info (+⭐ future custom).  
- Auto-scroll toggle.

---

### 2.5 Drag & Drop Behavior
- **From Explorer:** Prompt to move to Staging (default).  
  - “Always move to staging” option in Settings → General.  
  - Files → Uncategorized; Folders → Series nodes.  
- **Series → Series:** Opens Organize Dialog for merge decision.  
- **Catalog → Catalog:** Drag between library tabs (e.g., Anime ↔ TV).  
- Visual highlight shows valid drop targets.

---

### 2.6 Keyboard Shortcuts
| Shortcut | Action |
|-----------|--------|
| Ctrl + A | Select All in active panel |
| F2 | Rename (single item) |
| Ctrl + L | Toggle Console |
| Ctrl + Shift + L | Export Console Log |
| Ctrl + E | Open Organize Dialog |
| Ctrl + M | Move to Library (presets/custom) |
| Ctrl + Delete | Delete selected (confirmation) |
| ⭐ | Future metadata refresh / bulk actions |

---

## 3️⃣ Catalog Tab
- Tabs: Anime · TV · Movies · ⭐ Custom Libraries.  
- Quick Search + Filter.  
- Missing Media Filter.  
- **Get List Integration:** shows missing series/movies; double-click expands to missing episodes.  
- Dynamic refresh on library change.  
- Import/Export Get List (plain text).  
- Move to Library actions.  
- Context menus for refresh / explorer.  
- ⭐ Expand Get List search provider definitions.

---

## 4️⃣ Settings Dialog

### 4.1 General
- Console visibility (default on/off).  
- Docking preference.  
- Console filters + export autosave (on close or timer).  
- Drag & drop behavior (Prompt / Always / Ignore).  
- Get List options (flag or auto-remove).  
- Metadata sync rules (skip or force regather).  
- Update behavior (auto-check on launch).  
- Tooltips for shortcuts.  
- Save window layout (default off).  
- Reset to Defaults button.

---

### 4.2 Directories
- **Staging Directory** (required at first launch; auto-monitored).  
- **Live Libraries:** TV · Movies · Anime · ⭐ Custom.  
  - “Include in Catalog” checkbox per library.  
  - Used by Move-to-Target and Catalog tabs.  
- Library Setup Dialog (add name + path).  
- ⭐ Handle drive-letter changes on import/export.

---

### 4.3 Patterns (Renaming)
- Controls how files/folders renamed **before move**.  
- Episode patterns with user-chosen zero-padding.  
- Movie patterns omit extra punctuation when series blank.  
- Specials/OVAs → Season 00 or Specials folder (user choice).  
- Regex rules remove junk tags (e.g., [group]).  
- Pattern Testing Tool (sample from staging).  
- Export/Import patterns (+regex).  
- ⭐ Finalize conditional syntax.

---

### 4.4 Cleanup
- Scope defaults to selected item.  
- Cleans before metadata phase.  
- Whitelisted folders ignored.  
- No profiles or reset needed.

---

### 4.5 Key Binds
- Full shortcut list with descriptions.  
- Import/Export profiles (JSON).  
- Tooltips per action.  
- Reset Key Bindings.  
- ⭐ Define conflict feedback mechanism.

---

### 4.6 Metadata
#### Media Server Options
- Jellyfin · Plex · Kodi · Emby · ⭐ Synology Video Station.  
- Selection affects metadata format & defaults.

#### Core Metadata
- Title · Year · Episode Titles · Synopsis · Genres · Cast · ⭐ Tags.

#### Artwork
- Enable/disable types (posters, banners, backdrops).  
- Language preference.  
- Image standardization (pass for size/quality).  
- User-definable targets.

#### Subtitles
- Download preferred languages.  
- Auto-embed into media (advanced + warning).  
- ⭐ List supported sources.

#### Audio Metadata
- Detect audio tracks & languages.  
- Manual override option.

#### Extras
- Trailers, themes, clips (optional).  
- ⭐ Define sources & licensing rules.

#### Behavior
- Skip artwork if present.  
- Skip metadata if present.  
- Force full regather toggle.  
- Auto-sync with live DB (default off).

#### Preferred Sources
- TMDB · TVDB · AniDB · etc.  
- API keys per source.  
- Fallback fills missing fields.  
- ⭐ Clarify runtime accuracy.

#### Library-Specific Settings
- Each library has its own naming + metadata rules.  
- Minimal vs Full presets.

#### Export/Import Profiles
- Export all metadata settings as profile for backup or reinstall.

---

## 5️⃣ Organize Dialog System

### 5.1 Purpose
Prepares staging media for metadata scraping and live move.

### 5.2 Layout
- Search Bar (pre-filled from regex clean).  
- Series Selection Dialog with preview.  
- Final Series Title above panes.  
- Left = Source (raw). Right = Target (organized).  
- Buttons between for Move/Undo/Redo/Auto-Assign/Apply.  
- Toggle regex cleaning for target view.

---

### 5.3 Auto-Assignment Workflow
1. Preprocess via regex (season/episode/movie).  
2. Infer season from parent folder if missing.  
3. Specials → Season 00 or Specials (user choice).  
4. Confident matches auto-move.  
5. Ambiguous flagged in source.  
6. ⭐ Finalize regex library.

---

### 5.4 Error Recovery Workflow
**Detection → Flagging → Correction → Validation → Apply → Memory**

- Detects ambiguous/duplicate/unknown/non-media items.  
- Visual flags with tooltips.  
- Error Summary Bar.  
- Fix via drag-drop or context menu (Mark Season X, Send to Specials, Move to Uncategorized, Retry, Ignore).  
- “Guess Again” re-runs regex.  
- Bulk actions available.  
- Apply disabled until critical errors cleared.  
- Summary dialog after apply.  
- Learns user corrections.  
- ⭐ Define pattern storage method.

---

### 5.5 Uncategorized Bin
- Files moved to `/SeriesRoot/Uncategorized/`.  
- Node appears if exists; collapsible.  
- Series flagged ⚠ if present.  
- Warn user before apply.

---

### 5.6 Apply Confirmation
- Scrollable list of Original → New paths.  
- Columns: Original · New · Status.  
- **Continue / Cancel** buttons.  
- Tooltips for conflicts.

---

### 5.7 Advanced Features (Future)
| Feature | Status |
|----------|---------|
| Watch Order Anchoring | ✅ Planned |
| Duplicate Merge Suggestions | ✅ Planned |
| Mixed Media Heuristics | ⭐ Review |
| Smart Auto-Learning | ⭐ TBD |
| Batch Mode | ⭐ Deferred |
| Metadata Preview Integration | ⭐ Deferred |

---

### 5.8 Outstanding Definitions ⭐
| Area | Notes |
|------|-------|
| Regex Library | Complete episode/movie/special patterns |
| Ghosted Target Data | Metadata source for layout preview |
| Watch Order Storage | Format for Jellyfin-style anchors |
| Operation Queue | Safe file move/rename handling |
| Icon / Color Scheme | Consistent UI theme |
| Pattern Learning Store | Config or DB location |
| Context Menu Matrix | Actions per type (file/folder/movie) |
| Bulk Limits | Safe batch threshold |
| Metadata Preview | Pre-scrape validation |
| Console Link | Progress logging for organize actions |

---

## 6️⃣ Future Development ⭐
- **Update System Tab**  
- **Metadata Fetch & Task Queue Integration**  
- **Enhanced Catalog Sync with Live Detection**  
- **UI Wireframes / Visual Design**  
- **Plugin / Extension Support**

---

### ✅ Summary
This document consolidates all confirmed design elements for **JMAD Media Tool V2**.  
⭐ Markers highlight areas requiring further definition or expansion before final spec freeze.
