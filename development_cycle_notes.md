# JMAD Media Tool V2 - Phased Development Cycle

This document outlines a logical, phased approach to developing the JMAD Media Tool V2, prioritizing foundational systems and user-facing configuration early in the cycle.

---

### Phase 0: Foundation & UI Shell

**Goal:** Create the non-functional skeleton of the application. This phase establishes the project structure and the main window, but with no working logic.

- **0.1. Project Scaffolding:**
  - Create the complete directory structure (`/app`, `/config`, `/tests`, etc.).
  - Initialize the main application entry point (`main.py`).
  - Install initial core dependencies (`PySide6`, `watchdog`, `requests`).

- **0.2. Database Initialization:**
  - Define the complete `SQLite` database schema to support all planned features (Staging, Libraries, Wish List, Trash Bin).
  - Create a `DatabaseManager` class to handle all connections and queries.

- **0.3. Main Window Construction:**
  - Build the primary application window, implementing the three-panel layout (Media Tree, Info/Preview, Console) with draggable splitters.
  - Implement the main toolbar and top-level menu structure with disabled actions.

---

### Phase 1: Settings & Configuration (High Priority)

**Goal:** Build a fully functional Settings dialog. This is prioritized because many subsequent features depend on being able to read configuration values.

- **1.1. Build the Settings UI:**
  - Construct the complete Settings dialog window with all planned tabs: `General`, `Directories`, `Renaming`, `Metadata`, `Libraries`, `Cleaning`, `Trash Bin`, `Appearance`, `Hotkeys`, and `Performance`.

- **1.2. Implement Configuration Backend:**
  - Create a `SettingsManager` class responsible for reading from and writing to configuration files (e.g., `config/settings.json`).
  - Implement the logic to load all settings on application startup and provide them to other components.

- **1.3. Connect UI to Backend:**
  - Link all the UI controls (checkboxes, text fields, sliders) in the Settings dialog to the `SettingsManager`.
  - Ensure that changes made in the UI are correctly saved to disk, and that the UI correctly reflects the loaded settings.

---

### Phase 2: The Core Workflow (Staging & Organization)

**Goal:** Implement the primary user workflow for identifying, structuring, and processing media files.

- **2.1. Directory Monitoring & State Management:**
  - Implement the `Directory Monitor` service to watch the staging folder.
  - Implement the `State Manager` to receive events from the monitor and add new files to the database with the `Unorganized` (Gray) status.

- **2.2. UI Population:**
  - Connect the main Media Tree view to the database. The tree should now populate with items from the staging directory and display their status.

- **2.3. Build the Unified Organize View:**
  - Create the complete `Organize View` dialog (Source, Action, and Target panes).
  - Implement the Series Search functionality to connect to metadata providers.
  - Implement all manual and automated sorting logic.

- **2.4. Finalize File Processing:**
  - Implement the `File Handler` logic triggered by the "Process Files" button.
  - This will perform the actual file renaming and moving on disk and update the item's status in the database to `Processed` (Blue).

---

### Phase 3: Automation & Deployment

**Goal:** Implement the 'magic' steps that happen after initial organization.

- **3.1. Metadata Enrichment:**
  - Fully implement the `Metadata Engine` to download NFO files, artwork, etc., for all items in the `Processed` state.
  - Handle potential errors and update item status to `Error` (Red) if fetching fails.

- **3.2. Final Renaming & Deployment:**
  - Apply the user's final, complex renaming patterns (from Settings).
  - Update the item's status to `Ready to Move` (Green).
  - Implement the final "Move to Library" action.

---

### Phase 4: Post-Milestone Feature Implementation

**Goal:** Build the major features that exist outside the core staging workflow. These can be developed in parallel or sequentially.

- **4.1. Libraries & Wish List:**
  - Build the UI for the Libraries view, including the Wish List and dynamic library tabs.
  - Implement the Library Scanner and all associated logic (missing media detection, 'Collected' status updates).

- **4.2. Cleaning Tool:**
  - Implement the 'Quick Clean' and 'Advanced Clean' functionalities.

- **4.3. Trash Bin:**
  - Build the Trash Bin view.
  - Implement the database logic for tracking deleted items and the 'Smart Restore' functionality.

---

### Phase 5: Polish & Finalization

**Goal:** Add the final layer of polish and user-centric features to complete the application.

- **5.1. Appearance & Theming:**
  - Implement the full theme engine, connecting the options in the `Appearance` settings tab to the live application UI.
  - Implement the Status Color Profile editor.

- **5.2. Hotkey System:**
  - Implement the global hotkey manager.
  - Connect the `Hotkeys` settings tab to the manager to allow for user customization.

- **5.3. Final Review:**
  - Conduct thorough end-to-end testing.
  - Fix remaining bugs and address any performance bottlenecks.
  - Finalize any user-facing documentation or tooltips.
