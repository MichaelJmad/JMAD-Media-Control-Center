This is the definitive, comprehensive plan for the JMAD Media Tool (Version 1). This document, the **Developers Roadmap**, serves as the final functional specification and outlines every detailed workflow, backend process, and component interaction required for implementation.

---

# JMAD Media Tool: Developers Roadmap (Version 1)

## 1. Architectural Overview & Data Flow

The JMAD Media Tool operates as a persistent, single-instance application responsible for managing defined file system paths and persistent user settings. All processes prioritize non-destructive, preview-first operations.

### 1.1 Core Application Components

| Component | Responsibility | Persistent Data Storage |
| :--- | :--- | :--- |
| **Directory Monitor Service** | Persistent, low-impact background thread. Scans `Staging Path` and `Watch Directory`. Triggers **File Detection Workflow**. | Configuration settings (Paths, Scan Interval). |
| **State Manager** | Centralized authority for all Media Title statuses (Gray, Blue, Green, Error). Manages transitions and updates the main UI. | **Media Title Index:** Stores name, source path, target path (if processed), current state, and flag data. |
| **Metadata Engine** | Handles external API calls (TMDB, TVDB) and manages the generation/reading of NFO files and artwork assets. | API Keys, Preferred Languages, Default Watch Order. |
| **File Handler** | Executes all file system commands (Rename, Move, Delete, Rollback). **Must ensure all moves/renames are atomic operations.** | Naming Templates, Fluff Regex Patterns. |
| **Appearance Profiles** | Manages all visual settings (Themes, Status Colors, Icons). | Saved custom profiles (JSON). |

### 1.2 File Detection Workflow (Directory Monitor)

1.  **Trigger:** `Directory Monitor Service` detects new/changed content in `Staging Path` or `Watch Directory`.
2.  **Move (If applicable):** If content is detected in the `Watch Directory`, the `File Handler` executes an atomic move to the `Staging Path`.
3.  **Initial Scan:** The `File Handler` performs a recursive scan of the new folder/file structure.
4.  **Fluff Removal (Initial):** `File Handler` applies the default **Fluff Regex Patterns** to the root folder name and contained files.
5.  **Index/State Assignment:** A new entry is created in the `State Manager`.
6.  **UI Update:** The new Media Title is displayed in the Staging Directory UI with the **Unorganized (Gray)** status.

---

## 2. Core State Management and Workflow

All media titles progress through five primary states. State transitions are only triggered by explicit user interaction or automated post-processing routines.

### 2.1 State Definitions and Transitions

| State (Icon/Color) | Definition | Triggering Function | Next States |
| :--- | :--- | :--- | :--- |
| **⚪ Unorganized (Gray)** | Raw input. Only Fluff Removal is applied. Source/target structures are undefined. | `Directory Monitor` / User creates a new entry. | $\rightarrow$ **Processing (Blue)** |
| **🔵 Processing (Blue)** | Files are mapped, structured, and named according to templates. Naming is correct, but metadata is absent. | `processOrganize()` / `processRawFile()` | $\rightarrow$ **Ready (Green)** |
| **🟢 Ready to Move (Green)** | Complete and finalized. NFOs, artwork, and anchoring data are generated and saved internally. Safe for deployment. | `processMetadataFinalize()` | $\rightarrow$ **Live (Catalogue)** |
| **🟡 Warning (Yellow)** | Non-critical issue (e.g., Uncategorized files, quality check failure). Does not block state transition. | `setFlag(WARNING)` | N/A (Applies to any state) |
| **🔴 Critical Error (Red)** | Core file system operation failed (e.g., failed rollback, permissions denied). All processes are blocked. | `setError(CRITICAL)` | $\rightarrow$ **Unorganized (Gray)** (Only via manual Reset) |

### 2.2 User Workflow Steps

| Step | Status | Required Action | Function/System Triggered |
| :--- | :--- | :--- | :--- |
| **1. Ingest** | ⚪ Gray | User selects title to define mapping. | **Organization Dialog** (Single) or **Batch Organize Wizard** (Bulk). |
| **2. Structure** | 🔵 Blue | User confirms naming and structure. | `processOrganizeAndRename()` |
| **3. Finalize** | 🟢 Green | User verifies fetched NFO/Artwork. | `processMetadataFinalize()` |
| **4. Deploy** | N/A | User commits to final move. | `processMoveToLiveLibrary()` |
| **5. Live** | N/A | Media is moved to the target library. | `File Handler: atomicMove(source, target)` |

---

## 3. Detailed Workflow Functionality

### 3.1 Organization Dialog (Single Item Processing)

The dialog is segmented into three vertical panels:

1.  **Source Panel:** Displays the raw file/folder hierarchy. Allows toggling Raw/Clean names and moving files to **Uncategorized** or **Quarantine**.
2.  **Control Panel:** Houses the search bar (to map to an external database ID), Naming Template selector, and Anchoring tool.
3.  **Right Panel Preview:** **Must be a live, non-editable render.** It uses the selected **Naming Template** and the current **Metadata ID** to project the final file path and structure.

**Commit Action (`processOrganizeAndRename`):**
1.  Verify the selected **Naming Template** is valid.
2.  Execute file system operations (rename files, create new directory structure).
3.  On success: `State Manager` updates status $\rightarrow$ **Processing (Blue)**.
4.  On failure: `File Handler` triggers a **Critical Failure (Red)** error mode with logging.

### 3.2 Batch Organize Wizard (Bulk Processing)

This wizard handles multiple selected **Gray** items, transitioning them efficiently to the **Blue** state.

#### 3.2.1 Series Assumption Algorithm

1.  **Fluff Cleaning:** Run deep `Fluff Removal` on all selected items.
2.  **Grouping:** Items are grouped by high-similarity of the **Clean Name** (e.g., "Naruto Shippuden S03" and "Naruto Shippuden Movie" are grouped).
3.  **User Confirmation Loop:**
    * **Prompt 1 (Grouping):** Display the raw and clean names for the assumed group. User must confirm **which items belong** (Individual Target Confirmation). Items deselected are queued for the next loop.
    * **Prompt 2 (Search/ID):** User confirms the final series name (e.g., "Naruto Shippuden") and assigns the external ID.
    * **Layout Confirmation:** A simplified **Right Panel Preview** shows the planned merged structure (e.g., Season 1, Season 2, Movie merged under the single ID).
    * **Status Update:** Confirmed items transition to **Processing (Blue)**. Repeat until all selected items are processed.

### 3.3 State-Aware Merge Logic (Critical Safety System)

This logic prevents merging a raw (lower-state) file directly into a finalized (higher-state) structure, maintaining data integrity.

| Condition | Source State | Target State | Required Action Sequence |
| :--- | :--- | :--- | :--- |
| **Standard Merge** | 🔵 Blue | 🟢 Green or 🔵 Blue | `File Handler`: Merge files into target structure. |
| **CRITICAL Merge** | ⚪ Gray | 🟢 Green or 🔵 Blue | **1. User Prompt:** Must explicitly confirm the pre-processing. **2. `State Manager`:** Queues the source item for **forced `processOrganizeAndRename()`**. **3. Final Action:** After successful processing to **Blue**, the merge is completed. |

---

## 4. Advanced Subsystems Specification

### 4.1 Fluff Removal Engine

* **Implementation:** Must use a multi-stage approach: 1. Default system-wide Regex (pre-defined). 2. User-defined Regex patterns (customizable). 3. Manual override/whitelist (per-file exclusion).
* **Application:** Applied aggressively during the **File Detection Workflow** and the **Batch Organize** process.
* **Validation:** Must prevent accidental removal of critical identifiers (e.g., season/episode numbers, titles).

### 4.2 Media Title Anchoring System

* **Implementation:** The `Metadata Engine` fetches a full chronological/canonical watch order list (if available).
* **Anchoring Data:** Must rely on specific NFO tags (`sorttitle`, `episode` number) to insert movies or specials correctly into the episodic timeline.
* **Manual Override:** The **Anchoring Interface** must be a drag-and-drop UI that allows the user to manually adjust the order of episodes/movies/specials within the timeline, overwriting scraped anchor data.

### 4.3 Error and Transactional Rollback

The `File Handler` must treat all structural file changes (renames, moves, folder creation) as a single transaction:

1.  **Critical Failure:** If any step fails (e.g., target directory creation, file lock), the entire sequence halts.
2.  **Rollback:** The `File Handler` attempts to undo any successful changes made during that specific operation (e.g., deleting partially created folders, restoring original file names).
3.  **Logging:** Log full details to the **Console Panel** and set the Media Title state to **Critical Error (Red)**.

### 4.4 Directory Management (Safety)

| Folder | Purpose | Functional Requirement |
| :--- | :--- | :--- |
| **Staging Directory** | Primary input/processing area. | Monitor Service runs here. All state transitions occur here. |
| **Uncategorized Folder** | User-flagged items requiring review. | Must *not* be monitored by the `Directory Monitor Service`. Only manual interaction allowed. |
| **Quarantine Folder** | Items marked for removal/deletion. | Must have a dedicated **Purge** function and a **Restore** function linked to the file's original path metadata. |
| **Watch Directory** | Automated input drop point. | Must be monitored by the `Directory Monitor Service`. All detected items are *moved*, not copied, to Staging. |

---

## 5. Customization and Aesthetics Specification

The application uses a **Profile System** to manage all visual elements, ensuring consistent aesthetics while allowing user preference.

### 5.1 Appearance Profiles Structure

The `Appearance Profiles` system manages two categories of settings simultaneously:

1.  **Status Visuals:** Custom hex codes and icon/emoji assignments for the five core status states (Gray, Blue, Green, Yellow, Red).
2.  **Application Theme:** The three primary color components that define the UI: **Primary Background**, **Text Color**, and **Accent Color**.

### 5.2 Default Theme Specifications

The application ships with three base themes, each offering a Dark Mode and a Light Mode (using muted gray backgrounds to prevent eye strain).

| Theme Name | Mode | Primary Background | Accent Color | Text Color |
| :--- | :--- | :--- | :--- | :--- |
| **Jmad** | **Dark (Default)** | Deep Charcoal Gray | Dark Greenish Gray | Muted White |
| **Jmad** | **Light** | Muted Light Gray | Pale Greenish Gray | Charcoal Gray |
| **Mike** | **Dark** | Deep Charcoal Gray | Bright Pink | Muted White |
| **Mike** | **Light** | Muted Light Gray | Soft Pastel Pink | Charcoal Gray |
| **Kerberos** | **Dark** | Deep Charcoal Gray | Nuclear Warning Orange | Muted White |
| **Kerberos** | **Light** | Muted Light Gray | Soft Pale Orange | Charcoal Gray |

---

## 6. Future Development (V2+)

The following features are deferred and retained for the long-term roadmap:

* **Audio Language Sampling:** Requires complex DSP/ML libraries to analyze audio tracks and identify spoken language.
* **Post-Move Server Webhook:** Integration with media server APIs (Plex/Jellyfin) to trigger a library scan automatically.
* **Automated Media Acquisition Integration:** Leveraging the **Get List** foundation to communicate with external tools (e.g., Radarr/Sonarr) for full lifecycle automation.
* **User Profiles:** Allowing multiple application users to save independent settings and themes.