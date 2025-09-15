#!/usr/bin/env python3
import json
from pathlib import Path
from doc_processor import DocumentProcessor
from vector_store import VectorStore

def process_all_text_files():
    """Process all text files in ocr/output and create chunks"""
    output_dir = Path("ocr/output")
    text_files = list(output_dir.glob("*.txt"))
    
    if not text_files:
        print("No text files found in ocr/output")
        return []
    
    print(f"Processing {len(text_files)} text files...")
    
    processor = DocumentProcessor()
    all_chunks = []
    
    for text_file in text_files:
        print(f"Processing {text_file.name}...")
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process the document - save content to temp file first
            temp_file = f"temp_{text_file.name}"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Process the document
            result = processor.process_document(temp_file)
            chunks = result.get('chunks', [])
            
            # Clean up temp file
            Path(temp_file).unlink()
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

def main():
    print("=== Processing All Text Files ===")
    
    # Process and chunk files
    chunks = process_all_text_files()
    if not chunks:
        print("No chunks created. Exiting.")
        return
    
    # Load into vector database
    if load_into_vector_db(chunks):
        print("\n✓ All files processed and loaded into vector database!")
        print("✓ Ready to launch Streamlit!")
    else:
        print("\n✗ Failed to load into vector database")

if __name__ == "__main__":
    main()
