# SVG Generator Script

A Python script that generates A4-sized SVG graphics from text files. Each line of text is displayed on top of a pale yellow colored rectangle. The script supports using a page from a PDF or an image file as a background.

## Features

- Generates A4-sized (210mm x 297mm) SVG files
- Supports Japanese text with Noto Sans CJK font
- Each text line gets a pale yellow background rectangle
- Optional PDF or image backgrounds
- Self-contained SVG output with embedded images

## Installation

```bash
pipenv install
```

## Usage

### Basic usage (text only):
```bash
pipenv run python svg_generator.py --text-file your_text.txt
```

### With image background:
```bash
pipenv run python svg_generator.py --text-file your_text.txt --background-file image.png --output-file result.svg
```

### With PDF background (specific page):
```bash
pipenv run python svg_generator.py --text-file your_text.txt --background-file document.pdf --page-number 2 --output-file result.svg
```

## Command Line Arguments

- `--text-file` (required): Path to the input plain text file
- `--background-file` (optional): Path to background image (PNG, JPEG, etc.) or PDF file
- `--page-number` (optional): Page number for PDF background (0-indexed, default: 0)
- `--output-file` (optional): Output SVG filename (default: output.svg)

## Supported Background Formats

- Images: PNG, JPEG, GIF, BMP, TIFF
- PDF files (any page)

## Examples

The repository includes sample files:
- `sample_japanese_text.txt` - Japanese text sample
- `sample_text.txt` - English text sample

## Requirements

- Python 3.11+
- PyMuPDF (for PDF processing)
- Pillow (for image processing)
- Noto Sans CJK font (for Japanese text support) 