import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from typing import Optional, List

class MediaTypeSelectionDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, media_types: List[str]):
        super().__init__(parent)
        self.parent = parent
        self.title("Select Media Type")
        self.transient(parent)
        self.grab_set()

        self.result_media_type: Optional[str] = None
        self.media_types = media_types

        self._build_ui()

        # Center the dialog
        self.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

    def _build_ui(self):
        main_frame = tb.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        tb.Label(main_frame, text="Please select the media type for the selected items:", font=("Helvetica", 12, "bold")).pack(pady=10)

        self.media_type_var = tk.StringVar(value=self.media_types[0] if self.media_types else "")
        
        # Use a Frame to hold the radio buttons for better layout control
        radio_frame = tb.Frame(main_frame)
        radio_frame.pack(pady=10, fill="x")
        radio_frame.columnconfigure(0, weight=1) # Center the radio buttons

        for i, media_type in enumerate(self.media_types):
            rb = tb.Radiobutton(radio_frame, text=media_type, variable=self.media_type_var, value=media_type, bootstyle="info-round-toggle")
            rb.grid(row=i, column=0, sticky="w", pady=2, padx=50) # Indent radio buttons

        button_frame = tb.Frame(main_frame)
        button_frame.pack(pady=10)

        tb.Button(button_frame, text="Continue", command=self._on_continue, bootstyle="success").pack(side="left", padx=5)
        tb.Button(button_frame, text="Cancel", command=self._on_cancel, bootstyle="danger").pack(side="left", padx=5)

    def _on_continue(self):
        self.result_media_type = self.media_type_var.get()
        self.destroy()

    def _on_cancel(self):
        self.result_media_type = None
        self.destroy()

    def show(self) -> Optional[str]:
        self.parent.wait_window(self)
        return self.result_media_type
