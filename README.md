# Hovercraft Full of Eels 🛸🐍📄🇯🇵

![](eels.png)

Python script to aid translation of scanned documents into Japanese.

Generates an A4-sized SVG in which it places

* text lines with white, semi-transparent background rectangles
* an image or page from a PDF as background

( ⚠ Code is almost exclusively written by claude-4-sonnet. )

## Usage

```bash
$ python eels.py \
    --txt ocr_ja.txt \
    --doc scan.jpg \
    --out eels.svg
```

## Workflow

1. Get original document text content
    * Example: `$ ocrmypdf -l eng+deu --sidecar ocr.txt scan.jpg ocr.pdf`
2. Translate text
    * `ocr.txt` -> `ocr_ja.txt`
3. Generate SVG
    * `$ python eels.py --txt ocr_ja.txt --doc scan.jpg --out eels.svg`
4. Position/scale/adjust textboxes
    * `$ inkscape eels.svg`
    * ...
5. Save as PDF

## Dependencies

### System

ImageMagick

- **Ubuntu/Debian**: `sudo apt install imagemagick`
- **macOS**: `brew install imagemagick`

Font: Noto Sans CJK

- **Ubuntu/Debian**: `sudo apt install fonts-noto-cjk`
- **macOS**: `brew install font-noto-sans-cjk`

### Python

- **PyMuPDF** (`fitz`) - PDF processing
- **Pillow** (`PIL`) - Image processing  
