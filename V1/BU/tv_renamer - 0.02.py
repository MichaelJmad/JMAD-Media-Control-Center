import os
import json
import re
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *

SETTINGS_FILE = "settings.json"
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
DEBUG = False

def dprint(*args):
    if DEBUG:
        print("[DEBUG]", *args)

# ---------------------------
# Settings
# ---------------------------
DEFAULT_SETTINGS = {
    "tv_root": os.getcwd(),
    "staging": os.path.join(os.getcwd(), "Staging"),
    "parsing": os.path.join(os.getcwd(), "Parsing"),
    "live": os.path.join(os.getcwd(), "Live")
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    else:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

# ---------------------------
# Helper functions
# ---------------------------
SEASON_DIR_RE = re.compile(r'^(?:s(?:eason)?\s*)?(\d+)$', re.IGNORECASE)
SxxExx_RE = re.compile(r'[sS](\d{1,2})[eE](\d{1,3})')

def is_video_file(filename):
    return os.path.splitext(filename)[1].lower() in VIDEO_EXTS

def season_from_folder(folder_name):
    m = SEASON_DIR_RE.match(folder_name.strip())
    if m:
        return int(m.group(1))
    return None

def parse_sxxexx(filename):
    m = SxxExx_RE.search(filename)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

# ---------------------------
# Collect series and episodes
# ---------------------------
def collect_series(tv_root):
    series_list = []
    for show in sorted(os.listdir(tv_root)):
        show_path = os.path.join(tv_root, show)
        if not os.path.isdir(show_path):
            continue

        seasons = []
        for entry in sorted(os.listdir(show_path)):
            full = os.path.join(show_path, entry)
            if os.path.isdir(full):
                sn = season_from_folder(entry)
                if sn:
                    episodes = [f for f in sorted(os.listdir(full)) if is_video_file(f)]
                    seasons.append({"season": sn, "episodes": episodes, "path": full})

        if seasons:
            for s in seasons:
                series_list.append({
                    "path": s["path"],
                    "name": show,
                    "season": s["season"],
                    "episodes": s["episodes"],
                    "needs_info": False
                })
        else:
            episodes = [f for f in sorted(os.listdir(show_path)) if is_video_file(f)]
            if episodes:
                series_list.append({
                    "path": show_path,
                    "name": show,
                    "season": None,
                    "episodes": episodes,
                    "needs_info": True
                })
    return series_list

# ---------------------------
# GUI Components
# ---------------------------
class SeriesRenamer(tb.Window):
    def __init__(self, settings):
        super().__init__(themename="darkly")
        self.title("TV Renamer v0.02")
        self.geometry("1200x700")
        self.settings = settings

        # Top frame: workflow buttons
        top = tb.Frame(self)
        top.pack(fill=X, padx=10, pady=8)
        tb.Button(top, text="Settings", bootstyle=SECONDARY, command=self.edit_settings).pack(side=LEFT, padx=5)
        tb.Button(top, text="Move to Parsing", bootstyle=INFO, command=lambda: self.move_series("parsing")).pack(side=LEFT, padx=5)
        tb.Button(top, text="Move to Live", bootstyle=SUCCESS, command=lambda: self.move_series("live")).pack(side=LEFT, padx=5)
        tb.Button(top, text="Rescan", bootstyle=PRIMARY, command=self.load_series).pack(side=LEFT, padx=5)
        tb.Button(top, text="Exit", bootstyle=DANGER, command=self.destroy).pack(side=RIGHT, padx=5)

        # Tree frame with scrollbar
        tree_frame = tb.Frame(self)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=6)

        self.tree = tb.Treeview(tree_frame, columns=("episodes",), show="tree headings", bootstyle="dark")
        self.tree.heading("#0", text="Show / Season / Episode")
        self.tree.heading("episodes", text="Episodes Count")
        self.tree.column("episodes", width=120, anchor="center")
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        vsb = tb.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill=Y)

        # Bind double-click editing
        self.tree.bind("<Double-1>", self.on_double_click)

        self.series_data = []
        self.load_series()

    def edit_settings(self):
        for key in ["tv_root","staging","parsing","live"]:
            path = filedialog.askdirectory(title=f"Select {key.replace('_',' ').title()}", initialdir=self.settings[key])
            if path:
                self.settings[key] = path
        save_settings(self.settings)
        self.load_series()

    def load_series(self):
        self.tree.delete(*self.tree.get_children())
        self.series_data = collect_series(self.settings["tv_root"])

        # Group seasons under series
        series_dict = {}
        for s in self.series_data:
            key = s["name"]
            if key not in series_dict:
                series_dict[key] = {"series": s, "seasons": []}
            series_dict[key]["seasons"].append(s)

        for series_name, data in series_dict.items():
            series_node = self.tree.insert("", "end", text=series_name,
                                           values=("",),
                                           tags=("needs_info" if any(se["needs_info"] for se in data["seasons"]) else ""))
            # Add seasons under series
            for s in sorted(data["seasons"], key=lambda x: x["season"] or 0):
                season_num = s["season"] if s["season"] else 0
                season_text = f"Season {season_num:02d}" if season_num else "Unknown"
                season_node = self.tree.insert(series_node, "end", text=season_text,
                                               values=(len(s["episodes"]),),
                                               tags=("needs_info" if s["needs_info"] else ""))
                # Add episodes under the season
                for ep_file in s["episodes"]:
                    self.tree.insert(season_node, "end", text=ep_file)

        self.tree.tag_configure("needs_info", foreground="red")

    def on_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        parent = self.tree.parent(item_id)
        grandparent = self.tree.parent(parent)

        if not parent:  # Series node
            # Find series index
            for idx, s in enumerate(self.series_data):
                if s["name"] == self.tree.item(item_id, "text"):
                    series_idx = idx
                    break
            else:
                return
            new_name = simpledialog.askstring("Series Name", "Enter series name:",
                                              initialvalue=self.series_data[series_idx]["name"])
            if new_name:
                self.series_data[series_idx]["name"] = new_name
        elif not grandparent:  # Season node
            season_node = self.tree.item(item_id, "text")
            new_season = simpledialog.askinteger("Season Number", "Enter new season number:", minvalue=1)
            if new_season:
                self.tree.item(item_id, text=f"Season {new_season:02d}")
        else:  # Episode node
            ep_name = self.tree.item(item_id, "text")
            new_ep = simpledialog.askstring("Episode Name", "Enter new filename:", initialvalue=ep_name)
            if new_ep:
                self.tree.item(item_id, text=new_ep)

    def move_series(self, target):
        folder = self.settings[target]
        if not os.path.exists(folder):
            os.makedirs(folder)
        for series in self.series_data:
            dest = os.path.join(folder, series["name"])
            if not os.path.exists(dest):
                os.rename(series["path"], dest)
            else:
                messagebox.showwarning("Warning", f"{series['name']} already exists in {target}. Skipping.")
        messagebox.showinfo("Done", f"Series moved to {target}.")
        self.load_series()

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    settings = load_settings()
    app = SeriesRenamer(settings)
    app.mainloop()
