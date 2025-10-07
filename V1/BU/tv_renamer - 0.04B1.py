# tv_renamer_0.06.py
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
        self.series_name = "" # Will be set by parent

class Season:
    def __init__(self, key):
        self.key = key  # int or str
        self.episodes = []

class Series:
    def __init__(self, name):
        self.name = name
        self.seasons = {}  # key -> Season
        self.unsorted = []
        
    def get_all_episodes(self):
        all_eps = []
        for season in self.seasons.values():
            all_eps.extend(season.episodes)
        all_eps.extend(self.unsorted)
        return all_eps

# -------------------------
# BatchAction & History
# -------------------------
class BatchAction:
    def __init__(self, description, moves=None, created_folders=None):
        self.description = description
        self.moves = moves or []
        self.created_folders = created_folders or []

class HistoryManager:
    def __init__(self):
        self.history_log = [] # List of (BatchAction, status_str)
        self.current_pos = -1

    def push(self, action: BatchAction):
        # When a new action is pushed, truncate any "redo" history
        if self.current_pos < len(self.history_log) - 1:
            self.history_log = self.history_log[:self.current_pos + 1]
        self.history_log.append((action, "new"))
        self.current_pos += 1

    def can_undo(self):
        return self.current_pos >= 0

    def can_redo(self):
        return self.current_pos < len(self.history_log) - 1

    def undo(self, stop_at=None):
        if not self.can_undo():
            return None, None
        
        action, status = self.history_log[self.current_pos]
        failures = []
        prune_candidates = set()
        for src, dst in reversed(action.moves):
            try:
                if os.path.exists(dst):
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    shutil.move(dst, src)
                    prune_candidates.add(os.path.dirname(dst))
                else:
                    failures.append((src, dst, "dst missing"))
            except Exception as e:
                failures.append((src, dst, str(e)))

        for path in prune_candidates:
            prune_empty_dirs(path, stop_at=stop_at)
        
        self.history_log[self.current_pos] = (action, "undone")
        self.current_pos -= 1
        return failures, action

    def redo(self, stop_at=None):
        if not self.can_redo():
            return None, None
            
        self.current_pos += 1
        action, status = self.history_log[self.current_pos]
        failures = []
        prune_candidates = set()
        
        for src, dst in action.moves:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    prune_candidates.add(os.path.dirname(src))
                else:
                    failures.append((src, dst, "src missing"))
            except Exception as e:
                failures.append((src, dst, str(e)))
        
        for folder in action.created_folders:
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        
        for path in prune_candidates:
            prune_empty_dirs(path, stop_at=stop_at)
            
        self.history_log[self.current_pos] = (action, "redone")
        return failures, action

    def clear(self):
        self.history_log.clear()
        self.current_pos = -1

# -------------------------
# Settings helpers
# -------------------------

def load_settings():
    defaults = {
        "tv_root": "", "staging": "", "parsing": "", "live": "",
        "theme": "darkly", "rename_format": "SxxExx",
        "show_history_by_default": False, "history_undocked_by_default": False
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                defaults.update(settings)
                if defaults["theme"] not in VALID_THEMES:
                    defaults["theme"] = "darkly"
        except (json.JSONDecodeError, IOError):
            pass
    return defaults

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        messagebox.showwarning("Settings", f"Failed to save settings: {e}")

# -------------------------
# Filesystem helpers
# -------------------------

def prune_empty_dirs(path: str, stop_at: str | None = None):
    try:
        path = os.path.abspath(path)
        if stop_at:
            stop_at = os.path.abspath(stop_at)
        while os.path.isdir(path):
            if os.listdir(path):
                break
            if stop_at and os.path.samefile(path, stop_at):
                break
            parent = os.path.dirname(path)
            os.rmdir(path)
            path = parent
    except Exception:
        pass

# -------------------------
# Main Application
# -------------------------
class TVRenamerApp(tb.Window):
    def __init__(self, settings):
        theme = settings.get("theme", "darkly")
        super().__init__(themename=theme)
        self.title("TV Renamer")
        self.geometry("1280x760")

        self.settings = settings
        self.history = HistoryManager()
        self.series_list = []
        self.series_map = {}

        self.history_docked = not bool(settings.get("history_undocked_by_default", False))
        self.history_visible = bool(settings.get("show_history_by_default", False))
        self.history_toplevel = None
        self.history_undocked_listbox = None

        self._build_ui()
        if self.settings.get("tv_root"):
            self.scan_root()

    def _build_ui(self):
        toolbar = tb.Frame(self, padding=6)
        toolbar.pack(side="top", fill="x")

        tb.Button(toolbar, text="Move to Parsing", bootstyle="info", command=self.move_to_parsing).pack(side="left", padx=3)
        tb.Button(toolbar, text="Move to Live", bootstyle="info", command=self.move_to_live).pack(side="left", padx=3)
        tb.Button(toolbar, text="Rescan", bootstyle="primary", command=self.scan_root).pack(side="left", padx=3)
        tb.Button(toolbar, text="Settings", bootstyle="secondary", command=self.open_settings).pack(side="left", padx=8)
        tb.Button(toolbar, text="Show History", bootstyle="secondary", command=self.toggle_history_panel).pack(side="left", padx=8)

        self.btn_exit = tb.Button(toolbar, text="Exit", bootstyle="danger", command=self.destroy)
        self.btn_exit.pack(side="right", padx=3)

        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=6, pady=6)

        left_frame = tb.Frame(main_paned, padding=4)
        self.tree_series = ttk.Treeview(left_frame, columns=("count", "status"), show="tree headings", selectmode="extended")
        self.tree_series.heading("#0", text="Series / Seasons")
        self.tree_series.heading("count", text="Episodes")
        self.tree_series.heading("status", text="Status")
        self.tree_series.pack(fill="both", expand=True, side="left")
        vs_left = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_series.yview)
        vs_left.pack(side="right", fill="y")
        self.tree_series.configure(yscrollcommand=vs_left.set)
        self.tree_series.bind("<Button-3>", self.on_series_right_click)
        self.tree_series.bind("<Double-1>", self.on_series_double_click)
        self.tree_series.bind("<<TreeviewSelect>>", self.update_preview_for_selection)
        main_paned.add(left_frame, weight=3)

        right_paned = ttk.PanedWindow(main_paned, orient="vertical")
        main_paned.add(right_paned, weight=4)
        
        # Define paned windows before creating children that need to reference them
        self.main_paned = main_paned
        self.right_paned = right_paned

        preview_frame = tb.Frame(right_paned, padding=4)
        self.tree_preview = ttk.Treeview(preview_frame, columns=("current", "new"), show="headings", selectmode="extended")
        self.tree_preview.heading("current", text="Current Filename")
        self.tree_preview.heading("new", text="New Filename")
        self.tree_preview.pack(fill="both", expand=True, side="left")
        vs_preview = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree_preview.yview)
        vs_preview.pack(side="right", fill="y")
        self.tree_preview.configure(yscrollcommand=vs_preview.set)
        right_paned.add(preview_frame, weight=2)

        self.history_frame = self._create_history_panel(right_paned)
        right_paned.add(self.history_frame, weight=1)

        if not self.history_visible:
            self.after(50, lambda: self.right_paned.forget(self.history_frame))

        self.bind_all("<Control-z>", lambda e: self.undo_action())
        self.bind_all("<Control-y>", lambda e: self.redo_action())

        self.tree_series.tag_configure("missing_season", foreground="red")
        
    def _create_history_panel(self, parent):
        frame = tb.Frame(parent, padding=(4,0))

        header = tb.Frame(frame)
        header.pack(fill="x")
        tb.Label(header, text="History", font="-weight bold").pack(side="left")
        
        undock_button = tb.Button(header, text="Undock", bootstyle="link", command=self.undock_history)
        undock_button.pack(side="right")
        
        if parent == self.right_paned:
            self.undock_btn = undock_button

        tb.Separator(frame, orient="horizontal").pack(fill="x", pady=2)
        
        list_container = tb.Frame(frame)
        list_container.pack(fill="both", expand=True)
        listbox = tk.Listbox(list_container, activestyle="none", selectbackground=self.style.colors.primary)
        listbox.pack(fill="both", expand=True, side="left")
        vs_hist = ttk.Scrollbar(list_container, orient="vertical", command=listbox.yview)
        vs_hist.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=vs_hist.set)
        
        footer = tb.Frame(frame)
        footer.pack(fill="x", pady=(4,0))
        tb.Button(footer, text="Undo", bootstyle="danger-outline", command=self.undo_action).pack(side="left", padx=2)
        tb.Button(footer, text="Redo", bootstyle="secondary-outline", command=self.redo_action).pack(side="left", padx=2)
        tb.Button(footer, text="Clear", bootstyle="warning-outline", command=self.clear_history_confirm).pack(side="right", padx=2)

        if parent == self.right_paned:
            self.history_listbox = listbox
        
        return frame

    def scan_root(self):
        tv_root = self.settings.get("tv_root")
        if not tv_root or not os.path.exists(tv_root):
            messagebox.showwarning("TV Root", "Please set a valid TV root folder in Settings.")
            return
            
        self.series_list.clear()
        self.series_map.clear()
        self.tree_series.delete(*self.tree_series.get_children())

        for item in sorted(os.listdir(tv_root)):
            s_path = os.path.join(tv_root, item)
            if os.path.isdir(s_path):
                series = Series(item)
                self._parse_series_folder(series, s_path)
                self.series_list.append(series)
                self.series_map[item] = series

        self.populate_tree()
        self.update_preview_for_selection()
        self.refresh_history_list()
        
    def _parse_series_folder(self, series: Series, path):
        for entry in sorted(os.listdir(path)):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                m = re.match(r'(?i)season\s*(\d+)', entry)
                key = int(m.group(1)) if m else entry
                season = Season(key)
                for ep_file in sorted(os.listdir(full_path)):
                    ep_path = os.path.join(full_path, ep_file)
                    if os.path.splitext(ep_path)[1].lower() in VIDEO_EXTS:
                        episode = Episode(ep_path, season=key)
                        episode.series_name = series.name
                        season.episodes.append(episode)
                series.seasons[key] = season
            elif os.path.splitext(full_path)[1].lower() in VIDEO_EXTS:
                episode = Episode(full_path)
                episode.series_name = series.name
                series.unsorted.append(episode)

    def populate_tree(self):
        self.tree_series.delete(*self.tree_series.get_children())
        for s in sorted(self.series_list, key=lambda x: x.name):
            sid = self.tree_series.insert("", "end", text=s.name, values=("", ""), open=False)
            if not s.seasons and not s.unsorted:
                self.tree_series.item(sid, tags=("missing_season",))
            
            sorted_keys = sorted(s.seasons.keys(), key=lambda k: (isinstance(k, str), k))
            for k in sorted_keys:
                sec = s.seasons[k]
                label = f"Season {k:02d}" if isinstance(k, int) else k
                self.tree_series.insert(sid, "end", text=label, values=(len(sec.episodes), ""))
            if s.unsorted:
                self.tree_series.insert(sid, "end", text="Unsorted", values=(len(s.unsorted), "Unsorted"))

    def update_preview_for_selection(self, event=None):
        self.tree_preview.delete(*self.tree_preview.get_children())
        selected_items = self.tree_series.selection()
        if not selected_items:
            return

        episodes_to_show = []
        for item_id in selected_items:
            parent_id = self.tree_series.parent(item_id)
            item_text = self.tree_series.item(item_id, "text")

            if not parent_id:
                series = self.series_map.get(item_text)
                if series: episodes_to_show.extend(series.get_all_episodes())
            else:
                series_name = self.tree_series.item(parent_id, "text")
                series = self.series_map.get(series_name)
                if series:
                    if item_text == "Unsorted":
                        episodes_to_show.extend(series.unsorted)
                    else:
                        m = re.search(r'(\d+)', item_text)
                        try:
                            key_type_is_int = isinstance(next(iter(series.seasons.keys())), int)
                            key = int(m.group(1)) if m and key_type_is_int else item_text
                            if key in series.seasons:
                                episodes_to_show.extend(series.seasons[key].episodes)
                        except StopIteration: # No seasons
                            pass
        
        for ep in sorted(list(set(episodes_to_show)), key=lambda x: x.path):
            new_name = os.path.basename(ep.path)
            if isinstance(ep.season, int):
                # This is a placeholder for a real renaming engine
                new_name = f"{ep.series_name} - S{ep.season:02d}Exx{os.path.splitext(ep.path)[1]}"
            self.tree_preview.insert("", "end", values=(os.path.basename(ep.path), new_name))
            
    def undo_action(self):
        failures, action = self.history.undo(stop_at=self.settings.get("tv_root"))
        if action is None: return
        if failures: messagebox.showwarning("Undo Failed", "Could not undo some files.")
        self.refresh_history_list()
        self.scan_root()

    def redo_action(self):
        failures, action = self.history.redo(stop_at=self.settings.get("tv_root"))
        if action is None: return
        if failures: messagebox.showwarning("Redo Failed", "Could not redo some files.")
        self.refresh_history_list()
        self.scan_root()

    def refresh_history_list(self):
        listbox = self.history_undocked_listbox if self.history_toplevel else self.history_listbox
        if not listbox: return
            
        listbox.delete(0, tk.END)
        for i, (action, status) in enumerate(self.history.history_log):
            prefix = ""
            if status == "undone": prefix = "[UNDO] "
            elif status == "redone": prefix = "[REDO] "
            
            listbox.insert(tk.END, f"{prefix}{action.description}")
            if status == "undone":
                listbox.itemconfig(i, {'fg': 'grey'})
            else:
                listbox.itemconfig(i, {'fg': self.style.colors.fg})

        if self.history.can_undo():
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(self.history.current_pos)
            listbox.see(self.history.current_pos)

    def clear_history_confirm(self):
        if messagebox.askyesno("Clear History", "Clear all undo/redo history? This cannot be undone."):
            self.history.clear()
            self.refresh_history_list()

    def find_episode_by_title(self, title):
        # Helper to find episode objects from their title (basename)
        for series in self.series_list:
            for episode in series.get_all_episodes():
                if os.path.basename(episode.path) == title:
                    return episode
        return None

    def rename_selected_preview(self):
        sel = self.tree_preview.selection()
        if not sel:
            messagebox.showinfo("Rename", "No files selected in the preview panel.")
            return
        if not messagebox.askyesno("Confirm Rename", f"Rename {len(sel)} selected file(s)?"):
            return
        moves = []
        created_folders = set()
        prune_candidates = set()
        for item in sel:
            cur, new_name = self.tree_preview.item(item, "values")
            ep = self.find_episode_by_title(cur)
            if not ep: continue
            
            src = ep.path
            dst = os.path.join(os.path.dirname(src), new_name)
            if os.path.abspath(src) == os.path.abspath(dst): continue
            
            try:
                shutil.move(src, dst)
                moves.append((src, dst))
                prune_candidates.add(os.path.dirname(src))
                ep.path = dst # Update model
            except Exception as e:
                messagebox.showwarning("Rename error", f"Failed: {src} -> {dst}\n{e}")
        
        if moves:
            action = BatchAction(description=f"Rename {len(moves)} files", moves=moves)
            self.history.push(action)
            for p in prune_candidates:
                prune_empty_dirs(p, stop_at=self.settings.get("tv_root"))
            self.scan_root()
            
    def combine_selected_series(self):
        sel_ids = [it for it in self.tree_series.selection() if not self.tree_series.parent(it)]
        if len(sel_ids) < 2:
            messagebox.showinfo("Combine", "Select two or more top-level series to combine.")
            return

        names = [self.tree_series.item(t, "text") for t in sel_ids]
        target_name = simpledialog.askstring("Combine Series", f"Combine {len(names)} series into which name?", initialvalue=names[0])
        if not target_name: return

        tv_root = self.settings.get("tv_root")
        if not tv_root: return

        target_folder = os.path.join(tv_root, target_name)
        os.makedirs(target_folder, exist_ok=True)
        
        moves = []
        prune_candidates = set()
        
        for name in names:
            if name == target_name: continue
            src_series = self.series_map.get(name)
            if not src_series: continue
            
            src_folder = os.path.join(tv_root, name)
            # Move all files from source series folder to target series folder
            for dirpath, _, filenames in os.walk(src_folder):
                for f in filenames:
                    src_path = os.path.join(dirpath, f)
                    # Construct a relative path to maintain structure
                    rel_path = os.path.relpath(src_path, src_folder)
                    dst_path = os.path.join(target_folder, rel_path)
                    try:
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.move(src_path, dst_path)
                        moves.append((src_path, dst_path))
                    except Exception as e:
                        messagebox.showwarning("Combine error", f"{src_path} -> {dst_path}: {e}")
            prune_candidates.add(src_folder)
        
        if moves:
            action = BatchAction(description=f"Combine {len(names)} series into '{target_name}'", moves=moves, created_folders=[target_folder])
            self.history.push(action)
            for p in prune_candidates:
                prune_empty_dirs(p, stop_at=tv_root)
            self.scan_root()

    def on_series_right_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if not item: return
        if item not in self.tree_series.selection():
            self.tree_series.selection_set(item)
        menu = tb.Menu(self, tearoff=0)
        menu.add_command(label="Rename Series / Season", command=lambda: self.open_rename_dialog(item))
        menu.add_separator()
        menu.add_command(label="Move Selected to Season…", command=lambda: self.context_move_selected_to_season(item))
        menu.add_command(label="Combine Selected Series...", command=self.combine_selected_series)
        menu.add_separator()
        menu.add_command(label="Rename Selected Files (in Preview)", command=self.rename_selected_preview)
        menu.post(event.x_root, event.y_root)

    def on_series_double_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if item and self.tree_series.get_children(item):
            self.tree_series.item(item, open=not self.tree_series.item(item, "open"))

    def toggle_history_panel(self):
        if self.history_toplevel:
            self.dock_history()
            return
        if self.history_visible:
            self.right_paned.forget(self.history_frame)
            self.history_visible = False
        else:
            self.right_paned.add(self.history_frame, weight=1)
            self.history_visible = True
            
    def undock_history(self):
        if self.history_toplevel: return
        self.right_paned.forget(self.history_frame)

        self.history_toplevel = tb.Toplevel(self)
        self.history_toplevel.title("History")
        self.history_toplevel.geometry("600x400")
        
        undocked_panel = self._create_history_panel(self.history_toplevel)
        undocked_panel.pack(fill="both", expand=True, padx=4, pady=4)
        
        header = undocked_panel.winfo_children()[0]
        # Replace the "Undock" button with a "Dock" button in the new window
        header.winfo_children()[1].destroy() # Destroy original Undock button
        tb.Button(header, text="Dock", bootstyle="link", command=self.dock_history).pack(side="right")
        
        self.history_undocked_listbox = undocked_panel.winfo_children()[2].winfo_children()[0]
        
        self.history_toplevel.protocol("WM_DELETE_WINDOW", self.dock_history)
        self.refresh_history_list()

    def dock_history(self):
        if not self.history_toplevel: return
        
        self.history_toplevel.destroy()
        self.history_toplevel = None
        self.history_undocked_listbox = None
        
        if self.history_visible:
            self.right_paned.add(self.history_frame, weight=1)
        self.refresh_history_list()

    def open_settings(self):
        messagebox.showinfo("Settings", "Settings dialog not yet implemented.")
    
    def move_to_parsing(self):
        messagebox.showinfo("Move", "Move to Parsing not yet implemented.")
        
    def move_to_live(self):
        messagebox.showinfo("Move", "Move to Live not yet implemented.")

    def open_rename_dialog(self, item):
        messagebox.showinfo("Rename", "Rename dialog not yet implemented.")

    def context_move_selected_to_season(self, item):
        messagebox.showinfo("Move", "Move to season not yet implemented.")


if __name__ == "__main__":
    settings = load_settings()
    app = TVRenamerApp(settings)
    app.mainloop()