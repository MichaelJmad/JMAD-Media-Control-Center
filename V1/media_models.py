from __future__ import annotations
import os
import re
import json
import shutil
from typing import Dict, List, Optional, Tuple
from collections import Counter
from pathlib import Path

# -------------------------
# Configuration (moved from JMADMediaManager)
# -------------------------
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
CLEANUP_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt", ".mp3", ".json", ".xml"}
SETTINGS_FILE = "settings.json"
PATTERNS_FILE = "patterns.json"

DEFAULT_SETTINGS = {
    "directories": {
        "staging": "",
        "tv_shows": "",
        "movies": "",
        "anime": "",
        "trash": ""
    },
    "episode_pattern": "{series} - S{season:02d}E{episode:02d}{ext}",
    "movie_pattern": "{series}{ext}",
    "console_visible": True,
    "move_presets": [],
    "cleanup_ext_states": {
        "selected": {".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt"},
        "custom_exts_str": ""
    }
}

DEFAULT_FLUFF_PATTERNS = [
    r"\[.*?\]",
    r"\(.*?\)",
    r"\b(1080p|720p|2160p|4k|x264|x265|h264|h265|hevc|webrip|bluray|bdrip)\b",
    r"(s\d+)",
]

# -------------------------
# Data Models (moved from JMADMediaManager)
# -------------------------
class Episode:
    def __init__(self, path: str, season: Optional[int] = None, year: Optional[int] = None):
        self.path = path
        self.season = season
        self.series_name: str = ""
        self.parsed_episode_num: Optional[int] = None
        self.override_new_name: Optional[str] = None
        self.original_basename = os.path.basename(path)
        self.year = year

    def basename(self) -> str:
        return os.path.basename(self.path)

class Season:
    def __init__(self, key: int):
        self.key = key
        self.episodes: List[Episode] = []

class Series:
    def __init__(self, name: str):
        self.name = name
        self.seasons: Dict[int, Season] = {}
        self.unsorted: List[Episode] = []
        self.has_nonstandard_folders = False
        self.cover_art_path: Optional[str] = None
        self.year: Optional[int] = None
        self.is_processed: bool = False
        self.media_type: str = ""

    def get_all_episodes(self) -> List[Episode]:
        all_episodes = []
        for key in sorted(self.seasons.keys()):
            all_episodes.extend(self.seasons[key].episodes)
        all_episodes.extend(self.unsorted)
        return all_episodes

class BatchAction:
    def __init__(self, description: str, moves: List[Tuple[str, str]]):
        self.description = description
        self.moves = moves
        self.metadata_path: Optional[str] = None

class HistoryManager:
    def __init__(self, console_logger):
        self.history_log: List[Tuple[BatchAction, str]] = []
        self.current_pos: int = -1
        self.log = console_logger

    def push(self, action: BatchAction):
        if self.current_pos < len(self.history_log) - 1:
            self.history_log = self.history_log[: self.current_pos + 1]
        self.history_log.append((action, "new"))
        self.current_pos += 1
        self.log(f"Action: {action.description}")

    def can_undo(self) -> bool:
        return self.current_pos >= 0

    def can_redo(self) -> bool:
        return self.current_pos < len(self.history_log) - 1

    def _perform_moves(self, moves: List[Tuple[str, str]], is_undo: bool) -> List[str]:
        failures = []
        move_order = list(reversed(moves)) if is_undo else moves
        
        for src, dst in move_order:
            a, b = (dst, src) if is_undo else (src, dst)
            try:
                target_dir = Path(b).parent
                target_dir.mkdir(parents=True, exist_ok=True)

                if os.path.exists(a):
                    shutil.move(a, b)
                elif not is_undo:
                    failures.append(f"Source missing: {os.path.basename(a)}")
            except Exception as e:
                failures.append(f"Error moving {os.path.basename(a)}: {e}")
        return failures
        
    def execute_action(self, action: BatchAction, stop_at: Optional[str] = None) -> List[str]:
        original_src_dirs = {os.path.dirname(src) for src, _ in action.moves}
        
        failures = self._perform_moves(action.moves, is_undo=False)
        if not failures:
            self.push(action)
            for d in sorted(list(original_src_dirs), key=len, reverse=True):
                prune_empty_dirs(d, stop_at=stop_at)
        return failures

    def undo(self, stop_at: Optional[str] = None) -> Tuple[List[str], Optional[BatchAction]]:
        if not self.can_undo(): return [], None
        action, _ = self.history_log[self.current_pos]
        self.log(f"Undoing: {action.description}")

        dirs_to_prune = set()
        stop_at_path_abs = os.path.abspath(stop_at) if stop_at else None

        for _, dst in action.moves:
            path = os.path.abspath(dst)
            if os.path.isdir(path):
                dirs_to_prune.add(path)
            
            parent = os.path.dirname(path)
            while parent:
                if stop_at_path_abs and os.path.normcase(parent) == os.path.normcase(stop_at_path_abs):
                    break
                dirs_to_prune.add(parent)
                new_parent = os.path.dirname(parent)
                if new_parent == parent:
                    break
                parent = new_parent

        failures = self._perform_moves(action.moves, is_undo=True)
        
        if not failures:
            metadata_path = getattr(action, 'metadata_path', None)
            if metadata_path and os.path.exists(metadata_path):
                try:
                    dirs_to_prune.add(os.path.dirname(metadata_path))
                    os.remove(metadata_path)
                except Exception as e:
                    failures.append(f"Failed to clean up metadata file: {e}")

            for d in sorted(list(dirs_to_prune), key=len, reverse=True):
                prune_empty_dirs(d, stop_at=stop_at)
            
            self.history_log[self.current_pos] = (action, "undone")
            self.current_pos -= 1
        else:
            self.log(f"Undo failed for: {action.description}")

        return failures, action

    def redo(self, stop_at: Optional[str] = None) -> Tuple[List[str], Optional[BatchAction]]:
        if not self.can_redo(): return [], None
        self.current_pos += 1
        action, _ = self.history_log[self.current_pos]
        self.log(f"Redoing: {action.description}")
        
        original_src_dirs = {os.path.dirname(src) for src, _ in action.moves}

        failures = self._perform_moves(action.moves, is_undo=False)
        
        if not failures:
            for d in sorted(list(original_src_dirs), key=len, reverse=True):
                prune_empty_dirs(d, stop_at=stop_at)
            self.history_log[self.current_pos] = (action, "redone")
        else:
            self.log(f"Redo failed for: {action.description}")
            self.current_pos -= 1
        return failures, action
        
    def clear(self):
        self.history_log.clear()
        self.current_pos = -1
        self.log("History cleared.")

# -------------------------
# Utility Functions (moved from JMADMediaManager)
# -------------------------
def load_settings() -> dict:
    s = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s.update(json.load(f))
        except (json.JSONDecodeError, IOError): pass
    return s

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        # messagebox.showwarning("Settings Error", f"Failed to save settings: {e}") # Cannot use messagebox here
        print(f"Settings Error: Failed to save settings: {e}")

def load_patterns() -> List[str]:
    if not os.path.exists(PATTERNS_FILE):
        save_patterns(DEFAULT_FLUFF_PATTERNS)
        return DEFAULT_FLUFF_PATTERNS
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_FLUFF_PATTERNS

def save_patterns(patterns: List[str]):
    try:
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2)
    except Exception as e:
        # messagebox.showwarning("Patterns Error", f"Failed to save patterns: {e}") # Cannot use messagebox here
        print(f"Patterns Error: Failed to save patterns: {e}")


def prune_empty_dirs(path: str, stop_at: Optional[str] = None):
    try:
        path = os.path.abspath(path)
        stop_at_path = os.path.abspath(stop_at) if stop_at else None
        
        if not os.path.isdir(path):
            return

        while path and os.path.isdir(path) and not os.listdir(path):
            if stop_at_path and os.path.samefile(path, stop_at_path): break
            parent = os.path.dirname(path)
            if stop_at_path and os.path.samefile(path, stop_at_path):
                 break
            os.rmdir(path)
            path = parent
    except (OSError, PermissionError, FileNotFoundError): pass
    
def create_portable_dirs():
    for dirname in ["database", "logs", "themes"]:
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

# -------------------------
# Filename Parsing & Scanning (moved from JMADMediaManager)
# -------------------------
SEASON_HINT_RE = re.compile(r"(?:season[\s._-]*([0-9]{1,2}))|(?:\bS([0-9]{1,2})\b)", re.I)
EPISODE_PATTERNS = [
    re.compile(r"s00[exs](\d{1,3})", re.I), # s00e01, s00s01 for specials
    re.compile(r"s(\d{1,2})[ex](\d{1,3})", re.I),
    re.compile(r"(\d{1,2})x(\d{1,3})", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d)(\d{2})(?!\d)[._\-\s]?", re.I),
    re.compile(r"[._\-\s]e(\d{1,3})(?:[._\-\s]|$)", re.I),
    re.compile(r"episode[\s._-]*(\d+)", re.I),
    re.compile(r"ep[\s._-]*(\d+)", re.I),
    re.compile(r"part[\s._-]*(\d+)", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d{3})(?!\d)[._\-\s]?(?!\d)", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d{2})(?!\d)[._\-\s]?(?!\d)", re.I),
]

def suggest_series_name(original_name: str, fluff_patterns: List[str]) -> str:
    name = original_name
    for pat in fluff_patterns:
        try:
            name = re.sub(pat, "", name, flags=re.I)
        except re.error:
            # Ignore invalid patterns from user settings
            pass
    name = re.sub(r"[._]", " ", name)
    return " ".join(name.split()).strip()


def parse_episode_info(basename: str) -> Tuple[Optional[int], Optional[int]]:
    for i, pat in enumerate(EPISODE_PATTERNS):
        m = pat.search(basename)
        if m and m.groups():
            try:
                groups = m.groups()
                if i == 0:
                    return 0, int(groups[0])
                if i in [1, 2]:
                    return int(groups[0]), int(groups[1])
                if i == 3:
                    return int(groups[0]), int(groups[1])
                else:
                    return None, int(groups[-1])
            except (ValueError, IndexError):
                continue
    return None, None

YEAR_PATTERN = re.compile(r"[\(\[._\-\s](\d{4})[\)\]_\-\s]", re.I)

def parse_movie_info(basename: str) -> Optional[int]:
    m = YEAR_PATTERN.search(basename)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None

def predict_new_movie_filename(ep: Episode, settings: dict) -> Optional[str]:
    if ep.override_new_name: return ep.override_new_name
    if not ep.series_name: return None
    _, ext = os.path.splitext(ep.path)
    pattern = settings.get("movie_pattern", DEFAULT_SETTINGS["movie_pattern"])
    try:
        return pattern.format(series=ep.series_name, year=ep.year if ep.year is not None else "", ext=ext)
    except (KeyError, ValueError, TypeError):
        return None

def predict_new_filename(ep: Episode, settings: dict) -> Optional[str]:
    if ep.override_new_name: return ep.override_new_name
    if ep.season is None or ep.parsed_episode_num is None or not ep.series_name: return None
    _, ext = os.path.splitext(ep.path)
    pattern = settings.get("episode_pattern", DEFAULT_SETTINGS["episode_pattern"])
    try:
        return pattern.format(series=ep.series_name, season=int(ep.season), episode=int(ep.parsed_episode_num), ext=ext)
    except (KeyError, ValueError, TypeError):
        return None

def scan_media_roots(settings: dict) -> Dict[str, Series]:
    series_map: Dict[str, Series] = {}
    fluff_patterns = load_patterns() # Ensure fluff patterns are loaded

    print(f"DEBUG: Scanning directories: staging={staging_dir}, tv_shows={tv_shows_dir}, movies={movies_dir}, anime={anime_dir}")

    def _process_file(file_path: str, media_type_hint: Optional[str] = None):
        basename = os.path.basename(file_path)
        name_no_ext, ext = os.path.splitext(basename)

        if ext.lower() not in VIDEO_EXTS:
            return

        # Try to parse episode info first
        season, episode_num = parse_episode_info(name_no_ext)
        
        # Try to parse movie info (year)
        year = parse_movie_info(name_no_ext)

        # Determine series name
        series_name = suggest_series_name(name_no_ext, fluff_patterns)
        
        print(f"DEBUG: Processing file: {file_path}")
        print(f"  Basename: {basename}, Name No Ext: {name_no_ext}, Ext: {ext}")
        print(f"  Parsed: Season={season}, Episode={episode_num}, Year={year}")
        print(f"  Suggested Series Name: {series_name}")
        print(f"  Initial Media Type Hint: {media_type_hint}")

        # Handle movie files in Movies/MovieTitle subfolders (as per DEVELOPMENT.md)
        # This logic needs to be careful not to override valid series names
        parent_dir = os.path.basename(os.path.dirname(file_path))
        grandparent_dir = os.path.basename(os.path.dirname(os.path.dirname(file_path)))

        if grandparent_dir.lower() == "movies" and parent_dir != staging_dir: # Check if it's a movie subfolder
            series_name = parent_dir # Use subfolder name as movie title
            season = -1 # Hint for movie type
            media_type_hint = "Movie" # Explicitly set media type for this case
            print(f"  Detected Movie Subfolder: series_name={series_name}, season={season}, media_type_hint={media_type_hint}")

        # If it's a direct file in staging, and no episode/season, treat as potential movie
        if not season and not episode_num and media_type_hint is None:
            # Check if the file is directly in a configured movie directory
            if movies_dir and os.path.commonpath([file_path, movies_dir]) == movies_dir:
                media_type_hint = "Movie"
            elif anime_dir and os.path.commonpath([file_path, anime_dir]) == anime_dir:
                # If it's in anime dir, but no episode info, could be an anime movie
                media_type_hint = "Anime Movie"
            elif tv_shows_dir and os.path.commonpath([file_path, tv_shows_dir]) == tv_shows_dir:
                media_type_hint = "TV Series" # Assume TV series if in TV dir and no episode info (might be a single file series)
            else:
                # If in staging and no other hints, assume it's a movie if no episode info
                media_type_hint = "Movie" if not season and not episode_num else None
            print(f"  Inferred Media Type (no season/episode): {media_type_hint}")


        if series_name not in series_map:
            series_map[series_name] = Series(series_name)
            series_map[series_name].year = year # Assign year to series if available
            series_map[series_name]._inferred_media_type = media_type_hint # Store inferred type
            print(f"  New Series Created: {series_name}, Inferred Type: {media_type_hint}")

        series = series_map[series_name]
        
        # Update series media type if a stronger hint is provided
        if media_type_hint and not series.media_type:
            series.media_type = media_type_hint
            print(f"  Series {series_name} media_type set to {media_type_hint} (initial hint)")
        elif media_type_hint and series.media_type != media_type_hint:
            # If there's a conflict or a more specific type, prioritize
            if media_type_hint == "Anime Movie" and series.media_type == "Anime":
                series.media_type = "Anime Movie"
                print(f"  Series {series_name} media_type updated to Anime Movie (from Anime)")
            elif media_type_hint == "Movie" and series.media_type == "Anime Movie":
                pass # Keep Anime Movie
            elif media_type_hint == "TV Series" and series.media_type == "Anime":
                pass # Keep Anime
            else:
                series.media_type = media_type_hint # Default to new hint
                print(f"  Series {series_name} media_type updated to {media_type_hint} (new hint)")


        episode = Episode(file_path, season=season, year=year)
        episode.series_name = series_name
        episode.parsed_episode_num = episode_num

        if season is not None:
            if season not in series.seasons:
                series.seasons[season] = Season(season)
            series.seasons[season].episodes.append(episode)
            print(f"  Added episode {basename} to Season {season} of {series_name}")
        else:
            series.unsorted.append(episode)
            print(f"  Added episode {basename} to Unsorted of {series_name}")

    def _scan_directory_recursive(base_dir: str, media_type_hint: Optional[str] = None):
        if not base_dir or not os.path.isdir(base_dir):
            print(f"DEBUG: Skipping scan of invalid directory: {base_dir}")
            return

        print(f"DEBUG: Starting recursive scan of {base_dir} with hint {media_type_hint}")
        for root, dirs, files in os.walk(base_dir):
            # Check for non-standard folders (e.g., if a series folder contains unexpected subfolders)
            if root != base_dir and os.path.basename(root) not in ["Season 0", "Specials", "Movies"] and not re.match(r"Season \d+", os.path.basename(root), re.I):
                # If this is a subfolder of a series, mark the series as having non-standard folders
                # This logic needs to be refined to correctly identify the parent series
                pass # For now, we'll rely on the series object itself to track this

            for f in files:
                _process_file(os.path.join(root, f), media_type_hint)

    # Scan staging directory first, as it's the primary source
    _scan_directory_recursive(staging_dir)

    # Scan specific media type directories, potentially overriding or adding to staging findings
    _scan_directory_recursive(tv_shows_dir, "TV Series")
    _scan_directory_recursive(movies_dir, "Movie")
    _scan_directory_recursive(anime_dir, "Anime")

    # Post-processing to infer media type for series that are still 'Unknown'
    for sname, series in series_map.items():
        if not series.media_type:
            # If a series has season 0, it's likely a TV series or Anime with specials
            if 0 in series.seasons:
                series.media_type = "TV Series" # Default to TV Series
            elif series.year:
                series.media_type = "Movie" # If it has a year and no seasons, likely a movie
            else:
                series.media_type = "TV Series" # Default fallback
        print(f"DEBUG: Final Series Map Entry: {sname}, Media Type: {series.media_type}, Has Non-Standard Folders: {series.has_nonstandard_folders}")

        # Check for non-standard folders for each series
        series_path = os.path.join(staging_dir, series.name)
        if os.path.isdir(series_path):
            for root, dirs, files in os.walk(series_path):
                if root == series_path: # Only check direct subfolders of the series root
                    for d in dirs:
                        if d.lower() not in ["season 0", "specials", "movies"] and not re.match(r"season \d+", d, re.I):
                            series.has_nonstandard_folders = True
                            print(f"DEBUG: Series {sname} marked as having non-standard folders due to: {d}")
                            break
                if series.has_nonstandard_folders:
                    break


    print(f"DEBUG: scan_media_roots returning {len(series_map)} series.")
    return series_map

