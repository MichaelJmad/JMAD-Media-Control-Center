import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# ---------------------------
# Config
# ---------------------------
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}
DEBUG = False  # set True to print debug logs to console

def dprint(*args):
    if DEBUG:
        print("[DEBUG]", *args)

# ---------------------------
# Parsing helpers
# ---------------------------

SEASON_DIR_RE = re.compile(r'^(?:s(?:eason)?\s*)?(\d+)$', re.IGNORECASE)
SxxExx_RE     = re.compile(r'[sS](\d{1,2})[eE](\d{1,3})')
E3or4_RE      = re.compile(r'[eE](\d{3,4})(?!\d)')
NUM_RE        = re.compile(r'\d+')

def season_from_folder(folder_name: str) -> int | None:
    m = SEASON_DIR_RE.match(folder_name.strip())
    if m:
        val = int(m.group(1))
        dprint("season_from_folder:", folder_name, "->", val)
        return val
    return None

def parse_sxxexx(name: str) -> tuple[int, int] | None:
    m = SxxExx_RE.search(name)
    if m:
        s = int(m.group(1))
        e = int(m.group(2))
        dprint("parse_sxxexx:", name, "->", (s, e))
        return s, e
    return None

def parse_e3or4(name: str) -> tuple[int, int] | None:
    m = E3or4_RE.search(name)
    if not m:
        return None
    digits = m.group(1)
    if len(digits) == 3:
        s = int(digits[0])
        e = int(digits[1:])
    else:
        s = int(digits[:2])
        e = int(digits[-2:])
    dprint("parse_e3or4:", name, "->", (s, e))
    return s, e

def first_number(name: str) -> int | None:
    m = NUM_RE.search(name)
    if m:
        val = int(m.group(0))
        dprint("first_number:", name, "->", val)
        return val
    return None

def suggest_new_name(filename: str, season_hint: int | None, in_season_folder: bool, in_flat_show: bool) -> tuple[str | None, tuple[int,int] | None]:
    name, ext = os.path.splitext(filename)

    se = parse_sxxexx(name)
    if se:
        s, e = se
        return f"S{s:02d}E{e:02d}{ext}", (s, e)

    e705 = parse_e3or4(name)
    if e705:
        s, e = e705
        return f"S{s:02d}E{e:02d}{ext}", (s, e)

    if in_season_folder and season_hint is not None:
        ep = first_number(name)
        if ep is not None:
            return f"S{season_hint:02d}E{ep:02d}{ext}", (season_hint, ep)
        else:
            return None, None

    return None, None

# ---------------------------
# Discovery
# ---------------------------

def is_video_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in VIDEO_EXTS

def find_shows(tv_root: str):
    if not os.path.isdir(tv_root):
        return
    for show in sorted(os.listdir(tv_root)):
        sp = os.path.join(tv_root, show)
        if os.path.isdir(sp):
            yield sp, show

def season_subfolders(show_path: str):
    season_list = []
    for entry in os.listdir(show_path):
        full = os.path.join(show_path, entry)
        if os.path.isdir(full):
            sn = season_from_folder(entry)
            if sn is not None:
                season_list.append((full, entry, sn))
    # Sort by numeric season
    season_list.sort(key=lambda x: x[2])
    return season_list

def collect_candidates(tv_root: str):
    rows = []

    for show_path, show_name in find_shows(tv_root):
        seasons = season_subfolders(show_path)

        if seasons:
            for season_path, season_label, season_num in seasons:
                for f in sorted(os.listdir(season_path)):
                    if not is_video_file(f):
                        continue
                    old_path = os.path.join(season_path, f)
                    new_base, pair = suggest_new_name(
                        filename=f,
                        season_hint=season_num,
                        in_season_folder=True,
                        in_flat_show=False
                    )
                    if new_base and f != new_base:
                        rows.append({
                            "old_path": old_path,
                            "new_name": new_base,
                            "show": show_name,
                            "season": f"S{season_num:02d}",
                            "old_base": f,
                            "new_base": new_base
                        })
        else:
            for f in sorted(os.listdir(show_path)):
                if not is_video_file(f):
                    continue
                old_path = os.path.join(show_path, f)
                new_base, pair = suggest_new_name(
                    filename=f,
                    season_hint=None,
                    in_season_folder=False,
                    in_flat_show=True
                )
                if new_base and f != new_base:
                    rows.append({
                        "old_path": old_path,
                        "new_name": new_base,
                        "show": show_name,
                        "season": "-",
                        "old_base": f,
                        "new_base": new_base
                    })

    return rows

# ---------------------------
# GUI
# ---------------------------

class EditableTree(tb.Treeview):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self._edit_entry = None
        self.bind("<Double-1>", self._begin_edit)

    def _begin_edit(self, event):
        region = self.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)
        if col_id != "#4" or not row_id:  # only "new" column editable
            return

        x, y, w, h = self.bbox(row_id, col_id)
        value = self.set(row_id, "new")

        self._edit_entry = tb.Entry(self)
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.insert(0, value)
        self._edit_entry.focus()
        self._edit_entry.bind("<Return>", lambda e: self._save_edit(row_id))
        self._edit_entry.bind("<Escape>", lambda e: self._cancel_edit())
        self._edit_entry.bind("<FocusOut>", lambda e: self._save_edit(row_id))

    def _save_edit(self, row_id):
        if not self._edit_entry:
            return
        new_val = self._edit_entry.get().strip()
        if new_val:
            self.set(row_id, "new", new_val)
        self._edit_entry.destroy()
        self._edit_entry = None

    def _cancel_edit(self):
        if self._edit_entry:
            self._edit_entry.destroy()
            self._edit_entry = None

class App(tb.Window):
    def __init__(self, tv_root: str):
        super().__init__(themename="darkly")
        self.title("TV Show File Renamer (Dark)")
        self.geometry("1000x600")

        # Top bar
        top = tb.Frame(self)
        top.pack(fill=X, padx=10, pady=8)

        tb.Label(top, text="TV Root:").pack(side=LEFT)
        self.root_var = tk.StringVar(value=tv_root)
        self.root_entry = tb.Entry(top, textvariable=self.root_var, width=60)
        self.root_entry.pack(side=LEFT, padx=6)

        tb.Button(top, text="Browse", bootstyle=SECONDARY, command=self.browse_root).pack(side=LEFT, padx=6)
        tb.Button(top, text="Rescan", bootstyle=INFO, command=self.load_rows).pack(side=LEFT, padx=6)

        # Instruction label
        tb.Label(self, text="Double-click the 'New Filename' column to edit any name.", bootstyle=INFO).pack(pady=(0,5))

        # Tree with Scrollbar
        tree_frame = tb.Frame(self)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=6)

        self.tree = EditableTree(tree_frame, columns=("show", "season", "old", "new"), show="headings", bootstyle="dark")
        self.tree.heading("show", text="Show")
        self.tree.heading("season", text="Season")
        self.tree.heading("old", text="Current Filename")
        self.tree.heading("new", text="New Filename")

        self.tree.column("show", width=200, anchor="w")
        self.tree.column("season", width=80, anchor="center")
        self.tree.column("old", width=350, anchor="w")
        self.tree.column("new", width=350, anchor="w")

        vsb = tb.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        # Buttons
        btns = tb.Frame(self)
        btns.pack(fill=X, padx=10, pady=10)
        tb.Button(btns, text="Rename Selected", bootstyle=SUCCESS, command=self.rename_selected).pack(side=LEFT, padx=5)
        tb.Button(btns, text="Rename All", bootstyle=PRIMARY, command=self.rename_all).pack(side=LEFT, padx=5)
        tb.Button(btns, text="Exit", bootstyle=DANGER, command=self.destroy).pack(side=RIGHT, padx=5)

        self.rows = []
        self.load_rows()  # auto-load detected folder on startup

    def browse_root(self):
        path = filedialog.askdirectory(title="Select TV root folder")
        if path:
            self.root_var.set(path)
            self.load_rows()

    def load_rows(self):
        self.tree.delete(*self.tree.get_children())
        tv_root = self.root_var.get().strip()
        self.rows = collect_candidates(tv_root)
        for idx, row in enumerate(self.rows):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(row["show"], row["season"], row["old_base"], row["new_base"])
            )
        if not self.rows:
            messagebox.showinfo("Info", "No rename candidates found.\nRules:\n• Season folders: derive season from folder\n• Flat folders: only files with SxxEyy or E705/E1205 considered")

    def _apply_renames(self, index_iterable):
        errors = []
        for iid in index_iterable:
            i = int(iid)
            row = self.rows[i]
            edited_new = self.tree.set(iid, "new").strip()
            old_path = row["old_path"]
            new_path = os.path.join(os.path.dirname(old_path), edited_new)

            _, old_ext = os.path.splitext(old_path)
            _, new_ext = os.path.splitext(edited_new)
            if new_ext.lower() != old_ext.lower():
                new_path = os.path.splitext(new_path)[0] + old_ext

            try:
                os.rename(old_path, new_path)
                dprint("RENAMED:", old_path, "->", new_path)
            except Exception as e:
                errors.append(f"{os.path.basename(old_path)}: {e}")

        if errors:
            messagebox.showerror("Some renames failed", "\n".join(errors[:20]))
        else:
            messagebox.showinfo("Done", "Rename complete.")
        self.load_rows()

    def rename_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "No rows selected.")
            return
        self._apply_renames(sel)

    def rename_all(self):
        all_ids = self.tree.get_children()
        if not all_ids:
            messagebox.showinfo("Info", "Nothing to rename.")
            return
        self._apply_renames(all_ids)

# ---------------------------
# Main
# ---------------------------

if __name__ == "__main__":
    DEFAULT_TV_ROOT = os.getcwd()  # auto-load folder where script/exe is run
    app = App(DEFAULT_TV_ROOT)
    app.mainloop()
