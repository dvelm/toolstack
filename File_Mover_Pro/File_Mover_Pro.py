import os
import shutil
import tkinter as tk
from tkinter import filedialog, ttk
import threading
from datetime import datetime
import platform
import sys

class ResponsiveFileMoverApp:
    def __init__(self, root, is_frame=False):
        self.root = root
        self.is_frame = is_frame
        
        # Only call title() if this is not a frame (direct Tk root)
        if not is_frame:
            self.root.title("File Mover Pro")
            
        self.root.configure(bg="#f0f4f8")
        
        # Set minimum window size (only for main window)
        if not is_frame:
            self.root.minsize(300, 450)
        
        # Make the layout responsive
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(7, weight=1)
        
        # Variables
        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.dimension_gb = tk.DoubleVar(value=14.98)  # Default 14.98 GB
        self.sort_option = tk.StringVar(value="name")  # "name" or "time"
        self.order_option = tk.StringVar(value="asc")  # "asc" or "desc"
        
        # Get platform info to adjust for mobile
        self.is_mobile = self.check_if_mobile()
        self.create_widgets()
        
        # Set the theme
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except:
            pass  # Fallback if theme not available
        self.style.configure("TButton", padding=10, relief="flat")
        self.style.configure("TProgressbar", thickness=20)
        
    def check_if_mobile(self):
        # Simple check for mobile platforms - this can be expanded
        system = platform.system().lower()
        return system in ('android', 'ios') or hasattr(sys, 'getandroidapilevel')
    
    def create_widgets(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f4f8", padx=20, pady=20)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        
        # App Title
        title_label = tk.Label(
            main_frame, 
            text="File Mover Pro", 
            font=("Helvetica", 18, "bold"),
            bg="#f0f4f8", 
            fg="#2c3e50"
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="ew")
        
        # Frames for different sections
        folder_frame = tk.LabelFrame(main_frame, text="Folder Selection", bg="#f0f4f8", fg="#2c3e50", padx=10, pady=10)
        folder_frame.grid(row=1, column=0, sticky="ew", pady=10)
        folder_frame.grid_columnconfigure(1, weight=1)
        
        # Source folder
        tk.Label(folder_frame, text="Source:", bg="#f0f4f8", fg="#2c3e50").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        source_entry = tk.Entry(folder_frame, textvariable=self.source_folder, width=30 if not self.is_mobile else 15)
        source_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        source_entry.bind("<Button-1>", lambda e: source_entry.focus_set())  # Force focus on click
        tk.Button(
            folder_frame, 
            text="Browse", 
            command=self.browse_source,
            bg="#4a86e8",
            fg="white",
            bd=0,
            padx=10,
            pady=5
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Output folder
        tk.Label(folder_frame, text="Output:", bg="#f0f4f8", fg="#2c3e50").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        output_entry = tk.Entry(folder_frame, textvariable=self.output_folder, width=30 if not self.is_mobile else 15)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        output_entry.bind("<Button-1>", lambda e: output_entry.focus_set())  # Force focus on click
        tk.Button(
            folder_frame, 
            text="Browse", 
            command=self.browse_output,
            bg="#4a86e8",
            fg="white",
            bd=0,
            padx=10,
            pady=5
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Settings frame
        settings_frame = tk.LabelFrame(main_frame, text="Transfer Settings", bg="#f0f4f8", fg="#2c3e50", padx=10, pady=10)
        settings_frame.grid(row=2, column=0, sticky="ew", pady=10)
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # Dimension
        tk.Label(settings_frame, text="Size Limit (GB):", bg="#f0f4f8", fg="#2c3e50").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        dimension_entry = tk.Entry(settings_frame, textvariable=self.dimension_gb, width=10)
        dimension_entry.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        dimension_entry.bind("<Button-1>", lambda e: dimension_entry.focus_set())  # Force focus on click
        
        # File sort options
        option_frame = tk.LabelFrame(main_frame, text="File Selection Priority", bg="#f0f4f8", fg="#2c3e50", padx=10, pady=10)
        option_frame.grid(row=3, column=0, sticky="ew", pady=10)
        option_frame.grid_columnconfigure(0, weight=1)
        
        # Sort type options
        sort_desc = tk.Label(
            option_frame, 
            text="Choose how files should be selected for transfer:",
            bg="#f0f4f8", 
            fg="#2c3e50",
            wraplength=380 if not self.is_mobile else 250,
            justify="left"
        )
        sort_desc.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Create a frame for sort type
        sort_type_frame = tk.Frame(option_frame, bg="#f0f4f8")
        sort_type_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        sort_type_frame.grid_columnconfigure(0, weight=1)
        sort_type_frame.grid_columnconfigure(1, weight=1)
        
        # Sort type radio buttons
        sort_by_name = tk.Radiobutton(
            sort_type_frame, 
            text="Sort by Name", 
            variable=self.sort_option, 
            value="name",
            bg="#f0f4f8",
            fg="#2c3e50",
            selectcolor="#dae5f4"
        )
        sort_by_name.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        sort_by_time = tk.Radiobutton(
            sort_type_frame, 
            text="Sort by Modified Time", 
            variable=self.sort_option, 
            value="time",
            bg="#f0f4f8",
            fg="#2c3e50",
            selectcolor="#dae5f4"
        )
        sort_by_time.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Order description
        order_desc = tk.Label(
            option_frame,
            text="Choose the sorting order:",
            bg="#f0f4f8",
            fg="#2c3e50",
            wraplength=380 if not self.is_mobile else 250,
            justify="left"
        )
        order_desc.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        # Sort order options - Modified for mobile
        sort_order_frame = tk.Frame(option_frame, bg="#f0f4f8")
        sort_order_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        
        if self.is_mobile:
            # For mobile: stack vertically
            sort_order_frame.grid_columnconfigure(0, weight=1)
            
            ascending_radio = tk.Radiobutton(
                sort_order_frame,
                text="Ascending (A→Z / Oldest First)",
                variable=self.order_option,
                value="asc",
                bg="#f0f4f8",
                fg="#2c3e50",
                selectcolor="#dae5f4",
                wraplength=250,
                justify="left"
            )
            ascending_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            
            descending_radio = tk.Radiobutton(
                sort_order_frame,
                text="Descending (Z→A / Newest First)",
                variable=self.order_option,
                value="desc",
                bg="#f0f4f8",
                fg="#2c3e50",
                selectcolor="#dae5f4",
                wraplength=250,
                justify="left"
            )
            descending_radio.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        else:
            # For desktop: keep horizontal layout
            sort_order_frame.grid_columnconfigure(0, weight=1)
            sort_order_frame.grid_columnconfigure(1, weight=1)
            
            ascending_radio = tk.Radiobutton(
                sort_order_frame,
                text="Ascending (A→Z / Oldest First)",
                variable=self.order_option,
                value="asc",
                bg="#f0f4f8",
                fg="#2c3e50",
                selectcolor="#dae5f4",
                wraplength=180 if not self.is_mobile else 120,
                justify="left"
            )
            ascending_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            
            descending_radio = tk.Radiobutton(
                sort_order_frame,
                text="Descending (Z→A / Newest First)",
                variable=self.order_option,
                value="desc",
                bg="#f0f4f8",
                fg="#2c3e50",
                selectcolor="#dae5f4",
                wraplength=180 if not self.is_mobile else 120,
                justify="left"
            )
            descending_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Help text for sorting options
        sort_help = tk.Label(
            option_frame,
            text="• Sort by Name + Ascending: Alphabetically A to Z\n• Sort by Name + Descending: Alphabetically Z to A\n• Sort by Time + Ascending: Oldest files first\n• Sort by Time + Descending: Newest files first",
            bg="#f0f4f8",
            fg="#7f8c8d",
            font=("Helvetica", 8),
            wraplength=380 if not self.is_mobile else 250,
            justify="left"
        )
        sort_help.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        # Progress section
        progress_frame = tk.LabelFrame(main_frame, text="Progress", bg="#f0f4f8", fg="#2c3e50", padx=10, pady=10)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=10)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Status label
        self.status_label = tk.Label(
            progress_frame, 
            text="Ready to move files",
            bg="#f0f4f8", 
            fg="#2c3e50",
            wraplength=380 if not self.is_mobile else 250,
        )
        self.status_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # File counter labels
        self.file_count_label = tk.Label(
            progress_frame, 
            text="Files: 0/0",
            bg="#f0f4f8", 
            fg="#2c3e50"
        )
        self.file_count_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.size_label = tk.Label(
            progress_frame, 
            text="Size: 0.00 GB/0.00 GB",
            bg="#f0f4f8", 
            fg="#2c3e50"
        )
        self.size_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        # Action buttons
        button_frame = tk.Frame(main_frame, bg="#f0f4f8")
        button_frame.grid(row=5, column=0, pady=15, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # Start button
        self.start_button = tk.Button(
            button_frame, 
            text="START TRANSFER", 
            command=self.start_moving,
            bg="#4caf50",
            fg="white",
            font=("Helvetica", 10, "bold"),
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Cancel button
        self.cancel_button = tk.Button(
            button_frame, 
            text="CANCEL", 
            command=self.cancel_operation,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 10, "bold"),
            bd=0,
            padx=20,
            pady=10,
            state="disabled",
            cursor="hand2"
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Footer
        footer = tk.Label(
            main_frame, 
            text="© 2025 File Mover Pro",
            font=("Helvetica", 8),
            bg="#f0f4f8", 
            fg="#95a5a6"
        )
        footer.grid(row=6, column=0, pady=10, sticky="ew")
        
        # For mobile, set extra padding
        if self.is_mobile:
            for widget in main_frame.winfo_children():
                widget.grid_configure(padx=5, pady=5)
    
    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder.set(folder)
            # Update status to show folder info
            try:
                file_count = sum([len(files) for r, d, files in os.walk(folder)])
                self.status_label.config(text=f"Selected source folder with {file_count} files")
            except:
                pass
    
    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
    
    def start_moving(self):
        # Check if operation is already running
        if hasattr(self, 'move_thread') and self.move_thread.is_alive():
            return
        
        # Validate inputs
        if not os.path.isdir(self.source_folder.get()):
            self.status_label.config(text="Invalid source folder!")
            return
        
        if not os.path.isdir(self.output_folder.get()):
            self.status_label.config(text="Invalid output folder!")
            return
        
        # Update UI controls
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        
        # Flag to control thread execution
        self.running = True
        
        # Start moving in a separate thread to keep UI responsive
        self.move_thread = threading.Thread(target=self.move_files, daemon=True)
        self.move_thread.start()
    
    def cancel_operation(self):
        if hasattr(self, 'running'):
            self.running = False
            self.status_label.config(text="Operation canceled by user")
            self.cancel_button.config(state="disabled")
            self.start_button.config(state="normal")
    
    def format_size(self, size_bytes):
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    
    def move_files(self):
        try:
            source_path = self.source_folder.get()
            output_path = self.output_folder.get()
            dimension_bytes = int(self.dimension_gb.get() * 1024 * 1024 * 1024)  # Convert GB to bytes
            
            # Update status
            self.status_label.config(text="Scanning files...")
            
            # Get all files from source directory
            all_files = []
            for root, _, files in os.walk(source_path):
                for file in files:
                    if not self.running:
                        return
                    
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        file_mtime = os.path.getmtime(file_path)
                        file_name = os.path.basename(file_path).lower()
                        all_files.append((file_path, file_size, file_mtime, file_name))
                    except (FileNotFoundError, PermissionError):
                        # Skip files that can't be accessed
                        continue
            
            # Update status
            self.status_label.config(text=f"Found {len(all_files)} files. Sorting...")
            
            # Get sort options
            sort_by = self.sort_option.get()
            order = self.order_option.get()
            
            # Sort files based on options
            if sort_by == "name":
                # Sort by filename
                if order == "asc":
                    all_files.sort(key=lambda x: x[3])  # Ascending by name
                    sort_description = "alphabetically (A-Z)"
                else:
                    all_files.sort(key=lambda x: x[3], reverse=True)  # Descending by name
                    sort_description = "alphabetically (Z-A)"
            else:  # sort_by == "time"
                # Sort by modification time
                if order == "asc":
                    all_files.sort(key=lambda x: x[2])  # Ascending by time (oldest first)
                    sort_description = "by oldest modified first"
                else:
                    all_files.sort(key=lambda x: x[2], reverse=True)  # Descending by time (newest first)
                    sort_description = "by newest modified first"
            
            total_bytes = 0
            files_to_move = []
            
            # Select files to move
            for file_path, file_size, _, _ in all_files:
                if not self.running:
                    return
                    
                if total_bytes + file_size <= dimension_bytes:
                    files_to_move.append((file_path, file_size))
                    total_bytes += file_size
                else:
                    # Check if we have no files yet and this single file would exceed the limit
                    if not files_to_move and total_bytes == 0:
                        files_to_move.append((file_path, file_size))
                        total_bytes += file_size
                        self.status_label.config(text=f"Warning: First file exceeds size limit!")
                    break
            
            if not files_to_move:
                self.status_label.config(text="No files to move within the specified dimension!")
                self.start_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                return
            
            # Update UI
            total_gb = total_bytes / (1024 * 1024 * 1024)
            self.progress["maximum"] = len(files_to_move)
            self.progress["value"] = 0
            self.status_label.config(text=f"Moving {len(files_to_move)} files sorted {sort_description}")
            
            # Format for size display
            dimension_gb = self.dimension_gb.get()
            self.size_label.config(text=f"Size: 0.00 GB/{dimension_gb:.2f} GB")
            self.file_count_label.config(text=f"Files: 0/{len(files_to_move)}")
            
            # Move files with progress
            moved_bytes = 0
            for index, (file_path, file_size) in enumerate(files_to_move):
                if not self.running:
                    return
                    
                rel_path = os.path.relpath(file_path, source_path)
                dest_path = os.path.join(output_path, rel_path)
                
                # Create directory structure if needed
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                try:
                    # Update status for current file
                    file_name = os.path.basename(file_path)
                    self.status_label.config(text=f"Moving: {file_name}")
                    
                    # Move the file
                    shutil.move(file_path, dest_path)
                    
                    # Update moved bytes
                    moved_bytes += file_size
                    moved_gb = moved_bytes / (1024 * 1024 * 1024)
                    
                    # Update progress
                    self.progress["value"] = index + 1
                    self.file_count_label.config(text=f"Files: {index+1}/{len(files_to_move)}")
                    self.size_label.config(text=f"Size: {moved_gb:.2f} GB/{dimension_gb:.2f} GB")
                    
                    # Use update_idletasks for smoother UI on main window
                    if not self.is_frame:
                        self.root.update_idletasks()
                    
                except Exception as e:
                    self.status_label.config(text=f"Error moving {file_name}: {str(e)}")
                    continue
            
            # Final status update
            moved_gb = moved_bytes / (1024 * 1024 * 1024)
            if moved_bytes > 0:
                percent = (moved_bytes / dimension_bytes) * 100 if dimension_bytes > 0 else 100
                completion_time = datetime.now().strftime("%H:%M:%S")
                self.status_label.config(text=f"Completed at {completion_time}! Moved {len(files_to_move)} files ({moved_gb:.2f} GB, {percent:.1f}%)")
            else:
                self.status_label.config(text="No files were moved.")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
        finally:
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.running = False

def run_app():
    root = tk.Tk()
    root.title("File Mover Pro")  # Set title on the root window
    
    # Detect if mobile
    system = platform.system().lower()
    is_mobile = system in ('android', 'ios') or hasattr(sys, 'getandroidapilevel')
    
    # Set up scrolling for mobile (USING GRID INSTEAD OF PACK)
    if is_mobile:
        # Create canvas with scrollbar
        main_frame = tk.Frame(root)
        main_frame.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(main_frame, bg="#f0f4f8")
        canvas.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a frame inside the canvas
        content_frame = tk.Frame(canvas, bg="#f0f4f8")
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        # Make the content frame expand to fill canvas width
        def configure_frame(event):
            canvas.itemconfig(canvas_window, width=event.width)
            
        canvas.bind("<Configure>", configure_frame)
        
        # Make sure scrolling works
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        content_frame.bind("<Configure>", on_frame_configure)
        
        # App goes in the content frame - pass is_frame=True to indicate this is a frame, not the root
        app = ResponsiveFileMoverApp(content_frame, is_frame=True)
        
        # Add touch scrolling
        def _on_touch_start(event):
            canvas.scan_mark(event.x, event.y)
            
        def _on_touch_move(event):
            canvas.scan_dragto(event.x, event.y, gain=1)
        
        canvas.bind("<ButtonPress-1>", _on_touch_start)
        canvas.bind("<B1-Motion>", _on_touch_move)
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Size for mobile
        window_width = min(500, root.winfo_screenwidth() - 20)
        window_height = min(800, root.winfo_screenheight() - 40)
    else:
        # For desktop, just create the app normally
        app = ResponsiveFileMoverApp(root)
        window_width = 500
        window_height = 750
    
    # Center window on screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    root.mainloop()

if __name__ == "__main__":
    run_app()