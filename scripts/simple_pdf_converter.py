#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from pdfminer.high_level import extract_text

def convert_pdf_to_text_simple(pdf_path, output_path):
    """Convert PDF to text using pdfminer (simpler, more reliable)"""
    try:
        text = extract_text(pdf_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Error converting {pdf_path}: {e}")
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
        print(f"Converting {pdf_file.name}...")
        
        if convert_pdf_to_text_simple(pdf_file, output_file):
            converted_count += 1
            print(f"✓ Converted {pdf_file.name}")
        else:
            print(f"✗ Failed to convert {pdf_file.name}")
    
    print(f"\n✓ Successfully converted {converted_count}/{len(pdf_files)} files")

if __name__ == "__main__":
    main()

