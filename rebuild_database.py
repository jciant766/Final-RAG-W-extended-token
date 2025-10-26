"""
ONE SCRIPT TO RULE THEM ALL
Rebuild vector database with or without PDF conversion
"""

import os
import sys
import shutil
import time
import subprocess
from pathlib import Path

def delete_vector_db():
    """Delete the vector database"""
    db_path = "chroma_db"
    
    if not os.path.exists(db_path):
        print("ℹ️  No vector database to delete")
        return True
    
    print("🗑️  Deleting vector database...")
    
    for attempt in range(3):
        try:
            shutil.rmtree(db_path)
            print("✅ Vector database deleted")
            return True
        except PermissionError:
            if attempt < 2:
                print(f"⚠️  Locked, retrying...")
                time.sleep(2)
            else:
                print("\n❌ ERROR: Database is locked!")
                print("   Close Streamlit (Ctrl+C) and run again")
                return False
    return False

def convert_pdfs():
    """Convert PDFs to text (optional)"""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        print("❌ Docling not installed")
        print("   Run: cd ocr && pip install -r requirements.txt && cd ..")
        return False
    
    legislation_folder = Path("Legislation")
    output_folder = Path("ocr/output")
    
    if not legislation_folder.exists():
        print("❌ Legislation folder not found")
        return False
    
    pdf_files = sorted(legislation_folder.glob("*.pdf"))
    if not pdf_files:
        print("ℹ️  No PDFs to convert")
        return True
    
    print(f"\n📄 Found {len(pdf_files)} PDFs")
    output_folder.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter()
    
    converted = 0
    for idx, pdf_file in enumerate(pdf_files, 1):
        output_path = output_folder / f"{pdf_file.stem}.txt"
        
        if output_path.exists():
            print(f"[{idx}/{len(pdf_files)}] ⏭️  {pdf_file.name}")
            continue
        
        try:
            print(f"[{idx}/{len(pdf_files)}] 📝 {pdf_file.name}...", end=" ")
            result = converter.convert(pdf_file)
            text = result.document.export_to_text()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print("✅")
            converted += 1
        except Exception as e:
            print(f"❌ {e}")
    
    print(f"✅ Converted {converted} PDFs")
    return True

def process_documents():
    """Process text files into chunks"""
    print("\n⏱️  Processing documents into chunks (3-5 minutes)...")
    print("-" * 70)
    
    try:
        subprocess.run([sys.executable, "process_all_documents.py"], check=True)
        print("\n✅ Documents processed")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    print("=" * 70)
    print("REBUILD VECTOR DATABASE")
    print("=" * 70)
    
    print("\nOptions:")
    print("  1. Quick rebuild (use existing text files) - 5-10 minutes")
    print("  2. Full rebuild with PDF conversion - 20-40 minutes")
    
    choice = input("\nChoose (1/2): ").strip()
    
    if choice not in ['1', '2']:
        print("❌ Invalid choice")
        return
    
    print("\n⚠️  Make sure Streamlit is closed!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Delete database
    if not delete_vector_db():
        return
    
    # Convert PDFs if option 2
    if choice == '2':
        print("\n📄 Converting PDFs...")
        if not convert_pdfs():
            return
    
    # Process documents
    if not process_documents():
        return
    
    # Done
    print("\n" + "=" * 70)
    print("✅ REBUILD COMPLETE!")
    print("=" * 70)
    print("\nNext: streamlit run main.py")
    print("(Embeddings will auto-generate on startup)")

if __name__ == "__main__":
    main()


