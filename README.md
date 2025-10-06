# JMAD Media Tool
This tool is your one stop shop for managing all of your media needs this is a placeholder concept and may be subject to change.
JMAD Media Tool: High-Level Plan & Functional Specification
This document outlines the complete functional requirements and technical scope for the JMAD Media Tool (Version 1). The tool provides an intelligent, state-aware, and highly customizable solution for organizing and standardizing media files before deployment to a live media server (e.g., Plex, Jellyfin). The core philosophy emphasizes absolute data fidelity and user confidence before any file system changes are executed.

1. Core Workflow & Application Philosophy
The application utilizes a State Management philosophy, ensuring media titles progress through user-controlled states. This guarantees that files are fully verified, renamed, and metadata-rich before deployment, preventing common library errors.

Standardized Status Protocol (UI Color & Icon)
The UI uses standardized color indicators and icons, which are fully customizable via Theme Profiles (Section 5.2), to communicate the necessary next action.

Icon/Color

Status Name

Definition

User Action Required

⚪ Gray

Unorganized

Media is raw, unverified, or unrecognized. Requires initial title mapping.

Initiate Organize Dialog to map raw files to a standard title.

🔵 Blue

Processing/Pending

Media is named and structured, but full metadata (NFO/Artwork) is not finalized.

Initiate Metadata Fetch and Finalize content.

🟢 Green

Ready to Move

Media has complete, verified metadata and structure. Clean and ready for deployment.

Initiate Move to Live Library.

🟡 Yellow

Warning (Non-Critical)

Appears alongside the color status. Indicates minor issues (e.g., Uncategorized files, quality deficiency).

Manual review is optional.

🔴 Red

Critical Error

Overrides all colors. Signifies a core process failure (e.g., file move failed, permissions revoked).

Immediate resolution required.

2. Main Application Components (Tabs)
The application uses a multi-tab interface to manage the workflow:

Staging Directory: Primary workspace for organizing and state transitions.

Live Libraries (Catalog): Read-only view of deployed media for diagnostics.

Tools: Access to advanced utilities (Cleanup, Diagnostics, Patterns).

Settings: Configuration hub for directories, naming, metadata, and appearance.

Organization Dialog
The Organization Dialog is the main interactive tool for processing a single media title. It includes a Right Panel Preview to provide real-time visualization of the resulting file and folder structure before file system changes are committed.

3. Detailed Feature Breakdown
3.1 Directory & File Handling
Feature

Description

Directory Settings

Defines the physical locations: Staging Directory (input), Live Libraries (targets), Uncategorized Folder, and Quarantine Folder.

Fluff Removal

User-defined Regex patterns strip non-essential text (e.g., release tags) to normalize file names, aiding accurate metadata scraping.

Directory Monitor

A persistent service actively monitors Staging for new files, flagging them immediately as Unorganized (Gray) after initial fluff removal.

Uncategorized Folder

A holding area for files or folders that the user is unsure how to process (e.g., partial downloads, misidentified files), awaiting manual review.

Quarantine Folder

A dedicated holding location for files or folders that have been marked for deletion or removal (e.g., duplicates). Items here require a final user action (Purge or Restore).

Patterns/Naming Templates

Fully customizable templates using variables (e.g., {title}, S{season}, {resolution}) to create clean, server-compatible file and folder outputs.

3.2 Metadata & Server Integration
Feature

Description

Metadata Scraper

Integrates with APIs (TMDB, TVDB) to fetch accurate titles, release dates, episode summaries, and key artwork.

NFO File Generation

Generates server-compatible NFO files containing all collected metadata, custom sorting keys, and anchoring data for permanent record.

Artwork Management

Downloads, resizes, and saves all required artwork (posters, backgrounds, episode thumbnails) using standard server naming conventions.

Subtitle/Trailer/Theme Management

Integrated fetching, renaming, and organization for auxiliary media (subtitles, trailers, and series theme MP3s).

Default Language Preference

User settings for Preferred Audio/Subtitle Language guide scraping efforts and file-level flagging.

4. Advanced Automation & Safety
4.1 Batch Processing and Merging
The Batch system groups and merges related sources, minimizing repetitive actions while confirming critical decisions.

Feature

Logic

State Handling

Batch Organize

Selects multiple items and attempts to Assume/Merge them into single series groups (e.g., S01 and S02 files → Series Title).



Raw/Clean Title Toggle

During confirmation, allows toggling the display between the raw file name and the simplified, fluff-removed title.



State-Aware Merge Offer

If merging a Red (Unorganized) source into a Green (Ready) target, a prompt details the required pre-merge processing (renaming/structuring) that will occur before the files are physically merged.



Raw File Processing

Function to process single, orphaned files not in series folders. User searches for the correct title, and the file is then wrapped in the proper folder structure.



4.2 Media Title Anchoring (Watch Order & Collections)
Controls the viewing order for complex franchises, placing movies and specials within the episodic timeline.

Feature

Logic

Server Awareness

Default Watch Order

Initial setting defines the preferred series layout: Canonical, Chronological, or Release Order.



Anchoring Automation

Uses external metadata (e.g., TVDB lists) to automatically place movies/specials into the timeline using NFO tags.

Server Feature Gating: Feature is grayed out if the target server lacks NFO tag support for anchoring.

Auto-Flagging

If a movie/special is detected but reliable anchor data is missing, the media title receives a Warning Flag (🟡), requiring manual placement.



4.3 Diagnostics and Catalog Management
Feature

Description

Location

Media Inspector Tool

Displays deep file analysis (Codec, Resolution, Bitrate) for quality control.

Tools Menu

Diagnostic Flagging

Compares media quality against user-defined Target Standards (e.g., minimum 1080p). Fails/Flags titles that require an upgrade.

General/Diagnostics Settings

Media Details Dialog

Unified dialog for deployed media to view live metadata and anchoring status.

Catalog Tab

Watch Directory

A background service monitors a separate download-complete folder, automatically moving new items to the Staging Path, flagged Unorganized (Gray).

Directories Settings

4.4 Get List Management (Tracking Foundation)
This module is the foundation for future automated acquisition, providing a persistent, searchable list of desired media.

Feature

Description

Location

Get List UI

A dedicated view to manually add, track, and update the acquisition status of desired Movies and TV Series.

Tools Menu

Manual Tracking

Allows users to manually input media titles, capturing the correct title ID and release year from integrated databases.

Get List UI

Import/Export

Simple mechanism to import/export the list data (e.g., JSON or plain text).

Get List UI

Status Update

Entries can be manually updated (e.g., "Wanted," "Downloading," "Acquired").

Get List UI

5. Final Operational Definitions
5.1 File Operation Safety & Error Handling
Critical file operations require robust safety checks and transactional methods to prevent data loss.

Pre-Operation Check: Verify read/write/delete permissions before starting any major operation.

Non-Critical Failure: Log failure, continue the batch, and assign a Warning Flag (🟡) to the affected title.

Critical Failure: Attempt a transactional rollback. Assign the Critical Error State (🔴), requiring immediate user intervention.

5.2 Theme and Status Profiles (Appearance)
All visual elements are managed by savable Profiles in the Appearance Settings Tab. Light modes use muted grays to reduce eye strain.

Status Visuals (Consistent Across All Themes)
Status states use fixed color logic (Gray, Blue, Green, Yellow, Red) but allow customization of the hex code and accompanying emoji/icon.

Default Theme Profiles
Theme Name

Mode

Primary Background

Accent Color

Rationale

Jmad

Dark (Default)

Deep Charcoal Gray

Dark Greenish Gray

Primary, low-impact default theme.

Jmad

Light

Muted Light Gray

Pale Greenish Gray

Soft background for reduced eye strain.

Mike

Dark

Deep Charcoal Gray

Bright Pink

Personalized high-contrast theme.

Mike

Light

Muted Light Gray

Soft Pastel Pink

Balanced contrast for light-mode usage.

Kerberos

Dark

Deep Charcoal Gray

Nuclear Warning Orange

Aggressive accent color for immediate control identification.

Kerberos

Light

Muted Light Gray

Soft Pale Orange

Softened warning palette for light-mode.

6. Future Development / Low Priority Backlog
These items are out of scope for Version 1: Audio Language Sampling, Post-Move Server Webhook, Automated Media Acquisition Integration, and User Profiles.