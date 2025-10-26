"""
Convert PDF files from Legislation folder to text files
Uses docling for OCR processing
"""

import os
import sys
from pathlib import Path

def convert_all_pdfs():
    """Convert all PDFs from Legislation folder to text"""
    
    # Check if docling is available
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        print("❌ Docling is not installed!")
        print("\nTo install:")
        print("  1. cd ocr")
        print("  2. pip install -r requirements.txt")
        print("  3. cd ..")
        print("  4. Run this script again")
        return False
    
    legislation_folder = Path("Legislation")
    output_folder = Path("ocr/output")
    
    if not legislation_folder.exists():
        print(f"❌ Legislation folder not found: {legislation_folder}")
        return False
    
    # Get all PDF files
    pdf_files = sorted(legislation_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("ℹ️  No PDF files found in Legislation folder")
        return False
    
    print("=" * 70)
    print(f"📄 CONVERTING {len(pdf_files)} PDF FILES TO TEXT")
    print("=" * 70)
    
    # Create output folder
    output_folder.mkdir(parents=True, exist_ok=True)
    
    converter = DocumentConverter()
    
    converted = 0
    failed = 0
    skipped = 0
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        # Create output filename
        output_name = pdf_file.stem + ".txt"
        output_path = output_folder / output_name
        
        # Skip if already exists
        if output_path.exists():
            print(f"[{idx}/{len(pdf_files)}] ⏭️  SKIP: {pdf_file.name} (already exists)")
            skipped += 1
            continue
        
        try:
            print(f"\n[{idx}/{len(pdf_files)}] 📝 Converting: {pdf_file.name}")
            print(f"   Output: {output_path}")
            
            # Convert PDF to text
            result = converter.convert(pdf_file)
            text = result.document.export_to_text()
            
            # Save text file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Get file size
            size_kb = output_path.stat().st_size / 1024
            print(f"   ✅ SUCCESS: {size_kb:.1f} KB")
            converted += 1
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"✅ Converted: {converted}")
    print(f"⏭️  Skipped (already exist): {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Output folder: {output_folder.absolute()}")
    
    if converted > 0 or skipped > 0:
        print("\n✅ Text files are ready for processing!")
        return True
    else:
        print("\n⚠️  No files were converted")
        return False

if __name__ == "__main__":
    print("\n⚠️  NOTE: PDF conversion can take 5-30 seconds per file")
    print(f"   Estimated time: ~5-20 minutes for 43 PDFs\n")
    
    response = input("Proceed with conversion? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        success = convert_all_pdfs()
        
        if success:
            print("\n📍 NEXT STEPS:")
            print("   1. Close Streamlit if running")
            print("   2. Run: python delete_vector_db.py")
            print("   3. Run: python process_all_documents.py")
            print("   4. Run: streamlit run main.py")
    else:
        print("❌ Conversion cancelled")
