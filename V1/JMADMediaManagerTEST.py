#!/usr/bin/env python3
"""
JMAD Media Tool
A robust TV series and media renamer application.
Version: 6.8 (Advanced Organize Dialog)
"""
from __future__ import annotations
import os
import re
import json
import shutil
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, scrolledtext, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from typing import Dict, List, Optional, Tuple
from collections import Counter
from pathlib import Path

# -------------------------
# Configuration
# -------------------------
CURRENT_VERSION = "6.8"
UPDATE_CHECK_URL = "https://api.github.com/repos/yourusername/jmad-media-tool/releases/latest"

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
CLEANUP_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt", ".mp3", ".json", ".xml"}
SETTINGS_FILE = "settings.json"
PATTERNS_FILE = "patterns.json"

DEFAULT_SETTINGS = {
    "directories": {
        "staging": "",
        "tv_shows": "",
        "movies": "",
        "anime": ""
    },
    "episode_pattern": "{series} - S{season:02d}E{episode:02d}{ext}",
    "movie_pattern": "{series} ({year}){ext}",
    "console_visible": True,
    "move_presets": []
}

DEFAULT_FLUFF_PATTERNS = [
    r"\[.*?\]",
    r"\(.*?\)",
    r"\b(1080p|720p|2160p|4k|x264|x265|h264|h265|hevc|webrip|bluray|bdrip)\b",
    r"(s\d+)",
]

METADATA_FILENAME = ".jmad_info.json"
MEDIA_TYPES = ["TV Series", "Anime", "Movie", "Anime Movie"]

# -------------------------
# Data Models
# -------------------------
class Episode:
    def __init__(self, path: str, season: Optional[int] = None):
        self.path = path
        self.season = season
        self.series_name: str = ""
        self.parsed_episode_num: Optional[int] = None
        self.override_new_name: Optional[str] = None

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
        self.is_processed = False
        self.media_type = "TV Series"
        self.cover_art_path: Optional[str] = None
        self.year: Optional[int] = None

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
# Utility Functions
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
        messagebox.showwarning("Settings Error", f"Failed to save settings: {e}")

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
        messagebox.showwarning("Patterns Error", f"Failed to save patterns: {e}")


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
# Filename Parsing & Scanning
# -------------------------
SEASON_HINT_RE = re.compile(r"(?:season[\s._-]*([0-9]{1,2}))|(?:\bS([0-9]{1,2})\b)", re.I)
EPISODE_PATTERNS = [
    re.compile(r"s(\d{1,2})[ex](\d{1,3})", re.I),
    re.compile(r"(\d{1,2})x(\d{1,3})", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d)(\d{2})(?!\d)[._\-\s]?", re.I),
    re.compile(r"[._\-\s]e(\d{1,3})(?:[._\-\s]|$)", re.I),
    re.compile(r"episode[\s._-]*(\d+)", re.I),
    re.compile(r"ep[\s._-]*(\d+)", re.I),
    re.compile(r"part[\s._-]*(\d+)", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d{3})(?!\d)[._\-\s]?", re.I),
    re.compile(r"[._\-\s](?<!\d)(\d{2})(?!\d)[._\-\s]?", re.I),
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
                if i in [0, 1]:
                    return int(groups[0]), int(groups[1])
                if i == 2:
                    return int(groups[0]), int(groups[1])
                else:
                    return None, int(groups[-1])
            except (ValueError, IndexError):
                continue
    return None, None

def predict_new_filename(ep: Episode, settings: dict) -> Optional[str]:
    if ep.override_new_name: return ep.override_new_name
    if ep.season is None or ep.parsed_episode_num is None or not ep.series_name: return None
    _, ext = os.path.splitext(ep.path)
    pattern = settings.get("episode_pattern", DEFAULT_SETTINGS["episode_pattern"])
    try:
        return pattern.format(series=ep.series_name, season=int(ep.season), episode=int(ep.parsed_episode_num), ext=ext)
    except (KeyError, ValueError, TypeError):
        return f"InvalidPattern{ext}"

def scan_tv_root(tv_root: str) -> Dict[str, Series]:
    series_map: Dict[str, Series] = {}
    if not tv_root or not os.path.isdir(tv_root): return series_map
    
    try:
        for entry in os.scandir(tv_root):
            if not entry.is_dir(): continue
            series = Series(entry.name)
            
            metadata_path = os.path.join(entry.path, METADATA_FILENAME)
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        series.is_processed = metadata.get('is_processed', False)
                        series.media_type = metadata.get('media_type', 'TV Series')
                except (json.JSONDecodeError, IOError): pass

            all_episodes_temp = []
            series_root_path_abs = os.path.abspath(entry.path)
            
            for root, _, files in os.walk(series_root_path_abs):
                season_hint = None
                if not os.path.samefile(root, series_root_path_abs):
                    folder_name = os.path.basename(root)
                    m = SEASON_HINT_RE.search(folder_name)
                    if m:
                        groups = m.groups()
                        if groups[0]: season_hint = int(groups[0])
                        elif groups[1]: season_hint = int(groups[1])
                    elif re.search(r"specials", folder_name, re.I):
                        season_hint = 0
                    elif re.search(r"movies", folder_name, re.I):
                        season_hint = -1 # Special key for movies
                
                for f in files:
                    if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
                        ep = Episode(os.path.join(root, f), season=season_hint)
                        ep.series_name = series.name
                        _, parsed_episode = parse_episode_info(f)
                        ep.parsed_episode_num = parsed_episode
                        all_episodes_temp.append(ep)

            if not all_episodes_temp:
                continue

            has_season_folders = False
            is_disorganized = False

            for ep in all_episodes_temp:
                if ep.season is not None:
                    if ep.season >= 0: # Seasons and Specials
                        has_season_folders = True
                    series.seasons.setdefault(ep.season, Season(ep.season)).episodes.append(ep)
                else:
                    series.unsorted.append(ep)
            
            if series.unsorted:
                if has_season_folders:
                    is_disorganized = True
                else:
                    for ep in series.unsorted:
                        ep_dir_abs = os.path.abspath(os.path.dirname(ep.path))
                        if not os.path.samefile(ep_dir_abs, series_root_path_abs):
                            is_disorganized = True
                            break
            
            if series.media_type == "Movie" and is_disorganized:
                is_disorganized = False # Movies with subfolders are fine

            series.has_nonstandard_folders = is_disorganized
            series_map[entry.name] = series

        for s in series_map.values():
            for sec in s.seasons.values():
                sec.episodes.sort(key=lambda e: (e.parsed_episode_num or float('inf'), e.path.lower()))
            s.unsorted.sort(key=lambda e: e.path.lower())
    except Exception as e:
        print(f"Error scanning TV root: {e}")
    
    return series_map


# -------------------------
# UI Panels
# -------------------------
class InfoPreviewPanel(tb.Frame):
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        tb.Label(self, text="Preview", bootstyle="inverse-primary", padding=5, anchor="center").grid(row=0, column=0, sticky="ew")

        content_frame = tb.Frame(self, padding=10)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(1, weight=1)

        self.cover_label = tb.Label(content_frame, text="Cover Art Placeholder", anchor="center")
        self.cover_label.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        
        meta_frame = tb.Frame(content_frame)
        meta_frame.grid(row=0, column=1, sticky="new")
        meta_frame.columnconfigure(0, weight=1)

        self.title_label = tb.Label(meta_frame, text="Select a Series", font=("Helvetica", 16, "bold"))
        self.title_label.pack(fill="x", pady=(0,5))
        
        self.status_label = tb.Label(meta_frame, text="Status: N/A")
        self.status_label.pack(fill="x", pady=2)

        self.episodes_label = tb.Label(meta_frame, text="Episodes/Movies: N/A")
        self.episodes_label.pack(fill="x", pady=2)
    
    def update_info(self, series: Optional[Series]):
        if not series:
            self.title_label.config(text="Select a Series")
            self.status_label.config(text="Status: N/A")
            self.episodes_label.config(text="Episodes/Movies: N/A")
            return

        self.title_label.config(text=series.name)
        status = "Processed" if series.is_processed else "Not Processed"
        self.status_label.config(text=f"Status: {status} ({series.media_type})")
        
        episode_count = len(series.get_all_episodes())
        self.episodes_label.config(text=f"Files Found: {episode_count}")

class ConsolePanel(tb.Frame):
    def __init__(self, parent, app_controller, initial_content=""):
        super().__init__(parent)
        self.app = app_controller
        self.docked = True
        self.undocked_window = None
        self.original_parent = parent
        self._content_buffer = initial_content

        self._build_ui()
        self.last_geometry = "600x400"
        
        if self._content_buffer:
            self._refresh_display()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.header = tb.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        tb.Label(self.header, text="Console", bootstyle="inverse-primary", padding=5).grid(row=0, column=0, sticky="ew")
        
        self.hide_btn = tb.Button(self.header, text="Hide", command=self.app.toggle_console, bootstyle="toolbutton")
        self.hide_btn.grid(row=0, column=1, padx=2)

        self.text_frame = tb.Frame(self)
        self.text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)

        self.scrolled_text = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD, state="disabled")
        self.scrolled_text.grid(row=0, column=0, sticky="nsew")
        
        self.footer = tb.Frame(self)
        self.footer.grid(row=2, column=0, sticky="ew", padx=5, pady=(0,5))
        
        self.dock_btn = tb.Button(self.footer, text="Undock", command=self.toggle_dock, bootstyle="outline-secondary")
        self.dock_btn.pack(side="left")
        
        tb.Button(self.footer, text="Clear", command=self.clear, bootstyle="outline-danger").pack(side="right")

    def log(self, message):
        self._content_buffer += message + "\n"
        self.scrolled_text.config(state="normal")
        self.scrolled_text.insert(tk.END, message + "\n")
        self.scrolled_text.config(state="disabled")
        self.scrolled_text.see(tk.END)

    def clear(self):
        self._content_buffer = ""
        self.scrolled_text.config(state="normal")
        self.scrolled_text.delete(1.0, tk.END)
        self.scrolled_text.config(state="disabled")
        self.log("Console cleared.")
    
    def _refresh_display(self):
        self.scrolled_text.config(state="normal")
        self.scrolled_text.delete(1.0, tk.END)
        self.scrolled_text.insert(1.0, self._content_buffer)
        self.scrolled_text.config(state="disabled")
        self.scrolled_text.see(tk.END)
    
    def get_content(self):
        return self._content_buffer
    
    def toggle_dock(self):
        if self.docked:
            content = self.get_content()
            self.undocked_window = tk.Toplevel(self.app)
            self.undocked_window.title("JMAD Media Tool - Console")
            self.undocked_window.geometry("600x400")
            self.undocked_window.configure(bg=self.app.style.colors.bg)
            
            new_console = ConsolePanel(self.undocked_window, self.app, content)
            new_console.pack(fill="both", expand=True, padx=5, pady=5)
            new_console.docked = False
            new_console.dock_btn.config(text="Dock")
            new_console.undocked_window = self.undocked_window
            new_console.original_parent = self.original_parent
            
            self.app.console = new_console
            self.destroy()
            self.undocked_window.protocol("WM_DELETE_WINDOW", new_console.toggle_dock)
            self.app._update_layout_after_console_change()
        else:
            if self.undocked_window:
                content = self.get_content()
                new_console = ConsolePanel(self.original_parent, self.app, content)
                new_console.pack(fill="both", expand=True)
                new_console.docked = True
                new_console.dock_btn.config(text="Undock")
                
                self.app.console = new_console
                self.undocked_window.destroy()
                self.app._update_layout_after_console_change()              
# -------------------------
# Main Application Window
# -------------------------
class JMADMediaTool(tk.Tk):
    def __init__(self, settings: dict, patterns: List[str]):
        super().__init__()
        self.style = tb.Style(theme="darkly")
        self.title("JMAD Media Tool")
        self.geometry("1400x800")

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        icon_path = os.path.join(base_path, "JMADMMT.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Could not set icon: {e}")

        self.settings = settings
        self.fluff_patterns = patterns
        self.series_map: Dict[str, Series] = {}
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._build_ui()
        self.history = HistoryManager(self.console.log)
        self.after(100, self.post_init_tasks)

    def post_init_tasks(self):
        create_portable_dirs()
        self.scan_root()
        self.check_for_updates_simulated()
        self._update_layout_after_console_change()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        toolbar = tb.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        
        tb.Button(toolbar, text="Scan", command=self.scan_root, bootstyle="outline-success").pack(side="left", padx=4)
        tb.Button(toolbar, text="Settings", command=self.open_settings, bootstyle="outline-light").pack(side="left", padx=4)
        
        self.tools_menubutton = tb.Menubutton(toolbar, text="Tools", bootstyle="outline-info")
        self.tools_menubutton.pack(side="left", padx=4)
        self._build_tools_menu()
        
        tb.Button(toolbar, text="Catalog", state="disabled").pack(side="left", padx=4)

        tb.Button(toolbar, text="Redo", command=self.redo_action, bootstyle="outline-info").pack(side="right", padx=4)
        tb.Button(toolbar, text="Undo", command=self.undo_action, bootstyle="outline-warning").pack(side="right")
        
        main_paned = tb.PanedWindow(self, orient="horizontal", bootstyle="primary")
        main_paned.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        
        left_frame = tb.Frame(main_paned)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        header_frame = tb.Frame(left_frame)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)
        tb.Label(header_frame, text="Media Tree", bootstyle="inverse-primary", padding=5).grid(row=0, column=0, sticky="ew")
        tb.Label(header_frame, text="[Processed] [Type]", bootstyle="inverse-primary", padding=5, anchor="e").grid(row=0, column=1, sticky="ew")

        tree_container = tb.Frame(left_frame)
        tree_container.grid(row=1, column=0, sticky='nsew', padx=6, pady=6)
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        self.series_tree = tb.Treeview(tree_container, selectmode="extended", bootstyle="primary", columns=("processed", "type"))
        self.series_tree.grid(row=0, column=0, sticky="nsew")
        self.series_tree.heading("#0", text="Series Name")
        self.series_tree.heading("processed", text="Processed")
        self.series_tree.heading("type", text="Type")
        self.series_tree.column("#0", stretch=True, width=250)
        self.series_tree.column("processed", width=80, anchor="center")
        self.series_tree.column("type", width=100, anchor="w")

        self.series_tree.tag_configure('nonstandard', foreground='orange')
        vsb_left = tb.Scrollbar(tree_container, orient="vertical", command=self.series_tree.yview, bootstyle="primary-round")
        vsb_left.grid(row=0, column=1, sticky="ns")
        self.series_tree.configure(yscrollcommand=vsb_left.set)
        self.series_tree.bind("<<TreeviewSelect>>", self.on_series_selection)
        self.series_tree.bind("<Button-3>", self.on_series_right_click)
        self.series_tree.bind("<Control-a>", self._select_all)
        main_paned.add(left_frame, weight=2)
        
        self.right_frame = tb.Frame(main_paned)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        
        self.right_paned = tb.PanedWindow(self.right_frame, orient="vertical", bootstyle="primary")
        self.right_paned.grid(row=0, column=0, sticky="nsew")
        
        self.info_container = tb.Frame(self.right_paned)
        self.console_container = tb.Frame(self.right_paned)
        
        self.info_panel = InfoPreviewPanel(self.info_container, self)
        self.info_panel.pack(fill="both", expand=True)
        
        self.console = ConsolePanel(self.console_container, self)
        self.console.pack(fill="both", expand=True)
        
        self.right_paned.add(self.info_container, weight=3)
        self.right_paned.add(self.console_container, weight=1)
        
        main_paned.add(self.right_frame, weight=3)
        
    def _update_layout_after_console_change(self):
        current_panes = self.right_paned.panes()
        is_console_pane_visible = str(self.console_container) in current_panes
        should_be_visible = self.console.docked and self.settings.get("console_visible", True)

        if should_be_visible and not is_console_pane_visible:
            self.right_paned.add(self.console_container, weight=1)
        elif not should_be_visible and is_console_pane_visible:
            self.right_paned.remove(self.console_container)
        
        self.update_idletasks()
        
    def _build_tools_menu(self):
        tools_menu = tk.Menu(self.tools_menubutton, tearoff=0)
        tools_menu.add_command(label="Clean Files...", command=self.clean_files_tool)
        
        move_menu = tk.Menu(tools_menu, tearoff=0)
        self._populate_move_menu(move_menu)
        tools_menu.add_cascade(label="Move Selected To...", menu=move_menu)
        
        tools_menu.add_separator()
        console_text = "Show Console" if not self.settings.get("console_visible", True) else "Hide Console"
        tools_menu.add_command(label=console_text, command=self.toggle_console)

        self.tools_menubutton["menu"] = tools_menu

    def _populate_move_menu(self, menu):
        menu.delete(0, "end")
        presets = self.settings.get("move_presets", [])
        if presets:
            for preset in presets:
                menu.add_command(label=preset, command=lambda p=preset: self.move_series_tool(destination=p))
            menu.add_separator()
        
        menu.add_command(label="Choose Location...", command=self.move_series_tool)

    def scan_root(self):
        staging_dir = self.settings.get("directories", {}).get("staging")
        if not staging_dir or not os.path.isdir(staging_dir):
            if not self.winfo_viewable(): return
            messagebox.showwarning("Staging Directory Not Set", "Please configure a valid Staging directory in Settings.")
            return
        self.log(f"Scanning directory: {staging_dir}")
        self.series_map = scan_tv_root(staging_dir)
        self.populate_series_tree()
        self.info_panel.update_info(None)
        self.log(f"Scan complete. Found {len(self.series_map)} series.")

    def populate_series_tree(self):
        self.series_tree.delete(*self.series_tree.get_children())
        for sname in sorted(self.series_map.keys(), key=str.lower):
            series = self.series_map[sname]
            if not series.get_all_episodes(): continue
            tags = ('nonstandard',) if series.has_nonstandard_folders else ()
            processed_text = "✅" if series.is_processed else "☐"
            top_id = self.series_tree.insert("", "end", text=sname, open=False, tags=tags, values=(processed_text, series.media_type))
            
            season_keys = sorted(series.seasons.keys())
            if season_keys:
                for season_idx in season_keys:
                    if season_idx == -1: label = "Movies"
                    elif season_idx == 0: label = "Specials"
                    else: label = f"Season {season_idx:02d}"
                    self.series_tree.insert(top_id, "end", text=label)

            if series.unsorted:
                self.series_tree.insert(top_id, "end", text="Unsorted")

    def on_series_selection(self, event=None):
        selection = self.series_tree.selection()
        if not selection:
            self.info_panel.update_info(None)
            return

        item_id = selection[0]
        parent_id = self.series_tree.parent(item_id)
        series_name = self.series_tree.item(parent_id or item_id, "text")
        series = self.series_map.get(series_name)
        
        self.info_panel.update_info(series)

    def on_series_right_click(self, event):
        item_id = self.series_tree.identify_row(event.y)
        if not item_id: return
        current_selection = self.series_tree.selection()
        if item_id not in current_selection:
            self.series_tree.selection_set((item_id,))
            current_selection = (item_id,)
        menu = tb.Menu(self, tearoff=0)
        top_level_items = [item for item in current_selection if not self.series_tree.parent(item)]
        
        if top_level_items:
             menu.add_command(label="Organize / Combine Series...", command=lambda: self.open_organize_dialog(top_level_items))
             
             type_menu = tb.Menu(menu, tearoff=0)
             for t in MEDIA_TYPES:
                 type_menu.add_command(label=t, command=lambda media_type=t: self.set_series_type(top_level_items, media_type))
             menu.add_cascade(label="Set Type As", menu=type_menu)
             
             menu.add_separator()
             console_text = "Show Console" if not self.settings.get("console_visible", True) else "Hide Console"
             menu.add_command(label=console_text, command=self.toggle_console)
             menu.add_separator()
             
             tools_menu = tk.Menu(menu, tearoff=0)
             tools_menu.add_command(label="Clean Files...", command=self.clean_files_tool)
             
             move_menu = tk.Menu(tools_menu, tearoff=0)
             self._populate_move_menu(move_menu)
             tools_menu.add_cascade(label="Move Selected To...", menu=move_menu)

             menu.add_cascade(label="Tools", menu=tools_menu)

        if menu.index('end') is not None:
            menu.post(event.x_root, event.y_root)
            
    def set_series_type(self, item_ids: List[str], media_type: str):
        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root: return

        series_to_process = [self.series_map[self.series_tree.item(item_id, "text")] for item_id in item_ids]

        if media_type == "Anime Movie":
            all_series_names = sorted([s.name for s in self.series_map.values() if s.media_type in ["Anime", "TV Series"]])
            AssociateMovieDialog(self, series_to_process, all_series_names)
            return

        for series in series_to_process:
            series.media_type = media_type
            series.is_processed = True
            metadata = {"is_processed": True, "media_type": media_type}
            try:
                series_path = os.path.join(tv_root, series.name)
                if not os.path.isdir(series_path): os.makedirs(series_path, exist_ok=True)
                with open(os.path.join(series_path, METADATA_FILENAME), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                self.log(f"Set type for '{series.name}' to '{media_type}'")
            except Exception as e:
                self.log(f"Error setting type for '{series.name}': {e}")
        
        self.scan_root()

    def undo_action(self):
        if not self.history.can_undo(): return
        failures, _ = self.history.undo(stop_at=self.settings.get("directories", {}).get("staging"))
        if failures: messagebox.showwarning("Undo Failed", "\n".join(failures))
        self.scan_root()

    def redo_action(self):
        if not self.history.can_redo(): return
        failures, _ = self.history.redo(stop_at=self.settings.get("directories", {}).get("staging"))
        if failures: messagebox.showwarning("Redo Failed", "\n".join(failures))
        self.scan_root()

    def clear_history(self):
        if messagebox.askyesno("Clear History", "This will clear all undo/redo history. Continue?"):
            self.history.clear()

    def log(self, message):
        self.console.log(message)

    def open_settings(self):
        SettingsDialog(self)

    def open_organize_dialog(self, item_ids: List[str]):
        series_to_organize = [self.series_map[self.series_tree.item(item_id, "text")] for item_id in item_ids]
        if series_to_organize:
            OrganizeDialog(self, series_to_organize)

    def clean_files_tool(self):
        selected_ids = [item for item in self.series_tree.selection() if not self.series_tree.parent(item)]
        if not selected_ids:
            messagebox.showwarning("No Series Selected", "Please select one or more top-level series folders to clean.")
            return

        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root: return

        files_to_delete = []
        for item_id in selected_ids:
            series_name = self.series_tree.item(item_id, "text")
            series_path = os.path.join(tv_root, series_name)
            for root, _, files in os.walk(series_path):
                for f in files:
                    if os.path.splitext(f)[1].lower() in CLEANUP_EXTS:
                        files_to_delete.append(os.path.join(root, f))
        
        if not files_to_delete:
            messagebox.showinfo("Clean Files", "No files to clean in the selected series.")
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Found {len(files_to_delete)} files to clean (images, nfo, txt, etc.).\n\n"
            "This action is PERMANENT and CANNOT be undone.\n\n"
            "Are you sure you want to delete these files?"
        )

        if confirm:
            deleted_count = 0
            failed_count = 0
            for f_path in files_to_delete:
                try:
                    os.remove(f_path)
                    deleted_count += 1
                except OSError:
                    failed_count += 1
            
            self.log(f"Cleaned {deleted_count} files. Failed on {failed_count}.")
            messagebox.showinfo("Cleanup Complete", f"Successfully deleted {deleted_count} files.\nFailed to delete {failed_count} files.")
            self.scan_root()

    def move_series_tool(self, destination: Optional[str] = None):
        selected_ids = [item for item in self.series_tree.selection() if not self.series_tree.parent(item)]
        if not selected_ids:
            messagebox.showwarning("No Series Selected", "Please select one or more top-level series folders to move.")
            return

        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root: return
        
        if destination is None:
            destination = filedialog.askdirectory(title="Select Destination Folder", initialdir=tv_root)
        
        if not destination: return

        moves = []
        conflicts = []
        for item_id in selected_ids:
            series_name = self.series_tree.item(item_id, "text")
            src_path = os.path.join(tv_root, series_name)
            dst_path = os.path.join(destination, series_name)
            
            if os.path.exists(dst_path):
                conflicts.append(series_name)
            else:
                moves.append((src_path, dst_path))
        
        if conflicts:
            messagebox.showerror("Move Error", "The following series already exist in the destination and were not moved:\n\n" + "\n".join(conflicts))

        if not moves: return

        series_count = len(moves)
        if not messagebox.askyesno("Confirm Move", f"Move {series_count} series to the new location?"):
            return

        action = BatchAction(f"Move {series_count} series to '{os.path.basename(destination)}'", moves)
        failures = self.history.execute_action(action, stop_at=os.path.dirname(tv_root))
        
        if failures:
            messagebox.showerror("Move Failed", "Some series failed to move:\n\n" + "\n".join(failures))
        
        self.scan_root()

    def toggle_console(self):
        self.settings["console_visible"] = not self.settings.get("console_visible", True)
        save_settings(self.settings)

        if hasattr(self.console, 'hide_btn'):
            new_text = "Hide" if self.settings["console_visible"] else "Show"
            self.console.hide_btn.config(text=new_text)

        self._update_layout_after_console_change()
        self._build_tools_menu()
        
    def check_for_updates_simulated(self):
        latest_version = "7.0" 
        if CURRENT_VERSION < latest_version:
            if messagebox.askyesno("Update Available", f"Version {latest_version} is available.\nWould you like to update now?"):
                progress_win = tb.Toplevel(title="Downloading Update...")
                progress_win.geometry("300x100")
                pb = tb.Progressbar(progress_win, mode='determinate', bootstyle='success-striped')
                pb.pack(fill='x', padx=20, pady=20)
                progress_win.transient(self)
                progress_win.grab_set()

                def update_progress(val=0):
                    if val < 100:
                        pb.step(2)
                        progress_win.after(50, lambda: update_progress(val + 2))
                    else:
                        progress_win.destroy()
                        messagebox.showinfo("Update Complete", "Update downloaded. Please restart the application.")
                update_progress()

    def _select_all(self, event):
        widget = event.widget
        if isinstance(widget, tb.Treeview):
            all_items = self._get_all_tree_children(widget, "")
            widget.selection_set(all_items)
            return "break"
            
    def _get_all_tree_children(self, tree, item_id: str) -> List[str]:
        children = []
        for child_id in tree.get_children(item_id):
            children.append(child_id)
            children.extend(self._get_all_tree_children(tree, child_id))
        return children

# -------------------------
# Dialog Windows
# -------------------------
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: JMADMediaTool):
        super().__init__(parent)
        self.parent = parent
        self.settings = json.loads(json.dumps(parent.settings))
        self.patterns = parent.fluff_patterns[:]
        self.title("Settings")
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        self.resizable(True, True)
        self.minsize(600, 500)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        notebook = tb.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self._build_general_tab(notebook)
        self._build_patterns_tab(notebook)

        btn_frame = tb.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=(0, 10))
        btn_frame.columnconfigure(0, weight=1)
        tb.Button(btn_frame, text="Save", command=self._save, bootstyle="outline-success").grid(row=0, column=2, padx=6)
        tb.Button(btn_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").grid(row=0, column=1)

    def _build_general_tab(self, notebook):
        frm = tb.Frame(notebook, padding=10)
        notebook.add(frm, text="General")
        frm.columnconfigure(1, weight=1)

        tb.Label(frm, text="Episode Pattern:").grid(row=0, column=0, sticky="w", pady=6)
        self.ep_pattern_var = tk.StringVar(value=self.settings.get("episode_pattern", ""))
        tb.Entry(frm, textvariable=self.ep_pattern_var).grid(row=0, column=1, sticky="ew")

        tb.Label(frm, text="Movie Pattern:").grid(row=1, column=0, sticky="w", pady=6)
        self.movie_pattern_var = tk.StringVar(value=self.settings.get("movie_pattern", ""))
        tb.Entry(frm, textvariable=self.movie_pattern_var).grid(row=1, column=1, sticky="ew")

        self.console_visible_var = tk.BooleanVar(value=self.settings.get("console_visible", True))
        tb.Checkbutton(frm, text="Console Visible by Default", variable=self.console_visible_var).grid(row=2, column=1, sticky="w", pady=10)

        dir_frame = tb.LabelFrame(frm, text="Directories", padding=10)
        dir_frame.grid(row=3, column=0, columnspan=3, sticky="nsew")
        dir_frame.columnconfigure(1, weight=1)
        
        self.dir_entries = {}
        for i, (key, path) in enumerate(self.settings.get("directories", {}).items()):
            label_text = f"{key.replace('_', ' ').title()}:"
            tb.Label(dir_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5)
            var = tk.StringVar(value=path)
            tb.Entry(dir_frame, textvariable=var).grid(row=i, column=1, sticky="ew")
            tb.Button(dir_frame, text="...", command=lambda v=var: self._browse_dir(v)).grid(row=i, column=2, padx=5)
            self.dir_entries[key] = var
    
    def _build_patterns_tab(self, notebook):
        frm = tb.Frame(notebook, padding=10)
        notebook.add(frm, text="Patterns")
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)

        tb.Label(frm, text="Regex Patterns for Name Suggestions").pack()
        
        list_frame = tb.Frame(frm)
        list_frame.pack(fill="both", expand=True, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.patterns_listbox = tk.Listbox(list_frame)
        self.patterns_listbox.grid(row=0, column=0, sticky="nsew")
        for p in self.patterns:
            self.patterns_listbox.insert(tk.END, p)
        
        btn_frame = tb.Frame(frm)
        btn_frame.pack(fill="x")
        tb.Button(btn_frame, text="Add", command=self._add_pattern).pack(side="left")
        tb.Button(btn_frame, text="Edit", command=self._edit_pattern).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Delete", command=self._delete_pattern).pack(side="left")

    def _browse_dir(self, var):
        path = filedialog.askdirectory(title="Select Folder", initialdir=var.get())
        if path: var.set(path)

    def _add_pattern(self):
        new_pattern = simpledialog.askstring("Add Pattern", "Enter new regex pattern:", parent=self)
        if new_pattern: self.patterns_listbox.insert(tk.END, new_pattern)
    
    def _edit_pattern(self):
        selection = self.patterns_listbox.curselection()
        if not selection: return
        idx = selection[0]
        old_pattern = self.patterns_listbox.get(idx)
        new_pattern = simpledialog.askstring("Edit Pattern", "Edit regex pattern:", initialvalue=old_pattern, parent=self)
        if new_pattern:
            self.patterns_listbox.delete(idx)
            self.patterns_listbox.insert(idx, new_pattern)

    def _delete_pattern(self):
        selection = self.patterns_listbox.curselection()
        if selection: self.patterns_listbox.delete(selection[0])

    def _save(self):
        self.settings["episode_pattern"] = self.ep_pattern_var.get()
        self.settings["movie_pattern"] = self.movie_pattern_var.get()
        self.settings["console_visible"] = self.console_visible_var.get()
        for key, var in self.dir_entries.items():
            self.settings["directories"][key] = var.get()

        save_settings(self.settings)
        self.parent.settings = self.settings

        new_patterns = list(self.patterns_listbox.get(0, tk.END))
        save_patterns(new_patterns)
        self.parent.fluff_patterns = new_patterns

        self.parent._build_tools_menu()
        self.parent.log("Settings saved.")
        self.destroy()

class OrganizeDialog(tk.Toplevel):
    def __init__(self, parent: "JMADMediaTool", series_list: List[Series]):
        super().__init__(parent)
        self.parent_app = parent
        self.is_combine_mode = len(series_list) > 1
        self.title("Organize Series" if not self.is_combine_mode else "Combine Series")
        self.transient(parent)
        self.grab_set()

        self.all_series = series_list
        self.target_series = series_list[0]
        self.structure_changed = False
        self.local_undo_stack = []
        self.local_redo_stack = []
        self._preview_row_to_target_id: Dict[str, str] = {}
        
        self._build_ui()
        self.populate_trees()
        self.suggest_name()

        self.update_idletasks()
        self.resizable(True, True)
        self.minsize(1000, 750)
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        win_w = 1200
        win_h = 950
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top_frame = tb.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        tb.Label(top_frame, text="Final Series Name:").pack(side="left")
        self.target_name_var = tk.StringVar(value=self.target_series.name)
        self.target_name_var.trace_add("write", lambda *_: self._update_preview_tree())
        tb.Entry(top_frame, textvariable=self.target_name_var).pack(side="left", fill="x", expand=True, padx=5)
        suggestion_frame = tb.Frame(top_frame)
        suggestion_frame.pack(side='left')
        tb.Label(suggestion_frame, text="Suggestion:").pack(side="left", padx=(10, 2))
        self.suggestion_label = tb.Label(suggestion_frame, text="", bootstyle="info", cursor="hand2")
        self.suggestion_label.pack(side="left")
        self.suggestion_label.bind("<Button-1>", self.apply_suggestion)

        main_paned = tb.PanedWindow(self, orient="vertical", bootstyle="info")
        main_paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        top_paned = tb.PanedWindow(main_paned, orient="horizontal", bootstyle="info")
        
        source_frame = tb.Frame(top_paned)
        tb.Label(source_frame, text="Source Files", bootstyle="inverse-primary", padding=5).pack(fill="x")
        self.source_tree = tb.Treeview(source_frame, selectmode="extended")
        self.source_tree.pack(fill="both", expand=True)
        self.source_tree.bind("<<TreeviewSelect>>", self._on_source_selection_change)
        top_paned.add(source_frame, weight=1)

        action_frame = tb.Frame(top_paned, padding=10)
        self.move_season_btn = tb.Button(action_frame, text="Move to Season >>", command=self.move_selection_to_season, bootstyle="outline-info", state="disabled")
        self.move_season_btn.pack(pady=5, fill="x")
        self.move_specials_btn = tb.Button(action_frame, text="Move to Specials >>", command=lambda: self.move_selection_to_folder("Specials"), bootstyle="outline-info", state="disabled")
        self.move_specials_btn.pack(pady=5, fill="x")
        self.move_movies_btn = tb.Button(action_frame, text="Move to Movies >>", command=lambda: self.move_selection_to_folder("Movies"), bootstyle="outline-info", state="disabled")
        self.move_movies_btn.pack(pady=5, fill="x")
        self.move_custom_btn = tb.Button(action_frame, text="Move to... >>", command=self.move_selection_to_custom_folder, bootstyle="outline-info", state="disabled")
        self.move_custom_btn.pack(pady=5, fill="x")
        tb.Separator(action_frame, orient="horizontal").pack(fill="x", pady=20)
        self.undo_btn = tb.Button(action_frame, text="Undo", command=self.undo_local_change, bootstyle="outline-warning", state="disabled")
        self.undo_btn.pack(pady=5, fill="x")
        self.redo_btn = tb.Button(action_frame, text="Redo", command=self.redo_local_change, bootstyle="outline-info", state="disabled")
        self.redo_btn.pack(pady=5, fill="x")
        top_paned.add(action_frame)

        target_frame = tb.Frame(top_paned)
        tb.Label(target_frame, text="Target Structure", bootstyle="inverse-success", padding=5).pack(fill="x")
        self.target_tree = tb.Treeview(target_frame, selectmode="extended")
        self.target_tree.pack(fill="both", expand=True)
        self.target_tree.tag_configure('conflict', foreground='red')
        self.target_tree.bind("<Double-Button-3>", self._on_target_tree_double_right_click)
        self.target_tree.bind("<Double-1>", self._on_target_tree_left_double_click)
        top_paned.add(target_frame, weight=1)
        
        main_paned.add(top_paned, weight=3)

        preview_container = tb.Frame(main_paned)
        
        tb.Label(preview_container, text="Rename Preview", bootstyle="inverse-primary", padding=5).pack(fill="x")
        
        preview_frame = tb.Frame(preview_container)
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_tree = tb.Treeview(preview_frame, columns=("current", "new"), show="headings", selectmode="extended")
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        vsb = tb.Scrollbar(preview_frame, orient="vertical", command=self.preview_tree.yview, bootstyle="primary-round")
        vsb.grid(row=0, column=1, sticky="ns")
        self.preview_tree.configure(yscrollcommand=vsb.set)
        self.preview_tree.heading("current", text="Current Name")
        self.preview_tree.heading("new", text="New Name")
        self.preview_tree.column("current", anchor="w", width=350, stretch=True)
        self.preview_tree.column("new", anchor="w", width=250, stretch=True)
        self.preview_tree.tag_configure('conflict', foreground='red')
        self.preview_tree.bind("<Double-Button-3>", self._on_preview_tree_double_right_click)

        self.apply_preview_rename_btn = tb.Button(preview_container, text="Apply Renames to Target Structure", command=self._apply_preview_renames, bootstyle="outline-success")
        self.apply_preview_rename_btn.pack(side="bottom", fill="x", padx=5, pady=(0,5))

        main_paned.add(preview_container, weight=2)
        
        bottom_frame = tb.Frame(self)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.processed_var = tk.BooleanVar(value=self.target_series.is_processed)
        tb.Checkbutton(bottom_frame, text="Mark as Processed", variable=self.processed_var).pack(side="left", padx=10)
        self.type_var = tk.StringVar(value=self.target_series.media_type)
        tb.Combobox(bottom_frame, textvariable=self.type_var, values=MEDIA_TYPES, state="readonly").pack(side="left")

        btn_text = "Combine" if self.is_combine_mode else "Apply Changes"
        self.apply_btn = tb.Button(bottom_frame, text=btn_text, command=self.apply_changes, bootstyle="outline-success")
        self.apply_btn.pack(side="right", padx=5)
        tb.Button(bottom_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").pack(side="right")

    def _on_source_selection_change(self, event=None):
        state = "normal" if self.source_tree.selection() else "disabled"
        self.move_season_btn.config(state=state)
        self.move_specials_btn.config(state=state)
        self.move_custom_btn.config(state=state)
        self.move_movies_btn.config(state=state)

    def _capture_state(self):
        def capture_tree(tree, parent=""):
            items = []
            for item_id in tree.get_children(parent):
                items.append({
                    'text': tree.item(item_id, "text"),
                    'tags': tree.item(item_id, "tags"),
                    'open': tree.item(item_id, "open"),
                    'children': capture_tree(tree, item_id)
                })
            return items
        
        state = {
            'source': capture_tree(self.source_tree),
            'target': capture_tree(self.target_tree)
        }
        
        if not self.local_undo_stack or self.local_undo_stack[-1] != state:
            self.local_undo_stack.append(state)
            self.local_redo_stack.clear()
            self._update_undo_redo_buttons()

    def _restore_state(self, state):
        def restore_tree(tree, data, parent=""):
            for item_data in data:
                item_id = tree.insert(parent, "end", text=item_data['text'], tags=item_data['tags'], open=item_data['open'])
                if item_data.get('children'):
                    restore_tree(tree, item_data['children'], item_id)
        
        self.source_tree.delete(*self.source_tree.get_children())
        self.target_tree.delete(*self.target_tree.get_children())
        restore_tree(self.source_tree, state['source'])
        restore_tree(self.target_tree, state['target'])
        self._check_target_conflicts()
        self._update_preview_tree()

    def undo_local_change(self):
        if len(self.local_undo_stack) > 1:
            current_state = self.local_undo_stack.pop()
            self.local_redo_stack.append(current_state)
            
            previous_state = self.local_undo_stack[-1]
            self._restore_state(previous_state)
        self._update_undo_redo_buttons()

    def redo_local_change(self):
        if not self.local_redo_stack: return
        
        state_to_restore = self.local_redo_stack.pop()
        self.local_undo_stack.append(state_to_restore)
        self._restore_state(state_to_restore)
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self.undo_btn.config(state="normal" if len(self.local_undo_stack) > 1 else "disabled")
        self.redo_btn.config(state="normal" if self.local_redo_stack else "disabled")

    def populate_trees(self):
        self.source_tree.delete(*self.source_tree.get_children())
        self.target_tree.delete(*self.target_tree.get_children())
        
        for series in self.all_series:
            self._populate_tree_with_series_files(self.source_tree, series)
        
        self._update_preview_tree()
        self._capture_state()

    def _populate_tree_with_series_files(self, tree, series):
        staging_dir = self.parent_app.settings.get("directories", {}).get("staging", "")
        series_path = os.path.join(staging_dir, series.name)
        
        def add_to_tree(parent_id, current_path):
            try:
                for entry_name in sorted(os.listdir(current_path)):
                    full_path = os.path.join(current_path, entry_name)
                    if os.path.isdir(full_path):
                        child_id = tree.insert(parent_id, "end", text=entry_name, open=False, tags=(full_path,))
                        add_to_tree(child_id, full_path)
                    else:
                        tree.insert(parent_id, "end", text=entry_name, tags=(full_path,))
            except FileNotFoundError:
                pass 
        
        if os.path.exists(series_path):
            series_id = tree.insert("", "end", text=series.name, open=True, tags=(series_path,))
            add_to_tree(series_id, series_path)

    def move_selection_to_season(self):
        season_num = simpledialog.askinteger("Season Number", "Enter season number:", parent=self)
        if season_num is not None:
            self.move_selection_to_folder(f"Season {season_num:02d}")

    def move_selection_to_custom_folder(self):
        folder_name = simpledialog.askstring("Folder Name", "Enter destination folder:", parent=self)
        if folder_name and folder_name.strip():
            self.move_selection_to_folder(folder_name.strip())

    def move_selection_to_folder(self, folder_name: str):
        self.structure_changed = True
        selection = self.source_tree.selection()
        if not selection: return

        target_folder_id = next((c for c in self.target_tree.get_children() if self.target_tree.item(c, "text") == folder_name), None)
        if not target_folder_id:
            target_folder_id = self.target_tree.insert("", "end", text=folder_name, open=True)

        files_to_move: List[Tuple[str, str, str]] = []
        
        for item_id in selection:
            self._collect_files_recursively(self.source_tree, item_id, files_to_move)

        for _, source_path, basename in files_to_move:
            self.target_tree.insert(target_folder_id, "end", text=basename, tags=(source_path,))

        for item_id in selection:
            if self.source_tree.exists(item_id):
                self.source_tree.delete(item_id)
        
        self._prune_empty_source_folders()
        self._sort_target_tree()
        self._check_target_conflicts()
        self._update_preview_tree()
        self._capture_state()

    def _prune_empty_source_folders(self):
        while True:
            pruned_this_pass = False
            all_items = self._get_all_children(self.source_tree, "")
            for item_id in reversed(all_items):
                if self.source_tree.exists(item_id) and not self.source_tree.get_children(item_id) and self.source_tree.item(item_id, "tags"):
                    path = self.source_tree.item(item_id, "tags")[0]
                    if os.path.isdir(path):
                        self.source_tree.delete(item_id)
                        pruned_this_pass = True
            if not pruned_this_pass:
                break

    def _collect_files_recursively(self, tree, item_id, file_list):
        tags = tree.item(item_id, "tags")
        if not tags: return
        
        source_path = tags[0]
        if os.path.isfile(source_path):
            if not any(f[1] == source_path for f in file_list):
                file_list.append((item_id, source_path, os.path.basename(source_path)))
        
        for child_id in tree.get_children(item_id):
            self._collect_files_recursively(tree, child_id, file_list)

    def _get_all_children(self, tree, item_id: str) -> List[str]:
        children = []
        for child_id in tree.get_children(item_id):
            children.append(child_id)
            children.extend(self._get_all_children(tree, child_id))
        return children

    def _on_target_tree_double_right_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if not item_id: return
        self.structure_changed = True
        x, y, w, h = self.target_tree.bbox(item_id)
        entry = tb.Entry(self.target_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, self.target_tree.item(item_id, "text"))
        entry.focus()
        def save(e):
            self.target_tree.item(item_id, text=entry.get().strip())
            entry.destroy()
            self._check_target_conflicts()
            self._update_preview_tree()
            self._capture_state()
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _on_target_tree_left_double_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if item_id:
            self.target_tree.item(item_id, open=not self.target_tree.item(item_id, "open"))

    def suggest_name(self, event=None):
        if self.is_combine_mode:
            name_stems = [suggest_series_name(s.name, self.parent_app.fluff_patterns) for s in self.all_series]
            if name_stems:
                most_common_name = Counter(name_stems).most_common(1)[0][0]
                self.suggestion_label.config(text=most_common_name)
                return
        
        suggested = suggest_series_name(self.target_series.name, self.parent_app.fluff_patterns)
        self.suggestion_label.config(text=suggested)


    def apply_suggestion(self, event=None):
        self.target_name_var.set(self.suggestion_label.cget("text"))
    
    def _sort_target_tree(self):
        def sort_key(item_id):
            text = self.target_tree.item(item_id, "text")
            if text.lower() == 'movies': return (-1, 0)
            match = re.match(r'(?i)Season\s*(\d+)', text)
            if match: return (0, int(match.group(1)))
            if text.lower() == 'specials': return (1, 0)
            return (2, text.lower())

        items = list(self.target_tree.get_children(""))
        items.sort(key=sort_key)
        for i, item_id in enumerate(items):
            self.target_tree.move(item_id, "", i)

    def _check_target_conflicts(self):
        folder_contents: Dict[str, List[str]] = {}
        has_conflicts = False

        def gather_basenames(item_id, parent_folder_name):
            item_text = self.target_tree.item(item_id, "text")
            is_folder = not self.target_tree.get_children(item_id)
            
            if is_folder:
                for child_id in self.target_tree.get_children(item_id):
                    gather_basenames(child_id, item_text)
            else:
                folder_contents.setdefault(parent_folder_name, []).append(item_text)

        for root_item_id in self.target_tree.get_children(""):
            gather_basenames(root_item_id, "__root__")

        conflicts_by_folder: Dict[str, set] = {}
        for folder, files in folder_contents.items():
            counts = Counter(files)
            conflicts = {name for name, count in counts.items() if count > 1}
            if conflicts:
                conflicts_by_folder[folder] = conflicts
                has_conflicts = True

        def tag_conflicts(item_id, parent_folder_name):
            item_text = self.target_tree.item(item_id, "text")
            is_folder = bool(self.target_tree.get_children(item_id))
            
            current_tags = list(self.target_tree.item(item_id, "tags")) if self.target_tree.item(item_id, "tags") else []
            if 'conflict' in current_tags: current_tags.remove('conflict')
            
            if not is_folder:
                if parent_folder_name in conflicts_by_folder and item_text in conflicts_by_folder[parent_folder_name]:
                    current_tags.append('conflict')

            self.target_tree.item(item_id, tags=tuple(current_tags))
            
            if is_folder:
                for child_id in self.target_tree.get_children(item_id):
                    tag_conflicts(child_id, item_text)
        
        for root_item_id in self.target_tree.get_children(""):
             tag_conflicts(root_item_id, "__root__")

        self.apply_btn.config(state="disabled" if has_conflicts else "normal")

    def _update_preview_tree(self):
        self.preview_tree.delete(*self.preview_tree.get_children())
        self._preview_row_to_target_id.clear()

        series_name = self.target_name_var.get()
        if not series_name:
            return

        for folder_id in self.target_tree.get_children(""):
            folder_name = self.target_tree.item(folder_id, "text")
            m = SEASON_HINT_RE.search(folder_name)
            season_num = None
            if m:
                groups = m.groups()
                if groups[0]: season_num = int(groups[0])
                elif groups[1]: season_num = int(groups[1])
            elif re.search(r"specials", folder_name, re.I):
                season_num = 0
            
            if re.search(r"movies", folder_name, re.I):
                continue

            for file_id in self.target_tree.get_children(folder_id):
                basename = self.target_tree.item(file_id, "text")
                _, parsed_ep = parse_episode_info(basename)
                
                tags = self.target_tree.item(file_id, "tags")
                path = tags[0] if tags else basename
                
                ep = Episode(path, season=season_num)
                ep.series_name = series_name
                ep.parsed_episode_num = parsed_ep
                
                current_name_no_ext, _ = os.path.splitext(basename)
                current_display = f"[S{season_num:02d}] {current_name_no_ext}" if season_num is not None else current_name_no_ext
                
                pred_full = predict_new_filename(ep, self.parent_app.settings)
                pred_display = os.path.splitext(pred_full)[0] if pred_full else "(Cannot determine new name)"

                row_id = self.preview_tree.insert("", "end", values=(current_display, pred_display))
                self._preview_row_to_target_id[row_id] = file_id

        self._check_preview_conflicts()

    def _check_preview_conflicts(self):
        all_new_names = [self.preview_tree.set(row_id, "new") for row_id in self.preview_tree.get_children()]
        counts = Counter(all_new_names)
        conflicts = {name for name, count in counts.items() if count > 1 and name != "(Cannot determine new name)"}
        for row_id in self.preview_tree.get_children():
            name = self.preview_tree.set(row_id, "new")
            self.preview_tree.item(row_id, tags=('conflict',) if name in conflicts else ())
        self.apply_preview_rename_btn.config(state="disabled" if conflicts else "normal")

    def _apply_preview_renames(self):
        if 'disabled' in self.apply_preview_rename_btn.state():
            messagebox.showerror("Conflicts Found", "Please resolve filename conflicts in the preview (marked in red) before applying.")
            return

        self.structure_changed = True
        for preview_id in self.preview_tree.get_children():
            target_id = self._preview_row_to_target_id.get(preview_id)
            if not target_id: continue

            original_basename = self.target_tree.item(target_id, "text")
            _, ext = os.path.splitext(original_basename)
            new_name_no_ext = self.preview_tree.set(preview_id, "new")
            
            self.target_tree.item(target_id, text=new_name_no_ext + ext)
        
        self._check_target_conflicts()
        self._update_preview_tree()
        self._capture_state()

    def _on_preview_tree_double_right_click(self, event):
        row_id = self.preview_tree.identify_row(event.y)
        if not row_id or self.preview_tree.identify_column(event.x) != "#2": return
        
        x, y, w, h = self.preview_tree.bbox(row_id, column="new")
        entry = tb.Entry(self.preview_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, self.preview_tree.set(row_id, "new"))
        entry.focus()
        
        def save(e):
            self.preview_tree.set(row_id, "new", entry.get().strip())
            entry.destroy()
            self._check_preview_conflicts()
        
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)


    def apply_changes(self):
        final_target_name = self.target_name_var.get().strip()
        if not final_target_name:
            messagebox.showerror("Invalid Name", "Final series name cannot be empty.")
            return

        staging_dir = self.parent_app.settings.get("directories", {}).get("staging")
        final_series_path = os.path.join(staging_dir, final_target_name)
        original_names = {s.name for s in self.all_series}

        if final_target_name not in original_names and os.path.isdir(final_series_path):
            messagebox.showinfo("Conflict Detected", f"A folder named '{final_target_name}' already exists and was not part of this organization session. It will be added to the source list so you can combine it.")
            
            conflicting_series = self.parent_app.series_map.get(final_target_name)
            if conflicting_series and conflicting_series not in self.all_series:
                self._capture_state()
                self.all_series.append(conflicting_series)
                self.populate_trees() 
                self.is_combine_mode = True
                self.title("Combine Series")
                self.apply_btn.config(text="Combine")
            else:
                messagebox.showwarning("Scan Needed", f"Could not find series data for '{final_target_name}'. You may need to rescan your library from the main window.")
            return

        description: str
        all_moves: List[Tuple[str, str]]
        metadata_to_create_path: Optional[str] = None

        if not self.structure_changed and not self.is_combine_mode and final_target_name != self.target_series.name:
            original_path = os.path.join(staging_dir, self.target_series.name)
            all_moves = [(original_path, final_series_path)]
            description = f"Rename series {self.target_series.name} -> {final_target_name}"
        else:
            all_moves = []
            def plan_moves_from_tree(item_id, parent_path):
                text = self.target_tree.item(item_id, "text")
                current_path = os.path.join(parent_path, text)
                tags = self.target_tree.item(item_id, "tags")
                if tags:
                    original_path = tags[0]
                    if os.path.abspath(original_path) != os.path.abspath(current_path):
                        all_moves.append((original_path, current_path))
                if self.target_tree.get_children(item_id):
                        for child_id in self.target_tree.get_children(item_id):
                            plan_moves_from_tree(child_id, current_path)
            for top_item_id in self.target_tree.get_children(""):
                plan_moves_from_tree(top_item_id, final_series_path)
            
            description = f"Organize series: {final_target_name}"
            metadata_to_create_path = os.path.join(final_series_path, METADATA_FILENAME)

        metadata_changed = self.target_series.is_processed != self.processed_var.get() or self.target_series.media_type != self.type_var.get()

        if not all_moves and not metadata_changed:
            messagebox.showinfo("Organize", "No changes to apply.")
            return
            
        if all_moves and not messagebox.askyesno("Confirm Changes", f"Apply {len(all_moves)} file/folder operations?"):
            return
        
        action = BatchAction(description, all_moves)
        action.metadata_path = metadata_to_create_path
        failures = self.parent_app.history.execute_action(action, stop_at=staging_dir)

        if not failures:
            metadata = {
                "is_processed": self.processed_var.get(),
                "media_type": self.type_var.get()
            }
            try:
                if not os.path.isdir(final_series_path): os.makedirs(final_series_path, exist_ok=True)
                with open(os.path.join(final_series_path, METADATA_FILENAME), 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                failures.append(f"Could not write metadata: {e}")

            source_folders_to_prune = {os.path.join(staging_dir, s.name) for s in self.all_series}
            for path in source_folders_to_prune:
                if os.path.abspath(path) != os.path.abspath(final_series_path):
                    prune_empty_dirs(path, stop_at=staging_dir)

        if failures:
            messagebox.showerror("Operation Failed", "Some operations failed. Please review the changes.\n\n" + "\n".join(failures))
        
        self.destroy()
        self.parent_app.scan_root()

class AssociateMovieDialog(tk.Toplevel):
    def __init__(self, parent: "JMADMediaTool", movies_to_associate: List[Series], all_series_names: List[str]):
        super().__init__(parent)
        self.parent_app = parent
        self.movies = movies_to_associate
        self.all_series = all_series_names
        
        self.title("Associate Anime Movie")
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        self.update_idletasks()
        self.resizable(True, True)
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

        
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"+{x}+{y}")
        
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        frm = tb.Frame(self, padding=20)
        frm.grid(row=0, column=0, sticky="nsew")
        frm.columnconfigure(0, weight=1) 
        
        movie_names = ", ".join([f"'{s.name}'" for s in self.movies])
        tb.Label(frm, text=f"Choose a parent series for: {movie_names}", wraplength=480).pack(pady=(0, 10), fill="x")
        
        self.series_var = tk.StringVar()
        self.series_combo = tb.Combobox(frm, textvariable=self.series_var, values=self.all_series, state="readonly")
        self.series_combo.pack(fill="x", pady=5)
        if self.all_series:
            self.series_combo.set(self.all_series[0])
            
        btn_frame = tb.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        tb.Button(btn_frame, text="OK", command=self._apply_association, bootstyle="outline-success").grid(row=0, column=2, padx=6)
        tb.Button(btn_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").grid(row=0, column=1)


    def _apply_association(self):
        parent_series_name = self.series_var.get()
        if not parent_series_name:
            messagebox.showwarning("No Series Selected", "Please select a parent series.", parent=self)
            return
            
        staging_dir = self.parent_app.settings.get("directories", {}).get("staging")
        if not staging_dir: return
        
        moves = []
        for movie_series in self.movies:
            src_path = os.path.join(staging_dir, movie_series.name)
            dst_path = os.path.join(staging_dir, parent_series_name, "Movies", movie_series.name)
            moves.append((src_path, dst_path))
            
        action = BatchAction(f"Associate {len(moves)} movie(s) with {parent_series_name}", moves)
        
        parent_series_path = os.path.join(staging_dir, parent_series_name)
        action.metadata_path = os.path.join(parent_series_path, METADATA_FILENAME) 
        
        failures = self.parent_app.history.execute_action(action, stop_at=staging_dir)
        
        if failures:
            messagebox.showerror("Operation Failed", "Some movies failed to associate:\n\n" + "\n".join(failures))
        
        self.destroy()
        self.parent_app.scan_root()

# -------------------------
# Entrypoint
# -------------------------
def main():
    settings = load_settings()
    patterns = load_patterns()
    app = JMADMediaTool(settings, patterns)
    app.mainloop()

if __name__ == "__main__":
    main()

