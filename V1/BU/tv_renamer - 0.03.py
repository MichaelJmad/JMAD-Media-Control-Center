import os
import json
import re
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
        self.number = number  # Can be int or str
        self.episodes = []

class Series:
    def __init__(self, name):
        self.name = name
        self.seasons = {}  # key: int or str, value: Season
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

# -------------------- Main App -------------------- #
class SeriesRenamer(tb.Window):
    def __init__(self, settings):
        # Validate theme
        valid_themes = ["darkly","superhero","cosmo","flatly","minty"]
        theme = settings.get("theme", "darkly")
        if theme not in valid_themes:
            theme = "darkly"

        super().__init__(themename=theme)
        self.title("TV Series Renamer 0.04")
        self.geometry("1200x700")
        self.settings = settings
        self.series_list = []

        self.setup_ui()
        if settings["tv_root"]:
            self.scan_root()

    def setup_ui(self):
        # ---------------- Toolbar ---------------- #
        toolbar = tb.Frame(self, padding=5)
        toolbar.pack(side="top", fill="x")

        self.btn_parsing = tb.Button(toolbar, text="Move to Parsing", bootstyle="info", command=self.move_parsing)
        self.btn_parsing.pack(side="left", padx=2)
        self.btn_live = tb.Button(toolbar, text="Move to Live", bootstyle="info", command=self.move_live)
        self.btn_live.pack(side="left", padx=2)
        self.btn_rescan = tb.Button(toolbar, text="Rescan", bootstyle="info", command=self.scan_root)
        self.btn_rescan.pack(side="left", padx=2)
        self.btn_settings = tb.Button(toolbar, text="Settings", bootstyle="secondary", command=self.open_settings)
        self.btn_settings.pack(side="left", padx=2)

        self.btn_exit = tb.Button(toolbar, text="Exit", bootstyle="danger", command=self.destroy)
        self.btn_exit.pack(side="right", padx=2)

        # ---------------- Paned Window ---------------- #
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # Left treeview
        left_frame = tb.Frame(paned, padding=5)
        self.tree_series = ttk.Treeview(left_frame, columns=("count", "status"), show="tree headings")
        self.tree_series.heading("#0", text="Series / Seasons / Episodes")
        self.tree_series.heading("count", text="Episodes")
        self.tree_series.heading("status", text="Status")
        self.tree_series.pack(fill="both", expand=True)
        self.tree_series.bind("<Button-3>", self.on_right_click)
        paned.add(left_frame, weight=3)

        # Right preview treeview
        right_frame = tb.Frame(paned, padding=5)
        self.tree_preview = ttk.Treeview(right_frame, columns=("current","new"), show="headings")
        self.tree_preview.heading("current", text="Current Filename")
        self.tree_preview.heading("new", text="New Filename")
        self.tree_preview.pack(fill="both", expand=True)
        paned.add(right_frame, weight=2)

    # ---------------- File Operations ---------------- #
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
                series = Series(item)
                self.parse_series_folder(series, s_path)
                self.series_list.append(series)
        self.populate_tree()
        self.populate_preview()

    def parse_series_folder(self, series, path):
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                match = entry.lower().replace(" ", "").replace("_","")
                if "season" in match or (match.startswith("s") and any(c.isdigit() for c in match)):
                    try:
                        num = int("".join(filter(str.isdigit, match)))
                    except:
                        num = 1
                    season = Season(num)
                    for ep in os.listdir(full_path):
                        ep_path = os.path.join(full_path, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1] in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=num))
                    series.seasons[num] = season
                else:
                    # Non-season folder (Specials, Movies)
                    label = entry
                    season = Season(label)
                    for ep in os.listdir(full_path):
                        ep_path = os.path.join(full_path, ep)
                        if os.path.isfile(ep_path) and os.path.splitext(ep_path)[1] in VIDEO_EXTS:
                            season.episodes.append(Episode(ep_path, season=label))
                    series.seasons[label] = season
            else:
                if os.path.splitext(full_path)[1] in VIDEO_EXTS:
                    series.unsorted.append(Episode(full_path))

    # ---------------- Treeview ---------------- #
    def populate_tree(self):
        self.tree_series.delete(*self.tree_series.get_children())
        for s in self.series_list:
            series_id = self.tree_series.insert("", "end", text=s.name, values=("", ""))
            if not s.seasons:
                self.tree_series.item(series_id, tags=("missing_season",))
            numeric_seasons = sorted([k for k in s.seasons.keys() if isinstance(k,int)])
            string_seasons = sorted([k for k in s.seasons.keys() if isinstance(k,str)])
            sorted_seasons = numeric_seasons + string_seasons
            for num in sorted_seasons:
                season = s.seasons[num]
                season_label = f"Season {num}" if isinstance(num,int) else num
                season_id = self.tree_series.insert(series_id, "end", text=season_label, values=(len(season.episodes), ""))
                for ep in season.episodes:
                    self.tree_series.insert(season_id, "end", text=ep.title, values=("",))
            for ep in s.unsorted:
                ep_id = self.tree_series.insert(series_id, "end", text=ep.title, values=("", "Unsorted"))
                self.tree_series.item(ep_id, tags=("unsorted",))
        self.tree_series.tag_configure("missing_season", foreground="red")
        self.tree_series.tag_configure("unsorted", foreground="red")

    # ---------------- Preview ---------------- #
    def populate_preview(self):
        self.tree_preview.delete(*self.tree_preview.get_children())
        rename_format = self.settings.get("rename_format","SxxExx")
        pattern = re.compile(r"(S\d{1,2}E\d{1,2})", re.IGNORECASE)
        for s in self.series_list:
            for season in s.seasons.values():
                for ep in season.episodes:
                    match = pattern.search(ep.title)
                    if match:
                        new_name = match.group(1) + os.path.splitext(ep.path)[1]
                        self.tree_preview.insert("", "end", values=(ep.title, new_name))

    # ---------------- Right Click ---------------- #
    def on_right_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Series / Season / Episode", command=lambda: self.open_rename_dialog(item))
            menu.post(event.x_root, event.y_root)

    def open_rename_dialog(self, item):
        series_name = self.tree_series.item(item, "text")
        series_obj = next((s for s in self.series_list if s.name==series_name), None)
        if series_obj:
            dlg = RenameSeriesDialog(self, item, {
                "name": series_obj.name,
                "episodes": [ep.title for season in series_obj.seasons.values() for ep in season.episodes]+
                            [ep.title for ep in series_obj.unsorted]
            })
            self.wait_window(dlg)
            self.populate_preview()

    # ---------------- Toolbar Commands ---------------- #
    def move_parsing(self): messagebox.showinfo("Move", "Move to Parsing functionality not implemented yet.")
    def move_live(self): messagebox.showinfo("Move", "Move to Live functionality not implemented yet.")

    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        self.wait_window(dlg)
        self.settings = dlg.settings
        save_settings(self.settings)
        # Validate theme
        valid_themes = ["darkly","superhero","cosmo","flatly","minty"]
        theme = self.settings.get("theme","darkly")
        if theme not in valid_themes:
            theme = "darkly"
        self.style.theme_use(theme)

# -------------------- Rename GUI -------------------- #
class RenameSeriesDialog(tb.Toplevel):
    def __init__(self, parent, series_item, series_data):
        super().__init__(parent)
        self.title("Rename Series")
        self.geometry("700x500")
        self.parent = parent
        self.series_item = series_item
        self.series_data = series_data

        self.series_name_var = tk.StringVar(value=self.series_data["name"])
        tb.Label(self, text="Series Name:").pack(pady=5)
        tb.Entry(self, textvariable=self.series_name_var).pack(fill="x", padx=10)

        self.tree = tb.Treeview(self, columns=("episodes",), show="tree headings")
        self.tree.heading("#0", text="Seasons / Episodes")
        self.tree.heading("episodes", text="Episode Count")
        self.tree.column("episodes", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=10)
        tb.Button(btn_frame, text="Add Season", bootstyle=INFO, command=self.add_season).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Save", bootstyle=SUCCESS, command=self.save).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cancel", bootstyle=DANGER, command=self.destroy).pack(side="right", padx=5)

        self.tree.bind("<Double-1>", self.rename_node)
        self.load_tree()

    def load_tree(self):
        self.tree.delete(*self.tree.get_children())
        seasons = {1: []}
        for ep in self.series_data["episodes"]:
            seasons[1].append(ep)
        for s_num in sorted(seasons.keys()):
            season_node = self.tree.insert("", "end", text=f"Season {s_num:02d}", values=(len(seasons[s_num]),))
            for ep in seasons[s_num]:
                self.tree.insert(season_node, "end", text=ep, values=("",))

    def add_season(self):
        new_num = simpledialog.askinteger("Add Season", "Season number:")
        if new_num:
            self.tree.insert("", "end", text=f"Season {new_num:02d}", values=(0,))

    def rename_node(self, event):
        item = self.tree.focus()
        if not item:
            return
        current = self.tree.item(item, "text")
        new_val = simpledialog.askstring("Rename", "New name:", initialvalue=current)
        if new_val:
            self.tree.item(item, text=new_val)

    def save(self):
        new_name = self.series_name_var.get().strip()
        if new_name:
            self.series_data["name"] = new_name
            self.parent.tree_series.item(self.series_item, text=new_name)
        self.destroy()

# -------------------- Settings GUI -------------------- #
class SettingsDialog(tb.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("500x400")
        self.settings = settings

        # Folder settings
        tb.Label(self, text="TV Root Folder:").pack(pady=5)
        self.tv_root_var = tk.StringVar(value=self.settings.get("tv_root",""))
        tb.Entry(self, textvariable=self.tv_root_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle=INFO, command=self.browse_tv_root).pack(padx=10, pady=2)

        tb.Label(self, text="Staging Folder:").pack(pady=5)
        self.staging_var = tk.StringVar(value=self.settings.get("staging",""))
        tb.Entry(self, textvariable=self.staging_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle=INFO, command=self.browse_staging).pack(padx=10, pady=2)

        tb.Label(self, text="Parsing Folder:").pack(pady=5)
        self.parsing_var = tk.StringVar(value=self.settings.get("parsing",""))
        tb.Entry(self, textvariable=self.parsing_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle=INFO, command=self.browse_parsing).pack(padx=10, pady=2)

        tb.Label(self, text="Live Folder:").pack(pady=5)
        self.live_var = tk.StringVar(value=self.settings.get("live",""))
        tb.Entry(self, textvariable=self.live_var).pack(fill="x", padx=10)
        tb.Button(self, text="Browse", bootstyle=INFO, command=self.browse_live).pack(padx=10, pady=2)

        # Theme
        tb.Label(self, text="Theme:").pack(pady=5)
        self.theme_var = tk.StringVar(value=self.settings.get("theme","darkly"))
        tb.OptionMenu(self, self.theme_var, "darkly", "flatly", "minty", "superhero", "cosmo").pack(fill="x", padx=10)

        # Rename format
        tb.Label(self, text="Default Rename Format:").pack(pady=5)
        self.rename_var = tk.StringVar(value=self.settings.get("rename_format","SxxExx"))
        tb.Entry(self, textvariable=self.rename_var).pack(fill="x", padx=10)

        # Save / Cancel
        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=20)
        tb.Button(btn_frame, text="Save", bootstyle=SUCCESS, command=self.save).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cancel", bootstyle=DANGER, command=self.destroy).pack(side="right", padx=5)

    def browse_tv_root(self):
        folder = filedialog.askdirectory(title="Select TV Root Folder")
        if folder: self.tv_root_var.set(folder)

    def browse_staging(self):
        folder = filedialog.askdirectory(title="Select Staging Folder")
        if folder: self.staging_var.set(folder)

    def browse_parsing(self):
        folder = filedialog.askdirectory(title="Select Parsing Folder")
        if folder: self.parsing_var.set(folder)

    def browse_live(self):
        folder = filedialog.askdirectory(title="Select Live Folder")
        if folder: self.live_var.set(folder)

    def save(self):
        self.settings["tv_root"] = self.tv_root_var.get()
        self.settings["staging"] = self.staging_var.get()
        self.settings["parsing"] = self.parsing_var.get()
        self.settings["live"] = self.live_var.get()
        self.settings["theme"] = self.theme_var.get()
        self.settings["rename_format"] = self.rename_var.get()
        self.destroy()

# -------------------- Main -------------------- #
if __name__ == "__main__":
    settings = load_settings()
    app = SeriesRenamer(settings)
    app.mainloop()
