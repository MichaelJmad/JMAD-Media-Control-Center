import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, scrolledtext, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from typing import Dict, List, Optional, Tuple
import os
import re
import json
from collections import Counter

# Assuming these are available from JMADMediaManager or a new common utility file
from media_models import Episode, Series, BatchAction, HistoryManager, suggest_series_name, parse_movie_info, predict_new_movie_filename, prune_empty_dirs, load_settings, save_settings, load_patterns, save_patterns, VIDEO_EXTS, DEFAULT_SETTINGS

class MovieOrganizeDialog(tk.Toplevel):
    def __init__(self, parent_app, series_list: List[Series]):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.series_list = series_list # In movie mode, each 'series' is essentially a movie
        
        self.title("Organize Movies")
        self.transient(parent_app)
        self.grab_set()

        self.local_undo_stack = []
        self.local_redo_stack = []
        self.movies_data: List[Dict] = [] # Stores data for each movie: original_path, assumed_title, proposed_path, etc.
        
        self._build_ui()
        self.populate_movies_list()
        self._update_undo_redo_buttons() # Initialize button states

        self.update_idletasks()
        self.resizable(True, True)
        self.minsize(800, 600)
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        win_w = 1000
        win_h = 700
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main_frame = tb.Frame(self, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        tb.Label(main_frame, text="Movies to Organize", bootstyle="inverse-primary", padding=5).pack(fill="x")

        # Treeview for movies data
        self.movies_tree = tb.Treeview(main_frame, columns=("original", "assumed_title", "proposed_path", "status"), show="headings", selectmode="browse")
        self.movies_tree.pack(fill="both", expand=True, pady=5)

        self.movies_tree.heading("original", text="Original File/Folder")
        self.movies_tree.heading("assumed_title", text="Assumed Movie Title")
        self.movies_tree.heading("proposed_path", text="Proposed New Path")
        self.movies_tree.heading("status", text="Status")

        self.movies_tree.column("original", width=200, stretch=True)
        self.movies_tree.column("assumed_title", width=200, stretch=True)
        self.movies_tree.column("proposed_path", width=300, stretch=True)
        self.movies_tree.column("status", width=100, stretch=False)

        self.movies_tree.tag_configure('conflict', foreground='red')
        self.movies_tree.tag_configure('ready', foreground='green')
        self.movies_tree.tag_configure('warning', foreground='orange')

        self.movies_tree.bind("<Double-1>", self._on_movie_double_click)

        # Buttons for Undo/Redo and Apply/Cancel
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.undo_btn = tb.Button(button_frame, text="Undo", command=self.undo_local_change, bootstyle="outline-warning", state="disabled")
        self.undo_btn.pack(side="left", padx=5)
        self.redo_btn = tb.Button(button_frame, text="Redo", command=self.redo_local_change, bootstyle="outline-info", state="disabled")
        self.redo_btn.pack(side="left", padx=5)

        self.apply_btn = tb.Button(button_frame, text="Apply Changes", command=self.apply_changes, bootstyle="outline-success", state="disabled")
        self.apply_btn.pack(side="right", padx=5)
        tb.Button(button_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").pack(side="right")

    def populate_movies_list(self):
        self.movies_tree.delete(*self.movies_tree.get_children())
        self.movies_data.clear()

        staging_dir = self.parent_app.settings.get("directories", {}).get("staging", "")
        movie_target_dir = self.parent_app.settings.get("directories", {}).get("movies", staging_dir)

        for series_obj in self.series_list: # Each series_obj here represents a potential movie
            # Assuming for movie mode, series_obj.name is the original folder/file name
            original_path = os.path.join(staging_dir, series_obj.name)
            
            # Find the actual video file within the series_obj (movie folder)
            video_file = None
            if os.path.isdir(original_path):
                for root, _, files in os.walk(original_path):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
                            video_file = os.path.join(root, f)
                            break
                    if video_file: break
            elif os.path.isfile(original_path) and os.path.splitext(original_path)[1].lower() in VIDEO_EXTS:
                video_file = original_path
            
            if not video_file:
                self.parent_app.log(f"Warning: No video file found in {original_path}. Skipping.")
                continue

            basename = os.path.basename(video_file)
            assumed_title = suggest_series_name(os.path.splitext(basename)[0], self.parent_app.fluff_patterns)
            year = parse_movie_info(basename)
            if year:
                assumed_title = f"{assumed_title} ({year})"
            
            proposed_path = os.path.join(movie_target_dir, assumed_title, basename)

            movie_entry = {
                "original_path": video_file,
                "assumed_title": assumed_title,
                "proposed_path": proposed_path,
                "status": "Ready", # Initial status
                "tree_id": None # Will store the treeview item ID
            }
            self.movies_data.append(movie_entry)

        self._update_movies_tree()
        self._check_conflicts()
        self._capture_state()

    def _update_movies_tree(self):
        self.movies_tree.delete(*self.movies_tree.get_children())
        for movie_entry in self.movies_data:
            tags = (movie_entry["status"].lower(),) if movie_entry["status"] != "Ready" else ('ready',)
            item_id = self.movies_tree.insert("", "end", values=(
                os.path.basename(movie_entry["original_path"]),
                movie_entry["assumed_title"],
                os.path.relpath(movie_entry["proposed_path"], self.parent_app.settings.get("directories", {}).get("movies", "")),
                movie_entry["status"]
            ), tags=tags)
            movie_entry["tree_id"] = item_id

    def _on_movie_double_click(self, event):
        item_id = self.movies_tree.identify_row(event.y)
        if not item_id: return

        col = self.movies_tree.identify_column(event.x)
        if col == "#2": # Assumed Movie Title column
            self._edit_movie_title(item_id)

    def _edit_movie_title(self, item_id):
        # Find the movie data associated with this item_id
        movie_entry = next((m for m in self.movies_data if m["tree_id"] == item_id), None)
        if not movie_entry: return

        x, y, w, h = self.movies_tree.bbox(item_id, column="assumed_title")
        entry = tb.Entry(self.movies_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, movie_entry["assumed_title"])
        entry.focus()

        def save(e):
            new_title = entry.get().strip()
            if not new_title:
                messagebox.showerror("Invalid Name", "Movie title cannot be empty.")
                entry.destroy()
                return

            movie_entry["assumed_title"] = new_title
            
            # Re-calculate proposed path based on new title
            basename = os.path.basename(movie_entry["original_path"])
            _, ext = os.path.splitext(basename)
            movie_target_dir = self.parent_app.settings.get("directories", {}).get("movies", "")
            movie_entry["proposed_path"] = os.path.join(movie_target_dir, new_title, new_title + ext)

            entry.destroy()
            self._check_conflicts()
            self._update_movies_tree()
            self._capture_state()
        
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _check_conflicts(self):
        has_conflicts = False
        titles_seen = Counter()
        
        movie_target_dir = self.parent_app.settings.get("directories", {}).get("movies", "")

        for movie_entry in self.movies_data:
            current_status = "Ready"
            tags = ('ready',)

            # Check for duplicate titles among selected movies
            titles_seen[movie_entry["assumed_title"]] += 1
            if titles_seen[movie_entry["assumed_title"]] > 1:
                current_status = "Conflict: Duplicate Title"
                tags = ('conflict',)
                has_conflicts = True
            
            # Check if target folder already exists on disk
            target_folder = os.path.join(movie_target_dir, movie_entry["assumed_title"])
            if os.path.exists(target_folder) and not os.path.samefile(target_folder, os.path.dirname(movie_entry["original_path"])):
                current_status = "Conflict: Target Folder Exists"
                tags = ('conflict',)
                has_conflicts = True

            movie_entry["status"] = current_status
            if movie_entry["tree_id"]:
                self.movies_tree.item(movie_entry["tree_id"], tags=tags, values=(
                    os.path.basename(movie_entry["original_path"]),
                    movie_entry["assumed_title"],
                    os.path.relpath(movie_entry["proposed_path"], movie_target_dir),
                    movie_entry["status"]
                ))
        
        self.apply_btn.config(state="disabled" if has_conflicts else "normal")

    def _capture_state(self):
        # Capture a deep copy of movies_data
        state = [entry.copy() for entry in self.movies_data]
        
        if not self.local_undo_stack or self.local_undo_stack[-1] != state:
            self.local_undo_stack.append(state)
            self.local_redo_stack.clear()
            self._update_undo_redo_buttons()

    def _restore_state(self, state):
        self.movies_data = [entry.copy() for entry in state] # Restore deep copy
        self._update_movies_tree()
        self._check_conflicts()

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

    def apply_changes(self):
        staging_dir = self.parent_app.settings.get("directories", {}).get("staging")
        movie_target_dir = self.parent_app.settings.get("directories", {}).get("movies")

        if not staging_dir or not movie_target_dir:
            messagebox.showerror("Error", "Staging or Movie directory is not configured.")
            return

        all_moves: List[Tuple[str, str]] = []
        failures: List[str] = []

        for movie_entry in self.movies_data:
            original_path = movie_entry["original_path"]
            proposed_path = movie_entry["proposed_path"]
            assumed_title = movie_entry["assumed_title"]

            # Ensure the target movie folder exists
            target_movie_folder = os.path.join(movie_target_dir, assumed_title)
            os.makedirs(target_movie_folder, exist_ok=True)

            # Construct the final destination path for the file
            final_file_destination = os.path.join(target_movie_folder, os.path.basename(original_path))
            
            if os.path.abspath(original_path) != os.path.abspath(final_file_destination):
                all_moves.append((original_path, final_file_destination))
        
        if not all_moves:
            messagebox.showinfo("Organize", "No changes to apply.")
            return

        if not messagebox.askyesno("Confirm Changes", f"Apply {len(all_moves)} file/folder operations?"):
            return

        description = f"Organize {len(self.movies_data)} Movies"
        action = BatchAction(description, all_moves)
        failures = self.parent_app.history.execute_action(action, stop_at=staging_dir)

        if failures:
            messagebox.showerror("Operation Failed", "Some operations failed. Please review the changes.\n\n" + "\n".join(failures))
        
        # Prune original source folders (if they were folders)
        for series_obj in self.series_list:
            original_source_folder = os.path.join(staging_dir, series_obj.name)
            if os.path.isdir(original_source_folder):
                prune_empty_dirs(original_source_folder, stop_at=staging_dir)

        self.destroy()
        self.parent_app.scan_root()
