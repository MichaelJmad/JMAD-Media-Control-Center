# JMAD Media Tool V2 - Project Log

## 2025-10-31

*   **Phase 1: Foundation & UI Shell**
    *   Set up the initial project structure with `main.py`, `app/`, `config/`, and `tests/` directories.
    *   Created `v2/app/main_window.py` and implemented the `MainWindow` class.
    *   Built the three-panel layout using `QSplitter` for the media tree, info/preview, and console panels.
    *   Added the main toolbar and menu bar with placeholder actions.

*   **Phase 2: Directory Scanning & State Display**
    *   Created the `DirectoryMonitor` service using the `watchdog` library to monitor the staging directory.
    *   Created the `StateManager` service to manage the media item state in a SQLite database.
    *   Integrated the `DirectoryMonitor` and `StateManager` into the `MainWindow`.
    *   Implemented the initial population of the media tree from the database.
    *   Used `QThread` and `Signal` for thread-safe communication between the `DirectoryMonitor` and `MainWindow`.
    *   Created a `SettingsManager` to handle loading and saving settings from a `settings.json` file.
    *   The `DirectoryMonitor` now uses the staging directory from the settings file.
    *   Added error handling to `StateManager` and `SettingsManager`.
    *   Added unit tests for `StateManager` and `SettingsManager`.

*   **Phase 3: The Unified Organize View**
    *   Created the `views` directory and the `organize_dialog.py` file.
    *   Implemented the basic layout of the `OrganizeDialog` with source, action, and target panes, and a top toolbar.
    *   Added an "Organize" button to the toolbar and a corresponding action to the "Tools" menu in `MainWindow` to open the `OrganizeDialog`.
    *   Created a `MetadataService` to interact with the TMDB API.
    *   Integrated the `MetadataService` into the `OrganizeDialog` to provide series search functionality.
    *   Added a placeholder for the TMDB API key in `settings.json`.