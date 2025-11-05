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
from media_models import Episode, Season, Series, BatchAction, HistoryManager, suggest_series_name, parse_episode_info, parse_movie_info, predict_new_filename, predict_new_movie_filename, prune_empty_dirs, load_settings, save_settings, load_patterns, save_patterns, VIDEO_EXTS, DEFAULT_SETTINGS

class SeriesOrganizeDialog(tk.Toplevel):
    def __init__(self, parent_app, series_list: List[Series], media_type: str):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.series_list = series_list
        self.media_type = media_type
        self.is_combine_mode = len(series_list) > 1
        self.target_series = series_list[0] # For initial naming suggestion

        self.title(f"Organize {media_type}" if not self.is_combine_mode else f"Combine {media_type}s")
        self.transient(parent_app)
        self.grab_set()

        self.local_undo_stack = []
        self.local_redo_stack = []
        self._preview_row_to_target_id: Dict[str, str] = {}
        self.structure_changed = False # Flag to indicate if the target tree has been modified

        self._build_ui()
        self.populate_trees()
        self.suggest_name()
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
        self.rowconfigure(1, weight=1)

        # Top Frame for Series Name and Suggestion
        top_frame = tb.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        tb.Label(top_frame, text="Final Series Name:").pack(side="left")
        self.target_name_var = tk.StringVar(value=self.target_series.name)
        self.target_name_var.trace_add("write", lambda *_: (self._update_preview_tree(), self.target_tree.item(self.target_tree_root_id, text=self.target_name_var.get())))
        self.target_name_entry = tb.Entry(top_frame, textvariable=self.target_name_var)
        self.target_name_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Disable series name entry for Anime Movie if it's a single series
        if self.media_type == "Anime Movie" and not self.is_combine_mode:
            self.target_name_entry.config(state="disabled")
            self.target_name_var.set(self.target_series.name) # Keep original series name

        suggestion_frame = tb.Frame(top_frame)
        suggestion_frame.pack(side='left')
        tb.Label(suggestion_frame, text="Suggestion:").pack(side="left", padx=(10, 2))
        self.suggestion_label = tb.Label(suggestion_frame, text="", bootstyle="info", cursor="hand2")
        self.suggestion_label.pack(side="left")
        self.suggestion_label.bind("<Button-1>", self.apply_suggestion)

        # Main Paned Window for Source, Actions, Target, and Preview
        main_paned = tb.PanedWindow(self, orient="vertical", bootstyle="info")
        main_paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Top Paned Window for Source, Actions, Target
        top_paned = tb.PanedWindow(main_paned, orient="horizontal", bootstyle="info")
        
        # Source Frame
        source_frame = tb.Frame(top_paned)
        tb.Label(source_frame, text="Source Files", bootstyle="inverse-primary", padding=5).pack(fill="x")
        self.source_tree = tb.Treeview(source_frame, selectmode="extended")
        self.source_tree.pack(fill="both", expand=True)
        self.source_tree.bind("<<TreeviewSelect>>", self._on_source_selection_change)
        top_paned.add(source_frame, weight=1)

    def _on_source_selection_change(self, event=None):
        selected_items = self.source_tree.selection()
        state = "normal" if selected_items else "disabled"
        self.move_season_btn.config(state=state)
        self.move_specials_btn.config(state=state)
        self.move_custom_btn.config(state=state)
        if self.media_type == "Anime Movie" and self.move_movies_btn:
            self.move_movies_btn.config(state=state)

        # Action Frame
        action_frame = tb.Frame(top_paned, padding=10)
        self.move_season_btn = tb.Button(action_frame, text="Move to Season >>", command=self.move_selection_to_season, bootstyle="outline-info", state="disabled")
        self.move_season_btn.pack(pady=5, fill="x")
        self.move_specials_btn = tb.Button(action_frame, text="Move to Specials >>", command=lambda: self.move_selection_to_folder("Specials"), bootstyle="outline-info", state="disabled")
        self.move_specials_btn.pack(pady=5, fill="x")
        
        # Conditionally show/hide/configure Move to Movies button
        if self.media_type == "Anime Movie":
            self.move_movies_btn = tb.Button(action_frame, text="Move to Movies >>", command=lambda: self.move_selection_to_folder("Movies"), bootstyle="outline-info", state="disabled")
            self.move_movies_btn.pack(pady=5, fill="x")
        else:
            self.move_movies_btn = None # Not used for other series types

        self.move_custom_btn = tb.Button(action_frame, text="Move to... >>", command=self.move_selection_to_custom_folder, bootstyle="outline-info", state="disabled")
        self.move_custom_btn.pack(pady=5, fill="x")
        tb.Separator(action_frame, orient="horizontal").pack(fill="x", pady=20)
        self.undo_btn = tb.Button(action_frame, text="Undo", command=self.undo_local_change, bootstyle="outline-warning", state="disabled")
        self.undo_btn.pack(pady=5, fill="x")
        self.redo_btn = tb.Button(action_frame, text="Redo", command=self.redo_local_change, bootstyle="outline-info", state="disabled")
        self.redo_btn.pack(pady=5, fill="x")
        top_paned.add(action_frame)

        # Target Frame
        target_frame = tb.Frame(top_paned)
        tb.Label(target_frame, text="Target Structure", bootstyle="inverse-success", padding=5).pack(fill="x")
        self.target_tree = tb.Treeview(target_frame, selectmode="extended")
        self.target_tree.pack(fill="both", expand=True)
        self.target_tree.tag_configure('conflict', foreground='red')
        self.target_tree.bind("<Double-Button-3>", self._on_target_tree_double_right_click)
        self.target_tree.bind("<Double-1>", self._on_target_tree_left_double_click)
        
        self.target_tree_root_id = self.target_tree.insert("", "end", text="Loading...", open=True)
        
        top_paned.add(target_frame, weight=1)
        
        main_paned.add(top_paned, weight=3)

        # Preview Container
        preview_container = tb.Frame(main_paned)
        
        tb.Label(preview_container, text="Rename Preview", bootstyle="inverse-primary", padding=5).pack(fill="x")
        
        preview_frame = tb.Frame(preview_container)
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_tree = tb.Treeview(preview_frame, columns=("current", "new"), show="headings", selectmode="extended")
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        vsb = tb.Scrollbar(preview_frame, orient="vertical", command=self.preview_tree.yview, bootstyle="primary-round")
        vsb.grid(row=0, column=1, sticky="ns")
        self.preview_tree.configure(yscrollcommand=vsb.set)
        self.preview_tree.heading("current", text="Current Name")
        self.preview_tree.heading("new", text="New Name")
        self.preview_tree.column("current", anchor="w", width=350, stretch=True)
        self.preview_tree.column("new", anchor="w", width=250, stretch=True)
        self.preview_tree.tag_configure('conflict', foreground='red')
        self.preview_tree.bind("<Double-Button-3>", self._on_preview_tree_double_right_click)

        self.apply_preview_rename_btn = tb.Button(preview_container, text="Apply Renames to Target Structure", command=self._apply_preview_renames, bootstyle="outline-success")
        self.apply_preview_rename_btn.pack(side="bottom", fill="x", padx=5, pady=(0,5))

        main_paned.add(preview_container, weight=2)
        
        # Bottom Frame for Processed Checkbox and Apply/Cancel Buttons
        bottom_frame = tb.Frame(self)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.processed_var = tk.BooleanVar(value=False) # Default to False, will be set by logic
        tb.Checkbutton(bottom_frame, text="Mark as Processed", variable=self.processed_var).pack(side="left", padx=10)
        
        btn_text = "Combine" if self.is_combine_mode else "Apply Changes"
        self.apply_btn = tb.Button(bottom_frame, text=btn_text, command=self.apply_changes, bootstyle="outline-success")
        self.apply_btn.pack(side="right", padx=5)
        tb.Button(bottom_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").pack(side="right")

    def populate_trees(self):
        self.source_tree.delete(*self.source_tree.get_children())
        self.target_tree.delete(*self.target_tree.get_children())
        
        # Re-create the root node for the target tree
        self.target_tree_root_id = self.target_tree.insert("", "end", text=self.target_series.name, open=True)

        for series in self.series_list:
            self._populate_tree_with_series_files(self.source_tree, series)
        
        # Initially populate target tree with the current structure of target_series
        self._populate_tree_with_series_files(self.target_tree, self.target_series, is_target_tree=True, parent_node_id=self.target_tree_root_id)

        self._update_preview_tree()
        self._capture_state()

    def _populate_tree_with_series_files(self, tree, series, is_target_tree=False, parent_node_id=None):
        staging_dir = self.parent_app.settings.get("directories", {}).get("staging", "")
        series_path = os.path.join(staging_dir, series.name)
        
        def add_to_tree(parent_id, current_path):
            try:
                for entry_name in sorted(os.listdir(current_path)):
                    full_path = os.path.join(current_path, entry_name)
                    if os.path.isdir(full_path):
                        child_id = tree.insert(parent_id, "end", text=entry_name, open=False, tags=(full_path,))
                        add_to_tree(child_id, full_path)
                    else:
                        if is_target_tree:
                            tree.insert(parent_id, "end", text=entry_name, tags=(full_path, entry_name))
                        else:
                            tree.insert(parent_id, "end", text=entry_name, tags=(full_path,))
            except FileNotFoundError:
                pass 
        
        if os.path.exists(series_path):
            if parent_node_id is None:
                series_id = tree.insert("", "end", text=series.name, open=True, tags=(series_path,))
                add_to_tree(series_id, series_path)
            else:
                add_to_tree(parent_node_id, series_path)

    def move_selection_to_season(self):
        self.structure_changed = True
        season_num = simpledialog.askinteger("Season Number", "Enter season number:", parent=self)
        if season_num is not None:
            self.move_selection_to_folder(f"Season {season_num:02d}")

    def move_selection_to_custom_folder(self):
        self.structure_changed = True
        folder_name = simpledialog.askstring("Folder Name", "Enter destination folder:", parent=self)
        if folder_name and folder_name.strip():
            self.move_selection_to_folder(folder_name.strip())

    def move_selection_to_folder(self, folder_name: str):
        self.structure_changed = True
        selection = self.source_tree.selection()
        if not selection: return

        # Determine the parent for the new folder (root of target tree)
        parent_for_new_folder = self.target_tree_root_id

        # Check if the folder already exists under the target root
        target_folder_id = None
        for child_id in self.target_tree.get_children(parent_for_new_folder):
            if self.target_tree.item(child_id, "text") == folder_name:
                target_folder_id = child_id
                break
        
        if not target_folder_id:
            target_folder_id = self.target_tree.insert(parent_for_new_folder, "end", text=folder_name, open=True)

        files_to_move: List[Tuple[str, str, str]] = []
        
        for item_id in selection:
            self._collect_files_recursively(self.source_tree, item_id, files_to_move)

        for _, source_path, basename in files_to_move:
            self.target_tree.insert(target_folder_id, "end", text=basename, tags=(source_path, basename))

        for item_id in selection:
            if self.source_tree.exists(item_id):
                self.source_tree.delete(item_id)
        
        self._prune_empty_source_folders()
        self._sort_target_tree()
        self._check_target_conflicts()
        self._update_preview_tree()
        self._capture_state()

    def _prune_empty_source_folders(self):
        while True:
            pruned_this_pass = False
            all_items = self._get_all_children(self.source_tree, "")
            for item_id in reversed(all_items):
                if self.source_tree.exists(item_id) and not self.source_tree.get_children(item_id) and self.source_tree.item(item_id, "tags"):
                    path = self.source_tree.item(item_id, "tags")[0]
                    if os.path.isdir(path):
                        self.source_tree.delete(item_id)
                        pruned_this_pass = True
            if not pruned_this_pass:
                break

    def _collect_files_recursively(self, tree, item_id, file_list):
        tags = tree.item(item_id, "tags")
        if not tags: return
        
        source_path = tags[0]
        if os.path.isfile(source_path):
            if not any(f[1] == source_path for f in file_list):
                file_list.append((item_id, source_path, os.path.basename(source_path)))
        
        for child_id in tree.get_children(item_id):
            self._collect_files_recursively(tree, child_id, file_list)

    def _get_all_children(self, tree, item_id: str) -> List[str]:
        children = []
        for child_id in tree.get_children(item_id):
            children.append(child_id)
            children.extend(self._get_all_children(tree, child_id))
        return children

    def _on_target_tree_double_right_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if not item_id: return
        self.structure_changed = True
        x, y, w, h = self.target_tree.bbox(item_id)
        entry = tb.Entry(self.target_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, self.target_tree.item(item_id, "text"))
        entry.focus()
        def save(e):
            new_name = entry.get().strip()
            if not new_name:
                messagebox.showerror("Invalid Name", "Name cannot be empty.")
                entry.destroy()
                return

            old_name = self.target_tree.item(item_id, "text")
            if new_name == old_name: # No change
                entry.destroy()
                return

            self.target_tree.item(item_id, text=new_name)

            if not self.target_tree.get_children(item_id): # It's a file if it has no children
                tags = list(self.target_tree.item(item_id, "tags"))
                if tags:
                    if len(tags) > 1:
                        tags[1] = new_name
                    else:
                        tags.append(new_name)
                    self.target_tree.item(item_id, tags=tuple(tags))
            
            entry.destroy()
            self._check_target_conflicts()
            self._update_preview_tree()
            self._capture_state()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def _on_target_tree_left_double_click(self, event):
        item_id = self.target_tree.identify_row(event.y)
        if item_id:
            self.target_tree.item(item_id, open=not self.target_tree.item(item_id, "open"))

    def suggest_name(self, event=None):
        if self.is_combine_mode:
            name_stems = [suggest_series_name(s.name, self.parent_app.fluff_patterns) for s in self.series_list]
            if name_stems:
                most_common_name = Counter(name_stems).most_common(1)[0][0]
                self.suggestion_label.config(text=most_common_name)
                return
        
        suggested = suggest_series_name(self.target_series.name, self.parent_app.fluff_patterns)
        self.suggestion_label.config(text=suggested)

    def apply_suggestion(self, event=None):
        self.target_name_var.set(self.suggestion_label.cget("text"))
    
    def _sort_target_tree(self):
        def sort_key(item_id):
            text = self.target_tree.item(item_id, "text")
            if text.lower() == 'movies': return (-1, 0)
            match = re.match(r'(?i)Season\s*(\d+)', text)
            if match: return (0, int(match.group(1)))
            if text.lower() == 'specials': return (1, 0)
            return (2, text.lower())

        items = list(self.target_tree.get_children(self.target_tree_root_id)) # Sort children of the root
        items.sort(key=sort_key)
        for i, item_id in enumerate(items):
            self.target_tree.move(item_id, self.target_tree_root_id, i)

    def _check_target_conflicts(self):
        folder_contents: Dict[str, List[str]] = {}
        has_conflicts = False

        def gather_basenames(item_id, parent_folder_name):
            item_text = self.target_tree.item(item_id, "text")
            is_folder = bool(self.target_tree.get_children(item_id))
            
            if is_folder:
                for child_id in self.target_tree.get_children(item_id):
                    gather_basenames(child_id, item_text)
            else:
                folder_contents.setdefault(parent_folder_name, []).append(item_text)

        # Start gathering from children of the target_tree_root_id
        for root_item_id in self.target_tree.get_children(self.target_tree_root_id):
            gather_basenames(root_item_id, "__root__") # Use __root__ as a placeholder for the top-level items

        conflicts_by_folder: Dict[str, set] = {}
        for folder, files in folder_contents.items():
            counts = Counter(files)
            conflicts = {name for name, count in counts.items() if count > 1}
            if conflicts:
                conflicts_by_folder[folder] = conflicts
                has_conflicts = True

        def tag_conflicts(item_id, parent_folder_name):
            item_text = self.target_tree.item(item_id, "text")
            is_folder = bool(self.target_tree.get_children(item_id))
            
            current_tags = list(self.target_tree.item(item_id, "tags")) if self.target_tree.item(item_id, "tags") else []
            if 'conflict' in current_tags: current_tags.remove('conflict')
            
            if not is_folder:
                if parent_folder_name in conflicts_by_folder and item_text in conflicts_by_folder[parent_folder_name]:
                    current_tags.append('conflict')

            self.target_tree.item(item_id, tags=tuple(current_tags))
            
            if is_folder:
                for child_id in self.target_tree.get_children(item_id):
                    tag_conflicts(child_id, item_text)
        
        # Start tagging from children of the target_tree_root_id
        for root_item_id in self.target_tree.get_children(self.target_tree_root_id):
             tag_conflicts(root_item_id, "__root__")

        self.apply_btn.config(state="disabled" if has_conflicts else "normal")

    def _update_preview_tree(self):
        self.preview_tree.delete(*self.preview_tree.get_children())
        self._preview_row_to_target_id.clear()

        series_name = self.target_name_var.get()
        if not series_name:
            return

        for folder_id in self.target_tree.get_children(self.target_tree_root_id): # Iterate children of the root
            folder_name = self.target_tree.item(folder_id, "text")
            
            for file_id in self.target_tree.get_children(folder_id):
                basename = self.target_tree.item(file_id, "text")
                
                tags = self.target_tree.item(file_id, "tags")
                path = tags[0] if tags else basename
                
                ep = Episode(path)
                ep.series_name = series_name
                
                pred_full = None
                if folder_name.lower() == "movies": # Movies folder within a series
                    ep.series_name = self.target_tree.item(file_id, "text").split('.')[0] # Use filename as movie title
                    ep.year = parse_movie_info(basename) # Try to parse year from basename
                    pred_full = predict_new_movie_filename(ep, self.parent_app.settings)
                else: # Seasons, Specials, or custom folders
                    m = re.search(r'(?i)Season\s*(\d+)', folder_name)
                    season_num = None
                    if m:
                        season_num = int(m.group(1))
                    elif folder_name.lower() == "specials":
                        season_num = 0
                    ep.season = season_num
                    _, parsed_ep = parse_episode_info(basename)
                    ep.parsed_episode_num = parsed_ep
                    pred_full = predict_new_filename(ep, self.parent_app.settings)
                
                row_tags = ()
                if pred_full is None:
                    pred_display = os.path.splitext(ep.original_basename)[0]
                    row_tags = ('unnamed',)
                else:
                    pred_display = os.path.splitext(pred_full)[0]

                current_name_no_ext, _ = os.path.splitext(basename)
                current_display = current_name_no_ext
                
                # Add prefix for display in current name column
                if folder_name.lower() == "movies":
                    current_display = f"[M] {current_name_no_ext}"
                elif ep.season is not None:
                    current_display = f"[S{ep.season:02d}] {current_name_no_ext}"
                
                row_id = self.preview_tree.insert("", "end", values=(current_display, pred_display), tags=row_tags)
                self._preview_row_to_target_id[row_id] = file_id

        self.preview_tree.tag_configure('unnamed', foreground='yellow')
        self._check_preview_conflicts()

    def _check_preview_conflicts(self):
        all_new_names = [self.preview_tree.set(row_id, "new") for row_id in self.preview_tree.get_children()]
        counts = Counter(all_new_names)
        conflicts = {name for name, count in counts.items() if count > 1 and name != "(Cannot determine new name)"}
        for row_id in self.preview_tree.get_children():
            name = self.preview_tree.set(row_id, "new")
            self.preview_tree.item(row_id, tags=('conflict',) if name in conflicts else ())
        self.apply_preview_rename_btn.config(state="disabled" if conflicts else "normal")

    def _apply_preview_renames(self):
        if 'disabled' in self.apply_preview_rename_btn.state():
            messagebox.showerror("Conflicts Found", "Please resolve filename conflicts in the preview (marked in red) before applying.")
            return

        self.structure_changed = True
        for preview_id in self.preview_tree.get_children():
            target_id = self._preview_row_to_target_id.get(preview_id)
            if not target_id: continue

            original_basename = self.target_tree.item(target_id, "text")
            _, ext = os.path.splitext(original_basename)
            new_name_no_ext_from_preview = self.preview_tree.set(preview_id, "new")
            
            new_full_filename = new_name_no_ext_from_preview + ext

            self.target_tree.item(target_id, text=new_full_filename, tags=(self.target_tree.item(target_id, "tags")[0], new_full_filename))
        
        self._check_target_conflicts()
        self._update_preview_tree()
        self._capture_state()

    def _on_preview_tree_double_right_click(self, event):
        row_id = self.preview_tree.identify_row(event.y)
        if not row_id or self.preview_tree.identify_column(event.x) != "#2": return
        
        x, y, w, h = self.preview_tree.bbox(row_id, column="new")
        entry = tb.Entry(self.preview_tree, bootstyle="warning")
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, self.preview_tree.set(row_id, "new"))
        entry.focus()
        
        def save(e):
            self.preview_tree.set(row_id, "new", entry.get().strip())
            entry.destroy()
            self._check_preview_conflicts()
        
        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

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
        
        if not self.local_undo_stack or self.local_undo_stack[-1] != state:
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
        self._update_preview_tree()

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
        final_series_name = self.target_name_var.get().strip()
        if not final_series_name:
            messagebox.showerror("Invalid Name", "Final series name cannot be empty.")
            return

        staging_dir = self.parent_app.settings.get("directories", {}).get("staging")
        if not staging_dir:
            messagebox.showerror("Error", "Staging directory is not configured.")
            return

        # Determine the base path for the final series structure based on media_type
        if self.media_type == "TV Series":
            base_media_dir = self.parent_app.settings.get("directories", {}).get("tv_shows", staging_dir)
        elif self.media_type == "Anime" or self.media_type == "Anime Movie":
            base_media_dir = self.parent_app.settings.get("directories", {}).get("anime", staging_dir)
        else: # Fallback, though should be caught by MediaTypeSelectionDialog
            base_media_dir = staging_dir
        
        final_destination_root = os.path.join(base_media_dir, final_series_name)

        all_moves: List[Tuple[str, str]] = []
        failures: List[str] = []

        # Plan moves from the children of the root node in the target tree
        for child_id in self.target_tree.get_children(self.target_tree_root_id):
            self._plan_moves_from_tree_recursive(child_id, final_destination_root, all_moves)
        
        if not all_moves:
            messagebox.showinfo("Organize", "No changes to apply.")
            return

        if not messagebox.askyesno("Confirm Changes", f"Apply {len(all_moves)} file/folder operations?"):
            return

        description = f"Organize {self.media_type}: {final_series_name}"
        action = BatchAction(description, all_moves)
        failures = self.parent_app.history.execute_action(action, stop_at=staging_dir)

        if failures:
            messagebox.showerror("Operation Failed", "Some operations failed. Please review the changes.\n\n" + "\n".join(failures))
        
        # Prune original source folders
        source_folders_to_prune = {os.path.join(staging_dir, s.name) for s in self.series_list}
        for path in source_folders_to_prune:
            if os.path.abspath(path) != os.path.abspath(final_destination_root):
                prune_empty_dirs(path, stop_at=staging_dir)

        self.destroy()
        self.parent_app.scan_root()

    def _plan_moves_from_tree_recursive(self, item_id, current_destination_parent_path, all_moves_list):
        text = self.target_tree.item(item_id, "text")
        tags = self.target_tree.item(item_id, "tags")
        
        original_source_path = tags[0] if tags else None
        
        is_folder = bool(self.target_tree.get_children(item_id))

        if is_folder:
            intended_new_name = text
            current_destination_path = os.path.join(current_destination_parent_path, intended_new_name)
            
            for child_id in self.target_tree.get_children(item_id):
                self._plan_moves_from_tree_recursive(child_id, current_destination_path, all_moves_list)
        else:
            intended_new_name = tags[1] if len(tags) > 1 else os.path.basename(original_source_path)
            current_destination_path = os.path.join(current_destination_parent_path, intended_new_name)

            if original_source_path and os.path.isfile(original_source_path):
                if os.path.abspath(original_source_path) != os.path.abspath(current_destination_path):
                    all_moves_list.append((original_source_path, current_destination_path))
