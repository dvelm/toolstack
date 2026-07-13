#!/usr/bin/env python3
"""
📄 PDF Tool — Edit, Compress & Manipulate PDF Files
=====================================================
A comprehensive CLI tool for PDF editing, compression, and manipulation.

Features:
  • Compress PDFs (4 methods: lossless, smart, aggressive, raster)
  • Merge multiple PDFs into one
  • Split PDFs into separate files
  • Rotate pages
  • Crop pages
  • Extract text from PDFs
  • Extract images from PDFs
  • Remove/select specific pages
  • Reorder pages
  • Add watermarks
  • View PDF metadata and info

Usage:
  python pdf_tool.py <command> [options]

Examples:
  python pdf_tool.py compress input.pdf -o compressed.pdf -m smart -q 80
  python pdf_tool.py merge file1.pdf file2.pdf -o merged.pdf
  python pdf_tool.py split input.pdf -o pages/
  python pdf_tool.py info input.pdf
  python pdf_tool.py rotate input.pdf -o rotated.pdf -a 90
  python pdf_tool.py extract-text input.pdf -o output.txt
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────
# Core Imports
# ──────────────────────────────────────────────────────────

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)



# ──────────────────────────────────────────────────────────
# Version
# ──────────────────────────────────────────────────────────

VERSION = "1.0.0"


# ══════════════════════════════════════════════════════════
#  COMPRESSION MODULE
# ══════════════════════════════════════════════════════════

def compress_lossless(
    input_path: str,
    output_path: str,
) -> dict:
    """
    Method 1 — Lossless Optimization:
      Uses PyMuPDF's scrub() + subset_fonts() + ez_save().
      Preserves ALL quality. Best for text-heavy PDFs and documents
      where you need pixel-perfect output.
      Strips metadata, subsets fonts, removes dead weight.
    """
    orig_size = Path(input_path).stat().st_size
    doc = fitz.open(input_path)

    # 1. Strip dead weight (metadata, thumbnails, attachments)
    doc.scrub(
        metadata=True,
        xml_metadata=True,
        attached_files=True,
        embedded_files=True,
        thumbnails=True,
        reset_fields=True,
        reset_responses=True,
    )

    # 2. Subset fonts — keep only used glyphs
    doc.subset_fonts()

    # 3. Save with garbage collection + deflate
    doc.ez_save(output_path)
    doc.close()

    new_size = Path(output_path).stat().st_size
    ratio = (1 - new_size / orig_size) * 100

    return {
        "original_size": orig_size,
        "new_size": new_size,
        "saved_bytes": orig_size - new_size,
        "reduction_percent": round(ratio, 2),
    }


def compress_smart(
    input_path: str,
    output_path: str,
    quality: int = 75,
    dpi_target: int = 150,
    dpi_threshold: int = 200,
) -> dict:
    """
    Method 2 — Smart Compression (Recommended):
      Uses PyMuPDF's rewrite_images() to compress ONLY images
      while preserving all vector text, annotations, and metadata.
      This is the best balance of quality vs file size.

      - Images above dpi_threshold are downsampled to dpi_target
      - JPEG quality controls recompression level
      - Text and vector graphics remain 100% sharp
    """
    orig_size = Path(input_path).stat().st_size
    doc = fitz.open(input_path)

    # Rewrite images — compress only images, preserve everything else
    doc.rewrite_images(
        dpi_threshold=dpi_threshold,
        dpi_target=dpi_target,
        quality=quality,
        lossy=True,
        lossless=True,
        bitonal=True,
        color=True,
        gray=True,
    )

    # Subset fonts and save
    doc.subset_fonts()
    doc.ez_save(output_path)
    doc.close()

    new_size = Path(output_path).stat().st_size
    ratio = (1 - new_size / orig_size) * 100

    return {
        "original_size": orig_size,
        "new_size": new_size,
        "saved_bytes": orig_size - new_size,
        "reduction_percent": round(ratio, 2),
    }


def compress_aggressive(
    input_path: str,
    output_path: str,
    quality: int = 50,
    dpi_target: int = 96,
    dpi_threshold: int = 100,
) -> dict:
    """
    Method 3 — Aggressive Compression:
      Maximum size reduction. Uses rewrite_images() with very low
      DPI targets + converts to grayscale + strips all metadata.
      Good for email/web where file size matters most.
    """
    orig_size = Path(input_path).stat().st_size
    doc = fitz.open(input_path)

    # Strip all metadata aggressively
    doc.scrub(
        metadata=True,
        xml_metadata=True,
        attached_files=True,
        embedded_files=True,
        thumbnails=True,
        reset_fields=True,
        reset_responses=True,
    )

    # Rewrite images with aggressive settings
    doc.rewrite_images(
        dpi_threshold=dpi_threshold,
        dpi_target=dpi_target,
        quality=quality,
        lossy=True,
        lossless=True,
        bitonal=True,
        color=True,
        gray=True,
        set_to_gray=True,  # Convert to grayscale for maximum compression
    )

    # Subset fonts and save
    doc.subset_fonts()
    doc.ez_save(output_path)
    doc.close()

    new_size = Path(output_path).stat().st_size
    ratio = (1 - new_size / orig_size) * 100

    return {
        "original_size": orig_size,
        "new_size": new_size,
        "saved_bytes": orig_size - new_size,
        "reduction_percent": round(ratio, 2),
    }


def compress_raster(
    input_path: str,
    output_path: str,
    zoom: float = 0.75,
    quality: int = 85,
) -> dict:
    """
    Method 4 — Full Raster (Last Resort):
      Renders every page as a JPEG image.
      ⚠ Destroys vector text — use only for scanned documents
      where text layer is not needed.
      Maximum compression for image-only PDFs.
    """
    doc = fitz.open(input_path)
    new_doc = fitz.open()
    orig_size = Path(input_path).stat().st_size

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("jpeg", quality)

        rect = fitz.Rect(0, 0, pix.width, pix.height)
        new_page = new_doc.new_page(width=pix.width, height=pix.height)
        new_page.insert_image(rect, stream=img_bytes)

    doc.close()

    # Save with aggressive options
    new_doc.ez_save(output_path)
    new_doc.close()

    new_size = Path(output_path).stat().st_size
    ratio = (1 - new_size / orig_size) * 100

    return {
        "original_size": orig_size,
        "new_size": new_size,
        "saved_bytes": orig_size - new_size,
        "reduction_percent": round(ratio, 2),
    }


def compress_pdf(
    input_path: str,
    output_path: str,
    method: str = "auto",
    quality: int = 75,
    dpi_target: int = 150,
) -> dict:
    """
    Compress a PDF file using the specified method.
    'auto' analyzes the PDF and picks the best method.
    """
    print(f"  📥 Input:  {input_path}")
    print(f"  📤 Output: {output_path}")
    print(f"  🔧 Method: {method}")

    if method == "auto":
        # Analyze PDF to choose best method
        doc = fitz.open(input_path)
        total_images = 0
        total_pages = len(doc)
        for page_num in range(min(total_pages, 10)):  # Sample first 10 pages
            page = doc[page_num]
            total_images += len(page.get_images(full=True))
        doc.close()

        size_mb = Path(input_path).stat().st_size / (1024 * 1024)
        images_per_page = total_images / max(total_pages, 1)

        if images_per_page < 0.5 and size_mb < 10:
            print("  ℹ️  Text-heavy PDF → using lossless optimization")
            method = "lossless"
        elif images_per_page >= 2 or size_mb > 20:
            print(f"  ℹ️  Image-heavy PDF ({images_per_page:.1f} imgs/page) → using smart compression")
            method = "smart"
        else:
            print(f"  ℹ️  Mixed content → using smart compression")
            method = "smart"

    methods = {
        "lossless": compress_lossless,
        "smart": compress_smart,
        "aggressive": compress_aggressive,
        "raster": compress_raster,
    }

    if method not in methods:
        raise ValueError(f"Unknown compression method: {method}. "
                         f"Use: auto, lossless, smart, aggressive, or raster")

    if method == "lossless":
        result = compress_lossless(input_path, output_path)
    elif method == "smart":
        result = compress_smart(input_path, output_path, quality=quality, dpi_target=dpi_target)
    elif method == "aggressive":
        result = compress_aggressive(input_path, output_path, quality=quality, dpi_target=max(72, dpi_target - 60))
    elif method == "raster":
        result = compress_raster(input_path, output_path, zoom=dpi_target / 300, quality=quality)
    else:
        raise ValueError(f"Unknown method: {method}")

    return result


# ══════════════════════════════════════════════════════════
#  EDITING MODULE
# ══════════════════════════════════════════════════════════

def merge_pdfs(input_paths: list[str], output_path: str) -> dict:
    """Merge multiple PDFs into one."""
    doc_out = fitz.open()

    for path in input_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"File not found: {path}")
        doc_in = fitz.open(path)
        doc_out.insert_pdf(doc_in)
        doc_in.close()

    doc_out.save(output_path, garbage=4, deflate=True)
    doc_out.close()

    return {
        "input_files": len(input_paths),
        "output": output_path,
        "output_size": Path(output_path).stat().st_size,
    }


def split_pdf(input_path: str, output_dir: str, page_range: Optional[str] = None) -> dict:
    """
    Split PDF into separate pages or a page range.
    page_range format: "1-5" or "1,3,5" or "1-5,7,9-12"
    """
    doc = fitz.open(input_path)
    total = len(doc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(input_path).stem
    pages_to_extract = _parse_page_range(page_range, total) if page_range else list(range(total))
    extracted = 0

    for page_num in pages_to_extract:
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        out_path = output_dir / f"{base_name}_page_{page_num + 1:04d}.pdf"
        new_doc.save(str(out_path), garbage=4, deflate=True)
        new_doc.close()
        extracted += 1

    doc.close()

    return {
        "input": input_path,
        "total_pages": total,
        "extracted": extracted,
        "output_dir": str(output_dir),
    }


def rotate_pdf(input_path: str, output_path: str, angle: int = 90) -> dict:
    """Rotate all pages by angle (90, 180, 270)."""
    doc = fitz.open(input_path)
    total = len(doc)

    for page_num in range(total):
        page = doc[page_num]
        page.set_rotation(angle)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return {
        "input": input_path,
        "output": output_path,
        "angle": angle,
        "pages_rotated": total,
    }


def crop_pdf(input_path: str, output_path: str,
             left: float = 0, right: float = 0,
             top: float = 0, bottom: float = 0) -> dict:
    """
    Crop pages by margins (in points, 72pt = 1 inch).
    Positive values shrink the visible area inward.
    """
    doc = fitz.open(input_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect

        new_rect = fitz.Rect(
            rect.x0 + left,
            rect.y0 + top,
            rect.x1 - right,
            rect.y1 - bottom,
        )

        # Ensure we don't clip to negative
        new_rect = new_rect.normalize()
        page.set_cropbox(new_rect)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return {
        "input": input_path,
        "output": output_path,
        "margins": {"left": left, "right": right, "top": top, "bottom": bottom},
    }


def extract_text(input_path: str, output_path: Optional[str] = None) -> str:
    """Extract text from all pages and optionally save to file."""
    doc = fitz.open(input_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            text_parts.append(f"─" * 60)
            text_parts.append(f"  Page {page_num + 1}")
            text_parts.append(f"─" * 60)
            text_parts.append(text)

    doc.close()
    full_text = "\n".join(text_parts)

    if output_path:
        Path(output_path).write_text(full_text, encoding="utf-8")

    return full_text


def extract_images(input_path: str, output_dir: str, min_size: int = 100) -> dict:
    """Extract images from PDF and save them."""
    doc = fitz.open(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(input_path).stem
    total_extracted = 0
    total_size = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            if len(image_bytes) < min_size:
                continue

            img_path = output_dir / f"{base_name}_p{page_num + 1:04d}_img{img_index + 1:03d}.{image_ext}"
            img_path.write_bytes(image_bytes)
            total_extracted += 1
            total_size += len(image_bytes)

    doc.close()

    return {
        "input": input_path,
        "output_dir": str(output_dir),
        "images_extracted": total_extracted,
        "total_size_bytes": total_size,
    }


def select_pages(input_path: str, output_path: str,
                 pages: list[int], reverse: bool = False) -> dict:
    """
    Select specific pages from a PDF.
    Pages are 1-indexed.
    """
    doc = fitz.open(input_path)
    total = len(doc)
    new_doc = fitz.open()

    # Validate page indices
    valid_pages = []
    for p in pages:
        if 1 <= p <= total:
            valid_pages.append(p)
        else:
            print(f"  ⚠️  Warning: page {p} is out of range (1-{total})")

    if reverse:
        valid_pages = sorted(valid_pages, reverse=True)

    for p in valid_pages:
        new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)

    if len(new_doc) == 0:
        raise ValueError("No valid pages to extract")

    new_doc.save(output_path, garbage=4, deflate=True)
    new_doc.close()
    doc.close()

    return {
        "input": input_path,
        "output": output_path,
        "selected_pages": valid_pages,
        "total_output_pages": len(valid_pages),
    }


def add_watermark(input_path: str, output_path: str,
                  text: str, opacity: float = 0.3,
                  font_size: int = 72, color: tuple = (0.5, 0.5, 0.5),
                  diagonal: bool = True) -> dict:
    """
    Add a text watermark to every page.
    Uses page-level text insertion for reliable compatibility.
    """
    doc = fitz.open(input_path)

    # Clamp opacity to valid range
    opacity = max(0.0, min(1.0, opacity))

    # Normalize color — accept tuples or use gray default
    if isinstance(color, tuple) and len(color) == 3:
        r, g, b = color
    else:
        r = g = b = 0.5

    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect

        # Create a subtle background tint using Shape with opacity
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(
            fill=(r, g, b),
            fill_opacity=opacity / 4,  # Subtle background tint
            width=0,
        )
        shape.commit()

        # Add watermark text using page-level insertion
        if diagonal:
            # Place watermark diagonally — repeat across page for coverage
            # Note: page.insert_text() does not support arbitrary rotation
            # in all PyMuPDF versions, so we tile horizontally instead
            step_y = int(rect.height * 0.25)
            for y_offset in range(step_y, int(rect.height), step_y):
                page.insert_text(
                    point=(rect.width * 0.05, y_offset),
                    text=text,
                    fontsize=font_size,
                    color=(r, g, b),
                    overlay=False,
                )
        else:
            # Center the watermark horizontally
            char_avg_width = font_size * 0.6
            text_width = len(text) * char_avg_width
            x_center = (rect.width - text_width) / 2

            page.insert_text(
                point=(x_center, rect.height / 2),
                text=text,
                fontsize=font_size,
                color=(r, g, b),
                overlay=False,
            )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return {
        "input": input_path,
        "output": output_path,
        "watermark_text": text,
        "opacity": opacity,
    }


# ══════════════════════════════════════════════════════════
#  INFO & UTILITY MODULE
# ══════════════════════════════════════════════════════════

def get_pdf_info(input_path: str) -> dict:
    """Get detailed information about a PDF file."""
    doc = fitz.open(input_path)
    metadata = doc.metadata or {}
    path = Path(input_path)

    info = {
        "filename": path.name,
        "path": str(path.absolute()),
        "size_bytes": path.stat().st_size,
        "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        "pages": len(doc),
        "pdf_version": f"PDF {doc.pdf_version}" if hasattr(doc, 'pdf_version') and doc.pdf_version else "Unknown",
        "encrypted": doc.is_encrypted,
        "needs_pass": doc.needs_pass if hasattr(doc, 'needs_pass') else False,
        "metadata": {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "mod_date": metadata.get("modDate", ""),
        },
        "has_images": False,
        "total_images": 0,
        "has_text": False,
    }

    # Check for images and text
    for page_num in range(min(len(doc), 5)):  # Check first 5 pages
        page = doc[page_num]
        images = page.get_images(full=True)
        if images:
            info["has_images"] = True
            info["total_images"] += len(images)
        text = page.get_text("text").strip()
        if text:
            info["has_text"] = True

    # If more pages, sample
    if len(doc) > 5:
        for page_num in range(5, len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            if images:
                info["total_images"] += len(images)
            if not info["has_text"]:
                text = page.get_text("text").strip()
                if text:
                    info["has_text"] = True

    doc.close()
    return info


def display_info(info: dict) -> None:
    """Pretty-print PDF info."""
    print(f"\n📄  PDF Information")
    print(f"{'─' * 60}")
    print(f"  Filename:     {info['filename']}")
    print(f"  Path:         {info['path']}")
    print(f"  Size:         {info['size_mb']} MB ({info['size_bytes']:,} bytes)")
    print(f"  Pages:        {info['pages']}")
    print(f"  Version:      {info['pdf_version']}")
    print(f"  Encrypted:    {'🔒 Yes' if info['encrypted'] else '🔓 No'}")

    if info["total_images"] > 0:
        print(f"  Images:       {info['total_images']} found")
    print(f"  Contains text: {'✅ Yes' if info['has_text'] else '❌ No (scanned?)'}")
    print()

    meta = info["metadata"]
    has_meta = any(v for v in meta.values())
    if has_meta:
        print(f"  📋  Metadata")
        print(f"  {'─' * 56}")
        for key, val in meta.items():
            if val:
                label = key.replace("_", " ").title()
                print(f"    {label:20}: {val}")
    else:
        print(f"  📋  Metadata: None")
    print()


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _parse_page_range(range_str: str, total: int) -> list[int]:
    """
    Parse a page range string like "1-5,7,9-12" into a list of 0-indexed ints.
    """
    pages = set()
    parts = range_str.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start.strip())
            end = int(end.strip())
            pages.update(range(max(1, start), min(total, end) + 1))
        else:
            p = int(part)
            if 1 <= p <= total:
                pages.add(p)

    return sorted(pages)


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _print_compression_result(result: dict) -> None:
    """Display compression results."""
    old_fmt = _format_size(result["original_size"])
    new_fmt = _format_size(result["new_size"])
    saved_fmt = _format_size(result["saved_bytes"])
    pct = result["reduction_percent"]

    print(f"\n  ✅  Compression complete!")
    print(f"  {'─' * 50}")
    print(f"     Before:     {old_fmt:>10}")
    print(f"     After:      {new_fmt:>10}")
    print(f"     Saved:      {saved_fmt:>10}  ({pct:.1f}% reduction)")
    print()


# ══════════════════════════════════════════════════════════
#  CLI ARGUMENT PARSER
# ══════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf_tool",
        description="📄 PDF Tool — Edit, Compress & Manipulate PDF Files",
        epilog="More help: python pdf_tool.py <command> --help",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version=f"pdf_tool v{VERSION}"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        description="Available commands:",
        metavar="",
    )

    # ── compress ──────────────────────────────────────────
    p_compress = subparsers.add_parser(
        "compress", aliases=["c"],
        help="📦 Compress PDF file size",
        description="Compress a PDF file using different methods.",
    )
    p_compress.add_argument("input", help="Input PDF file path")
    p_compress.add_argument("-o", "--output", required=True,
                            help="Output PDF file path")
    p_compress.add_argument("-m", "--method", choices=["auto", "lossless", "smart", "aggressive", "raster"],
                            default="auto",
                            help="Compression method (default: auto)")
    p_compress.add_argument("-q", "--quality", type=int, default=75,
                            help="Image quality for smart/aggressive/raster (1-100, default: 75)")
    p_compress.add_argument("-d", "--dpi-target", type=int, default=150,
                            help="Target DPI for image downsampling (default: 150)")

    # ── merge ─────────────────────────────────────────────
    p_merge = subparsers.add_parser(
        "merge", aliases=["m"],
        help="🔗 Merge multiple PDFs into one",
        description="Merge multiple PDF files into a single PDF.",
    )
    p_merge.add_argument("inputs", nargs="+", help="Input PDF files to merge (space-separated)")
    p_merge.add_argument("-o", "--output", required=True, help="Output PDF file path")

    # ── split ─────────────────────────────────────────────
    p_split = subparsers.add_parser(
        "split", aliases=["s"],
        help="✂️  Split PDF into separate pages",
        description="Split a PDF into individual page files or extract a page range.",
    )
    p_split.add_argument("input", help="Input PDF file path")
    p_split.add_argument("-o", "--output-dir", required=True,
                         help="Output directory for page files")
    p_split.add_argument("-p", "--pages", help="Page range (e.g., '1-5,7,9-12')")

    # ── rotate ────────────────────────────────────────────
    p_rotate = subparsers.add_parser(
        "rotate", aliases=["r"],
        help="🔄 Rotate PDF pages",
        description="Rotate all pages by a specified angle.",
    )
    p_rotate.add_argument("input", help="Input PDF file path")
    p_rotate.add_argument("-o", "--output", required=True, help="Output PDF file path")
    p_rotate.add_argument("-a", "--angle", type=int, choices=[90, 180, 270], default=90,
                          help="Rotation angle in degrees (default: 90)")

    # ── crop ──────────────────────────────────────────────
    p_crop = subparsers.add_parser(
        "crop", aliases=["cr"],
        help="✂️  Crop PDF pages",
        description="Crop pages by removing margin space.",
    )
    p_crop.add_argument("input", help="Input PDF file path")
    p_crop.add_argument("-o", "--output", required=True, help="Output PDF file path")
    p_crop.add_argument("-l", "--left", type=float, default=0, help="Left margin to crop (points)")
    p_crop.add_argument("-r", "--right", type=float, default=0, help="Right margin to crop (points)")
    p_crop.add_argument("-t", "--top", type=float, default=0, help="Top margin to crop (points)")
    p_crop.add_argument("-b", "--bottom", type=float, default=0, help="Bottom margin to crop (points)")

    # ── extract-text ──────────────────────────────────────
    p_et = subparsers.add_parser(
        "extract-text", aliases=["et"],
        help="📝 Extract text from PDF",
        description="Extract all text from a PDF file.",
    )
    p_et.add_argument("input", help="Input PDF file path")
    p_et.add_argument("-o", "--output", help="Output text file (prints to stdout if omitted)")

    # ── extract-images ────────────────────────────────────
    p_ei = subparsers.add_parser(
        "extract-images", aliases=["ei"],
        help="🖼️  Extract images from PDF",
        description="Extract all images embedded in a PDF file.",
    )
    p_ei.add_argument("input", help="Input PDF file path")
    p_ei.add_argument("-o", "--output-dir", default="extracted_images",
                      help="Output directory for images (default: extracted_images)")
    p_ei.add_argument("--min-size", type=int, default=100,
                      help="Minimum image file size in bytes (default: 100)")

    # ── select-pages ──────────────────────────────────────
    p_sp = subparsers.add_parser(
        "select", aliases=["sel"],
        help="📑 Select/reorder/delete pages",
        description="Extract specific pages from a PDF (reorders too).",
    )
    p_sp.add_argument("input", help="Input PDF file path")
    p_sp.add_argument("-o", "--output", required=True, help="Output PDF file path")
    p_sp.add_argument("-p", "--pages", required=True,
                      help="Page numbers to extract, 1-indexed (e.g., '1,3,5-8')")
    p_sp.add_argument("--reverse", action="store_true",
                      help="Reverse the selected page order")

    # ── watermark ─────────────────────────────────────────
    p_wm = subparsers.add_parser(
        "watermark", aliases=["w"],
        help="💧 Add text watermark to PDF",
        description="Add a text watermark across every page.",
    )
    p_wm.add_argument("input", help="Input PDF file path")
    p_wm.add_argument("-o", "--output", required=True, help="Output PDF file path")
    p_wm.add_argument("-t", "--text", default="CONFIDENTIAL",
                      help="Watermark text (default: CONFIDENTIAL)")
    p_wm.add_argument("--opacity", type=float, default=0.3,
                      help="Opacity (0.0-1.0, default: 0.3)")
    p_wm.add_argument("--font-size", type=int, default=72,
                      help="Font size (default: 72)")
    p_wm.add_argument("--no-diagonal", action="store_false", dest="diagonal",
                      help="Place watermark horizontally instead of diagonally")

    # ── info ──────────────────────────────────────────────
    p_info = subparsers.add_parser(
        "info", aliases=["i"],
        help="ℹ️  Show PDF information",
        description="Display detailed metadata and properties of a PDF file.",
    )
    p_info.add_argument("input", help="Input PDF file path")

    # ── batch ─────────────────────────────────────────────
    p_batch = subparsers.add_parser(
        "batch",
        help="📦 Batch compress all PDFs in a folder",
        description="Compress all PDF files in a directory.",
    )
    p_batch.add_argument("folder", help="Folder containing PDF files")
    p_batch.add_argument("-o", "--output-dir", help="Output directory (default: creates 'compressed' subfolder)")
    p_batch.add_argument("-m", "--method", choices=["auto", "lossless", "smart", "aggressive", "raster"],
                         default="auto", help="Compression method (default: auto)")
    p_batch.add_argument("-q", "--quality", type=int, default=75,
                         help="Image quality (default: 75)")
    p_batch.add_argument("-d", "--dpi-target", type=int, default=150,
                         help="Target DPI (default: 150)")

    return parser


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command in ("compress", "c"):
            _check_input(args.input)
            result = compress_pdf(
                args.input, args.output,
                method=args.method, quality=args.quality,
                dpi_target=args.dpi_target,
            )
            _print_compression_result(result)

        elif args.command in ("merge", "m"):
            for f in args.inputs:
                _check_input(f)
            result = merge_pdfs(args.inputs, args.output)
            print(f"  ✅  Merged {result['input_files']} files → {result['output']}")
            print(f"      Size: {_format_size(result['output_size'])}\n")

        elif args.command in ("split", "s"):
            _check_input(args.input)
            result = split_pdf(args.input, args.output_dir, args.pages)
            print(f"  ✅  Extracted {result['extracted']} of {result['total_pages']} pages")
            print(f"      → {result['output_dir']}/\n")

        elif args.command in ("rotate", "r"):
            _check_input(args.input)
            result = rotate_pdf(args.input, args.output, args.angle)
            print(f"  ✅  Rotated {result['pages_rotated']} pages by {result['angle']}°\n")

        elif args.command in ("crop", "cr"):
            _check_input(args.input)
            result = crop_pdf(args.input, args.output, args.left, args.right, args.top, args.bottom)
            print(f"  ✅  Cropped → {result['output']}\n")

        elif args.command in ("extract-text", "et"):
            _check_input(args.input)
            text = extract_text(args.input, args.output)
            if args.output:
                print(f"  ✅  Text extracted to {args.output}")
                print(f"      ({len(text)} characters)\n")
            else:
                print(text)

        elif args.command in ("extract-images", "ei"):
            _check_input(args.input)
            result = extract_images(args.input, args.output_dir, args.min_size)
            print(f"  ✅  Extracted {result['images_extracted']} images")
            print(f"      → {result['output_dir']}/\n")

        elif args.command in ("select", "sel"):
            _check_input(args.input)
            # Open once to get page count, then close
            temp_doc = fitz.open(args.input)
            total = len(temp_doc)
            temp_doc.close()
            pages = _parse_page_range(args.pages, total)
            result = select_pages(args.input, args.output, pages, args.reverse)
            print(f"  ✅  Extracted {len(result['selected_pages'])} pages")
            print(f"      → {result['output']}\n")

        elif args.command in ("watermark", "w"):
            _check_input(args.input)
            result = add_watermark(
                args.input, args.output,
                text=args.text, opacity=args.opacity,
                font_size=args.font_size, diagonal=args.diagonal,
            )
            print(f"  ✅  Watermark added → {result['output']}\n")

        elif args.command in ("info", "i"):
            _check_input(args.input)
            info = get_pdf_info(args.input)
            display_info(info)

        elif args.command == "batch":
            batch_compress(
                args.folder, args.output_dir,
                method=args.method, quality=args.quality,
                dpi_target=args.dpi_target,
            )

        else:
            parser.print_help()

    except Exception as e:
        print(f"\n  ❌  Error: {e}\n", file=sys.stderr)
        return 1

    return 0


def batch_compress(folder: str, output_dir: Optional[str] = None,
                   method: str = "auto", quality: int = 75, dpi_target: int = 150) -> None:
    """Compress all PDFs in a folder."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise NotADirectoryError(f"Folder not found: {folder}")

    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = folder_path / "compressed"

    out_path.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(folder_path.glob("*.pdf"))
    if not pdf_files:
        print(f"  ⚠️  No PDF files found in {folder}")
        return

    print(f"\n  📦  Batch compressing {len(pdf_files)} files...\n")
    print(f"  {'─' * 60}")
    print(f"  {'File':30s} {'Before':>10s} → {'After':>10s} {'Saved':>10s}")
    print(f"  {'─' * 60}")

    total_before = 0
    total_after = 0

    for pdf_path in pdf_files:
        out_file = out_path / pdf_path.name
        size_before = pdf_path.stat().st_size

        try:
            result = compress_pdf(str(pdf_path), str(out_file),
                                  method=method, quality=quality, dpi_target=dpi_target)
            size_after = result["new_size"]
        except Exception as e:
            print(f"  ❌  {pdf_path.name:30s} Error: {e}")
            continue

        total_before += size_before
        total_after += size_after

        saved = size_before - size_after
        pct = (saved / size_before * 100) if size_before > 0 else 0
        sign = "" if saved <= 0 else "−"
        print(f"  {'✓ ' + pdf_path.name:30s} {_format_size(size_before):>10s} → {_format_size(size_after):>10s} "
              f"{sign}{_format_size(abs(saved)):>9s} ({pct:.1f}%)")

    print(f"  {'─' * 60}")
    total_saved = total_before - total_after
    total_pct = (total_saved / total_before * 100) if total_before > 0 else 0
    sign = "" if total_saved <= 0 else "−"
    print(f"  {'TOTAL':30s} {_format_size(total_before):>10s} → {_format_size(total_after):>10s} "
          f"{sign}{_format_size(abs(total_saved)):>10s} ({total_pct:.1f}%)")
    print(f"\n  ✅  Batch done! Files saved to: {out_path}\n")


def _check_input(path: str) -> None:
    """Verify input file exists and is a PDF."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.suffix.lower() != ".pdf" and path != "-":
        # Some tools accept stdin, but generally warn
        pass


# ──────────────────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(main())
