#!/usr/bin/env python3
"""
JMAD Media Tool
A robust TV series and media renamer application.
Version: 6.8 (Advanced Organize Dialog)
"""
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, scrolledtext, ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from typing import Dict, List, Optional, Tuple, Set # Added Set for clean_files_tool
import os # Added
import shutil # Added
import media_models
from media_models import *

from media_type_selection_dialog import MediaTypeSelectionDialog # New Import
from series_organize_dialog import SeriesOrganizeDialog # New Import
from movie_organize_dialog import MovieOrganizeDialog # New Import

# -------------------------
# Configuration
# -------------------------
CURRENT_VERSION = "6.8"
UPDATE_CHECK_URL = "https://api.github.com/repos/yourusername/jmad-media-tool/releases/latest"
MEDIA_TYPES = ["", "TV Series", "Anime", "Movie", "Anime Movie"]




class ConsolePanel(tb.Frame):
    def __init__(self, parent, app_controller, initial_content=""):
        super().__init__(parent)
        self.app = app_controller
        self.docked = True
        self.undocked_window = None
        self.original_parent = parent
        self._content_buffer = initial_content

        self._build_ui()
        self.last_geometry = "600x400"
        
        if self._content_buffer:
            self._refresh_display()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self.header = tb.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        tb.Label(self.header, text="Console", bootstyle="inverse-primary", padding=5).grid(row=0, column=0, sticky="ew")
        
        self.hide_btn = tb.Button(self.header, text="Hide", command=self.app.toggle_console, bootstyle="toolbutton")
        self.hide_btn.grid(row=0, column=1, padx=2)

        self.text_frame = tb.Frame(self)
        self.text_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)

        self.scrolled_text = scrolledtext.ScrolledText(self.text_frame, wrap=tk.WORD, state="disabled", height=10) # Set initial height
        self.scrolled_text.grid(row=0, column=0, sticky="nsew")
        
        self.footer = tb.Frame(self)
        self.footer.grid(row=2, column=0, sticky="ew", padx=5, pady=(0,5))
        
        self.dock_btn = tb.Button(self.footer, text="Undock", command=self.toggle_dock, bootstyle="outline-secondary")
        self.dock_btn.pack(side="left")
        
        tb.Button(self.footer, text="Clear", command=self.clear, bootstyle="outline-danger").pack(side="right")

    def log(self, message):
        self._content_buffer += message + "\n"
        self.scrolled_text.config(state="normal")
        self.scrolled_text.insert(tk.END, message + "\n")
        self.scrolled_text.config(state="disabled")
        self.scrolled_text.see(tk.END)

    def clear(self):
        self._content_buffer = ""
        self.scrolled_text.config(state="normal")
        self.scrolled_text.delete(1.0, tk.END)
        self.scrolled_text.config(state="disabled")
        self.log("Console cleared.")
    
    def _refresh_display(self):
        self.scrolled_text.config(state="normal")
        self.scrolled_text.delete(1.0, tk.END)
        self.scrolled_text.insert(1.0, self._content_buffer)
        self.scrolled_text.config(state="disabled")
        self.scrolled_text.see(tk.END)
    
    def get_content(self):
        return self._content_buffer
    
    def toggle_dock(self):
        if self.docked:
            content = self.get_content()
            self.undocked_window = tk.Toplevel(self.app)
            self.undocked_window.title("JMAD Media Tool - Console")
            self.undocked_window.geometry("600x400")
            self.undocked_window.configure(bg=self.app.style.colors.bg)
            
            new_console = ConsolePanel(self.undocked_window, self.app, content)
            new_console.pack(fill="both", expand=True, padx=5, pady=5)
            new_console.docked = False
            new_console.dock_btn.config(text="Dock")
            new_console.undocked_window = self.undocked_window
            new_console.original_parent = self.original_parent
            
            self.app.console = new_console
            self.destroy()
            self.undocked_window.protocol("WM_DELETE_WINDOW", new_console.toggle_dock)
            self.app._update_layout_after_console_change()
        else:
            if self.undocked_window:
                content = self.get_content()
                new_console = ConsolePanel(self.original_parent, self.app, content)
                new_console.pack(fill="both", expand=True)
                new_console.docked = True
                new_console.dock_btn.config(text="Undock")
                
                self.app.console = new_console
                self.undocked_window.destroy()
                self.app._update_layout_after_console_change()

class CleanupPanel(tb.Frame):
    ALL_CLEANUP_EXTS = media_models.CLEANUP_EXTS

    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        self.selected_exts = {} # To store BooleanVar for each extension
        self.custom_exts_var = tk.StringVar() # Initialize without value, will be set from settings
        self.cleanup_button_text_var = tk.StringVar() # New: StringVar for dynamic button text
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1) # Allow column to expand

        tb.Label(self, text="Cleanup Tool", bootstyle="inverse-primary", padding=5, anchor="center").grid(row=0, column=0, sticky="ew")

        # Load cleanup settings
        cleanup_settings = self.app.settings.get("cleanup_ext_states", DEFAULT_SETTINGS["cleanup_ext_states"])
        initial_selected_exts = set(cleanup_settings.get("selected", DEFAULT_SETTINGS["cleanup_ext_states"]["selected"])) # Convert to set for efficient lookup
        self.custom_exts_var.set(cleanup_settings.get("custom_exts_str", DEFAULT_SETTINGS["cleanup_ext_states"]["custom_exts_str"])) # Set from loaded settings

        # All Cleanup Extensions
        all_exts_frame = tb.LabelFrame(self, text="Extensions to Clean", padding=10)
        all_exts_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        col_count = 3 # Aim for 3 columns
        for c in range(col_count):
            all_exts_frame.columnconfigure(c, weight=1) # Configure columns to expand

        for i, ext in enumerate(sorted(self.ALL_CLEANUP_EXTS)):
            row_idx = i // col_count
            col_idx = i % col_count
            
            var = tk.BooleanVar(value=(ext in initial_selected_exts)) # Initialize from loaded settings
            
            cb = tb.Checkbutton(all_exts_frame, text=ext, variable=var, bootstyle="round-toggle")
            cb.grid(row=row_idx, column=col_idx, sticky="w", padx=5, pady=2)
            self.selected_exts[ext] = var

        # Custom Extensions Input
        custom_frame = tb.LabelFrame(self, text="Custom Extensions (comma-separated)", padding=10)
        custom_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        custom_frame.columnconfigure(0, weight=1) # Allow entry to expand
        tb.Entry(custom_frame, textvariable=self.custom_exts_var).grid(row=0, column=0, sticky="ew", padx=5, pady=2);

        tb.Button(self, textvariable=self.cleanup_button_text_var, command=self._run_cleanup, bootstyle="danger").grid(row=3, column=0, pady=10)

        # Configure rows to expand
        self.rowconfigure(1, weight=1) # All extensions frame
        self.rowconfigure(2, weight=1) # Custom extensions frame
        self.rowconfigure(3, weight=0) # Button row - do not expand, but ensure it's there

    def _run_cleanup(self):
        selected_extensions_for_cleanup = {ext for ext, var in self.selected_exts.items() if var.get()}
        
        # Add custom extensions
        custom_exts_str = self.custom_exts_var.get().strip()
        if custom_exts_str:
            # Split by comma, strip whitespace, add leading dot if missing, convert to lowercase
            parsed_custom_exts = {f".{e.strip().lstrip('.')}" for e in custom_exts_str.split(',') if e.strip()}
            selected_extensions_for_cleanup.update(parsed_custom_exts)

        # Save current state of cleanup settings
        self.app.settings["cleanup_ext_states"] = {
            "selected": list(selected_extensions_for_cleanup), # Convert set to list for JSON serialization
            "custom_exts_str": custom_exts_str
        }
        media_models.save_settings(self.app.settings) # Save the updated settings to file

        self.app.clean_files_tool(selected_extensions_for_cleanup)

# -------------------------
# Main Application Window
# -------------------------
class JMADMediaTool(tk.Tk):
    def __init__(self, settings: dict, patterns: List[str]):
        super().__init__()
        self.style = tb.Style(theme="darkly")
        self.title("JMAD Media Tool")
        self.geometry("1400x800")

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        icon_path = os.path.join(base_path, "JMADMMT.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Could not set icon: {e}")

        self.settings = settings
        self.fluff_patterns = patterns # Initialize fluff_patterns
        self.series_map: Dict[str, media_models.Series] = {}
        self._tooltip_win: Optional[tk.Toplevel] = None
        self._build_ui()
        self.history = media_models.HistoryManager(self.console.log)
        self.after(100, self.post_init_tasks)

    def post_init_tasks(self):
        media_models.create_portable_dirs()
        self.scan_root()
        # self.check_for_updates_simulated()
        self._update_layout_after_console_change()
        self._update_cleanup_button_text() # New: Initial update of cleanup button text

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        toolbar = tb.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        
        tb.Button(toolbar, text="Scan", command=self.scan_root, bootstyle="outline-success").pack(side="left", padx=4)
        tb.Button(toolbar, text="Settings", command=self.open_settings, bootstyle="outline-light").pack(side="left", padx=4)
        
        self.tools_menubutton = tb.Menubutton(toolbar, text="Tools", bootstyle="outline-info")
        self.tools_menubutton.pack(side="left", padx=4)
        self._build_tools_menu()
        
        tb.Button(toolbar, text="Catalog", state="disabled").pack(side="left", padx=4)

        tb.Button(toolbar, text="Redo", command=self.redo_action, bootstyle="outline-info").pack(side="right", padx=4)
        tb.Button(toolbar, text="Undo", command=self.undo_action, bootstyle="outline-warning").pack(side="right")
        
        main_paned = tb.PanedWindow(self, orient="horizontal", bootstyle="primary")
        main_paned.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        
        left_frame = tb.Frame(main_paned)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        header_frame = tb.Frame(left_frame)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(0, weight=1)
        tb.Label(header_frame, text="Media Tree", bootstyle="inverse-primary", padding=5).grid(row=0, column=0, sticky="ew")

        tree_container = tb.Frame(left_frame)
        tree_container.grid(row=1, column=0, sticky='nsew', padx=6, pady=6)
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        self.series_tree = tb.Treeview(tree_container, selectmode="extended", bootstyle="primary", columns=("media_type"))
        self.series_tree.grid(row=0, column=0, sticky="nsew")
        self.series_tree.heading("#0", text="Series Name")
        self.series_tree.heading("media_type", text="Media Type")
        self.series_tree.column("#0", stretch=True, width=250)
        self.series_tree.column("media_type", width=100, anchor="w")

        self.series_tree.tag_configure('nonstandard', foreground='orange')
        vsb_left = tb.Scrollbar(tree_container, orient="vertical", command=self.series_tree.yview, bootstyle="primary-round")
        vsb_left.grid(row=0, column=1, sticky="ns")
        self.series_tree.configure(yscrollcommand=vsb_left.set)
        self.series_tree.bind("<<TreeviewSelect>>", self.on_series_selection)
        self.series_tree.bind("<Button-3>", self.on_series_right_click)
        self.series_tree.bind("<Control-a>", self._select_all)
        self.series_tree.bind("<Button-1>", self._clear_selection)
        self.series_tree.bind("<<TreeviewOpen>>", self._on_tree_open) # New: Bind to handle deep expansion # New: Bind left-click for deselection
        main_paned.add(left_frame, weight=2)
        
        self.right_frame = tb.Frame(main_paned)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        
        self.right_paned = tb.PanedWindow(self.right_frame, orient="vertical", bootstyle="primary")
        self.right_paned.grid(row=0, column=0, sticky="nsew") # Removed expand=True
        
        self.cleanup_container = tb.Frame(self.right_paned) # New container for cleanup panel
        self.console_container = tb.Frame(self.right_paned)
        
        self.cleanup_panel = CleanupPanel(self.cleanup_container, self) # New cleanup panel
        self.cleanup_panel.pack(fill="both", expand=True)
        
        self.console = ConsolePanel(self.console_container, self)
        self.console.pack(fill="both", expand=True)
        
        self.right_paned.add(self.cleanup_container, weight=4) # Cleanup takes 4/5
        self.right_paned.add(self.console_container, weight=1) # Console takes 1/5
        
        main_paned.add(self.right_frame, weight=3)
        
    def _update_layout_after_console_change(self):
        current_panes = self.right_paned.panes()
        is_console_pane_visible = str(self.console_container) in current_panes
        should_be_visible = self.console.docked and self.settings.get("console_visible", True)

        if should_be_visible and not is_console_pane_visible:
            self.right_paned.add(self.console_container, weight=1)
        elif not should_be_visible and is_console_pane_visible:
            self.right_paned.remove(self.console_container)
        
        self.update_idletasks()
        
    def _build_tools_menu(self):
        tools_menu = tk.Menu(self.tools_menubutton, tearoff=0)
        
        move_menu = tk.Menu(tools_menu, tearoff=0)
        self._populate_move_menu(move_menu)
        tools_menu.add_cascade(label="Move Selected To...", menu=move_menu)
        
        tools_menu.add_separator()
        console_text = "Show Console" if not self.settings.get("console_visible", True) else "Hide Console"
        tools_menu.add_command(label=console_text, command=self.toggle_console)

        self.tools_menubutton["menu"] = tools_menu

    def _populate_move_menu(self, menu):
        menu.delete(0, "end")
        presets = self.settings.get("move_presets", [])
        if presets:
            for preset in presets:
                menu.add_command(label=preset, command=lambda p=preset: self.move_series_tool(destination=p))
            menu.add_separator()
        
        menu.add_command(label="Choose Location...", command=self.move_series_tool)

    def scan_root(self):
        self.log(f"Scanning directories...")
        self.series_map = media_models.scan_media_roots(self.settings)
        self.populate_series_tree() # Added this line
        self.log(f"Scan complete. Found {len(self.series_map)} series.")

    def populate_series_tree(self):
        self.series_tree.delete(*self.series_tree.get_children())
        for sname in sorted(self.series_map.keys(), key=str.lower):
            series = self.series_map[sname]
            if not series.get_all_episodes(): continue
            tags = ('nonstandard',) if series.has_nonstandard_folders else ()
            top_id = self.series_tree.insert("", "end", text=sname, open=False, tags=tags, values=(getattr(series, '_inferred_media_type', 'Unknown'),))
            
            season_keys = sorted(series.seasons.keys())
            if season_keys:
                for season_idx in season_keys:
                    if season_idx == -1: label = "Movies"
                    elif season_idx == 0: label = "Specials"
                    else: label = f"Season {season_idx:02d}"
                    self.series_tree.insert(top_id, "end", text=label)

            if series.unsorted:
                unsorted_id = self.series_tree.insert(top_id, "end", text="Unsorted", open=False)
                for ep in series.unsorted:
                    self.series_tree.insert(unsorted_id, "end", text=ep.basename())

    def on_series_selection(self, event=None):
        selection = self.series_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        parent_id = self.series_tree.parent(item_id)
        series_name = self.series_tree.item(parent_id or item_id, "text")
        series = self.series_map.get(series_name)

    def on_series_right_click(self, event):
        item_id = self.series_tree.identify_row(event.y)
        if not item_id: return
        current_selection = self.series_tree.selection()
        if item_id not in current_selection:
            self.series_tree.selection_set((item_id,))
            current_selection = (item_id,)
        menu = tb.Menu(self, tearoff=0)
        top_level_items = [item for item in current_selection if not self.series_tree.parent(item)]
        
        if top_level_items:
             menu.add_command(label="Organize / Combine Series...", command=lambda: self.open_organize_dialog(top_level_items))
             
             menu.add_separator()
             console_text = "Show Console" if not self.settings.get("console_visible", True) else "Hide Console"
             menu.add_command(label=console_text, command=self.toggle_console)
             menu.add_separator()
             
             tools_menu = tk.Menu(menu, tearoff=0)
             
             move_menu = tk.Menu(tools_menu, tearoff=0)
             self._populate_move_menu(move_menu)
             tools_menu.add_cascade(label="Move Selected To...", menu=move_menu)

             menu.add_cascade(label="Tools", menu=tools_menu)

        if menu.index('end') is not None:
            menu.post(event.x_root, event.y_root)
            
    def set_series_type(self, item_ids: List[str], media_type: str):
        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root: return

        series_to_process = [self.series_map[self.series_tree.item(item_id, "text")] for item_id in item_ids]

        if media_type == "Anime Movie":
            # Instead of AssociateMovieDialog, open OrganizeDialog with a flag
            # The OrganizeDialog will handle the association UI dynamically
            self.open_organize_dialog(item_ids, pre_selected_media_type="Anime Movie")
            return

        for series in series_to_process:
            series.media_type = media_type
            series.is_processed = bool(media_type) # Mark as processed if a media_type is assigned
        
        self.scan_root()

    def undo_action(self):
        if not self.history.can_undo(): return
        failures, _ = self.history.undo(stop_at=self.settings.get("directories", {}).get("staging"))
        if failures: messagebox.showwarning("Undo Failed", "\n".join(failures))
        self.scan_root()

    def redo_action(self):
        if not self.history.can_redo(): return
        failures, _ = self.history.redo(stop_at=self.settings.get("directories", {}).get("staging"))
        if failures: messagebox.showwarning("Redo Failed", "\n".join(failures))
        self.scan_root()

    def clear_history(self):
        if messagebox.askyesno("Clear History", "This will clear all undo/redo history. Continue?"):
            self.history.clear()

    def log(self, message):
        self.console.log(message)

    def open_settings(self):
        SettingsDialog(self)

    def open_organize_dialog(self, item_ids: List[str], pre_selected_media_type: Optional[str] = None):
        series_to_organize = [self.series_map[self.series_tree.item(item_id, "text")] for item_id in item_ids]
        if not series_to_organize:
            return

        selected_media_type = pre_selected_media_type
        if not selected_media_type:
            # If no pre-selected type, open the selection dialog
            dialog = MediaTypeSelectionDialog(self, MEDIA_TYPES[1:]) # Exclude empty string
            selected_media_type = dialog.show()

        if selected_media_type:
            if selected_media_type in ["TV Series", "Anime", "Anime Movie"]:
                SeriesOrganizeDialog(self, series_to_organize, selected_media_type)
            elif selected_media_type == "Movie":
                MovieOrganizeDialog(self, series_to_organize)
            else:
                self.log(f"Unsupported media type selected: {selected_media_type}")
        else:
            self.log("Media type selection cancelled.")

    def clean_files_tool(self, extensions_to_clean: Optional[Set[str]] = None):
        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root or not os.path.isdir(tv_root):
            messagebox.showwarning("Staging Directory Not Set", "Please configure a valid Staging directory in Settings.")
            return

        if extensions_to_clean is None:
            # If called from the Tools menu, use the default CLEANUP_EXTS
            extensions_to_clean = CLEANUP_EXTS
        
        selected_ids = [item for item in self.series_tree.selection() if not self.series_tree.parent(item)]

        target_paths = []
        if selected_ids:
            # Clean only selected series
            for item_id in selected_ids:
                series_name = self.series_tree.item(item_id, "text")
                target_paths.append(os.path.join(tv_root, series_name))
            scope_description = "selected series"
        else:
            # Clean entire staging directory
            target_paths.append(tv_root)
            scope_description = "entire staging directory"

        files_to_delete = []
        for path_to_scan in target_paths:
            for root, _, files in os.walk(path_to_scan):
                for f in files:
                    if os.path.splitext(f)[1].lower() in extensions_to_clean:
                        files_to_delete.append(os.path.join(root, f))
        
        if not files_to_delete:
            messagebox.showinfo("Clean Files", f"No files to clean in the {scope_description} with the selected extensions.")
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Found {len(files_to_delete)} files to clean in the {scope_description} (extensions: {', '.join(sorted(extensions_to_clean))}).\n\n"
            "This action is PERMANENT and CANNOT be undone.\n\n"
            "Are you sure you want to delete these files?"
        )

        if confirm:
            trash_dir = self.settings.get("directories", {}).get("trash")
            if not trash_dir or not os.path.isdir(trash_dir):
                messagebox.showwarning("Cleanup Error", "Trash directory is not configured or does not exist. Files will be permanently deleted.")
                perform_permanent_delete = True
            else:
                perform_permanent_delete = False

            moved_count = 0
            deleted_count = 0
            failed_count = 0
            for f_path in files_to_delete:
                try:
                    if perform_permanent_delete:
                        os.remove(f_path)
                        deleted_count += 1
                    else:
                        # Construct mirrored path in trash
                        relative_path = os.path.relpath(f_path, tv_root)
                        dest_path = os.path.join(trash_dir, relative_path)
                        
                        # Ensure destination directory exists
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        shutil.move(f_path, dest_path)
                        moved_count += 1
                except Exception as e:
                    failed_count += 1
                    self.log(f"Failed to move/delete {f_path}: {e}")
            
            if perform_permanent_delete:
                self.log(f"Cleaned {deleted_count} files (permanently deleted). Failed on {failed_count}.")
                messagebox.showinfo("Cleanup Complete", f"Successfully deleted {deleted_count} files.\nFailed to delete {failed_count} files.")
            else:
                self.log(f"Cleaned {moved_count} files (moved to trash). Failed on {failed_count}.")
                messagebox.showinfo("Cleanup Complete", f"Successfully moved {moved_count} files to trash.\nFailed to move {failed_count} files.")
            self.scan_root()

    def move_series_tool(self, destination: Optional[str] = None):
        selected_ids = [item for item in self.series_tree.selection() if not self.series_tree.parent(item)]
        if not selected_ids:
            messagebox.showwarning("No Series Selected", "Please select one or more top-level series folders to move.")
            return

        tv_root = self.settings.get("directories", {}).get("staging")
        if not tv_root: return
        
        if destination is None:
            destination = filedialog.askdirectory(title="Select Destination Folder", initialdir=tv_root)
        
        if not destination: return

        moves = []
        conflicts = []
        for item_id in selected_ids:
            series_name = self.series_tree.item(item_id, "text")
            src_path = os.path.join(tv_root, series_name)
            dst_path = os.path.join(destination, series_name)
            
            if os.path.exists(dst_path):
                conflicts.append(series_name)
            else:
                moves.append((src_path, dst_path))
        
        if conflicts:
            messagebox.showerror("Move Error", "The following series already exist in the destination and were not moved:\n\n" + "\n".join(conflicts))

        if not moves: return

        series_count = len(moves)
        if not messagebox.askyesno("Confirm Move", f"Move {series_count} series to the new location?"):
            return

        action = BatchAction(f"Move {series_count} series to '{os.path.basename(destination)}'", moves)
        failures = self.history.execute_action(action, stop_at=os.path.dirname(tv_root))
        
        if failures:
            messagebox.showerror("Move Failed", "Some series failed to move:\n\n" + "\n".join(failures))
        
        self.scan_root()

    def toggle_console(self):
        self.settings["console_visible"] = not self.settings.get("console_visible", True)
        save_settings(self.settings)

        if hasattr(self.console, 'hide_btn'):
            new_text = "Hide" if self.settings["console_visible"] else "Show"
            self.console.hide_btn.config(text=new_text)

        self._update_layout_after_console_change()
        self._build_tools_menu()
        
    def check_for_updates_simulated(self):
        latest_version = "7.0" 
        if CURRENT_VERSION < latest_version:
            if messagebox.askyesno("Update Available", f"Version {latest_version} is available.\nWould you like to update now?"):
                progress_win = tb.Toplevel(title="Downloading Update...")
                progress_win.geometry("300x100")
                pb = tb.Progressbar(progress_win, mode='determinate', bootstyle='success-striped')
                pb.pack(fill='x', padx=20, pady=20)
                progress_win.transient(self)
                progress_win.grab_set()

                def update_progress(val=0):
                    if val < 100:
                        pb.step(2)
                        progress_win.after(50, lambda: update_progress(val + 2))
                    else:
                        progress_win.destroy()
                        messagebox.showinfo("Update Complete", "Update downloaded. Please restart the application.")
                update_progress()

    def _select_all(self, event):
        widget = event.widget
        if isinstance(widget, tb.Treeview):
            all_items = self._get_all_tree_children(widget, "")
            widget.selection_set(all_items)
            return "break"
            
    def _get_all_tree_children(self, tree, item_id: str) -> List[str]:
        children = []
        for child_id in tree.get_children(item_id):
            children.append(child_id)
            children.extend(self._get_all_tree_children(tree, child_id))
        return children

    def _clear_selection(self, event):
        # Check if the click was on an item or on empty space
        if not self.series_tree.identify_row(event.y):
            self.series_tree.selection_remove(self.series_tree.selection())
            # Explicitly call _update_cleanup_button_text after clearing selection
            self._update_cleanup_button_text()

    def _expand_all_children(self, item_id):
        for child_id in self.series_tree.get_children(item_id):
            self.series_tree.item(child_id, open=True)
            self._expand_all_children(child_id) # Recursively expand children

    def _on_tree_open(self, event):
        item_id = self.series_tree.focus() # Get the ID of the item that was just opened
        if item_id:
            self._expand_all_children(item_id)

    def _update_cleanup_button_text(self, event=None):
        selected_items = self.series_tree.selection()
        if selected_items:
            num_selected = len(selected_items)
            self.cleanup_panel.cleanup_button_text_var.set(f"Run Cleanup ({num_selected} Selected Items)")
        else:
            self.cleanup_panel.cleanup_button_text_var.set("Run Cleanup (All Staging)")

# -------------------------
# Dialog Windows
# -------------------------
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: JMADMediaTool):
        super().__init__(parent)
        self.parent = parent
        self.settings = json.loads(json.dumps(parent.settings))
        self.patterns = parent.fluff_patterns[:]
        self.title("Settings")
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        self.resizable(True, True)
        self.minsize(600, 500)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        notebook = tb.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self._build_general_tab(notebook)
        self._build_patterns_tab(notebook)

        btn_frame = tb.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=(0, 10))
        btn_frame.columnconfigure(0, weight=1)
        tb.Button(btn_frame, text="Save", command=self._save, bootstyle="outline-success").grid(row=0, column=2, padx=6)
        tb.Button(btn_frame, text="Cancel", command=self.destroy, bootstyle="outline-danger").grid(row=0, column=1)

    def _build_general_tab(self, notebook):
        frm = tb.Frame(notebook, padding=10)
        notebook.add(frm, text="General")
        frm.columnconfigure(1, weight=1)

        tb.Label(frm, text="Episode Pattern:").grid(row=0, column=0, sticky="w", pady=6)
        self.ep_pattern_var = tk.StringVar(value=self.settings.get("episode_pattern", ""))
        tb.Entry(frm, textvariable=self.ep_pattern_var).grid(row=0, column=1, sticky="ew")

        tb.Label(frm, text="Movie Pattern:").grid(row=1, column=0, sticky="w", pady=6)
        self.movie_pattern_var = tk.StringVar(value=self.settings.get("movie_pattern", ""))
        tb.Entry(frm, textvariable=self.movie_pattern_var).grid(row=1, column=1, sticky="ew")

        self.console_visible_var = tk.BooleanVar(value=self.settings.get("console_visible", True))
        tb.Checkbutton(frm, text="Console Visible by Default", variable=self.console_visible_var).grid(row=2, column=1, sticky="w", pady=10)

        dir_frame = tb.LabelFrame(frm, text="Directories", padding=10)
        dir_frame.grid(row=3, column=0, columnspan=3, sticky="nsew")
        dir_frame.columnconfigure(1, weight=1)
        
        self.dir_entries = {}
        for i, (key, path) in enumerate(self.settings.get("directories", {}).items()):
            label_text = f"{key.replace('_', ' ').title()}:"
            tb.Label(dir_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5)
            var = tk.StringVar(value=path)
            tb.Entry(dir_frame, textvariable=var).grid(row=i, column=1, sticky="ew")
            tb.Button(dir_frame, text="...", command=lambda v=var: self._browse_dir(v)).grid(row=i, column=2, padx=5)
            self.dir_entries[key] = var
    
    def _build_patterns_tab(self, notebook):
        frm = tb.Frame(notebook, padding=10)
        notebook.add(frm, text="Patterns")
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)

        tb.Label(frm, text="Regex Patterns for Name Suggestions").pack()
        
        list_frame = tb.Frame(frm)
        list_frame.pack(fill="both", expand=True, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.patterns_listbox = tk.Listbox(list_frame)
        self.patterns_listbox.grid(row=0, column=0, sticky="nsew")
        for p in self.patterns:
            self.patterns_listbox.insert(tk.END, p)
        
        btn_frame = tb.Frame(frm)
        btn_frame.pack(fill="x")
        tb.Button(btn_frame, text="Add", command=self._add_pattern).pack(side="left")
        tb.Button(btn_frame, text="Edit", command=self._edit_pattern).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Delete", command=self._delete_pattern).pack(side="left")

    def _browse_dir(self, var):
        path = filedialog.askdirectory(title="Select Folder", initialdir=var.get())
        if path: var.set(path)

    def _add_pattern(self):
        new_pattern = simpledialog.askstring("Add Pattern", "Enter new regex pattern:", parent=self)
        if new_pattern: self.patterns_listbox.insert(tk.END, new_pattern)
    
    def _edit_pattern(self):
        selection = self.patterns_listbox.curselection()
        if not selection: return
        idx = selection[0]
        old_pattern = self.patterns_listbox.get(idx)
        new_pattern = simpledialog.askstring("Edit Pattern", "Edit regex pattern:", initialvalue=old_pattern, parent=self)
        if new_pattern:
            self.patterns_listbox.delete(idx)
            self.patterns_listbox.insert(idx, new_pattern)

    def _delete_pattern(self):
        selection = self.patterns_listbox.curselection()
        if selection: self.patterns_listbox.delete(selection[0])

    def _save(self):
        self.settings["episode_pattern"] = self.ep_pattern_var.get()
        self.settings["movie_pattern"] = self.movie_pattern_var.get()
        self.settings["console_visible"] = self.console_visible_var.get()
        for key, var in self.dir_entries.items():
            self.settings["directories"][key] = var.get()

        media_models.save_settings(self.settings)
        self.parent.settings = self.settings

        new_patterns = list(self.patterns_listbox.get(0, tk.END))
        media_models.save_patterns(new_patterns)
        self.parent.fluff_patterns = new_patterns

        self.parent._build_tools_menu()
        self.parent.log("Settings saved.")
        self.destroy()

# -------------------------
# Entrypoint
# -------------------------
def main():
    settings = media_models.load_settings()
    patterns = media_models.load_patterns()
    app = JMADMediaTool(settings, patterns)
    app.mainloop()

if __name__ == "__main__":
    main()
