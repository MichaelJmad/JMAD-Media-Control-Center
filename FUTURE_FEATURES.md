# Future Features Documentation

This document describes features that were implemented but deferred to future versions.

## Intelligent Media Scanner (v2+)

### Overview
An intelligent media scanning system that parses folder/file names, extracts metadata, and groups related media into organized series structures.

### Current Implementation
Located in: `infrastructure/services/media_scanner.py`

### Key Features

#### 1. Smart Series Grouping
The scanner intelligently groups multiple folders with similar names into a single series entry:

**Example:**
```
Staging folder contains:
- Blue Exorcist [720p][v2][HEVC 10bit x265][1080p] [Specials 1]
- Blue Exorcist [BD][1080p][Remastered] [Season 2]
- Blue Exorcist [BD][v2] [Specials 2]
- Blue Exorcist [Tenrai-Sensei][Remastered][HEVC 10bit x265][BD][Batch] s1

Tree displays:
└─ Blue Exorcist
   ├─ Season 0 (Specials)
   ├─ Season 1
   └─ Season 2
```

#### 2. Fluff Pattern Cleaning
Uses `FluffParser` to remove encoding tags, resolution markers, and other metadata from series names:
- Removes: `[720p]`, `[BD]`, `[v2]`, `[HEVC 10bit x265]`, etc.
- Extracts clean series name: "Blue Exorcist"

Default patterns (from config/settings.py):
```python
fluff_patterns = [
    r"\[.*?\]",           # [tags]
    r"\(.*?\)",           # (tags)
    r"\b(1080p|720p|2160p|4k|x264|x265|h264|h265|hevc|webrip|bluray|bdrip)\b",
    r"(s\d+)",            # Season markers
]
```

#### 3. Episode Parsing
Uses `EpisodeParser` to extract season/episode numbers from filenames:

Supported formats:
- `s01e05.mkv` → Season 1, Episode 5
- `S02E10.mkv` → Season 2, Episode 10
- `1x05.mkv` → Season 1, Episode 5
- `Blue Exorcist 005.mkv` → Episode 5 (season inferred)

#### 4. Movie Year Detection
Uses `MovieParser` to extract release years from movie folder names:
- `Inception (2010)` → year: 2010
- `The Matrix (1999)` → year: 1999

#### 5. Media Type Inference
Automatically detects media type based on:
- Organizational folders: "Anime", "Movies", "TV Series", "TV Shows"
- Folder name patterns (presence of year, episode numbers, etc.)
- File naming conventions

#### 6. Recursive Directory Walking
Recursively scans all subdirectories to find video files:
- Searches for files with video extensions (from `config/constants.py`)
- Handles nested folder structures
- Gracefully handles permission errors

### Domain Models Created

The intelligent scanner creates rich domain models:

**Series:**
- `name`: Original series name with tags
- `clean_name`: Cleaned series name (no tags)
- `media_type`: ANIME, MOVIE, TV_SERIES
- `root_path`: Base directory path
- `seasons`: Collection of Season objects

**Episode:**
- `path`: Full file path
- `episode_number`: EpisodeNumber value object (season, episode)
- `title`: Episode title (if parseable)
- `year`: Release year (for movies)
- `original_basename`: Original filename

### Technical Details

**Class:** `MediaScanner`
**Location:** `infrastructure/services/media_scanner.py`

**Dependencies:**
- `FluffParser` - Cleans series names
- `EpisodeParser` - Extracts episode numbers
- `MovieParser` - Extracts movie years
- Domain models: `Series`, `Episode`, `Movie`
- Value objects: `MediaType`, `EpisodeNumber`, `FilePath`

**Key Methods:**
- `scan_directory(directory)` - Main entry point, returns Dict[str, Series]
- `_walk_directory(directory)` - Recursive file walking
- `_process_file(file_path, ...)` - Process individual video file
- `_extract_series_name(file_path, ...)` - Determine series name from path
- `_infer_media_type(file_path, ...)` - Determine media type
- `detect_nonstandard_structure(series)` - Detect unusual folder layouts

### Use Cases

**ScanMediaUseCase** (application/use_cases/scan_media.py):
- Uses MediaScanner to scan staging directory
- Detects non-standard structures
- Returns ScanResult DTO with organized series data

### Why Deferred to v2+

While powerful, this intelligent processing adds complexity that's not needed for V1:
- V1 focuses on simple folder-level operations
- Users may want to see exact folder names before organizing
- Parsing logic requires tuning for different naming conventions
- Grouping behavior should be configurable

### Recommendation for v2

When implementing in v2:
1. Make intelligent scanning **optional** (toggle in settings)
2. Add **preview mode** - show what grouping will occur before applying
3. Allow **manual override** - user can adjust grouping decisions
4. Add **pattern customization** - users define their own fluff patterns
5. Support **undo** - if grouping is wrong, allow ungrouping
6. Add **conflict resolution** - handle series with identical clean names

### Testing Data

Test data in `/staging/` directory demonstrates various scenarios:
- Multiple folders for same series (Blue Exorcist, My Hero Academia, etc.)
- Various tagging patterns ([720p], [BD], [Dual Audio], etc.)
- Different season markers (S00, s1, [Season 2], [Specials 1])
- Movie formats with years
- Mixed naming conventions

---

## Other Deferred Features

(Add other future features here as they're identified)
