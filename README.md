# JMAD Media Control Center (JMCC)
### The Ultimate Desktop Organizer & Library Manager for Home Media Collections

**JMAD Media Control Center (JMCC)** is a high-performance desktop application designed to streamline media file renaming, staging consolidation, library mapping, and wishlist monitoring across multiple storage drives. It bridges raw file intake with clean, standardized, home theater-ready media libraries.

---

## 🌟 Key Features

### 📂 Intelligent Staging & Media Renamer
* **Fluff Stripping Parser:** Automatically parses raw, cluttered filenames (e.g. from downloads) to extract clean titles, seasons, and episode numbers.
* **Extras Folder Mapping:** Easily routes non-credit specials (NCOPs, NCEDs), filler, and bonus files into dedicated extras subdirectories without polluting main media player catalogs.
* **Manual & Batch Renumbering:** Includes a robust actions editor to renumber multi-file lists, shift episode counts sequentially, or map specific files to alternate seasons.

### 🏛️ Smart Library Management & Multi-Drive Consolidation
* **Drive-Aware Copy-Verify-Delete:** Moves organized files across drives with transactional safety. It automatically verifies destination file integrity before deleting source files, protecting against transfer data loss.
* **Free Space Warning:** Enforces a 10 GB safety margin on target drives, automatically suggesting alternative drives or prompting to relocate entire series directories to keep collections consolidated.
* **Cached Library Browser:** Renders local directories instantly using smart data caching while refreshing directory changes in the background.

### ⚖️ Side-by-Side Merge Collision Wizard
* **Automatic Preflight Collision Detection:** Scans library contents by title and metadata API IDs before moving files, flagging pre-existing items.
* **Technical Spec Comparison:** Displays colliding episodes side-by-side, exposing differences in **file sizes, video resolutions, video codecs, and audio tracks** to let you easily choose which version to preserve.

### 📋 Tag-Based Wishlist
* **Flexible Sub-Lists:** Organizes items using filter tags (e.g. Get List, On Hold, Backlog, Needs Fixed).
* **Automatic Acquisition Sweeper:** A background health scanner checks library additions against metadata API IDs, automatically purging wishlist items once they are successfully acquired.
* **Needs Fixed Relocation:** Mark files needing adjustment in the library browser to physically move them to a separate workspace folder while flagging them in the wishlist UI with a distinct visual badge.

### 🗺️ Watch Order Timeline Visualizer
* **Interactive Canvas:** Build chronological timelines of complex series, spinoffs, and movies using a visual drag-and-drop node canvas.
* **Relational Branch Shifting:** Automatically shifts movie and spinoff cards on the canvas when parent season nodes are collapsed or expanded, keeping layouts organized.

---

## 💾 Installation & Setup

### 1. Download the Release
Go to the **Releases** tab of the GitHub repository and download the latest version:
* **Installer (`.exe`):** Recommended for full desktop integration.
* **Portable (`.exe`):** Run the application directly without installation.
* **ZIP Archive:** Extract and run the application executable.

### 2. Configuration Mappings
On first launch, open the **Settings** panel (cog icon) to configure:
1. **Staging Directory:** The folder where raw downloaded folders are staged for organization.
2. **Library Directories:** Your destination media folders (supports multiple drives).
3. **Metadata Providers:** Toggle integrations for TMDB (movies/TV), AniList, and MyAnimeList (MAL) for automated title lookups.

---

## 📖 Basic Workflow

1. **Intake (Staging):** Place your raw media files in the Staging folder and click **Scan Staging** inside the app.
2. **Link Metadata:** Link unmapped folders to metadata providers using the search drawer.
3. **Organize:** Click **Organize** to let the app naturally group and rename files into standardized season directories.
4. **Merge to Library:** Click **Move to Library**. The app checks for collisions, prompts you to select versions in the **Merge Wizard** if conflicts exist, and safely transfers files to your permanent collection in the background.

---

## 💻 System Requirements

* **Operating System:** Windows 10 or Windows 11 (64-bit).
* **Storage:** Compatible with NTFS, exFAT, and local network shared drives.
* **Hardware:** Minimal CPU and RAM footprint; performance scales dynamically with multi-core processors during library scans.
