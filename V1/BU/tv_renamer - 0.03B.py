import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}

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

# -------------------- Main App -------------------- #
class SeriesRenamer(tb.Window):
    def __init__(self, root_folder):
        super().__init__(themename="darkly")
        self.title("TV Series Renamer")
        self.geometry("1200x700")
        self.root_folder = root_folder
        self.series_list = []

        self.setup_ui()
        self.scan_root()

    def setup_ui(self):
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

    # -------------------- Scanning -------------------- #
    def scan_root(self):
        self.series_list.clear()
        self.tree_series.delete(*self.tree_series.get_children())
        for item in os.listdir(self.root_folder):
            s_path = os.path.join(self.root_folder, item)
            if os.path.isdir(s_path):
                series = Series(item)
                self.parse_series_folder(series, s_path)
                self.series_list.append(series)
        self.populate_tree()

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
                    # Non-season folder (Specials, Movies, etc.)
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

    # -------------------- Treeview Population -------------------- #
    def populate_tree(self):
        for s in self.series_list:
            series_id = self.tree_series.insert("", "end", text=s.name, values=("", ""))
            if not s.seasons:
                self.tree_series.item(series_id, tags=("missing_season",))
            # Sort numeric seasons first, then string-based
            numeric_seasons = sorted([k for k in s.seasons.keys() if isinstance(k, int)])
            string_seasons = sorted([k for k in s.seasons.keys() if isinstance(k, str)])
            sorted_seasons = numeric_seasons + string_seasons

            for num in sorted_seasons:
                season = s.seasons[num]
                season_label = f"Season {num}" if isinstance(num, int) else num
                season_id = self.tree_series.insert(series_id, "end", text=season_label, values=(len(season.episodes), ""))
                for ep in season.episodes:
                    self.tree_series.insert(season_id, "end", text=ep.title, values=("",))
            # Unsorted episodes
            for ep in s.unsorted:
                ep_id = self.tree_series.insert(series_id, "end", text=ep.title, values=("", "Unsorted"))
                self.tree_series.item(ep_id, tags=("unsorted",))
        self.tree_series.tag_configure("missing_season", foreground="red")
        self.tree_series.tag_configure("unsorted", foreground="red")

    # -------------------- Right Click -------------------- #
    def on_right_click(self, event):
        item = self.tree_series.identify_row(event.y)
        if item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Series / Season / Episode", command=lambda: self.open_rename_dialog(item))
            menu.post(event.x_root, event.y_root)

    def open_rename_dialog(self, item):
        series_name = self.tree_series.item(item, "text")
        series_obj = None
        for s in self.series_list:
            if s.name == series_name:
                series_obj = s
                break
        if series_obj:
            dlg = RenameSeriesDialog(self, item, {
                "name": series_obj.name,
                "episodes": [ep.title for season in series_obj.seasons.values() for ep in season.episodes] +
                            [ep.title for ep in series_obj.unsorted]
            })
            self.wait_window(dlg)

# -------------------- Rename GUI -------------------- #
class RenameSeriesDialog(tb.Toplevel):
    def __init__(self, parent, series_item, series_data):
        super().__init__(parent)
        self.title("Rename Series")
        self.geometry("700x500")
        self.parent = parent
        self.series_item = series_item
        self.series_data = series_data
        self.modified = False

        self.series_name_var = tk.StringVar(value=self.series_data["name"])
        tb.Label(self, text="Series Name:").pack(pady=5)
        self.entry_name = tb.Entry(self, textvariable=self.series_name_var)
        self.entry_name.pack(fill="x", padx=10)

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
        seasons = {1: []}  # default season 1
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
            self.modified = True

    def rename_node(self, event):
        item = self.tree.focus()
        if not item:
            return
        current = self.tree.item(item, "text")
        new_val = simpledialog.askstring("Rename", "New name:", initialvalue=current)
        if new_val:
            self.tree.item(item, text=new_val)
            self.modified = True

    def save(self):
        new_name = self.series_name_var.get().strip()
        if new_name:
            self.series_data["name"] = new_name
            self.parent.tree_series.item(self.series_item, text=new_name)
        self.destroy()

# -------------------- Main -------------------- #
if __name__ == "__main__":
    root_folder = filedialog.askdirectory(title="Select TV Root Folder")
    if root_folder:
        app = SeriesRenamer(root_folder)
        app.mainloop()
