# PDF Tool Pro

A modern, feature-rich PDF editing and compression tool with a beautiful web UI.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.0+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🚀 How to Run

### Step 1 — Install Python

Make sure you have **Python 3.9+** installed. Check by running:

```bash
python3 --version
```

If not installed, download it from [python.org](https://www.python.org/downloads/).

### Step 2 — Install dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

### Step 3 — Start the app

**Option A — From terminal (any platform):**

```bash
streamlit run pdf_ui.py
```

Your browser opens automatically at `http://localhost:8501`. Done!

**Option B — Double-click (Linux):**

1. Run the installer once: `bash install.sh`
2. Press the **Super/Windows key**, search for **"PDF Tool Pro"**
3. Click to launch — opens in your browser

**Option C — Double-click (Windows):**

Double-click `run.bat`. Your browser opens automatically.

---

## What It Does

Upload a PDF and choose an operation:

| Operation | What it does |
|-----------|-------------|
| 📦 **Compress** | Reduce file size (4 methods: lossless, smart, aggressive, raster) |
| 🔗 **Merge** | Combine multiple PDFs into one |
| ✂️ **Split** | Extract pages into separate files |
| 🔄 **Rotate** | Rotate all pages (90°, 180°, 270°) |
| 📐 **Crop** | Remove margins from pages |
| 📝 **Extract Text** | Pull all text from a PDF |
| 🖼️ **Extract Images** | Save all embedded images |
| 📑 **Select Pages** | Pick specific pages (e.g. 1,3,5-8) |
| 💧 **Watermark** | Add text overlay to every page |
| ℹ️ **Info** | View metadata, page count, file details |

---

## Compression Methods

| Method | Description |
|--------|-------------|
| **Auto** | Analyzes your PDF and picks the best approach |
| **Lossless** | Zero quality loss — strips metadata, subsets fonts |
| **Smart** | Compresses images only — text stays 100% sharp (recommended) |
| **Aggressive** | Maximum compression — lower DPI + grayscale |
| **Raster** | Renders pages as images — last resort for scanned docs |

### Output

All processed files are saved to the `output/` folder next to the program, with the original filename and an operation suffix:

| Operation | Suffix | Example |
|-----------|--------|---------|
| Compress | `-cmprs` | `document-cmprs.pdf` |
| Merge | `-merged` | `document-merged.pdf` |
| Split | `-split` | `document-split/` (folder) |
| Rotate | `-rotated` | `document-rotated.pdf` |
| Crop | `-cropped` | `document-cropped.pdf` |
| Extract Text | `-text` | `document-text.txt` |
| Extract Images | `-images` | `document-images/` (folder) |
| Select Pages | `-selected` | `document-selected.pdf` |
| Watermark | `-watermarked` | `document-watermarked.pdf` |

You can also download the result directly from the browser via the download button.

---

## Command Line Usage

All operations also work from the terminal:

```bash
# Compress
python3 pdf_tool.py compress input.pdf -o compressed.pdf

# Merge
python3 pdf_tool.py merge a.pdf b.pdf -o merged.pdf

# Split
python3 pdf_tool.py split input.pdf -o pages/

# Rotate
python3 pdf_tool.py rotate input.pdf -o rotated.pdf -a 90

# Extract text
python3 pdf_tool.py extract-text input.pdf -o output.txt

# View info
python3 pdf_tool.py info input.pdf

# Help
python3 pdf_tool.py --help
```

---

## Linux Full Install

For the best experience on Linux, run the installer once:

```bash
bash install.sh
```

This adds the app to your system launcher and configures `.sh` files to run on double-click instead of opening in a text editor.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Python not found" | Install Python 3.9+ and add it to your PATH |
| "No module named fitz" | Run `pip install PyMuPDF` |
| Port 8501 already in use | Use `streamlit run pdf_ui.py --server.port 8502` |
| Ctrl+C doesn't stop Streamlit | Fixed in v1.0.1 — update or use `./run --stop` |
| Double-click opens text editor (Linux) | Run `bash install.sh` |
| Streamlit won't start | Check the log: `cat /tmp/pdf-tool-pro-launch.log` |

---

## File Structure

```
pdf-tool-pro/
├── pdf_tool.py          # Core PDF engine
├── pdf_ui.py            # Web UI (Streamlit)
├── requirements.txt     # Dependencies
├── run                  # Linux launcher (--stop to kill, --help for usage)
├── run.bat              # Windows launcher
├── install.sh           # Linux system installer
├── output/              # Processed files saved here (auto-created)
├── README.md            # This file
└── CHANGELOG.md         # Release history
```

---

## License

MIT License — use freely in personal and commercial projects.
