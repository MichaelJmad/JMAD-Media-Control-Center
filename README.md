# JMAD Media Control Center (JMCC)
### The Ultimate Desktop Orchestrator for Media Intake, Organization, and Library Synchronization

Welcome to the **JMAD Media Control Center (JMCC)** repository. JMCC is a high-performance desktop application designed to streamline media file renaming, metadata extraction, staging consolidation, library mapping, and wishlist monitoring across multiple storage drives.

Built on top of a multi-process desktop architecture, JMCC bridges raw file intake workflows with clean, standardized, home theater-ready media libraries.

---

## 🚀 Key Capabilities

* **3-Process Decoupled Architecture:** Built using **Electron + React 18 + TypeScript 5**. React runs a zero-blocking, fast renderer UI. The Main Process acts as a lightweight event router, while all CPU-intensive tasks (scanning, MediaInfo parsing, recursive folder copying) run inside isolated **Node Worker Threads** or **Utility Processes**.
* **2-Tier Database Engine:** Leverages a transactional SQLite database (`better-sqlite3`) separating metadata `Entities` from physical disk `Directories`. This handles folder movements and renames without orphan references or metadata loss.
* **Drive-Aware Staging-to-Library Engine:** Automatically consolidates items across multiple drives, calculates target volume capacities, performs same-drive instant moves where possible, and executes reliable cross-drive **Copy-Verify-Delete** operations.
* **Side-by-Side Merge Wizard:** When preflight scans detect library title collisions, it loads a side-by-side comparison screen exposing differences in **file sizes, video resolutions, video codecs, and audio formats**, letting you choose which release to preserve.
* **Integrated Tag-Based Wishlist:** Tracks needed items using custom filter tags (e.g. Dubs, On Hold, Backlog, Needs Fixed). Includes a background **Wishlist Health Checker** that matches local library API IDs (TMDB, AniList, MAL) to automatically purge acquisitions even if file names vary.
* **Diagnostics & Telemetry:** Features real-time operational logs visible in the console, controlled by centralized debug toggles, and persistent crash reports captured via the custom **BugBox** error monitor.

---

## 📂 Repository Structure

```
JMCC/
├── docs/                          # Architecture blueprints & decision logs
│   ├── README.md                  # This file
│   ├── MASTER_BLUEPRINT.md        # Technical architecture specifications
│   ├── MODULE_REGISTRY.md         # Inventory of services and functional contracts
│   ├── SESSION_GATEWAY.md         # Persistent workspace contexts
│   └── DECISION_LEDGER.md         # Detailed chronological engineering decisions
│
├── src/
│   ├── main/                      # Electron Main Process (Main Thread Orchestrator)
│   │   ├── main.ts                # Application bootstrapping & window manager
│   │   ├── ipc/                   # IPC channel registrations (Staging, Library, Settings, etc.)
│   │   ├── services/              # Core Services (FileSystem, Scanner, Move, Metadata, Wishlist)
│   │   └── workers/               # Worker Thread tasks (MediaInfo probing, file copying)
│   │
│   ├── renderer/                  # React Frontend Process (HTML/CSS/TSX)
│   │   ├── index.tsx              # React UI entry point
│   │   ├── App.tsx                # Page router & main wrapper
│   │   ├── components/            # UI components (Merge Wizard, Wishlist Module, Dialogs)
│   │   └── styles/                # CSS layout files and themes
│   │
│   ├── preload/                   # Electron Context Bridge
│   │   └── preload.ts             # Safe IPC channel exposure to React
│   │
│   └── shared/                    # Shared typings and constants
│       ├── types/                 # Shared TypeScript interfaces (media, ipc, settings)
│       └── constants/             # Default patterns, file extensions, configuration defaults
│
├── backups/                       # Automatic database and file backups
├── tmp_restore/                   # Mock media data structures for testing
└── package.json                   # Script mappings and dependencies
```

---

## 🛠️ Installation & Getting Started

### Prerequisites
* **Node.js LTS** (version 18 or newer recommended)
* **npm** (comes bundled with Node)
* **Windows OS** (optimized for Windows File System and PowerShell)

### 1. Clone & Install Dependencies
Clone the repository and run the package installation script:
```bash
git clone https://github.com/MichaelJMAD/JMCC.git
cd JMCC
npm install
```

### 2. Startup Scripts
For convenience, startup and development scripts are available in the root folder:
* **`run-dev.ps1`**: Executes Webpack in watch mode and spawns the Electron development window.
* **`launch.ps1`**: Installs dependencies and launches the application.
* **`package.ps1`**: Installs app dependencies and compiles binary builders.

Alternatively, execute standard commands:
```bash
# Compile bundle assets
npm run build

# Start Electron in development mode
npm run start
```

---

## 📦 Build & Packaging

To compile a production-ready package (ZIP, portable executable, or NSIS installer), run the package builder script:
```bash
npm run package
```
This script triggers Webpack compile pipelines, updates app dependencies, and outputs Windows binaries inside the `dist-app/` or `dist/` directories.

---

## 💾 Codebase Backups

To create a clean, lightweight backup archive of the workspace source code:
1. Open PowerShell.
2. Execute the included bracket-proof backup utility:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File .\backup.ps1
   ```
This script reads `package.json` to fetch the current version, sweeps the directory (omitting `node_modules`, `dist-app`, staging `tmp_restore` media folders, and historical backups), and creates a zipped release package under the parent directory (e.g. `../JMCC-v2.4.2-rc.2-<TIMESTAMP>.zip`).

---

## 🔌 IPC Communication API Contracts

All interaction between the React frontend UI and Node backend services is routed through secure Context Bridge IPC channels using the standard pattern `jmcc:{domain}:{action}`:

| IPC Channel | Mode | Purpose |
| :--- | :--- | :--- |
| `jmcc:staging:scan` | Query | Scan staging directories for newly added files. |
| `jmcc:organize:execute` | Transaction | Execute renaming and organization structures on disk. |
| `jmcc:move:start` | Queue Task | Begin moving organized folders to configured libraries. |
| `jmcc:library:list` | Query | Retrieve current items, expected counts, and sizes in library. |
| `jmcc:wishlist:add` | Mutation | Add media records with custom tags to the wishlist. |
| `jmcc:wishlist:health-check`| Event | Trigger a manual health scan comparing wishlist to libraries. |
| `jmcc:bugbox:report` | Log | Capture main-process exceptions and push them to the Diagnostics UI. |
