# JMAD Media Tool V2.0 - Development Cycle Notes

This document outlines the detailed breakdown of each development phase for the V2.0 milestone.

### Phase 1: Foundation & UI Shell (Complete)
*   **Subphase 1.1: Project Scaffolding:** Set up project structure and dependencies.
*   **Subphase 1.2: Main Window Construction:** Build the main window with a three-panel layout.
*   **Subphase 1.3: Toolbar & Menus:** Implement the main toolbar and placeholder actions.
*   **Subphase 1.4: Database Initialization:** Create the initial SQLite database schema.

---
### Phase 2: Directory Scanning & State Display (Complete)
*   **Subphase 2.1: Directory Monitor Service:** Implement the background file watcher.
*   **Subphase 2.2: State Manager Integration:** Connect the file watcher to the database.
*   **Subphase 2.3: Populate Media Tree:** Display database items in the main window's tree view.
*   **Subphase 2.4: Tree View Interaction:** Implement selection and interaction logic for the tree.
*   **Subphase 2.5: Implement Multi-Selection:** Enable multi-item selection with Ctrl/Shift.

---
### Phase 3: Settings
*   **Subphase 3.1: UI Scaffolding:** Build the basic settings window with a tabbed or sectioned layout.
*   **Subphase 3.2: Directories Tab:** Implement UI and logic for setting the Staging and Library paths.
*   **Subphase 3.3: Renaming Patterns Tab:** Implement UI for managing regex patterns for title cleaning and file renaming.
*   **Subphase 3.4: Metadata Tab:** Implement UI for metadata provider settings (e.g., API keys), media server preferences (Plex/Jellyfin), and artwork choices.
*   **Subphase 3.5: Saving & Loading:** Implement the logic to save all settings to a persistent file (e.g., `settings.json`) and load them when the application starts.
*   **Subphase 3.6: Cleaning Tab:** Implement UI for configuring the Cleaning Tool options.
*   **Subphase 3.7: Trash Tab:** Implement UI for managing the Trash Bin settings.
*   **Subphase 3.8: Libraries Tab:** Implement UI for the placeholder Libraries tab.

---
### Phase 4: The Unified Organize View
*   **Subphase 4.1: Dialog Creation:** Build the `Organize View` dialog window and its complete layout.
*   **Subphase 4.2: Series Search:** Implement the series search bar and title confirmation logic.
*   **Subphase 4.3: Manual Sorting:** Implement the logic for the 'Set as...' action buttons, handling both file and folder selections and the two-column target view.
*   **Subphase 4.4: Automated Sorting:** Implement the "Auto-Sort" button and its confirmation dialog.
*   **Subphase 4.5: Finalize Organization:** Implement the "Process Files" button to commit the plan to disk.

---
### Phase 5: Automated Enrichment & Deployment
*   **Subphase 5.1: Metadata Engine:** Implement the logic to fetch NFO files and artwork.
*   **Subphase 5.2: Final Renaming:** Apply the user-defined complex renaming patterns.
*   **Subphase 5.3: Update State to "Ready":** Transition the item's status after enrichment.
*   **Subphase 5.4: Move to Library:** Implement the final action to move processed files to the library.