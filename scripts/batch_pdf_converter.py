#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import subprocess

def convert_with_pymupdf(pdf_path, output_path):
    """Convert PDF using PyMuPDF (fitz) - more reliable"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except ImportError:
        print("PyMuPDF not available, trying pdfplumber...")
        return convert_with_pdfplumber(pdf_path, output_path)
    except Exception as e:
        print(f"PyMuPDF error: {e}")
        return convert_with_pdfplumber(pdf_path, output_path)

def convert_with_pdfplumber(pdf_path, output_path):
    """Convert PDF using pdfplumber - fallback option"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except ImportError:
        print("pdfplumber not available, trying basic pdfminer...")
        return convert_with_pdfminer_basic(pdf_path, output_path)
    except Exception as e:
        print(f"pdfplumber error: {e}")
        return convert_with_pdfminer_basic(pdf_path, output_path)

def convert_with_pdfminer_basic(pdf_path, output_path):
    """Convert PDF using basic pdfminer - last resort"""
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"pdfminer error: {e}")
        return False

def main():
    input_dir = Path("ocr/input_pdfs")
    output_dir = Path("ocr/output")
    output_dir.mkdir(exist_ok=True)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files to convert...")
    
    converted_count = 0
    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}.txt"
        
        # Skip if already exists
        if output_file.exists():
            print(f"✓ {pdf_file.name} already converted")
            converted_count += 1
            continue
            
        print(f"Converting {pdf_file.name}...")
        
        if convert_with_pymupdf(pdf_file, output_file):
            converted_count += 1
            print(f"✓ Converted {pdf_file.name}")
        else:
            print(f"✗ Failed to convert {pdf_file.name}")
    
    print(f"\n✓ Successfully converted {converted_count}/{len(pdf_files)} files")

if __name__ == "__main__":
    main()

