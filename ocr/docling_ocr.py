import argparse
import os
import sys
import tempfile
import requests
from urllib.parse import urlparse
from pathlib import Path
from tqdm import tqdm

# Docling imports (assuming the package provides a converter API)
try:
    from docling.document_converter import DocumentConverter
except Exception:
    DocumentConverter = None


def download_file(url: str, dest_path: Path) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        with open(dest_path, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    return dest_path


def infer_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path) or 'document.pdf'
    if not os.path.splitext(name)[1]:
        name += '.pdf'
    return name


def convert_pdf_to_text(input_pdf: Path, output_txt: Path) -> None:
    if DocumentConverter is None:
        raise RuntimeError("Docling is not installed or import failed. Install from ocr/requirements.txt")
    converter = DocumentConverter()
    result = converter.convert(input_pdf)
    
    # Try to export with page markers if Docling supports per-page export
    try:
        # Check if result has page-level access
        if hasattr(result.document, 'pages') and result.document.pages:
            # Build text with page markers
            text_parts = []
            for page_num, page in enumerate(result.document.pages, start=1):
                text_parts.append(f"--- PAGE {page_num} ---\n")
                page_text = page.export_to_text() if hasattr(page, 'export_to_text') else str(page)
                text_parts.append(page_text)
                text_parts.append("\n\n")
            text = ''.join(text_parts)
        else:
            # Fallback: use standard export without page markers
            text = result.document.export_to_text()
            print("  ⚠️  Warning: Could not detect pages, exporting without page markers")
    except Exception as e:
        # Fallback to standard export
        text = result.document.export_to_text()
        print(f"  ⚠️  Warning: Page marker insertion failed ({e}), exporting without page markers")
    
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(text)


def is_url(s: str) -> bool:
    return s.startswith('http://') or s.startswith('https://') or s.startswith('file://')


def main():
    parser = argparse.ArgumentParser(description="Standalone Docling OCR to TXT from URLs")
    parser.add_argument('inputs', nargs='+', help='One or more URLs or local PDF file paths')
    parser.add_argument('--out', default='ocr/output', help='Output directory for .txt files')
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for src in args.inputs:
        try:
            if is_url(src):
                filename = infer_filename_from_url(src)
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_pdf = Path(tmpdir) / filename
                    print(f"Downloading {src} -> {tmp_pdf}")
                    download_file(src, tmp_pdf)
                    out_txt = out_dir / (Path(filename).stem + '.txt')
                    print(f"Converting {tmp_pdf} -> {out_txt}")
                    convert_pdf_to_text(tmp_pdf, out_txt)
                    print(f"Saved: {out_txt}")
            else:
                pdf_path = Path(src)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"File not found: {pdf_path}")
                out_txt = out_dir / (pdf_path.stem + '.txt')
                print(f"Converting {pdf_path} -> {out_txt}")
                convert_pdf_to_text(pdf_path, out_txt)
                print(f"Saved: {out_txt}")
        except Exception as e:
            print(f"Error processing {url}: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()


