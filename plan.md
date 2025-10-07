# JMAD Media Tool - Development Plan

This document outlines the development plan for the JMAD Media Tool, based on the initial requirements and technology choices.

## 1. Technology Stack (Python Prototype)

*   **Language:** Python 3.10+
*   **UI Framework:** PyQt6 (for a robust and native-looking UI and tray icon functionality)
*   **Database:** JSON file (`media_index.json`) for the Media Title Index.
*   **Configuration:** JSON file (`config.json`) managed through the UI.
*   **Packaging:** PyInstaller to create a standalone executable.

## 2. Project Structure

```
/JMAD-Media-Tool
|-- /app
|   |-- /core
|   |   |-- __init__.py
|   |   |-- config_manager.py   # Manages config.json
|   |   |-- state_manager.py    # Manages media_index.json
|   |   |-- file_handler.py     # File operations, renaming templates
|   |   |-- metadata_engine.py  # TMDB/TVDB API interaction
|   |   |-- directory_monitor.py# Background file system watcher
|   |-- /ui
|   |   |-- __init__.py
|   |   |-- main_window.py      # Main application window
|   |   |-- tray_icon.py        # System tray icon and menu
|   |   |-- organize_dialog.py  # Dialog for organizing single titles
|   |   |-- batch_wizard.py     # Wizard for batch organizing
|   |   |-- settings_window.py  # UI for editing config.json
|   |-- main.py                 # Application entry point
|-- /docs
|   |-- README.md
|   |-- DevRoadMap.md
|   |-- plan.md
|-- config.json.template
|-- requirements.txt
```

## 3. Project Setup
* Create the project structure as defined in section 2.
* Initialize a git repository.
* Create initial empty files.
* Move documentation files (`plan.md`, `DevRoadMap.md`, `README.md`) to the `/docs` directory.

## 4. Phase 1: Core Infrastructure

### 4.1. Configuration Manager (`config_manager.py`)

*   Create a class to manage loading and saving `config.json`.
*   Define default settings (paths, API keys, templates).
*   Ensure it's portable by saving `config.json` in the application's root folder.

### 4.2. State Manager (`state_manager.py`)

*   Create a `MediaTitle` data class to hold information about each media item (source path, target path, state, metadata ID, etc.).
*   Create a `StateManager` class to:
    *   Load and save the list of `MediaTitle` objects to `media_index.json`.
    *   Provide methods to add, update, and retrieve media titles.
    *   Manage the state transitions (Unorganized, Processing, Ready to Move).

### 4.3. Directory Monitor Service (`directory_monitor.py`)

*   Implement a background thread that periodically scans the "Staging" and "Watch" directories defined in `config.json`.
*   When new files are detected, it should add them to the `StateManager` with the "Unorganized" status.

### 4.4. Metadata Engine (`metadata_engine.py`)

*   Create a class to interact with the TMDB and/or TVDB APIs.
*   Implement methods to search for media, fetch details, and download artwork.
*   Include a function to generate NFO files from the fetched metadata.

### 4.5. File Handler (`file_handler.py`)

*   Implement "fluff removal" logic to clean up file names.
*   Create a template engine to generate new file and folder names based on the templates in `config.json`.
*   Implement file operations (rename, move, delete) with a "preview-first" approach.

## 5. Phase 2: User Interface

### 5.1. Tray Icon (`tray_icon.py`)

*   Create a persistent tray icon.
*   Implement a context menu with options to "Show/Hide Window" and "Quit".

### 5.2. Main Window (`main_window.py`)

*   Create the main UI to display the list of media titles from the `StateManager`.
*   Display the status of each title with color indicators.
*   Add buttons to trigger the "Organize Dialog" and "Batch Organize Wizard".

### 5.3. Settings Window (`settings_window.py`)

*   Create a window to edit the settings from `config.json`.
*   Provide fields for paths, API keys, and renaming templates.

## 6. Next Steps & Open Items

*   **UI Mockups:** Once you have the UI mockups, we can refine the UI development plan.
*   **Error Handling:** We will need to define a strategy for handling and displaying errors (e.g., API errors, file access errors).
*   **First Implementation Step:** I will start by setting up the project structure and implementing the `ConfigManager`.