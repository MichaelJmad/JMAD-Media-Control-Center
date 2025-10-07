# JMAD Media Tool - UI Plan

This document outlines the user interface design and workflow for the JMAD Media Tool.

## 1. Main Window (`main_window.py`)

The main window is the central hub for managing media files.

*   **Layout:**
    *   A central table view will display the list of all media titles managed by the application.
    *   A toolbar at the top will contain the primary action buttons.
    *   A status bar at the bottom will provide feedback on background operations.

*   **Table View Columns:**
    *   **Status:** A color-coded icon indicating the current state (Unorganized, Processing, Ready to Move, Error).
    *   **Source Path:** The original location of the file.
    *   **Original Name:** The initial file name.
    *   **New Name:** The proposed new name (populated after organization).
    *   **Actions:** A button to open the "Organize Dialog" for each item.

*   **Toolbar Buttons:**
    *   **Organize:** Opens the "Organize Dialog" for the selected media file.
    *   **Batch Organize:** Launches the "Batch Organize Wizard" for multiple selected files.
    *   **Settings:** Opens the application settings window.
    *   **Exit:** Closes the application.

## 2. Tray Icon (`tray_icon.py`)

The tray icon provides quick access to essential functions without opening the main window.

*   **Context Menu (Right-Click):**
    *   **Show/Hide Window:** Toggles the visibility of the main application window.
    *   **Check for New Media:** Manually triggers a scan of the "Watch" and "Staging" directories.
    *   **Quit:** Exits the application.

## 3. Organize Dialog (`organize_dialog.py`)

This dialog is for processing a single media file.

*   **Layout:**
    *   Displays the original file name at the top.
    *   A search input field for finding the media title on TMDB or TVDB.
    *   A list to display search results.
    *   A preview section showing the proposed new file and folder structure.

*   **Workflow:**
    1.  The user enters a search query for the movie or TV show.
    2.  The application displays a list of matching titles from the selected metadata provider.
    3.  The user selects the correct title.
    4.  The dialog shows a preview of the new file name and folder structure based on the configured templates.
    5.  The user clicks "Approve" to confirm, and the media's state changes to "Processing."

## 4. Batch Organize Wizard (`batch_wizard.py`)

A step-by-step wizard to simplify organizing large batches of files, especially TV show episodes.

*   **Step 1: Grouping**
    *   The wizard automatically groups files based on file name similarity, assuming they belong to the same series.
    *   The user can review and adjust these groups.

*   **Step 2: Search & Identification**
    *   For each group, the user provides a search query to find the correct series on TMDB or TVDB.

*   **Step 3: Confirmation**
    *   The wizard displays a comprehensive preview of the new file and folder structure for all episodes across all seasons.

*   **Step 4: Processing**
    *   Upon confirmation, all media items in the batch are moved to the "Processing" state.

## 5. Settings Window (`settings_window.py`)

This window allows users to configure the application's behavior.

*   **Layout:** A tabbed interface to separate different settings categories.

*   **Tabs:**
    *   **Paths:** Input fields for the "Staging," "Watch," and final "Destination" directories.
    *   **API Keys:** Secure input fields for TMDB and TVDB API keys.
    *   **Naming Templates:** Editable text areas for defining the file and folder naming conventions for movies and TV shows.
    *   **Advanced:** Settings for the directory monitor's polling interval and other expert-level options.
