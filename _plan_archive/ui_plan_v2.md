# JMAD Media Tool - UI Plan (Version 2)

This document outlines the redesigned, tab-based user interface for the JMAD Media Tool.

## 1. Main Application Window

The application will be a single-window, tabbed interface with a global toolbar at the top.

*   **Global Toolbar:**
    *   **Context-Aware:** The toolbar will adapt to the active tab and selected item, showing relevant actions.
    *   **Navigation:** It will serve as the primary navigation for the application.
    *   **Menus:** It will feature a "Tools" menu and a "Settings" button.

## 2. Tab 1: Staging

This tab is for managing new and unorganized media.

*   **Layout:** A 50/50 vertical split.

*   **Left Panel: Media Tree**
    *   A tree-like view of the files and folders in the staging directory.
    *   Allows for easy navigation and selection of media files.

*   **Right Panel: Preview & Console**
    *   **Preview Area:** The top 75% of this panel will display a preview of the selected media file (e.g., a video player for movies, an image viewer for artwork).
    *   **Console:** The bottom 25% will be a console window that can be docked, undocked into its own floating window, or hidden entirely. When hidden or undocked, the preview area will expand to fill the entire right panel.

## 3. Tab 2: Libraries

This tab provides access to the user's media libraries and acquisition lists.

*   **Layout:** A sub-tabbed interface.

*   **Sub-Tab 1: Get List**
    *   This tab is for managing media that the user wants to acquire.
    *   It will contain its own set of sub-tabs for each library type (e.g., "Movies," "TV Shows," "Anime").

*   **Sub-Tabs 2-N: Live Libraries**
    *   A dedicated sub-tab for each media library defined in the settings (e.g., "Movies," "TV Shows," "Anime").
    *   Each tab will display the contents of the corresponding library.

## 4. In-App Dialogs & Views

To maintain a single-window experience, dialogs and settings will be handled within the main application window.

*   **Settings View:**
    *   Clicking the "Settings" button in the global toolbar will switch the main view to a dedicated settings area, replacing the tabbed interface. This provides ample space for configuration.
    *   A "Back" or "Save" button will return the user to the previous tabbed view.

*   **Tools Menu:**
    *   The "Tools" menu in the global toolbar will provide access to various application utilities. The tools currently planned are:
        *   **Fluff Regex Editor:** This tool will provide an interface for managing the regular expression patterns used for "fluff removal." Users will be able to:
            *   View and edit the default system-wide regex patterns.
            *   Add, edit, and delete their own custom regex patterns.
            *   Test patterns against sample file names to see the results in real-time.
        *   **Clean Files Tool:** (Description to be provided by the user).

This new plan aims to create a more unified and powerful user experience. Please let me know your thoughts on this direction, and we can refine it further.