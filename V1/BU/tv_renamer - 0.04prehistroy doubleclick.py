# tv_renamer_0.04c.py
import os
import json
import re
import shutil
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
SETTINGS_FILE = "settings.json"

# -------------------- Data Classes -------------------- #
class Episode:
    def __init__(self, path, season=None, ep_num=None, title=None):
        self.path = path
        self.season = season
        self.ep_num = ep_num
        self.title = title or os.path.splitext(os.path.basename(path))[0]

class Season:
    def __init__(self, number):
        self.number = number  # int or str
        self.episodes = []

class Series:
    def __init__(self, name):
        self.name = name
        self.seasons = {}  # key: int or str -> Season
        self.unsorted = []

# -------------------- Settings -------------------- #
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    else:
        return {
            "tv_root": "",
            "staging": "",
            "parsing": "",
            "live": "",
            "theme": "darkly",
            "rename_format": "SxxExx"
        }

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

# -------------------- Undo Manager (multi-step) -------------------- #
class UndoManager:
    def __init__(self):
        # stack of actions, each action is list of (src, dst) pairs
        self.stack = []

    def push_action(self, action_list, description=None):
        """action_list: list of tuples (src, dst); description optional string"""
        self.stack.append({"moves": action_list.copy(), "desc": description})

    def undo_last(self):
        if not self.stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        action = self.stack.pop()
        moves = action["moves"]
        failures = []
        # reverse order: move dst -> src
        for src, dst in reversed(moves):
            try:
                if os.path.exists(dst):
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
                else:
                    failures.append((src, dst, "dst missing"))
            except Exception as e:
                failures.append((src, dst, str(e)))
        if failures:
            msg = "Undo completed with some failures:\n" + "\n".join(f"{s} <- {d}: {err}" for s,d,err in failures)
            messagebox.showwarning("Undo", msg)
        else:
            messagebox.showinfo("Undo", "Undo completed.")
        # caller should refresh tree/preview

    def clear(self):
        self.stack.clear()

# -------------------- Main App -------------------- #
class SeriesRenamer(tb.Window):
    def __init__(self, settings):
        # validate theme
        valid_themes = ["darkly","superhero","cosmo","flatly","minty"]
        theme = settings.get("theme","darkly")
        if theme not in valid_themes:
            theme = "darkly"
        super().__init__(themename=theme)
        self.title("TV Series Renamer 0.04c")
        self.geometry("1200x700")
        self.settings = settings
        self.series_list = []
        self.undo = UndoManager()

        self.setup_ui()
        if self.settings.get("tv_root"):
            self.scan_root()

    def setup_ui(self):
        # toolbar
        toolbar = tb.Frame(self, padding=5)
        toolbar.pack(side="top", fill="x")

        self.btn_parsing = tb.Button(toolbar, text="Move to Parsing", bootstyle="info", command=self.move_parsing)
        self.btn_parsing.pack(side="left", padx=2)
        self.btn_live = tb.Button(toolbar, text="Move to Live", bootstyle="info", command=self.move_live)
        self.btn_live.pack(side="left", padx=2)
        self.btn_rescan = tb.Button(toolbar, text="Rescan", bootstyle="info", command=self.scan_root)
        self.btn_rescan.pack(side="left", padx=2)
        self.btn_rename = tb.Button(toolbar, text="Rename Selected (Preview)", bootstyle="warning", command=self.rename_selected_preview)
        self.btn_rename.pack(side="left", padx=2)
        self.btn_settings = tb.Button(toolbar, text="Settings", bootstyle="secondary", command=self.open_settings)
        self.btn_settings.pack(side="left", padx=2)

        self.btn_undo = tb.Button(toolbar, text="Undo Last Action", bootstyle="danger", command=self.undo_and_refresh)
        self.btn_undo.pack(side="left", padx=8)

        self.btn_exit = tb.Button(toolbar, text="Exit", bootstyle="danger", command=self.destroy)
        self.btn_exit.pack(side="right", padx=2)

        # paned
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # left tree
        left_frame = tb.Frame(paned, padding=5)
        self.tree_series = ttk.Treeview(left_frame, columns=("count","status"), show="tree headings", selectmode="extended")
        self.tree_series.heading("#0", text="Series / Seasons / Episodes")
        self.tree_series.heading("count", text="Episodes")
        self.tree_series.heading("status", text="Status")
        self.tree_series.pack(fill="both", expand=True)
        self.tree_series.bind("<Button-3>", self.on_right_click)
        paned.add(left_frame, weight=3)

        # right preview
        right_frame = tb.Frame(paned, padding=5)
        self.tree_preview = ttk.Treeview(right_frame, columns=("current","new"), show="headings", selectmode="extended")
        self.tree_preview.heading("current", text="Current Filename")
        self.tree_preview.heading("new", text="New Filename")
        self.tree_preview.pack(fill="both", expand=True)
        paned.add(right_frame, weight=2)

    # ---------- scanning/parsing ----------
    def scan_root(self):
        tv_root = self.settings.get("tv_root")
        if not tv_root or not os.path.exists(tv_root):
            messagebox.showwarning("TV Root", "Please set a valid TV root folder in Settings.")
            return
        self.series_list.clear()
        self.tree_series.delete(*self.tree_series.get_children())
        for item in os.listdir(tv_root):
            s_path = os.path.join(tv_root, item)
            if os.path.isdir(s_path):
                s = Series(item)
                self.parse_series_folder(s, s_path)
                self.series_list.append(s)
        self.populate_tree()
        self.populate_preview()

    def parse_series_folder(self, series, path):
        # read entries
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                key = entry.strip()
                lmatch = entry.lower().replace(" ", "").replace("_","")
                if "season" in lmatch or (lmatch.startswith("s") and any(c.isdigit() for c in lmatch)):
                    try:
                        num = int("".join(filter(str.isdigit, lmatch)))
                    except:
                        num = 1
                    season = Season(num)
                    for ep in sorted(os.listdir(full)):
                        ep_path = os.path.join(full, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1] in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=num))
                    series.seasons[num] = season
                else:
                    # specials / movies / nested
                    season = Season(key)
                    for ep in sorted(os.listdir(full)):
                        ep_path = os.path.join(full, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1] in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=key))
                    series.seasons[key] = season
            else:
                if os.path.splitext(full)[1] in VIDEO_EXTS:
                    series.unsorted.append(Episode(full))

    # ---------- tree population ----------
    def populate_tree(self):
        self.tree_series.delete(*self.tree_series.get_children())
        for s in self.series_list:
            sid = self.tree_series.insert("", "end", text=s.name, values=("", ""))
            if not s.seasons:
                self.tree_series.item(sid, tags=("missing_season",))
            numeric = sorted([k for k in s.seasons.keys() if isinstance(k,int)])
            strings = sorted([k for k in s.seasons.keys() if isinstance(k,str)])
            order = numeric + strings
            for k in order:
                season = s.seasons[k]
                label = f"Season {k:02d}" if isinstance(k,int) else k
                seid = self.tree_series.insert(sid, "end", text=label, values=(len(season.episodes), ""))
                for ep in season.episodes:
                    self.tree_series.insert(seid, "end", text=ep.title, values=("",))
            for ep in s.unsorted:
                epid = self.tree_series.insert(sid, "end", text=ep.title, values=("", "Unsorted"))
                self.tree_series.item(epid, tags=("unsorted",))
        self.tree_series.tag_configure("missing_season", foreground="red")
        self.tree_series.tag_configure("unsorted", foreground="red")

    # ---------- preview ----------
    def populate_preview(self):
        self.tree_preview.delete(*self.tree_preview.get_children())
        pattern = re.compile(r"(S\d{1,2}E\d{1,2})", re.IGNORECASE)
        for s in self.series_list:
            for season in s.seasons.values():
                for ep in season.episodes:
                    # prefer extracting from filename/title
                    match = pattern.search(ep.title)
                    if match:
                        new_name = match.group(1).upper() + os.path.splitext(ep.path)[1]
                    else:
                        # fallback: if in numeric season and has index in listing, generate SxxExx using index
                        if isinstance(season.number, int):
                            # find index in season
                            try:
                                idx = season.episodes.index(ep) + 1
                                new_name = f"S{int(season.number):02d}E{int(idx):02d}" + os.path.splitext(ep.path)[1]
                            except:
                                new_name = os.path.basename(ep.path)
                        else:
                            new_name = os.path.basename(ep.path)
                    self.tree_preview.insert("", "end", values=(ep.title, new_name))

    # ---------- right-click ----------
    def on_right_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Series / Season / Episode", command=lambda: self.open_rename_dialog(item))
            menu.post(event.x_root, event.y_root)

    def open_rename_dialog(self, item):
        # get series root from selected item
        text = self.tree_series.item(item, "text")
        # find corresponding Series object by searching root or parent root
        # ensure we find top-level series name (if item is a season/episode get its series parent)
        parent = self.tree_series.parent(item)
        if parent:
            # walk up to find the topmost parent
            root_item = parent
            while self.tree_series.parent(root_item):
                root_item = self.tree_series.parent(root_item)
            series_name = self.tree_series.item(root_item, "text")
        else:
            series_name = text
        series_obj = next((x for x in self.series_list if x.name == series_name), None)
        if series_obj:
            dlg = RenameSeriesDialog(self, item, series_obj, self.settings, self.undo)
            self.wait_window(dlg)
            # after dialog closes, perform merges if series names collide
            self._merge_series_by_name()
            self.populate_tree()
            self.populate_preview()

    # ---------- merge series if same name ----------
    def _merge_series_by_name(self):
        # make a map name->series and merge duplicates
        name_map = {}
        to_remove = []
        for s in list(self.series_list):
            if s.name not in name_map:
                name_map[s.name] = s
            else:
                target = name_map[s.name]
                # merge seasons
                for k,v in s.seasons.items():
                    if k in target.seasons:
                        target.seasons[k].episodes.extend(v.episodes)
                    else:
                        target.seasons[k] = v
                # merge unsorted
                target.unsorted.extend(s.unsorted)
                to_remove.append(s)
        for s in to_remove:
            if s in self.series_list:
                self.series_list.remove(s)

    # ---------- toolbar actions: rename preview ----------
    def rename_selected_preview(self):
        sel = self.tree_preview.selection()
        if not sel:
            messagebox.showinfo("Rename", "No items selected in preview.")
            return
        if not messagebox.askyesno("Confirm", f"Rename {len(sel)} selected file(s) as shown?"):
            return
        action_group = []
        # for each selected preview row, find Episode object by title(path)
        for item in sel:
            current, new = self.tree_preview.item(item, "values")
            # find ep in data
            ep_found = None
            for s in self.series_list:
                for season in s.seasons.values():
                    for ep in season.episodes:
                        if ep.title == current:
                            ep_found = ep
                            break
                    if ep_found:
                        break
                if ep_found:
                    break
            if ep_found:
                src = ep_found.path
                dst = os.path.join(os.path.dirname(src), new)
                try:
                    if src != dst:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.move(src, dst)
                        action_group.append((src, dst))
                        ep_found.path = dst
                        ep_found.title = new
                except Exception as e:
                    messagebox.showwarning("Rename error", f"Failed to rename {src} -> {dst}\n{e}")
        if action_group:
            self.undo.push_action(action_group, description="Rename preview batch")
            messagebox.showinfo("Rename", "Rename completed.")
            self.populate_tree()
            self.populate_preview()

    # ---------- move parsing/live ----------
    def move_parsing(self):
        self._move_selected_in_tree_to(self.settings.get("parsing"), "parsing")

    def move_live(self):
        self._move_selected_in_tree_to(self.settings.get("live"), "live")

    def _move_selected_in_tree_to(self, target_root, label):
        if not target_root or not os.path.exists(target_root):
            messagebox.showwarning("Move", f"Target folder invalid: {target_root}")
            return
        selected = self.tree_series.selection()
        if not selected:
            messagebox.showinfo("Move", "Select series/seasons/episodes in the left tree to move.")
            return
        if not messagebox.askyesno("Confirm Move", f"Move {len(selected)} selected item(s) to {label}?"):
            return
        overall_actions = []
        for item in selected:
            # compute series name for the item (walk up to top-level)
            top = item
            while self.tree_series.parent(top):
                top = self.tree_series.parent(top)
            series_name = self.tree_series.item(top, "text")
            series_obj = next((s for s in self.series_list if s.name == series_name), None)
            if not series_obj:
                continue
            dest_series_folder = os.path.join(target_root, series_obj.name)
            os.makedirs(dest_series_folder, exist_ok=True)
            # if item is top-level series move entire thing
            if self.tree_series.parent(item) == "":
                # move entire series (seasons and unsorted)
                for season in series_obj.seasons.values():
                    season_label = f"Season {season.number}" if isinstance(season.number,int) else season.number
                    season_folder = os.path.join(dest_series_folder, season_label)
                    os.makedirs(season_folder, exist_ok=True)
                    for ep in season.episodes:
                        dst = os.path.join(season_folder, os.path.basename(ep.path))
                        try:
                            shutil.move(ep.path, dst)
                            overall_actions.append((ep.path, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed to move {ep.path} -> {dst}\n{e}")
                # unsorted
                if series_obj.unsorted:
                    ufold = os.path.join(dest_series_folder, "Unsorted")
                    os.makedirs(ufold, exist_ok=True)
                    for ep in series_obj.unsorted:
                        dst = os.path.join(ufold, os.path.basename(ep.path))
                        try:
                            shutil.move(ep.path, dst)
                            overall_actions.append((ep.path, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed to move {ep.path} -> {dst}\n{e}")
            else:
                # item could be season or episode; determine node text to find which
                item_text = self.tree_series.item(item,"text")
                parent_text = self.tree_series.item(self.tree_series.parent(item),"text") if self.tree_series.parent(item) else None
                # if parent is series and item is season -> move whole season
                if parent_text == series_name and item_text.lower().startswith("season"):
                    # find season number
                    label = item_text
                    # parse number heuristic
                    num = None
                    m = re.search(r"(\d+)", item_text)
                    if m:
                        num = int(m.group(1))
                    # find season object
                    season_obj = None
                    if num is not None and num in series_obj.seasons:
                        season_obj = series_obj.seasons[num]
                    elif item_text in series_obj.seasons:
                        season_obj = series_obj.seasons[item_text]
                    if season_obj:
                        season_folder = os.path.join(dest_series_folder, item_text)
                        os.makedirs(season_folder, exist_ok=True)
                        for ep in season_obj.episodes:
                            dst = os.path.join(season_folder, os.path.basename(ep.path))
                            try:
                                shutil.move(ep.path, dst)
                                overall_actions.append((ep.path, dst))
                                ep.path = dst
                            except Exception as e:
                                messagebox.showwarning("Move error", f"Failed to move {ep.path} -> {dst}\n{e}")
                else:
                    # likely episode node - move single episode into matching season under dest
                    # find episode by title under the series
                    moved_one = False
                    for season in series_obj.seasons.values():
                        for ep in season.episodes:
                            if ep.title == item_text:
                                # create season folder under dest
                                season_label = f"Season {season.number}" if isinstance(season.number,int) else season.number
                                season_folder = os.path.join(dest_series_folder, season_label)
                                os.makedirs(season_folder, exist_ok=True)
                                dst = os.path.join(season_folder, os.path.basename(ep.path))
                                try:
                                    shutil.move(ep.path, dst)
                                    overall_actions.append((ep.path, dst))
                                    ep.path = dst
                                    moved_one = True
                                except Exception as e:
                                    messagebox.showwarning("Move error", f"Failed to move {ep.path} -> {dst}\n{e}")
                                break
                        if moved_one:
                            break
                    if not moved_one:
                        # try unsorted
                        for ep in series_obj.unsorted:
                            if ep.title == item_text:
                                ufold = os.path.join(dest_series_folder, "Unsorted")
                                os.makedirs(ufold, exist_ok=True)
                                dst = os.path.join(ufold, os.path.basename(ep.path))
                                try:
                                    shutil.move(ep.path, dst)
                                    overall_actions.append((ep.path, dst))
                                    ep.path = dst
                                except Exception as e:
                                    messagebox.showwarning("Move error", f"Failed to move {ep.path} -> {dst}\n{e}")
                                break
        if overall_actions:
            self.undo.push_action(overall_actions, description=f"Move to {label}")
            messagebox.showinfo("Move", "Move completed.")
            self.populate_tree()
            self.populate_preview()

    # ---------- settings ----------
    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        self.wait_window(dlg)
        self.settings = dlg.settings
        save_settings(self.settings)
        valid_themes = ["darkly","superhero","cosmo","flatly","minty"]
        theme = self.settings.get("theme","darkly")
        if theme not in valid_themes:
            theme = "darkly"
        try:
            self.style.theme_use(theme)
        except Exception:
            pass

    # ---------- undo helpers ----------
    def undo_and_refresh(self):
        self.undo.undo_last()
        self.scan_root()

# -------------------- Rename GUI (enhanced) -------------------- #
class RenameSeriesDialog(tb.Toplevel):
    def __init__(self, parent, invoking_item, series_obj, settings, undo_manager):
        super().__init__(parent)
        self.parent = parent
        self.invoking_item = invoking_item
        self.series = series_obj
        self.settings = settings
        self.undo = undo_manager

        self.title(f"Rename / Organize: {self.series.name}")
        self.geometry("800x600")

        # Top: series name edit
        topf = tb.Frame(self)
        topf.pack(fill="x", padx=8, pady=6)
        tb.Label(topf, text="Series Name:").pack(side="left")
        self.series_name_var = tk.StringVar(value=self.series.name)
        self.series_name_entry = tb.Entry(topf, textvariable=self.series_name_var)
        self.series_name_entry.pack(side="left", fill="x", expand=True, padx=6)

        btnf = tb.Frame(topf)
        btnf.pack(side="right")
        tb.Button(btnf, text="Apply Rename (Series)", bootstyle="primary", command=self.apply_series_rename).pack(side="left", padx=4)
        tb.Button(btnf, text="Close", bootstyle="secondary", command=self.close).pack(side="left", padx=4)

        # Middle: seasons & episodes tree (allows multi-select)
        self.tree = tb.Treeview(self, columns=("info",), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Seasons / Episodes")
        self.tree.heading("info", text="Info")
        self.tree.column("info", width=160, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<Double-1>", self.on_double_rename)

        # bottom controls
        bottom = tb.Frame(self)
        bottom.pack(fill="x", padx=8, pady=6)
        tb.Button(bottom, text="Add Season", bootstyle="info", command=self.add_season).pack(side="left", padx=4)
        tb.Button(bottom, text="Move Selected to Folder", bootstyle="warning", command=self.move_selected_to_folder).pack(side="left", padx=4)
        tb.Button(bottom, text="Refresh", bootstyle="secondary", command=self.load_tree).pack(side="left", padx=4)

        self.load_tree()

    def load_tree(self):
        self.tree.delete(*self.tree.get_children())
        # show seasons first in numeric order then strings
        numeric = sorted([k for k in self.series.seasons.keys() if isinstance(k,int)])
        strings = sorted([k for k in self.series.seasons.keys() if isinstance(k,str)])
        order = numeric + strings
        for k in order:
            season = self.series.seasons[k]
            label = f"Season {k:02d}" if isinstance(k,int) else k
            sid = self.tree.insert("", "end", text=label, values=(f"{len(season.episodes)} eps",))
            for ep in season.episodes:
                self.tree.insert(sid, "end", text=ep.title, values=(os.path.basename(ep.path),))
        # unsorted
        if self.series.unsorted:
            usid = self.tree.insert("", "end", text="Unsorted", values=(f"{len(self.series.unsorted)} eps",))
            for ep in self.series.unsorted:
                self.tree.insert(usid, "end", text=ep.title, values=(os.path.basename(ep.path),))

    def on_double_rename(self, event):
        item = self.tree.focus()
        if not item:
            return
        current = self.tree.item(item, "text")
        new = simpledialog.askstring("Rename", "New name:", initialvalue=current)
        if not new:
            return
        parent = self.tree.parent(item)
        # If it's a season node (parent == ""), update season label (and if numeric, update season key)
        if parent == "":
            # Season rename: change key if numeric -> careful
            old_label = current
            # parse number if possible
            m = re.search(r"(\d+)", old_label)
            old_key = None
            if m:
                old_key = int(m.group(1))
            if old_key is not None and old_key in self.series.seasons:
                season_obj = self.series.seasons.pop(old_key)
                # if new is numeric, store as int else store as string
                mnew = re.search(r"(\d+)", new)
                if mnew:
                    new_key = int(mnew.group(1))
                else:
                    new_key = new
                self.series.seasons[new_key] = season_obj
            else:
                # string-based season rename
                if old_label in self.series.seasons:
                    season_obj = self.series.seasons.pop(old_label)
                    self.series.seasons[new] = season_obj
            # log nothing on label change alone (physical folder rename happens on save or apply)
            self.load_tree()
        else:
            # episode rename: only rename the display/title, not filesystem until save/apply
            # find episode object by title under the series
            found = False
            for season in self.series.seasons.values():
                for ep in season.episodes:
                    if ep.title == current:
                        ep.title = new
                        found = True
                        break
                if found:
                    break
            if not found:
                for ep in self.series.unsorted:
                    if ep.title == current:
                        ep.title = new
                        found = True
                        break
            self.load_tree()

    def add_season(self):
        new_num = simpledialog.askinteger("Add Season", "Season number:")
        if new_num is None:
            return
        if new_num in self.series.seasons:
            messagebox.showinfo("Add Season", "Season already exists.")
            return
        self.series.seasons[new_num] = Season(new_num)
        self.load_tree()

    def apply_series_rename(self):
        new_name = self.series_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("Rename", "Series name cannot be empty.")
            return
        old_name = self.series.name
        if old_name == new_name:
            messagebox.showinfo("Rename", "Name unchanged.")
            return
        # prepare move actions: move root folder old_name -> new_name
        tv_root = self.settings.get("tv_root")
        if not tv_root:
            messagebox.showwarning("Settings", "Set TV Root in settings before renaming.")
            return
        old_folder = os.path.join(tv_root, old_name)
        new_folder = os.path.join(tv_root, new_name)
        # if old_folder does not exist on disk, we may instead only mutate internal object and handle physical moves later.
        actions = []
        if os.path.exists(old_folder):
            # ensure new folder does not conflict; if exists, we'll move contents into it (merge)
            os.makedirs(new_folder, exist_ok=True)
            # move seasons and unsorted into new_folder
            # move each file and record action
            for k, season in list(self.series.seasons.items()):
                season_label = f"Season {k}" if isinstance(k,int) else k
                dest_season_folder = os.path.join(new_folder, season_label)
                os.makedirs(dest_season_folder, exist_ok=True)
                for ep in list(season.episodes):
                    src = ep.path
                    dst = os.path.join(dest_season_folder, os.path.basename(src))
                    if os.path.abspath(src) != os.path.abspath(dst):
                        try:
                            shutil.move(src, dst)
                            actions.append((src, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed moving {src} -> {dst}\n{e}")
            if self.series.unsorted:
                dest_unsorted = os.path.join(new_folder, "Unsorted")
                os.makedirs(dest_unsorted, exist_ok=True)
                for ep in list(self.series.unsorted):
                    src = ep.path
                    dst = os.path.join(dest_unsorted, os.path.basename(src))
                    if os.path.abspath(src) != os.path.abspath(dst):
                        try:
                            shutil.move(src, dst)
                            actions.append((src, dst))
                            ep.path = dst
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed moving {src} -> {dst}\n{e}")
            # once files moved, if old_folder empty remove it (best-effort)
            try:
                if os.path.exists(old_folder) and not os.listdir(old_folder):
                    os.rmdir(old_folder)
            except Exception:
                pass
        # update series name in-memory
        self.series.name = new_name
        # log actions for undo
        if actions:
            self.undo.push_action(actions, description=f"Rename series {old_name} -> {new_name}")
        messagebox.showinfo("Rename", f"Series renamed to '{new_name}'. Merge/move performed if folders existed on disk.")
        self.parent.populate_tree()
        self.parent.populate_preview()

    def move_selected_to_folder(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Move", "Select episode(s) (or season nodes) to move.")
            return
        folder_name = simpledialog.askstring("Target folder", "Folder name to create under series (e.g. Specials, Movies):")
        if not folder_name:
            return
        tv_root = self.settings.get("tv_root")
        if not tv_root:
            messagebox.showwarning("Settings", "Set TV Root in settings before moving.")
            return
        dest_base = os.path.join(tv_root, self.series.name, folder_name)
        os.makedirs(dest_base, exist_ok=True)
        actions = []
        # move episodes selected; if a season node selected, move all episodes in that season
        for item in selected:
            text = self.tree.item(item,"text")
            parent = self.tree.parent(item)
            if parent == "":
                # season node selected (or Unsorted)
                # find season key
                m = re.search(r"(\d+)", text)
                if m:
                    key = int(m.group(1))
                else:
                    key = text
                season = self.series.seasons.get(key)
                if season:
                    for ep in list(season.episodes):
                        src = ep.path
                        dst = os.path.join(dest_base, os.path.basename(src))
                        try:
                            shutil.move(src, dst)
                            actions.append((src, dst))
                            ep.path = dst
                            # also move ep object into a season named folder_name (string) under series
                        except Exception as e:
                            messagebox.showwarning("Move error", f"Failed moving {src} -> {dst}\n{e}")
                    # attach moved episodes into a new season key under series as folder_name
                    if folder_name not in self.series.seasons:
                        self.series.seasons[folder_name] = Season(folder_name)
                    # move ep objects from old season into new season list if they were moved
                    moved_titles = {os.path.basename(dst) for _,dst in actions}
                    # rebuild season.episodes removing moved ones
                    remaining = []
                    for ep in season.episodes:
                        if os.path.basename(ep.path) in moved_titles:
                            self.series.seasons[folder_name].episodes.append(ep)
                        else:
                            remaining.append(ep)
                    season.episodes = remaining
            else:
                # episode node selected
                ep_title = text
                # find episode in seasons or unsorted
                found = False
                for k, season in list(self.series.seasons.items()):
                    for ep in list(season.episodes):
                        if ep.title == ep_title:
                            src = ep.path
                            dst = os.path.join(dest_base, os.path.basename(src))
                            try:
                                shutil.move(src, dst)
                                actions.append((src, dst))
                                ep.path = dst
                                # remove from current season list and add to new
                                season.episodes.remove(ep)
                                if folder_name not in self.series.seasons:
                                    self.series.seasons[folder_name] = Season(folder_name)
                                self.series.seasons[folder_name].episodes.append(ep)
                                found = True
                                break
                            except Exception as e:
                                messagebox.showwarning("Move error", f"Failed moving {src} -> {dst}\n{e}")
                    if found:
                        break
                if not found:
                    for ep in list(self.series.unsorted):
                        if ep.title == ep_title:
                            src = ep.path
                            dst = os.path.join(dest_base, os.path.basename(src))
                            try:
                                shutil.move(src, dst)
                                actions.append((src, dst))
                                ep.path = dst
                                self.series.unsorted.remove(ep)
                                if folder_name not in self.series.seasons:
                                    self.series.seasons[folder_name] = Season(folder_name)
                                self.series.seasons[folder_name].episodes.append(ep)
                                found = True
                            except Exception as e:
                                messagebox.showwarning("Move error", f"Failed moving {src} -> {dst}\n{e}")
                            break
        if actions:
            self.undo.push_action(actions, description=f"Move selected to {folder_name} under {self.series.name}")
            messagebox.showinfo("Move", f"Moved {len(actions)} file(s) to {folder_name}.")
            self.load_tree()
            self.parent.populate_tree()
            self.parent.populate_preview()

    def close(self):
        self.destroy()

# -------------------- Settings Dialog -------------------- #
class SettingsDialog(tb.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.settings = settings
        self.title("Settings")
        self.geometry("520x420")

        tb.Label(self, text="TV Root Folder:").pack(pady=4)
        self.tv_var = tk.StringVar(value=self.settings.get("tv_root",""))
        tb.Entry(self, textvariable=self.tv_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle="info", command=self.browse_tv).pack(padx=10, pady=2)

        tb.Label(self, text="Staging Folder:").pack(pady=4)
        self.staging_var = tk.StringVar(value=self.settings.get("staging",""))
        tb.Entry(self, textvariable=self.staging_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle="info", command=self.browse_staging).pack(padx=10, pady=2)

        tb.Label(self, text="Parsing Folder:").pack(pady=4)
        self.parsing_var = tk.StringVar(value=self.settings.get("parsing",""))
        tb.Entry(self, textvariable=self.parsing_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle="info", command=self.browse_parsing).pack(padx=10, pady=2)

        tb.Label(self, text="Live Folder:").pack(pady=4)
        self.live_var = tk.StringVar(value=self.settings.get("live",""))
        tb.Entry(self, textvariable=self.live_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle="info", command=self.browse_live).pack(padx=10, pady=2)

        tb.Label(self, text="Theme:").pack(pady=4)
        self.theme_var = tk.StringVar(value=self.settings.get("theme","darkly"))
        tb.Combobox(self, textvariable=self.theme_var, values=["darkly","superhero","cosmo","flatly","minty"]).pack(fill="x", padx=10)

        tb.Label(self, text="Rename Format (not used for scrub mode):").pack(pady=4)
        self.rename_var = tk.StringVar(value=self.settings.get("rename_format","SxxExx"))
        tb.Entry(self, textvariable=self.rename_var).pack(fill="x", padx=10)

        btnf = tb.Frame(self)
        btnf.pack(pady=12)
        tb.Button(btnf, text="Save", bootstyle="success", command=self.save).pack(side="left", padx=6)
        tb.Button(btnf, text="Cancel", bootstyle="danger", command=self.destroy).pack(side="left", padx=6)

    def browse_tv(self):
        f = filedialog.askdirectory(title="Select TV Root Folder")
        if f: self.tv_var.set(f)
    def browse_staging(self):
        f = filedialog.askdirectory(title="Select Staging Folder")
        if f: self.staging_var.set(f)
    def browse_parsing(self):
        f = filedialog.askdirectory(title="Select Parsing Folder")
        if f: self.parsing_var.set(f)
    def browse_live(self):
        f = filedialog.askdirectory(title="Select Live Folder")
        if f: self.live_var.set(f)

    def save(self):
        self.settings["tv_root"] = self.tv_var.get()
        self.settings["staging"] = self.staging_var.get()
        self.settings["parsing"] = self.parsing_var.get()
        self.settings["live"] = self.live_var.get()
        self.settings["theme"] = self.theme_var.get()
        self.settings["rename_format"] = self.rename_var.get()
        self.destroy()

# -------------------- main -------------------- #
if __name__ == "__main__":
    settings = load_settings()
    app = SeriesRenamer(settings)
    app.mainloop()
