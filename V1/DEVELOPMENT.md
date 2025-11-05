# JMAD Media Tool - Development Overview

This document describes the current development state and UI layout of the JMAD Media Tool, aiming to facilitate further development and bug fixing.

## Current Application State

The JMAD Media Tool is a Python-based desktop application designed for media organization and renaming. It utilizes `tkinter` with `ttkbootstrap` for its graphical user interface. The application's core functionality includes scanning media directories, organizing files based on user-defined patterns, and providing undo/redo capabilities for file operations.

Currently, the application appears to be in a functional state, providing a comprehensive set of features for media management as described in `USER_GUIDE.md`.

## Key Features Implemented:

*   **Major Refactor: Organize Dialogs and Media Type Handling:** The `OrganizeDialog` has been refactored into a new architecture to provide a more intuitive and robust media organization workflow. This includes:
    *   **`MediaTypeSelectionDialog`**: A new initial dialog to prompt the user for the media type (TV Series, Anime, Anime Movie, Movie) before proceeding to the specific organization dialog.
    *   **`SeriesOrganizeDialog`**: A dedicated dialog for organizing TV Series, Anime, and Anime Movies. It features an editable series name, source/target panes, and controls for moving media to seasons, specials, movies (within a series), or custom folders. It supports local undo/redo for in-dialog changes.
    *   **`MovieOrganizeDialog`**: A dedicated dialog for organizing standalone Movies, including multi-selection. It presents a list of movies with editable assumed titles, proposed new paths, and conflict indicators. It also supports local undo/redo.
    *   **`MediaOrganizer` (Backend Logic)**: A new, abstracted component responsible for all core media organization and renaming logic, independent of the UI. It manages different internal data models for series and movies, implements specific renaming rules, conflict detection, and folder structuring.
    *   **`JMADMediaTool` Updates**: The main application's `scan_tv_root` has been refactored to `scan_media_roots` to scan all relevant media type directories and infer media types. The `populate_series_tree` now displays series/movie titles directly, with media type as a column/tag, without showing top-level media type folders. The `.jmad_info.json` metadata file has been removed, with media type and processed status now managed dynamically in memory.
    *   **Staging Root Handling**: The system continues to handle media titles located directly within the main staging directory, outside of any media type-specific parent folders.

*   **Media Scanning:** Scans a user-defined staging directory for TV series and movie files.
*   **Interactive Media Tree:** Displays detected series, seasons, and individual files, with visual indicators for processed status and non-standard folders.
*   **Filename Renaming:** Applies user-configurable naming patterns for episodes and movies, with a real-time preview of new filenames.
*   **Undo/Redo History:** Implements a history manager for batch file operations, allowing users to revert or re-apply changes.
*   **File Cleanup:** Identifies and deletes extraneous files (e.g., `.nfo`, `.txt`, image files) within series folders.
*   **Series Moving:** Functionality to move entire series folders to designated destinations or custom locations.
*   **Settings Management:** User-configurable settings for directories, naming patterns, and regex patterns for name suggestion.
*   **Console Logging:** An integrated console panel for logging application activities and messages.
*   **Media Type Assignment:** Ability to mark series as processed and assign media types (TV Series, Anime, Movie, Anime Movie).

## Completed Changes to Achieve "Working Order"


*   **Media Scanning:** Scans a user-defined staging directory for TV series and movie files.
*   **Interactive Media Tree:** Displays detected series, seasons, and individual files, with visual indicators for processed status and non-standard folders.
*   **Organize/Combine Series Dialog:** Allows users to graphically organize files into seasons, specials, or custom folders, and combine multiple series.
*   **Filename Renaming:** Applies user-configurable naming patterns for episodes and movies, with a real-time preview of new filenames.
*   **Undo/Redo History:** Implements a history manager for batch file operations, allowing users to revert or re-apply changes.
*   **File Cleanup:** Identifies and deletes extraneous files (e.g., `.nfo`, `.txt`, image files) within series folders.
*   **Series Moving:** Functionality to move entire series folders to designated destinations or custom locations.
*   **Settings Management:** User-configurable settings for directories, naming patterns, and regex patterns for name suggestion.
*   **Console Logging:** An integrated console panel for logging application activities and messages.
*   **Media Type Assignment:** Ability to mark series as processed and assign media types (TV Series, Anime, Movie, Anime Movie).

## Completed Changes to Achieve "Working Order"

The following outlines the changes that have been implemented to address feedback and achieve a more robust and functional application, with a focus on media type integration, improved specials detection, and enhanced movie handling.

### Media Type Selection Default to Empty
*   The `MEDIA_TYPES` global variable was updated to include an empty string, allowing the media type selection to default to nothing selected.
*   The `Series` class now initializes `media_type` to an empty string.
*   `scan_tv_root` now defaults `media_type` to an empty string if not found in metadata.
*   The `OrganizeDialog`'s `Combobox` for media type now includes the empty option and has a trace to react to changes.
*   `JMADMediaTool.set_series_type` was updated to handle the empty media type, unmarking as processed and removing the metadata file if selected.

### Improved Specials Detection
*   The `EPISODE_PATTERNS` list in `JMADMediaManager.py` was enhanced with a new regex pattern (`s00[exs](\d{1,3})`) to specifically detect specials (e.g., `S00E01`, `S00S01`).
*   The `parse_episode_info` function's logic was updated to correctly interpret this new pattern, assigning `season 0` for specials.
*   Negative lookaheads (`(?!\d)`) were added to the 3-digit and 2-digit episode number regex patterns to prevent partial number matches, making the parsing more robust.

### Robust Rename Process and Fluff Parser
*   The `Episode` class now stores `original_basename` to preserve the initial filename.
*   `predict_new_filename` now returns `None` if it cannot determine a new name, instead of a generic "InvalidPattern".
*   `OrganizeDialog._update_preview_tree` was modified to:
    *   Display the `original_basename` in the "New Name" column if `predict_new_filename` returns `None`.
    *   Visually flag these entries with an `unnamed` tag (yellow foreground).
*   `OrganizeDialog._apply_preview_renames` was updated to store the intended new filename (or original if undetermined) in the `tags` of the `target_tree` item.
*   `OrganizeDialog.apply_changes` (specifically `plan_moves_from_tree`) now uses the `intended_new_filename` from the `target_tree` item's tags, ensuring files are moved with their original names if no new name was determined or edited.

### Enhanced Movie Handling (Normal and Anime Movies)
*   **Dynamic Restructuring:** `OrganizeDialog._on_media_type_change` now calls `_restructure_for_movies` when "Movie" or "Anime Movie" is selected. This dynamically rebuilds the `target_tree` to a "folder-per-movie" structure (e.g., `MovieTitle/MovieFile.ext`).
*   **Synchronized Renaming:** `OrganizeDialog._on_target_tree_double_right_click` was enhanced to synchronize renaming: if a movie folder is renamed, its child media file is updated, and vice-versa.
*   **Movie-Specific Naming:** A new function `predict_new_movie_filename` was added to handle movie naming patterns.
*   **Preview Update:** `OrganizeDialog._update_preview_tree` now correctly uses `predict_new_movie_filename` and displays appropriate `current_display` for movies.
*   **Associate Anime Movie Logic:** `AssociateMovieDialog._apply_association` was modified to:
    *   Find the actual video file within the selected "Anime Movie" series folder.
    *   Move the video file and any other associated files into a new subfolder named after the movie (without extension) under the parent series' `Movies` folder (e.g., `ParentSeriesName/Movies/MovieTitle/MovieFile.ext`).

### `scan_tv_root` Enhancement for Subfolders Named After Movies
*   The `scan_tv_root` function was enhanced to correctly identify and categorize movie files within `Movies/MovieTitle` subfolders. It now assigns a `season_hint` of `-1` (for movies) and uses the `MovieTitle` (the subfolder name) as the `series_name` for the `Episode` object, ensuring these are properly recognized in the application's internal data model.

### UI Change: Cleanup Tool Replaces Info Preview Panel
*   The `InfoPreviewPanel` has been removed from the main application window.
*   A new `CleanupPanel` has been integrated into the main window, replacing the `InfoPreviewPanel`.
*   The `CleanupPanel` provides checkboxes for selecting common and uncommon file extensions to be cleaned.
*   The `clean_files_tool` in `JMADMediaTool` has been modified to:
    *   Accept a set of extensions to clean (from the `CleanupPanel`).
    *   Clean only selected series in the `series_tree` if any are selected.
    *   Clean the entire staging directory if no series are selected.
*   Calls to `self.info_panel.update_info()` have been removed.
*   The "Clean Files..." menu entries from the main toolbar and right-click context menu have been removed, as cleanup is now initiated directly from the `CleanupPanel`.

### Indentation and Syntax Fixes
*   All identified `IndentationError` and syntax issues within the `CleanupPanel` class and the `OrganizeDialog._update_preview_tree` method have been thoroughly reviewed and corrected.

### UI Fixes and Enhancements
*   The `right_paned` in `JMADMediaTool._build_ui` now has `expand=True` removed from its `grid` call (as it's not a valid option for `grid`), relying on parent `rowconfigure`/`columnconfigure` and `sticky="nsew"` for expansion.
*   A "Custom Extensions" input field has been added to the `CleanupPanel`, allowing users to specify additional file extensions for cleanup. These custom extensions are parsed and included in the cleanup process.
*   **Pane Sizing Adjustment:** The weights for `cleanup_container` and `console_container` in `JMADMediaTool._build_ui` have been adjusted to `weight=4` and `weight=1` respectively, ensuring the console pane takes up approximately the bottom fifth of the right pane, and the cleanup tool fills the rest.
*   **CleanupPanel Layout Refactor:** `CleanupPanel._build_ui` has been refactored to use the `grid` layout manager for its internal elements, providing more robust control over sizing and visibility of the common, uncommon, and custom extension options. This also enables multi-column display for the common and uncommon file checkboxes.
*   **Console Initial Size:** An initial `height=10` (lines) has been set for the `scrolledtext` widget within the `ConsolePanel`, ensuring it starts at a smaller, more manageable size while still allowing manual resizing.

### Bug Fix: Series Not Displaying in Media Tree
*   A call to `self.populate_series_tree()` was added to `JMADMediaTool.scan_root` after `self.series_map` is populated, ensuring that scanned series are displayed in the media tree.

### Cleanup Extensions Update
*   The `.docx` extension has been added to the `ALL_CLEANUP_EXTS` set in `CleanupPanel` and is now included in the default selected extensions for cleanup.

### Cleanup Tool Toggles Persistence
*   `DEFAULT_SETTINGS` now includes a `cleanup_ext_states` key to store the selected cleanup extensions and custom extensions string.
*   `CleanupPanel._build_ui` has been updated to load these states from `self.app.settings` when the panel is built, initializing the checkboxes and custom extension input field accordingly.
*   `CleanupPanel._run_cleanup` has been updated to save the current state of selected extensions and the custom extensions string back to `self.app.settings` and then calls `save_settings()` to persist these changes to `settings.json`.

### Media Tree Enhancements
*   **Deselection:** A `_clear_selection` method has been added to `JMADMediaTool` and bound to the `series_tree`'s `<Button-1>` event, allowing users to deselect items by clicking on empty space.
*   **Unsorted Node Display:** `JMADMediaTool.populate_series_tree` has been modified to display individual filenames under an "Unsorted" node, providing a clearer view of the unsorted content.
*   **Deep Expansion:** A `_expand_all_children` method has been added to `JMADMediaTool` and bound to the `series_tree`'s `<<TreeviewOpen>>` event, enabling automatic recursive expansion of all sub-nodes when a parent node is expanded.
*   **Dynamic Cleanup Button Text:** The "Run Cleanup" button in the `CleanupPanel` now displays dynamic text based on the selection in the `series_tree`: "Run Cleanup (X Selected Items)" if items are selected, or "Run Cleanup (All Staging)" if no items are selected. This is handled by a new `cleanup_button_text_var` in `CleanupPanel` and a `_update_cleanup_button_text` method in `JMADMediaTool`, which is called on `<<TreeviewSelect>>` events and during initial setup.
*   **Bug Fix: Dynamic Cleanup Button Text on Deselection:** The `_clear_selection` method has been updated to explicitly call `_update_cleanup_button_text` after clearing the selection, ensuring the button text correctly reflects the deselected state.

### Organize Dialog Enhancements
*   **Retain Year in Movie Filenames:**
    *   A new `parse_movie_info` function has been added to extract year patterns from movie filenames.
    *   The `Episode` class now includes an optional `year` attribute.
    *   `scan_tv_root` has been updated to populate `Episode.year` for movie files using `parse_movie_info`.
    *   `predict_new_movie_filename` has been modified to gracefully handle `ep.year` being `None` when formatting the movie pattern.
*   **Combine AssociateMovieDialog with OrganizeDialog (Dynamic Update):**
    *   The `AssociateMovieDialog` class has been removed.
    *   `JMADMediaTool.set_series_type` now opens `OrganizeDialog` directly for Anime Movie association, passing an `is_anime_movie_association` flag.
    *   `OrganizeDialog.__init__` now accepts and stores the `is_anime_movie_association` flag.
    *   `OrganizeDialog._build_ui` has been modified to include an initially hidden association controls frame (combobox for existing parent series, entry for new parent series) for Anime Movie association.
    *   `OrganizeDialog._on_media_type_change` has been updated to dynamically show/hide/update these association controls based on the selected media type.
    *   `OrganizeDialog.apply_changes` has been significantly modified to handle the Anime Movie association logic, including creating new parent series folders and moving files into the correct structure.
*   **Disable 'Final Series Name' for 'Movie' Type:** The "Final Series Name" entry box in `OrganizeDialog` is now disabled when "Movie" is selected as the media type, and a placeholder text "Movie" is set.
*   **Target Tree Root Display:**
    *   A root node (`self.target_tree_root_id`) has been added to the `target_tree` in `OrganizeDialog._build_ui`.
    *   `OrganizeDialog._on_media_type_change` has been updated to dynamically set the text of this root node based on the media type: "Movie" for normal movies, and the `target_name_var` (series name) for TV Series/Anime.
    *   A trace has been added to `target_name_var` to update the root node's text when the series name changes.
*   **Movie Renaming Logic for Multiple Selections:** `OrganizeDialog.move_selection_to_folder` has been modified to correctly apply the folder-per-movie structure when moving items to "Movies" for movie media types.

### Cleanup Tool: Move to Mirrored Trash Folder
*   A new `"trash"` directory setting has been added to `DEFAULT_SETTINGS`.
*   `JMADMediaTool.clean_files_tool` has been modified to move files to a mirrored trash directory (configured in settings) instead of permanently deleting them. If the trash directory is not configured or invalid, it falls back to permanent deletion with a warning.

### Organize Dialog Initial Size
*   The initial size and minimum size of the `OrganizeDialog` have been reduced to `1000x700` and `800x600` respectively, making it smaller by default while retaining user resizing capabilities.

### Bug Fix: Organize Dialog Cycling Errors
*   The `_tkinter.TclError: Item I001 not found` error, which occurred when cycling series types in the `OrganizeDialog`, has been resolved by ensuring that the `self.target_tree_root_id` is re-created within `OrganizeDialog._restructure_for_movies` and `OrganizeDialog.populate_trees` after the `target_tree` is cleared.

## Initial Test Plan (After Implementation of All Changes):

1.  **Run the application.**
2.  **Verify New Features:**
    *   **Media Type Default:** Open the "Organize Series" dialog for a new series. Check that the "Set Type As" dropdown defaults to empty.
    *   **Specials Detection:** Create a test folder with a special named `S00S1.Mkv` and `S00E02.mkv`. Scan the staging directory. Open the `Organize Dialog` for this series and observe if `season 0` and the correct episode numbers are parsed.
    *   **Undetermined Names:** Create a file with a very unusual name that `predict_new_filename` is unlikely to parse (e.g., `My.Random.Video.File.2023.no.pattern.mp4`). Verify it gets flagged in yellow with its original name in the preview. Try editing the name. Try applying changes without editing.
    *   **Movie Handling (Normal):** Change a series to "Movie" type in the `Organize Dialog`. Observe if the `target_tree` restructures correctly (folder per movie). Verify that the "Final Series Name" entry is disabled and shows "Movie". Rename a movie file and its parent folder; verify synchronization.
    *   **Anime Movie Handling (Simplified for V1):**
        *   Select an item in the media tree and set its type to "Anime Movie".
        *   Open the `Organize Dialog` for this item. Verify that the association controls (combobox for existing parent series, entry for new parent series) are *not* visible.
        *   Verify that the "Final Series Name" entry is disabled and shows "Movie" (or similar placeholder, as it's now treated like a regular movie for V1).
        *   Verify that the `target_tree` restructures correctly (folder per movie) and that renaming works as for normal movies.
    *   **Cleanup Tool UI:** Verify that the Cleanup Tool pane is visible and resizes correctly. Check that the "Run Cleanup (Selected or All Staging)" button is visible and its text updates dynamically based on media tree selection. Test adding custom extensions (e.g., `.log`, `.bak`) and running cleanup with them. Ensure the common and uncommon file checkboxes are now visible and functional, and are displayed in multiple columns, including the newly added `.docx` extension. Verify that the state of these checkboxes and the custom extensions field persists after closing and reopening the application.
    *   **Media Tree Deselection:** Click on an item in the media tree to select it, then click on an empty space within the treeview. Verify that the item is deselected.
    *   **Media Tree Deep Expansion:** Expand a parent node in the media tree. Verify that all its sub-nodes (children, grandchildren, etc.) also expand automatically.
    *   **Media Tree Unsorted Display:** If you have unsorted files, verify that they are listed individually under an "Unsorted" node when the series is expanded.
    *   **Cleanup Tool Trash Functionality:** Configure a trash directory in settings. Run cleanup on some test files. Verify that the files are moved to the trash directory with a mirrored structure, and not permanently deleted. Test with an unconfigured trash directory to ensure permanent deletion with a warning.
3.  **Basic Regression:** Quickly re-test core TV series organization to ensure no regressions.
4.  **Error Handling:** Intentionally create scenarios to trigger errors (e.g., missing staging dir, permission issues, malformed patterns.json) and observe how the application handles them.

All requested changes have been implemented. Please proceed with testing according to the plan above. Let me know if you encounter any issues or have further modifications.