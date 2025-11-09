# V1 Organize Feature Design Documentation

## Overview
The organize feature allows users to reorganize media files within staging into a structured format, assigning episodes to seasons and handling specials/movies appropriately. Files remain in staging under organized media-type folders (Anime, TV Shows, Movies) until explicitly moved to library using the Move tool.

## Workflow

### 1. User Initiates Organize
- User selects one or multiple folders from media tree
- Click green "Organize" button (center of toolbar) OR right-click → "Organize..."
- Organize button is green when items are selected, disabled when nothing selected
- Processed media (in organizational folders) shown with green indicator

### 2. Media Type Selection Dialog
First dialog that appears asking user to select media type:

**Options:**
- TV Series
- Movies
- Anime

**Routing:**
- TV Series → Series Organize Dialog → creates in /staging/TV Shows/
- Anime → Series Organize Dialog → creates in /staging/Anime/
- Movies → Movies Organize Dialog → creates in /staging/Movies/

**Note:** Anime Movies option removed in v1.5.0 (no longer needed - use Movies or Anime)

---

## Series Organize Dialog

### Layout: Media Title + 3-Pane Design + Preview Table

```
┌────────────────────────────────────────────────────────────────┐
│             Organize TV Series / Anime / Anime Movies          │
├────────────────────────────────────────────────────────────────┤
│ Media Title: [My Hero Academia_________________] ← Editable    │
├──────────────┬──────────────┬──────────────────────────────────┤
│  Organizing 3 folder(s)          [← Undo]  [Redo →]           │
├──────────────┬──────────────┬──────────────────────────────────┤
│              │              │                                  │
│   SOURCE     │   ACTIONS    │           TARGET                 │
│   (Left)     │  (Middle)    │          (Right)                 │
│              │              │                                  │
│  Tree of     │  [Move to    │  Organized structure:            │
│  selected    │   Season]    │  ├─ Season 1                     │
│  folders     │              │  │  ├─ My Hero Academia S01E01   │
│  from        │  [Move to    │  │  └─ My Hero Academia S01E02   │
│  staging     │   Specials]  │  ├─ Season 2                     │
│              │              │  │  └─ My Hero Academia S02E01   │
│  ├─ Folder1  │  [Move to    │  ├─ Specials                    │
│  │  ├─file1  │   Movies]    │  │  └─ My Hero Academia S00E01  │
│  │  └─file2  │              │  └─ Movies                       │
│  └─ Folder2  │  [Move to... │     └─ Movie Title.mkv          │
│     └─file3  │   (custom)]  │                                  │
│              │              │                                  │
├──────────────┴──────────────┴──────────────────────────────────┤
│  PREVIEW (Table - ALL Target Files Grouped by Season)          │
│  Season/Folder   │ Original Path           │ New Name (Edit)   │
│  ▼ Season 1      │                         │                   │
│    Season 1      │ Folder1/file1.mkv       │ Title S01E01.mkv  │
│    Season 1      │ Folder1/file2.mkv       │ Title S01E02.mkv  │
│  ▼ Specials      │                         │                   │
│    Specials      │ Folder2/special.mkv     │ Title S00E01.mkv  │
├────────────────────────────────────────────────────────────────┤
│                          [Cancel]  [Execute]                   │
└────────────────────────────────────────────────────────────────┘
```

### Media Title Field (NEW in V1)

**Purpose:** Define the series title that will be used in all filenames

**Behavior:**
- Auto-populated by inferring from first selected folder
- Strips out: season numbers (S01, Season 1), quality tags ([1080p], [BD]), year (2019), release groups ([HorribleSubs])
- User can edit to customize the title
- All generated filenames use this title as prefix
- Changes regenerate ALL filenames in preview

**Example:**
- Folder: "My Hero Academia [1080p][720p][Specials][BD] S00"
- Inferred Title: "My Hero Academia"
- Generated Files: "My Hero Academia S01E01.mkv"

### Undo/Redo Buttons (NEW in V1)

**Purpose:** Local undo/redo within the organize dialog

**Features:**
- Undo button: Steps back through organization changes
- Redo button: Steps forward through undone changes
- Saves state of BOTH source and target trees
- Independent from main application undo/redo
- Updates button states (disabled when can't undo/redo)

### Left Pane - Source

**Purpose:** Display selected media folders and their files

**Structure:**
- Nested tree view of original folder structure
- Shows folders from staging exactly as they are
- User can expand/collapse folders
- Shows files inside each folder
- **Files disappear from source when moved to target**

**Example:**
```
├─ My Hero Academia [Season 1]
│  ├─ s1s1.mkv
│  ├─ s1s2.mkv
│  └─ s1s3.mkv
├─ My Hero Academia [Specials]
│  └─ s0s2.mkv
└─ My Hero Academia S02
   ├─ episode_01.mkv
   └─ episode_02.mkv
```

**Interactions:**
- User can select files or entire folders
- Multi-select with standard keybindings (Ctrl+Click, Shift+Click)
- Selected items can be moved using action buttons
- Empty folders automatically removed

### Middle Pane - Actions

**Purpose:** Provide buttons to move selected items to target pane

**Buttons:**

1. **"Move to Season"** (was "Move to Series")
   - Prompts user for season number (e.g., 1, 2, 3)
   - Moves selected files to "Season X" in target pane
   - Files renamed with media title and season prefix

2. **"Move to Specials"**
   - Moves selected files to "Specials" in target pane
   - Files prefixed with S00

3. **"Move to Movies"**
   - Moves selected files to "Movies" folder in target pane
   - Files prefixed with M

4. **"Move to..." (custom)**
   - User can specify custom destination
   - For edge cases or special handling

### Right Pane - Target

**Purpose:** Display organized structure as user builds it

**Structure:**
- Nested tree showing final organization
- User builds this structure by moving items from source
- Folders sorted alphabetically

**Season Folders:**
```
Season 1
├─ My Hero Academia S01E01.mkv
├─ My Hero Academia S01E02.mkv
└─ My Hero Academia S01E03.mkv

Season 2
├─ My Hero Academia S02E01.mkv
└─ My Hero Academia S02E02.mkv

Specials
└─ My Hero Academia S00E01.mkv
```

**Interactions:**
- Multi-select with standard keybindings
- User can expand/collapse nodes
- **User can rename folders** (right-click → rename)

### Keyboard Shortcuts for Season Assignment (NEW in v1.5.0)

**Purpose:** Quick season assignment without clicking buttons

**Number Keys (Seasons 1-10):**
- Press `1` = Move to Season 1
- Press `2` = Move to Season 2
- Press `3` = Move to Season 3
- Press `4` = Move to Season 4
- Press `5` = Move to Season 5
- Press `6` = Move to Season 6
- Press `7` = Move to Season 7
- Press `8` = Move to Season 8
- Press `9` = Move to Season 9
- Press `0` = Move to Season 10

**Shift + Number Keys (Seasons 11-20):**
- Press `Shift+1` = Move to Season 11
- Press `Shift+2` = Move to Season 12
- Press `Shift+3` = Move to Season 13
- Press `Shift+4` = Move to Season 14
- Press `Shift+5` = Move to Season 15
- Press `Shift+6` = Move to Season 16
- Press `Shift+7` = Move to Season 17
- Press `Shift+8` = Move to Season 18
- Press `Shift+9` = Move to Season 19
- Press `Shift+0` = Move to Season 20

**Behavior:**
- Works on selected items in source pane
- Creates season folder if it doesn't exist
- Automatically detects and assigns episode numbers
- Multiple files can be moved at once
- Much faster than clicking "Move to Season" button repeatedly

**Example Workflow:**
1. Select files in source pane
2. Press `5` → All selected files moved to Season 5
3. Select more files
4. Press `Shift+5` → Moved to Season 15

### Bottom Pane - Preview Table (UPDATED in V1)

**Purpose:** Show ALL target files with original paths and new names

**Display Format:** Table with 3 columns
```
Season/Folder   | Original Path                  | New Name (Editable)
─────────────────────────────────────────────────────────────────
▼ Season 1      |                                |
  Season 1      | My Hero Academia/s1s1.mkv      | My Hero Academia S01E01.mkv
  Season 1      | My Hero Academia/s1s2.mkv      | My Hero Academia S01E02.mkv
▼ Specials      |                                |
  Specials      | Specials/s0s2.mkv              | My Hero Academia S00E02.mkv
```

**Features:**
- Shows ALL files in target pane (not just selected)
- Grouped by season with section headers
- Original path shows relative path from staging (tooltip shows full path)
- New name is editable - click to change
- Updates automatically when files moved or title changed
- Section headers are dark gray with white text

**Automatic Episode Detection:**
- Uses EpisodeParser to extract episode numbers
- Handles multiple formats:
  - Standard: S01E02, s01e02
  - Alternative: s01s02, s1s3
  - Single digits: - 1, - 5
  - Padded: - 01, - 05
  - Three digits: 026, 105
- **Retains original episode numbers** (critical feature)
- Falls back to regex if parser fails

### Movie Handling in Series Dialog (v1.5.0)

**Purpose:** Handle anime movies and other movies within a series

**"Move to Movies" Button:**
- Creates "Movies" folder in target tree
- Each movie gets its own subfolder within Movies/
- Uses same title inference as standalone movies dialog

**Filename Generation for Movies:**
- **No longer uses** "Title M01.ext" format
- **Now infers movie title from filename** (like movies dialog)
- Strips quality tags: `[1080p]`, `[BD]`, etc.
- Keeps year in parentheses: `(2011)`
- Each movie file keeps its unique descriptive name

**Examples:**
```
Original file: "Blue Exorcist Movie 01 [1080p][BD] (2011).mkv"
New filename:  "Blue Exorcist Movie 01 (2011).mkv"

Original file: "Your Name [BluRay] (2016).mkv"
New filename:  "Your Name (2016).mkv"
```

**Folder Structure:**
```
/staging/anime/Blue Exorcist/
  ├─ Season 1/
  │  ├─ Blue Exorcist S01E01.mkv
  │  └─ Blue Exorcist S01E02.mkv
  └─ Movies/
     ├─ Blue Exorcist Movie 01 (2011)/
     │  └─ Blue Exorcist Movie 01 (2011).mkv
     └─ Blue Exorcist Movie 02 (2017)/
        └─ Blue Exorcist Movie 02 (2017).mkv
```

**Key Differences from Regular Episodes:**
- Each movie gets its own subfolder (not in season folder with other files)
- Filename comes from title inference, not episode numbering
- Year is preserved in filename
- Quality tags are stripped

---

## Execution Behavior (CRITICAL)

### Where Files Go

**Files stay in staging, organized by media type:**

```
Before organize:
/staging/
  ├─ My Hero Academia S01/
  │  ├─ s1s1.mkv
  │  └─ s1s2.mkv
  └─ My Hero Academia [Specials]/
     └─ s0s2.mkv

After organize (Anime selected):
/staging/anime/
  └─ My Hero Academia/
     ├─ Season 1/
     │  ├─ My Hero Academia S01E01.mkv
     │  └─ My Hero Academia S01E02.mkv
     └─ Specials/
        └─ My Hero Academia S00E02.mkv

Original folders removed (empty).
```

**Media Type Folder Mapping:**
- TV Series → `/staging/TV Shows/[Title]/`
- Anime → `/staging/Anime/[Title]/`
- Movies → `/staging/Movies/[Title]/`

**Important:** Files are NOT moved to library directories. That will be handled by a separate Move tool (to be implemented).

### Cleanup Behavior

**Empty Folder Removal:**
- Source folders automatically deleted if empty after moving files
- Recursively removes nested empty folders
- Only affects folders within staging directory (safety check)

---

## Movies Organize Dialog

**Status:** Implemented and working (v1.5.0)

### Layout: Single-Pane with Editable Preview

```
┌────────────────────────────────────────────────────────────────┐
│               Organize Movies / Anime Movies                   │
├────────────────────────────────────────────────────────────────┤
│ Preview: Double-click on 'New Name' to edit                   │
├────────────────────────────────────────────────────────────────┤
│  PREVIEW (Table) - Editable                                    │
│  Original File           │  →  │  New Name / Action            │
│  Inception.mkv           │  →  │  Inception (2010).mkv  ← Edit │
│  sample.avi              │  →  │  (will be removed)            │
│  info.txt                │  →  │  (will be removed)            │
├────────────────────────────────────────────────────────────────┤
│                          [Cancel]  [Execute]                   │
└────────────────────────────────────────────────────────────────┘
```

### Simplified Design Philosophy (v1.5.0)

**Removed:** Media title field (was redundant)
**Added:** Editable preview table with direct inline editing

**Why the change:**
- Each movie folder already has its own name with year
- Title field was confusing and redundant
- Users can now directly edit any filename in the preview
- Much simpler workflow: auto-infer → edit if needed → execute

### Automatic Title Inference

**Each file automatically gets its title from its folder name:**

**Inference Logic:**
- Strips quality tags: `[1080p]`, `[720p]`, `[BD]`, `[BluRay]`
- Strips release groups
- **Keeps year in parentheses**: `(2010)`
- Cleans extra spaces and formatting

**Examples:**
- Folder: `"Inception [1080p][BD] (2010)"` → File: `"Inception (2010).mkv"`
- Folder: `"The Matrix (1999) [720p]"` → File: `"The Matrix (1999).mkv"`
- Folder: `"Parasite (2019)"` → File: `"Parasite (2019).mkv"`

### Editable Preview Table

**Features:**
- **Single-selection mode** (not multi-select)
- **Double-click "New Name" column to edit** any filename
- Original file and arrow columns are read-only
- Changes saved automatically when editing
- Context menu: Right-click → "Remove from organize"

**Column Behavior:**
- Column 0 (Original File): Read-only, white text
- Column 1 (Arrow): Read-only, gray text
- Column 2 (New Name): **Editable**, green text

**User Workflow:**
1. Dialog opens with all files showing auto-inferred names
2. Review the names
3. Double-click any "New Name" to customize it
4. Press Enter to save edit
5. Click Execute when satisfied

### Context Menu

**Purpose:** Remove unwanted files from organize operation

**Features:**
- Right-click on media file rows in preview table
- "Remove from organize" option
- Marks file as excluded (is_included = False)
- Preview updates to hide excluded files
- Non-media files cannot be excluded (always removed)

### Execution Behavior

**Where Files Go:**

**Each movie gets its own folder based on its inferred title:**
```
Before organize:
/staging/
  ├─ Inception (2010)/
  │  └─ Inception.mkv
  ├─ The Matrix (1999)/
  │  └─ Matrix.mkv
  └─ Interstellar (2014)/
     └─ Interstellar.mkv

After organize:
/staging/movies/
  ├─ Inception (2010)/
  │  └─ Inception (2010).mkv
  ├─ The Matrix (1999)/
  │  └─ The Matrix (1999).mkv
  └─ Interstellar (2014)/
     └─ Interstellar (2014).mkv

Original folders removed.
```

**Media Type Folder Mapping:**
- Movies → `/staging/movies/[Title]/`
- Anime Movies → `/staging/movies/[Title]/` (same as movies)

**Important:** Files are NOT moved to library directories. That will be handled by a separate Move tool (to be implemented).

### Cleanup Behavior

**Non-Media File Removal:**
- All files with non-video extensions removed after organize
- Includes: .txt, .nfo, .srt, sample files, etc.
- Only video files kept (.mkv, .mp4, .avi, .mov, etc.)
- Count shown in success message

**Empty Folder Removal:**
- Source folders automatically deleted if empty after moving files
- Recursively removes nested empty folders
- Only affects folders within staging directory (safety check)

### Data Structure

**Operations Dictionary:**
```python
{
    "mode": "multi" or "single",
    "single_title": "Movie Title" or None,
    "movies": [
        {
            "original_path": "/path/to/file.mkv",
            "movie_title": "Inception (2010)",
            "new_name": "Inception (2010).mkv"
        },
        # ... more movies
    ],
    "non_media_files": [
        "/path/to/sample.avi",
        "/path/to/info.txt"
    ]
}
```

**Media File Entries:**
```python
[
    {
        "folder": "Inception (2010)",
        "file_path": "/staging/Inception (2010)/Inception.mkv",
        "inferred_title": "Inception (2010)",
        "is_included": True  # Can be set to False via context menu
    },
    # ... more entries
]
```

---

## Technical Implementation

### Episode Parser

**EpisodeParser Features:**
- Multiple pattern support (S01E02, s01s02, - 1, - 01, 026)
- `parse()` - Full parse with season and episode
- `parse_episode_only()` - Just episode number (used when season known from context)
- Season hint detection in folder paths
- Fallback to regex if patterns fail

**Pattern Precedence:**
1. Special episodes: s00e01, s0s2
2. Standard: s01e02, s01s02
3. Alternative: 1x02
4. Three digit: 105 (season 1, episode 5)
5. Episode markers: e01, episode 01, ep 01
6. Pure numbers: 001, 01, 1

### File Operations

**When Execute Clicked:**
1. Creates media-type folder in staging (Anime, TV Shows, Movies)
2. Creates series folder within media-type folder
3. Creates season folders within series folder (or "Season 00" if setting enabled)
4. Moves and renames files using shutil.move()
5. Removes empty source folders
6. Auto-refreshes media tree (file watcher detects changes)

**No History Recording (for now):**
- File moves executed directly with shutil
- No undo support for organize operations (can be added later)

---

## Main Application Features

### Toolbar Layout (UPDATED in v1.5.0)

**Button Positioning:**
- Scan and Organize buttons are **centered** between Media Browser and Settings tabs
- Previously were on the left side of toolbar
- Makes them more prominent and easy to access

**Button States:**
- Scan: Always enabled
- Organize: Green when items selected, gray when disabled

### Processed Media Indicator (NEW in v1.5.0)

**Purpose:** Visually distinguish organized media from unorganized media

**Behavior:**
- Media titles in organizational folders (Anime, TV Shows, Movies) shown with **green indicator**
- Helps user identify which media has already been processed
- Media in root staging directory shown without indicator (not yet organized)

**Example:**
```
Media Tree:
├─ Random Folder [no indicator]        ← Not organized yet
├─ Anime/ [organizational folder]
│  └─ Naruto [green ✓]                 ← Organized/processed
├─ TV Shows/ [organizational folder]
│  └─ Breaking Bad [green ✓]           ← Organized/processed
└─ Unorganized Movie [no indicator]    ← Not organized yet
```

### Auto-Scan on Launch
- Application automatically scans staging on startup
- 100ms delay to let UI render first
- Shows helpful message if no staging configured

### File System Monitoring
- QFileSystemWatcher monitors staging directory
- Auto-refreshes tree when files added/removed/modified
- 1-second debounce to handle bulk operations
- Updates when staging directory changed in settings

### Organizational Folder Scanning (UPDATED in v1.5.0)
- Recognizes Anime, TV Shows, Movies folders (customizable in settings)
- Scans inside them for media titles
- Shows media titles directly in tree (not org folders)
- Sets media type based on which org folder they're in
- Media in org folders shown with green indicator (processed)

### Dynamic Cleanup Button
- Shows "Clean Staging Directory" when nothing selected
- Shows "Clean Selected (N)" when items selected
- Cleans selected folders or entire staging accordingly

### Cleanup Tool Features (UPDATED in v1.5.0)

**Sample File Detection & Preview:**
- When "Sample" category is selected, tool identifies sample files
- Shows preview dialog before deletion with list of files to be removed
- User must confirm deletion of samples
- Prevents accidental deletion of wanted files

**Cleanup Settings Persistence:**
- Checkbox states saved to settings.json
- Custom extensions text saved
- Settings automatically loaded on startup
- Saved on application close
- Uses 'any' match for forgiving category detection

**File Categories:**
- Images: .jpg, .jpeg, .png, .gif, .bmp, .webp
- Documents: .txt, .nfo, .pdf, .doc, .docx
- Subtitles: .srt, .sub, .ass, .ssa, .vtt
- Archives: .zip, .rar, .7z, .tar, .gz
- Data Files: .json, .yml, .yaml, .torrent
- **Sample Files:** Detects "sample" in filename (case-insensitive)

### Preview Tab
- Console area has two tabs: Console and Preview
- Preview shows full file/folder structure of selected items
- Recursively displays all folders and files
- Shows file sizes in human-readable format
- Color-coded: folders (blue), files (gray)
- Auto-updates when selection changes

### Settings Toast
- Green toast notification when switching from Settings tab
- Matches green organize button color
- Shows "Settings saved" message

---

## Application Settings (UPDATED in v1.5.0)

### Specials Folder Naming

**Purpose:** Choose how special episodes are organized

**Options:**
- **Unchecked (Default):** Folder named "Specials"
  - Example: `/staging/Anime/Naruto/Specials/`
- **Checked:** Folder named "Season 00"
  - Example: `/staging/Anime/Naruto/Season 00/`

**File Naming:**
- Files always use S00Exx format regardless of folder name
- Example: "Naruto S00E01.mkv"

**Use Case:**
- Some media servers prefer "Season 00" naming convention
- Others prefer "Specials" for clarity
- User can choose based on their library management software

### Organizational Folder Names (NEW in v1.5.0)

**Purpose:** Customize the names of organizational folders in staging

**Configurable Folders:**
1. **Anime Folder** (default: "Anime")
2. **TV Shows Folder** (default: "TV Shows")
3. **Movies Folder** (default: "Movies")

**Settings Interface:**
- Text entry fields for each folder name
- Changes apply on settings save
- Scanner uses these names to identify organizational folders
- Execute operations create folders with these names

**Examples:**
```
Default:
/staging/Anime/
/staging/TV Shows/
/staging/Movies/

Custom (if user prefers):
/staging/Anime Series/
/staging/Television/
/staging/Films/
```

**Important:**
- Folder names must be unique
- Scanner looks for these exact names to identify processed media
- Changing names requires re-organizing existing media
- Empty values revert to defaults

---

## Example Workflow

### Scenario: Organizing 3 My Hero Academia Folders

1. **User selects 3 folders:**
   - "My Hero Academia S01"
   - "My Hero Academia [Specials]"
   - "My Hero Academia S02"

2. **Click green "Organize" button (or right-click → Organize)**
   - MediaTypeDialog appears

3. **User selects "Anime"**
   - SeriesOrganizeDialog opens
   - Title field shows: "My Hero Academia"

4. **Source pane shows:**
   ```
   ├─ My Hero Academia S01
   │  ├─ s1s1.mkv
   │  ├─ s1s2.mkv
   │  └─ s1s3.mkv
   ├─ My Hero Academia [Specials]
   │  └─ s0s2.mkv
   └─ My Hero Academia S02
      ├─ episode_01.mkv
      └─ episode_02.mkv
   ```

5. **User organizes (using keyboard shortcuts):**
   - Selects files from "My Hero Academia S01"
   - Presses `1` → Files moved to Season 1

   - Selects files from "My Hero Academia [Specials]"
   - Clicks "Move to Specials" → Files moved to Specials

   - Selects files from "My Hero Academia S02"
   - Presses `2` → Files moved to Season 2

   (Alternative: User could click "Move to Season" buttons instead of hotkeys)

6. **Target pane shows:**
   ```
   Season 1
   ├─ My Hero Academia S01E01.mkv
   ├─ My Hero Academia S01E02.mkv
   └─ My Hero Academia S01E03.mkv

   Season 2
   ├─ My Hero Academia S02E01.mkv
   └─ My Hero Academia S02E02.mkv

   Specials
   └─ My Hero Academia S00E02.mkv
   ```

7. **Preview table shows all files grouped by season**
   - User can edit individual filenames if needed

8. **User clicks "Execute"**
   - Files organized within staging
   - Creates: `/staging/anime/My Hero Academia/Season 1/...`
   - Original folders cleaned up
   - Success message: "Successfully organized 6 file(s) in staging"
   - Tree auto-refreshes showing new structure

---

## Global Undo/Redo System (v1.5.1) - IMPLEMENTED ✓

### Overview
A global undo/redo system that tracks all file operations performed in the application and allows users to reverse them.

### Architecture

**Command Pattern Implementation:**
- Base `Command` class with `execute()`, `undo()`, and `describe()` methods
- Concrete command classes for each operation type
- `UndoRedoManager` maintains command history stacks

**Command Types:**
1. **OrganizeCommand** - Tracks organize operations (series/movies)
2. **MoveCommand** - Tracks move operations
3. **RenameCommand** - Tracks rename operations
4. **DeleteCommand** - Tracks delete operations (with trash recovery)
5. **CleanupCommand** - Tracks cleanup operations

### Features

**History Management:**
- Configurable history depth (default: 50 operations)
- Undo stack and redo stack maintained separately
- Executing new operation clears redo stack

**UI Integration:**
- Toolbar buttons for undo/redo
- Keyboard shortcuts: Ctrl+Z (undo), Ctrl+Y or Ctrl+Shift+Z (redo)
- Button tooltips show operation description
- Disabled state when no operations available

**Operation Metadata:**
- Each command stores all information needed for reversal
- Timestamps for operation tracking
- Operation descriptions for user feedback

### Implementation Details

**UndoRedoManager:**
- Singleton pattern for global access
- Thread-safe operation (Qt signals/slots)
- Emits signals when undo/redo availability changes
- Integrates with main window for UI updates

**File Operation Tracking:**
- All file operations go through command objects
- Automatic history recording
- Preserves file metadata and structure
- Uses trash directory for deleted file recovery

### User Experience

**Feedback:**
- Success/error messages after undo/redo
- Clear descriptions of what was undone/redone
- Visual indication of undo/redo availability

**Limitations:**
- Cannot undo external file system changes
- History cleared on application restart
- Undo depth limited to prevent memory issues

---

## Future Enhancements (v2+)

- Auto-detect season from folder name in series organize
- Batch rename with patterns
- Episode title detection from online sources
- Conflict resolution UI for duplicate filenames
- Preview before/after comparison view
- Import/export organization profiles
- Multi-part movie detection and handling

---

**Last Updated:** 2025-11-08
**Version:** 1.5.0 (Enhanced Edition)
**Status:** V1 organize feature fully implemented and working

**Major Features:**
  - Series Organize Dialog: Complete with multi-pane layout, undo/redo, movie handling, keyboard shortcuts
  - Movies Organize Dialog: Complete with editable preview (simplified from v1.4.0)
  - Processed media indicator (green flag)
  - Customizable organizational folder names
  - Specials folder naming option (Specials vs Season 00)
  - Sample file preview in cleanup tool
  - Centered Scan/Organize buttons
  - Renamed tv_series → TV Shows
