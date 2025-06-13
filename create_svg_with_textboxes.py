#!/usr/bin/env python3
"""
Generates an A4-sized SVG based on a text file with strings and a background that can
be provided as and image or page from a PDF.

Puts each text line on top of a white, semi-transparent rectangle.
Always uses external file references and copies images to the output directory to deal
with Inkscape compatibility issues.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import xml.sax.saxutils
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageFont


# Constants
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_WIDTH_PX = int(A4_WIDTH_MM * 3.779527559)  # Convert mm to pixels (96 DPI)
A4_HEIGHT_PX = int(A4_HEIGHT_MM * 3.779527559)
FONTS = [
    # Primary choice - Noto Sans CJK
    ("NotoSansCJK-Regular.ttc", "Noto Sans CJK JP Regular"),
    # Good Japanese font commonly available on macOS
    ("Hiragino Sans GB.ttc", "Hiragino Sans"),
    # Other fallbacks with decent CJK support
    ("NotoSans-Regular.ttf", "Noto Sans"),
    ("DejaVuSans.ttf", "DejaVu Sans"),
    ("LiberationSans-Regular.ttf", "Liberation Sans"),
]

FONT_SIZE = 16
RECTANGLE_COLOR = "#FFFFFF"
RECTANGLE_OPACITY = 0.9
TEXT_COLOR = "#000000"
TEXT_PADDING = 5
LINE_SPACING = 27


def load_font_with_fallbacks() -> Tuple[ImageFont.FreeTypeFont, str]:
    """Load font with graceful fallbacks for better compatibility."""
    print("\n=== Loading Font ===")
    primary_font_found = False

    # Try each font in the fallback chain
    for font_file, svg_name in FONTS:
        # Search in common font directories
        search_paths = [
            "/usr/share/fonts",
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            "/Library/Fonts",
            "/opt/homebrew/share/fonts",
            "/usr/local/share/fonts",
        ]

        for base_path in search_paths:
            if not os.path.exists(base_path):
                continue

            # Search recursively in font directories
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower() == font_file.lower():
                        full_path = os.path.join(root, file)
                        try:
                            font = ImageFont.truetype(full_path, FONT_SIZE)

                            if font_file == FONTS[0][0]:
                                primary_font_found = True
                                print(f"Using primary font: {svg_name} ({full_path})")
                            else:
                                print(
                                    f"Warning: Primary font 'Noto Sans CJK JP Regular' not found."
                                )
                                print(f"Using fallback font: {svg_name} ({full_path})")
                                print("For best Japanese text rendering, install with:")
                                print(
                                    "  Ubuntu/Debian: sudo apt install fonts-noto-cjk"
                                )
                                print("  macOS: brew install font-noto-sans-cjk")

                            return font, svg_name
                        except OSError:
                            continue

    # Ultimate fallback to system default
    if not primary_font_found:
        print("Warning: Primary font 'Noto Sans CJK JP Regular' not found.")
        print("Warning: No suitable fallback fonts found. Using system default.")
        print("Japanese characters may not display correctly.")

    return ImageFont.load_default(), "sans-serif"


def validate_files(text_file: str, background_file: Optional[str]) -> None:
    """Validate that input files exist and are of correct types."""
    if not os.path.exists(text_file):
        raise FileNotFoundError(f"Text file not found: {text_file}")

    if background_file:
        if not os.path.exists(background_file):
            raise FileNotFoundError(f"Background file not found: {background_file}")

        ext = Path(background_file).suffix.lower()
        if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
            raise ValueError(f"Unsupported background file type: {ext}")


def process_pdf_background(
    pdf_path: str,
    page_number: int,
    output_dir: str = ".",
    output_file: str = "output.svg",
) -> str:
    """Extract a page from PDF and save as external PNG file."""
    print("\n=== Pre-processing PDF ===")
    try:
        doc = fitz.open(pdf_path)
        if page_number >= len(doc):
            raise ValueError(
                f"Page {page_number} does not exist in PDF (has {len(doc)} pages)"
            )

        page = doc.load_page(page_number)
        # Render at high resolution (300 DPI)
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)

        # Save as external PNG file in the same directory as SVG
        pdf_name = Path(pdf_path).stem
        output_filename = f"{pdf_name}_page_{page_number}.png"
        output_path = Path(output_dir) / output_filename
        pix.save(str(output_path))
        doc.close()
        print(f"Extracted PDF page to: {output_path}")

        # Return just the filename for relative reference
        return output_filename

    except Exception as e:
        raise RuntimeError(f"Error processing PDF: {e}")


def normalize_image_orientation(image_path: str) -> str:
    """
    Normalize image orientation using ImageMagick's auto-orient feature.
    Creates a temporary file with normalized orientation.

    Args:
        image_path: Path to the input image

    Returns:
        Path to the normalized image (temporary file)

    Raises:
        RuntimeError: If ImageMagick is not available or command fails
    """
    print("\n=== Normalizing Image Orientation ===")
    # Check if ImageMagick is available
    try:
        result = subprocess.run(
            ["convert", "-version"], capture_output=True, text=True, check=True
        )
        print(f"Using ImageMagick: {result.stdout.split()[0:3]}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try the newer 'magick' command
        try:
            result = subprocess.run(
                ["magick", "-version"], capture_output=True, text=True, check=True
            )
            print(f"Using ImageMagick: {result.stdout.split()[0:3]}")
            convert_cmd = "magick"
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "ImageMagick not found. Please install ImageMagick to handle EXIF orientation."
            )
    else:
        convert_cmd = "convert"

    # Create temporary file for normalized image
    temp_file = tempfile.NamedTemporaryFile(
        suffix=Path(image_path).suffix, delete=False
    )
    temp_path = temp_file.name
    temp_file.close()

    try:
        # Run auto-orient command
        cmd = [convert_cmd, image_path, "-auto-orient", temp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        print(f"Normalized image orientation: {image_path} -> {temp_path}")
        return temp_path

    except subprocess.CalledProcessError as e:
        # Clean up temp file on error
        os.unlink(temp_path)
        raise RuntimeError(f"Failed to normalize image orientation: {e.stderr}")


def process_image_background(
    image_path: str, output_file: str = "output.svg", normalize_orientation: bool = True
) -> str:
    """Process image and copy to SVG directory for external reference."""

    print("\n=== Pre-processing Image ===")
    print(f"Processing image: {image_path}")

    # Normalize orientation if requested
    working_image_path = image_path
    temp_file_to_cleanup = None

    if normalize_orientation:
        try:
            working_image_path = normalize_image_orientation(image_path)
            temp_file_to_cleanup = working_image_path
            print(f"Image orientation normalized")
        except RuntimeError as e:
            print(f"Warning: Could not normalize orientation: {e}")
            print("Proceeding with original image...")
            working_image_path = image_path

    try:
        # Copy image to SVG directory and use filename only
        result = copy_image_to_svg_dir(working_image_path, output_file)
        return result

    finally:
        # Clean up temporary file if created
        if temp_file_to_cleanup and temp_file_to_cleanup != image_path:
            try:
                os.unlink(temp_file_to_cleanup)
                print(f"Cleaned up temporary file: {temp_file_to_cleanup}")
            except OSError:
                pass  # File might already be deleted


def calculate_text_dimensions(
    text: str, font: ImageFont.FreeTypeFont
) -> Tuple[int, int]:
    """Calculate the bounding box dimensions of text using PIL."""
    bbox = font.getbbox(text)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


def create_background_element(background_data: str) -> str:
    """Create SVG background image element using external file reference."""
    # Use external file reference with proper escaping and Inkscape compatibility
    escaped_path = xml.sax.saxutils.escape(background_data)

    # For better Inkscape compatibility, use both href and xlink:href
    # and ensure proper namespace declaration
    return f"""<image x="0" y="0" width="{A4_WIDTH_PX}" height="{A4_HEIGHT_PX}" 
           href="{escaped_path}" 
           xlink:href="{escaped_path}"
           preserveAspectRatio="xMidYMid meet"/>"""


def create_text_line_elements(
    text: str,
    y_position: int,
    font: ImageFont.FreeTypeFont,
    font_name: str = FONTS[0][1],
) -> str:
    """Create SVG elements for a single line of text with its background rectangle."""
    if not text.strip():  # Handle empty lines
        return ""

    text_width, text_height = calculate_text_dimensions(text, font)

    # Rectangle dimensions with padding
    rect_width = text_width + (TEXT_PADDING * 2)
    rect_height = text_height + (TEXT_PADDING * 2)

    # Position rectangle at left margin
    rect_x = 20
    rect_y = y_position - TEXT_PADDING

    # Position text properly aligned with rectangle
    # Use the rectangle's center for vertical alignment
    text_x = rect_x + TEXT_PADDING
    text_y = rect_y + (rect_height / 2)  # Center vertically in rectangle

    return f"""<g>
    <rect x="{rect_x}" y="{rect_y}" width="{rect_width}" height="{rect_height}" 
          fill="{RECTANGLE_COLOR}" stroke="none" opacity="{RECTANGLE_OPACITY}"/>
    <text x="{text_x}" y="{text_y}" font-family="{font_name}" font-size="{FONT_SIZE}" 
          fill="{TEXT_COLOR}" dominant-baseline="central" text-anchor="start">{xml.sax.saxutils.escape(text)}</text>
</g>"""


def generate_svg(text_lines: list, background_element: str = "") -> str:
    """Generate the complete SVG document with external image support."""
    # Load font for text dimension calculations with fallbacks
    try:
        font, font_name = load_font_with_fallbacks()
    except Exception as e:
        raise RuntimeError(f"Could not load any font: {e}")

    # SVG header with proper namespace declarations for external images
    svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" 
     viewBox="0 0 {A4_WIDTH_PX} {A4_HEIGHT_PX}" 
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">
"""

    # Add background if provided
    if background_element:
        svg_content += f"  {background_element}\n"

    # Add text lines
    y_position = 40  # Start position from top
    for line in text_lines:
        line_elements = create_text_line_elements(
            line.rstrip("\n"), y_position, font, font_name
        )
        if line_elements:
            svg_content += f"  {line_elements}\n"
        y_position += LINE_SPACING

    # Close SVG
    svg_content += "</svg>"

    return svg_content


def copy_image_to_svg_dir(image_path: str, output_file: str) -> str:
    """Copy image file to the same directory as the SVG for better compatibility."""
    import shutil

    output_dir = Path(output_file).parent
    image_name = Path(image_path).name
    dest_path = output_dir / image_name

    # Only copy if it's not already in the same directory
    if Path(image_path).resolve() != dest_path.resolve():
        shutil.copy2(image_path, dest_path)
        print(f"Copied image to SVG directory: {dest_path}")

    return image_name  # Return just the filename for relative reference


def main():
    parser = argparse.ArgumentParser(
        description="Generate A4-sized SVG from text file with external image references"
    )
    parser.add_argument("--text-file", required=True, help="Path to input text file")
    parser.add_argument("--background-file", help="Path to background image or PDF")
    parser.add_argument(
        "--page-number",
        type=int,
        default=0,
        help="Page number for PDF background (0-indexed)",
    )
    parser.add_argument(
        "--output-file", default="output.svg", help="Output SVG filename"
    )
    parser.add_argument(
        "--no-normalize-orientation",
        action="store_true",
        help="Skip automatic image orientation normalization (EXIF auto-orient)",
    )

    args = parser.parse_args()

    try:
        # Validate input files
        validate_files(args.text_file, args.background_file)

        # Read text file
        with open(args.text_file, "r", encoding="utf-8") as f:
            text_lines = f.readlines()

        # Process background if provided
        background_element = ""
        if args.background_file:
            output_dir = Path(args.output_file).parent
            ext = Path(args.background_file).suffix.lower()
            if ext == ".pdf":
                background_data = process_pdf_background(
                    args.background_file, args.page_number, output_dir, args.output_file
                )
                background_element = create_background_element(background_data)
            else:
                normalize_orientation = not args.no_normalize_orientation
                background_data = process_image_background(
                    args.background_file, args.output_file, normalize_orientation
                )
                background_element = create_background_element(background_data)

        # Generate SVG
        svg_content = generate_svg(text_lines, background_element)

        # Write output
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(svg_content)

        print("\n=== Generating SVG ===")
        print(f"SVG generated successfully: {args.output_file}")
        if args.background_file:
            print(
                "Note: SVG uses external image references with Inkscape compatibility features."
            )
            print(
                "Images have been copied to the SVG directory for better portability."
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
