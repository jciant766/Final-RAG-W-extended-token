#!/usr/bin/env python3
import os
import json
import subprocess
import sys
from pathlib import Path
from doc_processor import DocumentProcessor
from vector_store import VectorStore

def convert_pdfs_to_text():
    """Convert all PDFs in input_pdfs to text files in output folder"""
    input_dir = Path("ocr/input_pdfs")
    output_dir = Path("ocr/output")
    output_dir.mkdir(exist_ok=True)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in ocr/input_pdfs")
        return []
    
    print(f"Found {len(pdf_files)} PDF files to convert...")
    
    converted_files = []
    for pdf_file in pdf_files:
        print(f"Converting {pdf_file.name}...")
        try:
            # Use docling to convert PDF to text
            result = subprocess.run([
                sys.executable, "-c", 
                f"""
import sys
sys.path.append('ocr')
from docling_ocr import convert_pdf_to_text
convert_pdf_to_text('{pdf_file}', '{output_dir / pdf_file.stem}.txt')
"""
            ], capture_output=True, text=True, cwd=".")
            
            if result.returncode == 0:
                converted_files.append(output_dir / f"{pdf_file.stem}.txt")
                print(f"✓ Converted {pdf_file.name}")
            else:
                print(f"✗ Failed to convert {pdf_file.name}: {result.stderr}")
        except Exception as e:
            print(f"✗ Error converting {pdf_file.name}: {e}")
    
    return converted_files

def process_and_chunk_files(text_files):
    """Process text files and create chunks"""
    print(f"\nProcessing {len(text_files)} text files...")
    
    processor = DocumentProcessor()
    all_chunks = []
    
    for text_file in text_files:
        print(f"Processing {text_file.name}...")
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process the document
            chunks = processor.process_document(content, text_file.stem)
            all_chunks.extend(chunks)
            print(f"✓ Created {len(chunks)} chunks from {text_file.name}")
        except Exception as e:
            print(f"✗ Error processing {text_file.name}: {e}")
    
    # Save all chunks to JSON
    with open('processed_chunks.json', 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Total chunks created: {len(all_chunks)}")
    print("✓ Saved to processed_chunks.json")
    return all_chunks

def load_into_vector_db(chunks):
    """Load chunks into ChromaDB vector database"""
    print("\nLoading chunks into vector database...")
    
    try:
        # Initialize vector store
        vector_store = VectorStore()
        
        # Clear existing collection
        vector_store.collection.delete()
        print("✓ Cleared existing collection")
        
        # Load new chunks
        vector_store.load_documents(chunks)
        print(f"✓ Loaded {len(chunks)} chunks into vector database")
        
        return True
    except Exception as e:
        print(f"✗ Error loading into vector database: {e}")
        return False

def launch_streamlit():
    """Launch Streamlit application"""
    print("\nLaunching Streamlit application...")
    try:
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", "main.py"], 
                        cwd=".", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✓ Streamlit launched successfully!")
        print("✓ Open your browser to http://localhost:8501")
        return True
    except Exception as e:
        print(f"✗ Error launching Streamlit: {e}")
        return False

def main():
    """Main workflow"""
    print("=== Full RAG Workflow ===")
    
    # Step 1: Convert PDFs to text
    print("\n1. Converting PDFs to text...")
    text_files = convert_pdfs_to_text()
    if not text_files:
        print("No files to process. Exiting.")
        return
    
    # Step 2: Process and chunk files
    print("\n2. Processing and chunking files...")
    chunks = process_and_chunk_files(text_files)
    if not chunks:
        print("No chunks created. Exiting.")
        return
    
    # Step 3: Load into vector database
    print("\n3. Loading into vector database...")
    if not load_into_vector_db(chunks):
        print("Failed to load into vector database. Exiting.")
        return
    
    # Step 4: Launch Streamlit
    print("\n4. Launching Streamlit...")
    if launch_streamlit():
        print("\n✓ Workflow completed successfully!")
        print("✓ Your RAG system is ready to use!")
    else:
        print("\n✗ Failed to launch Streamlit")

if __name__ == "__main__":
    main()

