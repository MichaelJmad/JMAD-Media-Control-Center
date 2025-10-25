# JMAD Media Tool V1 User Guide

## Introduction
The JMAD Media Tool is a robust application designed to help you organize and rename your TV series and movies. This guide will walk you through its features and how to use them effectively.

## Installation
To run the JMAD Media Tool, you need Python 3 and the `ttkbootstrap` library.
1.  **Install Python 3:** Download and install Python 3.x from [python.org](https://www.python.org/downloads/).
2.  **Install Dependencies:** Open your terminal or command prompt, navigate to the `V1` directory, and install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Application:** Execute the main Python script:
    ```bash
    python JMADMediaManager.py
    ```
    If you are using the packaged executable, simply run the `JMAD Media Tool.exe` file from the `dist` directory.

## Getting Started

### 1. Configure Directories
Upon first launch, or if your directories are not set, the application will prompt you to configure them. You can also access settings via the "Settings" button in the toolbar.
*   **Staging Directory:** This is the root directory where your unorganized media files are located. The tool will scan this directory for series and movies.
*   **TV Shows Directory:** The destination for your organized TV series.
*   **Movies Directory:** The destination for your organized movies.
*   **Anime Directory:** The destination for your organized anime series.

### 2. Scan Media
Click the "Scan" button in the toolbar to scan your configured "Staging Directory". The application will populate the "Media Tree" on the left with detected series and their files.
*   **Media Tree:** Displays a hierarchical view of your media.
    *   Top-level items are series names.
    *   Sub-items can be "Season XX", "Specials", "Movies" (for anime movies), or "Unsorted" (for files not clearly belonging to a season).
    *   A "☐" indicates the series is not yet processed, "✅" indicates it has been processed.
    *   Orange text indicates non-standard folder structures within a series.

## Core Features

### Organize / Combine Series
1.  **Select Series:** In the "Media Tree", select one or more top-level series you wish to organize or combine.
2.  **Open Organize Dialog:** Right-click on the selected series and choose "Organize / Combine Series...".
3.  **Final Series Name:** Enter the desired final name for the series. A suggestion will be provided based on common naming conventions. Click the suggestion to apply it.
4.  **Source Files (Left Panel):** This tree view shows all files currently associated with the selected series.
5.  **Target Structure (Right Panel):** This tree view represents how your files will be organized.
    *   **Move to Season:** Select files in the "Source Files" panel and click "Move to Season >>" to assign them to a specific season number.
    *   **Move to Specials:** Moves selected files to a "Specials" folder.
    *   **Move to Movies:** Moves selected files to a "Movies" folder (useful for anime movies).
    *   **Move to...:** Allows you to specify a custom folder name for selected files.
    *   **Rename Folders/Files:** Double-right-click on a folder or file in the "Target Structure" to rename it.
    *   **Conflicts:** Files with conflicting names in the same target folder will be marked in red. Resolve these before applying changes.
6.  **Rename Preview (Bottom Panel):** Shows the current and predicted new filenames based on your chosen patterns and organization.
    *   **Apply Renames to Target Structure:** Applies the suggested renames to the "Target Structure".
    *   **Edit New Name:** Double-right-click on a "New Name" in the preview to manually edit it.
7.  **Mark as Processed:** Check this box to mark the series as processed.
8.  **Set Type As:** Select the media type (TV Series, Anime, Movie, Anime Movie). For "Anime Movie", you will be prompted to associate it with a parent anime series.
9.  **Apply Changes / Combine:** Click this button to execute the file operations (moving, renaming, creating folders).

### Undo / Redo Actions
The tool includes an undo/redo history for file operations.
*   **Undo:** Reverts the last file operation.
*   **Redo:** Reapplies a previously undone operation.
*   **Clear History:** Clears all undo/redo history (accessible via the "Tools" menu).

### Clean Files
1.  **Select Series:** Select one or more top-level series in the "Media Tree".
2.  **Clean Files:** Go to "Tools" -> "Clean Files...". This will detect and offer to delete common cleanup files (e.g., `.nfo`, `.txt`, `.jpg`, `.srt`) within the selected series folders. This action is permanent.

### Move Selected To...
1.  **Select Series:** Select one or more top-level series in the "Media Tree".
2.  **Move Selected To...:** Go to "Tools" -> "Move Selected To..." or right-click on a series.
3.  **Choose Destination:** Select a predefined move preset or "Choose Location..." to browse for a new destination folder. This will move the entire series folder to the new location.

### Settings
Access settings via the "Settings" button in the toolbar.
*   **General Tab:**
    *   **Episode Pattern:** Define the naming pattern for TV series episodes (e.g., `{series} - S{season:02d}E{episode:02d}{ext}`).
    *   **Movie Pattern:** Define the naming pattern for movies (e.g., `{series} ({year}){ext}`).
    *   **Console Visible by Default:** Toggle the visibility of the console panel.
    *   **Directories:** Configure your staging, TV shows, movies, and anime directories.
*   **Patterns Tab:**
    *   Manage regex patterns used to clean up filenames and suggest series names. You can add, edit, or delete patterns.

### Console
The console panel (visible at the bottom right by default) logs all actions and messages from the application.
*   **Hide/Show Console:** Toggle its visibility via the "Tools" menu or the "Hide" button in the console header.
*   **Undock/Dock:** Undock the console into a separate window or dock it back into the main application.
*   **Clear:** Clears the console output.

## Troubleshooting
*   **"Staging Directory Not Set"**: Ensure your staging directory is configured in the settings and is a valid path.
*   **File Conflicts**: Resolve any red-highlighted conflicts in the "Target Structure" or "Rename Preview" before applying changes.
*   **Application Icon**: If the icon is not displaying, ensure `JMADMMT.ico` is in the `images/` directory.
*   **Missing Files after Move/Organize**: Check the console for any error messages during file operations.

## Support
For any issues or feedback, please report them using the `/reportbug` slash command in the chat.
