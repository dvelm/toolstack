# ToolStack

A collection of useful Python tools for various tasks.

## Current Tools

### 1. Advanced Python File Comparing
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

## Future Tools
More tools will be added to this collection over time. Check back for updates!

## License
This project is open source and available under the MIT License.