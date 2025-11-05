# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JMAD Media Tool is a Python desktop application for organizing and renaming TV series, anime, and movie files. It provides a visual interface for scanning media directories, parsing filenames, organizing into seasons/specials, and batch renaming with undo/redo capabilities.

**Tech Stack:**
- Python 3 with tkinter
- ttkbootstrap for modern UI
- Portable application design (JSON-based settings/patterns)

## Development Commands

### Running the Application
```bash
# From V1 directory
python JMADMediaManager.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Testing Workflow
1. Configure staging directory in Settings
2. Create test media folders in staging with sample files
3. Run "Scan" to detect media
4. Test organize dialog, renaming, and cleanup features
5. Verify undo/redo functionality

## Architecture

### Core Components

**JMADMediaManager.py** - Main application file containing:
- `JMADMediaTool`: Main window class with media tree UI and toolbar
- `ConsolePanel`: Dockable/undockable console for logging
- `CleanupPanel`: Right-side panel for selecting file extensions to clean
- `SettingsDialog`: Configuration dialog for directories, patterns, naming conventions

**media_models.py** - Data models and business logic:
- `Episode`, `Season`, `Series`: Data models for media items
- `BatchAction`, `HistoryManager`: Undo/redo system
- `scan_media_roots()`: Recursive directory scanner with media type inference
- Filename parsing functions: `parse_episode_info()`, `parse_movie_info()`, `predict_new_filename()`
- Settings/patterns persistence

**series_organize_dialog.py** - Dialog for organizing TV series and anime:
- Three-pane layout: Source files → Actions → Target structure
- Local undo/redo for in-dialog changes
- Preview pane showing current vs. new filenames
- Supports moving files to seasons, specials, custom folders
- Conflict detection and resolution

**movie_organize_dialog.py** - Dialog for organizing standalone movies:
- Table view with original file, assumed title, proposed path
- Edit movie titles by double-clicking
- Conflict detection for duplicate titles and existing folders
- Local undo/redo

**media_type_selection_dialog.py** - Initial dialog for selecting media type before organizing (TV Series, Anime, Movie, Anime Movie)

### Key Design Patterns

**Media Type Workflow:**
1. User selects series in tree and chooses "Organize"
2. `MediaTypeSelectionDialog` prompts for media type
3. Based on selection, opens either `SeriesOrganizeDialog` or `MovieOrganizeDialog`
4. Dialog builds file operations, user confirms, operations execute via `HistoryManager`

**Filename Parsing Strategy:**
- Multiple regex patterns in `EPISODE_PATTERNS` (media_models.py:268-279)
- Priority order: S00E01 specials → SxxExx → xxExx → 3-digit → 2-digit
- Negative lookaheads prevent partial matches
- Fluff removal via user-configurable regex patterns

**Undo/Redo System:**
- `HistoryManager` tracks batch file move operations
- Stores (source, destination) tuples for each file
- Undo reverses operations and prunes empty directories
- Dialog-local undo/redo for tree structure changes before committing

**Settings Persistence:**
- `settings.json`: Directories, naming patterns, console visibility, cleanup states
- `patterns.json`: User-defined regex patterns for name cleaning
- Changes auto-save when modified in SettingsDialog

### Important File Locations

**Configuration:**
- `settings.json`: Runtime settings (created on first run)
- `patterns.json`: Regex patterns for filename parsing

**Portable Directories (auto-created):**
- `database/`, `logs/`, `themes/`

**Assets:**
- `JMADMMT.ico`: Application icon

## Development Notes

### When Adding Features

**For new media type handling:**
- Update `MEDIA_TYPES` in JMADMediaManager.py:27
- Add logic in `scan_media_roots()` for type inference
- Consider if existing `SeriesOrganizeDialog` or `MovieOrganizeDialog` can handle it

**For new filename patterns:**
- Add regex to `EPISODE_PATTERNS` in media_models.py
- Update `parse_episode_info()` to handle new pattern's capture groups
- Test with edge cases (e.g., "S00E01", "301", "3x05")

**For new cleanup extensions:**
- Add to `CLEANUP_EXTS` in media_models.py:14
- Update `DEFAULT_SETTINGS["cleanup_ext_states"]["selected"]` for defaults

### Critical Behaviors

**File Operations Safety:**
- All moves go through `HistoryManager.execute_action()`
- Always provide `stop_at` parameter to prevent pruning above staging root
- Check for conflicts before executing (duplicate filenames, existing paths)
- Trash directory support: moves to mirrored trash folder if configured

**Media Tree Updates:**
- Always call `scan_root()` after file operations to refresh UI
- Tree displays media type as column and uses tags for non-standard folders
- Supports Ctrl+A for select-all and click-on-empty-space to deselect

**Dialog State Management:**
- Local undo stacks in organize dialogs don't affect global history
- Must call `_capture_state()` after tree modifications
- Conflicts disable Apply button until resolved

### Known Constraints

- Windows path handling (uses `os.path` throughout, assumes backslashes on Windows)
- Staging directory is primary scan location; other directories (tv_shows, movies, anime) are supplementary
- Media type inference can be overridden but is initially based on directory structure and filename patterns
- Year extraction from movie filenames uses pattern: `[\(\[._\-\s](\d{4})[\)\]_\-\s]`

## Common Tasks

**Adding a new toolbar button:**
1. In `JMADMediaTool._build_ui()` around line 243
2. Add `tb.Button(toolbar, text="Label", command=self.method_name)`
3. Implement method in `JMADMediaTool` class

**Modifying rename patterns:**
- Episode pattern format: `{series}`, `{season:02d}`, `{episode:02d}`, `{ext}`
- Movie pattern format: `{series}`, `{year}`, `{ext}`
- Edit in Settings UI or directly in settings.json

**Adding new organize dialog features:**
1. Modify tree structure in `_build_ui()` method
2. Update `populate_trees()` to populate new UI elements
3. Add to `_capture_state()` for undo support
4. Modify `apply_changes()` to execute new file operations

## Debugging Tips

- Console panel shows all file operations and errors
- Enable debug prints in `scan_media_roots()` (already present with `print(f"DEBUG: ...")`)
- Check `media_models.py:346-487` for detailed media scanning debug output
- Test undo/redo after any file operation changes
