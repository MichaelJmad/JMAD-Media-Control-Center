# tv_renamer_0.04d.py
import os
import json
import re
import shutil
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# -------------------------
# Configuration / Constants
# -------------------------
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
SETTINGS_FILE = "settings.json"
VALID_THEMES = ["darkly", "superhero", "cosmo", "flatly", "minty"]

# -------------------------
# Data Models
# -------------------------
class Episode:
    def __init__(self, path, season=None, ep_num=None, title=None):
        self.path = path
        self.season = season
        self.ep_num = ep_num
        self.title = title or os.path.splitext(os.path.basename(path))[0]

class Season:
    def __init__(self, key):
        self.key = key  # int or str
        self.episodes = []

class Series:
    def __init__(self, name):
        self.name = name
        self.seasons = {}  # key -> Season
        self.unsorted = []

# -------------------------
# BatchAction & History
# -------------------------
class BatchAction:
    def __init__(self, description, moves=None, created_folders=None):
        """
        moves: list of (src, dst)
        created_folders: list of folder paths that were created by this action
        """
        self.description = description
        self.moves = moves or []
        self.created_folders = created_folders or []

class HistoryManager:
    def __init__(self):
        self.undo_stack = []  # list of BatchAction
        self.redo_stack = []  # list of BatchAction

    def push(self, action: BatchAction):
        self.undo_stack.append(action)
        self.redo_stack.clear()

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def undo(self):
        if not self.can_undo():
            return None
        action = self.undo_stack.pop()
        failures = []
        for src, dst in reversed(action.moves):
            try:
                if os.path.exists(dst):
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
                else:
                    failures.append((src, dst, "dst missing"))
            except Exception as e:
                failures.append((src, dst, str(e)))
        for folder in action.created_folders:
            try:
                if os.path.isdir(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except Exception:
                pass
        self.redo_stack.append(action)
        return failures

    def redo(self):
        if not self.can_redo():
            return None
        action = self.redo_stack.pop()
        failures = []
        for src, dst in action.moves:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.move(src, dst)
                else:
                    failures.append((src, dst, "src missing"))
            except Exception as e:
                failures.append((src, dst, str(e)))
        for folder in action.created_folders:
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        self.undo_stack.append(action)
        return failures

    def list_history(self):
        return [a.description for a in self.undo_stack]

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

# -------------------------
# Settings helpers
# -------------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
                defaults = {
                    "tv_root": "",
                    "staging": "",
                    "parsing": "",
                    "live": "",
                    "theme": "darkly",
                    "rename_format": "SxxExx",
                    "show_history_by_default": False,
                    "history_undocked_by_default": False
                }
                defaults.update(s)
                if defaults["theme"] not in VALID_THEMES:
                    defaults["theme"] = "darkly"
                return defaults
        except Exception:
            pass
    return {
        "tv_root": "",
        "staging": "",
        "parsing": "",
        "live": "",
        "theme": "darkly",
        "rename_format": "SxxExx",
        "show_history_by_default": False,
        "history_undocked_by_default": False
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        messagebox.showwarning("Settings", f"Failed to save settings: {e}")

# -------------------------
# Main Application
# -------------------------
class TVRenamerApp(tb.Window):
    def __init__(self, settings):
        theme = settings.get("theme", "darkly")
        if theme not in VALID_THEMES:
            theme = "darkly"
        super().__init__(themename=theme)
        self.title("TV Renamer 0.04d")
        self.geometry("1200x700")

        self.settings = settings
        self.history = HistoryManager()
        self.series_list = []

        # history panel state
        self.history_docked = not bool(settings.get("history_undocked_by_default", False))
        self.history_visible = bool(settings.get("show_history_by_default", False))
        self.history_toplevel = None

        # drag state used in rename dialog only (kept for compatibility)
        self._dragging = {"start": None, "widget": None}

        self._build_ui()

        if self.settings.get("tv_root"):
            self.scan_root()

    # -------------------------
    # UI Construction
    # -------------------------
    def _build_ui(self):
        toolbar = tb.Frame(self, padding=6)
        toolbar.pack(side="top", fill="x")

        self.btn_parsing = tb.Button(toolbar, text="Move to Parsing", bootstyle="info", command=self.move_to_parsing)
        self.btn_parsing.pack(side="left", padx=3)
        self.btn_live = tb.Button(toolbar, text="Move to Live", bootstyle="info", command=self.move_to_live)
        self.btn_live.pack(side="left", padx=3)
        self.btn_rescan = tb.Button(toolbar, text="Rescan", bootstyle="info", command=self.scan_root)
        self.btn_rescan.pack(side="left", padx=3)
        self.btn_rename_preview = tb.Button(toolbar, text="Rename Selected (Preview)", bootstyle="warning", command=self.rename_selected_preview)
        self.btn_rename_preview.pack(side="left", padx=3)
        self.btn_settings = tb.Button(toolbar, text="Settings", bootstyle="secondary", command=self.open_settings)
        self.btn_settings.pack(side="left", padx=8)

        self.btn_undo = tb.Button(toolbar, text="Undo", bootstyle="danger", command=self.undo_action)
        self.btn_undo.pack(side="left", padx=3)
        self.btn_redo = tb.Button(toolbar, text="Redo", bootstyle="secondary", command=self.redo_action)
        self.btn_redo.pack(side="left", padx=3)

        self.btn_view_history = tb.Button(toolbar, text="Toggle History Panel", bootstyle="secondary", command=self.toggle_history_panel)
        self.btn_view_history.pack(side="left", padx=8)

        self.btn_exit = tb.Button(toolbar, text="Exit", bootstyle="danger", command=self.destroy)
        self.btn_exit.pack(side="right", padx=3)

        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=6, pady=6)

        left_frame = tb.Frame(main_paned, padding=4)
        self.tree_series = ttk.Treeview(left_frame, columns=("count", "status"), show="tree headings", selectmode="extended")
        self.tree_series.heading("#0", text="Series / Seasons / Episodes")
        self.tree_series.heading("count", text="Episodes")
        self.tree_series.heading("status", text="Status")
        self.tree_series.pack(fill="both", expand=True, side="left")
        vs_left = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_series.yview)
        vs_left.pack(side="right", fill="y")
        self.tree_series.configure(yscrollcommand=vs_left.set)
        self.tree_series.bind("<Button-3>", self.on_series_right_click)
        self.tree_series.bind("<Double-1>", self.on_series_double_click)
        main_paned.add(left_frame, weight=3)

        right_paned = ttk.PanedWindow(main_paned, orient="vertical")
        main_paned.add(right_paned, weight=4)

        preview_frame = tb.Frame(right_paned, padding=4)
        self.tree_preview = ttk.Treeview(preview_frame, columns=("current", "new"), show="headings", selectmode="extended")
        self.tree_preview.heading("current", text="Current Filename")
        self.tree_preview.heading("new", text="New Filename")
        self.tree_preview.pack(fill="both", expand=True, side="left")
        vs_preview = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree_preview.yview)
        vs_preview.pack(side="right", fill="y")
        self.tree_preview.configure(yscrollcommand=vs_preview.set)
        self.tree_preview.bind("<Double-1>", self.on_preview_edit)
        right_paned.add(preview_frame, weight=2)

        history_frame = tb.Frame(right_paned, padding=4)
        self.history_listbox = tk.Listbox(history_frame, activestyle="none")
        self.history_listbox.pack(fill="both", expand=True, side="left")
        vs_hist = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_listbox.yview)
        vs_hist.pack(side="right", fill="y")
        self.history_listbox.configure(yscrollcommand=vs_hist.set)
        self.history_listbox.bind("<Button-3>", self.on_history_right_click)
        self.history_listbox.bind("<Double-1>", self.on_history_double)
        hist_btn_frame = tb.Frame(history_frame)
        hist_btn_frame.pack(fill="x")
        tb.Button(hist_btn_frame, text="Pop Out History (Undock)", bootstyle="secondary", command=self.undock_history).pack(side="left", padx=6, pady=6)
        tb.Button(hist_btn_frame, text="Clear History", bootstyle="danger", command=self.clear_history_confirm).pack(side="right", padx=6, pady=6)
        right_paned.add(history_frame, weight=1)

        self.main_paned = main_paned
        self.right_paned = right_paned
        self.preview_frame = preview_frame
        self.history_frame = history_frame

        if not self.history_visible:
            self.after(50, lambda: self.right_paned.forget(history_frame))

        self.bind_all("<Control-z>", lambda e: self.undo_action())
        self.bind_all("<Control-y>", lambda e: self.redo_action())

        self._dragging = {"start": None, "widget": None}
        self.tree_series.tag_configure("unsorted", foreground="red")
        self.tree_series.tag_configure("missing_season", foreground="red")

    # -------------------------
    # Scanning & Parsing
    # -------------------------
    def scan_root(self):
        tv_root = self.settings.get("tv_root")
        if not tv_root or not os.path.exists(tv_root):
            messagebox.showwarning("TV Root", "Please set a valid TV root folder in Settings.")
            return
        self.series_list.clear()
        self.tree_series.delete(*self.tree_series.get_children())

        for item in sorted(os.listdir(tv_root)):
            s_path = os.path.join(tv_root, item)
            if os.path.isdir(s_path):
                series = Series(item)
                self._parse_series_folder(series, s_path)
                self.series_list.append(series)

        self.populate_tree()
        self.populate_preview()
        self.refresh_history_list()

    def _parse_series_folder(self, series: Series, path):
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                low = entry.lower().replace(" ", "").replace("_", "")
                if "season" in low or (low.startswith("s") and any(c.isdigit() for c in low)):
                    digits = "".join(filter(str.isdigit, low))
                    try:
                        num = int(digits) if digits else 1
                    except:
                        num = 1
                    season = Season(num)
                    for ep in sorted(os.listdir(full)):
                        ep_path = os.path.join(full, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1].lower() in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=num))
                    series.seasons[num] = season
                else:
                    key = entry
                    season = Season(key)
                    for ep in sorted(os.listdir(full)):
                        ep_path = os.path.join(full, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1].lower() in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=key))
                    series.seasons[key] = season
            else:
                if os.path.splitext(full)[1].lower() in VIDEO_EXTS:
                    series.unsorted.append(Episode(full))

    # -------------------------
    # Tree & Preview Population
    # -------------------------
    def populate_tree(self):
        self.tree_series.delete(*self.tree_series.get_children())
        for s in self.series_list:
            sid = self.tree_series.insert("", "end", text=s.name, values=("", ""))
            if not s.seasons:
                self.tree_series.item(sid, tags=("missing_season",))
            numeric = sorted([k for k in s.seasons.keys() if isinstance(k, int)])
            strings = sorted([k for k in s.seasons.keys() if isinstance(k, str)])
            order = numeric + strings
            for k in order:
                sec = s.seasons[k]
                label = f"Season {k:02d}" if isinstance(k, int) else k
                seid = self.tree_series.insert(sid, "end", text=label, values=(len(sec.episodes), ""))
                for ep in sec.episodes:
                    self.tree_series.insert(seid, "end", text=ep.title, values=("",))
            if s.unsorted:
                usid = self.tree_series.insert(sid, "end", text="Unsorted", values=(len(s.unsorted), "Unsorted"))
                for ep in s.unsorted:
                    self.tree_series.insert(usid, "end", text=ep.title, values=(os.path.basename(ep.path),))
        self.tree_series.tag_configure("missing_season", foreground="red")
        self.tree_series.tag_configure("unsorted", foreground="red")

    def populate_preview(self):
        self.tree_preview.delete(*self.tree_preview.get_children())
        pattern = re.compile(r"(S\d{1,2}E\d{1,2})", re.IGNORECASE)
        for s in self.series_list:
            for sec in s.seasons.values():
                for idx, ep in enumerate(sec.episodes, start=1):
                    match = pattern.search(ep.title)
                    if match:
                        new = match.group(1).upper() + os.path.splitext(ep.path)[1]
                    else:
                        if isinstance(sec.key, int):
                            new = f"S{sec.key:02d}E{idx:02d}" + os.path.splitext(ep.path)[1]
                        else:
                            new = os.path.basename(ep.path)
                    self.tree_preview.insert("", "end", values=(ep.title, new))

    # -------------------------
    # Helpers
    # -------------------------
    def find_episode_by_title(self, title):
        for s in self.series_list:
            for sec in s.seasons.values():
                for ep in sec.episodes:
                    if ep.title == title:
                        return ep, s, sec
            for ep in s.unsorted:
                if ep.title == title:
                    return ep, s, None
        return None, None, None

    def refresh_history_list(self):
        if self.history_toplevel and hasattr(self, "history_undocked_listbox"):
            lb = self.history_undocked_listbox
            lb.delete(0, tk.END)
            for idx, a in enumerate(self.history.undo_stack):
                lb.insert(tk.END, f"{idx+1}: {a.description}")
        else:
            self.history_listbox.delete(0, tk.END)
            for idx, a in enumerate(self.history.undo_stack):
                self.history_listbox.insert(tk.END, f"{idx+1}: {a.description}")

    # -------------------------
    # Toolbar actions: rename preview
    # -------------------------
    def rename_selected_preview(self):
        sel = self.tree_preview.selection()
        if not sel:
            messagebox.showinfo("Rename", "No preview rows selected.")
            return
        if not messagebox.askyesno("Confirm", f"Rename {len(sel)} selected file(s)?"):
            return
        moves = []
        created_folders = set()
        for item in sel:
            cur, newname = self.tree_preview.item(item, "values")
            ep, series_obj, sec_obj = self.find_episode_by_title(cur)
            if not ep:
                continue
            src = ep.path
            dst = os.path.join(os.path.dirname(src), newname)
            if os.path.abspath(src) == os.path.abspath(dst):
                continue
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                moves.append((src, dst))
                ep.path = dst
                ep.title = newname
            except Exception as e:
                messagebox.showwarning("Rename error", f"Failed: {src} -> {dst}\n{e}")
        if moves:
            action = BatchAction(description=f"Rename preview batch ({len(moves)} files)", moves=moves, created_folders=list(created_folders))
            self.history.push(action)
            self.refresh_history_list()
            messagebox.showinfo("Rename", "Rename completed.")
            self.populate_tree()
            self.populate_preview()

    # -------------------------
    # Move Selected (left tree) (used for Move to Parsing/Live)
    # -------------------------
    def move_to_parsing(self):
        self._move_selected_in_tree_to(self.settings.get("parsing"), "parsing")

    def move_to_live(self):
        self._move_selected_in_tree_to(self.settings.get("live"), "live")

    def _move_selected_in_tree_to(self, target_root, label):
        if not target_root:
            messagebox.showwarning("Move", "Target folder not set in Settings.")
            return
        if not os.path.exists(target_root):
            messagebox.showwarning("Move", f"Target folder does not exist: {target_root}")
            return
        selected = self.tree_series.selection()
        if not selected:
            messagebox.showinfo("Move", "No items selected in the left tree.")
            return
        if not messagebox.askyesno("Confirm", f"Move {len(selected)} selected item(s) to {label}?"):
            return

        moves = []
        created_folders = set()
        for it in selected:
            top = it
            while self.tree_series.parent(top):
                top = self.tree_series.parent(top)
            series_name = self.tree_series.item(top, "text")
            series_obj = next((x for x in self.series_list if x.name == series_name), None)
            if not series_obj:
                continue
            dest_series_folder = os.path.join(target_root, series_obj.name)
            os.makedirs(dest_series_folder, exist_ok=True)
            created_folders.add(dest_series_folder)
            if self.tree_series.parent(it) == "":
                for sec in series_obj.seasons.values():
                    season_label = f"Season {sec.key}" if isinstance(sec.key, int) else sec.key
                    dest_season_folder = os.path.join(dest_series_folder, season_label)
                    os.makedirs(dest_season_folder, exist_ok=True)
                    created_folders.add(dest_season_folder)
                    for ep in list(sec.episodes):
                        src = ep.path
                        dst = os.path.join(dest_season_folder, os.path.basename(src))
                        try:
                            shutil.move(src, dst)
                            moves.append((src, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed: {src} -> {dst}\n{e}")
                if series_obj.unsorted:
                    dest_uns = os.path.join(dest_series_folder, "Unsorted")
                    os.makedirs(dest_uns, exist_ok=True)
                    created_folders.add(dest_uns)
                    for ep in list(series_obj.unsorted):
                        src = ep.path
                        dst = os.path.join(dest_uns, os.path.basename(src))
                        try:
                            shutil.move(src, dst)
                            moves.append((src, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed: {src} -> {dst}\n{e}")
            else:
                it_text = self.tree_series.item(it, "text")
                parent_text = self.tree_series.item(self.tree_series.parent(it), "text") if self.tree_series.parent(it) else None
                if parent_text == series_name and it_text.lower().startswith("season"):
                    m = re.search(r"(\d+)", it_text)
                    key = int(m.group(1)) if m else it_text
                    sec = series_obj.seasons.get(key)
                    if sec:
                        season_folder = os.path.join(dest_series_folder, it_text)
                        os.makedirs(season_folder, exist_ok=True)
                        created_folders.add(season_folder)
                        for ep in list(sec.episodes):
                            src = ep.path
                            dst = os.path.join(season_folder, os.path.basename(src))
                            try:
                                shutil.move(src, dst)
                                moves.append((src, dst))
                                ep.path = dst
                            except Exception as e:
                                messagebox.showwarning("Move error", f"Failed: {src} -> {dst}\n{e}")
                else:
                    ep_title = it_text
                    found = False
                    for sec in series_obj.seasons.values():
                        for ep in sec.episodes:
                            if ep.title == ep_title:
                                season_folder = os.path.join(dest_series_folder, f"Season {sec.key}" if isinstance(sec.key, int) else sec.key)
                                os.makedirs(season_folder, exist_ok=True)
                                created_folders.add(season_folder)
                                dst = os.path.join(season_folder, os.path.basename(ep.path))
                                try:
                                    shutil.move(ep.path, dst)
                                    moves.append((ep.path, dst))
                                    ep.path = dst
                                    found = True
                                except Exception as e:
                                    messagebox.showwarning("Move error", f"Failed: {ep.path} -> {dst}\n{e}")
                                break
                        if found:
                            break
                    if not found:
                        for ep in series_obj.unsorted:
                            if ep.title == ep_title:
                                dest_uns = os.path.join(dest_series_folder, "Unsorted")
                                os.makedirs(dest_uns, exist_ok=True)
                                created_folders.add(dest_uns)
                                dst = os.path.join(dest_uns, os.path.basename(ep.path))
                                try:
                                    shutil.move(ep.path, dst)
                                    moves.append((ep.path, dst))
                                    ep.path = dst
                                except Exception as e:
                                    messagebox.showwarning("Move error", f"Failed: {ep.path} -> {dst}\n{e}")
        if moves:
            action = BatchAction(description=f"Move to {label} ({len(moves)} files)", moves=moves, created_folders=list(created_folders))
            self.history.push(action)
            self.refresh_history_list()
            messagebox.showinfo("Move", "Move completed.")
            self.populate_tree()
            self.populate_preview()

    # -------------------------
    # Undo / Redo handlers
    # -------------------------
    def undo_action(self):
        failures = self.history.undo()
        if failures is None:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        if failures:
            txt = "\n".join(f"{s} <- {d}: {e}" for s,d,e in failures)
            messagebox.showwarning("Undo Some Failures", txt)
        else:
            messagebox.showinfo("Undo", "Undo completed.")
        self.refresh_history_list()
        self.scan_root()

    def redo_action(self):
        failures = self.history.redo()
        if failures is None:
            messagebox.showinfo("Redo", "Nothing to redo.")
            return
        if failures:
            txt = "\n".join(f"{s} -> {d}: {e}" for s,d,e in failures)
            messagebox.showwarning("Redo Some Failures", txt)
        else:
            messagebox.showinfo("Redo", "Redo completed.")
        self.refresh_history_list()
        self.scan_root()

    # -------------------------
    # History panel handlers
    # -------------------------
    def toggle_history_panel(self):
        if self.history_toplevel:
            self.dock_history()
            return
        if self.history_visible:
            try:
                self.right_paned.forget(self.history_frame)
            except Exception:
                pass
            self.history_visible = False
        else:
            try:
                self.right_paned.add(self.history_frame, weight=1)
            except Exception:
                pass
            self.history_visible = True
        if self.history_visible and not self.history_docked and not self.history_toplevel:
            self.undock_history()
        self.refresh_history_list()

    def undock_history(self):
        if self.history_toplevel:
            return
        try:
            self.right_paned.forget(self.history_frame)
        except Exception:
            pass
        top = tb.Toplevel(self)
        top.title("History")
        top.geometry("600x400")
        listbox = tk.Listbox(top, activestyle="none")
        listbox.pack(fill="both", expand=True, side="left")
        vs = ttk.Scrollbar(top, orient="vertical", command=listbox.yview)
        vs.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=vs.set)
        for idx, a in enumerate(self.history.undo_stack):
            listbox.insert(tk.END, f"{idx+1}: {a.description}")
        listbox.bind("<Button-3>", lambda e, lb=listbox: self.on_history_right_click_undocked(e, lb))
        listbox.bind("<Double-1>", lambda e, lb=listbox: self.on_history_double_undocked(e, lb))
        self.history_toplevel = top
        self.history_undocked_listbox = listbox
        def on_close():
            self.dock_history()
        top.protocol("WM_DELETE_WINDOW", on_close)

    def dock_history(self):
        if not self.history_toplevel:
            if not self.history_visible:
                self.right_paned.add(self.history_frame, weight=1)
                self.history_visible = True
            return
        try:
            self.history_toplevel.destroy()
        except Exception:
            pass
        self.history_toplevel = None
        if not self.history_visible:
            self.right_paned.add(self.history_frame, weight=1)
            self.history_visible = True
        self.refresh_history_list()

    def refresh_history_list(self):
        if self.history_toplevel and hasattr(self, "history_undocked_listbox"):
            lb = self.history_undocked_listbox
            lb.delete(0, tk.END)
            for idx, a in enumerate(self.history.undo_stack):
                lb.insert(tk.END, f"{idx+1}: {a.description}")
        else:
            self.history_listbox.delete(0, tk.END)
            for idx, a in enumerate(self.history.undo_stack):
                self.history_listbox.insert(tk.END, f"{idx+1}: {a.description}")

    def on_history_right_click(self, event):
        idx = self.history_listbox.nearest(event.y)
        if idx < 0:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Undo to Here", command=lambda i=idx: self.undo_to_index(i))
        menu.add_command(label="Redo to Here", command=lambda i=idx: self.redo_to_index(i))
        menu.post(event.x_root, event.y_root)

    def on_history_right_click_undocked(self, event, listbox):
        idx = listbox.nearest(event.y)
        if idx < 0:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Undo to Here", command=lambda i=idx: (self.undo_to_index(i), self.refresh_history_list()))
        menu.add_command(label="Redo to Here", command=lambda i=idx: (self.redo_to_index(i), self.refresh_history_list()))
        menu.post(event.x_root, event.y_root)

    def on_history_double(self, event):
        idxs = self.history_listbox.curselection()
        if idxs:
            self.undo_to_index(idxs[0])

    def on_history_double_undocked(self, event, listbox):
        idxs = listbox.curselection()
        if idxs:
            self.undo_to_index(idxs[0])
            self.refresh_history_list()

    def clear_history_confirm(self):
        if messagebox.askyesno("Clear History", "Clear all undo/redo history?"):
            self.history.clear()
            self.refresh_history_list()
            messagebox.showinfo("History", "History cleared.")

    def undo_to_index(self, idx):
        while len(self.history.undo_stack) > idx:
            self.undo_action()
        self.refresh_history_list()

    def redo_to_index(self, idx):
        while len(self.history.undo_stack) <= idx and self.history.can_redo():
            self.redo_action()
        self.refresh_history_list()

    # -------------------------
    # Series tree handlers
    # -------------------------
    def on_series_right_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if not item:
            return
        self.tree_series.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Rename Series / Season / Episode", command=lambda it=item: self.open_rename_dialog(it))
        menu.add_command(label="Select All Under Node", command=lambda it=item: self.select_all_under(it))
        menu.add_separator()
        menu.add_command(label="Move Selected to Season...", command=lambda: self.context_move_selected_to_season(item))
        menu.add_separator()
        menu.add_command(label="Undo Last", command=self.undo_action)
        menu.add_command(label="Redo Last", command=self.redo_action)
        menu.post(event.x_root, event.y_root)

    def on_series_double_click(self, event):
        item = self.tree_series.focus()
        if not item:
            return
        if self.tree_series.get_children(item):
            self.tree_series.item(item, open=not self.tree_series.item(item, "open"))

    def select_all_under(self, item):
        def gather(it):
            ids = []
            for ch in self.tree_series.get_children(it):
                ids.append(ch)
                ids.extend(gather(ch))
            return ids
        ids = [item] + gather(item)
        self.tree_series.selection_set(ids)

    def context_move_selected_to_season(self, item):
        top = item
        while self.tree_series.parent(top):
            top = self.tree_series.parent(top)
        series_name = self.tree_series.item(top, "text")
        series_obj = next((s for s in self.series_list if s.name == series_name), None)
        if not series_obj:
            return
        options = []
        numeric = sorted([k for k in series_obj.seasons.keys() if isinstance(k,int)])
        strings = sorted([k for k in series_obj.seasons.keys() if isinstance(k,str)])
        for k in numeric:
            options.append(f"Season {k:02d}")
        for k in strings:
            options.append(str(k))
        options.append("<<Create New Season...>>")
        choice = simpledialog.askstring("Move to Season", "Enter season name/number (e.g. Season 01) or <<Create New Season...>>:", initialvalue=options[0] if options else "")
        if not choice:
            return
        if choice == "<<Create New Season...>>":
            newnum = simpledialog.askinteger("New Season", "Enter numeric season number (or cancel):")
            if newnum is None:
                return
            target_label = f"Season {newnum:02d}"
            target_key = newnum
        else:
            m = re.search(r"(\d+)", choice)
            if m:
                target_key = int(m.group(1))
                target_label = f"Season {target_key:02d}"
            else:
                target_key = choice
                target_label = choice
        self._move_selected_tree_items_to_season(series_obj, target_key, target_label)

    def _move_selected_tree_items_to_season(self, series_obj: Series, target_key, target_label):
        sel = self.tree_series.selection()
        if not sel:
            messagebox.showinfo("Move", "No items selected")
            return
        tv_root = self.settings.get("tv_root")
        if not tv_root:
            messagebox.showwarning("Settings", "Set TV Root first.")
            return
        dest_season_folder = os.path.join(tv_root, series_obj.name, target_label)
        os.makedirs(dest_season_folder, exist_ok=True)
        created_folders = {dest_season_folder}
        moves = []
        for it in sel:
            text = self.tree_series.item(it, "text")
            if text == "Unsorted" and self.tree_series.parent(it) and self.tree_series.item(self.tree_series.parent(it), "text") == series_obj.name:
                for ep in list(series_obj.unsorted):
                    src = ep.path
                    dst = os.path.join(dest_season_folder, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                        series_obj.unsorted.remove(ep)
                        if target_key not in series_obj.seasons:
                            series_obj.seasons[target_key] = Season(target_key)
                        series_obj.seasons[target_key].episodes.append(ep)
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
            else:
                ep_title = text
                ep, s_obj, sec_obj = self.find_episode_by_title(ep_title)
                if ep and s_obj.name == series_obj.name:
                    src = ep.path
                    dst = os.path.join(dest_season_folder, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                        if sec_obj:
                            sec_obj.episodes.remove(ep)
                        else:
                            if ep in series_obj.unsorted:
                                series_obj.unsorted.remove(ep)
                        if target_key not in series_obj.seasons:
                            series_obj.seasons[target_key] = Season(target_key)
                        series_obj.seasons[target_key].episodes.append(ep)
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
        if moves:
            action = BatchAction(description=f"Move {len(moves)} files into {series_obj.name}/{target_label}", moves=moves, created_folders=list(created_folders))
            self.history.push(action)
            self.refresh_history_list()
            messagebox.showinfo("Move", "Move completed.")
            self.populate_tree()
            self.populate_preview()

    # -------------------------
    # Rename / Organize dialog
    # -------------------------
    def open_rename_dialog(self, item):
        top = item
        while self.tree_series.parent(top):
            top = self.tree_series.parent(top)
        series_name = self.tree_series.item(top, "text")
        series_obj = next((s for s in self.series_list if s.name == series_name), None)
        if not series_obj:
            return
        dlg = RenameDialog(self, series_obj, self.settings, self.history)
        self.wait_window(dlg)
        self._merge_series_by_name()
        self.populate_tree()
        self.populate_preview()
        self.refresh_history_list()

    def _merge_series_by_name(self):
        name_map = {}
        to_remove = []
        for s in list(self.series_list):
            if s.name not in name_map:
                name_map[s.name] = s
            else:
                tgt = name_map[s.name]
                for k, v in s.seasons.items():
                    if k in tgt.seasons:
                        tgt.seasons[k].episodes.extend(v.episodes)
                    else:
                        tgt.seasons[k] = v
                tgt.unsorted.extend(s.unsorted)
                to_remove.append(s)
        for r in to_remove:
            if r in self.series_list:
                self.series_list.remove(r)

    # -------------------------
    # Preview edit handler
    # -------------------------
    def on_preview_edit(self, event):
        item = self.tree_preview.focus()
        if not item:
            return
        cur, new = self.tree_preview.item(item, "values")
        newname = simpledialog.askstring("Edit New Filename", "New filename:", initialvalue=new)
        if not newname:
            return
        self.tree_preview.item(item, values=(cur, newname))

    # -------------------------
    # Rename Selected Helpers (RenameDialog)
    # -------------------------
    def _merge_series_files_if_needed(self):
        pass  # placeholder if needed later

    # -------------------------
    # Settings GUI
    # -------------------------
    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        self.wait_window(dlg)
        self.settings = dlg.settings
        save_settings(self.settings)
        theme = self.settings.get("theme", "darkly")
        if theme not in VALID_THEMES:
            theme = "darkly"
        try:
            self.style.theme_use(theme)
        except Exception:
            pass
        # if user changed default history visibility, update panel
        self.history_visible = bool(self.settings.get("show_history_by_default", False))
        self.history_docked = not bool(self.settings.get("history_undocked_by_default", False))
        # ensure UI reflects settings (user can rescan)
        self.scan_root()

# -------------------------
# Rename / Organize Dialog (with drag/drop & context menu)
# -------------------------
class RenameDialog(tb.Toplevel):
    def __init__(self, parent: TVRenamerApp, series_obj: Series, settings, history: HistoryManager):
        super().__init__(parent)
        self.parent_app = parent
        self.series = series_obj
        self.settings = settings
        self.history = history
        self.title(f"Rename / Organize: {self.series.name}")
        self.geometry("900x600")

        topf = tb.Frame(self)
        topf.pack(fill="x", padx=8, pady=6)
        tb.Label(topf, text="Series Name:").pack(side="left")
        self.series_name_var = tk.StringVar(value=self.series.name)
        self.series_name_entry = tb.Entry(topf, textvariable=self.series_name_var)
        self.series_name_entry.pack(side="left", fill="x", expand=True, padx=6)
        tb.Button(topf, text="Apply Series Rename", bootstyle="primary", command=self.apply_series_rename).pack(side="left", padx=6)
        tb.Button(topf, text="Close", bootstyle="secondary", command=self.close).pack(side="left", padx=6)

        center = tb.Frame(self)
        center.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree = ttk.Treeview(center, columns=("info",), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Seasons / Episodes")
        self.tree.heading("info", text="Info")
        self.tree.column("info", width=180, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        vs = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)

        self.load_tree()
        self.tree.bind("<Double-1>", self.on_double_rename)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<ButtonPress-1>", self.on_tree_button_press)
        self.tree.bind("<B1-Motion>", self.on_tree_drag)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_drop)

        bottom = tb.Frame(self)
        bottom.pack(fill="x", padx=8, pady=6)
        tb.Button(bottom, text="Add Season", bootstyle="info", command=self.add_season).pack(side="left", padx=4)
        tb.Button(bottom, text="Move Selected to Folder", bootstyle="warning", command=self.move_selected_to_folder).pack(side="left", padx=4)
        tb.Button(bottom, text="Refresh", bootstyle="secondary", command=self.load_tree).pack(side="left", padx=4)
        self.status_var = tk.StringVar(value="")
        tb.Label(bottom, textvariable=self.status_var).pack(side="right")
        self._drag_src_items = None

    def load_tree(self):
        self.tree.delete(*self.tree.get_children())
        numeric = sorted([k for k in self.series.seasons.keys() if isinstance(k, int)])
        strings = sorted([k for k in self.series.seasons.keys() if isinstance(k, str)])
        order = numeric + strings
        for k in order:
            sec = self.series.seasons[k]
            label = f"Season {k:02d}" if isinstance(k, int) else k
            sid = self.tree.insert("", "end", text=label, values=(f"{len(sec.episodes)} eps",))
            for ep in sec.episodes:
                self.tree.insert(sid, "end", text=ep.title, values=(os.path.basename(ep.path),))
        if self.series.unsorted:
            usid = self.tree.insert("", "end", text="Unsorted", values=(f"{len(self.series.unsorted)} eps",))
            for ep in self.series.unsorted:
                self.tree.insert(usid, "end", text=ep.title, values=(os.path.basename(ep.path),))

    def on_double_rename(self, event):
        item = self.tree.focus()
        if not item:
            return
        cur = self.tree.item(item, "text")
        new = simpledialog.askstring("Rename", "New name:", initialvalue=cur)
        if not new:
            return
        if self.tree.parent(item) == "":
            m = re.search(r"(\d+)", cur)
            old_key = int(m.group(1)) if m else cur
            if old_key in self.series.seasons:
                sec_obj = self.series.seasons.pop(old_key)
                mnew = re.search(r"(\d+)", new)
                new_key = int(mnew.group(1)) if mnew else new
                self.series.seasons[new_key] = sec_obj
            else:
                if cur in self.series.seasons:
                    sec_obj = self.series.seasons.pop(cur)
                    self.series.seasons[new] = sec_obj
            self.load_tree()
        else:
            ep_title = cur
            ep, s_obj, sec_obj = self.parent_app.find_episode_by_title(ep_title)
            if ep:
                ep.title = new
            self.load_tree()

    def on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Rename Node", command=lambda it=item: self.rename_node(it))
        menu.add_separator()
        menu.add_command(label="Move Selected to Season...", command=self.move_selected_to_folder)
        menu.add_command(label="Move Selected to Specials", command=lambda: self.move_selected_to_named_folder("Specials"))
        menu.add_command(label="Move Selected to Movies", command=lambda: self.move_selected_to_named_folder("Movies"))
        menu.add_separator()
        menu.add_command(label="Undo Last", command=self.parent_app.undo_action)
        menu.add_command(label="Redo Last", command=self.parent_app.redo_action)
        menu.post(event.x_root, event.y_root)

    def rename_node(self, item):
        cur = self.tree.item(item, "text")
        new = simpledialog.askstring("Rename", "New name:", initialvalue=cur)
        if not new:
            return
        self.on_double_rename(None)

    def add_season(self):
        val = simpledialog.askinteger("Add Season", "Season number:")
        if val is None:
            return
        if val in self.series.seasons:
            messagebox.showinfo("Add Season", "Season exists")
            return
        self.series.seasons[val] = Season(val)
        self.load_tree()

    # Drag & Drop (simple)
    def on_tree_button_press(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            self._drag_src_items = None
            return
        sel = self.tree.selection()
        if item not in sel:
            sel = (item,)
            self.tree.selection_set(sel)
        self._drag_src_items = sel
        self.status_var.set(f"Drag started: {len(sel)} item(s)")

    def on_tree_drag(self, event):
        if self._drag_src_items:
            self.status_var.set(f"Dragging {len(self._drag_src_items)} item(s)...")

    def on_tree_drop(self, event):
        if not self._drag_src_items:
            return
        target = self.tree.identify_row(event.y)
        if not target:
            self.status_var.set("Drop cancelled (no target)")
            self._drag_src_items = None
            return
        if self.tree.parent(target) == "":
            target_text = self.tree.item(target, "text")
            m = re.search(r"(\d+)", target_text)
            if m:
                key = int(m.group(1))
            else:
                key = target_text
            top = target
            while self.tree.parent(top):
                top = self.tree.parent(top)
            series_name = self.tree.item(top, "text")
            series_obj = next((s for s in self.parent_app.series_list if s.name == series_name), None)
            if not series_obj:
                self._drag_src_items = None
                return
            self.parent_app._move_selected_tree_items_to_season(series_obj, key, target_text)
            self._drag_src_items = None
            self.load_tree()
        else:
            self.status_var.set("Drop target must be a season node (or top-level)")
            self._drag_src_items = None

    def move_selected_to_folder(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Move", "No items selected.")
            return
        folder_name = simpledialog.askstring("Target Folder", "Folder name under series (e.g. Specials):")
        if not folder_name:
            return
        self.move_selected_to_named_folder(folder_name)

    def move_selected_to_named_folder(self, folder_name):
        tv_root = self.settings.get("tv_root")
        if not tv_root:
            messagebox.showwarning("Settings", "Set TV Root before moving.")
            return
        dest_base = os.path.join(tv_root, self.series.name, folder_name)
        os.makedirs(dest_base, exist_ok=True)
        created_folders = {dest_base}
        moves = []
        sel = self.tree.selection()
        for item in sel:
            text = self.tree.item(item, "text")
            if text == "Unsorted":
                for ep in list(self.series.unsorted):
                    src = ep.path
                    dst = os.path.join(dest_base, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                        self.series.unsorted.remove(ep)
                        if folder_name not in self.series.seasons:
                            self.series.seasons[folder_name] = Season(folder_name)
                        self.series.seasons[folder_name].episodes.append(ep)
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
            else:
                ep_title = text
                ep, s_obj, sec_obj = self.parent_app.find_episode_by_title(ep_title)
                if ep and s_obj.name == self.series.name:
                    src = ep.path
                    dst = os.path.join(dest_base, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                        if sec_obj:
                            sec_obj.episodes.remove(ep)
                        else:
                            if ep in self.series.unsorted:
                                self.series.unsorted.remove(ep)
                        if folder_name not in self.series.seasons:
                            self.series.seasons[folder_name] = Season(folder_name)
                        self.series.seasons[folder_name].episodes.append(ep)
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
        if moves:
            action = BatchAction(description=f"Move {len(moves)} files to {self.series.name}/{folder_name}", moves=moves, created_folders=list(created_folders))
            self.history.push(action)
            self.parent_app.refresh_history_list()
            messagebox.showinfo("Move", f"Moved {len(moves)} files to {folder_name}.")
            self.load_tree()
            self.parent_app.populate_tree()
            self.parent_app.populate_preview()

    def apply_series_rename(self):
        new_name = self.series_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("Rename", "Series name cannot be empty.")
            return
        old_name = self.series.name
        if old_name == new_name:
            messagebox.showinfo("Rename", "Name unchanged.")
            return
        tv_root = self.settings.get("tv_root")
        if not tv_root:
            messagebox.showwarning("Settings", "Set TV Root first.")
            return
        old_folder = os.path.join(tv_root, old_name)
        new_folder = os.path.join(tv_root, new_name)
        moves = []
        created_folders = set()
        if os.path.exists(old_folder):
            os.makedirs(new_folder, exist_ok=True)
            created_folders.add(new_folder)
            for key, sec in list(self.series.seasons.items()):
                season_label = f"Season {key}" if isinstance(key, int) else str(key)
                dst_season = os.path.join(new_folder, season_label)
                os.makedirs(dst_season, exist_ok=True)
                created_folders.add(dst_season)
                for ep in list(sec.episodes):
                    src = ep.path
                    dst = os.path.join(dst_season, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
            if self.series.unsorted:
                dst_uns = os.path.join(new_folder, "Unsorted")
                os.makedirs(dst_uns, exist_ok=True)
                created_folders.add(dst_uns)
                for ep in list(self.series.unsorted):
                    src = ep.path
                    dst = os.path.join(dst_uns, os.path.basename(src))
                    try:
                        shutil.move(src, dst)
                        moves.append((src, dst))
                        ep.path = dst
                    except Exception as e:
                        messagebox.showwarning("Move error", f"{src} -> {dst}: {e}")
            try:
                if os.path.isdir(old_folder) and not os.listdir(old_folder):
                    os.rmdir(old_folder)
            except Exception:
                pass
        self.series.name = new_name
        if moves or created_folders:
            action = BatchAction(description=f"Rename series {old_name} -> {new_name}", moves=moves, created_folders=list(created_folders))
            self.history.push(action)
            self.parent_app.refresh_history_list()
        messagebox.showinfo("Rename", f"Series renamed to {new_name}.")
        self.parent_app._merge_series_by_name()
        self.parent_app.populate_tree()
        self.parent_app.populate_preview()
        self.load_tree()

    def close(self):
        self.destroy()

# -------------------------
# Settings Dialog
# -------------------------
class SettingsDialog(tb.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent = parent
        self.settings = dict(settings)
        self.title("Settings")
        self.geometry("540x480")

        f = tb.Frame(self)
        f.pack(fill="both", expand=True, padx=8, pady=8)

        tb.Label(f, text="TV Root Folder:").grid(row=0, column=0, sticky="w")
        self.tv_var = tk.StringVar(value=self.settings.get("tv_root",""))
        tb.Entry(f, textvariable=self.tv_var).grid(row=0, column=1, sticky="ew", padx=6)
        tb.Button(f, text="Browse", bootstyle="info", command=self.browse_tv).grid(row=0, column=2, padx=6)

        tb.Label(f, text="Staging Folder:").grid(row=1, column=0, sticky="w")
        self.staging_var = tk.StringVar(value=self.settings.get("staging",""))
        tb.Entry(f, textvariable=self.staging_var).grid(row=1, column=1, sticky="ew", padx=6)
        tb.Button(f, text="Browse", bootstyle="info", command=self.browse_staging).grid(row=1, column=2, padx=6)

        tb.Label(f, text="Parsing Folder:").grid(row=2, column=0, sticky="w")
        self.parsing_var = tk.StringVar(value=self.settings.get("parsing",""))
        tb.Entry(f, textvariable=self.parsing_var).grid(row=2, column=1, sticky="ew", padx=6)
        tb.Button(f, text="Browse", bootstyle="info", command=self.browse_parsing).grid(row=2, column=2, padx=6)

        tb.Label(f, text="Live Folder:").grid(row=3, column=0, sticky="w")
        self.live_var = tk.StringVar(value=self.settings.get("live",""))
        tb.Entry(f, textvariable=self.live_var).grid(row=3, column=1, sticky="ew", padx=6)
        tb.Button(f, text="Browse", bootstyle="info", command=self.browse_live).grid(row=3, column=2, padx=6)

        tb.Label(f, text="Theme:").grid(row=4, column=0, sticky="w")
        self.theme_var = tk.StringVar(value=self.settings.get("theme","darkly"))
        cmb = ttk.Combobox(f, textvariable=self.theme_var, values=VALID_THEMES, state="readonly")
        cmb.grid(row=4, column=1, sticky="ew", padx=6)

        tb.Label(f, text="Rename Format:").grid(row=5, column=0, sticky="w")
        self.rename_var = tk.StringVar(value=self.settings.get("rename_format","SxxExx"))
        tb.Entry(f, textvariable=self.rename_var).grid(row=5, column=1, sticky="ew", padx=6)

        self.show_history_var = tk.BooleanVar(value=self.settings.get("show_history_by_default", False))
        tb.Checkbutton(f, text="Show History Panel by default", variable=self.show_history_var).grid(row=6, column=1, sticky="w", pady=6)

        self.undock_history_var = tk.BooleanVar(value=self.settings.get("history_undocked_by_default", False))
        tb.Checkbutton(f, text="Undock History Panel by default", variable=self.undock_history_var).grid(row=7, column=1, sticky="w", pady=6)

        f.columnconfigure(1, weight=1)

        btnf = tb.Frame(self)
        btnf.pack(fill="x", padx=8, pady=8)
        tb.Button(btnf, text="Save", bootstyle="success", command=self.save).pack(side="left", padx=6)
        tb.Button(btnf, text="Cancel", bootstyle="danger", command=self.destroy).pack(side="left", padx=6)

    def browse_tv(self):
        p = filedialog.askdirectory(title="Select TV Root Folder")
        if p: self.tv_var.set(p)
    def browse_staging(self):
        p = filedialog.askdirectory(title="Select Staging Folder")
        if p: self.staging_var.set(p)
    def browse_parsing(self):
        p = filedialog.askdirectory(title="Select Parsing Folder")
        if p: self.parsing_var.set(p)
    def browse_live(self):
        p = filedialog.askdirectory(title="Select Live Folder")
        if p: self.live_var.set(p)

    def save(self):
        self.settings["tv_root"] = self.tv_var.get()
        self.settings["staging"] = self.staging_var.get()
        self.settings["parsing"] = self.parsing_var.get()
        self.settings["live"] = self.live_var.get()
        theme = self.theme_var.get()
        if theme not in VALID_THEMES:
            theme = "darkly"
        self.settings["theme"] = theme
        self.settings["rename_format"] = self.rename_var.get()
        self.settings["show_history_by_default"] = bool(self.show_history_var.get())
        self.settings["history_undocked_by_default"] = bool(self.undock_history_var.get())
        self.destroy()

# -------------------------
# Main run
# -------------------------
if __name__ == "__main__":
    settings = load_settings()
    app = TVRenamerApp(settings)
    app.mainloop()
