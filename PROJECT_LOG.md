# JMAD Media Tool V2 - Project Log

## 2025-10-12: Initial Development & Phase 2 Completion

This log entry summarizes the initial development sprint, covering the completion of Phase 1 and Phase 2 of the V2.0 implementation roadmap.

### Phase 1: Foundation & UI Shell (Complete)

The initial phase focused on establishing the core architecture and UI skeleton of the application.

- **Project Structure:** A new `v2` directory was created to house the new application, separating it from the V1 files. A full subdirectory structure (`app`, `ui`, `services`, `database`) was created.
- **Dependencies:** The project was set up to use `PySide6` for the UI, `watchdog` for file monitoring, and `requests` for future API calls.
- **UI Shell:** The main application window was built using `PySide6`. It features a three-panel layout with resizable splitters for the Media Tree, Info/Preview, and Console panels. Based on initial review, the top menu bar was removed in favor of a cleaner toolbar-only navigation.
- **Database:** A `DatabaseManager` class was created to handle an SQLite database. The manager was later refactored to be thread-safe using `threading.local()` to prevent cross-thread errors during background operations.

### Phase 2: Directory Scanning & State Display (Complete)

This phase focused on making the application aware of the file system and displaying that information to the user.

- **File System Monitoring:** A `DirectoryMonitor` service was implemented to run in a background thread and watch the `staging` directory for file creation, deletion, and modification events.
- **State Management:** A `StateManager` was created to interface between the `DirectoryMonitor` and the `DatabaseManager`. When a new file is detected, the `StateManager` now correctly adds it to the database with an "Unorganized" status.
- **UI Population & Tree View:** The placeholder label in the UI's left panel was replaced with a `QTreeView`. Logic was implemented to read all media items from the database and populate the tree.
- **Hierarchical Display:** The tree view logic was significantly refined to correctly parse file paths and display them in a nested (hierarchical) folder structure, mirroring the file system. This involved fixing several bugs related to path-splitting on Windows.
- **Selection Model:** Based on a clarification of the project requirements, the tree view was updated to support standard multi-item selection using `Ctrl` and `Shift` keys (`ExtendedSelection`). The initial single-click toggle implementation was removed.

### Phase 3: The Unified Organize View (In Progress)

Work has begun on the core organization feature.

- **Dialog Creation (Subphase 3.1):**
    - The UI shell for the `OrganizeDialog` has been created.
    - The layout was significantly refined based on user feedback. The final layout includes a top search bar with a "Search" button, and a central "Action Pane" containing buttons for "Set as Season", "Set as Movie", "Set as Special", "Set as Custom", "Auto-Sort", "Undo", "Redo", and "Remove".
    - The logic to populate the dialog's "Source" tree was implemented. This logic correctly gathers all files from the user's selection in the main window (including expanding selected folders) and displays them in a nested tree.

- **Dialog Refinement (Subphase 3.1):** The layout for the `OrganizeDialog` was finalized after several iterations based on user feedback. The final design includes a "Search" button in the top toolbar and a central action pane with buttons for "Set as Season", "Set as Movie", "Set as Special", "Set as Custom", "Auto-Sort", "Undo", and "Redo". The logic to populate the dialog's source tree was also debugged to correctly handle nested structures when a folder is selected.
- **Series Search (Subphase 3.2):** Initial functionality has been implemented. The application now makes a "best guess" for the series title to auto-populate the search bar. The "Search" button "locks in" the title (whether guessed or manually entered) and displays it in a "Confirmed Title" label, preparing it for subsequent operations. This involved debugging the title-guessing logic and fixing a regex-related crash.

### Current Application State

The application is currently in a stable state where it can:
- Launch and display the main window.
- Monitor the `staging` directory for new files and add them to a persistent database in a thread-safe manner.
- Display all files from the database in a nested tree structure in the main window.
- Support multi-selection of items in the tree.
- Open the `OrganizeDialog` and populate its source view with the selected files.
- In the dialog, it can guess the series title and allow the user to "lock in" a confirmed title.

The next step is to begin implementing the manual sorting functionality (**Subphase 3.3**), starting with the "Set as Season" button.
