#!/usr/bin/env python3
"""
📄 PDF Tool — Modern Web UI
=============================
A beautiful, modern web interface for PDF editing and compression.
Powered by Streamlit + PyMuPDF.

Usage:
  streamlit run pdf_ui.py
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from io import BytesIO

import streamlit as st

# Ensure the pdf_tool module can be imported
sys.path.insert(0, str(Path(__file__).parent))

from pdf_tool import (
    compress_pdf, merge_pdfs, split_pdf, rotate_pdf, crop_pdf,
    extract_text, extract_images, select_pages, add_watermark,
    get_pdf_info, _format_size, _parse_page_range,
)

# ═══════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PDF Tool Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════
#  CUSTOM CSS — Modern Dark Glassmorphism Theme
# ═══════════════════════════════════════════════════════════

CUSTOM_CSS = """
<style>
    /* ── Global Reset & Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ── Main Container ── */
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%);
        min-height: 100vh;
    }

    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: rgba(20, 20, 50, 0.95);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }
    section[data-testid="stSidebar"] .stRadio > label {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 0.6rem 1rem;
        margin: 0.15rem 0;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    section[data-testid="stSidebar"] .stRadio > label:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(99,102,241,0.3);
        transform: translateX(4px);
    }
    section[data-testid="stSidebar"] .stRadio > label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.15));
        border-color: rgba(99,102,241,0.4);
        box-shadow: 0 0 20px rgba(99,102,241,0.1);
    }

    /* ── Headers ── */
    h1, h2, h3 {
        font-weight: 700;
        background: linear-gradient(135deg, #e0e0ff 0%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
    }
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 1.8rem !important; }

    /* ── Cards ── */
    .card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    .card:hover {
        border-color: rgba(99,102,241,0.2);
        box-shadow: 0 8px 32px rgba(99,102,241,0.08);
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── File Uploader ── */
    section[data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.03);
        border: 2px dashed rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    section[data-testid="stFileUploader"]:hover {
        border-color: rgba(99,102,241,0.4);
        background: rgba(99,102,241,0.05);
    }

    /* ── Info Boxes ── */
    .info-box {
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .warning-box {
        background: rgba(234,179,8,0.1);
        border: 1px solid rgba(234,179,8,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* ── Metrics ── */
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem;
    }
    div[data-testid="metric-container"] > label {
        color: rgba(255,255,255,0.6) !important;
    }
    div[data-testid="metric-container"] > div {
        color: #e0e0ff !important;
    }

    /* ── Progress bars ── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #6366f1, #a855f7) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99,102,241,0.2) !important;
    }

    /* ── Slider ── */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #6366f1, #a855f7) !important;
    }

    /* ── Selectbox ── */
    div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
    }

    /* ── Text Input ── */
    input, textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    input:focus, textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-color: #6366f1 transparent transparent transparent !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
    }

    /* ── Download Button ── */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        box-shadow: 0 4px 15px rgba(16,185,129,0.3) !important;
    }
    .stDownloadButton > button:hover {
        box-shadow: 0 8px 25px rgba(16,185,129,0.4) !important;
    }

    /* ── Animations ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .fade-in {
        animation: fadeIn 0.4s ease-out;
    }
    .slide-in {
        animation: slideIn 0.3s ease-out;
    }

    /* ── Result container ── */
    .result-container {
        animation: fadeIn 0.5s ease-out;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.02);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(99,102,241,0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99,102,241,0.5);
    }

    /* ── Markdown text ── */
    p, li, .markdown-text-container {
        color: rgba(255,255,255,0.8) !important;
        line-height: 1.7 !important;
    }

    /* ── Sidebar title ── */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e0e0ff;
        padding: 0.5rem 0.5rem 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sidebar-title span {
        font-size: 1.6rem;
    }
</style>
"""


# ═══════════════════════════════════════════════════════════
#  APP STATE
# ═══════════════════════════════════════════════════════════

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "processed_bytes": None,
        "result_path": None,
        "result_data": None,
        "current_file_name": None,
        "processing": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ═══════════════════════════════════════════════════════════
#  OPERATION CONFIG
# ═══════════════════════════════════════════════════════════

OPERATIONS = {
    "📦 Compress": {
        "icon": "📦",
        "desc": "Reduce PDF file size (4 methods)",
        "long_desc": "Compress your PDF to reduce file size. Choose from:\n\n• Auto — Analyzes your PDF and picks the best approach\n• Lossless — Zero quality loss, strips metadata, subsets fonts\n• Smart — Compresses images only, text stays 100% sharp (recommended)\n• Aggressive — Maximum compression, lower DPI + grayscale\n• Raster — Renders pages as images, last resort for scanned docs",
        "multiple_files": False,
    },
    "🔗 Merge": {
        "icon": "🔗",
        "desc": "Combine multiple PDFs into one",
        "long_desc": "Merge multiple PDF files into a single document.\n\nUpload 2 or more PDFs and they will be combined in order into one file.",
        "multiple_files": True,
    },
    "✂️ Split": {
        "icon": "✂️",
        "desc": "Extract pages into separate files",
        "long_desc": "Split a PDF into individual pages or extract a specific range.\n\nEach page becomes a separate PDF file, or you can choose specific pages (e.g., 1-5,7,9-12).",
        "multiple_files": False,
    },
    "🔄 Rotate": {
        "icon": "🔄",
        "desc": "Rotate page orientation",
        "long_desc": "Rotate all pages in your PDF by 90, 180, or 270 degrees clockwise.\n\nUseful for scanned documents with wrong orientation.",
        "multiple_files": False,
    },
    "📐 Crop": {
        "icon": "📐",
        "desc": "Crop page margins",
        "long_desc": "Remove margins from all pages by setting the amount to cut from each edge.\n\nMeasurements are in points (72pt = 1 inch).",
        "multiple_files": False,
    },
    "📝 Extract Text": {
        "icon": "📝",
        "desc": "Extract text content",
        "long_desc": "Pull all text content from a PDF and save it as a plain text file.\n\nUseful for making PDFs searchable or copy-pasteable.",
        "multiple_files": False,
    },
    "🖼️ Extract Images": {
        "icon": "🖼️",
        "desc": "Extract embedded images",
        "long_desc": "Save all embedded images from a PDF to a folder.\n\nYou can set a minimum image size filter to ignore tiny icons or decorations.",
        "multiple_files": False,
    },
    "📑 Select Pages": {
        "icon": "📑",
        "desc": "Pick specific pages",
        "long_desc": "Extract specific pages from a PDF using page numbers or ranges.\n\nSupports syntax like 1,3,5-8 and can reverse page order.",
        "multiple_files": False,
    },
    "💧 Watermark": {
        "icon": "💧",
        "desc": "Add text watermark overlay",
        "long_desc": "Add a text watermark to every page.\n\nCustomize the text, opacity, font size, color, and choose between single or diagonal tiled placement.",
        "multiple_files": False,
    },
    "ℹ️ Info": {
        "icon": "ℹ️",
        "desc": "View PDF metadata & details",
        "long_desc": "View detailed information about your PDF.\n\nIncludes page count, file size, image count, text content, and metadata (title, author, creation date, etc.).",
        "multiple_files": False,
    },
}

# ═══════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temp and return path."""
    suffix = Path(uploaded_file.name).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def read_file_bytes(path: str) -> bytes:
    """Read a file as bytes."""
    with open(path, "rb") as f:
        return f.read()


# Output folder — save results next to the program
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Suffixes for each operation
OP_SUFFIXES = {
    "compress": "-cmprs",
    "merge": "-merged",
    "split": "-split",
    "rotate": "-rotated",
    "crop": "-cropped",
    "extract_text": "-text",
    "extract_images": "-images",
    "select": "-selected",
    "watermark": "-watermarked",
}


def get_output_path(original_name: str, op_key: str, ext: str = ".pdf") -> Path:
    """
    Build output path: output/<original_name_without_ext><suffix><ext>
    Example: output/document-cmprs.pdf
    """
    stem = Path(original_name).stem
    suffix = OP_SUFFIXES.get(op_key, "")
    out_path = OUTPUT_DIR / f"{stem}{suffix}{ext}"
    # Avoid overwriting — append number if exists
    counter = 1
    while out_path.exists():
        out_path = OUTPUT_DIR / f"{stem}{suffix}_{counter}{ext}"
        counter += 1
    return out_path


def show_pdf_info(input_path: str):
    """Display PDF info in a pretty format."""
    info = get_pdf_info(input_path)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pages", info["pages"])
    with col2:
        st.metric("Size", info["size_mb"])
    with col3:
        st.metric("Images", info["total_images"] if info["has_images"] else "None")
    with col4:
        st.metric("Has Text", "✅ Yes" if info["has_text"] else "❌ No")

    meta = info["metadata"]
    has_meta = any(v for v in meta.values())
    if has_meta:
        with st.expander("📋 Metadata", expanded=False):
            for key, val in meta.items():
                if val:
                    label = key.replace("_", " ").title()
                    st.write(f"**{label}:** {val}")


# ═══════════════════════════════════════════════════════════
#  OPERATION PANELS
# ═══════════════════════════════════════════════════════════

def render_compress_panel(input_path: str, original_name: str = ""):
    """Compress panel."""
    st.markdown("### ⚙️ Compression Settings")

    method = st.selectbox(
        "Method",
        options=["auto", "lossless", "smart", "aggressive", "raster"],
        index=0,
        help="auto: analyzes PDF and picks the best method",
    )

    # Show method descriptions
    method_info = {
        "auto": "🔍 Analyzes your PDF and picks the best approach automatically",
        "lossless": "✨ Zero quality loss — strips metadata, subsets fonts, removes dead weight",
        "smart": "🎯 Compresses images only — text stays 100% sharp (recommended)",
        "aggressive": "⚡ Maximum compression — lower DPI + grayscale, best for email/web",
        "raster": "🖼️ Renders pages as images — last resort for scanned docs only",
    }
    st.info(method_info.get(method, ""))

    # Show quality settings for methods that use them
    if method in ("smart", "aggressive", "raster", "auto"):
        col1, col2 = st.columns(2)
        with col1:
            quality = st.slider(
                "Image Quality",
                min_value=10, max_value=100, value=75, step=5,
                help="Higher = better quality, larger file",
            )
        with col2:
            dpi_target = st.slider(
                "Target DPI",
                min_value=72, max_value=300, value=150, step=12,
                help="Images above 200 DPI get downsampled to this",
            )
    else:
        quality = 75
        dpi_target = 150

    if st.button("📦 Compress Now", use_container_width=True, type="primary"):
        try:
            with st.spinner("Compressing PDF... 🔄"):
                out_path = get_output_path(original_name or Path(input_path).name, "compress")
                result = compress_pdf(
                    input_path, str(out_path),
                    method=method, quality=quality,
                    dpi_target=dpi_target,
                )
            st.session_state.processed_bytes = read_file_bytes(str(out_path))
            st.session_state.current_file_name = out_path.name

            st.markdown('<div class="result-container">', unsafe_allow_html=True)
            st.markdown("### ✅ Compression Complete")

            cols = st.columns(3)
            with cols[0]:
                st.metric("Original", _format_size(result["original_size"]))
            with cols[1]:
                st.metric("Compressed", _format_size(result["new_size"]))
            with cols[2]:
                reduction = result["reduction_percent"]
                st.metric("Saved", f"{reduction:.1f}%",
                          delta=f"{_format_size(result['saved_bytes'])}" if reduction >= 0 else None,
                          delta_color="inverse" if reduction < 0 else "normal")

            st.success(f"💾 Saved to: `{out_path}`")
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Compression failed: {e}")


def render_merge_panel(input_paths: list, original_names: list = None):
    """Merge panel."""
    st.markdown("### 🔗 Merge Settings")
    st.info(f"📎 **{len(input_paths)}** files loaded")
    for i, p in enumerate(input_paths):
        st.write(f"  **{i+1}.** {Path(p).name}")

    if st.button("🔗 Merge Now", use_container_width=True, type="primary"):
        try:
            with st.spinner("Merging PDFs... 🔄"):
                first_name = (original_names[0] if original_names else Path(input_paths[0]).name)
                out_path = get_output_path(first_name, "merge")
                result = merge_pdfs(input_paths, str(out_path))
            st.session_state.processed_bytes = read_file_bytes(str(out_path))
            st.session_state.current_file_name = out_path.name
            st.success(f"✅ Merged {result['input_files']} files → {_format_size(result['output_size'])}")
            st.info(f"💾 Saved to: `{out_path}`")
        except Exception as e:
            st.error(f"❌ Merge failed: {e}")


def render_split_panel(input_path: str, original_name: str = ""):
    """Split panel."""
    doc_info = get_pdf_info(input_path)
    total = doc_info["pages"]
    st.markdown("### ✂️ Split Settings")
    st.info(f"📄 This PDF has **{total}** pages")

    col1, col2 = st.columns([3, 1])
    with col1:
        use_range = st.checkbox("Extract specific pages only", value=False)
    pages_str = ""
    if use_range:
        pages_str = st.text_input(
            "Pages (e.g. '1-5,7,9-12')",
            placeholder=f"1-{total}",
            help="Leave empty to extract all pages as separate files",
        )

    if st.button("✂️ Split Now", use_container_width=True, type="primary"):
        try:
            with st.spinner("Splitting PDF... 🔄"):
                stem = Path(original_name).stem if original_name else Path(input_path).stem
                out_dir = OUTPUT_DIR / f"{stem}-split"
                out_dir.mkdir(exist_ok=True)
                page_range = pages_str if use_range and pages_str.strip() else None
                result = split_pdf(input_path, str(out_dir), page_range)

            st.success(f"✅ Extracted **{result['extracted']}** of **{result['total_pages']}** pages")
            st.info(f"💾 Saved to: `{out_dir}/`")

            # Create a zip of all pages for download
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(out_dir.glob("*.pdf")):
                    zf.write(f, f.name)
            zip_buffer.seek(0)

            st.session_state.processed_bytes = zip_buffer.getvalue()
            stem = Path(original_name).stem if original_name else Path(input_path).stem
            st.session_state.current_file_name = f"{stem}-split.zip"
        except Exception as e:
            st.error(f"❌ Split failed: {e}")


def render_rotate_panel(input_path: str, original_name: str = ""):
    """Rotate panel."""
    st.markdown("### 🔄 Rotation Settings")
    angle = st.selectbox(
        "Rotation Angle",
        options=[90, 180, 270],
        index=0,
        help="Clockwise rotation in degrees",
    )

    if st.button("🔄 Rotate Now", use_container_width=True, type="primary"):
        try:
            with st.spinner("Rotating pages... 🔄"):
                out_path = get_output_path(original_name or Path(input_path).name, "rotate")
                result = rotate_pdf(input_path, str(out_path), angle)
            st.session_state.processed_bytes = read_file_bytes(str(out_path))
            st.session_state.current_file_name = out_path.name
            st.success(f"✅ Rotated {result['pages_rotated']} pages by {angle}°")
            st.info(f"💾 Saved to: `{out_path}`")
        except Exception as e:
            st.error(f"❌ Rotation failed: {e}")


def render_crop_panel(input_path: str, original_name: str = ""):
    """Crop panel."""
    st.markdown("### 📐 Crop Settings")
    st.info("Set margins in points (72pt = 1 inch) to remove from each edge.")
    col1, col2 = st.columns(2)
    with col1:
        left = st.number_input("Left margin", min_value=0.0, value=0.0, step=5.0, format="%.1f")
        top = st.number_input("Top margin", min_value=0.0, value=0.0, step=5.0, format="%.1f")
    with col2:
        right = st.number_input("Right margin", min_value=0.0, value=0.0, step=5.0, format="%.1f")
        bottom = st.number_input("Bottom margin", min_value=0.0, value=0.0, step=5.0, format="%.1f")

    if st.button("📐 Crop Now", use_container_width=True, type="primary"):
        try:
            with st.spinner("Cropping PDF... 🔄"):
                out_path = get_output_path(original_name or Path(input_path).name, "crop")
                result = crop_pdf(input_path, str(out_path), left, right, top, bottom)
            st.session_state.processed_bytes = read_file_bytes(str(out_path))
            st.session_state.current_file_name = out_path.name
            st.success(f"✅ Cropped successfully!")
            st.info(f"💾 Saved to: `{out_path}`")
        except Exception as e:
            st.error(f"❌ Crop failed: {e}")


def render_extract_text_panel(input_path: str, original_name: str = ""):
    """Extract text panel."""
    if st.button("📝 Extract Text", use_container_width=True, type="primary"):
        try:
            with st.spinner("Extracting text... 🔄"):
                text = extract_text(input_path)
                out_path = get_output_path(original_name or Path(input_path).name, "extract_text", ext=".txt")
                out_path.write_text(text, encoding="utf-8")
            st.session_state.result_data = text
            st.session_state.current_file_name = out_path.name
            st.session_state.processed_bytes = text.encode("utf-8")

            st.markdown("### ✅ Text Extracted")
            st.info(f"💾 Saved to: `{out_path}`")
            with st.expander("📄 Preview", expanded=True):
                st.text_area("Extracted Text", text, height=300)
        except Exception as e:
            st.error(f"❌ Text extraction failed: {e}")


def render_extract_images_panel(input_path: str, original_name: str = ""):
    """Extract images panel."""
    min_size = st.number_input(
        "Minimum image size (bytes)",
        min_value=0, value=100, step=50,
        help="Ignores tiny images below this size",
    )

    if st.button("🖼️ Extract Images", use_container_width=True, type="primary"):
        try:
            with st.spinner("Extracting images... 🔄"):
                stem = Path(original_name).stem if original_name else Path(input_path).stem
                out_dir = OUTPUT_DIR / f"{stem}-images"
                out_dir.mkdir(exist_ok=True)
                result = extract_images(input_path, str(out_dir), min_size=min_size)

            if result["images_extracted"] == 0:
                st.warning("⚠️ No images found in this PDF (or all were below minimum size)")
            else:
                st.success(f"✅ Extracted **{result['images_extracted']}** images ({_format_size(result['total_size_bytes'])})")
                st.info(f"💾 Saved to: `{out_dir}/`")

                # Show image previews
                cols = st.columns(3)
                for i, img_path in enumerate(sorted(out_dir.iterdir())):
                    with cols[i % 3]:
                        st.image(str(img_path), use_container_width=True)

                # Create zip for download
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in sorted(out_dir.iterdir()):
                        zf.write(f, f.name)
                zip_buffer.seek(0)
                st.session_state.processed_bytes = zip_buffer.getvalue()
                stem = Path(original_name).stem if original_name else Path(input_path).stem
                st.session_state.current_file_name = f"{stem}-images.zip"
        except Exception as e:
            st.error(f"❌ Image extraction failed: {e}")


def render_select_panel(input_path: str, original_name: str = ""):
    """Select pages panel."""
    doc_info = get_pdf_info(input_path)
    total = doc_info["pages"]
    st.markdown("### 📑 Select Pages")
    st.info(f"📄 This PDF has **{total}** pages")

    pages_str = st.text_input(
        "Page numbers to extract",
        placeholder="e.g. 1,3,5-8",
        help="1-indexed, supports ranges like '1-5' and commas '1,3,5'",
    )
    reverse = st.checkbox("Reverse page order", value=False)

    if st.button("📑 Extract Selected Pages", use_container_width=True, type="primary"):
        if not pages_str.strip():
            st.error("⚠️ Please enter page numbers")
            return
        with st.spinner("Extracting pages... 🔄"):
            try:
                pages = _parse_page_range(pages_str, total)
                if not pages:
                    st.error(f"⚠️ No valid pages in range (1-{total})")
                    return
                out_path = get_output_path(original_name or Path(input_path).name, "select")
                result = select_pages(input_path, str(out_path), pages, reverse)
            except Exception as e:
                st.error(f"⚠️ Error: {e}")
                return

        st.session_state.processed_bytes = read_file_bytes(str(out_path))
        st.session_state.current_file_name = out_path.name
        st.success(f"✅ Extracted **{len(pages)}** pages")
        st.info(f"💾 Saved to: `{out_path}`")


def render_watermark_panel(input_path: str, original_name: str = ""):
    """Watermark panel."""
    st.markdown("### 💧 Watermark Settings")
    text = st.text_input("Watermark Text", value="CONFIDENTIAL")
    col1, col2 = st.columns(2)
    with col1:
        opacity = st.slider("Opacity", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
        font_size = st.slider("Font Size", min_value=12, max_value=120, value=72, step=6)
    with col2:
        diagonal = st.checkbox("Diagonal tiling", value=True, help="Tile text across page")
        # Color picker-like: simple presets
        color_presets = {
            "Gray": (0.5, 0.5, 0.5),
            "Red": (0.8, 0.2, 0.2),
            "Blue": (0.2, 0.3, 0.8),
            "Green": (0.2, 0.7, 0.2),
            "Black": (0, 0, 0),
            "Light Gray": (0.7, 0.7, 0.7),
        }
        color_name = st.selectbox("Color", options=list(color_presets.keys()))
        color = color_presets[color_name]

    if st.button("💧 Add Watermark", use_container_width=True, type="primary"):
        try:
            with st.spinner("Adding watermark... 🔄"):
                out_path = get_output_path(original_name or Path(input_path).name, "watermark")
                result = add_watermark(
                    input_path, str(out_path),
                    text=text, opacity=opacity,
                    font_size=font_size, color=color,
                    diagonal=diagonal,
                )
            st.session_state.processed_bytes = read_file_bytes(str(out_path))
            st.session_state.current_file_name = out_path.name
            st.success(f"✅ Watermark added")
            st.info(f"💾 Saved to: `{out_path}`")
        except Exception as e:
            st.error(f"❌ Watermark failed: {e}")


def render_info_panel(input_path: str):
    """Info panel."""
    st.markdown("### ℹ️ PDF Information")
    show_pdf_info(input_path)


# ═══════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════

def main():
    init_session_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Header ──
    st.markdown(
        '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem">'
        '<span style="font-size:2.5rem">📄</span>'
        '<div><h1 style="margin:0">PDF Tool Pro</h1>'
        '<p style="color:rgba(255,255,255,0.5);margin:0">Edit, Compress &amp; Manipulate PDFs — beautifully</p></div></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-title"><span>⚡</span> Operations</div>',
            unsafe_allow_html=True,
        )
        operation = st.radio(
            "Choose an operation",
            options=list(OPERATIONS.keys()),
            format_func=lambda x: f"{x}",
            label_visibility="collapsed",
        )
        st.divider()
        op_info = OPERATIONS[operation]

        st.markdown(
            f'<p style="color:rgba(255,255,255,0.5);font-size:0.9rem">'
            f'{op_info["desc"]}</p>',
            unsafe_allow_html=True,
        )

        # File upload(s) in sidebar
        st.markdown("### 📎 Files")
        if op_info["multiple_files"]:
            uploaded_files = st.file_uploader(
                "Upload PDF files",
                type="pdf",
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
        else:
            uploaded_files = st.file_uploader(
                "Upload a PDF file",
                type="pdf",
                accept_multiple_files=False,
                label_visibility="collapsed",
            )

        st.divider()
        st.caption("PDF Tool Pro v1.0 • Powered by PyMuPDF + Streamlit")

    # ── Main Content ──
    main_col = st.container()

    with main_col:
        # Check if files are uploaded
        if not uploaded_files:
            long_desc = op_info.get("long_desc", "").replace("\n", "<br>")
            st.markdown(
                '<div class="card fade-in" style="text-align:center;padding:4rem">'
                f'<span style="font-size:4rem">{op_info["icon"]}</span>'
                f'<h2>{operation}</h2>'
                f'<p style="color:rgba(255,255,255,0.6);max-width:600px;margin:0 auto;line-height:1.8">'
                f'{long_desc}</p>'
                '<br>'
                f'<p style="color:rgba(255,255,255,0.4)">'
                f'Upload your PDF{"" if not op_info["multiple_files"] else "s"} to get started.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            # Clear previous results
            st.session_state.processed_bytes = None
            st.session_state.result_data = None
            return

        # Convert uploaded files to temp paths
        if op_info["multiple_files"]:
            input_paths = [save_uploaded_file(f) for f in uploaded_files]
            input_path = input_paths[0]  # primary file for operations that need one
        else:
            input_path = save_uploaded_file(uploaded_files)
            input_paths = [input_path]

        # Show current file info
        if op_info["multiple_files"]:
            fname = f"{len(uploaded_files)} files"
        else:
            fname = uploaded_files.name
        st.markdown(
            f'<div class="info-box fade-in">📎 <strong>File{"" if not op_info["multiple_files"] else "s"}:</strong> '
            f'{fname}</div>',
            unsafe_allow_html=True,
        )

        # Show quick info card if single file (skip for Info operation — panel shows it)
        if not op_info["multiple_files"] and operation != "ℹ️ Info":
            show_pdf_info(input_path)

        st.markdown('<div class="fade-in">', unsafe_allow_html=True)

        # Get original filename(s) from uploaded files
        if op_info["multiple_files"]:
            original_names = [f.name for f in uploaded_files]
        else:
            original_names = [uploaded_files.name]

        # Render the appropriate panel
        panel_map = {
            "📦 Compress": lambda p: render_compress_panel(p, original_names[0]),
            "🔗 Merge": lambda p: render_merge_panel(input_paths, original_names),
            "✂️ Split": lambda p: render_split_panel(p, original_names[0]),
            "🔄 Rotate": lambda p: render_rotate_panel(p, original_names[0]),
            "📐 Crop": lambda p: render_crop_panel(p, original_names[0]),
            "📝 Extract Text": lambda p: render_extract_text_panel(p, original_names[0]),
            "🖼️ Extract Images": lambda p: render_extract_images_panel(p, original_names[0]),
            "📑 Select Pages": lambda p: render_select_panel(p, original_names[0]),
            "💧 Watermark": lambda p: render_watermark_panel(p, original_names[0]),
            "ℹ️ Info": render_info_panel,
        }

        panel_map[operation](input_path)

        st.markdown('</div>', unsafe_allow_html=True)

        # ── Download Button ──
        if st.session_state.processed_bytes is not None:
            st.divider()
            fname = st.session_state.current_file_name or "output.pdf"
            fname = fname.replace(" ", "_").lower()

            mime_map = {
                ".pdf": "application/pdf",
                ".txt": "text/plain",
                ".zip": "application/zip",
            }
            ext = Path(fname).suffix
            mime = mime_map.get(ext, "application/octet-stream")

            st.download_button(
                label=f"⬇️ Download {fname}",
                data=st.session_state.processed_bytes,
                file_name=fname,
                mime=mime,
                use_container_width=True,
            )

        # Cleanup temp files
        for p in input_paths:
            try:
                os.unlink(p)
            except (OSError, PermissionError):
                pass


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
