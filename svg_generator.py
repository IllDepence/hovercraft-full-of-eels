#!/usr/bin/env python3
"""
SVG Generator Script

Generates an A4-sized SVG graphic from a text file. Each line of text is displayed
on top of a pale yellow colored rectangle. Supports using a page from a PDF or an 
image file as a background for the entire graphic.
"""

import argparse
import base64
import os
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
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_SIZE = 16
RECTANGLE_COLOR = "#FFFACD"  # Pale yellow
TEXT_COLOR = "#000000"  # Black
TEXT_PADDING = 5
LINE_SPACING = 25


def validate_files(text_file: str, background_file: Optional[str]) -> None:
    """Validate that input files exist and are of correct types."""
    if not os.path.exists(text_file):
        raise FileNotFoundError(f"Text file not found: {text_file}")
    
    if background_file:
        if not os.path.exists(background_file):
            raise FileNotFoundError(f"Background file not found: {background_file}")
        
        ext = Path(background_file).suffix.lower()
        if ext not in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            raise ValueError(f"Unsupported background file type: {ext}")


def process_pdf_background(pdf_path: str, page_number: int, use_external: bool = False, output_dir: str = ".", output_file: str = "output.svg") -> str:
    """Extract a page from PDF and convert to base64 encoded PNG or save as external file."""
    try:
        doc = fitz.open(pdf_path)
        if page_number >= len(doc):
            raise ValueError(f"Page {page_number} does not exist in PDF (has {len(doc)} pages)")
        
        page = doc.load_page(page_number)
        # Render at high resolution (300 DPI)
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        
        if use_external:
            # Save as external PNG file in the same directory as SVG
            pdf_name = Path(pdf_path).stem
            output_filename = f"{pdf_name}_page_{page_number}.png"
            output_path = Path(output_dir) / output_filename
            pix.save(str(output_path))
            doc.close()
            print(f"Extracted PDF page to: {output_path}")
            
            # Return just the filename for relative reference
            return output_filename
        else:
            # Convert to base64
            img_data = pix.tobytes("png")
            doc.close()
            return base64.b64encode(img_data).decode('utf-8')
    
    except Exception as e:
        raise RuntimeError(f"Error processing PDF: {e}")


def process_image_background(image_path: str, use_external: bool = False, output_file: str = "output.svg", copy_to_svg_dir: bool = False) -> str:
    """Convert image to base64 encoded format or return path for external reference."""

    print(f"Processing image: {image_path}")

    if use_external:
        if copy_to_svg_dir:
            # Copy image to SVG directory and use filename only
            return copy_image_to_svg_dir(image_path, output_file)
        else:
            # Calculate relative path from output SVG to image file
            output_dir = Path(output_file).parent.resolve()
            image_path_abs = Path(image_path).resolve()
            
            try:
                # Try to create a relative path
                relative_path = os.path.relpath(image_path_abs, output_dir)
                print(f"Using relative path: {relative_path}")
                return relative_path
            except ValueError:
                # If relative path fails (different drives on Windows), use absolute path
                print(f"Cannot create relative path, using absolute: {image_path_abs}")
                return str(image_path_abs)

    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            import io
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return base64.b64encode(img_bytes.read()).decode('utf-8')
    
    except Exception as e:
        raise RuntimeError(f"Error processing image: {e}")


def calculate_text_dimensions(text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """Calculate the bounding box dimensions of text using PIL."""
    bbox = font.getbbox(text)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


def create_background_element(background_data: str, is_pdf: bool, use_external: bool = False) -> str:
    """Create SVG background image element."""
    if use_external:
        # Use external file reference with proper escaping and Inkscape compatibility
        escaped_path = xml.sax.saxutils.escape(background_data)
        
        # For better Inkscape compatibility, use both href and xlink:href
        # and ensure proper namespace declaration
        return f'''<image x="0" y="0" width="{A4_WIDTH_PX}" height="{A4_HEIGHT_PX}" 
               href="{escaped_path}" 
               xlink:href="{escaped_path}"
               preserveAspectRatio="xMidYMid meet"/>'''
    else:
        # Use embedded base64 data
        mime_type = "image/png" if is_pdf else "image/png"  # We convert everything to PNG
        return f'''<image x="0" y="0" width="{A4_WIDTH_PX}" height="{A4_HEIGHT_PX}" 
               href="data:{mime_type};base64,{background_data}" 
               preserveAspectRatio="xMidYMid meet"/>'''


def create_text_line_elements(text: str, y_position: int, font: ImageFont.FreeTypeFont) -> str:
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
    
    # Position text centered in rectangle
    text_x = rect_x + TEXT_PADDING
    text_y = y_position + text_height - TEXT_PADDING  # Adjust for baseline
    
    return f'''<g>
    <rect x="{rect_x}" y="{rect_y}" width="{rect_width}" height="{rect_height}" 
          fill="{RECTANGLE_COLOR}" stroke="none"/>
    <text x="{text_x}" y="{text_y}" font-family="Noto Sans CJK JP" font-size="{FONT_SIZE}" 
          fill="{TEXT_COLOR}">{xml.sax.saxutils.escape(text)}</text>
</g>'''


def generate_svg(text_lines: list, background_element: str = "", use_external: bool = False) -> str:
    """Generate the complete SVG document."""
    # Load font for text dimension calculations
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        raise RuntimeError(f"Could not load font: {FONT_PATH}")
    
    # SVG header with proper namespace declarations for external images
    if use_external:
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" 
     viewBox="0 0 {A4_WIDTH_PX} {A4_HEIGHT_PX}" 
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">
'''
    else:
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" 
     viewBox="0 0 {A4_WIDTH_PX} {A4_HEIGHT_PX}" 
     xmlns="http://www.w3.org/2000/svg">
'''
    
    # Add background if provided
    if background_element:
        svg_content += f"  {background_element}\n"
    
    # Add text lines
    y_position = 40  # Start position from top
    for line in text_lines:
        line_elements = create_text_line_elements(line.rstrip('\n'), y_position, font)
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
    parser = argparse.ArgumentParser(description="Generate A4-sized SVG from text file")
    parser.add_argument("--text-file", required=True, help="Path to input text file")
    parser.add_argument("--background-file", help="Path to background image or PDF")
    parser.add_argument("--page-number", type=int, default=0, 
                       help="Page number for PDF background (0-indexed)")
    parser.add_argument("--output-file", default="output.svg", 
                       help="Output SVG filename")
    parser.add_argument("--external-images", action="store_true",
                       help="Use external file references instead of embedding images as base64")
    parser.add_argument("--copy-images", action="store_true",
                       help="Copy image files to SVG directory for better compatibility (use with --external-images)")
    
    args = parser.parse_args()
    
    try:
        # Validate input files
        validate_files(args.text_file, args.background_file)
        
        # Read text file
        with open(args.text_file, 'r', encoding='utf-8') as f:
            text_lines = f.readlines()
        
        # Process background if provided
        background_element = ""
        if args.background_file:
            output_dir = Path(args.output_file).parent
            ext = Path(args.background_file).suffix.lower()
            if ext == '.pdf':
                background_data = process_pdf_background(args.background_file, args.page_number, 
                                                       args.external_images, output_dir, args.output_file)
                background_element = create_background_element(background_data, is_pdf=True, 
                                                             use_external=args.external_images)
            else:
                background_data = process_image_background(args.background_file, args.external_images, 
                                                         args.output_file, args.copy_images)
                background_element = create_background_element(background_data, is_pdf=False, 
                                                             use_external=args.external_images)
        
        # Generate SVG
        svg_content = generate_svg(text_lines, background_element, args.external_images)
        
        # Write output
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"SVG generated successfully: {args.output_file}")
        if args.external_images and args.background_file:
            print("Note: SVG uses external image references with Inkscape compatibility features.")
            if args.copy_images:
                print("Images have been copied to the SVG directory for better portability.")
            else:
                print("Keep image files in the same relative location for proper display.")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 