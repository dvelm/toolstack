# ToolStack Repository

This repository contains a collection of useful tools for various tasks.

## Repository Structure

### 1. File Mover Pro

A cross-platform desktop application for efficiently moving or copying files with advanced filtering, sorting, and size limit options.

**Location**: `File_Mover_Pro/`

**Features**:
- Move or Copy files with size limits
- Filter by file extensions and date ranges
- Sort by modified time or name
- Real-time progress tracking
- High DPI and responsive design support

**Quick Start**:
```bash
python File_Mover_Pro/File_Mover_Pro_v2.py
```
Or use `run.bat` / `run.sh` in the project folder.

---

### 2. Advanced Python File Comparing
An advanced file comparison tool built with PyQt6 that allows you to compare folders and files with multiple comparison methods. This tool provides a graphical interface for comparing directories and identifying identical, different, and unique files.

#### Features
- **Multiple Comparison Methods**:
  - Soft Compare: Quickly compares files by size and last-modified time (fastest method)
  - Smart Compare: Compares files by size first, then hashes only same-size files (balanced speed and accuracy)
  - Deep Compare: Hashes every file and compares full contents (most accurate but slowest)
- **Multi-threaded Operations**: Uses QThreadPool for efficient parallel processing
- **Real-time Progress Tracking**: Visual progress bars with accurate progress updates
- **File Filtering**: Filter by file type (images, documents, audio, video) or custom extensions
- **Recursive Directory Scanning**: Option to include subdirectories
- **Status Highlighting**: Color-coded results for quick identification
- **Detailed Reporting**: Generate comprehensive comparison reports
- **File Moving**: Copy files between panels with optional folder structure preservation
- **Comprehensive Logging**: Both terminal and GUI logging for debugging

#### Installation
1. Clone this repository or download the folder
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

#### Usage
1. Run the tool using the batch file:
   ```
   run.bat
   ```
   Or directly with Python:
   ```
   python Advanced_Python_File_Comparing.py
   ```

2. Load folders in both panels using "Add Folder" or drag and drop
3. Select comparison options (subfolders, file filters)
4. Choose a comparison method (Soft, Smart, or Deep)
5. View results with color-coded files
6. Generate reports or move files as needed

### 3. PDF Tool Pro

A modern, feature-rich PDF editing and compression tool with a beautiful web UI.

**Location**: `pdf-tool-pro/`

**Features**:
- Compress PDFs (4 methods: lossless, smart, aggressive, raster)
- Merge multiple PDFs into one
- Split PDFs into separate pages
- Rotate, crop, and watermark pages
- Extract text and images
- Select specific pages
- View PDF metadata and info
- Modern dark glassmorphism UI

**Quick Start**:
```bash
cd pdf-tool-pro
pip install -r requirements.txt
streamlit run pdf_ui.py
```
Or double-click `run` on Linux / `run.bat` on Windows.

---

## Future Tools
More tools will be added to this collection over time. Check back for updates!

## License
This project is open source and available under the MIT License.
