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

def generate_new_name(filename):
    m = SxxExx_RE.search(filename)
    if m:
        season, ep = m.groups()
        season = int(season)
        ep = int(ep)
        name = re.sub(r'.*\- ', '', filename).split('.')[0]
        return f"S{season:02d}E{ep:02d} - {name}{os.path.splitext(filename)[1]}"
    else:
        return filename

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
                    "needs_info": False,
                    "status": "staging"
                })
        else:
            episodes = [f for f in sorted(os.listdir(show_path)) if is_video_file(f)]
            if episodes:
                series_list.append({
                    "path": show_path,
                    "name": show,
                    "season": None,
                    "episodes": episodes,
                    "needs_info": True,
                    "status": "staging"
                })
    return series_list

# ---------------------------
# GUI Main Window
# ---------------------------
class SeriesRenamer(tb.Window):
    def __init__(self, settings):
        super().__init__(themename="darkly")
        self.title("TV Renamer v0.03a")
        self.geometry("1300x750")
        self.settings = settings

        # Top frame
        top = tb.Frame(self)
        top.pack(fill=X, padx=10, pady=8)
        self.btn_move_parsing = tb.Button(top, text="Move to Parsing", bootstyle=INFO, command=lambda: self.move_series("parsing"))
        self.btn_move_parsing.pack(side=LEFT, padx=5)
        self.btn_move_live = tb.Button(top, text="Move to Live", bootstyle=INFO, command=lambda: self.move_series("live"))
        self.btn_move_live.pack(side=LEFT, padx=5)
        self.btn_rescan = tb.Button(top, text="Rescan", bootstyle=INFO, command=self.load_series)
        self.btn_rescan.pack(side=LEFT, padx=5)
        self.btn_settings = tb.Button(top, text="Settings", bootstyle=SECONDARY, command=self.open_settings_dialog)
        self.btn_settings.pack(side=LEFT, padx=5)
        spacer = tb.Label(top, text="")
        spacer.pack(side=LEFT, expand=True)
        tb.Button(top, text="Exit", bootstyle=DANGER, command=self.destroy).pack(side=RIGHT, padx=5)

        # Tree frame
        tree_frame = tb.Frame(self)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=6)
        self.tree = tb.Treeview(tree_frame, columns=("episodes",), show="tree headings")
        self.tree.heading("#0", text="Show / Season / Episode")
        self.tree.heading("episodes", text="Episodes Count")
        self.tree.column("episodes", width=120, anchor="center")
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.config(selectmode="extended")
        vsb = tb.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill=Y)

        # Preview frame
        self.preview_frame = tb.Frame(self)
        self.preview_frame.pack(fill=BOTH, expand=True, padx=10, pady=6)
        self.preview_tree = tb.Treeview(self.preview_frame, columns=("current", "new_name"), show="headings")
        self.preview_tree.heading("current", text="Current Filename")
        self.preview_tree.heading("new_name", text="New Filename (double-click to edit)")
        self.preview_tree.column("current", width=400)
        self.preview_tree.column("new_name", width=400)
        self.preview_tree.pack(fill=BOTH, expand=True, side=LEFT)
        vsb_preview = tb.Scrollbar(self.preview_frame, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=vsb_preview.set)
        vsb_preview.pack(side=RIGHT, fill=Y)

        # Bindings
        self.tree.bind("<Button-1>", self.on_left_click)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        self.tree.tag_configure("needs_info", foreground="red")
        self.tree.tag_configure("parsing", foreground="purple")
        self.tree.tag_configure("staging", foreground="white")
        self.tree.tag_configure("selected", background="#00aa00")

        self.series_data = []
        self.load_series()

    # ---------------------------
    # Event handlers
    # ---------------------------
    def on_left_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.update_preview()

    def on_double_click(self, event):
        """Select and toggle expansion for nodes with children"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        if self.tree.get_children(item):
            self.tree.item(item, open=not self.tree.item(item, "open"))

    def on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Rename", command=lambda: self.rename_series(item))
        menu.post(event.x_root, event.y_root)

    # ---------------------------
    # Core methods
    # ---------------------------
    def load_series(self):
        """Load all series from the TV root folder into the main tree."""
        self.series_data = collect_series(self.settings["tv_root"])
        self.tree.delete(*self.tree.get_children())

        # Group series by name
        grouped = {}
        for s in self.series_data:
            if s["name"] not in grouped:
                grouped[s["name"]] = []
            grouped[s["name"]].append(s)

        for series_name, seasons in grouped.items():
            needs_info_flag = any(s["needs_info"] for s in seasons)
            series_node = self.tree.insert(
                "", "end", text=series_name,
                tags=("needs_info",) if needs_info_flag else ()
            )

            # Add seasons as children
            for s in sorted(seasons, key=lambda x: (x["season"] if x["season"] else 0)):
                season_text = f"Season {s['season']:02d}" if s["season"] else "Unknown"
                season_node = self.tree.insert(
                    series_node, "end", text=season_text,
                    values=(len(s["episodes"]),)
                )
                for ep in s["episodes"]:
                    self.tree.insert(season_node, "end", text=ep)

        self.update_preview()

    def update_preview(self):
        """Populate the preview tree with current filenames and new names."""
        self.preview_tree.delete(*self.preview_tree.get_children())
        for s in self.series_data:
            for ep in s["episodes"]:
                new_name = generate_new_name(ep)
                self.preview_tree.insert("", "end", values=(ep, new_name))

    # Placeholder for context menu rename
    def rename_series(self, item):
        # Find series data by tree item text
        series_text = self.tree.item(item, "text")
        matching_series = [s for s in self.series_data if s["name"] == series_text]
        if matching_series:
            dialog = RenameSeriesDialog(self, item, matching_series[0])
            self.wait_window(dialog)

    def move_series(self, folder):
        messagebox.showinfo("Move", f"Move series to {folder} (not yet implemented)")

    def open_settings_dialog(self):
        messagebox.showinfo("Settings", "Settings dialog (not yet implemented)")

# ---------------------------
# Rename GUI
# ---------------------------
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
        self.entry_name.pack(fill=X, padx=10)

        # Tree for seasons and episodes
        self.tree = tb.Treeview(self, columns=("episodes",), show="tree headings")
        self.tree.heading("#0", text="Seasons / Episodes")
        self.tree.heading("episodes", text="Episode Count")
        self.tree.column("episodes", width=120, anchor="center")
        self.tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.load_tree()

        btn_frame = tb.Frame(self)
        btn_frame.pack(pady=10)
        tb.Button(btn_frame, text="Add Season", bootstyle=INFO, command=self.add_season).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Save", bootstyle=SUCCESS, command=self.save).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Cancel", bootstyle=DANGER, command=self.destroy).pack(side=RIGHT, padx=5)

        self.tree.bind("<Double-1>", self.rename_node)

    def load_tree(self):
        self.tree.delete(*self.tree.get_children())
        seasons = {}
        for ep in self.series_data["episodes"]:
            season_num = self.series_data.get("season") or 1
            if season_num not in seasons:
                seasons[season_num] = []
            seasons[season_num].append(ep)
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
            self.parent.tree.item(self.series_item, text=new_name)
        self.destroy()

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    settings = load_settings()
    app = SeriesRenamer(settings)
    app.mainloop()
