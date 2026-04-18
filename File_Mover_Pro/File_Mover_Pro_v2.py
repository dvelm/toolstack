import os
import shutil
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from datetime import datetime
import platform
import sys

# --- HIGH RESOLUTION FIX ---
# This tells Windows to use the native resolution instead of stretching/blurring the app.
if platform.system() == 'Windows':
    try:
        import ctypes
        # Try Windows 8.1+ DPI awareness first
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Fallback for Windows Vista/7/8
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

class DatePicker(tk.Toplevel):
    """Custom Date Picker popup menu"""
    def __init__(self, parent, target_var, title="Select Date"):
        super().__init__(parent)
        self.title(title)
        self.geometry("280x150")
        self.configure(bg="#f0f4f8")
        self.resizable(False, False)
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self.target_var = target_var
        
        # Center the popup over parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (280 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (150 // 2)
        self.geometry(f"+{x}+{y}")

        # Parse current date or use today
        try:
            current_date = datetime.strptime(target_var.get(), "%Y-%m-%d")
        except:
            current_date = datetime.now()

        # UI Setup
        frame = tk.Frame(self, bg="#f0f4f8", padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Year", bg="#f0f4f8").grid(row=0, column=0, padx=5)
        tk.Label(frame, text="Month", bg="#f0f4f8").grid(row=0, column=1, padx=5)
        tk.Label(frame, text="Day", bg="#f0f4f8").grid(row=0, column=2, padx=5)

        # Year dropdown
        current_year = datetime.now().year
        self.year_var = tk.StringVar(value=str(current_date.year))
        years = [str(y) for y in range(current_year - 20, current_year + 5)]
        self.year_cb = ttk.Combobox(frame, textvariable=self.year_var, values=years, width=5, state="readonly")
        self.year_cb.grid(row=1, column=0, padx=5, pady=5)

        # Month dropdown
        self.month_var = tk.StringVar(value=f"{current_date.month:02d}")
        months = [f"{m:02d}" for m in range(1, 13)]
        self.month_cb = ttk.Combobox(frame, textvariable=self.month_var, values=months, width=3, state="readonly")
        self.month_cb.grid(row=1, column=1, padx=5, pady=5)

        # Day dropdown
        self.day_var = tk.StringVar(value=f"{current_date.day:02d}")
        days = [f"{d:02d}" for d in range(1, 32)]
        self.day_cb = ttk.Combobox(frame, textvariable=self.day_var, values=days, width=3, state="readonly")
        self.day_cb.grid(row=1, column=2, padx=5, pady=5)

        # Buttons
        btn_frame = tk.Frame(frame, bg="#f0f4f8")
        btn_frame.grid(row=2, column=0, columnspan=3, pady=15)
        
        ttk.Button(btn_frame, text="Set Date", command=self.set_date).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def set_date(self):
        selected_date = f"{self.year_var.get()}-{self.month_var.get()}-{self.day_var.get()}"
        try:
            # Validate real dates (e.g. catch Feb 30th)
            datetime.strptime(selected_date, "%Y-%m-%d")
            self.target_var.set(selected_date)
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Date", "The selected date is invalid.", parent=self)


class ResponsiveFileMoverApp:
    def __init__(self, root_frame, root_window):
        self.frame = root_frame
        self.root_window = root_window
        
        self.frame.configure(bg="#f0f4f8")
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Define Variables
        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        
        self.action_option = tk.StringVar(value="move") # Move or Copy
        self.sort_option = tk.StringVar(value="time")   # Default to Time
        self.order_option = tk.StringVar(value="asc")   # "asc" or "desc"
        
        # Filter Variables
        self.dimension_gb = tk.DoubleVar(value=14.98)
        self.extensions_var = tk.StringVar(value="")    # Empty means all files
        
        self.filter_date_var = tk.BooleanVar(value=False)
        self.from_date_var = tk.StringVar(value="2020-01-01")
        self.to_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        self.is_mobile = self.check_if_mobile()
        
        self.setup_styles()
        self.create_widgets()
        
    def setup_styles(self):
        self.style = ttk.Style()
        try:
            # Standardizing theme so buttons and scrollbars look clean
            self.style.theme_use('clam')
        except tk.TclError:
            pass
            
        self.style.configure("TButton", padding=6, relief="flat", background="#e1e8ed")
        self.style.configure("Action.TButton", padding=10, background="#4a86e8", foreground="white", font=("Helvetica", 10, "bold"))
        self.style.map("Action.TButton", background=[("active", "#3a76d8")])
        self.style.configure("Cancel.TButton", padding=10, background="#e74c3c", foreground="white", font=("Helvetica", 10, "bold"))
        self.style.map("Cancel.TButton", background=[("active", "#c0392b")])
        self.style.configure("TProgressbar", thickness=15)
        self.style.configure("TLabelframe", background="#f0f4f8")
        self.style.configure("TLabelframe.Label", background="#f0f4f8", foreground="#2c3e50", font=("Helvetica", 10, "bold"))
        
    def check_if_mobile(self):
        system = platform.system().lower()
        return system in ('android', 'ios') or hasattr(sys, 'getandroidapilevel')
    
    def create_widgets(self):
        main_container = tk.Frame(self.frame, bg="#f0f4f8", padx=15, pady=15)
        main_container.pack(fill="both", expand=True)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Title
        tk.Label(main_container, text="File Mover Pro", font=("Helvetica", 20, "bold"), bg="#f0f4f8", fg="#2c3e50").grid(row=0, column=0, pady=(0, 15), sticky="w")
        
        # 1. Folders Section
        folder_frame = ttk.LabelFrame(main_container, text="1. Locations")
        folder_frame.grid(row=1, column=0, sticky="ew", pady=5)
        folder_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(folder_frame, text="Source:", background="#f0f4f8").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(folder_frame, textvariable=self.source_folder).grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ttk.Button(folder_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=10, pady=10)
        
        ttk.Label(folder_frame, text="Output:", background="#f0f4f8").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(folder_frame, textvariable=self.output_folder).grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        ttk.Button(folder_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=10, pady=10)

        # 2. Action Section (Copy vs Move)
        action_frame = ttk.LabelFrame(main_container, text="2. Operation Type")
        action_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        tk.Radiobutton(action_frame, text="Move Files (Cut & Paste)", variable=self.action_option, value="move", bg="#f0f4f8", command=self.update_action_button).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        tk.Radiobutton(action_frame, text="Copy Files (Keep Originals)", variable=self.action_option, value="copy", bg="#f0f4f8", command=self.update_action_button).grid(row=0, column=1, padx=20, pady=10, sticky="w")

        # 3. Filters Section
        filter_frame = ttk.LabelFrame(main_container, text="3. Filters & Limits")
        filter_frame.grid(row=3, column=0, sticky="ew", pady=5)
        filter_frame.grid_columnconfigure(1, weight=1)
        
        # Size and Extensions
        ttk.Label(filter_frame, text="Size Limit (GB):", background="#f0f4f8").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        ttk.Entry(filter_frame, textvariable=self.dimension_gb, width=10).grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        ttk.Label(filter_frame, text="File Types (e.g. .jpg, .mp4):", background="#f0f4f8").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        ttk.Entry(filter_frame, textvariable=self.extensions_var).grid(row=1, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        ttk.Label(filter_frame, text="*Leave empty for all files", background="#f0f4f8", font=("Helvetica", 8), foreground="#7f8c8d").grid(row=2, column=1, padx=5, sticky="w")

        # Date Range Filter
        tk.Checkbutton(filter_frame, text="Filter by Date Modified", variable=self.filter_date_var, bg="#f0f4f8", command=self.toggle_date_fields).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        self.date_frame = tk.Frame(filter_frame, bg="#f0f4f8")
        self.date_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        
        ttk.Label(self.date_frame, text="From:", background="#f0f4f8").grid(row=0, column=0, padx=(0,5))
        self.from_entry = ttk.Entry(self.date_frame, textvariable=self.from_date_var, width=12, state="disabled")
        self.from_entry.grid(row=0, column=1)
        self.from_btn = ttk.Button(self.date_frame, text="🗓", width=3, state="disabled", command=lambda: self.open_date_picker(self.from_date_var, "From Date"))
        self.from_btn.grid(row=0, column=2, padx=(2, 15))
        
        ttk.Label(self.date_frame, text="To:", background="#f0f4f8").grid(row=0, column=3, padx=(0,5))
        self.to_entry = ttk.Entry(self.date_frame, textvariable=self.to_date_var, width=12, state="disabled")
        self.to_entry.grid(row=0, column=4)
        self.to_btn = ttk.Button(self.date_frame, text="🗓", width=3, state="disabled", command=lambda: self.open_date_picker(self.to_date_var, "To Date"))
        self.to_btn.grid(row=0, column=5, padx=(2, 0))

        # 4. Sorting Section
        sort_frame = ttk.LabelFrame(main_container, text="4. Selection Priority (Sorting)")
        sort_frame.grid(row=4, column=0, sticky="ew", pady=5)
        
        inner_sort = tk.Frame(sort_frame, bg="#f0f4f8")
        inner_sort.grid(row=0, column=0, padx=10, pady=10)
        
        tk.Radiobutton(inner_sort, text="Sort by Modified Time", variable=self.sort_option, value="time", bg="#f0f4f8").grid(row=0, column=0, padx=10, sticky="w")
        tk.Radiobutton(inner_sort, text="Sort by Name", variable=self.sort_option, value="name", bg="#f0f4f8").grid(row=0, column=1, padx=10, sticky="w")
        
        tk.Radiobutton(inner_sort, text="Ascending (Oldest / A→Z)", variable=self.order_option, value="asc", bg="#f0f4f8").grid(row=1, column=0, padx=10, pady=(5,0), sticky="w")
        tk.Radiobutton(inner_sort, text="Descending (Newest / Z→A)", variable=self.order_option, value="desc", bg="#f0f4f8").grid(row=1, column=1, padx=10, pady=(5,0), sticky="w")

        # 5. Progress Section
        progress_frame = ttk.LabelFrame(main_container, text="Progress")
        progress_frame.grid(row=5, column=0, sticky="ew", pady=10)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        
        stats_frame = tk.Frame(progress_frame, bg="#f0f4f8")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        stats_frame.grid_columnconfigure(1, weight=1)
        
        self.file_count_label = tk.Label(stats_frame, text="Files: 0/0", bg="#f0f4f8", fg="#2c3e50")
        self.file_count_label.grid(row=0, column=0, sticky="w")
        
        self.size_label = tk.Label(stats_frame, text="Size: 0.00 GB / 0.00 GB", bg="#f0f4f8", fg="#2c3e50")
        self.size_label.grid(row=0, column=1, sticky="e")
        
        self.status_label = tk.Label(progress_frame, text="Ready.", bg="#f0f4f8", fg="#2c3e50", wraplength=400, justify="center")
        self.status_label.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        # Buttons
        button_frame = tk.Frame(main_container, bg="#f0f4f8")
        button_frame.grid(row=6, column=0, pady=15, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        self.start_button = ttk.Button(button_frame, text="START MOVE", style="Action.TButton", command=self.start_operation)
        self.start_button.grid(row=0, column=0, padx=10, sticky="ew")
        
        self.cancel_button = ttk.Button(button_frame, text="CANCEL", style="Cancel.TButton", command=self.cancel_operation, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=10, sticky="ew")

        # Extra padding for mobile layout
        if self.is_mobile:
            for widget in main_container.winfo_children():
                widget.grid_configure(padx=2, pady=2)

    def toggle_date_fields(self):
        state = "normal" if self.filter_date_var.get() else "disabled"
        self.from_entry.config(state=state)
        self.to_entry.config(state=state)
        self.from_btn.config(state=state)
        self.to_btn.config(state=state)

    def update_action_button(self):
        action = self.action_option.get().upper()
        self.start_button.config(text=f"START {action}")

    def open_date_picker(self, target_var, title):
        DatePicker(self.root_window, target_var, title)

    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)
            try:
                count = sum([len(files) for r, d, files in os.walk(folder)])
                self.status_label.config(text=f"Source folder selected: {count} files found.")
            except:
                pass
    
    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
    
    def start_operation(self):
        if hasattr(self, 'op_thread') and self.op_thread.is_alive():
            return
        
        if not os.path.isdir(self.source_folder.get()):
            self.status_label.config(text="Invalid Source Folder!")
            return
        if not os.path.isdir(self.output_folder.get()):
            self.status_label.config(text="Invalid Output Folder!")
            return
        
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.running = True
        
        self.op_thread = threading.Thread(target=self.process_files, daemon=True)
        self.op_thread.start()
    
    def cancel_operation(self):
        if hasattr(self, 'running'):
            self.running = False
            self.status_label.config(text="Operation canceled by user.")
            self.cancel_button.config(state="disabled")
            self.start_button.config(state="normal")
    
    def process_files(self):
        try:
            source_path = self.source_folder.get()
            output_path = self.output_folder.get()
            action = self.action_option.get()
            dimension_bytes = int(self.dimension_gb.get() * 1024 * 1024 * 1024)
            
            # Setup Filters
            exts = [e.strip().lower() for e in self.extensions_var.get().split(',')]
            exts = [e if e.startswith('.') else f".{e}" for e in exts if e]
            
            from_ts = 0
            to_ts = float('inf')
            if self.filter_date_var.get():
                try:
                    from_ts = datetime.strptime(self.from_date_var.get(), "%Y-%m-%d").timestamp()
                    to_ts = datetime.strptime(self.to_date_var.get() + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    self.status_label.config(text="Invalid Date format! Use YYYY-MM-DD.")
                    return
            
            self.status_label.config(text="Scanning and filtering files...")
            
            all_files = []
            for root_dir, _, files in os.walk(source_path):
                for file in files:
                    if not self.running: return
                    
                    # Extension Filter
                    if exts and not any(file.lower().endswith(ext) for ext in exts):
                        continue
                        
                    file_path = os.path.join(root_dir, file)
                    try:
                        file_mtime = os.path.getmtime(file_path)
                        
                        # Date Filter
                        if not (from_ts <= file_mtime <= to_ts):
                            continue
                            
                        file_size = os.path.getsize(file_path)
                        file_name = file.lower()
                        all_files.append((file_path, file_size, file_mtime, file_name))
                    except (FileNotFoundError, PermissionError):
                        continue
            
            # Sorting
            sort_by = self.sort_option.get()
            order = self.order_option.get()
            
            if sort_by == "name":
                all_files.sort(key=lambda x: x[3], reverse=(order == "desc"))
            else:
                all_files.sort(key=lambda x: x[2], reverse=(order == "desc"))
            
            # Cap by Size Limit
            total_bytes = 0
            files_to_process = []
            
            for file_path, file_size, _, _ in all_files:
                if not self.running: return
                
                if total_bytes + file_size <= dimension_bytes:
                    files_to_process.append((file_path, file_size))
                    total_bytes += file_size
                else:
                    if not files_to_process and total_bytes == 0:
                        files_to_process.append((file_path, file_size))
                        total_bytes += file_size
                    break
            
            if not files_to_process:
                self.status_label.config(text="No files met the specified criteria!")
                self.start_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                return
            
            # Start UI Update for Transfer
            self.progress["maximum"] = len(files_to_process)
            self.progress["value"] = 0
            
            dimension_gb = self.dimension_gb.get()
            self.size_label.config(text=f"Size: 0.00 GB / {dimension_gb:.2f} GB")
            self.file_count_label.config(text=f"Files: 0/{len(files_to_process)}")
            
            processed_bytes = 0
            action_verb = "Copying" if action == "copy" else "Moving"
            
            for index, (file_path, file_size) in enumerate(files_to_process):
                if not self.running: return
                    
                rel_path = os.path.relpath(file_path, source_path)
                dest_path = os.path.join(output_path, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                try:
                    file_name = os.path.basename(file_path)
                    self.status_label.config(text=f"{action_verb}: {file_name}")
                    
                    if action == "copy":
                        shutil.copy2(file_path, dest_path)
                    else:
                        shutil.move(file_path, dest_path)
                    
                    processed_bytes += file_size
                    processed_gb = processed_bytes / (1024 ** 3)
                    
                    self.progress["value"] = index + 1
                    self.file_count_label.config(text=f"Files: {index+1}/{len(files_to_process)}")
                    self.size_label.config(text=f"Size: {processed_gb:.2f} GB / {dimension_gb:.2f} GB")
                    
                    self.root_window.update_idletasks()
                        
                except Exception as e:
                    self.status_label.config(text=f"Error {action.lower()}ing {file_name}: {str(e)}")
                    continue
            
            processed_gb = processed_bytes / (1024 ** 3)
            percent = (processed_bytes / dimension_bytes) * 100 if dimension_bytes > 0 else 100
            time_now = datetime.now().strftime("%H:%M:%S")
            verb_done = "Copied" if action == "copy" else "Moved"
            self.status_label.config(text=f"Success at {time_now}! {verb_done} {len(files_to_process)} files ({processed_gb:.2f} GB, {percent:.1f}% limit used)")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
        finally:
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.running = False


def run_app():
    root = tk.Tk()
    root.title("File Mover Pro - Advanced Edition")
    
    # Configure the main root window
    root.minsize(350, 650)
    root.configure(bg="#f0f4f8")
    
    # Create a grid layout that expands
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # ---------------------------------------------------------
    # UNIVERSAL SCROLLING SETUP (Applied to all platforms)
    # ---------------------------------------------------------
    main_scroll_frame = tk.Frame(root, bg="#f0f4f8")
    main_scroll_frame.grid(row=0, column=0, sticky="nsew")
    main_scroll_frame.grid_rowconfigure(0, weight=1)
    main_scroll_frame.grid_columnconfigure(0, weight=1)

    # The Canvas acts as the viewport for scrolling
    canvas = tk.Canvas(main_scroll_frame, bg="#f0f4f8", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    # The Navigation Bar (Scrollbar) with arrows at the top and bottom
    scrollbar = ttk.Scrollbar(main_scroll_frame, orient="vertical", command=canvas.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Link canvas and scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)

    # The actual content frame inside the canvas
    content_frame = tk.Frame(canvas, bg="#f0f4f8")
    canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

    # Keep content frame width synced with canvas width
    def configure_frame(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", configure_frame)

    # Update scroll region whenever content changes size
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    content_frame.bind("<Configure>", on_frame_configure)

    # Mouse Wheel Scrolling bindings for PC
    def _on_mousewheel(event):
        # Platform-independent mouse wheel direction
        direction = int(-1*(event.delta/120)) if event.delta else 0
        canvas.yview_scroll(direction, "units")

    # Binding mouse scroll for Windows/macOS
    root.bind_all("<MouseWheel>", _on_mousewheel)
    
    # Binding mouse scroll for Linux
    root.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    root.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    # Initialize the actual App logic into the content_frame
    app = ResponsiveFileMoverApp(content_frame, root)

    # Mobile touch drag-scrolling support
    system = platform.system().lower()
    is_mobile = system in ('android', 'ios') or hasattr(sys, 'getandroidapilevel')
    if is_mobile:
        def _on_touch_start(event):
            canvas.scan_mark(event.x, event.y)
        def _on_touch_move(event):
            canvas.scan_dragto(event.x, event.y, gain=1)
            
        canvas.bind("<ButtonPress-1>", _on_touch_start)
        canvas.bind("<B1-Motion>", _on_touch_move)
        
        window_width = min(500, root.winfo_screenwidth() - 20)
        window_height = min(900, root.winfo_screenheight() - 40)
    else:
        window_width = 580
        window_height = 800

    # Center Window logic
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = max(0, int(screen_height/2 - window_height/2))
    
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.mainloop()

if __name__ == "__main__":
    run_app()