# Changelog

All notable changes to PDF Tool Pro are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.1] — 2026-07-13

### Fixed

- **Ctrl+C now properly stops Streamlit** when port is already in use and PID cannot be found
  - Root cause: `ss -tlnp` shows port but Process column is empty (permissions issue), so all PID extraction methods (`lsof`, `fuser`, `ss`, `pgrep`) failed silently
  - Root cause: `wait` only works on child processes — Streamlit started by a previous `./run` is not a child of the current script
  - Solution: PID file (`/tmp/pdf-tool-pro.pid`) written when starting Streamlit, read back when port is already in use
  - Solution: `fuser -k PORT/tcp` kills Streamlit by port number directly when PID is unknown (no PID needed!)
  - Solution: Extracted shared helpers `port_in_use()` and `kill_by_port()` to reduce duplication
  - Solution: Replaced `ss -tlnp` with `ss -tln` (without `-p`) everywhere to avoid permission issues
- **`--stop` now uses `fuser -k` as fallback** when PID extraction fails, instead of just suggesting manual kill
- **Improved error messages** — warns if `fuser -k` may not have worked, with manual kill suggestion as fallback

### Changed

- Refactored launcher script with extracted helper functions for cleaner code
- Port detection uses robust regex pattern (`grep -E ":${PORT}[[:space:]]"`) to avoid matching wrong ports

---

## [1.0.0] — 2026-07-13

### Initial Release

#### Core Engine (`pdf_tool.py`)

- **Compress** — 4 compression methods using modern PyMuPDF APIs:
  - **Lossless** — `scrub()` + `subset_fonts()` + `ez_save()` — zero quality loss
  - **Smart** — `rewrite_images()` — compresses only images, text stays 100% sharp
  - **Aggressive** — `rewrite_images()` with grayscale + metadata strip
  - **Raster** — Full page render as JPEG (last resort)
- **Auto mode** — Analyzes PDF content (image density + file size) to pick the best method
- **Merge** — Combine multiple PDFs into a single file
- **Split** — Extract all pages or a specific range into separate files
- **Rotate** — Rotate all pages by 90°, 180°, or 270°
- **Crop** — Remove margins from all pages (configurable per edge, in points)
- **Extract Text** — Pull text content from all pages, save to file or stdout
- **Extract Images** — Save all embedded images with minimum size filter
- **Select Pages** — Extract specific pages with range syntax (`1-5,7,9-12`), with reverse option
- **Watermark** — Add text overlay with configurable opacity, font size, color, and diagonal tiling
- **Batch Compress** — Process all PDFs in a folder at once with summary table
- **PDF Info** — Display metadata, page count, encryption status, image count, and content detection
- **CLI** — Full argparse-based CLI with command aliases (e.g., `c` for compress, `m` for merge)

#### Web UI (`pdf_ui.py`)

- **Modern dark glassmorphism theme** — Custom CSS with gradient backgrounds, glass effects, and smooth animations
- **Sidebar navigation** — 10 operations accessible via radio buttons with hover effects
- **File upload** — Single or multi-file upload depending on operation
- **Interactive controls** — Sliders, selectboxes, number inputs, checkboxes for each operation
- **Real-time PDF info** — Automatic metadata display after upload
- **Compression metrics** — Before/after/percentage display with color-coded deltas
- **Image preview** — Inline preview of extracted images in a 3-column grid
- **Text preview** — Expandable text area for extracted text
- **ZIP download** — Split pages and extracted images bundled as ZIP for single download
- **Download button** — Prominent green download button with correct MIME types
- **Error handling** — User-friendly error messages for all operations
- **Session state** — Proper state management across Streamlit reruns
- **Responsive layout** — Works on desktop and mobile browsers

#### Launcher Scripts

- **`run`** (Linux) — GUI-first launcher with:
  - Python and dependency checking
  - Port conflict detection (reuses existing instance)
  - Background Streamlit launch with `disown`
  - Port polling until ready (30s timeout)
  - Browser auto-open via `xdg-open`
  - Desktop notification via `notify-send`
  - Error dialogs via `zenity` (falls back gracefully)
  - Log file at `/tmp/pdf-tool-pro-launch.log`
- **`run.bat`** (Windows) — Batch launcher with:
  - Python detection (`python3` then `python`)
  - Package availability checks
  - Clear error messages with installation instructions
- **`install.sh`** (Linux installer) — System installer with:
  - Python and dependency verification
  - Auto-install missing packages via pip
  - Registers `.desktop` file to `~/.local/share/applications/`
  - Sets MIME associations for shell script execution
  - Adds Thunar custom action for "Run Script"
  - Updates desktop database

#### Desktop Integration

- **`PDF-Tool-Pro.desktop`** — XFCE desktop entry with `Terminal=false`
- **`run-script.desktop`** — MIME handler for `application/x-shellscript` files
- **Thunar custom action** — "Run Script" right-click option for `.sh` files
- **MIME type registration** — Shell scripts configured to execute (not open in editor) on double-click

#### Output Folder

- **Auto-saves** all processed files to `output/` folder next to the program
- **Original filenames preserved** with operation suffix (e.g., `document-cmprs.pdf`)
- **No overwriting** — appends `_1`, `_2` if file already exists
- **Download button** still available for browser download

#### Launcher Updates

- **`run --stop`** — Gracefully stop the running Streamlit server
- **`run --help`** — Show usage instructions
- **`xdg-open` backgrounded** — Terminal no longer blocks when launching

#### Dependencies

- `PyMuPDF >= 1.25.0` — PDF rendering, compression, editing
- `Streamlit >= 1.0` — Web UI framework

---

## Known Issues

- **XFCE/Thunar double-click:** Double-clicking `.sh` files requires running `install.sh` first AND setting Thunar's "Executable text files" to "Ask each time" or "Run them" (Edit → Preferences → Behavior). Without this, files may open in a text editor.
- **Raster compression:** Converts vector content to raster images (lossy). Use lossless for text documents.
- **Watermark rotation:** Diagonal tiling uses horizontal stepping as a workaround due to PyMuPDF limitations.
- **No macOS launcher:** The `run` script uses `xdg-open` which is Linux-only. macOS users should run `streamlit run pdf_ui.py` directly.

---

## Roadmap

### v1.1.0

- [ ] Password-protected PDF support (encrypt/decrypt)
- [ ] PDF to images export (PNG/JPEG per page)
- [ ] Dark/light theme toggle in the UI

### v1.2.0

- [ ] PDF/A conversion for archival compliance
- [ ] PDF comparison (diff two documents)
- [ ] Bookmark/outline management

### v2.0.0

- [ ] REST API for headless integration
- [ ] Plugin system for custom operations
