# File Mover Pro

A cross-platform desktop application for efficiently moving or copying files with advanced filtering, sorting, and size limit options.

## Features

- **Move or Copy Files**: Choose between moving files (cut & paste) or copying them (keeping originals)
- **Size Limit**: Set a maximum total size limit (in GB) for batch operations
- **File Type Filtering**: Filter by extensions (e.g., `.jpg`, `.mp4`, `.pdf`)
- **Date Filtering**: Filter files by modified date range with a custom date picker
- **Flexible Sorting**: Sort files by modified time or name, in ascending or descending order
- **Real-time Progress**: Visual progress bar with file count and size tracking
- **Cancellation Support**: Cancel operations mid-process
- **High DPI Support**: Native resolution support on Windows
- **Responsive Design**: Works on desktop and mobile platforms with scrolling support

## Requirements

- Python 3.7+
- Tkinter (usually included with Python)

No external dependencies required.

## Usage

### Quick Start

Run the application:
```bash
python File_Mover_Pro_v2.py
```

Or use the provided batch file:
```bash
run.bat
```

### How to Use

1. **Select Folders**: Choose a source folder (where files are) and an output folder (destination)
2. **Choose Operation**: Select "Move" or "Copy" mode
3. **Set Filters** (optional):
   - Set a size limit in GB
   - Enter file extensions to include (comma-separated, e.g., `.jpg, .png, .gif`)
   - Enable date filtering and select a date range using the calendar picker
4. **Configure Sorting**: Choose how files should be prioritized (by time or name)
5. **Start**: Click "START MOVE" or "START COPY" to begin
6. **Monitor**: Watch the progress bar and statistics update in real-time

## Interface Sections

| Section | Description |
|---------|-------------|
| 1. Locations | Source and output folder paths |
| 2. Operation Type | Move or Copy mode selection |
| 3. Filters & Limits | Size limit, file types, and date range filters |
| 4. Selection Priority | Sorting by time or name, ascending or descending |
| Progress | Visual progress bar with file count and size statistics |

## Keyboard & Mouse

- **Mouse Wheel**: Scroll through the interface
- **Touch Drag**: Mobile touch scrolling support
- **Calendar Button**: Opens date picker for date range selection

## File Structure

```
File_Mover_Pro/
├── File_Mover_Pro_v2.py    # Main application
├── File_Mover_Pro.py       # Original version
├── requirements.txt        # Python dependencies
├── run.bat                 # Windows launcher
└── README.md               # This file
```

## Platform Support

- **Windows**: Full support with DPI awareness
- **macOS**: Full support
- **Linux**: Full support
- **Mobile**: Touch-enabled scrolling for Android/iOS

## License

This project is provided as-is for personal and educational use.