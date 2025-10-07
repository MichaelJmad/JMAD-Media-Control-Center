#!/usr/bin/env python3
"""
JMAD Media Tool
A robust TV series and media renamer application.
Version: 4.6 (Undo Recording Fix)
"""
import os
import re
import json
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from typing import Dict, List, Optional, Tuple
from collections import Counter

# -------------------------
# Configuration
# -------------------------
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
SETTINGS_FILE = "settings.json"
VALID_THEMES = ["litera", "darkly", "superhero", "cosmo", "flatly", "minty"]
DEFAULT_SETTINGS = {
    "tv_root": "",
    "episode_pattern": "{series} - S{season:02d}E{episode:02d}{ext}",
    "theme": "litera"
}

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

class HistoryManager:
    def __init__(self):
        self.history_log: List[Tuple[BatchAction, str]] = []
        self.current_pos: int = -1

    def push(self, action: BatchAction):
        if self.current_pos < len(self.history_log) - 1:
            self.history_log = self.history_log[: self.current_pos + 1]
        self.history_log.append((action, "new"))
        self.current_pos += 1

    def can_undo(self) -> bool:
        return self.current_pos >= 0

    def can_redo(self) -> bool:
        return self.current_pos < len(self.history_log) - 1

    def _perform_moves(self, moves: List[Tuple[str, str]], is_undo: bool, stop_at: Optional[str]) -> List[str]:
        failures = []
        move_order = list(reversed(moves)) if is_undo else moves
        
        for src, dst in move_order:
            a, b = (dst, src) if is_undo else (src, dst)
            try:
                if not os.path.isdir(os.path.dirname(b)):
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                if os.path.exists(a):
                    shutil.move(a, b)
                    prune_empty_dirs(os.path.dirname(a), stop_at=stop_at)
                elif not is_undo:
                    failures.append(f"Source missing: {os.path.basename(a)}")
            except Exception as e:
                failures.append(f"Error moving {os.path.basename(a)}: {e}")
        return failures
        
    def execute_action(self, action: BatchAction, stop_at: Optional[str] = None) -> List[str]:
        """Executes a new action and adds it to the history log."""
        failures = self._perform_moves(action.moves, is_undo=False, stop_at=stop_at)
        if not failures:
            self.push(action)
        return failures

    def undo(self, stop_at: Optional[str] = None) -> Tuple[List[str], Optional[BatchAction]]:
        if not self.can_undo(): return [], None
        action, _ = self.history_log[self.current_pos]
        failures = self._perform_moves(action.moves, is_undo=True, stop_at=stop_at)
        self.history_log[self.current_pos] = (action, "undone")
        self.current_pos -= 1
        return failures, action

    def redo(self, stop_at: Optional[str] = None) -> Tuple[List[str], Optional[BatchAction]]:
        if not self.can_redo(): return [], None
        self.current_pos += 1
        action, _ = self.history_log[self.current_pos]
        failures = self._perform_moves(action.moves, is_undo=False, stop_at=stop_at)
        self.history_log[self.current_pos] = (action, "redone")
        return failures, action
        
    def clear(self):
        self.history_log.clear()
        self.current_pos = -1

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

def prune_empty_dirs(path: str, stop_at: Optional[str] = None):
    try:
        path = os.path.abspath(path)
        stop_at_path = os.path.abspath(stop_at) if stop_at else None
        while os.path.isdir(path) and not os.listdir(path):
            if stop_at_path and os.path.samefile(path, stop_at_path): break
            parent = os.path.dirname(path)
            os.rmdir(path)
            path = parent
    except (OSError, PermissionError): pass

# -------------------------
# Filename Parsing & Scanning
# -------------------------
SEASON_HINT_RE = re.compile(r"(?:season[\s._-]*([0-9]{1,2}))|(?:\bS([0-9]{1,2})\b)", re.I)
EPISODE_PATTERNS = [
    re.compile(r"s(\d{1,2})[ex](\d{1,3})", re.I),
    re.compile(r"(\d{1,2})x(\d{1,3})", re.I),
    re.compile(r"[._\-\s]e(\d{1,3})(?:[._\-\s]|$)", re.I),
    re.compile(r"episode[\s._-]*(\d+)", re.I),
    re.compile(r"ep[\s._-]*(\d+)", re.I),
    re.compile(r"part[\s._-]*(\d+)", re.I),
    re.compile(r"[._\-\s](\d{2,3})(?:[._\-\s]|$)", re.I),
]

def parse_episode_info(basename: str) -> Optional[int]:
    for pat in EPISODE_PATTERNS:
        m = pat.search(basename)
        if m and m.groups():
            try: return int(m.groups()[-1])
            except (ValueError, IndexError): continue
    return None

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
    for entry in os.scandir(tv_root):
        if not entry.is_dir(): continue
        series = Series(entry.name)
        series_map[entry.name] = series

        for sub_entry in os.scandir(entry.path):
            if sub_entry.is_dir():
                folder_name = sub_entry.name
                if not SEASON_HINT_RE.search(folder_name) and not re.search(r"specials", folder_name, re.I):
                    series.has_nonstandard_folders = True
                    break
        
        for root, _, files in os.walk(entry.path):
            folder_name = os.path.basename(root)
            season_hint: Optional[int] = None
            m = SEASON_HINT_RE.search(folder_name)
            if m:
                groups = m.groups()
                if groups[0]: season_hint = int(groups[0])
                elif groups[1]: season_hint = int(groups[1])
            elif re.search(r"specials", folder_name, re.I): season_hint = 0
            for f in files:
                if os.path.splitext(f)[1].lower() not in VIDEO_EXTS: continue
                ep = Episode(os.path.join(root, f), season=season_hint)
                ep.series_name = series.name
                ep.parsed_episode_num = parse_episode_info(f)
                if ep.season is not None:
                    series.seasons.setdefault(ep.season, Season(ep.season)).episodes.append(ep)
                else:
                    series.unsorted.append(ep)
    for s in series_map.values():
        for sec in s.seasons.values():
            sec.episodes.sort(key=lambda e: (e.parsed_episode_num or float('inf'), e.path.lower()))
        s.unsorted.sort(key=lambda e: e.path.lower())
    return series_map

# -------------------------
# UI Panels
# -------------------------
class PreviewPanel(tb.Frame):
    def __init__(self, parent, app_controller, settings: dict, history: HistoryManager):
        super().__init__(parent)
        self.app = app_controller
        self.settings = settings
        self.history = history
        self._row_to_episode: Dict[str, Episode] = {}
        self._build_ui()

    def _build_ui(self):
        tb.Label(self, text="Preview", bootstyle="inverse-primary", padding=5, anchor="center").pack(fill="x")
        tree_frame = tb.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree = tb.Treeview(tree_frame, columns=("current", "new"), show="headings", selectmode="extended")
        self.tree.heading("current", text="Current Name")
        self.tree.heading("new", text="New Name")
        self.tree.column("current", anchor="w", width=350, stretch=True)
        self.tree.column("new", anchor="w", width=250, stretch=True)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = tb.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview, bootstyle="primary-round")
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.tag_configure('conflict', foreground='red')
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self.app.hide_tooltip)
        self.tree.bind("<Double-Button-3>", self._on_double_right_click)
        self.btn_apply = tb.Button(self, text="Rename", command=self._apply_renames, bootstyle="outline-success")
        self.btn_apply.pack(fill="x", padx=6, pady=(0, 6))

    def set_items(self, episodes: List[Episode]):
        self.tree.delete(*self.tree.get_children())
        self._row_to_episode.clear()
        for ep in episodes:
            pred = predict_new_filename(ep, self.settings) or "(Cannot determine new name)"
            row_id = self.tree.insert("", "end", values=(ep.basename(), pred))
            self._row_to_episode[row_id] = ep
        self._check_rename_conflicts()

    def _check_rename_conflicts(self):
        all_new_names = [self.tree.set(row_id, "new") for row_id in self.tree.get_children()]
        counts = Counter(all_new_names)
        conflicts = {name for name, count in counts.items() if count > 1 and name != "(Cannot determine new name)"}
        has_conflicts = False
        for row_id in self.tree.get_children():
            name = self.tree.set(row_id, "new")
            if name in conflicts:
                self.tree.item(row_id, tags=('conflict',))
                has_conflicts = True
            else:
                self.tree.item(row_id, tags=())
        self.btn_apply.config(state="disabled" if has_conflicts else "normal")

    def _apply_renames(self):
        if 'disabled' in self.btn_apply.state():
            messagebox.showerror("Conflicts Found", "Please resolve all filename conflicts (marked in red) before applying.")
            return
        moves = []
        for row_id, ep in self._row_to_episode.items():
            new_name = self.tree.set(row_id, "new")
            if new_name and new_name != "(Cannot determine new name)" and new_name != ep.basename():
                dst = os.path.join(os.path.dirname(ep.path), new_name)
                moves.append((ep.path, dst))
        if not moves: return
        if not messagebox.askyesno("Confirm Rename", f"Rename {len(moves)} file(s)?"): return
        failures = self.app.perform_file_operation(moves, f"Rename {len(moves)} files")
        if failures: messagebox.showerror("Rename Error", "Some files failed to rename:\n\n" + "\n".join(failures))
        self.app.scan_root()

    def _on_double_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id or self.tree.identify_column(event.x) != "#2": return
        x, y, w, h = self.tree.bbox(row_id, column="new")
        entry = tb.Entry(self.tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h + 10)
        entry.insert(0, self.tree.set(row_id, "new"))
        entry.focus()
        def save(e):
            ep = self._row_to_episode[row_id]
            new_name = entry.get().strip()
            ep.override_new_name = new_name
            self.tree.set(row_id, "new", new_name)
            entry.destroy()
            self._check_rename_conflicts()
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _on_motion(self, event):
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if row and col in ("#1", "#2"):
            text = self.tree.set(row, col)
            self.app.show_tooltip(text, event.x_root, event.y_root)
        else:
            self.app.hide_tooltip()

class HistoryPanel(tb.Frame):
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        self._build_ui()

    def _build_ui(self):
        tb.Label(self, text="History", bootstyle="inverse-primary", padding=5, anchor="center").pack(fill="x")
        list_frame = tb.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox = tk.Listbox(list_frame, activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        vsb = tb.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview, bootstyle="primary-round")
        vsb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=vsb.set)
        btn_frame = tb.Frame(self)
        btn_frame.pack(fill="x", padx=6, pady=(0,6))
        tb.Button(btn_frame, text="Undo", command=self.app.undo_action, bootstyle="outline-warning").pack(side="left")
        tb.Button(btn_frame, text="Redo", command=self.app.redo_action, bootstyle="outline-info").pack(side="left", padx=6)
        tb.Button(btn_frame, text="Clear", command=self.app.clear_history, bootstyle="outline-warning").pack(side="right")

    def refresh(self, history_manager: HistoryManager):
        self.listbox.delete(0, tk.END)
        for i, (action, status) in enumerate(history_manager.history_log):
            prefix = {"undone": "[UNDO] ", "redone": "[REDO] "}.get(status, "")
            self.listbox.insert(tk.END, f"{prefix}{action.description}")
            if status == "undone": self.listbox.itemconfig(i, {'fg': 'grey'})
        if history_manager.can_undo():
            self.listbox.selection_set(history_manager.current_pos)
            self.listbox.see(history_manager.current_pos)

# -------------------------
# Main Application Window
# -------------------------
class JMADMediaTool(tb.Window):
    def __init__(self, settings: dict):
        theme = settings.get("theme", "darkly")
        super().__init__(themename=theme)
        self.title("JMAD Media Tool")
        self.geometry("1400x800")
        self.settings = settings
        self.history = HistoryManager()
        self.series_map: Dict[str, Series] = {}
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._build_ui()
        self.after(100, self.scan_root)

    def _build_ui(self):
        toolbar = tb.Frame(self)
        toolbar.pack(side="top", fill="x", padx=6, pady=6)
        
        tb.Button(toolbar, text="Scan Root", command=self.scan_root, bootstyle="outline-success").pack(side="left", padx=4)
        tb.Button(toolbar, text="Settings", command=self.open_settings, bootstyle="outline-light").pack(side="left", padx=4)
        tb.Button(toolbar, text="Undo", command=self.undo_action, bootstyle="outline-warning").pack(side="left", padx=4)
        tb.Button(toolbar, text="Redo", command=self.redo_action, bootstyle="outline-info").pack(side="left", padx=4)
        tb.Button(toolbar, text="Exit", command=self.destroy, bootstyle="outline-danger").pack(side="right", padx=4)
        
        paned = tb.PanedWindow(self, orient="horizontal", bootstyle="primary")
        paned.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        
        left_frame = tb.Frame(paned)
        tb.Label(left_frame, text="Series/Season", bootstyle="inverse-primary", padding=5, anchor="center").pack(fill="x")
        tree_container = tb.Frame(left_frame)
        tree_container.pack(fill='both', expand=True, padx=6, pady=6)
        self.series_tree = tb.Treeview(tree_container, show="tree", selectmode="extended", bootstyle="primary")
        self.series_tree.pack(fill="both", expand=True, side="left")
        self.series_tree.tag_configure('nonstandard', foreground='orange')
        vsb_left = tb.Scrollbar(tree_container, orient="vertical", command=self.series_tree.yview, bootstyle="primary-round")
        vsb_left.pack(side="right", fill="y")
        self.series_tree.configure(yscrollcommand=vsb_left.set)
        self.series_tree.bind("<<TreeviewSelect>>", self.on_series_selection)
        self.series_tree.bind("<Button-3>", self.on_series_right_click)
        paned.add(left_frame, weight=2)
        
        right_paned = tb.PanedWindow(paned, orient="vertical", bootstyle="primary")
        self.preview_panel = PreviewPanel(right_paned, self, self.settings, self.history)
        self.history_panel = HistoryPanel(right_paned, self)
        right_paned.add(self.preview_panel, weight=3)
        right_paned.add(self.history_panel, weight=1)
        paned.add(right_paned, weight=3)

    def scan_root(self):
        tv_root = self.settings.get("tv_root")
        if not tv_root or not os.path.isdir(tv_root):
            if not self.winfo_viewable(): return
            messagebox.showwarning("TV Root Not Set", "Please configure a valid TV Root in Settings.")
            return
        self.series_map = scan_tv_root(tv_root)
        self.populate_series_tree()
        self.preview_panel.set_items([])
        self.history_panel.refresh(self.history)

    def populate_series_tree(self):
        self.series_tree.delete(*self.series_tree.get_children())
        for sname in sorted(self.series_map.keys(), key=str.lower):
            series = self.series_map[sname]
            tags = ('nonstandard',) if series.has_nonstandard_folders else ()
            top_id = self.series_tree.insert("", "end", text=sname, open=False, tags=tags)
            for season_idx in sorted(series.seasons.keys()):
                label = "Specials" if season_idx == 0 else f"Season {season_idx:02d}"
                self.series_tree.insert(top_id, "end", text=label)
            if series.unsorted:
                self.series_tree.insert(top_id, "end", text="Unsorted")

    def on_series_selection(self, event=None):
        episodes: List[Episode] = []
        for item in self.series_tree.selection():
            parent_id = self.series_tree.parent(item)
            series_name = self.series_tree.item(parent_id or item, "text")
            series = self.series_map.get(series_name)
            if not series: continue
            if not parent_id:
                episodes.extend(series.get_all_episodes())
            else:
                node_text = self.series_tree.item(item, "text")
                if node_text == "Unsorted":
                    episodes.extend(series.unsorted)
                else:
                    try:
                        season_key = 0 if node_text == "Specials" else int(re.findall(r'\d+', node_text)[0])
                        if season_key in series.seasons:
                            episodes.extend(series.seasons[season_key].episodes)
                    except (IndexError, ValueError): pass
        self.preview_panel.set_items(episodes)

    def on_series_right_click(self, event):
        item_id = self.series_tree.identify_row(event.y)
        if not item_id: return
        current_selection = self.series_tree.selection()
        if item_id not in current_selection:
            self.series_tree.selection_set((item_id,))
            current_selection = (item_id,)
        menu = tb.Menu(self, tearoff=0)
        top_level_items = [item for item in current_selection if not self.series_tree.parent(item)]
        if len(top_level_items) >= 1:
             menu.add_command(label="Organize / Combine Series...", command=lambda: self.open_organize_dialog(top_level_items))
        if menu.index('end') is not None:
            menu.post(event.x_root, event.y_root)

    def perform_file_operation(self, moves: List[Tuple[str, str]], description: str) -> List[str]:
        failures = self.history._perform_moves(moves, is_undo=False, stop_at=self.settings.get("tv_root"))
        if not failures:
            action = BatchAction(description, moves)
            self.history.push(action)
        self.history_panel.refresh(self.history)
        return failures

    def undo_action(self):
        if not self.history.can_undo(): return
        failures, _ = self.history.undo(stop_at=self.settings.get("tv_root"))
        if failures: messagebox.showwarning("Undo Failed", "\n".join(failures))
        self.scan_root()

    def redo_action(self):
        if not self.history.can_redo(): return
        failures, _ = self.history.redo(stop_at=self.settings.get("tv_root"))
        if failures: messagebox.showwarning("Redo Failed", "\n".join(failures))
        self.scan_root()

    def clear_history(self):
        if messagebox.askyesno("Clear History", "This will clear all undo/redo history. Continue?"):
            self.history.clear()
            self.history_panel.refresh(self.history)

    def open_settings(self):
        SettingsDialog(self)

    def open_organize_dialog(self, item_ids: List[str]):
        series_to_organize = [self.series_map[self.series_tree.item(item_id, "text")] for item_id in item_ids]
        if series_to_organize:
            OrganizeDialog(self, series_to_organize)

    def show_tooltip(self, text: str, x: int, y: int):
        self.hide_tooltip()
        if not text or len(text.strip()) < 1: return
        self._tooltip_win = tk.Toplevel(self)
        self._tooltip_win.wm_overrideredirect(True)
        self._tooltip_win.wm_geometry(f"+{x+20}+{y+20}")
        tb.Label(self._tooltip_win, text=text, relief="solid", background="#FFFFE0", padding=5).pack()

    def hide_tooltip(self, event=None):
        if self._tooltip_win:
            self._tooltip_win.destroy()
            self._tooltip_win = None

# -------------------------
# Dialog Windows
# -------------------------
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: JMADMediaTool):
        super().__init__(parent)
        self.parent = parent
        self.settings = dict(parent.settings)
        self.title("Settings")
        self.transient(parent)
        self.grab_set()
        self._build_ui()

        self.update_idletasks()
        self.resizable(False, False)
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
        frm = tb.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        tb.Label(frm, text="TV Root Folder:").grid(row=0, column=0, sticky="w", pady=6)
        self.var_tv_root = tk.StringVar(value=self.settings.get("tv_root", ""))
        tb.Entry(frm, textvariable=self.var_tv_root).grid(row=0, column=1, sticky="ew", padx=6)
        tb.Button(frm, text="Browse...", command=self._browse, bootstyle="outline-secondary").grid(row=0, column=2, padx=6)
        tb.Label(frm, text="Rename Pattern:").grid(row=1, column=0, sticky="nw", pady=6)
        self.var_pattern = tk.StringVar(value=self.settings.get("episode_pattern", ""))
        tb.Entry(frm, textvariable=self.var_pattern).grid(row=1, column=1, sticky="ew", padx=6, columnspan=2)
        tb.Label(frm, text="Keys: {series}, {season:02d}, {episode:02d}, {ext}").grid(row=2, column=1, sticky="w")
        tb.Label(frm, text="Theme:").grid(row=3, column=0, sticky="w", pady=10)
        self.var_theme = tk.StringVar(value=self.settings.get("theme"))
        tb.Combobox(frm, textvariable=self.var_theme, values=VALID_THEMES, state="readonly").grid(row=3, column=1, sticky="w", padx=6)
        btn_frame = tb.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        tb.Button(btn_frame, text="Save", command=self._save, bootstyle="outline-success").pack(side="right", padx=6)
        tb.Button(btn_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").pack(side="right")

    def _browse(self):
        p = filedialog.askdirectory(title="Select TV Root Folder", initialdir=self.var_tv_root.get())
        if p: self.var_tv_root.set(p)

    def _save(self):
        self.settings["tv_root"] = self.var_tv_root.get().strip()
        self.settings["episode_pattern"] = self.var_pattern.get().strip()
        self.settings["theme"] = self.var_theme.get()
        save_settings(self.settings)
        self.parent.settings = self.settings
        self.destroy()
        messagebox.showinfo("Settings Saved", "Settings have been saved. A restart is required for theme changes to take full effect.")
        self.parent.scan_root()

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
        
        self._build_ui()
        self.populate_trees()

        self.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        win_w = 1200
        win_h = 700
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _build_ui(self):
        top_frame = tb.Frame(self, padding=10)
        top_frame.pack(fill="x")
        tb.Label(top_frame, text="Final Series Name:").pack(side="left")
        self.target_name_var = tk.StringVar(value=self.target_series.name)
        tb.Entry(top_frame, textvariable=self.target_name_var).pack(side="left", fill="x", expand=True, padx=5)

        paned = tb.PanedWindow(self, orient="horizontal", bootstyle="info")
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        source_frame = tb.Frame(paned)
        tb.Label(source_frame, text="Source Files", bootstyle="inverse-primary", padding=5).pack(fill="x")
        self.source_tree = tb.Treeview(source_frame, selectmode="extended")
        self.source_tree.pack(fill="both", expand=True)
        self.source_tree.bind("<Button-1>", self._on_tree_click)
        paned.add(source_frame, weight=1)

        action_frame = tb.Frame(paned, padding=10)
        tb.Button(action_frame, text="Move to Season >>", command=self.move_selection_to_season, bootstyle="outline-info").pack(pady=5, fill="x")
        tb.Button(action_frame, text="Move to Specials >>", command=lambda: self.move_selection_to_folder("Specials"), bootstyle="outline-info").pack(pady=5, fill="x")
        tb.Button(action_frame, text="Move to... >>", command=self.move_selection_to_custom_folder, bootstyle="outline-info").pack(pady=5, fill="x")
        tb.Separator(action_frame, orient="horizontal").pack(fill="x", pady=20)
       # tb.Button(action_frame, text="Flatten Target", command=self.flatten_target, bootstyle="outline-warning").pack(pady=5, fill="x")
       # tb.Separator(action_frame, orient="horizontal").pack(fill="x", pady=20)
        self.undo_btn = tb.Button(action_frame, text="Undo", command=self.undo_local_change, bootstyle="outline-warning", state="disabled")
        self.undo_btn.pack(pady=5, fill="x")
        self.redo_btn = tb.Button(action_frame, text="Redo", command=self.redo_local_change, bootstyle="outline-info", state="disabled")
        self.redo_btn.pack(pady=5, fill="x")
        paned.add(action_frame)

        target_frame = tb.Frame(paned)
        tb.Label(target_frame, text="Target Structure", bootstyle="inverse-success", padding=5).pack(fill="x")
        self.target_tree = tb.Treeview(target_frame, selectmode="extended")
        self.target_tree.pack(fill="both", expand=True)
        self.target_tree.tag_configure('conflict', foreground='red')
        self.target_tree.bind("<Double-Button-3>", self._on_target_tree_double_right_click)
        self.target_tree.bind("<Double-1>", self._on_target_tree_left_double_click)
        paned.add(target_frame, weight=1)
        
        bottom_frame = tb.Frame(self, padding=10)
        bottom_frame.pack(fill="x")
        btn_text = "Combine" if self.is_combine_mode else "Apply Changes"
        self.apply_btn = tb.Button(bottom_frame, text=btn_text, command=self.apply_changes, bootstyle="outline-success")
        self.apply_btn.pack(side="right", padx=5)
        tb.Button(bottom_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").pack(side="right")

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
        
        source_list = self.all_series
        
        for series in source_list:
            series_id = self.source_tree.insert("", "end", text=series.name, open=True)
            tv_root = self.parent_app.settings.get("tv_root", "")
            series_path = os.path.join(tv_root, series.name)
            self.source_tree.item(series_id, tags=(series_path,))
            self._populate_tree_from_path(self.source_tree, series_path, series_id)

        if not self.is_combine_mode:
            for item_id in self.source_tree.get_children(""):
                self.copy_tree_item(self.source_tree, item_id, "", self.target_tree)
        self._capture_state()
        
    def _populate_tree_from_path(self, tree, path, parent_id):
        try:
            for entry in sorted(os.listdir(path)):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    child_id = tree.insert(parent_id, "end", text=entry, open=False)
                    tree.item(child_id, tags=(full_path,))
                    self._populate_tree_from_path(tree, full_path, child_id)
                else:
                    item_id = tree.insert(parent_id, "end", text=entry)
                    tree.item(item_id, tags=(full_path,))
        except FileNotFoundError: pass

    def _on_tree_click(self, event):
        tree = event.widget
        item_id = tree.identify_row(event.y)
        if not item_id: return
        descendants = self._get_all_children(tree, item_id)
        selection = descendants + [item_id]
        current_selection = tree.selection()
        if all(item in current_selection for item in selection):
            tree.selection_remove(*selection)
        else:
            tree.selection_add(*selection)
    
    def _get_all_children(self, tree, item_id: str) -> List[str]:
        children = []
        for child_id in tree.get_children(item_id):
            children.append(child_id)
            children.extend(self._get_all_children(tree, child_id))
        return children

    def move_selection_to_season(self):
        self._capture_state()
        season_num = simpledialog.askinteger("Season Number", "Enter season number:", parent=self)
        if season_num is not None:
            self.move_selection_to_folder(f"Season {season_num:02d}")

    def move_selection_to_custom_folder(self):
        self._capture_state()
        folder_name = simpledialog.askstring("Folder Name", "Enter destination folder:", parent=self)
        if folder_name and folder_name.strip():
            self.move_selection_to_folder(folder_name.strip())

    def move_selection_to_folder(self, folder_name):
        self.structure_changed = True
        selection = self.source_tree.selection()
        if not selection: return
        target_folder_id = next((c for c in self.target_tree.get_children() if self.target_tree.item(c, "text") == folder_name), None)
        if not target_folder_id:
            target_folder_id = self.target_tree.insert("", "end", text=folder_name, open=True)

        files_to_move = self._collect_files_from_selection(selection)

        for source_path, basename in files_to_move:
            self.target_tree.insert(target_folder_id, "end", text=basename, tags=(source_path,))

        for item_id in selection:
             if self.source_tree.exists(item_id) and self.source_tree.parent(item_id) in selection:
                 continue
             if self.source_tree.exists(item_id):
                self.source_tree.delete(item_id)
        
        self._sort_target_tree()
        self._check_target_conflicts()
    
    def _collect_files_from_selection(self, selection: Tuple[str, ...]) -> List[Tuple[str, str]]:
        file_list = []
        seen_paths = set()
        for item_id in selection:
            tags = self.source_tree.item(item_id, "tags")
            if not tags: continue
            source_path = tags[0]
            if os.path.isdir(source_path):
                for root, _, files in os.walk(source_path):
                    for f in files:
                        full_path = os.path.join(root, f)
                        if full_path not in seen_paths:
                            file_list.append((full_path, f))
                            seen_paths.add(full_path)
            elif os.path.isfile(source_path):
                if source_path not in seen_paths:
                    file_list.append((source_path, os.path.basename(source_path)))
                    seen_paths.add(source_path)
        return file_list

    def copy_tree_item(self, from_tree, item_id, to_parent_id, to_tree):
        if not from_tree.exists(item_id): return
        text = from_tree.item(item_id, "text")
        tags = from_tree.item(item_id, "tags")
        is_open = from_tree.item(item_id, "open")
        new_item_id = to_tree.insert(to_parent_id, "end", text=text, tags=tags, open=is_open)
        for child_id in from_tree.get_children(item_id):
            self.copy_tree_item(from_tree, child_id, new_item_id, to_tree)

    def _on_target_tree_double_right_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if not item_id: return
        self._capture_state()
        self.structure_changed = True
        x, y, w, h = self.target_tree.bbox(item_id)
        entry = tb.Entry(self.target_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h + 10)
        entry.insert(0, self.target_tree.item(item_id, "text"))
        entry.focus()
        def save(e):
            self.target_tree.item(item_id, text=entry.get().strip())
            entry.destroy()
            self._check_target_conflicts()
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _on_target_tree_left_double_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if item_id:
            self.target_tree.item(item_id, open=not self.target_tree.item(item_id, "open"))

    def flatten_target(self):
        self._capture_state()
        self.structure_changed = True
        all_files = []
        def gather_files(item_id):
            tags = self.target_tree.item(item_id, "tags")
            if tags and os.path.isfile(tags[0]):
                all_files.append(item_id)
            for child_id in self.target_tree.get_children(item_id):
                gather_files(child_id)
        
        for root_id in self.target_tree.get_children(""):
            gather_files(root_id)
            
        items_to_re_add = [(self.target_tree.item(item_id, "text"), self.target_tree.item(item_id, "tags")) for item_id in all_files]
        self.target_tree.delete(*self.target_tree.get_children())
        for text, tags in items_to_re_add:
            self.target_tree.insert("", "end", text=text, tags=tags)
        
        self._check_target_conflicts()
    
    def _sort_target_tree(self):
        def sort_key(item_id):
            text = self.target_tree.item(item_id, "text")
            match = re.match(r'(?i)Season\s*(\d+)', text)
            if match:
                return (0, int(match.group(1)))
            if text.lower() == 'specials':
                return (1, 0)
            return (2, text.lower())

        items = list(self.target_tree.get_children(""))
        items.sort(key=sort_key)
        for i, item_id in enumerate(items):
            self.target_tree.move(item_id, "", i)

    def _check_target_conflicts(self):
        folder_contents: Dict[str, List[str]] = {}
        has_conflicts = False

        def gather_basenames(item_id, parent_folder_name):
            is_folder = bool(self.target_tree.get_children(item_id))
            item_text = self.target_tree.item(item_id, "text")
            if not is_folder:
                folder_contents.setdefault(parent_folder_name, []).append(item_text)
            else:
                for child_id in self.target_tree.get_children(item_id):
                    gather_basenames(child_id, item_text)
        
        for root_item_id in self.target_tree.get_children(""):
            if not self.target_tree.get_children(root_item_id):
                 gather_basenames(root_item_id, "__root__")
            else:
                 gather_basenames(root_item_id, self.target_tree.item(root_item_id, "text"))

        conflicts_by_folder: Dict[str, set] = {}
        for folder, files in folder_contents.items():
            counts = Counter(files)
            conflicts = {name for name, count in counts.items() if count > 1}
            if conflicts:
                conflicts_by_folder[folder] = conflicts
                has_conflicts = True

        def tag_conflicts(item_id, parent_folder_name):
            is_folder = bool(self.target_tree.get_children(item_id))
            item_text = self.target_tree.item(item_id, "text")
            current_tags = list(self.target_tree.item(item_id, "tags"))
            if 'conflict' in current_tags: current_tags.remove('conflict')
            if not is_folder:
                if parent_folder_name in conflicts_by_folder and item_text in conflicts_by_folder[parent_folder_name]:
                    current_tags.append('conflict')
            self.target_tree.item(item_id, tags=tuple(current_tags))
            if is_folder:
                for child_id in self.target_tree.get_children(item_id):
                    tag_conflicts(child_id, item_text)
        
        for root_item_id in self.target_tree.get_children(""):
             if not self.target_tree.get_children(root_item_id):
                 tag_conflicts(root_item_id, "__root__")
             else:
                 tag_conflicts(root_item_id, self.target_tree.item(root_item_id, "text"))

        self.apply_btn.config(state="disabled" if has_conflicts else "normal")


    def apply_changes(self):
        final_target_name = self.target_name_var.get().strip()
        if not final_target_name:
            messagebox.showerror("Invalid Name", "Final series name cannot be empty.")
            return

        tv_root = self.parent_app.settings.get("tv_root")
        
        if not self.is_combine_mode and not self.structure_changed and final_target_name != self.target_series.name:
            original_path = os.path.join(tv_root, self.target_series.name)
            final_path = os.path.join(tv_root, final_target_name)
            if os.path.exists(final_path):
                messagebox.showerror("Error", f"A folder named '{final_target_name}' already exists.")
                return
            all_moves = [(original_path, final_path)]
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
                for child_id in self.target_tree.get_children(item_id):
                    plan_moves_from_tree(child_id, current_path)

            final_series_path = os.path.join(tv_root, final_target_name)
            for top_item_id in self.target_tree.get_children(""):
                plan_moves_from_tree(top_item_id, final_series_path)
            
            description = f"Organize series: {final_target_name}"

        if not all_moves:
             messagebox.showinfo("Organize", "No changes to apply.")
             return
             
        if not messagebox.askyesno("Confirm Changes", f"Apply {len(all_moves)} file/folder operations?"):
            return
        
        failures = self.parent_app.perform_file_operation(all_moves, description)

        if not failures:
            source_folders_to_prune = {os.path.join(tv_root, s.name) for s in self.all_series}
            for path in source_folders_to_prune:
                prune_empty_dirs(path, stop_at=tv_root)

        if failures:
            messagebox.showerror("Operation Failed", "Some operations failed. Please review the changes.\n\n" + "\n".join(failures))
        
        self.destroy()
        self.parent_app.scan_root()


# -------------------------
# Entrypoint
# -------------------------
def main():
    settings = load_settings()
    app = JMADMediaTool(settings)
    app.mainloop()

if __name__ == "__main__":
    main()

