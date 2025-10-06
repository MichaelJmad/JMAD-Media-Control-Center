
---

# JMAD Media Tool: Developers Roadmap (Version 1)

## 1. Architectural Overview & Data Flow

The JMAD Media Tool operates as a persistent, single-instance application (desktop or server-side). It must manage file system paths and persistent user settings. All workflows prioritize **non-destructive, preview-first operations** and **atomic file handling**.

### 1.1 Core Application Components

| Component | Responsibility | Persistent Data Storage | Technical Notes |
| :--- | :--- | :--- | :--- |
| **Directory Monitor Service** | Persistent, low-impact background thread. Scans `Staging Path` and `Watch Directory` for changes (polling or OS events). Triggers **File Detection Workflow**. | Configuration settings (Paths, Scan Interval). | Must be highly optimized to minimize CPU/IO load. |
| **State Manager** | Centralized authority for all Media Title statuses (Gray, Blue, Green, Error). Manages transitions, indexes media, and updates the UI. | **Media Title Index (Database/JSON):** Stores source path, target path, current state, metadata ID (TMDB/TVDB), flag data, and **original raw name**. | Central object responsible for application state. |
| **Metadata Engine** | Handles external API calls (TMDB, TVDB) and manages the generation/reading of NFO files and artwork assets. | API Keys, Preferred Languages, Default Watch Order. | Must handle API rate limiting and return structured JSON for NFO generation. Targets media files (`.mkv`, `.mp4`) and standard image types. |
| **File Handler** | Executes all file system commands (Rename, Move, Delete, Rollback). **Must ensure all moves/renames are atomic operations.** | Naming Templates, Fluff Regex Patterns. | Operations must be executed using **Copy-Verify-Delete Original** or equivalent OS-level atomic operation to ensure data fidelity. |
| **Appearance Profiles** | Manages all visual settings (Themes, Status Colors, Icons). | Saved custom profiles (JSON). | Must be a reactive component for instant theme switching. |

### 1.2 File Detection Workflow (Directory Monitor)

1.  **Trigger:** `Directory Monitor Service` detects new/changed content in `Staging Path` or `Watch Directory`.
2.  **Input Handling:** If content is detected in the `Watch Directory`, the `File Handler` executes an **atomic move** to the `Staging Path`.
3.  **Initial Scan:** The `File Handler` performs a recursive scan, identifying media files and associated auxiliary files (e.g., subtitles, covers).
4.  **Fluff Removal (Initial):** `File Handler` applies the default **Fluff Regex Patterns** to the root folder name and contained files to create a **Clean Name**. The raw original name must be preserved in the `State Manager`.
5.  **Index/State Assignment:** A new entry is created in the `State Manager`.
6.  **UI Update:** The new Media Title is displayed in the Staging Directory UI with the **Unorganized (Gray)** status.

---

## 2. Core State Management and Workflow

State transitions are only triggered by explicit user interaction (`Commit Actions`) or automated post-processing routines.

### 2.1 State Definitions and Transitions

| State (Icon/Color) | Definition | Triggering Function | Next States |
| :--- | :--- | :--- | :--- |
| **⚪ Unorganized (Gray)** | Raw input. Only Fluff Removal is applied. Source/target structures are undefined. **Requires mapping to an external ID.** | `Directory Monitor` / User creates a new entry. | $\rightarrow$ **Processing (Blue)** |
| **🔵 Processing (Blue)** | Files are mapped, structured, and named correctly, but metadata (NFO/Artwork) is absent or incomplete. | `processOrganizeAndRename()` / `processRawFile()` | $\rightarrow$ **Ready (Green)** |
| **🟢 Ready to Move (Green)** | Complete and finalized. NFOs, artwork, and anchoring data are generated and saved internally. Safe for deployment. | `processMetadataFinalize()` | $\rightarrow$ **Live (Catalogue)** |
| **🟡 Warning (Yellow)** | Non-critical issue (e.g., **Uncategorized** files, quality deficiency). Appears as a *secondary icon/flag* and **does not block state transition.** | `setFlag(WARNING)` | N/A (Applies to any state) |
| **🔴 Critical Error (Red)** | Core file system operation failed (e.g., failed rollback, permissions denied). All related processes are blocked. | `setError(CRITICAL)` | $\rightarrow$ **Unorganized (Gray)** (Only via manual **Reset State** function) |

### 2.2 User Workflow Steps (Triggered Functions)

| Step | Status | Required Action | Function/System Triggered |
| :--- | :--- | :--- | :--- |
| **1. Ingest/Map** | ⚪ Gray | User maps raw content to a standard title and structure. | **Organization Dialog** or **Batch Organize Wizard** (triggers `processOrganizeAndRename()`) |
| **2. Structure/Rename** | 🔵 Blue | System performs file/folder renaming based on the chosen template. | `processOrganizeAndRename()` |
| **3. Finalize Metadata** | 🟢 Green | System fetches and saves NFO/Artwork. | `processMetadataFinalize()` (must use external API) |
| **4. Deploy** | N/A | User commits to final move to a Live Library. | `processMoveToLiveLibrary()` |
| **5. Live** | N/A | Media is moved to the target library. | `File Handler: atomicMove(source, target)` |

---

## 3. Detailed Workflow Functionality

### 3.1 Organization Dialog (Single Item Processing UI)

The dialog is segmented into three vertical panels and serves as the primary processing interface for single titles.

1.  **Source Panel (Left):** Displays the raw file/folder hierarchy. Contains controls to:
    * Toggle display between **Raw Name** and **Clean Name**.
    * Initiate move actions to **Uncategorized** or **Quarantine** folders.
2.  **Control Panel (Center):** Houses interactive elements:
    * **Search Bar:** Maps the title to an external database ID (TMDB/TVDB).
    * **Naming Template Selector:** Dropdown for selecting saved templates.
    * **Fluff Pattern Editor Access:** Button to temporarily modify or exclude fluff patterns for the selected item.
    * **Anchoring Tool Access:** Button to open the drag-and-drop anchoring interface (Section 4.2).
3.  **Right Panel Preview:** **Must be a live, non-editable render.** It uses the selected **Naming Template** and the current **Metadata ID** to project the final file path and folder structure *before* commitment.

**Commit Action (`processOrganizeAndRename`):** This is a single atomic execution that commits the renaming and structure creation.

### 3.2 Batch Organize Wizard (Bulk Processing)

This wizard handles multiple selected **Gray** items, minimizing repetitive search and mapping actions.

#### 3.2.1 Series Assumption Algorithm

1.  **Fluff Cleaning:** Run deep `Fluff Removal` on all selected items.
2.  **Grouping:** Items are grouped by high-similarity of the **Clean Name**.
3.  **User Confirmation Loop:**
    * **Prompt 1 (Grouping):** User confirms which items (e.g., files for Season 1 and files for Season 2) belong to the assumed group. Items deselected are queued for the next loop.
    * **Prompt 2 (Search/ID):** User confirms the final series name and assigns the external ID.
    * **Layout Confirmation:** A simplified **Right Panel Preview** shows the planned merged structure.
    * **Status Update:** Confirmed items transition to **Processing (Blue)**.

### 3.3 State-Aware Merge Logic (Critical Safety System)

This logic prevents merging lower-state content into higher-state content without required pre-processing, ensuring structural integrity.

| Condition | Source State | Target State | Required Action Sequence (Pre-Processing) |
| :--- | :--- | :--- | :--- |
| **Standard Merge** | 🔵 Blue | 🟢 Green or 🔵 Blue | `File Handler`: Merge (copy/move) files into target structure. |
| **CRITICAL Merge** | ⚪ Gray | 🟢 Green or 🔵 Blue | **1. User Prompt:** Must explicitly confirm the pre-processing. **2. `State Manager`:** Queues the source item for **forced `processOrganizeAndRename()`** (i.e., rename/structure creation). **3. Final Action:** After successful transition to **Blue**, the merge is completed. |

---

## 4. Advanced Subsystems Specification

### 4.1 Fluff Removal Engine

* **Implementation:** Must use a multi-stage approach: **1. Default system-wide Regex** (for standard tags like `[WEB-DL]`, `[YTS]`). **2. User-defined Regex patterns** (customizable in Settings). **3. Manual override/whitelist** (per-file exclusion).
* **Validation:** Regex logic must be validated to prevent accidental removal of critical identifiers (e.g., season/episode numbers, custom naming identifiers).

### 4.2 Media Title Anchoring System

* **Implementation:** The `Metadata Engine` fetches the full chronological/canonical watch order list (if available via API).
* **Anchoring Data:** Must rely on specific NFO tags (`sorttitle`, `episode` number) to insert movies or specials correctly into the episodic timeline.
* **Manual Override:** The **Anchoring Interface** must be a drag-and-drop UI that allows the user to manually adjust the order, overwriting scraped anchor data.

### 4.3 Error and Transactional Rollback

The **Console Panel** displays all logging and error output. The `File Handler` must treat all structural file changes as a single transaction:

1.  **Critical Failure:** If any step fails (e.g., target directory creation, file lock), the entire sequence halts.
2.  **Rollback:** The `File Handler` attempts to undo any successful changes made during that specific operation (e.g., deleting partially created folders, restoring original file names).
3.  **Logging:** Log full details to the **Console Panel** and set the Media Title state to **Critical Error (Red)**.

### 4.4 Directory Management (Safety)

| Folder | Purpose | Functional Requirement |
| :--- | :--- | :--- |
| **Staging Directory** | Primary input/processing area. | Monitor Service runs here. All state transitions occur here. |
| **Uncategorized Folder** | User-flagged items **unsure how to process** (e.g., partial files). | Must *not* be monitored by the `Directory Monitor Service`. Only manual interaction allowed. |
| **Quarantine Folder** | Items marked for removal/deletion (e.g., duplicates). | Must have a dedicated **Purge** function (permanent delete) and a **Restore** function linked to the file's original path metadata. |
| **Watch Directory** | Automated input drop point (e.g., torrent client completed downloads). | Must be monitored by the `Directory Monitor Service`. All detected items are **moved**, not copied, to Staging. |

### 4.5 Get List Management (V1 Foundation)

This module provides the structural foundation for future automated acquisition features, acting as a persistent list of desired media.

* **Persistence:** The list must be saved in the application's persistent storage.
* **Functionality:** Allows users to manually add, view, and mark as acquired, desired Movies and TV Series.
* **Data Fields:** Each entry must store at least: `Title`, `External ID` (optional), `Status` (Wanted, Acquired, Downloading), and `Type` (Movie/Series).

---

## 5. Customization and Aesthetics Specification

### 5.1 Appearance Profiles Structure

The `Appearance Profiles` system manages two categories of settings simultaneously: **Status Visuals** (fixed logic, customizable color/icon) and **Application Theme** (customizable background/text/accent colors).

### 5.2 Default Theme Specifications (Technical)

All themes use **Muted Light Gray (`#F0F0F0`)** for light modes and **Deep Charcoal Gray (`#2A2A2A`)** for dark modes to reduce eye strain.

| Theme Name | Mode | Primary Background (Color & Hex) | Accent Color (Color & Hex) | Text Color (Color & Hex) |
| :--- | :--- | :--- | :--- | :--- |
| **Jmad** | **Dark (Default)** | Deep Charcoal Gray (`#2A2A2A`) | Dark Greenish Gray (`#3d543a`) | Muted White (`#E0E0E0`) |
| **Jmad** | **Light** | Muted Light Gray (`#F0F0F0`) | Pale Greenish Gray (`#accea7`) | Charcoal Gray (`#333333`) |
| **Mike** | **Dark** | Deep Charcoal Gray (`#2A2A2A`) | Bright Pinkish (`#9a0d8f`) | Muted White (`#E0E0E0`) |
| **Mike** | **Light** | Muted Light Gray (`#F0F0F0`) | Soft Pastel Pink (`#ed83e4`) | Charcoal Gray (`#333333`) |
| **Kerberos** | **Dark** | Deep Charcoal Gray (`#2A2A2A`) | Nuclear Warning Orange (`#ff8b26`) | Muted White (`#E0E0E0`) |
| **Kerberos** | **Light** | Muted Light Gray (`#F0F0F0`) | Soft Pale Orange (`#ffa85c`) | Charcoal Gray (`#333333`) |

---

## 6. Future Development (V2+)

The following features are deferred and retained for the long-term roadmap (V2 and beyond):

* **Audio Language Sampling:** Advanced feature requiring complex Digital Signal Processing (DSP) or Machine Learning (ML) to analyze audio tracks and identify spoken language.
* **Post-Move Server Webhook:** Integration with media server APIs (Plex/Jellyfin) to trigger a library scan automatically upon successful deployment.
* **Automated Media Acquisition Integration:** Leveraging the V1 **Get List Management** foundation to communicate with external tools (e.g., Radarr/Sonarr) for full lifecycle automation.
* **User Profiles:** Allowing multiple application users to save independent settings and UI configurations.
