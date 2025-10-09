# JMAD Media Tool V2 — Consolidated Development Plan

---

## 1.0 Project Overview & Core Philosophy

### 1.1 Vision
The JMAD Media Tool V2 is a state-aware, highly customizable solution for organizing, enriching, and standardizing media files before their deployment to a live media server (e.g., Plex, Jellyfin). The goal is to replace tools like Tiny Media Manager with a more intuitive, powerful, and reliable system.

### 1.2 Core Philosophy: State-Driven Workflow
The application is built around a **State Management** philosophy. Media titles progress through a series of user-controlled states, ensuring that files are verified, correctly named, and metadata-rich before being moved. This prevents common library errors and gives the user full confidence and control over the process.

### 1.3 The Workflow & Status Protocol
The entire end-to-end workflow is tracked via a clear, color-coded status system. These colors will be customizable in the application's theme settings.

| Icon/Color | Status Name | Definition & Workflow Step |
| :--- | :--- | :--- |
| **⚪ Gray/White** | **Unorganized** | **Start:** Raw, unprocessed files are detected in the Staging Directory. They require user action to be identified and structured. |
| **🔵 Blue** | **Processing/Pending** | **Step 1 (Organize):** The user has processed the files through the **Unified Organize View**. The files now have a simple, machine-readable structure and are correctly associated with a media title. They are ready for automated enrichment. |
| **🟢 Green** | **Ready to Move** | **Step 2 (Enrich):** The application has automatically fetched all required metadata (NFO, artwork) and applied the user's final, complex naming patterns. The media is 100% complete and verified. |
| **➡️** | **Move to Library** | **Step 3 (Deploy):** The user gives the final command to move the "Green" files to the designated live library. |

---

## 2.0 Application Architecture (Pending Discussion)

The detailed backend architecture requires further discussion. The following components, originally outlined in the V1 roadmap, are proposed as a starting point for the discussion:

- **Directory Monitor Service:** A background service to watch the Staging Directory for new or changed files.
- **State Manager:** A central component to manage the state (Gray, Blue, Green) of all media items.
- **Metadata Engine:** Handles all external API calls (e.g., TMDB, TVDB) for fetching metadata and artwork.
- **File Handler:** Executes all file system operations (rename, move, delete) in a safe, atomic manner.

---

## 3.0 UI & Main Application Layout

### 3.1 Main Window
The application will feature a three-panel layout defined by a series of splitters:
- A main **horizontal splitter** divides the window into a 50/50 left and right side.
- **Left Panel (Media Tree):** The entire left side is dedicated to the media tree view.
- **Right Panel (Info/Preview & Console):** The right side contains a **vertical splitter**.
  - The top 75% of the right side is the **Info/Preview Panel**.
  - The bottom 25% of the right side is the **Console Panel**.

### 3.2 Toolbar & Menus
A standard toolbar will provide quick access to primary actions like `Scan Staging Directory`, `Settings`, and `Tools`. Context menus will provide item-specific actions.

### 3.3 UI Behavior Specifications

#### 3.3.1 Tree View Selection Logic
- **Single-Item Selection:** The tree view supports single-item selection with a toggle mechanism.
  - Clicking an item selects it.
  - Clicking the same item again deselects it.
  - Clicking in a blank (non-item) area of the tree view will clear any current selection.
- **Multi-Selection:** Multi-item selection (e.g., using `Ctrl` or `Shift`) is not part of the initial implementation but is planned as a future enhancement.
- **Note:** This selection behavior must not interfere with the standard double-click action to expand or collapse folders in the tree.

---

## 4.0 Core Workflow Features (First Development Milestone)

This section outlines the primary features required to deliver the complete end-to-end workflow.

### 4.1 Directory Scanning
The application will monitor the user-defined `Staging Directory`. New files will be added to the Media Tree with the `⚪ Unorganized` status.

### 4.2 The Unified Organize View
This is the user's primary tool for converting `⚪ Unorganized` media into `🔵 Processing` media.

**Workflow:**
1.  **Initiation:** The user selects one or more `Unorganized` files/folders and opens the Organize View.
2.  **Automated Analysis:** The system immediately runs a "batch analysis":
    - It uses regex to clean file/folder names ("Fluff Remover").
    - It groups items that appear to belong to the same series.
    - It makes a "best guess" at the Series Title.
3.  **Interactive View:** The main view appears, giving the user full control:
    - **Series Confirmation:** A search bar allows the user to confirm or find the correct media title and lock in its ID (from TMDB, etc.).
    - **Source Pane (Left):** Shows the original files in their automatically-guessed groups (e.g., Season 1, Season 2). The user can manually drag-and-drop items to correct any errors.
    - **Target Pane (Right):** A flat list showing `Current Name -> Proposed New Name`. The "Proposed New Name" is an **editable field**, generated based on the confirmed series and the simple structure rules.

**Structuring Rules for this Stage:**
- **Episodes:** Are structured simply (e.g., `Series Name - S01E01.mkv`).
- **Series-Related Movies:** Are placed in a dedicated `Movies` sub-folder: `[Series Name]/Movies/[Movie Name (Year)]/[Movie Name (Year)].mkv`.

### 4.3 Automated Processing (Blue -> Green)
Once media is in the `🔵 Processing` state, the user can trigger this fully automated step. The application will:
1.  Fetch all metadata (NFO files, posters, fanart, etc.) from the user's configured sources.
2.  Apply the user's final, complex **renaming patterns** defined in the application's settings.
3.  Upon completion, transition the media to the `🟢 Ready to Move` state.

### 4.4 Move to Library
The user can select any `🟢 Ready to Move` item and trigger this action, which will safely move the files and their accompanying metadata to the correct folder in the live library.

---

## 5.0 Settings
The following settings will be prioritized for the first milestone:
- **Directories:** Defining paths for the Staging Directory and one or more Live Library destinations.
- **Patterns (Renaming):** A section for users to define the complex file/folder naming patterns used in the Automated Processing step.
- **Metadata Sources:** API keys and preferences for TMDB, TVDB, etc.

---

## 6.0 Future Development (Post-Milestone 1)
The following major features are planned for subsequent development cycles:
- **Catalog Tab:** A comprehensive, searchable view of the user's live libraries, with features for tracking missing media.
- **Advanced UI Customization:** A theme editor for customizing all application colors, fonts, and icons.
- **Advanced Tools:** Additional utilities for library cleaning, duplicate detection, etc.
- **Plugin & Extension Support.**

---

## 7.0 Open Questions & Next Steps
- **Define Backend Architecture:** Finalize the design and technologies for the core application components.
- **Define Development Priorities:** Solidify the feature list and timeline for the first and subsequent development milestones.
