"""
Reset Vector Database and Reprocess All Documents

This script will:
1. Delete the existing ChromaDB vector database
2. Delete processed chunks and reports
3. Optionally convert PDFs from Legislation folder to text files
4. Reprocess all documents and rebuild the vector store
"""

import os
import shutil
import sys
from pathlib import Path

def delete_vector_db():
    """Delete the ChromaDB vector database"""
    db_path = "chroma_db"
    if os.path.exists(db_path):
        print(f"🗑️  Deleting vector database: {db_path}")
        shutil.rmtree(db_path)
        print("✅ Vector database deleted")
    else:
        print("ℹ️  No vector database found to delete")

def delete_processed_files():
    """Delete processed chunks and reports"""
    files_to_delete = [
        "processed_chunks.json",
        "processing_report.json"
    ]
    
    for file in files_to_delete:
        if os.path.exists(file):
            print(f"🗑️  Deleting: {file}")
            os.remove(file)
            print(f"✅ {file} deleted")
        else:
            print(f"ℹ️  {file} not found")

def convert_pdfs_to_text():
    """Convert PDFs from Legislation folder to text files using docling"""
    legislation_folder = Path("Legislation")
    output_folder = Path("ocr/output")
    
    if not legislation_folder.exists():
        print("⚠️  Legislation folder not found")
        return False
    
    pdf_files = list(legislation_folder.glob("*.pdf"))
    if not pdf_files:
        print("ℹ️  No PDF files found in Legislation folder")
        return False
    
    print(f"\n📄 Found {len(pdf_files)} PDF files in Legislation folder")
    print("Converting PDFs to text using docling OCR...")
    
    # Check if docling OCR script exists
    ocr_script = Path("ocr/docling_ocr.py")
    if not ocr_script.exists():
        print("❌ OCR script not found at ocr/docling_ocr.py")
        print("   You'll need to manually convert PDFs or use another tool")
        return False
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Process each PDF
    for pdf_file in pdf_files:
        print(f"\n📝 Converting: {pdf_file.name}")
        
        # Copy PDF to ocr/input_pdfs/
        input_pdfs = Path("ocr/input_pdfs")
        input_pdfs.mkdir(parents=True, exist_ok=True)
        
        dest_pdf = input_pdfs / pdf_file.name
        shutil.copy2(pdf_file, dest_pdf)
        print(f"   Copied to: {dest_pdf}")
    
    print(f"\n✅ {len(pdf_files)} PDFs copied to ocr/input_pdfs/")
    print("⏱️  Run the OCR process: cd ocr && python docling_ocr.py")
    
    return True

def reprocess_documents():
    """Run the document processing script"""
    print("\n🔄 Starting document reprocessing...")
    print("=" * 60)
    
    # Check if process_all_documents.py exists
    if not os.path.exists("process_all_documents.py"):
        print("❌ process_all_documents.py not found")
        return False
    
    # Run the processing script
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "process_all_documents.py"],
            check=True,
            capture_output=False
        )
        print("\n✅ Document reprocessing completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during reprocessing: {e}")
        return False

def main():
    print("=" * 60)
    print("🔄 RESET AND REPROCESS VECTOR DATABASE")
    print("=" * 60)
    
    # Ask for confirmation
    print("\n⚠️  WARNING: This will delete your existing vector database!")
    print("   All processed chunks and embeddings will be removed.")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return
    
    # Step 1: Delete vector database
    print("\n📍 Step 1: Deleting Vector Database")
    print("-" * 60)
    delete_vector_db()
    
    # Step 2: Delete processed files
    print("\n📍 Step 2: Deleting Processed Files")
    print("-" * 60)
    delete_processed_files()
    
    # Step 3: Ask about PDF conversion
    print("\n📍 Step 3: PDF Conversion (Optional)")
    print("-" * 60)
    
    legislation_folder = Path("Legislation")
    if legislation_folder.exists():
        pdf_count = len(list(legislation_folder.glob("*.pdf")))
        if pdf_count > 0:
            print(f"Found {pdf_count} PDF files in Legislation folder")
            response = input("Do you want to convert PDFs to text? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                convert_pdfs_to_text()
                print("\n⏸️  PAUSED: Please run OCR processing first:")
                print("   1. cd ocr")
                print("   2. python docling_ocr.py")
                print("   3. Move output text files to project root")
                print("   4. Run this script again to complete reprocessing")
                return
    
    # Step 4: Reprocess documents
    print("\n📍 Step 4: Reprocessing Documents")
    print("-" * 60)
    
    # Check for text files
    txt_files = list(Path(".").glob("*.txt")) + list(Path("ocr/output").glob("*.txt"))
    if not txt_files:
        print("⚠️  No .txt files found to process!")
        print("   Make sure you have text files in:")
        print("   - Project root folder")
        print("   - ocr/output folder")
        return
    
    print(f"Found {len(txt_files)} text files to process")
    response = input("\nProceed with reprocessing? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        success = reprocess_documents()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ RESET AND REPROCESS COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\n📊 Next Steps:")
            print("   1. Your vector database has been rebuilt")
            print("   2. Check processing_report.json for details")
            print("   3. Run: streamlit run main.py")
            print("   4. Test with some queries from the search tips")
        else:
            print("\n❌ Reprocessing failed. Check the error messages above.")
    else:
        print("❌ Reprocessing cancelled")

if __name__ == "__main__":
    main()


